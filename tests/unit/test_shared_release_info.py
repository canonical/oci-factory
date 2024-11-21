import pytest

from src.shared.release_info import *


def test_get_revision_to_release_plain():
    all_releases = {
        "3.8-20.04": {
            "end-of-life": "2025-03-31T00:00:00Z",
            "edge": {"target": "43"},
            "stable": {"target": "43"},
            "candidate": {"target": "43"},
            "beta": {"target": "43"},
        }
    }
    assert get_revision_to_released_tags(all_releases) == {
        43: [
            "3.8-20.04_beta",
            "3.8-20.04_candidate",
            "3.8-20.04_edge",
            "3.8-20.04_stable",
        ]
    }


def test_get_revision_to_release_circular():
    all_releases = {
        "1.19.0-22.04": {
            "end-of-life": "2024-11-26T00:00:00Z",
            "stable": {"target": "1"},
            "candidate": {"target": "1.19.0-22.04_beta"},
            "beta": {"target": "1.19.0-22.04_candidate"},
            "edge": {"target": "5"},
        }
    }

    with pytest.raises(BadChannel) as excinfo:
        get_revision_to_released_tags(all_releases)
    assert (
        "Tag 1.19.0-22.04_candidate was caught in a circular dependency, following tags that follow themselves. Cannot pin a revision."
        in str(excinfo)
    )


def test_get_revision_to_release_alias():
    all_releases = {
        "1.19.0-22.04": {
            "end-of-life": "2024-11-26T00:00:00Z",
            "stable": {"target": "1"},
            "candidate": {"target": "5"},
            "beta": {"target": "1.19.0-22.04_candidate"},
            "edge": {"target": "5"},
        },
        "1-22.04": {
            "end-of-life": "2025-05-12T00:00:00Z",
            "stable": {"target": "4"},
            "candidate": {"target": "1-22.04_stable"},
            "beta": {"target": "1-22.04_candidate"},
            "edge": {"target": "1-22.04_beta"},
        },
    }

    assert get_revision_to_released_tags(all_releases) == {
        1: ["1.19.0-22.04_stable"],
        4: ["1-22.04_beta", "1-22.04_candidate", "1-22.04_edge", "1-22.04_stable"],
        5: ["1.19.0-22.04_beta", "1.19.0-22.04_candidate", "1.19.0-22.04_edge"],
    }
