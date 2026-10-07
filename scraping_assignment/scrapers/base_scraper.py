"""Base scraper class providing resilient HTTP session management, retry logic,

and polite request rate limiting.
"""

from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base scraper with built-in retry mechanism, polite delays,

    and custom header configuration.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (ETL-Pipeline-Assessment)"
    )

    def __init__(
        self,
        base_url: str,
        delay: float = 0.5,
        timeout: float = 10.0,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initialize the base scraper.

        Args:
            base_url: Root or initial URL for the target site.
            delay: Politeness delay in seconds between successive requests.
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum retry attempts for transient server errors.
            user_agent: Custom User-Agent header string.
        """
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.last_request_time: float = 0.0

        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        """Configure requests.Session with urllib3.util.Retry for resilience.

        Returns:
            Configured requests.Session instance.
        """
        session = requests.Session()

        # Retry on standard transient status codes and rate-limits
        retries = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    def _wait_for_politeness(self) -> None:
        """Enforce polite crawling delay between consecutive requests."""
        if self.delay <= 0:
            return
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            sleep_duration = self.delay - elapsed
            time.sleep(sleep_duration)

    def get_page(self, url: str) -> Optional[requests.Response]:
        """Fetch a page via HTTP GET with retry handling and polite delay.

        Args:
            url: The URL to fetch.

        Returns:
            requests.Response if successful, or None if the request failed.
        """
        self._wait_for_politeness()
        try:
            response = self.session.get(url, timeout=self.timeout)
            self.last_request_time = time.time()

            if response.status_code >= 400:
                logger.error(
                    "HTTP %d error fetching URL: %s",
                    response.status_code,
                    url,
                )
                return None

            return response
        except requests.RequestException as exc:
            self.last_request_time = time.time()
            logger.error(
                "Request failed for URL '%s' after retries: %s",
                url,
                exc,
                exc_info=True,
            )
            return None

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape all records from the target website.

        Returns:
            List of raw dictionaries extracted from pages.
        """
        pass

    def close(self) -> None:
        """Close the underlying requests.Session."""
        if self.session:
            self.session.close()

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
