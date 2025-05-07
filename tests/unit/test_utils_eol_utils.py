from datetime import datetime, timezone

import pytest

from src.image.utils.eol_utils import (
    generate_base_eol_exceed_warning,
    get_base_eol,
    track_eol_exceeds_base_eol,
)


def test_calculate_base_eol():
    # Test for LTS base image
    base = "24.04"
    expected_eol = datetime(year=2029, month=5, day=31, tzinfo=timezone.utc)
    assert get_base_eol(base) == expected_eol

    # Test for non-LTS base image
    base = "24.10"
    expected_eol = datetime(year=2025, month=7, day=10, tzinfo=timezone.utc)
    assert get_base_eol(base) == expected_eol


def test_generate_base_eol_exceed_warning():
    tracks_eol_exceed_base_eol = [
        {
            "track": "1.0-22.04",
            "base": "22.04",
            "track_eol": "2024-05-01",
            "base_eol": "2027-04-01",
        },
        {
            "track": "1.0-22.10",
            "base": "22.10",
            "track_eol": "2024-05-01",
            "base_eol": "2027-04-01",
        },
    ]
    title, text = generate_base_eol_exceed_warning(tracks_eol_exceed_base_eol)
    assert title == ("Found tracks with EOL date exceeding base image's EOL date\n")
    assert text == (
        "Following tracks have an EOL date that exceeds the base image's EOL date:\n"
        "| Track | Base | Track EOL Date | Base EOL Date |\n"
        "|-------|------|----------------|---------------|\n"
        "| 1.0-22.04 | 22.04 | 2024-05-01 | 2027-04-01 |\n"
        "| 1.0-22.10 | 22.10 | 2024-05-01 | 2027-04-01 |\n"
        "\nPlease check the EOL date of the base image and the track.\n"
    )


def test_track_eol_exceeds_base_eol():
    track = "1.0-22.04"
    track_eol = "2028-05-01T00:00:00Z"
    base_eol = "2027-06-01"
    result = track_eol_exceeds_base_eol(track, track_eol)
    assert result == {
        "track": track,
        "base": "ubuntu:22.04",
        "track_eol": track_eol[:10],
        "base_eol": base_eol,
    }


def test_track_eol_no_exceeds_base_eol_no_exceed():
    track = "1.0-22.04"
    track_eol = "2026-06-01T00:00:00Z"
    result = track_eol_exceeds_base_eol(track, track_eol)
    assert result is None
