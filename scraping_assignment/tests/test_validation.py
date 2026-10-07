"""Unit tests for the data validation module."""

import pytest
from processing.validation import validate_record, validate_records


@pytest.fixture
def valid_book():
    return {
        "source": "books",
        "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "name_or_title": "A Light in the Attic",
        "category": "Poetry",
        "price": 51.77,
        "rating": 3,
        "author": None,
        "tags": None,
        "scraped_at": "2026-10-07T12:00:00Z",
    }


@pytest.fixture
def valid_quote():
    return {
        "source": "quotes",
        "source_url": "https://quotes.toscrape.com/page/1/",
        "name_or_title": "The world as we have created it is a process of our thinking.",
        "category": None,
        "price": None,
        "rating": None,
        "author": "Albert Einstein",
        "tags": "change;thinking;world",
        "scraped_at": "2026-10-07T12:00:00Z",
    }


class TestValidateRecord:
    def test_valid_book_passes(self, valid_book):
        is_valid, reasons = validate_record(valid_book)
        assert is_valid is True
        assert reasons == []

    def test_valid_quote_passes(self, valid_quote):
        is_valid, reasons = validate_record(valid_quote)
        assert is_valid is True
        assert reasons == []

    def test_missing_or_empty_title(self, valid_book):
        record = dict(valid_book)
        record["name_or_title"] = ""
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("name_or_title" in r for r in reasons)

        record["name_or_title"] = "   "
        is_valid, reasons = validate_record(record)
        assert is_valid is False

        record["name_or_title"] = None
        is_valid, reasons = validate_record(record)
        assert is_valid is False

    def test_invalid_source(self, valid_book):
        record = dict(valid_book)
        record["source"] = "wikipedia"
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("source" in r for r in reasons)

        record["source"] = ""
        is_valid, _ = validate_record(record)
        assert is_valid is False

        record["source"] = None
        is_valid, _ = validate_record(record)
        assert is_valid is False

    def test_invalid_url_syntax(self, valid_book):
        record = dict(valid_book)
        record["source_url"] = "not_a_valid_url"
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("source_url" in r for r in reasons)

        record["source_url"] = "ftp://invalid-scheme.com/file"
        is_valid, reasons = validate_record(record)
        assert is_valid is False

        record["source_url"] = ""
        is_valid, reasons = validate_record(record)
        assert is_valid is False

    def test_negative_price(self, valid_book):
        record = dict(valid_book)
        record["price"] = -10.50
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("non-negative" in r for r in reasons)

    def test_non_numeric_price(self, valid_book):
        record = dict(valid_book)
        record["price"] = "fifty"
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("numeric" in r for r in reasons)

        record["price"] = True
        is_valid, reasons = validate_record(record)
        assert is_valid is False

    def test_zero_price_valid(self, valid_book):
        record = dict(valid_book)
        record["price"] = 0.0
        is_valid, reasons = validate_record(record)
        assert is_valid is True

    def test_rating_out_of_range(self, valid_book):
        for bad_rating in [0, 6, -1, 10]:
            record = dict(valid_book)
            record["rating"] = bad_rating
            is_valid, reasons = validate_record(record)
            assert is_valid is False
            assert any("range 1-5" in r for r in reasons)

    def test_rating_non_integer(self, valid_book):
        record = dict(valid_book)
        record["rating"] = 3.5
        is_valid, reasons = validate_record(record)
        assert is_valid is False
        assert any("integer" in r for r in reasons)

        record["rating"] = True
        is_valid, reasons = validate_record(record)
        assert is_valid is False

    def test_multiple_rejection_reasons_tracked(self, valid_book):
        bad_record = {
            "source": "bad_source",
            "source_url": "invalid_url",
            "name_or_title": "",
            "price": -100.0,
            "rating": 9,
        }
        is_valid, reasons = validate_record(bad_record)
        assert is_valid is False
        assert len(reasons) == 5


class TestValidateRecordsBatch:
    def test_batch_validation_separation(self, valid_book, valid_quote):
        invalid_rec = {
            "source": "books",
            "source_url": "https://books.toscrape.com/catalogue/bad.html",
            "name_or_title": "",
            "price": -5.0,
        }
        batch = [valid_book, invalid_rec, valid_quote]
        valid_list, rejected_list, reason_counts = validate_records(batch)

        assert len(valid_list) == 2
        assert len(rejected_list) == 1
        assert "_rejection_reasons" in rejected_list[0]
        assert "Missing or empty 'name_or_title'" in reason_counts
        assert "Price must be non-negative, got '-5.0'" in reason_counts
