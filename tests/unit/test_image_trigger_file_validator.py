from pathlib import Path
import pytest

import src.image.prepare_single_image_build_matrix as prep_matrix
from src.image.utils.schema.triggers import ImageTriggerValidationError
from glob import glob
from pathlib import Path


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
