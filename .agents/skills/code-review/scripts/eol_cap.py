#!/usr/bin/env python3
"""Check trigger end-of-life dates against the OCI Factory three-month EOL cap.

Usage:
    eol_cap.py [--review-date YYYY-MM-DD] END_OF_LIFE [END_OF_LIFE ...]

END_OF_LIFE accepts the trigger format (``2027-01-16T00:00:00Z``) or a plain
date. The cutoff is the review date plus three calendar months, clamped to the
last day of the target month (e.g. 2026-11-30 -> 2027-02-28). An end-of-life on
or before the cutoff is within the cap. Only the date part is compared.
Standard library only, so it runs wherever the review agent can run Python.
"""

import argparse
import calendar
from datetime import date, datetime, timezone

CAP_MONTHS = 3


def parse_date(value: str) -> date:
    """Parse ``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SSZ`` into a date."""
    value = value.strip().strip("'\"")
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"invalid date {value!r}: use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")


def add_months(start: date, months: int) -> date:
    """Add calendar months, clamping the day to the target month's length."""
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def cutoff(review_date: date) -> date:
    """Latest end-of-life allowed without an accepted support plan."""
    return add_months(review_date, CAP_MONTHS)


def check(review_date: date, end_of_life: date) -> str:
    """One line stating the cutoff and whether the date is within the cap."""
    limit = cutoff(review_date)
    status = "within cap" if end_of_life <= limit else "EXCEEDS cap"
    return f"review {review_date} cutoff {limit} end-of-life {end_of_life}: {status}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--review-date", type=parse_date,
                        default=datetime.now(timezone.utc).date(),
                        help="review date (default: today, UTC)")
    parser.add_argument("end_of_life", nargs="+", type=parse_date)
    args = parser.parse_args(argv)
    for end_of_life in args.end_of_life:
        print(check(args.review_date, end_of_life))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
