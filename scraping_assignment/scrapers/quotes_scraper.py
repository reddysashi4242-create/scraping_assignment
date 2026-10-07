"""Scraper for Quotes to Scrape (https://quotes.toscrape.com/).

Follows dynamic pagination via `li.next > a` until exhausted (no hardcoded page ranges).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class QuotesScraper(BaseScraper):
    """Scrapes quotes catalogue with dynamic pagination across all available pages."""

    DEFAULT_START_URL = "https://quotes.toscrape.com/"

    def __init__(
        self,
        start_url: Optional[str] = None,
        delay: float = 0.5,
        timeout: float = 10.0,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initialize QuotesScraper.

        Args:
            start_url: Starting entrypoint URL (defaults to https://quotes.toscrape.com/).
            delay: Rate limit delay in seconds.
            timeout: HTTP timeout in seconds.
            max_retries: Maximum HTTP retry attempts.
            user_agent: Optional User-Agent header.
        """
        super().__init__(
            base_url=start_url or self.DEFAULT_START_URL,
            delay=delay,
            timeout=timeout,
            max_retries=max_retries,
            user_agent=user_agent,
        )
        self.start_url = start_url or self.DEFAULT_START_URL

    def scrape(self) -> List[Dict[str, Any]]:
        """Extract quotes by dynamically following pagination links until the end.

        Returns:
            List of raw dictionaries containing quote records.
        """
        records: List[Dict[str, Any]] = []
        current_url: Optional[str] = self.start_url
        page_number = 1

        logger.info("Starting Quotes scraping from: %s", current_url)

        while current_url:
            response = self.get_page(current_url)
            if not response:
                logger.error(
                    "Failed to retrieve Quotes page %d at %s. Stopping Quotes scraper.",
                    page_number,
                    current_url,
                )
                break

            html_content = response.content.decode("utf-8", errors="replace")
            soup = BeautifulSoup(html_content, "html.parser")

            quote_elements = soup.select("div.quote")
            items_on_page = 0
            timestamp = datetime.now(timezone.utc).isoformat()

            for quote_div in quote_elements:
                item = self._parse_quote_element(
                    element=quote_div,
                    page_url=current_url,
                    timestamp=timestamp,
                )
                if item:
                    records.append(item)
                    items_on_page += 1

            logger.info(
                "Visited page %d: %s (Extracted %d quotes, cumulative: %d)",
                page_number,
                current_url,
                items_on_page,
                len(records),
            )

            # Follow dynamic pagination: li.next > a
            next_link = soup.select_one("li.next > a")
            if next_link and next_link.get("href"):
                next_href = next_link["href"].strip()
                current_url = urljoin(current_url, next_href)
                page_number += 1
            else:
                logger.info(
                    "No next page link found at page %d. Pagination complete.",
                    page_number,
                )
                current_url = None

        logger.info(
            "Finished Quotes scraping: %d raw records extracted across %d pages.",
            len(records),
            page_number,
        )
        return records

    def _parse_quote_element(
        self,
        element: Any,
        page_url: str,
        timestamp: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse a single quote container element into a raw record.

        Args:
            element: BeautifulSoup element for `div.quote`.
            page_url: Current page URL.
            timestamp: Scraping timestamp in ISO format.

        Returns:
            Dictionary with extracted raw quote fields.
        """
        # Quote text
        text_tag = element.select_one("span.text")
        raw_text = text_tag.get_text() if text_tag else None

        # Author
        author_tag = element.select_one("small.author")
        raw_author = author_tag.get_text(strip=True) if author_tag else None

        # Tags
        tag_tags = element.select("div.tags a.tag")
        raw_tags = [t.get_text(strip=True) for t in tag_tags] if tag_tags else []

        # Source URL: Current page URL where the quote appears
        # (Quotes to Scrape provides author bio links, but the quote itself resides on page_url)
        quote_source_url = page_url

        return {
            "source": "quotes",
            "source_url": quote_source_url,
            "name_or_title": raw_text,
            "category": None,
            "price": None,
            "rating": None,
            "author": raw_author,
            "tags": raw_tags,
            "scraped_at": timestamp,
        }
