"""Data cleaning and transformation module.

Implements normalization for whitespace, quotation marks, prices, ratings,
tags, and URLs across scraped data sources.
"""

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

# Quotation characters to strip from quote texts
QUOTE_CHARS = '"\'“”‘’«»„‟‚'

# Mapping of number words to integer values
RATING_WORD_MAP = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def clean_whitespace(val: Optional[str]) -> Optional[str]:
    """Strip leading/trailing whitespace and collapse extra whitespace,

    newlines, and non-breaking spaces (\\xa0) into a single space.

    Args:
        val: Input string or None.

    Returns:
        Cleaned string, or None if input was None.
    """
    if val is None:
        return None
    # Replace non-breaking spaces and other special space characters
    normalized = val.replace("\xa0", " ")
    # Collapse all whitespace sequences (spaces, tabs, newlines) into single space
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed


def strip_surrounding_quotes(val: Optional[str]) -> Optional[str]:
    """Strip surrounding quotation marks (smart, double, single, guillemets)

    and collapse internal whitespace.

    Args:
        val: Input quote string or None.

    Returns:
        Quote string with surrounding quotes removed, or None.
    """
    cleaned = clean_whitespace(val)
    if not cleaned:
        return cleaned

    # Strip surrounding quotes repeatedly in case of nested/stacked quote marks
    prev = None
    while prev != cleaned and cleaned:
        prev = cleaned
        cleaned = cleaned.strip(QUOTE_CHARS).strip()
    return cleaned


def clean_price(val: Any) -> Optional[float]:
    """Parse and clean a price representation into a numeric float.

    Strips currency symbols like '£', '$', '€', commas, and extra text.

    Args:
        val: Numeric or string price representation.

    Returns:
        Float value of price, or None if invalid or empty.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    if not isinstance(val, str):
        val = str(val)

    cleaned = val.replace("\xa0", " ").strip()
    if not cleaned:
        return None

    # Remove currency symbols and comma separators
    # Supports formats like '£51.77', '51.77', '$ 19.99', '€ 100,50'
    cleaned = cleaned.replace("£", "").replace("$", "").replace("€", "")
    cleaned = cleaned.replace(",", "").strip()

    # Match numeric float / integer pattern (optional sign, digits, optional decimal)
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def clean_rating(val: Any) -> Optional[int]:
    """Convert rating words ('One'..'Five') or numeric values into an integer 1..5.

    Preserves other integers (like 0 or 6) if explicitly parsed so validation can
    properly inspect out-of-range errors.

    Args:
        val: Rating as a word string (e.g. 'Three'), number, or string digit.

    Returns:
        Integer rating or None if unrecognized/empty.
    """
    if val is None:
        return None

    if isinstance(val, int):
        return val

    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return None

    s = clean_whitespace(str(val))
    if not s:
        return None

    s_lower = s.lower()
    if s_lower in RATING_WORD_MAP:
        return RATING_WORD_MAP[s_lower]

    try:
        # Check if direct digit string (e.g., '3')
        return int(s)
    except ValueError:
        return None


def clean_tags(val: Any) -> Optional[str]:
    """Clean and normalize tags: lowercase, sorted alphabetically, joined with ';'.

    Args:
        val: List of tag strings, or a delimited tag string.

    Returns:
        Normalized tags string (e.g. 'abilities;choices') or None if empty.
    """
    if val is None:
        return None

    raw_items: List[str] = []
    if isinstance(val, (list, tuple, set)):
        raw_items = [str(item) for item in val]
    elif isinstance(val, str):
        # Split on commas or semicolons
        raw_items = re.split(r"[,;]", val)
    else:
        raw_items = [str(val)]

    cleaned_set = set()
    for item in raw_items:
        clean_item = clean_whitespace(item)
        if clean_item:
            cleaned_set.add(clean_item.lower())

    if not cleaned_set:
        return None

    # Alphabetically sorted, joined with semicolon
    sorted_tags = sorted(cleaned_set)
    return ";".join(sorted_tags)


def normalize_url(url: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    """Normalize a URL to full HTTP/HTTPS format.

    Args:
        url: URL string or relative path.
        base_url: Optional base URL for resolving relative links.

    Returns:
        Fully resolved URL string or None.
    """
    if url is None:
        return None

    cleaned = clean_whitespace(url)
    if not cleaned:
        return None

    if base_url:
        cleaned = urljoin(base_url, cleaned)

    return cleaned


def clean_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a raw extracted record into the standardized Common Data Model.

    Common schema fields:
      source, source_url, name_or_title, category, price, rating, author, tags, scraped_at

    Fields not applicable to a source remain None/empty without inventing fake values.

    Args:
        raw_record: Dictionary containing extracted raw fields.

    Returns:
        Cleaned record dictionary following the standard schema.
    """
    raw_source = clean_whitespace(raw_record.get("source"))
    source_lower = raw_source.lower() if raw_source else ""

    raw_title = raw_record.get("name_or_title")
    if source_lower == "quotes":
        name_or_title = strip_surrounding_quotes(raw_title)
    else:
        name_or_title = clean_whitespace(raw_title)

    raw_url = raw_record.get("source_url")
    source_url = normalize_url(raw_url)

    # Category: applicable to books if present, None for quotes
    category = clean_whitespace(raw_record.get("category"))

    # Price: applicable to books, None for quotes
    price = clean_price(raw_record.get("price")) if raw_record.get("price") is not None else None

    # Rating: applicable to books, None for quotes
    rating = clean_rating(raw_record.get("rating")) if raw_record.get("rating") is not None else None

    # Author: applicable to quotes, None for books
    author = clean_whitespace(raw_record.get("author"))

    # Tags: applicable to quotes, None for books
    tags = clean_tags(raw_record.get("tags"))

    scraped_at = clean_whitespace(raw_record.get("scraped_at"))

    return {
        "source": source_lower,
        "source_url": source_url,
        "name_or_title": name_or_title,
        "category": category,
        "price": price,
        "rating": rating,
        "author": author,
        "tags": tags,
        "scraped_at": scraped_at,
    }
