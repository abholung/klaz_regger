from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from regger.client import RegistrationClient, RegistrationResult
from regger.control import CancelToken
from regger.providers.base import EmailCodeProvider, SmsCodeProvider


@dataclass(frozen=True)
class AccountRecord:
    email: str
    phone: str
    user_id: Optional[str]
    password: str
    token: str | None
    cookies: Dict[str, str]


class RegistrationWorkflow:
    def __init__(
        self,
        client: RegistrationClient,
        email_provider: EmailCodeProvider,
        sms_provider: SmsCodeProvider,
        email_confirmation_mode: str = "code",
        cancel_token: CancelToken | None = None,
    ) -> None:
        self.client = client
        self.email_provider = email_provider
        self.sms_provider = sms_provider
        self.email_confirmation_mode = email_confirmation_mode
        self.cancel_token = cancel_token
        self.logger = logging.getLogger(__name__)

    def run(self, email: str, phone: str, password: str) -> AccountRecord:
        if self.cancel_token:
            self.cancel_token.raise_if_cancelled()
        self.logger.info("Starting registration for %s", email)
        registration: RegistrationResult = self.client.register(email, phone, password)

        if self.email_confirmation_mode == "link":
            email_link = self.email_provider.get_code(email=email, user_id=registration.user_id)
            self.client.confirm_email_link(email_link)
        else:
            email_code = self.email_provider.get_code(email=email, user_id=registration.user_id)
            self.client.confirm_email(email=email, code=email_code, user_id=registration.user_id)

        sms_code = self.sms_provider.get_code(phone=phone, user_id=registration.user_id)
        self.client.confirm_phone(phone=phone, code=sms_code, user_id=registration.user_id)

        cookies = self.client.session.cookies.get_dict()
        self.logger.info("Registration completed for %s", email)
        return AccountRecord(
            email=email,
            phone=phone,
            user_id=registration.user_id,
            password=password,
            token=registration.token,
            cookies=cookies,
        )
