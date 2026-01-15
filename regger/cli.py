from __future__ import annotations

import argparse
import csv
import logging
import secrets
import signal
from dataclasses import replace
from pathlib import Path
from typing import Iterable, List, Tuple

from regger.browser_workflow import BrowserRegistrationWorkflow
from regger.config import Settings
from regger.control import CancelToken, CancelledError
from regger.providers.imap_email import ImapEmailLinkProvider
from regger.storage import AccountStore
from regger.records import AccountRecord


def load_inputs(path: str | Path) -> List[Tuple[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: List[Tuple[str, str]] = []
        for row in reader:
            email = (row.get("email") or "").strip()
            phone = (row.get("phone") or "").strip()
            if not email or not phone:
                raise ValueError("Input CSV must include non-empty email and phone columns.")
            rows.append((email, phone))
        return rows


def generate_password(length: int) -> str:
    length = max(length, 8)
    lower = "abcdefghijklmnopqrstuvwxyz"
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    special = "!@#$%^&*"
    required = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(special),
        secrets.choice(digits),
    ]
    pool = lower + upper + digits + special
    required.extend(secrets.choice(pool) for _ in range(length - len(required)))
    secrets.SystemRandom().shuffle(required)
    return "".join(required)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def prompt_single_input() -> List[Tuple[str, str]]:
    email = input("Введите email: ").strip()
    phone = input("Введите номер телефона: ").strip()
    if not email or not phone:
        raise ValueError("Email и телефон обязательны.")
    return [(email, phone)]


def run_workflow(
    settings: Settings,
    inputs: Iterable[Tuple[str, str]],
    password: str | None,
    password_length: int,
    cancel_token: CancelToken,
    country_code: str | None = None,
    followup_link_provider=None,
    sms_code_provider=None,
    phone_provider=None,
) -> List[AccountRecord]:
    if settings.email_confirmation_mode != "link":
        raise ValueError("Browser mode requires email confirmation by link.")
    email_provider = ImapEmailLinkProvider(settings, cancel_token=cancel_token)
    workflow = BrowserRegistrationWorkflow(settings, email_provider, cancel_token=cancel_token)
    results: List[AccountRecord] = []
    for email, phone in inputs:
        current_password = password or generate_password(password_length)
        record = workflow.run(
            email=email,
            phone=phone,
            password=current_password,
            country_code=country_code,
            followup_link_provider=followup_link_provider,
            sms_code_provider=sms_code_provider,
            phone_provider=phone_provider,
        )
        results.append(record)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated registration workflow runner")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--input", help="CSV with columns email,phone")
    parser.add_argument("--output", required=True, help="CSV file to save results")
    parser.add_argument("--password", help="Use fixed password for all accounts")
    parser.add_argument(
        "--proxy",
        help="Proxy URL, e.g. http://user:pass@host:port (overrides config)",
    )
    parser.add_argument(
        "--email-mode",
        choices=["code", "link"],
        help="Email confirmation mode: code or link (overrides config)",
    )
    parser.add_argument(
        "--country",
        help="Country code value for dropdown selection (e.g. NL or +31)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for a single email/phone instead of reading CSV",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--password-length",
        type=int,
        default=12,
        help="Length of generated password when --password is not provided",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(args.log_level)
    settings = Settings.from_json(args.config)
    if args.proxy:
        settings = replace(settings, proxy=args.proxy)
    if args.email_mode:
        settings = replace(settings, email_confirmation_mode=args.email_mode)
    if args.interactive:
        inputs = prompt_single_input()
    else:
        if not args.input:
            raise ValueError("--input is required unless --interactive is used.")
        inputs = load_inputs(args.input)

    cancel_token = CancelToken()

    def handle_sigint(_signum, _frame) -> None:
        cancel_token.cancel()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        records = run_workflow(
            settings,
            inputs,
            args.password,
            args.password_length,
            cancel_token,
            country_code=args.country,
        )
    except CancelledError:
        logging.getLogger(__name__).warning("Операция отменена пользователем.")
        return

    store = AccountStore(args.output)
    store.write(records)


if __name__ == "__main__":
    main()
