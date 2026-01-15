from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class PollingConfig:
    interval_seconds: int = 5
    timeout_seconds: int = 180


@dataclass(frozen=True)
class ImapConfig:
    host: str = ""
    port: int = 993
    user: str = ""
    password: str = ""
    folder: str = "INBOX"
    link_regex: str = ""


@dataclass(frozen=True)
class BrowserConfig:
    register_url: str = ""
    email_selector: str = ""
    password_selector: str = ""
    submit_selector: str = ""
    phone_selector: str = ""
    phone_submit_selector: str = ""
    sms_code_selector: str = ""
    sms_submit_selector: str = ""
    phone_stage: str = "after_email_confirm"


@dataclass(frozen=True)
class Settings:
    base_url: str
    email_confirmation_mode: str = "code"
    proxy: str | None = None
    polling: PollingConfig = PollingConfig()
    imap: ImapConfig = ImapConfig()
    browser: BrowserConfig = BrowserConfig()

    @staticmethod
    def from_json(path: str | Path) -> "Settings":
        raw: Dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        polling_raw = raw.get("polling", {})
        polling = PollingConfig(
            interval_seconds=polling_raw.get("interval_seconds", 5),
            timeout_seconds=polling_raw.get("timeout_seconds", 180),
        )
        imap_raw = raw.get("imap", {})
        imap = ImapConfig(
            host=imap_raw.get("host", ""),
            port=imap_raw.get("port", 993),
            user=imap_raw.get("user", ""),
            password=imap_raw.get("password", ""),
            folder=imap_raw.get("folder", "INBOX"),
            link_regex=imap_raw.get("link_regex", ""),
        )
        browser_raw = raw.get("browser", {})
        browser = BrowserConfig(
            register_url=browser_raw.get("register_url", ""),
            email_selector=browser_raw.get("email_selector", ""),
            password_selector=browser_raw.get("password_selector", ""),
            submit_selector=browser_raw.get("submit_selector", ""),
            phone_selector=browser_raw.get("phone_selector", ""),
            phone_submit_selector=browser_raw.get("phone_submit_selector", ""),
            sms_code_selector=browser_raw.get("sms_code_selector", ""),
            sms_submit_selector=browser_raw.get("sms_submit_selector", ""),
            phone_stage=browser_raw.get("phone_stage", "after_email_confirm"),
        )
        return Settings(
            base_url=raw["base_url"],
            email_confirmation_mode=raw.get("email_confirmation_mode", "code"),
            proxy=raw.get("proxy"),
            polling=polling,
            imap=imap,
            browser=browser,
        )
