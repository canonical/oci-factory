import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ACTION_DIR = Path(__file__).resolve().parents[2] / ".github/actions/check-kev"
CATALOG = ACTION_DIR / "testdata/catalog.json"


def classify(cve_ids: str, catalog: Path = CATALOG) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(ACTION_DIR / "check_kev.py")]
    return subprocess.run(
        command + ["--cve-ids", cve_ids, "--catalog-source", str(catalog)],
        env={**os.environ, "GITHUB_OUTPUT": "/dev/stdout"},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "entries,expected,ignored",
    [
        (
            ["CVE-2024-1000", "CVE-2024-2000"],
            {"CVE-2024-1000": False, "CVE-2024-2000": True},
            [],
        ),
        (["cve-2024-2002", "CVE-2024-2002"], {"CVE-2024-2002": True}, []),
        ([], {}, []),
        (
            ["GHSA-not-a-cve", 42, "CVE-2024-2000"],
            {"CVE-2024-2000": True},
            ["GHSA-not-a-cve", 42],
        ),
    ],
)
def test_classifies_cve_ids(entries, expected, ignored) -> None:
    result = classify(json.dumps(entries))
    assert result.returncode == 0, result.stderr
    outputs = dict(line.split("=", 1) for line in result.stdout.splitlines())
    assert json.loads(outputs["kev-results"]) == expected
    assert result.stderr.splitlines() == [
        f"::warning::Ignoring non-conforming CVE entry: {entry!r}" for entry in ignored
    ]


def test_catalog_metadata() -> None:
    result = classify("[]")
    assert result.returncode == 0, result.stderr
    assert dict(line.split("=", 1) for line in result.stdout.splitlines()) == {
        "kev-results": "{}",
        "catalog-source": str(CATALOG),
        "catalog-version": "2026.09.14",
        "catalog-release-date": "2026-09-14T00:00:00Z",
    }


@pytest.mark.parametrize(
    "kind,cve_ids,error",
    [
        ("missing", "[]", "KEV catalog not found"),
        ("malformed", "[]", "Invalid CISA KEV catalog"),
        ("count-mismatch", "[]", "Invalid CISA KEV catalog"),
        ("valid", "{", "Invalid CVE ID list"),
        ("valid", "{}", "Invalid CVE ID list"),
    ],
)
def test_fails_closed(tmp_path: Path, kind: str, cve_ids: str, error: str) -> None:
    catalog = tmp_path / "catalog.json"
    if kind == "valid":
        catalog = CATALOG
    elif kind == "malformed":
        catalog.write_text("{")
    elif kind == "count-mismatch":
        catalog.write_text(
            json.dumps({**json.loads(CATALOG.read_text()), "count": 999})
        )
    result = classify(cve_ids, catalog)
    assert result.returncode != 0
    assert error in result.stderr
    assert result.stdout == ""
