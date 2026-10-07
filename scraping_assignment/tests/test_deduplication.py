"""Unit tests for the deduplication module."""

import pytest
from processing.deduplication import generate_fingerprint, deduplicate_records


class TestGenerateFingerprint:
    def test_book_fingerprint_normalization_and_casing(self):
        rec1 = {"source": "books", "name_or_title": "A Light in the Attic!"}
        rec2 = {"source": "books", "name_or_title": "  a light in the attic  "}
        rec3 = {"source": "books", "name_or_title": "a   light in the attic..."}

        fp1 = generate_fingerprint(rec1)
        fp2 = generate_fingerprint(rec2)
        fp3 = generate_fingerprint(rec3)

        assert fp1 == fp2 == fp3
        assert len(fp1) == 64  # SHA-256 hex string length

    def test_different_books_different_fingerprints(self):
        rec1 = {"source": "books", "name_or_title": "A Light in the Attic"}
        rec2 = {"source": "books", "name_or_title": "Tipping the Velvet"}

        assert generate_fingerprint(rec1) != generate_fingerprint(rec2)

    def test_quote_fingerprint_author_and_text(self):
        rec1 = {
            "source": "quotes",
            "author": "Albert Einstein",
            "name_or_title": "The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.",
        }
        rec2 = {
            "source": "quotes",
            "author": "  albert einstein! ",
            "name_or_title": "the world as we have created it is a process of our thinking... extra tail text that differs after 50 chars",
        }

        # First 50 characters of normalized text:
        # "the world as we have created it is a process of ou"
        fp1 = generate_fingerprint(rec1)
        fp2 = generate_fingerprint(rec2)

        assert fp1 == fp2

    def test_quote_different_authors_differ(self):
        quote_text = "The world as we have created it is a process of our thinking."
        rec1 = {"source": "quotes", "author": "Albert Einstein", "name_or_title": quote_text}
        rec2 = {"source": "quotes", "author": "Stephen Hawking", "name_or_title": quote_text}

        assert generate_fingerprint(rec1) != generate_fingerprint(rec2)


class TestDeduplicateRecords:
    def test_separate_unique_and_duplicate(self):
        items = [
            {"source": "books", "name_or_title": "Book A", "price": 10.0},
            {"source": "books", "name_or_title": "Book B", "price": 20.0},
            {"source": "books", "name_or_title": "book a!", "price": 10.0},  # Duplicate of 0
            {"source": "quotes", "author": "Einstein", "name_or_title": "E=mc^2 is true"},
            {"source": "quotes", "author": "einstein", "name_or_title": "e=mc^2 is true!"},  # Duplicate of 3
        ]

        uniques, duplicates = deduplicate_records(items)

        assert len(uniques) == 3
        assert len(duplicates) == 2
        assert uniques[0]["name_or_title"] == "Book A"
        assert uniques[1]["name_or_title"] == "Book B"
        assert uniques[2]["author"] == "Einstein"
        assert duplicates[0]["name_or_title"] == "book a!"
        assert duplicates[1]["name_or_title"] == "e=mc^2 is true!"

    def test_all_unique_records(self):
        items = [
            {"source": "books", "name_or_title": "Book One"},
            {"source": "books", "name_or_title": "Book Two"},
            {"source": "books", "name_or_title": "Book Three"},
        ]
        uniques, duplicates = deduplicate_records(items)
        assert len(uniques) == 3
        assert len(duplicates) == 0

    def test_empty_records(self):
        uniques, duplicates = deduplicate_records([])
        assert uniques == []
        assert duplicates == []
