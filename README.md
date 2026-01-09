# klaz_regger

Массовый менеджер регистрации аккаунтов с графическим интерфейсом.

## Возможности
- Загрузка email баз (txt/csv/xlsx) с IMAP-настройками.
- Проверка IMAP до регистрации.
- Ротация SOCKS5-прокси из списка или через Proxy API.
- Интеграция с SMS-Activate (баланс, аренда номера).
- Генерация паролей, мониторинг email для подтверждения.
- Логи в интерфейсе и файл `logs/app.log`.
- Экспорт результатов в CSV и сохранение прогресса.

## Запуск
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Форматы входных файлов
### TXT
Каждая строка содержит email.

### CSV/XLSX
Ожидаемые колонки (регистр не важен):
- `email`
- `imap_server`
- `imap_port`
- `imap_login`
- `imap_password`

Если колонки не заданы, используются значения из UI.
