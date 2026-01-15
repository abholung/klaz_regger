from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AccountRecord:
    email: str
    phone: str
    user_id: Optional[str]
    password: str
    token: str | None
    cookies: Dict[str, str]
