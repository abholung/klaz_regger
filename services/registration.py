import random
import string
import time
from dataclasses import dataclass
from typing import Optional

import requests

from services.email_utils import EmailAccount, wait_for_confirmation
from services.proxy_utils import ProxyConfig
from services.phone_service import PhoneNumber


@dataclass
class RegistrationResult:
    email: str
    password: str
    proxy: Optional[str]
    phone: Optional[str]
    status: str
    reason: Optional[str] = None


def generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def perform_registration(
    target_url: str,
    email: EmailAccount,
    phone: Optional[PhoneNumber],
    password: str,
    proxy: Optional[ProxyConfig],
) -> bool:
    payload = {
        "email": email.address,
        "password": password,
        "phone": phone.number if phone else None,
    }
    proxies = None
    if proxy:
        proxy_url = proxy.as_url()
        proxies = {"http": proxy_url, "https": proxy_url}
    response = requests.post(target_url, json=payload, proxies=proxies, timeout=40)
    response.raise_for_status()
    return response.status_code == 200


def register_account(
    target_url: str,
    email: EmailAccount,
    phone: Optional[PhoneNumber],
    proxy: Optional[ProxyConfig],
    max_attempts: int = 3,
) -> RegistrationResult:
    password = generate_password()
    attempt = 0
    while attempt < max_attempts:
        try:
            success = perform_registration(target_url, email, phone, password, proxy)
            if success:
                confirmation_id = wait_for_confirmation(
                    email, ["confirm", "activate", "подтвердите"], timeout_seconds=60
                )
                if confirmation_id:
                    return RegistrationResult(
                        email=email.address,
                        password=password,
                        proxy=proxy.as_url() if proxy else None,
                        phone=phone.number if phone else None,
                        status="success",
                    )
                return RegistrationResult(
                    email=email.address,
                    password=password,
                    proxy=proxy.as_url() if proxy else None,
                    phone=phone.number if phone else None,
                    status="failed",
                    reason="No confirmation email",
                )
        except Exception as exc:
            attempt += 1
            if attempt >= max_attempts:
                return RegistrationResult(
                    email=email.address,
                    password=password,
                    proxy=proxy.as_url() if proxy else None,
                    phone=phone.number if phone else None,
                    status="failed",
                    reason=str(exc),
                )
            time.sleep(2)
            continue
    return RegistrationResult(
        email=email.address,
        password=password,
        proxy=proxy.as_url() if proxy else None,
        phone=phone.number if phone else None,
        status="failed",
        reason="Unknown error",
    )
