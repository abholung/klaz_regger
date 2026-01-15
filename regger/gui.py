from __future__ import annotations

import json
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import List

from regger.cli import configure_logging, run_workflow
from regger.config import Settings
from regger.control import CancelToken, CancelledError
from regger.storage import AccountStore
from regger.records import AccountRecord


class TextHandler:
    def __init__(self, widget: tk.Text) -> None:
        self.widget = widget

    def write(self, message: str) -> None:
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, message)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self) -> None:
        return None


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Regger GUI")
        self.cancel_token = CancelToken()
        self.worker: threading.Thread | None = None

        self.config_path = tk.StringVar(value="config.json")
        self.email = tk.StringVar()
        self.phone = tk.StringVar()
        self.password = tk.StringVar()
        self.proxy = tk.StringVar()
        self.country_code = tk.StringVar()
        self.log_level = tk.StringVar(value="INFO")

        self._build()

    def _build(self) -> None:
        padding = {"padx": 8, "pady": 4}
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Config файл").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.config_path, width=50).grid(
            row=0, column=1, **padding
        )
        ttk.Button(frame, text="Выбрать", command=self._pick_config).grid(
            row=0, column=2, **padding
        )

        ttk.Label(frame, text="Email").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.email, width=50).grid(row=1, column=1, **padding)

        ttk.Label(frame, text="Телефон").grid(row=2, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.phone, width=50).grid(row=2, column=1, **padding)

        ttk.Label(frame, text="Код страны (например NL или +31)").grid(
            row=3, column=0, sticky="w", **padding
        )
        ttk.Entry(frame, textvariable=self.country_code, width=50).grid(
            row=3, column=1, **padding
        )

        ttk.Label(frame, text="Пароль (авто, 8+ символов)").grid(
            row=4, column=0, sticky="w", **padding
        )
        ttk.Entry(frame, textvariable=self.password, width=50, show="*").grid(
            row=4, column=1, **padding
        )
        ttk.Label(frame, text="(если пусто — пароль будет сгенерирован)").grid(
            row=4, column=2, sticky="w", **padding
        )

        ttk.Label(frame, text="Прокси (обязательно)").grid(
            row=5, column=0, sticky="w", **padding
        )
        ttk.Entry(frame, textvariable=self.proxy, width=50).grid(row=5, column=1, **padding)

        ttk.Label(frame, text="Email режим: link (фиксировано)").grid(
            row=6, column=0, sticky="w", **padding
        )

        ttk.Label(frame, text="Лог уровень").grid(row=7, column=0, sticky="w", **padding)
        ttk.Combobox(
            frame,
            textvariable=self.log_level,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            width=47,
        ).grid(row=7, column=1, **padding)

        ttk.Label(frame, text="Браузерный режим включен (фиксировано)").grid(
            row=8, column=0, sticky="w", **padding
        )

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=9, column=0, columnspan=3, sticky="w", **padding)
        ttk.Button(button_frame, text="Старт", command=self.start).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Отмена", command=self.cancel).pack(side="left", padx=4)

        self.log_widget = tk.Text(frame, height=12, width=80, state="disabled")
        self.log_widget.grid(row=10, column=0, columnspan=3, **padding)

    def _pick_config(self) -> None:
        path = filedialog.askopenfilename(title="Выберите config.json", filetypes=[("JSON", "*.json")])
        if path:
            self.config_path.set(path)

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Regger", "Процесс уже запущен")
            return
        if not self.email.get().strip() or not self.phone.get().strip():
            messagebox.showwarning("Regger", "Введите email и телефон")
            return
        if not self.proxy.get().strip():
            messagebox.showwarning("Regger", "Прокси обязателен")
            return
        self.cancel_token = CancelToken()
        self._clear_log()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def _clear_log(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.configure(state="disabled")

    def _run(self) -> None:
        configure_logging(self.log_level.get())
        log_sink = TextHandler(self.log_widget)
        try:
            config_path = Path(self.config_path.get())
            if not config_path.exists():
                raise FileNotFoundError(
                    f"Файл не найден: {config_path}. Укажите корректный config.json."
                )
            settings = Settings.from_json(config_path)
            settings = replace(settings, proxy=self.proxy.get().strip())
            settings = replace(settings, email_confirmation_mode="link")

            inputs: List[tuple[str, str]] = [(self.email.get().strip(), self.phone.get().strip())]
            cookies_folder = config_path.parent / "cookies"
            records = run_workflow(
                settings,
                inputs,
                self.password.get().strip() or None,
                password_length=12,
                cancel_token=self.cancel_token,
                country_code=self.country_code.get().strip() or None,
                followup_link_provider=self._ask_followup_link,
                sms_code_provider=self._ask_sms_code,
                phone_provider=self._ask_phone,
            )
            store = AccountStore("data/output.csv")
            store.write(records)
            self._write_cookies(records, cookies_folder)
            log_sink.write("Готово. Результаты сохранены.\n")
        except CancelledError:
            log_sink.write("Операция отменена пользователем.\n")
        except Exception as exc:  # pylint: disable=broad-except
            log_sink.write(f"Ошибка: {exc}\n")

    def _ask_followup_link(self) -> str:
        return simpledialog.askstring("Ссылка", "Введите ссылку для дальнейшей регистрации:") or ""

    def _ask_sms_code(self, prompt: str) -> str:
        return simpledialog.askstring("SMS код", prompt) or ""

    def _ask_phone(self) -> str:
        return simpledialog.askstring("Новый номер", "Введите новый номер телефона:") or ""

    def _write_cookies(self, records: List[AccountRecord], folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for record in records:
            safe_email = record.email.replace("@", "_at_").replace(".", "_")
            safe_password = record.password.replace(":", "_").replace("/", "_")
            path = folder / f"{safe_email}__{safe_password}.json"
            path.write_text(json.dumps(record.cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
