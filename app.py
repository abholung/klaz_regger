import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import List, Optional

import requests
from services.email_utils import EmailAccount, check_imap_connection, load_email_accounts
from services.logging_setup import setup_logging
from services.phone_service import SmsActivateClient
from services.proxy_utils import ProxyPool, parse_proxy_list
from services.registration import RegistrationResult, register_account
from services.storage import export_results_csv, load_state, save_state


@dataclass
class AppConfig:
    target_url: str
    country_code: int
    accounts_to_create: int
    proxy_list: List[str]
    use_proxy_api: bool
    proxy_api_url: Optional[str]
    sms_api_key: str
    sms_service_code: str
    imap_server: str
    imap_port: int
    imap_login: str
    imap_password: str


class MockPhoneService:
    def get_balance(self) -> Optional[float]:
        return 10.0

    def get_number(self, country: int):
        return None


class RegistrationWorker(threading.Thread):
    def __init__(
        self,
        config: AppConfig,
        emails: List[EmailAccount],
        proxy_pool: ProxyPool,
        stop_event: threading.Event,
        log_queue: queue.Queue,
        results: List[RegistrationResult],
    ):
        super().__init__(daemon=True)
        self.config = config
        self.emails = emails
        self.proxy_pool = proxy_pool
        self.stop_event = stop_event
        self.log_queue = log_queue
        self.logger = setup_logging()
        self.results = results

    def run(self) -> None:
        self.logger.info("Registration worker started")
        for index in range(self.config.accounts_to_create):
            if self.stop_event.is_set():
                self.log_queue.put(("info", "Остановка по запросу пользователя."))
                break
            if index >= len(self.emails):
                self.log_queue.put(("error", "Недостаточно email-адресов."))
                break
            email_account = self.emails[index]
            proxy = self.proxy_pool.next_proxy()

            if not self._check_email(email_account):
                self.log_queue.put(
                    ("error", f"IMAP недоступен для {email_account.address}.")
                )
                continue

            phone = self._get_phone_number()
            if not phone:
                self.log_queue.put(("error", "Не удалось получить номер телефона."))

            self.log_queue.put(
                (
                    "info",
                    f"Регистрация {index + 1}/{self.config.accounts_to_create} для {email_account.address}",
                )
            )
            result = register_account(
                self.config.target_url,
                email_account,
                phone,
                proxy,
                max_attempts=3,
            )
            self.results.append(result)
            save_state(self.results)
            if result.status == "success":
                self.log_queue.put(("success", f"Успех: {result.email}"))
            else:
                self.log_queue.put(
                    (
                        "error",
                        f"Ошибка: {result.email} ({result.reason})",
                    )
                )
        self.log_queue.put(("info", "Регистрация завершена."))

    def _check_email(self, email_account: EmailAccount) -> bool:
        try:
            return check_imap_connection(email_account)
        except Exception as exc:
            self.logger.warning("IMAP check failed: %s", exc)
            return False

    def _get_phone_number(self):
        if not self.config.sms_api_key:
            return None
        client = SmsActivateClient(self.config.sms_api_key, self.config.sms_service_code)
        return client.get_number(self.config.country_code)


class RegistrationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mass Registration Manager")
        self.geometry("1000x700")
        self.logger = setup_logging()

        self.log_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: Optional[RegistrationWorker] = None
        self.results: List[RegistrationResult] = load_state()
        self.emails: List[EmailAccount] = []

        self._build_ui()
        self.after(200, self._process_log_queue)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        settings_frame = ttk.LabelFrame(main_frame, text="Настройки")
        settings_frame.pack(fill=tk.X)

        ttk.Label(settings_frame, text="Целевой URL").grid(row=0, column=0, sticky=tk.W)
        self.target_url_var = tk.StringVar(value="https://httpbin.org/post")
        ttk.Entry(settings_frame, textvariable=self.target_url_var, width=50).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W
        )

        ttk.Label(settings_frame, text="Страна (код)").grid(
            row=1, column=0, sticky=tk.W
        )
        self.country_var = tk.IntVar(value=1)
        ttk.Entry(settings_frame, textvariable=self.country_var, width=10).grid(
            row=1, column=1, padx=5, pady=5, sticky=tk.W
        )

        ttk.Label(settings_frame, text="Количество аккаунтов").grid(
            row=2, column=0, sticky=tk.W
        )
        self.count_var = tk.IntVar(value=5)
        ttk.Entry(settings_frame, textvariable=self.count_var, width=10).grid(
            row=2, column=1, padx=5, pady=5, sticky=tk.W
        )

        ttk.Label(settings_frame, text="API ключ SMS").grid(
            row=3, column=0, sticky=tk.W
        )
        self.sms_key_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.sms_key_var, width=50).grid(
            row=3, column=1, padx=5, pady=5, sticky=tk.W
        )

        ttk.Label(settings_frame, text="Сервис SMS").grid(
            row=4, column=0, sticky=tk.W
        )
        self.sms_service_var = tk.StringVar(value="kt")
        ttk.Entry(settings_frame, textvariable=self.sms_service_var, width=10).grid(
            row=4, column=1, padx=5, pady=5, sticky=tk.W
        )

        ttk.Label(settings_frame, text="Баланс SMS").grid(
            row=5, column=0, sticky=tk.W
        )
        self.balance_var = tk.StringVar(value="—")
        ttk.Label(settings_frame, textvariable=self.balance_var).grid(
            row=5, column=1, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(settings_frame, text="Стоимость регистрации").grid(
            row=5, column=2, sticky=tk.W
        )
        self.cost_var = tk.StringVar(value="—")
        ttk.Label(settings_frame, textvariable=self.cost_var).grid(
            row=5, column=3, padx=5, pady=5, sticky=tk.W
        )

        imap_frame = ttk.LabelFrame(main_frame, text="IMAP настройки по умолчанию")
        imap_frame.pack(fill=tk.X, pady=10)

        self.imap_server_var = tk.StringVar(value="imap.mail.ru")
        self.imap_port_var = tk.IntVar(value=993)
        self.imap_login_var = tk.StringVar()
        self.imap_password_var = tk.StringVar()

        ttk.Label(imap_frame, text="Сервер").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(imap_frame, textvariable=self.imap_server_var, width=25).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(imap_frame, text="Порт").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(imap_frame, textvariable=self.imap_port_var, width=8).grid(
            row=0, column=3, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(imap_frame, text="Логин").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(imap_frame, textvariable=self.imap_login_var, width=25).grid(
            row=1, column=1, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(imap_frame, text="Пароль").grid(row=1, column=2, sticky=tk.W)
        ttk.Entry(imap_frame, textvariable=self.imap_password_var, show="*", width=20).grid(
            row=1, column=3, padx=5, pady=5, sticky=tk.W
        )

        proxy_frame = ttk.LabelFrame(main_frame, text="Прокси")
        proxy_frame.pack(fill=tk.BOTH, pady=10)

        api_frame = ttk.Frame(proxy_frame)
        api_frame.pack(fill=tk.X, padx=5, pady=5)

        self.use_proxy_api_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_frame, text="Использовать Proxy API", variable=self.use_proxy_api_var
        ).pack(side=tk.LEFT)
        self.proxy_api_var = tk.StringVar()
        ttk.Entry(api_frame, textvariable=self.proxy_api_var, width=50).pack(
            side=tk.LEFT, padx=5
        )

        self.proxy_text = scrolledtext.ScrolledText(proxy_frame, height=5)
        self.proxy_text.pack(fill=tk.BOTH, padx=5, pady=5)

        email_frame = ttk.LabelFrame(main_frame, text="Email база")
        email_frame.pack(fill=tk.X)

        self.email_path_var = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.email_path_var, width=60).pack(
            side=tk.LEFT, padx=5, pady=5
        )
        ttk.Button(email_frame, text="Загрузить", command=self._load_emails).pack(
            side=tk.LEFT, padx=5
        )

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)

        ttk.Button(action_frame, text="Старт", command=self.start_registration).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action_frame, text="Стоп", command=self.stop_registration).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            action_frame, text="Экспорт CSV", command=self.export_results
        ).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="Логи")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _load_emails(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл email",
            filetypes=[("Email files", "*.txt *.csv *.xlsx"), ("All", "*.*")],
        )
        if not path:
            return
        self.email_path_var.set(path)
        try:
            settings = {
                "imap_server": self.imap_server_var.get(),
                "imap_port": self.imap_port_var.get(),
                "imap_login": self.imap_login_var.get(),
                "imap_password": self.imap_password_var.get(),
            }
            self.emails = load_email_accounts(Path(path), settings)
            self.log_queue.put(("info", f"Загружено {len(self.emails)} email."))
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))

    def _process_log_queue(self) -> None:
        while not self.log_queue.empty():
            level, message = self.log_queue.get()
            if level == "success":
                tag = "success"
            elif level == "error":
                tag = "error"
            else:
                tag = "info"
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.see(tk.END)
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")
        self.after(200, self._process_log_queue)

    def _build_config(self) -> AppConfig:
        return AppConfig(
            target_url=self.target_url_var.get(),
            country_code=self.country_var.get(),
            accounts_to_create=self.count_var.get(),
            proxy_list=self.proxy_text.get("1.0", tk.END).splitlines(),
            use_proxy_api=self.use_proxy_api_var.get(),
            proxy_api_url=self.proxy_api_var.get() or None,
            sms_api_key=self.sms_key_var.get(),
            sms_service_code=self.sms_service_var.get(),
            imap_server=self.imap_server_var.get(),
            imap_port=self.imap_port_var.get(),
            imap_login=self.imap_login_var.get(),
            imap_password=self.imap_password_var.get(),
        )

    def start_registration(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Внимание", "Регистрация уже запущена.")
            return
        if not self.emails:
            messagebox.showwarning("Внимание", "Сначала загрузите email базу.")
            return
        self._update_balance()
        config = self._build_config()
        proxy_lines = config.proxy_list
        if config.use_proxy_api and config.proxy_api_url:
            proxy_lines = self._fetch_proxy_api(config.proxy_api_url) or proxy_lines
        proxies = parse_proxy_list(proxy_lines)
        proxy_pool = ProxyPool(proxies)
        self.stop_event.clear()
        self.worker = RegistrationWorker(
            config,
            self.emails,
            proxy_pool,
            self.stop_event,
            self.log_queue,
            self.results,
        )
        self.worker.start()
        self.log_queue.put(("info", "Процесс регистрации запущен."))

    def stop_registration(self) -> None:
        self.stop_event.set()
        self.log_queue.put(("info", "Отправлен сигнал остановки."))

    def export_results(self) -> None:
        if not self.results:
            messagebox.showinfo("Информация", "Нет результатов для экспорта.")
            return
        path = filedialog.asksaveasfilename(
            title="Экспорт результатов",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        export_results_csv(Path(path), self.results)
        messagebox.showinfo("Готово", "Экспорт выполнен.")

    def _fetch_proxy_api(self, url: str) -> List[str]:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text.splitlines()
        except Exception as exc:
            self.log_queue.put(("error", f"Не удалось получить прокси: {exc}"))
            return []

    def _update_balance(self) -> None:
        if not self.sms_key_var.get():
            self.balance_var.set("—")
            self.cost_var.set("—")
            return
        try:
            client = SmsActivateClient(
                self.sms_key_var.get(), self.sms_service_var.get()
            )
            balance = client.get_balance()
            if balance is None:
                self.balance_var.set("Недоступно")
            else:
                self.balance_var.set(f"{balance:.2f}")
            self.cost_var.set("Зависит от сервиса")
        except Exception as exc:
            self.balance_var.set("Ошибка")
            self.cost_var.set("—")
            self.log_queue.put(("error", f"Ошибка баланса SMS: {exc}"))


if __name__ == "__main__":
    app = RegistrationApp()
    app.mainloop()
