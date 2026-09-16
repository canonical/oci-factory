#!/usr/bin/env python3

"""Classify CVE IDs using the CISA Known Exploited Vulnerabilities catalog."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

CVE_PATTERN = re.compile(r"CVE-[0-9]{4}-[0-9]{4,19}")
DOWNLOAD_ATTEMPTS = 4
DEFAULT_KEV_CATALOG_SOURCE = (
    "https://raw.githubusercontent.com/cisagov/kev-data/refs/heads/develop/"
    "known_exploited_vulnerabilities.json"
)


class CheckKevError(Exception):
    """An expected input, catalog, or output failure."""


def parse_cve_ids(value: str) -> list[str]:
    try:
        cve_ids = json.loads(value)
    except json.JSONDecodeError as error:
        raise CheckKevError("Invalid CVE ID list: expected a JSON array") from error

    if not isinstance(cve_ids, list):
        raise CheckKevError("Invalid CVE ID list: expected a JSON array")

    normalized_ids: set[str] = set()
    for entry in cve_ids:
        if not isinstance(entry, str) or CVE_PATTERN.fullmatch(entry.upper()) is None:
            print(
                f"::warning::Ignoring non-conforming CVE entry: {entry!r}",
                file=sys.stderr,
            )
            continue
        normalized_ids.add(entry.upper())

    return sorted(normalized_ids)


def download_catalog(source: str) -> Any:
    last_error: BaseException | None = None

    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with urllib.request.urlopen(source, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < DOWNLOAD_ATTEMPTS:
                time.sleep(1)

    raise CheckKevError(
        f"Failed to download CISA KEV catalog: {source}"
    ) from last_error


def load_catalog(source: str) -> dict[str, Any]:
    if source.startswith("https://"):
        catalog = download_catalog(source)
    else:
        path = Path(source)
        if not path.is_file():
            raise CheckKevError(f"KEV catalog not found: {source}")
        try:
            catalog = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CheckKevError(f"Invalid CISA KEV catalog: {source}") from error

    if not isinstance(catalog, dict):
        raise CheckKevError(f"Invalid CISA KEV catalog: {source}")

    catalog_version = catalog.get("catalogVersion")
    release_date = catalog.get("dateReleased")
    count = catalog.get("count")
    vulnerabilities = catalog.get("vulnerabilities")

    # CISA publishes a schema, but these consumer-specific checks are still
    # necessary: valid JSON with an incomplete vulnerability list could
    # otherwise make every requested CVE appear not to be in KEV. Error out
    # before classification instead of silently producing false negatives.
    valid_entries = isinstance(vulnerabilities, list) and all(
        isinstance(entry, dict)
        and isinstance(entry.get("cveID"), str)
        and CVE_PATTERN.fullmatch(entry["cveID"]) is not None
        for entry in vulnerabilities
    )
    if not (
        isinstance(catalog_version, str)
        and catalog_version
        and isinstance(release_date, str)
        and release_date
        and isinstance(count, int)
        and not isinstance(count, bool)
        and isinstance(vulnerabilities, list)
        and count == len(vulnerabilities)
        and valid_entries
    ):
        raise CheckKevError(f"Invalid CISA KEV catalog: {source}")

    return catalog


def append_outputs(
    classifications: dict[str, bool], catalog: dict[str, Any], source: str
) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")

    values = {
        "kev-results": json.dumps(classifications, separators=(",", ":")),
        "catalog-source": source,
        "catalog-version": catalog["catalogVersion"],
        "catalog-release-date": catalog["dateReleased"],
    }
    try:
        with open(output_path, "a", encoding="utf-8") as output:
            output.writelines(f"{name}={value}\n" for name, value in values.items())
    except OSError as error:
        raise CheckKevError(
            f"Unable to write GitHub action outputs: {output_path}"
        ) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cve-ids",
        required=True,
        help="JSON array of CVE IDs to classify",
    )
    parser.add_argument(
        "--catalog-source",
        default=DEFAULT_KEV_CATALOG_SOURCE,
        help="CISA KEV catalog URL or local file",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        cve_ids = parse_cve_ids(args.cve_ids)
        catalog_source = args.catalog_source
        catalog = load_catalog(catalog_source)
        known_exploited = {entry["cveID"] for entry in catalog["vulnerabilities"]}
        classifications = {cve_id: (cve_id in known_exploited) for cve_id in cve_ids}
        append_outputs(classifications, catalog, catalog_source)
    except CheckKevError as error:
        print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
