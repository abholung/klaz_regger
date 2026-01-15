from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from regger.config import Settings
from regger.control import CancelToken
from regger.providers.base import SmsCodeProvider
from regger.utils import format_endpoint


class HttpSmsCodeProvider(SmsCodeProvider):
    def __init__(
        self,
        settings: Settings,
        session: Optional[requests.Session] = None,
        cancel_token: Optional[CancelToken] = None,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.cancel_token = cancel_token
        self.logger = logging.getLogger(__name__)

    def get_code(self, phone: str, user_id: str | None = None) -> str:
        deadline = time.time() + self.settings.polling.timeout_seconds
        while time.time() < deadline:
            if self.cancel_token:
                self.cancel_token.raise_if_cancelled()
            endpoint = format_endpoint(
                self.settings.sms_code_endpoint,
                email="",
                phone=phone,
                user_id=user_id or "",
            )
            response = self.session.get(self.settings.base_url + endpoint, timeout=15)
            response.raise_for_status()
            payload = response.json()
            code = payload.get("code")
            if code:
                self.logger.info("SMS code received for %s", phone)
                return str(code)
            self.logger.debug("SMS code not yet available for %s", phone)
            time.sleep(self.settings.polling.interval_seconds)
        raise TimeoutError("SMS confirmation code was not received in time.")
