from __future__ import annotations

from regger.providers.base import SmsCodeProvider


class ManualSmsCodeProvider(SmsCodeProvider):
    def get_code(self, phone: str, user_id: str | None = None) -> str:
        prompt = f"Введите SMS код для номера {phone}: "
        code = input(prompt).strip()
        if not code:
            raise ValueError("SMS код не может быть пустым.")
        return code
