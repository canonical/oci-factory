import pytest

import src.shared.release_info as shared
from src.image.release import remove_eol_tags

from ..fixtures.sample_data import circular_release_json, release_json


def test_remove_eol_tags_no_change(release_json):
    """Ensure format of non-EOL tags are preserved"""

    revision_to_tag = {
        "latest_candidate": "1033",
        "1.1-22.04_beta": "1032",
    }

    result = remove_eol_tags(revision_to_tag, release_json)

    assert revision_to_tag == result, "No change should have occured"


def test_remove_eol_tags_malformed_tag(release_json):
    """Ensure malformed tag raises BadChannel exception."""

    revision_to_tag = {
        "malformed-tag": "1033",
    }

    with pytest.raises(shared.BadChannel):
        remove_eol_tags(revision_to_tag, release_json)


def test_remove_eol_tags(release_json):
    """Ensure EOL tags are removed."""

    revision_to_tag = {
        "latest_candidate": "1033",
        "1.1-22.04_beta": "1032",
        "eol-release_beta": "1032",
        "eol-upload_beta": "878",
        "eol-all_beta": "878",
    }

    excepted_result = {
        "latest_candidate": "1033",
        "1.1-22.04_beta": "1032",
    }

    result = remove_eol_tags(revision_to_tag, release_json)

    assert excepted_result == result, "All EOL tags should have been removed"


def test_remove_eol_tags_circular_release(circular_release_json):
    """Ensure circular releases are handled."""

    revision_to_tag = {
        "circular_edge": "1033",
    }

    with pytest.raises(shared.BadChannel):
        remove_eol_tags(revision_to_tag, circular_release_json)
