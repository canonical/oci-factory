import json
import runpy
import sys

import yaml

import src.image.prepare_single_image_build_matrix as prep_matrix


def test_write_revision_data_excludes_none_pro(tmp_path):
    build = {
        "source": "canonical/rocks-toolbox",
        "commit": "abcdef1234567890",
        "directory": "mock_rock/1.1",
        "name": "mock-rock",
        "path": "oci/mock-rock",
        "revision": 1,
        "track": "1.1-22.04",
        "pro": None,
        "release": {
            "1.1-22.04": {
                "end-of-life": "2030-05-01T00:00:00Z",
                "risks": ["beta"],
            }
        },
    }

    prep_matrix.write_revision_data(tmp_path, build)

    revision_data = json.loads((tmp_path / "1").read_text())
    assert "pro" not in revision_data


def test_merge_release_info_ignores_null_pro(tmp_path, monkeypatch):
    image_trigger_path = tmp_path / "image.yaml"
    image_trigger_path.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "upload": [],
                "release": {
                    "latest": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "candidate": "1.2-22.04_beta",
                    }
                },
            }
        )
    )

    revision_data_path = tmp_path / "revision-data.json"
    revision_data_path.write_text(
        json.dumps(
            {
                "source": "canonical/rocks-toolbox",
                "commit": "abcdef1234567890",
                "directory": "mock_rock/1.1",
                "name": "mock-rock",
                "path": "oci/mock-rock",
                "revision": 1,
                "track": "1.1-22.04",
                "pro": None,
                "release": {
                    "1.1-22.04": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "risks": ["beta"],
                    }
                },
            }
        )
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_release_info.py",
            "--image-trigger",
            str(image_trigger_path),
            "--revision-data-file",
            str(revision_data_path),
        ],
    )

    runpy.run_module("src.image.merge_release_info", run_name="__main__")

    merged_trigger = yaml.safe_load(image_trigger_path.read_text())
    assert "pro" not in merged_trigger["release"]["1.1-22.04"]
    prep_matrix.validate_image_trigger(merged_trigger)


def test_merge_release_info_copies_upload_pro_to_release_tracks(tmp_path, monkeypatch):
    image_trigger_path = tmp_path / "image.yaml"
    image_trigger_path.write_text(yaml.safe_dump({"version": 2, "upload": []}))

    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }
    revision_data_path = tmp_path / "revision-data.json"
    revision_data_path.write_text(
        json.dumps(
            {
                "source": "canonical/rocks-toolbox",
                "commit": "abcdef1234567890",
                "directory": "mock_rock/1.1",
                "name": "mock-rock",
                "path": "oci/mock-rock",
                "revision": 1,
                "track": "1.1-22.04",
                "pro": pro_config,
                "release": {
                    "1.1-22.04": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "risks": ["beta", "edge"],
                    }
                },
            }
        )
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_release_info.py",
            "--image-trigger",
            str(image_trigger_path),
            "--revision-data-file",
            str(revision_data_path),
        ],
    )

    runpy.run_module("src.image.merge_release_info", run_name="__main__")

    merged_trigger = yaml.safe_load(image_trigger_path.read_text())
    assert merged_trigger["release"]["1.1-22.04"]["pro"] == pro_config
    prep_matrix.validate_image_trigger(merged_trigger)
