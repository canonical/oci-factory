import pytest

import src.shared.release_info as shared
from src.image.release import (
    get_release_source,
    group_release_tags_by_revision_and_destination,
    remove_eol_tags,
    release_entry,
    validate_unique_destination_tags,
)

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


def test_remove_eol_tags_dangling_tag(release_json):
    """Ensure dangling tag raises BadChannel exception."""

    dangling_track = {
        "1.0.0-22.04_beta": "",  # the track for this tag does not exist
    }

    dangling_risk = {
        "1.0-22.04_gamma": "",  # the risk for this tag does not exist
    }

    with pytest.raises(shared.BadChannel):
        remove_eol_tags(dangling_track, release_json)

    with pytest.raises(shared.BadChannel):
        remove_eol_tags(dangling_risk, release_json)


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


def test_group_release_tags_by_revision_and_destination():
    release_tags = {
        "stable": release_entry(1, "public", tag="stable"),
        "latest": release_entry(1, "public", tag="latest"),
        "pro:esm-apps:1.0-24.04_stable": release_entry(
            2, "pro-acr", tag="1.0-24.04_stable"
        ),
        "pro:esm-apps:1.0-24.04_stable:alias:1.0-24.04": release_entry(
            2, "pro-acr", tag="1.0-24.04"
        ),
    }

    result = group_release_tags_by_revision_and_destination(release_tags, {})

    assert result[1]["public"] == ["latest", "stable"]
    assert sorted(result[2]["pro-acr"]) == ["1.0-24.04", "1.0-24.04_stable"]


def test_validate_unique_destination_tags_rejects_collision():
    release_tags = {
        "pro:esm-apps:1.0-24.04_stable": release_entry(
            1, "pro-acr", tag="1.0-24.04_stable"
        ),
        "pro:esm-infra:1.0-24.04_stable": release_entry(
            2, "pro-acr", tag="1.0-24.04_stable"
        ),
    }

    with pytest.raises(shared.BadChannel):
        validate_unique_destination_tags(release_tags)


def test_get_release_source_for_public_uses_ghcr():
    assert get_release_source(
        "public", "1.0-24.04", 1, "mock-rock", "canonical/oci-factory", ""
    ) == "docker://ghcr.io/canonical/oci-factory/mock-rock:1.0-24.04_1"


def test_get_release_source_for_pro_uses_local_archive(tmp_path):
    source = tmp_path / "mock-rock_1.0-24.04_1"
    source.touch()

    assert get_release_source(
        "pro-acr", "1.0-24.04", 1, "mock-rock", "canonical/oci-factory", tmp_path
    ) == f"oci-archive:{source}"


def test_get_release_source_for_pro_requires_local_archive(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_release_source(
            "pro-acr", "1.0-24.04", 1, "mock-rock", "canonical/oci-factory", tmp_path
        )
