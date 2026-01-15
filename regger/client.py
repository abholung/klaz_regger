from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from regger.config import Settings


@dataclass(frozen=True)
class RegistrationResult:
    user_id: str
    token: str | None
    raw: Dict[str, Any]


class RegistrationClient:
    def __init__(self, settings: Settings, session: Optional[requests.Session] = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()

    def register(self, email: str, phone: str, password: str) -> RegistrationResult:
        payload = {"email": email, "phone": phone, "password": password}
        response = self.session.post(
            self.settings.base_url + self.settings.register_endpoint,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        user_id = data.get(self.settings.user_id_field)
        if not user_id:
            raise ValueError("Registration response did not include user id field.")
        token = data.get(self.settings.token_field)
        return RegistrationResult(user_id=str(user_id), token=token, raw=data)

    def confirm_email(self, email: str, code: str, user_id: str | None = None) -> Dict[str, Any]:
        payload = {"email": email, "code": code}
        if user_id:
            payload["user_id"] = user_id
        response = self.session.post(
            self.settings.base_url + self.settings.confirm_email_endpoint,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def confirm_phone(self, phone: str, code: str, user_id: str | None = None) -> Dict[str, Any]:
        payload = {"phone": phone, "code": code}
        if user_id:
            payload["user_id"] = user_id
        response = self.session.post(
            self.settings.base_url + self.settings.confirm_phone_endpoint,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def confirm_email_link(self, link: str) -> Dict[str, Any]:
        response = self.session.get(link, timeout=20, allow_redirects=True)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"status": "ok", "body": response.text}
