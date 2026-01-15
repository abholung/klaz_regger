from __future__ import annotations

import email
import imaplib
import logging
import re
import time
from typing import Optional

from regger.config import Settings
from regger.control import CancelToken
from regger.providers.base import EmailCodeProvider


class ImapEmailLinkProvider(EmailCodeProvider):
    def __init__(self, settings: Settings, cancel_token: Optional[CancelToken] = None) -> None:
        if not settings.imap.host:
            raise ValueError("IMAP host is required for link-based email confirmation.")
        if not settings.imap.user or not settings.imap.password:
            raise ValueError("IMAP user/password are required for link-based email confirmation.")
        if not settings.imap.link_regex:
            raise ValueError("IMAP link_regex is required to extract confirmation URL.")
        self.settings = settings
        self.pattern = re.compile(settings.imap.link_regex)
        self.cancel_token = cancel_token
        self.logger = logging.getLogger(__name__)

    def get_code(self, email_address: str, user_id: str | None = None) -> str:
        deadline = time.time() + self.settings.polling.timeout_seconds
        while time.time() < deadline:
            if self.cancel_token:
                self.cancel_token.raise_if_cancelled()
            with imaplib.IMAP4_SSL(self.settings.imap.host, self.settings.imap.port) as client:
                client.login(self.settings.imap.user, self.settings.imap.password)
                client.select(self.settings.imap.folder)
                criteria = f'(TO "{email_address}")'
                status, messages = client.search(None, criteria)
                if status != "OK":
                    time.sleep(self.settings.polling.interval_seconds)
                    continue
                for message_id in reversed(messages[0].split()):
                    status, msg_data = client.fetch(message_id, "(RFC822)")
                    if status != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    body = _extract_text(msg)
                    match = self.pattern.search(body)
                    if match:
                        self.logger.info("Email confirmation link found for %s", email_address)
                        return match.group(0)
            self.logger.debug("Email confirmation link not yet available for %s", email_address)
            time.sleep(self.settings.polling.interval_seconds)
        raise TimeoutError("Email confirmation link was not received in time.")


def _extract_text(message: email.message.Message) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
        return "\n".join(parts)
    payload = message.get_payload(decode=True) or b""
    return payload.decode(message.get_content_charset() or "utf-8", errors="ignore")
