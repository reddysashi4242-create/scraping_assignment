"""Data validation module.

Enforces schema contracts and domain rules, tracking detailed rejection reasons
for quality reporting and metrics.
"""

from collections import Counter
import logging
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SOURCES = {"books", "quotes"}


def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single record against schema and domain rules.

    Rules checked:
      1. Source: Must be recognized ('books' or 'quotes').
      2. name_or_title: Must be present and non-empty.
      3. source_url: Must have valid HTTP/HTTPS syntax and network location.
      4. price: If present, must be a numeric value >= 0.
      5. rating: If present, must be an integer between 1 and 5.

    Args:
        record: Cleaned record dictionary.

    Returns:
        Tuple of (is_valid: bool, rejection_reasons: List[str]).
    """
    reasons: List[str] = []

    # 1. Source check
    source = record.get("source")
    if not source or not isinstance(source, str) or source.strip().lower() not in ALLOWED_SOURCES:
        reasons.append(f"Invalid or missing 'source': '{source}'")

    # 2. Presence of name_or_title
    name_or_title = record.get("name_or_title")
    if name_or_title is None or not str(name_or_title).strip():
        reasons.append("Missing or empty 'name_or_title'")

    # 3. Valid URL syntax
    source_url = record.get("source_url")
    if not source_url or not isinstance(source_url, str):
        reasons.append("Missing or empty 'source_url'")
    else:
        try:
            parsed = urlparse(source_url.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                reasons.append(f"Invalid URL syntax in 'source_url': '{source_url}'")
        except Exception as exc:
            reasons.append(f"Invalid URL syntax in 'source_url': '{source_url}' ({exc})")

    # 4. Numeric non-negative price (if present)
    price = record.get("price")
    if price is not None:
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            reasons.append(f"Price must be numeric, got '{price}' ({type(price).__name__})")
        elif price < 0:
            reasons.append(f"Price must be non-negative, got '{price}'")

    # 5. Rating in range 1-5 (if present)
    rating = record.get("rating")
    if rating is not None:
        if isinstance(rating, bool) or not isinstance(rating, int):
            reasons.append(f"Rating must be an integer, got '{rating}' ({type(rating).__name__})")
        elif rating < 1 or rating > 5:
            reasons.append(f"Rating must be in range 1-5, got '{rating}'")

    is_valid = len(reasons) == 0
    return is_valid, reasons


def validate_records(
    records: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """Validate a batch of records, separating valid from rejected records

    and tabulating rejection reason frequencies.

    Args:
        records: List of cleaned record dictionaries.

    Returns:
        Tuple containing:
          - valid_records: List of records passing all rules.
          - rejected_records: List of records that failed, enriched with '_rejection_reasons'.
          - reason_counts: Counter mapping each rejection reason to its frequency.
    """
    valid_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    reason_counter: Counter = Counter()

    for record in records:
        is_valid, reasons = validate_record(record)
        if is_valid:
            valid_records.append(record)
        else:
            rec_copy = dict(record)
            rec_copy["_rejection_reasons"] = reasons
            rejected_records.append(rec_copy)

            for reason in reasons:
                reason_counter[reason] += 1

            logger.warning(
                "Record rejected from source '%s' ('%s'): %s",
                record.get("source"),
                record.get("name_or_title", "Unknown"),
                ", ".join(reasons),
            )

    return valid_records, rejected_records, dict(reason_counter)
