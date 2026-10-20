import importlib.util
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".agents/skills/code-review/scripts/eol_cap.py"
spec = importlib.util.spec_from_file_location("eol_cap", SCRIPT)
eol_cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eol_cap)


@pytest.mark.parametrize(
    "review, expected",
    [
        ("2026-10-16", date(2027, 1, 16)),
        ("2026-11-30", date(2027, 2, 28)),  # clamped to month end
        ("2027-11-30", date(2028, 2, 29)),  # leap year
        ("2026-12-31", date(2027, 3, 31)),
        ("2026-01-31", date(2026, 4, 30)),
    ],
)
def test_cutoff(review, expected):
    assert eol_cap.cutoff(eol_cap.parse_date(review)) == expected


@pytest.mark.parametrize(
    "end_of_life, status",
    [
        ("2027-01-16", "within cap"),  # on the cutoff passes
        ("2027-01-16T00:00:00Z", "within cap"),  # trigger format
        ("'2026-12-01T00:00:00Z'", "within cap"),  # quoted YAML value
        ("2027-01-17", "EXCEEDS cap"),
        ("2027-04-16T00:00:00Z", "EXCEEDS cap"),
    ],
)
def test_check(end_of_life, status):
    line = eol_cap.check(date(2026, 10, 16), eol_cap.parse_date(end_of_life))
    assert line.startswith("review 2026-10-16 cutoff 2027-01-16 end-of-life ")
    assert line.endswith(status)


def test_main_prints_one_line_per_date(capsys):
    assert eol_cap.main(["--review-date", "2026-10-16", "2026-12-01", "2027-04-16T00:00:00Z"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "review 2026-10-16 cutoff 2027-01-16 end-of-life 2026-12-01: within cap",
        "review 2026-10-16 cutoff 2027-01-16 end-of-life 2027-04-16: EXCEEDS cap",
    ]


def test_invalid_date_is_rejected():
    with pytest.raises(SystemExit) as error:
        eol_cap.main(["--review-date", "2026-10-16", "16/10/2026"])
    assert error.value.code == 2
