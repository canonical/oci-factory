from glob import glob
from pathlib import Path

import pytest
import yaml

import src.image.prepare_single_image_build_matrix as prep_matrix
from src.image.utils.schema.triggers import ImageTriggerValidationError


def test_is_track_eol():
    eol_track = {
        "end-of-life": "2024-05-01T00:00:00Z",
        "risks": ["candidate", "edge", "beta"],
    }
    assert True == prep_matrix.is_track_eol(eol_track)

    valid_track = {
        "end-of-life": "2124-05-01T00:00:00Z",
        "risks": ["candidate", "edge", "beta"],
    }
    assert False == prep_matrix.is_track_eol(valid_track)


def test_filter_eol_tracks():
    build = {
        "release": {
            "1.0.0-22.04": {
                "end-of-life": "2024-05-01T00:00:00Z",
                "risks": ["candidate", "edge", "beta"],
            },
            "1.0-22.04": {
                "end-of-life": "2124-05-01T00:00:00Z",
                "risks": ["candidate", "edge", "beta"],
            },
        },
        "name": "mock",
    }
    filtered_build = prep_matrix.filter_eol_tracks(build)

    assert len(filtered_build["release"]) == 1


def test_find_eol_exceed_base_eol():
    build = [
        {
            "release": {
                "1.0.0-22.04": {
                    "end-of-life": "2024-05-01T00:00:00Z",
                },
                "1.0-22.04": {
                    "end-of-life": "2124-05-01T00:00:00Z",
                },
            },
        }
    ]
    eol_exceed = prep_matrix.find_eol_exceed_base_eol(build)
    assert len(eol_exceed) == 1
    assert eol_exceed[0]["track"] == "1.0-22.04"
    assert eol_exceed[0]["base"] == "ubuntu:22.04"


def test_filter_eol_builds():
    builds = [
        {
            "release": {
                "1.0.0-22.04": {
                    "end-of-life": "2024-05-01T00:00:00Z",
                    "risks": ["candidate", "edge", "beta"],
                },
            },
            "name": "mock",
        },
        {
            "release": {
                "1.0.0-22.04": {
                    "end-of-life": "2024-05-01T00:00:00Z",
                    "risks": ["candidate", "edge", "beta"],
                },
                "1.0-22.04": {
                    "end-of-life": "2124-05-01T00:00:00Z",
                    "risks": ["candidate", "edge", "beta"],
                },
            },
            "name": "mock",
        },
        {
            "release": {
                "1.0-22.04": {
                    "end-of-life": "2124-05-01T00:00:00Z",
                    "risks": ["candidate", "edge", "beta"],
                },
            },
            "name": "mock",
        },
    ]
    filtered_builds = prep_matrix.filter_eol_builds(builds)

    assert len(filtered_builds) == 2


def test_locate_trigger_yaml(tmpdir):
    tmpdir_path = Path(tmpdir)
    image_yaml_path = tmpdir_path / "image.yaml"
    image_yml_path = tmpdir_path / "image.yml"

    # test exception when no config is present
    with pytest.raises(FileNotFoundError):
        prep_matrix.locate_trigger_yaml(tmpdir_path)

    # test selection when yaml config is present
    image_yaml_path.touch()
    found_path = prep_matrix.locate_trigger_yaml(tmpdir_path)
    assert found_path == image_yaml_path

    # test exception when both yaml and yml configs are present
    image_yml_path.touch()
    with pytest.raises(prep_matrix.AmbiguousConfigFileError):
        prep_matrix.locate_trigger_yaml(tmpdir_path)

    # test selection when yml config is present
    image_yaml_path.unlink()
    found_path = prep_matrix.locate_trigger_yaml(tmpdir_path)
    assert found_path == image_yml_path


def test_flatten_pro_builds():
    builds = [
        {
            "name": "mock",
            "release": {
                "1.0-24.04": {
                    "end-of-life": "2030-05-01T00:00:00Z",
                    "risks": ["stable"],
                    "pro": {
                        "services": ["esm-apps", "esm-infra"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                }
            },
        },
        {"name": "public"},
    ]

    prep_matrix.flatten_pro_builds(builds)

    assert builds[0]["pro-services"] == "esm-apps,esm-infra"
    assert builds[0]["pro-token"] == "UBUNTU_PRO_TOKEN"
    assert builds[0]["pro-artifact-passphrase"] == "PRO_ARTIFACT_PASSPHRASE"
    assert builds[0]["pro"] == builds[0]["release"]["1.0-24.04"]["pro"]
    assert builds[1]["pro-services"] == ""


def test_flatten_pro_builds_uses_upload_pro():
    pro_config = {
        "services": ["esm-apps", "esm-infra"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }
    builds = [{"name": "mock", "pro": pro_config}]

    prep_matrix.flatten_pro_builds(builds)

    assert builds[0]["pro-services"] == "esm-apps,esm-infra"
    assert builds[0]["pro-token"] == "UBUNTU_PRO_TOKEN"
    assert builds[0]["pro-artifact-passphrase"] == "PRO_ARTIFACT_PASSPHRASE"


def test_dir_identifier_includes_sorted_pro_services():
    build = {
        "directory": "mock_rock/1.2",
        "pro": {
            "services": ["esm-infra", "esm-apps"],
            "config": {
                "token": "secrets.UBUNTU_PRO_TOKEN",
                "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
            },
        },
    }

    assert prep_matrix.get_dir_identifier(build) == "mock_rock_1.2_esm-apps_esm-infra"


def test_flatten_pro_builds_rejects_multiple_configs():
    builds = [
        {
            "name": "mock",
            "release": {
                "1.0-24.04": {
                    "pro": {
                        "services": ["esm-apps"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                },
                "1.1-24.04": {
                    "pro": {
                        "services": ["esm-infra"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                },
            },
        }
    ]

    with pytest.raises(prep_matrix.InvalidSchemaError):
        prep_matrix.flatten_pro_builds(builds)


def test_flatten_pro_builds_rejects_mixed_public_and_pro_tracks():
    builds = [
        {
            "name": "mock",
            "release": {
                "1.0-24.04": {
                    "pro": {
                        "services": ["esm-apps"],
                        "config": {
                            "token": "secrets.UBUNTU_PRO_TOKEN",
                            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
                        },
                    },
                },
                "latest": {"risks": ["stable"]},
            },
        }
    ]

    with pytest.raises(prep_matrix.InvalidSchemaError):
        prep_matrix.flatten_pro_builds(builds)
