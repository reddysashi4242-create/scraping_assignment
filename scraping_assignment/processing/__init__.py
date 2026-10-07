"""Data processing package containing cleaning, validation, and deduplication modules."""

from .cleaning import (
    clean_whitespace,
    strip_surrounding_quotes,
    clean_price,
    clean_rating,
    clean_tags,
    normalize_url,
    clean_record,
)
from .validation import validate_record, validate_records
from .deduplication import generate_fingerprint, deduplicate_records

__all__ = [
    "clean_whitespace",
    "strip_surrounding_quotes",
    "clean_price",
    "clean_rating",
    "clean_tags",
    "normalize_url",
    "clean_record",
    "validate_record",
    "validate_records",
    "generate_fingerprint",
    "deduplicate_records",
]
