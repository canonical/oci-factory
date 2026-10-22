from glob import glob
from pathlib import Path

import pydantic
import pytest

import src.image.prepare_single_image_build_matrix as prep_matrix
from src.image.utils.schema.triggers import ImageTriggerValidationError


PRO_SERVICES = [
    "esm-apps",
    "esm-infra",
    "fips-updates",
    "fips",
    "fips-preview",
    "ros",
    "ros-updates",
]


def _upload(pro=None):
    upload = {
        "source": "canonical/rocks-toolbox",
        "commit": "abcdef1234567890",
        "directory": "mock_rock/1.2",
    }
    if pro is not None:
        upload["pro"] = pro
    return upload


def test_existing_image_trigger_files():
    for oci_path in glob("oci/*"):
        prep_matrix.load_trigger_yaml(Path(oci_path))


def test_image_trigger_validator_missing_channel_risks():
    image_trigger = {
        "version": 1,
        "release": {
            "latest": {
                "end-of-life": "2030-05-01T00:00:00Z",
            },
        },
        "upload": [],
    }
    with pytest.raises(ImageTriggerValidationError):
        prep_matrix.validate_image_trigger(image_trigger)


def test_image_trigger_validator_missing_release_risks():
    image_trigger = {
        "version": 1,
        "release": {
            "latest": {
                "end-of-life": "2030-05-01T00:00:00Z",
                "candidate": "1.0-22.04_candidate",
            },
        },
        "upload": [
            {
                "source": "canonical/rocks-toolbox",
                "commit": "17916dd5de270e61a6a3fd3f4661a6413a50fd6f",
                "directory": "mock_rock/1.2",
                "release": {
                    "1.2-22.04": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "risks": [],
                    }
                },
            },
        ],
    }
    with pytest.raises(ImageTriggerValidationError):
        prep_matrix.validate_image_trigger(image_trigger)


def test_image_trigger_validator_minimal_input():
    image_trigger = {
        "version": 1,
        "release": {
            "latest": {
                "end-of-life": "2030-05-01T00:00:00Z",
                "candidate": "1.0-22.04_candidate",
            },
        },
        "upload": [
            {
                "source": "canonical/rocks-toolbox",
                "commit": "17916dd5de270e61a6a3fd3f4661a6413a50fd6f",
                "directory": "mock_rock/1.2",
                "release": {
                    "1.2-22.04": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "risks": ["beta"],
                    }
                },
            },
        ],
    }

    prep_matrix.validate_image_trigger(image_trigger)


def test_ignored_vulnerabilities_must_have_v2_schema():
    image_trigger = {
        "version": 1,
        "upload": [
            {
                "source": "canonical/rocks-toolbox",
                "commit": "abcdef1234567890",
                "directory": "mock_rock/1.2",
                "ignored-vulnerabilities": ["CVE-2023-1234"],
            },
        ],
    }

    with pytest.raises(
        ImageTriggerValidationError,
        match='ignored-vulnerabilities" field is not supported in',
    ):
        prep_matrix.validate_image_trigger(image_trigger)


def test_ignored_vulnerabilities_with_v2_schema():
    image_trigger = {
        "version": 2,
        "upload": [
            {
                "source": "canonical/rocks-toolbox",
                "commit": "abcdef1234567890",
                "directory": "mock_rock/1.2",
                "ignored-vulnerabilities": ["CVE-2023-1234", "CVE-2024-5678"],
            },
        ],
    }

    prep_matrix.validate_image_trigger(image_trigger)


@pytest.mark.parametrize("service", PRO_SERVICES)
def test_pro_service_is_supported(service):
    prep_matrix.validate_image_trigger(
        {"version": 2, "upload": [_upload({"services": [service]})]}
    )


@pytest.mark.parametrize(
    "pro",
    [
        {},
        {"services": []},
        {"services": ["esm-apps", "esm-apps"]},
        {"services": ["unknown-service"]},
        {"services": ["esm-apps"], "config": {"token": "not-supported"}},
    ],
)
def test_invalid_pro_configuration_is_rejected(pro):
    with pytest.raises(pydantic.ValidationError):
        prep_matrix.validate_image_trigger(
            {"version": 2, "upload": [_upload(pro)]}
        )


def test_public_and_pro_uploads_can_share_source():
    prep_matrix.validate_image_trigger(
        {
            "version": 2,
            "upload": [_upload(), _upload({"services": ["esm-infra"]})],
        }
    )


def test_pro_upload_identity_ignores_service_order():
    with pytest.raises(ImageTriggerValidationError, match="is not unique"):
        prep_matrix.validate_image_trigger(
            {
                "version": 2,
                "upload": [
                    _upload({"services": ["esm-apps", "esm-infra"]}),
                    _upload({"services": ["esm-infra", "esm-apps"]}),
                ],
            }
        )


def test_valid_pro_release_state():
    prep_matrix.validate_image_trigger(
        {
            "version": 2,
            "pro-release": {
                "1.2-22.04": {
                    "end-of-life": "2030-05-01T00:00:00Z",
                    "services": ["esm-apps", "esm-infra"],
                    "beta": "42",
                }
            },
        }
    )
