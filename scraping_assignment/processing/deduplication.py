"""Deduplication module using SHA-256 content fingerprints.

Generates deterministic fingerprints tailored to domain entities:
  - Books: source + name_or_title (lowercased, punctuation stripped, spaces collapsed)
  - Quotes: source + author + first 50 chars of quote (lowercased, punctuation stripped, spaces collapsed)
"""

import hashlib
import logging
import re
import string
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _normalize_for_hashing(text: str) -> str:
    """Normalize string for robust fingerprinting:

    converts to lowercase, removes punctuation, and collapses whitespace.

    Args:
        text: Input string.

    Returns:
        Normalized string.
    """
    if not text:
        return ""
    # Lowercase
    lower_text = text.lower()
    # Strip punctuation using regex
    no_punct = re.sub(r"[^\w\s]", "", lower_text)
    # Collapse whitespace
    collapsed = re.sub(r"\s+", " ", no_punct).strip()
    return collapsed


def generate_fingerprint(record: Dict[str, Any]) -> str:
    """Generate a SHA-256 fingerprint for a record based on source type.

    Rules:
      - Books: source + name_or_title (lowercase, stripped punctuation, collapsed spaces)
      - Quotes: source + author + first 50 chars of quote
      - Fallback: source + name_or_title

    Args:
        record: Record dictionary.

    Returns:
        64-character SHA-256 hex digest string.
    """
    source = (record.get("source") or "").strip().lower()
    name_or_title = str(record.get("name_or_title") or "")
    author = str(record.get("author") or "")

    if source == "books":
        norm_title = _normalize_for_hashing(name_or_title)
        raw_key = f"books:{norm_title}"
    elif source == "quotes":
        norm_author = _normalize_for_hashing(author)
        norm_quote = _normalize_for_hashing(name_or_title)
        norm_quote_50 = norm_quote[:50]
        raw_key = f"quotes:{norm_author}:{norm_quote_50}"
    else:
        norm_title = _normalize_for_hashing(name_or_title)
        raw_key = f"{source}:{norm_title}"

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def deduplicate_records(
    records: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Deduplicate records using SHA-256 fingerprinting.

    Preserves the first seen occurrence of each record and isolates duplicates.

    Args:
        records: List of record dictionaries.

    Returns:
        Tuple of (unique_records, duplicate_records).
    """
    unique_records: List[Dict[str, Any]] = []
    duplicate_records: List[Dict[str, Any]] = []
    seen_fingerprints: Set[str] = set()

    for record in records:
        fp = generate_fingerprint(record)
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            unique_records.append(record)
        else:
            duplicate_records.append(record)

    logger.info(
        "Deduplication complete: %d unique records, %d duplicate records identified.",
        len(unique_records),
        len(duplicate_records),
    )
    return unique_records, duplicate_records
