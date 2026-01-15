from __future__ import annotations

from abc import ABC, abstractmethod


class EmailCodeProvider(ABC):
    @abstractmethod
    def get_code(self, email: str, user_id: str | None = None) -> str:
        raise NotImplementedError


class SmsCodeProvider(ABC):
    @abstractmethod
    def get_code(self, phone: str, user_id: str | None = None) -> str:
        raise NotImplementedError
