# klaz_regger

Инструмент автоматизации регистрации для вашего сайта (email + телефон + подтверждения), с логированием, поддержкой прокси и возможностью прерывания по `Ctrl+C`.

Доступен один режим:
- **Браузерный режим**: использует Playwright для прохождения UI, получения cookies браузера и подтверждения email по ссылке.

## Архитектура

**Слои проекта:**

1. **GUI (`regger/gui.py`)**
   - Принимает email/телефон/прокси/код страны.
   - Пароль генерируется автоматически (8 символов, 1 заглавная, 1 строчная, 1 число, 1 спецсимвол).
   - Показывает окна для ввода ссылки и SMS-кода, включая смену номера.
   - Сохраняет cookies в папку `cookies` рядом с `config.json`.

2. **Провайдеры кодов (`regger/providers/*`)**
   - IMAP-провайдер извлекает ссылку подтверждения из письма.
   - Ручной ввод SMS-кода доступен при необходимости.

3. **Браузерный сценарий (`regger/browser_workflow.py`)**
   - Автоматизирует страницу регистрации в браузере.
   - Переходит по ссылке подтверждения из письма.
   - Вводит SMS-код вручную, поддерживает смену номера.
   - Экспортирует cookies браузера.

4. **Хранилище (`regger/storage.py`)**
   - Сохраняет результат в CSV.

## Формат данных

### Cookies

Cookies сохраняются отдельными файлами JSON в папку `cookies` рядом с `config.json`.

## Конфигурация

Файл `config.example.json` показывает обязательные поля:

```json
{
  "base_url": "https://www.kleinanzeigen.de/",
  "email_confirmation_mode": "link",
  "proxy": "portal.anyip.io:1080:user_e1f71f,type_mobile,country_DE,session_7284d267:111111",
  "imap": {
    "host": "imap.example.com",
    "port": 993,
    "user": "user@example.com",
    "password": "app-password",
    "folder": "INBOX",
    "link_regex": "https://example.com/confirm\\?token=[A-Za-z0-9._-]+"
  },
  "browser": {
    "register_url": "https://www.kleinanzeigen.de/m-benutzer-anmeldung.html",
    "email_selector": "#email",
    "password_selector": "#password",
    "submit_selector": "button[type=submit]",
    "account_type_selector": "#account-type",
    "account_type_value": "Privat",
    "name_selector": "#account-name",
    "name_value": "Privat",
    "phone_selector": "#phone",
    "phone_submit_selector": "#phone-submit",
    "country_selector": "#country-code",
    "sms_code_selector": "#sms_code",
    "sms_submit_selector": "#sms-submit",
    "change_number_selector": "#change-number",
    "phone_stage": "after_email_confirm"
  },
  "polling": {
    "interval_seconds": 5,
    "timeout_seconds": 180
  }
}
```

Если `email_confirmation_mode` = `link`, будет использован IMAP для извлечения ссылки подтверждения.

### Браузерный режим

1. Установите Playwright и браузеры:

```bash
pip install -r requirements.txt
python -m playwright install
```

2. Заполните блок `browser` в `config.json` (селекторы для вашей формы).

3. Запустите GUI и заполните поля.

### Графический интерфейс (GUI)

Запуск GUI приложения:

```bash
python -m regger.gui
```

В GUI можно указать:
- config.json (путь к файлу с селекторами формы)
- email/phone
- прокси (обязателен, формат `host:port:user:pass`)
- код страны

В окне ввода SMS можно написать `change`, чтобы перейти к смене номера (если задан `change_number_selector`).

### Сборка EXE (Windows)

Если нужен единый `exe` с GUI, можно собрать через PyInstaller.

1. Быстрый способ (батник):

```bat
build_exe.bat
```

Батник создаст виртуальное окружение, установит зависимости, Playwright (внутрь сборки) и соберет `exe`.

2. Ручная сборка:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

3. Соберите `exe`:

```bash
pyinstaller --noconsole --onefile -n regger_gui regger/gui.py
```

4. Готовый файл будет в `dist/regger_gui.exe`.

> Примечание: для EXE браузеры Playwright включаются через `PLAYWRIGHT_BROWSERS_PATH=0` в батнике, чтобы не требовать отдельной установки на целевой машине.
>
> ```bash
> python -m playwright install
> ```

## Запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
python -m playwright install
```

2. Скопируйте `config.example.json` в `config.json` и заполните IMAP и селекторы формы.

3. Запустите GUI (браузерный режим).
