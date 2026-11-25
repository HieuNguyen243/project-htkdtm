"""Playwright browser wrapper for authorized, robots-compliant JS-rendered pages."""

from __future__ import annotations

import asyncio
import random
import time

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from base_scraper import RobotsPolicy
from config import USER_AGENT


class PlaywrightScraper:
    """Manage Playwright browser lifecycle with polite rate limiting and robots.txt checks."""

    BLOCKED_STATUS_CODES = frozenset({401, 403, 429})

    def __init__(
        self,
        headless: bool = True,
        delay: float = 2.0,
        user_agent: str = USER_AGENT,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        if delay < 1.0:
            raise ValueError("delay must be at least 1.0 second")
        self.headless = headless
        self.delay = delay
        self.user_agent = user_agent
        self.robots_policy = robots_policy
        self._last_request = 0.0
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> PlaywrightScraper:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            user_agent=self.user_agent,
        )
        self._page = await self._context.new_page()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()

    async def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request
        jitter = random.uniform(0.2, 0.8)
        wait_seconds = self.delay + jitter - elapsed
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    async def navigate(
        self,
        url: str,
        wait_selector: str | None = None,
        timeout_ms: int = 20000,
    ) -> str:
        """Navigate to url after verifying robots.txt and rate limits, then return HTML."""
        if self._page is None:
            raise RuntimeError("PlaywrightScraper must be used inside an async with block")
        if self.robots_policy is not None and not self.robots_policy.can_fetch(url):
            raise PermissionError(f"Disallowed by robots.txt: {url}")

        await self._respect_rate_limit()
        try:
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        finally:
            self._last_request = time.monotonic()

        if response is not None and response.status in self.BLOCKED_STATUS_CODES:
            raise PermissionError(f"Access denied (HTTP {response.status}) at {url}; stopping cleanly")

        if wait_selector:
            await self._page.wait_for_selector(wait_selector, timeout=timeout_ms)
        else:
            await self._page.wait_for_load_state("networkidle", timeout=timeout_ms)
        return await self._page.content()

    async def get_page_content(self) -> str:
        """Return the current rendered DOM HTML."""
        if self._page is None:
            raise RuntimeError("PlaywrightScraper must be used inside an async with block")
        return await self._page.content()

    async def scroll_to_bottom(self, max_scrolls: int = 8, pause: float = 1.5) -> None:
        """Scroll incrementally to trigger lazy-loaded content on public pages."""
        if self._page is None:
            raise RuntimeError("PlaywrightScraper must be used inside an async with block")
        previous_height = 0
        for _ in range(max_scrolls):
            current_height = await self._page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                break
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(pause)
            previous_height = current_height
