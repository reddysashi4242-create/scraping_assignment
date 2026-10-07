"""Main CLI entrypoint for the end-to-end web scraping and ETL data pipeline.

Orchestrates:
  1. Extract: Runs BooksScraper and QuotesScraper with isolated failure domains.
  2. Clean: Normalizes whitespace, quotes, prices, ratings, tags, and URLs.
  3. Validate: Enforces schema contracts and logs rejection reasons.
  4. Deduplicate: Generates SHA-256 fingerprints to filter duplicates.
  5. Consolidate: Exports final dataset to CSV and metrics to summary_report.json.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper
from processing.cleaning import clean_record
from processing.validation import validate_records
from processing.deduplication import deduplicate_records

# Schema fields for the consolidated dataset
CSV_FIELDNAMES = [
    "source",
    "source_url",
    "name_or_title",
    "category",
    "price",
    "rating",
    "author",
    "tags",
    "scraped_at",
]


def setup_logging(log_file_path: Path, verbose: bool = False) -> None:
    """Configure console and file logging.

    Args:
        log_file_path: Absolute or relative path to the log file.
        verbose: If True, set console level to DEBUG.
    """
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File handler: logs everything to scraper.log (UTF-8)
    file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def run_pipeline(
    sources: List[str],
    delay: float = 0.5,
    timeout: float = 10.0,
    output_dir: Optional[Path] = None,
    log_file: Optional[Path] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Execute the end-to-end ETL pipeline.

    Args:
        sources: List of sources to extract ('books', 'quotes').
        delay: Politeness delay in seconds between HTTP requests.
        timeout: HTTP request timeout in seconds.
        output_dir: Directory where CSV and JSON reports will be saved.
        log_file: Path to scraper.log.
        verbose: Verbose logging flag.

    Returns:
        Summary report dictionary.
    """
    out_dir = output_dir or (PROJECT_ROOT / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_file or (PROJECT_ROOT / "logs" / "scraper.log")
    setup_logging(log_path, verbose=verbose)

    logger = logging.getLogger("ETLPipeline")
    start_dt = datetime.now(timezone.utc)
    start_time_iso = start_dt.isoformat()
    t0 = time.time()

    logger.info("==================================================")
    logger.info("Starting Web Scraping & ETL Data Pipeline Execution")
    logger.info("Active Sources: %s", ", ".join(sources))
    logger.info("Politeness Delay: %.2fs | Timeout: %.1fs", delay, timeout)
    logger.info("==================================================")

    source_metrics: Dict[str, Dict[str, Any]] = {}
    raw_records: List[Dict[str, Any]] = []

    # ----------------------------------------------------
    # 1. EXTRACT (with isolated try/except per source)
    # ----------------------------------------------------
    if "books" in sources:
        source_metrics["books"] = {"status": "PENDING", "raw_records": 0}
        logger.info("--- Phase 1A: Extracting Books to Scrape ---")
        try:
            with BooksScraper(delay=delay, timeout=timeout) as scraper:
                books_data = scraper.scrape()
                source_metrics["books"]["raw_records"] = len(books_data)
                source_metrics["books"]["status"] = "SUCCESS"
                raw_records.extend(books_data)
                logger.info("Extracted %d raw records from Books.", len(books_data))
        except Exception as exc:
            logger.error("Books scraper failed unexpectedly: %s", exc, exc_info=True)
            source_metrics["books"]["status"] = f"FAILED: {str(exc)}"

    if "quotes" in sources:
        source_metrics["quotes"] = {"status": "PENDING", "raw_records": 0}
        logger.info("--- Phase 1B: Extracting Quotes to Scrape ---")
        try:
            with QuotesScraper(delay=delay, timeout=timeout) as scraper:
                quotes_data = scraper.scrape()
                source_metrics["quotes"]["raw_records"] = len(quotes_data)
                source_metrics["quotes"]["status"] = "SUCCESS"
                raw_records.extend(quotes_data)
                logger.info("Extracted %d raw records from Quotes.", len(quotes_data))
        except Exception as exc:
            logger.error("Quotes scraper failed unexpectedly: %s", exc, exc_info=True)
            source_metrics["quotes"]["status"] = f"FAILED: {str(exc)}"

    # ----------------------------------------------------
    # 2. CLEAN
    # ----------------------------------------------------
    logger.info("--- Phase 2: Cleaning and Normalizing Records ---")
    cleaned_records: List[Dict[str, Any]] = []
    for raw in raw_records:
        cleaned = clean_record(raw)
        cleaned_records.append(cleaned)
    logger.info("Cleaned %d records into common schema format.", len(cleaned_records))

    # ----------------------------------------------------
    # 3. VALIDATE
    # ----------------------------------------------------
    logger.info("--- Phase 3: Validating Records ---")
    valid_records, rejected_records, rejection_reasons = validate_records(cleaned_records)
    logger.info(
        "Validation complete: %d valid records, %d rejected records.",
        len(valid_records),
        len(rejected_records),
    )
    if rejection_reasons:
        logger.warning("Rejection reasons breakdown: %s", json.dumps(rejection_reasons))

    # ----------------------------------------------------
    # 4. DEDUPLICATE
    # ----------------------------------------------------
    logger.info("--- Phase 4: Deduplicating Records ---")
    unique_records, duplicate_records = deduplicate_records(valid_records)
    logger.info(
        "Deduplication complete: %d unique records, %d duplicates removed.",
        len(unique_records),
        len(duplicate_records),
    )

    # ----------------------------------------------------
    # 5. CONSOLIDATE & EXPORT
    # ----------------------------------------------------
    csv_file_path = out_dir / "final_dataset.csv"
    logger.info("Writing consolidated dataset to: %s", csv_file_path)

    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_FIELDNAMES,
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for rec in unique_records:
            # Map None values to empty strings for standard CSV output
            row = {k: ("" if rec.get(k) is None else rec.get(k)) for k in CSV_FIELDNAMES}
            writer.writerow(row)

    end_dt = datetime.now(timezone.utc)
    end_time_iso = end_dt.isoformat()
    duration = round(time.time() - t0, 2)

    # Calculate per-source breakdowns in final unique dataset
    source_final_counts: Dict[str, int] = {}
    for rec in unique_records:
        src = rec.get("source", "unknown")
        source_final_counts[src] = source_final_counts.get(src, 0) + 1

    for src in source_metrics:
        source_metrics[src]["final_records"] = source_final_counts.get(src, 0)

    summary_report: Dict[str, Any] = {
        "pipeline_run": {
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "duration_seconds": duration,
            "sources_configured": sources,
            "politeness_delay_seconds": delay,
        },
        "source_statistics": source_metrics,
        "metrics_summary": {
            "total_raw_records": len(raw_records),
            "total_cleaned_records": len(cleaned_records),
            "total_valid_records": len(valid_records),
            "total_rejected_records": len(rejected_records),
            "rejected_by_reason": rejection_reasons,
            "duplicate_records_removed": len(duplicate_records),
            "final_clean_unique_records": len(unique_records),
        },
        "outputs": {
            "csv_path": str(csv_file_path),
            "log_path": str(log_path),
        },
    }

    report_file_path = out_dir / "summary_report.json"
    with open(report_file_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)

    logger.info("Saved summary report to: %s", report_file_path)
    logger.info("==================================================")
    logger.info("Pipeline completed successfully in %.2f seconds!", duration)
    logger.info("Final Clean Unique Records Saved: %d", len(unique_records))
    logger.info("==================================================")

    return summary_report


def main() -> None:
    """CLI parser and entrypoint."""
    parser = argparse.ArgumentParser(
        description="Production-quality Web Scraping and ETL Data Pipeline."
    )
    parser.add_argument(
        "--source",
        choices=["all", "books", "quotes"],
        default="all",
        help="Data source(s) to scrape (default: 'all')",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Politeness delay between HTTP requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save final dataset and report (default: output/)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path for log output (default: logs/scraper.log)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose DEBUG level logging",
    )

    args = parser.parse_args()

    sources = ["books", "quotes"] if args.source == "all" else [args.source]
    output_dir = Path(args.output_dir) if args.output_dir else None
    log_file = Path(args.log_file) if args.log_file else None

    run_pipeline(
        sources=sources,
        delay=args.delay,
        timeout=args.timeout,
        output_dir=output_dir,
        log_file=log_file,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
