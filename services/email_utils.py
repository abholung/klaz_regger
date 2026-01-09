import csv
import imaplib
import ssl
import time
from email import message_from_bytes
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import openpyxl


@dataclass
class EmailAccount:
    address: str
    imap_server: str
    imap_port: int
    imap_login: str
    imap_password: str


DEFAULT_IMAP_PORT = 993


def load_emails_from_txt(path: Path, default_settings: dict) -> List[EmailAccount]:
    accounts: List[EmailAccount] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        accounts.append(
            EmailAccount(
                address=line.strip(),
                imap_server=default_settings["imap_server"],
                imap_port=default_settings["imap_port"],
                imap_login=default_settings["imap_login"],
                imap_password=default_settings["imap_password"],
            )
        )
    return accounts


def load_emails_from_csv(path: Path, default_settings: dict) -> List[EmailAccount]:
    accounts: List[EmailAccount] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                continue
            email = row.get("email") or row.get("address") or row.get("mail")
            if not email:
                continue
            accounts.append(
                EmailAccount(
                    address=email.strip(),
                    imap_server=(row.get("imap_server") or default_settings["imap_server"]),
                    imap_port=int(row.get("imap_port") or default_settings["imap_port"]),
                    imap_login=(row.get("imap_login") or default_settings["imap_login"]),
                    imap_password=(
                        row.get("imap_password") or default_settings["imap_password"]
                    ),
                )
            )
    return accounts


def load_emails_from_xlsx(path: Path, default_settings: dict) -> List[EmailAccount]:
    workbook = openpyxl.load_workbook(path)
    sheet = workbook.active
    headers = [str(cell.value).strip() if cell.value else "" for cell in sheet[1]]
    accounts: List[EmailAccount] = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        data = dict(zip(headers, row))
        email = data.get("email") or data.get("address") or data.get("mail")
        if not email:
            continue
        accounts.append(
            EmailAccount(
                address=str(email).strip(),
                imap_server=(data.get("imap_server") or default_settings["imap_server"]),
                imap_port=int(data.get("imap_port") or default_settings["imap_port"]),
                imap_login=(data.get("imap_login") or default_settings["imap_login"]),
                imap_password=(
                    data.get("imap_password") or default_settings["imap_password"]
                ),
            )
        )
    return accounts


def load_email_accounts(path: Path, default_settings: dict) -> List[EmailAccount]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return load_emails_from_txt(path, default_settings)
    if suffix == ".csv":
        return load_emails_from_csv(path, default_settings)
    if suffix in {".xlsx", ".xlsm"}:
        return load_emails_from_xlsx(path, default_settings)
    raise ValueError("Unsupported file type")


def check_imap_connection(account: EmailAccount, timeout: int = 15) -> bool:
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(account.imap_server, account.imap_port, ssl_context=context, timeout=timeout) as imap:
        imap.login(account.imap_login, account.imap_password)
        return True


def wait_for_confirmation(
    account: EmailAccount,
    subject_keywords: Iterable[str],
    timeout_seconds: int = 60,
    poll_interval: int = 5,
) -> Optional[str]:
    context = ssl.create_default_context()
    keywords = [keyword.lower() for keyword in subject_keywords]
    elapsed = 0
    while elapsed < timeout_seconds:
        with imaplib.IMAP4_SSL(
            account.imap_server, account.imap_port, ssl_context=context
        ) as imap:
            imap.login(account.imap_login, account.imap_password)
            imap.select("INBOX")

            status, data = imap.search(None, "ALL")
            if status == "OK":
                ids = data[0].split()
                if ids:
                    latest_id = ids[-1]
                    status, message_data = imap.fetch(latest_id, "(BODY.PEEK[HEADER])")
                    if status == "OK" and message_data:
                        msg = message_from_bytes(message_data[0][1])
                        subject = (msg.get("Subject") or "").lower()
                        if not keywords or any(keyword in subject for keyword in keywords):
                            return latest_id.decode()
        time.sleep(poll_interval)
        elapsed += poll_interval
    return None
