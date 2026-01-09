import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class PhoneNumber:
    id: str
    number: str


class SmsActivateClient:
    BASE_URL = "https://sms-activate.org/stubs/handler_api.php"

    def __init__(self, api_key: str, service: str = "kt"):
        self.api_key = api_key
        self.service = service

    def _request(self, params: dict) -> str:
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.text

    def get_balance(self) -> Optional[float]:
        text = self._request({"api_key": self.api_key, "action": "getBalance"})
        if "ACCESS_BALANCE" in text:
            return float(text.split(":")[1])
        return None

    def get_number(self, country: int) -> Optional[PhoneNumber]:
        params = {
            "api_key": self.api_key,
            "action": "getNumber",
            "service": self.service,
            "country": country,
        }
        text = self._request(params)
        if text.startswith("ACCESS_NUMBER"):
            _, activation_id, number = text.split(":")
            return PhoneNumber(id=activation_id, number=number)
        return None

    def set_status(self, activation_id: str, status: int) -> None:
        self._request(
            {
                "api_key": self.api_key,
                "action": "setStatus",
                "id": activation_id,
                "status": status,
            }
        )
