# AI Usage & Verification Disclosure

**Assessment**: Realisieren Technologies (NxtWave) Take-Home Technical Assessment  
**Project**: Production-grade Web Scraping & ETL Data Pipeline

---

## 1. Disclosure of AI Assistance & Tools Used

In accordance with academic integrity and assessment guidelines, this document transparently outlines the use of AI tools during the development of this project:

- **AI Tools Used**: Google Antigravity IDE (Gemini 3.8 Flash model).
- **Primary Roles**:
  - Drafting initial boilerplate code and test fixtures.
  - Designing regex patterns for currency and Unicode quote handling.
  - Designing parametric test cases for edge condition coverage.
  - Formatting markdown documentation and architectural flowcharts.

---

## 2. Sample Prompts Used During Development

### Prompt 1: Session Retry & Politeness Design
> *"Implement a reusable BaseScraper class in Python using requests.Session and urllib3.util.Retry. It must retry on status codes 429, 500, 502, 503, 504, enforce a polite 0.5s rate-limiting delay between requests, and support clean context management."*

### Prompt 2: Text Normalization & Quote Stripping
> *"Write a cleaning function in Python that collapses multiple spaces, newlines, tabs, and non-breaking spaces (\xa0). In addition, write a function that strips smart double and single quotes (“”‘’), straight quotes, and guillemets («») without stripping interior apostrophes from words like 'it's' or 'don't'."*

### Prompt 3: Unit Testing Boundary Conditions
> *"Create a comprehensive pytest test suite for data validation and cleaning modules. Include tests for negative prices, invalid ratings (both string and out-of-range integers like 0 or 6), whitespace edge cases, and SHA-256 fingerprint collision resistance."*

---

## 3. Code Areas Assisted vs. Custom Implementations

| Area / File | AI Assistance Level | What the AI Generated | Developer Review & Refinement |
|---|---|---|---|
| `scrapers/base_scraper.py` | Moderate | Initial `HTTPAdapter` mount and `Retry` configuration template. | Added idempotent request method restriction (`HEAD, GET, OPTIONS`), custom User-Agent, and politeness timing calculation. |
| `scrapers/books_scraper.py` | Low | CSS selector suggestions for `product_pod`. | Validated dynamic pagination (`li.next > a`), relative link resolution via `urljoin`, and verified title attribute extraction to prevent truncated titles. |
| `scrapers/quotes_scraper.py` | Low | Basic DOM traversal for quotes and tags. | Added UTF-8 response byte decoding to prevent Windows console encoding corruption, and tag deduplication logic. |
| `processing/cleaning.py` | Moderate | Regex patterns for numeric price extraction and rating word mapping. | Added Unicode quote character coverage (`“”‘’«»„‟‚`), `\xa0` handling, and sorted tag formatting. |
| `processing/validation.py` | Low | Schema validation function structure. | Enforced type guarding (preventing `bool` from masquerading as `int`), and built a counter mechanism to tabulate multiple rejection reasons. |
| `processing/deduplication.py`| Low | SHA-256 hash boilerplate. | Standardized normalization (`_normalize_for_hashing`) for title and author strings, and ensured first-50-character truncation for quote fingerprints. |
| `tests/*.py` | Moderate | Test case templates and assertion fixtures. | Expanded test suite to 55 test cases covering boundary conditions, malformed types, and edge cases. |

---

## 4. Human Verification & Debugging Steps

Every component generated or assisted by AI underwent rigorous manual inspection, profiling, and debugging:

1. **Relative URL Resolution Verification**:
   - *Problem*: On `books.toscrape.com`, page 1 links to `catalogue/page-2.html`, while page 2 links to `page-3.html`.
   - *Fix*: Verified that `urllib.parse.urljoin(current_url, next_href)` properly resolves both relative patterns to `https://books.toscrape.com/catalogue/page-X.html` without path duplication.

2. **Windows Character Encoding Debugging**:
   - *Problem*: `div.quote span.text` on Windows command lines exhibited `\ufffd` or encoding distortion when using default platform encodings.
   - *Fix*: Explicitly decoded HTTP response bytes via `response.content.decode("utf-8", errors="replace")` and configured file handlers with explicit `encoding="utf-8"`.

3. **Validation Type Coercion Bug**:
   - *Problem*: In Python, `isinstance(True, int)` evaluates to `True`, which could allow boolean values into numeric rating and price checks.
   - *Fix*: Explicitly added `if isinstance(val, bool): reject` guards before numeric validation.

4. **Real-world Duplicate Verification**:
   - *Inspection*: Pipeline logs showed 1,000 raw books scraped, but 999 unique books in the final output.
   - *Verification*: Inspected raw data and confirmed that *"The Star-Touched Queen"* is indeed duplicated on pages 19 and 20 of `books.toscrape.com`. The deduplication logic functioned as intended.

---

## 5. Technical Interview Preparation & Defense

Below are key architectural questions and model explanations for interview defense:

### Q1: Why use dynamic pagination over range-based loops?
> **Answer**: Hardcoding `range(1, 51)` couples the pipeline to current page volumes. If the site expands to 60 pages or contracts to 20, a range loop either under-fetches or raises 404 HTTP errors. Dynamic pagination via `soup.select_one("li.next > a")` follows hypermedia controls (HATEOAS), ensuring the scraper gracefully handles changes in catalogue size.

### Q2: Why is politeness delay essential in web scraping?
> **Answer**: Without delay, 60 requests would fire in rapid bursts, which can overwhelm target servers, trigger HTTP 429 (Too Many Requests), or cause IP blacklisting. A 0.5s polite delay balances pipeline throughput with responsible web etiquette.

### Q3: How does the retry mechanism handle transient failures?
> **Answer**: `urllib3.util.Retry` is configured with an exponential backoff factor (`0.5s`) for transient HTTP status codes (`429`, `500`, `502`, `503`, `504`). Requests are retried up to 3 times before raising an error, preventing momentary network blips from terminating the entire run.

### Q4: Why SHA-256 for deduplication rather than comparing full strings?
> **Answer**: SHA-256 provides a fixed-length 64-character deterministic digest with virtually zero collision risk. Storing 64-character hashes in a hash set has $O(1)$ memory lookup efficiency, whereas comparing multi-paragraph raw quote strings across thousands of items increases memory and comparison overhead.

### Q5: How is fault isolation achieved between data sources?
> **Answer**: In `main.py`, each scraper executes in an independent `try/except` block. If `books.toscrape.com` experiences prolonged downtime or unrecoverable network failures, the error is logged, its status is flagged as failed in the summary report, and the pipeline continues to scrape `quotes.toscrape.com`.
