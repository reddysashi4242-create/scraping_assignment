"""Scraper for Books to Scrape (https://books.toscrape.com/).

Follows dynamic pagination via `li.next > a` until exhausted (no hardcoded page ranges).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BooksScraper(BaseScraper):
    """Scrapes books catalogue with dynamic pagination across all available pages."""

    DEFAULT_START_URL = "https://books.toscrape.com/"

    def __init__(
        self,
        start_url: Optional[str] = None,
        delay: float = 0.5,
        timeout: float = 10.0,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initialize BooksScraper.

        Args:
            start_url: Starting entrypoint URL (defaults to https://books.toscrape.com/).
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
        """Extract books by dynamically following pagination links until the end.

        Returns:
            List of raw dictionaries containing book details.
        """
        records: List[Dict[str, Any]] = []
        current_url: Optional[str] = self.start_url
        page_number = 1

        logger.info("Starting Books scraping from: %s", current_url)

        while current_url:
            response = self.get_page(current_url)
            if not response:
                logger.error(
                    "Failed to retrieve Books page %d at %s. Stopping Books scraper.",
                    page_number,
                    current_url,
                )
                break

            # Parse page content ensuring UTF-8 encoding
            html_content = response.content.decode("utf-8", errors="replace")
            soup = BeautifulSoup(html_content, "html.parser")

            product_pods = soup.select("article.product_pod")
            items_on_page = 0

            # Extract category from page header / breadcrumb if available
            page_category: Optional[str] = None
            breadcrumb_items = soup.select("ul.breadcrumb li")
            if len(breadcrumb_items) > 2:
                # Typically: Home > Books > Category Name
                page_category = breadcrumb_items[-1].get_text(strip=True)

            timestamp = datetime.now(timezone.utc).isoformat()

            for pod in product_pods:
                item = self._parse_product_pod(
                    pod=pod,
                    current_url=current_url,
                    timestamp=timestamp,
                    default_category=page_category,
                )
                if item:
                    records.append(item)
                    items_on_page += 1

            logger.info(
                "Visited page %d: %s (Extracted %d books, cumulative: %d)",
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
            "Finished Books scraping: %d raw records extracted across %d pages.",
            len(records),
            page_number,
        )
        return records

    def _parse_product_pod(
        self,
        pod: Any,
        current_url: str,
        timestamp: str,
        default_category: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Parse a single product pod element into a raw record.

        Args:
            pod: BeautifulSoup element for `article.product_pod`.
            current_url: Current page URL for resolving relative links.
            timestamp: Scraping timestamp in ISO format.
            default_category: Category inferred from page context if available.

        Returns:
            Dictionary with extracted raw book fields.
        """
        # Title: Preferred from 'title' attribute of <h3><a>, fallback to inner text
        title_tag = pod.select_one("h3 > a")
        title: Optional[str] = None
        detail_url: Optional[str] = None
        if title_tag:
            title = title_tag.get("title") or title_tag.get_text(strip=True)
            href = title_tag.get("href")
            if href:
                detail_url = urljoin(current_url, href)

        # Price
        price_tag = pod.select_one(".price_color")
        price_raw = price_tag.get_text(strip=True) if price_tag else None

        # Rating: CSS class on p.star-rating (e.g. ['star-rating', 'Three'])
        rating_tag = pod.select_one("p.star-rating")
        rating_raw: Optional[str] = None
        if rating_tag:
            classes = rating_tag.get("class", [])
            for cls in classes:
                if cls.lower() != "star-rating":
                    rating_raw = cls
                    break

        # Availability
        avail_tag = pod.select_one(".availability")
        availability_raw = avail_tag.get_text(strip=True) if avail_tag else None

        return {
            "source": "books",
            "source_url": detail_url,
            "name_or_title": title,
            "category": default_category,
            "price": price_raw,
            "rating": rating_raw,
            "availability": availability_raw,
            "author": None,
            "tags": None,
            "scraped_at": timestamp,
        }
