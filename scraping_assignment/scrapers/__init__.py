"""Scrapers package for Books to Scrape and Quotes to Scrape."""

from .base_scraper import BaseScraper
from .books_scraper import BooksScraper
from .quotes_scraper import QuotesScraper

__all__ = ["BaseScraper", "BooksScraper", "QuotesScraper"]
