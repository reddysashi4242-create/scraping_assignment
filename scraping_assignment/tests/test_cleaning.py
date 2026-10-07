"""Unit tests for the data cleaning and normalization module."""

import pytest
from processing.cleaning import (
    clean_whitespace,
    strip_surrounding_quotes,
    clean_price,
    clean_rating,
    clean_tags,
    normalize_url,
    clean_record,
)


class TestCleanWhitespace:
    def test_strip_and_collapse_spaces(self):
        text = "  Hello   world!  \t\n This  is a test.  "
        assert clean_whitespace(text) == "Hello world! This is a test."

    def test_non_breaking_spaces(self):
        text = "Item\xa0with\xa0\xa0non-breaking\xa0spaces"
        assert clean_whitespace(text) == "Item with non-breaking spaces"

    def test_newlines_and_tabs(self):
        text = "\n\r\tLine 1\n\n\rLine 2\t\t\r\n"
        assert clean_whitespace(text) == "Line 1 Line 2"

    def test_none_input(self):
        assert clean_whitespace(None) is None

    def test_empty_string(self):
        assert clean_whitespace("") == ""
        assert clean_whitespace("   \t\n  ") == ""


class TestStripSurroundingQuotes:
    def test_smart_double_quotes(self):
        text = "“The journey of a thousand miles begins with one step.”"
        assert strip_surrounding_quotes(text) == "The journey of a thousand miles begins with one step."

    def test_straight_double_quotes(self):
        text = '"Be the change you wish to see in the world."'
        assert strip_surrounding_quotes(text) == "Be the change you wish to see in the world."

    def test_straight_single_quotes(self):
        text = "'Stay hungry, stay foolish.'"
        assert strip_surrounding_quotes(text) == "Stay hungry, stay foolish."

    def test_smart_single_quotes(self):
        text = "‘To be or not to be.’"
        assert strip_surrounding_quotes(text) == "To be or not to be."

    def test_guillemets(self):
        text = "«Simplicity is the ultimate sophistication.»"
        assert strip_surrounding_quotes(text) == "Simplicity is the ultimate sophistication."

    def test_quotes_with_outer_whitespace(self):
        text = "  \n  “Spaced quote”  \t "
        assert strip_surrounding_quotes(text) == "Spaced quote"

    def test_nested_quotes(self):
        text = '“"Double wrapped quote"”'
        assert strip_surrounding_quotes(text) == "Double wrapped quote"

    def test_none_input(self):
        assert strip_surrounding_quotes(None) is None

    def test_preserves_internal_quotes(self):
        text = "“Don't cry because it's over, smile because it happened.”"
        assert strip_surrounding_quotes(text) == "Don't cry because it's over, smile because it happened."


class TestCleanPrice:
    def test_standard_pound_format(self):
        assert clean_price("£51.77") == 51.77

    def test_dollar_and_euro_formats(self):
        assert clean_price("$19.99") == 19.99
        assert clean_price("€120.50") == 120.50

    def test_non_breaking_space_in_price(self):
        assert clean_price("£\xa024.99") == 24.99

    def test_numeric_float_input(self):
        assert clean_price(45.99) == 45.99
        assert clean_price(10) == 10.0

    def test_negative_price(self):
        assert clean_price("-15.00") == -15.0

    def test_invalid_strings(self):
        assert clean_price("Free") is None
        assert clean_price("N/A") is None
        assert clean_price("") is None
        assert clean_price(None) is None


class TestCleanRating:
    def test_rating_words_standard(self):
        assert clean_rating("One") == 1
        assert clean_rating("Two") == 2
        assert clean_rating("Three") == 3
        assert clean_rating("Four") == 4
        assert clean_rating("Five") == 5

    def test_rating_words_case_insensitivity(self):
        assert clean_rating("one") == 1
        assert clean_rating("THREE") == 3
        assert clean_rating("fIvE") == 5

    def test_numeric_inputs(self):
        assert clean_rating(3) == 3
        assert clean_rating("4") == 4
        assert clean_rating(5.0) == 5

    def test_extended_words_for_validation_catching(self):
        # Clean converts word to int, allowing validator to catch out-of-bounds ratings
        assert clean_rating("Six") == 6
        assert clean_rating("Zero") == 0

    def test_invalid_and_empty(self):
        assert clean_rating("invalid-rating") is None
        assert clean_rating("") is None
        assert clean_rating(None) is None


class TestCleanTags:
    def test_list_of_tags_normalization(self):
        tags = ["World", "Change", "deep-thoughts", "Thinking"]
        assert clean_tags(tags) == "change;deep-thoughts;thinking;world"

    def test_deduplication_and_case_folding(self):
        tags = ["life", "Life", "LIFE", "books"]
        assert clean_tags(tags) == "books;life"

    def test_whitespace_and_empty_tags_in_list(self):
        tags = ["  tag1  ", "", "\t\n", "tag2\xa0"]
        assert clean_tags(tags) == "tag1;tag2"

    def test_string_input_delimited(self):
        raw = "philosophy, Inspirational; wisdom"
        assert clean_tags(raw) == "inspirational;philosophy;wisdom"

    def test_empty_tags(self):
        assert clean_tags([]) is None
        assert clean_tags("") is None
        assert clean_tags(None) is None


class TestNormalizeUrl:
    def test_relative_url_with_base(self):
        base = "https://books.toscrape.com/catalogue/page-2.html"
        rel = "in-her-wake_980/index.html"
        assert normalize_url(rel, base) == "https://books.toscrape.com/catalogue/in-her-wake_980/index.html"

    def test_already_absolute_url(self):
        url = "https://quotes.toscrape.com/page/2/"
        assert normalize_url(url, "https://quotes.toscrape.com/") == "https://quotes.toscrape.com/page/2/"

    def test_whitespace_in_url(self):
        url = "  https://example.com/item/1  \n"
        assert normalize_url(url) == "https://example.com/item/1"

    def test_none_url(self):
        assert normalize_url(None) is None


class TestCleanRecord:
    def test_clean_book_record(self):
        raw = {
            "source": "books",
            "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "name_or_title": "  A Light in the Attic  ",
            "category": "Poetry",
            "price": "£51.77",
            "rating": "Three",
            "availability": "In stock",
            "author": None,
            "tags": None,
            "scraped_at": "2026-10-07T12:00:00Z",
        }
        cleaned = clean_record(raw)
        assert cleaned["source"] == "books"
        assert cleaned["name_or_title"] == "A Light in the Attic"
        assert cleaned["price"] == 51.77
        assert cleaned["rating"] == 3
        assert cleaned["category"] == "Poetry"
        assert cleaned["author"] is None
        assert cleaned["tags"] is None

    def test_clean_quote_record(self):
        raw = {
            "source": "quotes",
            "source_url": "https://quotes.toscrape.com/page/1/",
            "name_or_title": "“The world as we have created it is a process of our thinking.”",
            "category": None,
            "price": None,
            "rating": None,
            "author": "  Albert Einstein  ",
            "tags": ["change", "Thinking", "world"],
            "scraped_at": "2026-10-07T12:00:00Z",
        }
        cleaned = clean_record(raw)
        assert cleaned["source"] == "quotes"
        assert cleaned["name_or_title"] == "The world as we have created it is a process of our thinking."
        assert cleaned["author"] == "Albert Einstein"
        assert cleaned["tags"] == "change;thinking;world"
        assert cleaned["price"] is None
        assert cleaned["rating"] is None
        assert cleaned["category"] is None
