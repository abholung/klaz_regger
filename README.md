# klaz_regger

Инструмент автоматизации регистрации для вашего сайта (email + телефон + подтверждения), с логированием, поддержкой прокси и возможностью прерывания по `Ctrl+C`.

Доступны два режима:
- **HTTP-режим**: использует API эндпоинты, polling кодов и сохраняет cookies HTTP-сессии.
- **Браузерный режим**: использует Playwright для прохождения UI, получения cookies браузера и подтверждения email по ссылке.

## Архитектура

**Слои проекта:**

1. **CLI (`regger/cli.py`)**
   - Читает входной CSV (email, phone).
   - Загружает конфиг JSON.
   - Запускает поток регистрации и сохраняет результат.

2. **Оркестратор (`regger/workflow.py`)**
   - Реализует шаги:
     1. регистрация
     2. получение email-кода или ссылки из письма
     3. подтверждение email
     4. получение SMS-кода (polling или ручной ввод)
     5. подтверждение телефона
     6. запись результата (включая cookies)

3. **HTTP-клиент (`regger/client.py`)**
   - Унифицированные запросы в ваш API.
   - Забирает `user_id` и `token` из ответа регистрации.

4. **Провайдеры кодов (`regger/providers/*`)**
   - Отдельные интерфейсы для email/SMS.
   - HTTP-провайдеры поддерживают polling до получения кода.
   - IMAP-провайдер извлекает ссылку подтверждения из письма.
   - Ручной ввод SMS-кода доступен при необходимости.

5. **Браузерный сценарий (`regger/browser_workflow.py`)**
   - Автоматизирует страницу регистрации в браузере.
   - Переходит по ссылке подтверждения из письма.
   - Вводит SMS-код вручную.
   - Экспортирует cookies браузера.

6. **Хранилище (`regger/storage.py`)**
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
  "register_endpoint": "/api/register",
  "confirm_email_endpoint": "/api/email/confirm",
  "confirm_phone_endpoint": "/api/phone/confirm",
  "email_code_endpoint": "/api/email/code?email={email}",
  "sms_code_endpoint": "/api/sms/code?phone={phone}",
  "email_confirmation_mode": "code",
  "proxy": "",
  "user_id_field": "user_id",
  "token_field": "token",
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

`email_code_endpoint` и `sms_code_endpoint` поддерживают шаблоны `{email}`, `{phone}`, `{user_id}`.  
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
python -m regger.cli --config config.json --output data/output.csv --interactive --browser --email-mode link --manual-sms
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
- режим подтверждения email
- флаги браузерного режима и ручного ввода SMS
- путь для сохранения CSV

### Сборка EXE (Windows)

Если нужен единый `exe` с GUI, можно собрать через PyInstaller.

1. Установите зависимости:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

2. Соберите `exe`:

```bash
pyinstaller --noconsole --onefile -n regger_gui -m regger.gui
```

3. Готовый файл будет в `dist/regger_gui.exe`.

> Примечание: если используется браузерный режим, Playwright и браузеры нужно установить на целевой машине (или включить их отдельно в дистрибутив). Для установки браузеров:
>
> ```bash
> python -m playwright install
> ```

## Запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Скопируйте `config.example.json` в `config.json` и заполните реальные эндпоинты.

3. Подготовьте CSV с email/phone.

4. Запустите:

```bash
python -m regger.cli --config config.json --input data/input.sample.csv --output data/output.csv
```

### Интерактивный режим (одноразовая регистрация)

```bash
python -m regger.cli --config config.json --output data/output.csv --interactive
```

### Прокси

```bash
python -m regger.cli --config config.json --input data/input.sample.csv --output data/output.csv --proxy "http://user:pass@host:port"
```

### Подтверждение email по ссылке + ручной ввод SMS

```bash
python -m regger.cli --config config.json --input data/input.sample.csv --output data/output.csv --email-mode link --manual-sms
```

При желании можно задать фиксированный пароль:

```bash
python -m regger.cli --config config.json --input data/input.sample.csv --output data/output.csv --password "SuperSecret123!"
```

## Расширение

- Добавьте новые провайдеры email/SMS для интеграций с внешними сервисами.
- Реализуйте ретраи/лимиты/параллельную обработку при необходимости.
