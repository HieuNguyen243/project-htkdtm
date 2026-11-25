"""Reference Playwright scraper template for authorized JS-rendered rental sites."""

from __future__ import annotations

import asyncio
from lxml import html

from base_scraper import BaseScraper, RoomListing
from config import parse_monthly_rent
from playwright_scraper import PlaywrightScraper


class PlaywrightSourceBot(BaseScraper):
    """Template bot combining BaseScraper validation with Playwright rendering.

    Only use against websites that permit automated access via robots.txt and
    explicit platform permission. Subclasses or instances should supply valid
    district URL templates and XPath selectors for the target site.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        url_patterns: dict[str, str],
        card_xpath: str = '//article[contains(@class, "listing-card")]',
        wait_selector: str | None = None,
        max_pages: int = 3,
        delay: float = 2.0,
        headless: bool = True,
        scroll_pages: bool = False,
    ) -> None:
        super().__init__(name=name, base_url=base_url, delay=delay)
        self.url_patterns = url_patterns
        self.card_xpath = card_xpath
        self.wait_selector = wait_selector
        self.max_pages = max_pages
        self.headless = headless
        self.scroll_pages = scroll_pages

    def district_url(self, slug: str, page: int = 1) -> str:
        pattern = self.url_patterns.get(slug)
        if not pattern:
            raise ValueError(f"Missing URL pattern for district slug: {slug}")
        return pattern.format(page=page)

    def parse_cards(self, page_html: str, district: str) -> tuple[list[RoomListing], list[dict[str, str]]]:
        """Override this method to extract RoomListing objects from rendered HTML."""
        tree = html.fromstring(page_html)
        accepted: list[RoomListing] = []
        rejected: list[dict[str, str]] = []
        for card in tree.xpath(self.card_xpath):
            url = "".join(card.xpath(".//a[@href][1]/@href")).strip()
            title = " ".join(card.xpath(".//h3[1]//text()")).strip()
            price_raw = " ".join(card.xpath('.//*[contains(@class, "price")][1]//text()')).strip()
            address = " ".join(card.xpath('.//*[contains(@class, "address")][1]//text()')).strip()
            area = " ".join(card.xpath('.//*[contains(@class, "area")][1]//text()')).strip()
            rent = parse_monthly_rent(price_raw)
            if not url or not title or rent is None:
                rejected.append(
                    {
                        "source_url": url or self.base_url,
                        "district": district,
                        "reason": "missing url, title, or monthly rent",
                    }
                )
                continue
            key = url.rstrip("/").rsplit("/", 1)[-1]
            accepted.append(
                RoomListing(
                    listing_id=f"{self.name}:{key}",
                    source_name=self.name,
                    source_record_key=key,
                    source_url=url,
                    district=district,
                    title=title,
                    rent_vnd_month=rent,
                    area_m2=area,
                    address_clean=address,
                )
            )
        return accepted, rejected

    async def _scrape_district_async(
        self, slug: str, district: str
    ) -> tuple[list[RoomListing], list[dict[str, str]]]:
        all_items: list[RoomListing] = []
        all_rejected: list[dict[str, str]] = []
        async with PlaywrightScraper(
            headless=self.headless,
            delay=self.delay,
            user_agent=self.user_agent,
            robots_policy=self.robots,
        ) as browser:
            for page_num in range(1, self.max_pages + 1):
                url = self.district_url(slug, page=page_num)
                rendered_html = await browser.navigate(url, wait_selector=self.wait_selector)
                if self.scroll_pages:
                    await browser.scroll_to_bottom()
                    rendered_html = await browser.get_page_content()
                items, rejected = self.parse_cards(rendered_html, district)
                if not items and not rejected:
                    break
                all_items.extend(items)
                all_rejected.extend(rejected)
        return all_items, all_rejected

    def scrape_district(self, slug: str, district: str) -> tuple[list[RoomListing], list[dict[str, str]]]:
        return asyncio.run(self._scrape_district_async(slug, district))
