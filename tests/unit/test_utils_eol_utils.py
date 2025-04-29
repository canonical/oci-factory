from datetime import datetime, timezone

import pytest

from src.image.utils.eol_utils import (
    calculate_base_eol,
    generate_base_eol_exceed_warning,
    track_eol_exceeds_base_eol,
)


def test_calculate_base_eol():
    # Test for LTS base image
    base_year = 2022
    base_month = 4
    expected_eol = datetime(year=2027, month=4, day=1, tzinfo=timezone.utc)
    assert calculate_base_eol(base_year, base_month) == expected_eol

    # Test for non-LTS base image
    base_year = 2023
    base_month = 5
    expected_eol = datetime(year=2024, month=2, day=1, tzinfo=timezone.utc)
    assert calculate_base_eol(base_year, base_month) == expected_eol

    base_year = 24
    base_month = 4
    expected_eol = datetime(year=2029, month=4, day=1, tzinfo=timezone.utc)
    assert calculate_base_eol(base_year, base_month) == expected_eol


def test_generate_base_eol_exceed_warning():
    tracks_eol_exceed_base_eol = [
        {
            "track": "1.0-22.04",
            "base": "22.04",
            "eol_date": "2024-05-01T00:00:00Z",
            "base_eol": "2027-04-01T00:00:00Z",
        },
        {
            "track": "1.0-22.10",
            "base": "22.10",
            "eol_date": "2024-05-01T00:00:00Z",
            "base_eol": "2027-04-01T00:00:00Z",
        },
    ]
    title, text = generate_base_eol_exceed_warning(tracks_eol_exceed_base_eol)
    assert title == ("Found tracks with EOL date exceeding base image's EOL date\n")
    assert text == (
        "Following tracks have an EOL date that exceeds the base image's EOL date:\n"
        "| Track | Base | EOL Date | Base Image EOL Date |\n"
        "|-------|------|----------|---------------------|\n"
        "| 1.0-22.04 | 22.04 | 2024-05-01T00:00:00Z | 2027-04-01T00:00:00Z |\n"
        "| 1.0-22.10 | 22.10 | 2024-05-01T00:00:00Z | 2027-04-01T00:00:00Z |\n"
        "\nPlease check the EOL date of the base image and the track.\n"
    )


def test_track_eol_exceeds_base_eol():
    track = "1.0-22.04"
    track_eol = "2028-05-01T00:00:00Z"
    base_eol = "2027-04-01T00:00:00Z"
    result = track_eol_exceeds_base_eol(track, track_eol)
    assert result == {
        "track": track,
        "base": "ubuntu:22.04",
        "eol_date": datetime.fromisoformat(track_eol),
        "base_eol": datetime.fromisoformat(base_eol),
    }


def test_track_eol_no_exceeds_base_eol_no_exceed():
    track = "1.0-22.04"
    track_eol = "2026-05-01T00:00:00Z"
    result = track_eol_exceeds_base_eol(track, track_eol)
    assert result is None
