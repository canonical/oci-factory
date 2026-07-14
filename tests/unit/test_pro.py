import pytest

from src.image.pro import (
    get_pro_artifact_passphrase_secret,
    get_pro_revision_refs,
    get_published_track,
    get_track_from_tag,
    has_pro_tracks,
    has_public_tracks,
)


def test_get_track_from_tag_without_naming_assumptions():
    assert get_track_from_tag("stable") == "latest"
    assert get_track_from_tag("1.0-24.04_stable") == "1.0-24.04"
    assert get_track_from_tag("1.0-24.04") == "1.0-24.04"


def test_has_public_tracks():
    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }

    assert not has_public_tracks({"release": {"1.0-24.04": {"pro-variants": [{"pro": pro_config, "services": ["esm-apps"], "stable": "1"}]}}})
    assert not has_public_tracks(
        {"upload": [{"release": {"1.0-24.04": {"pro": pro_config}}}]}
    )
    assert not has_public_tracks(
        {"upload": [{"pro": pro_config, "release": {"1.0-24.04": {}}}]}
    )
    assert has_public_tracks(
        {"release": {"1.0-24.04": {"pro-variants": []}, "latest": {"stable": "1"}}}
    )


def test_pro_helpers():
    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }
    image_trigger = {"release": {"1.0-24.04": {"pro-variants": [{"pro": pro_config, "services": ["esm-apps"], "stable": "1"}]}}}

    assert has_pro_tracks(image_trigger)
    assert get_pro_artifact_passphrase_secret(image_trigger) == "PRO_ARTIFACT_PASSPHRASE"

    upload_trigger = {"upload": [{"pro": pro_config, "release": {"1.0-24.04": {}}}]}
    assert has_pro_tracks(upload_trigger)
    assert get_pro_artifact_passphrase_secret(upload_trigger) == "PRO_ARTIFACT_PASSPHRASE"


def test_pro_artifact_passphrase_secret_must_be_unique():
    image_trigger = {
        "release": {
            "1.0-24.04": {
                "pro-variants": [{
                    "services": ["esm-apps"],
                    "stable": "1",
                    "pro": {
                        "services": ["esm-apps"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                }]
            },
            "2.0-24.04": {
                "pro-variants": [{
                    "services": ["esm-apps"],
                    "stable": "2",
                    "pro": {
                        "services": ["esm-apps"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.OTHER_PASSPHRASE",
                        },
                    },
                }]
            },
        }
    }

    with pytest.raises(ValueError):
        get_pro_artifact_passphrase_secret(image_trigger)


def test_get_pro_revision_refs():
    image_trigger = {
        "release": {
            "1.0-24.04": {
                "pro-variants": [{
                    "services": ["esm-apps"],
                    "stable": "1",
                    "pro": {
                        "services": ["esm-apps"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                }]
            },
            "latest": {},
        }
    }

    assert get_pro_revision_refs(
        image_trigger, ["1.0-24.04_1", "latest_2"]
    ) == ["1.0-24.04_1"]


def test_get_published_track():
    assert get_published_track("1.2-24.04") == "1.2-24.04"
    assert get_published_track(
        "1.2-24.04", {"services": ["esm-apps", "esm-infra"]}
    ) == "1.2-24.04"
    assert get_published_track(
        "1.2-24.04", {"services": ["fips", "esm-infra"]}
    ) == "1.2-fips-24.04"
    assert get_published_track(
        "1.2-24.04", {"services": ["fips-updates", "fips"]}
    ) == "1.2-fips-fips-updates-24.04"
