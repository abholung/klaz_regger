from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from regger.workflow import AccountRecord


class AccountStore:
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)

    def write(self, records: Iterable[AccountRecord]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["email", "phone", "user_id", "password", "token", "cookies"],
            )
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "email": record.email,
                        "phone": record.phone,
                        "user_id": record.user_id or "",
                        "password": record.password,
                        "token": record.token or "",
                        "cookies": json.dumps(record.cookies, ensure_ascii=False),
                    }
                )
