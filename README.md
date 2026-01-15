# klaz_regger

Инструмент автоматизации регистрации для вашего сайта (email + телефон + подтверждения), с логированием, поддержкой прокси и возможностью прерывания по `Ctrl+C`.

Доступен один режим:
- **Браузерный режим**: использует Playwright для прохождения UI, получения cookies браузера и подтверждения email по ссылке.

## Архитектура

**Слои проекта:**

1. **CLI (`regger/cli.py`)**
   - Читает входной CSV (email, phone).
   - Загружает конфиг JSON.
   - Запускает поток регистрации и сохраняет результат.

2. **Провайдеры кодов (`regger/providers/*`)**
   - IMAP-провайдер извлекает ссылку подтверждения из письма.
   - Ручной ввод SMS-кода доступен при необходимости.

3. **Браузерный сценарий (`regger/browser_workflow.py`)**
   - Автоматизирует страницу регистрации в браузере.
   - Переходит по ссылке подтверждения из письма.
   - Вводит SMS-код вручную.
   - Экспортирует cookies браузера.

4. **Хранилище (`regger/storage.py`)**
   - Сохраняет результат в CSV.

## Формат данных

### Входной CSV

```csv
email,phone
user1@example.com,+15550000001
```

### Выходной CSV

```csv
email,phone,user_id,password,token,cookies
user1@example.com,+15550000001,12345,MyPassword!,eyJhbGciOi...,"{\"sessionid\": \"...\"}"
```

## Конфигурация

Файл `config.example.json` показывает обязательные поля:

```json
{
  "base_url": "https://example.com",
  "email_confirmation_mode": "link",
  "proxy": "",
  "imap": {
    "host": "imap.example.com",
    "port": 993,
    "user": "user@example.com",
    "password": "app-password",
    "folder": "INBOX",
    "link_regex": "https://example.com/confirm\\?token=[A-Za-z0-9._-]+"
  },
  "browser": {
    "register_url": "https://example.com/register",
    "email_selector": "#email",
    "password_selector": "#password",
    "submit_selector": "button[type=submit]",
    "phone_selector": "#phone",
    "phone_submit_selector": "#phone-submit",
    "sms_code_selector": "#sms_code",
    "sms_submit_selector": "#sms-submit",
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

3. Запустите:

```bash
python -m regger.cli --config config.json --output data/output.csv --interactive --email-mode link
```

### Графический интерфейс (GUI)

Запуск GUI приложения:

```bash
python -m regger.gui
```

В GUI можно указать:
- `config.json`
- email/phone/password
- прокси
- режим подтверждения email (фиксирован на link)
- путь для сохранения CSV

### Сборка EXE (Windows)

Если нужен единый `exe` с GUI, можно собрать через PyInstaller.

1. Быстрый способ (батник):

```bat
build_exe.bat
```

Батник создаст виртуальное окружение, установит зависимости, Playwright и соберет `exe`.

2. Ручная сборка:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

3. Соберите `exe`:

```bash
pyinstaller --noconsole --onefile -n regger_gui -m regger.gui
```

4. Готовый файл будет в `dist/regger_gui.exe`.

> Примечание: если используется браузерный режим, Playwright и браузеры нужно установить на целевой машине (или включить их отдельно в дистрибутив). Для установки браузеров:
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

3. Запустите GUI или CLI (браузерный режим).
