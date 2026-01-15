from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict

from regger.config import Settings
from regger.control import CancelToken
from regger.providers.base import EmailCodeProvider
from regger.providers.manual_sms import ManualSmsCodeProvider
from regger.records import AccountRecord
from regger.utils import parse_proxy


class BrowserRegistrationWorkflow:
    def __init__(
        self,
        settings: Settings,
        email_provider: EmailCodeProvider,
        cancel_token: CancelToken | None = None,
    ) -> None:
        self.settings = settings
        self.email_provider = email_provider
        self.cancel_token = cancel_token
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        email: str,
        phone: str,
        password: str,
        country_code: str | None = None,
        followup_link_provider: Callable[[], str] | None = None,
        sms_code_provider: Callable[[str], str] | None = None,
        phone_provider: Callable[[], str] | None = None,
    ) -> AccountRecord:
        if self.cancel_token:
            self.cancel_token.raise_if_cancelled()
        browser_config = self.settings.browser
        if not browser_config.register_url:
            raise ValueError("browser.register_url is required for browser workflow")
        if not browser_config.email_selector or not browser_config.password_selector:
            raise ValueError("browser email/password selectors are required")
        if not browser_config.submit_selector:
            raise ValueError("browser submit_selector is required")

        from playwright.sync_api import sync_playwright

        proxy = {"server": parse_proxy(self.settings.proxy or "")}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, proxy=proxy)
            context = browser.new_context()
            page = context.new_page()

            self.logger.info("Opening registration page")
            page.goto(browser_config.register_url, wait_until="domcontentloaded")
            page.fill(browser_config.email_selector, email)
            page.fill(browser_config.password_selector, password)

            if browser_config.account_type_selector and browser_config.account_type_value:
                page.select_option(browser_config.account_type_selector, browser_config.account_type_value)

            if browser_config.name_selector:
                page.fill(browser_config.name_selector, browser_config.name_value)

            if browser_config.phone_stage == "before_email_confirm" and browser_config.phone_selector:
                page.fill(browser_config.phone_selector, phone)

            page.click(browser_config.submit_selector)
            page.wait_for_timeout(1000)

            if self.settings.email_confirmation_mode == "link":
                confirmation_link = self.email_provider.get_code(email=email)
                self.logger.info("Opening confirmation link in browser")
                page.goto(confirmation_link, wait_until="domcontentloaded")
            else:
                raise ValueError("Browser workflow currently requires email confirmation by link.")

            if followup_link_provider:
                followup_link = followup_link_provider()
                if followup_link:
                    self.logger.info("Opening follow-up link in browser")
                    page.goto(followup_link, wait_until="domcontentloaded")

            if browser_config.phone_stage == "after_email_confirm" and browser_config.phone_selector:
                if browser_config.country_selector and country_code:
                    page.select_option(browser_config.country_selector, country_code)
                page.fill(browser_config.phone_selector, phone)
                if browser_config.phone_submit_selector:
                    page.click(browser_config.phone_submit_selector)
                page.wait_for_timeout(500)

            sms_provider = ManualSmsCodeProvider()
            if browser_config.sms_code_selector:
                while True:
                    prompt = f"Введите SMS код для номера {phone} или 'change' для смены номера: "
                    code_value = (
                        sms_code_provider(prompt) if sms_code_provider else sms_provider.get_code(phone=phone)
                    )
                    if code_value.strip().lower() == "change":
                        if not browser_config.change_number_selector:
                            raise ValueError("change_number_selector is required to change phone number.")
                        page.click(browser_config.change_number_selector)
                        page.wait_for_timeout(500)
                        phone = phone_provider() if phone_provider else phone
                        if browser_config.country_selector and country_code:
                            page.select_option(browser_config.country_selector, country_code)
                        page.fill(browser_config.phone_selector, phone)
                        if browser_config.phone_submit_selector:
                            page.click(browser_config.phone_submit_selector)
                        page.wait_for_timeout(500)
                        continue
                    page.fill(browser_config.sms_code_selector, code_value)
                    if browser_config.sms_submit_selector:
                        page.click(browser_config.sms_submit_selector)
                    page.wait_for_timeout(500)
                    break

            cookies = {cookie["name"]: cookie["value"] for cookie in context.cookies()}
            browser.close()

        return AccountRecord(
            email=email,
            phone=phone,
            user_id=None,
            password=password,
            token=None,
            cookies=cookies,
        )
