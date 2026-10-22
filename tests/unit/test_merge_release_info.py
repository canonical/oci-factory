import json
import runpy
import sys

import pytest
import yaml

from src.image.utils.schema.triggers import ImageTriggerValidationError


def _revision_data(services, revision=42):
    return {
        "source": "canonical/rocks-toolbox",
        "commit": "abcdef1234567890",
        "directory": "mock_rock/1.2",
        "name": "mock-rock",
        "path": "oci/mock-rock",
        "revision": revision,
        "track": "1.2-22.04",
        "pro": {"services": services},
        "release": {
            "1.2-22.04": {
                "end-of-life": "2030-05-01T00:00:00Z",
                "risks": ["beta"],
            }
        },
    }


def _merge(tmp_path, monkeypatch, trigger, revision_data):
    trigger_path = tmp_path / "image.yaml"
    revision_path = tmp_path / "revision.json"
    trigger_path.write_text(yaml.safe_dump(trigger, sort_keys=False))
    revision_path.write_text(json.dumps(revision_data))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_release_info.py",
            "--image-trigger",
            str(trigger_path),
            "--revision-data-file",
            str(revision_path),
        ],
    )
    runpy.run_module("src.image.merge_release_info", run_name="__main__")
    return yaml.safe_load(trigger_path.read_text())


def test_merge_pro_release(tmp_path, monkeypatch):
    result = _merge(
        tmp_path,
        monkeypatch,
        {"version": 2, "upload": []},
        _revision_data(["esm-infra", "esm-apps"]),
    )

    release = result["pro-release"]["1.2-22.04"]
    assert release["end-of-life"] == "2030-05-01T00:00:00Z"
    assert release["services"] == ["esm-infra", "esm-apps"]
    assert release["beta"] == "42"
    assert release["edge"] == "1.2-22.04_beta"
    assert "release" not in result


def test_merge_rejects_conflicting_service_sets(tmp_path, monkeypatch):
    trigger = {
        "version": 2,
        "upload": [],
        "pro-release": {
            "1.2-22.04": {
                "end-of-life": "2030-05-01T00:00:00Z",
                "services": ["esm-apps"],
                "beta": "41",
            }
        },
    }

    with pytest.raises(ImageTriggerValidationError, match="different pro service"):
        _merge(tmp_path, monkeypatch, trigger, _revision_data(["esm-infra"]))


@pytest.mark.parametrize(
    "services, expected",
    [
        (["esm-apps", "esm-infra"], "1.2-22.04"),
        (["fips", "esm-infra"], "1.2-fips-22.04"),
        (["ros", "fips"], "1.2-fips-ros-22.04"),
        (["fips"], "25-edge-fips-26.04"),
    ],
)
def test_assemble_pro_track(services, expected):
    from src.image.merge_release_info import _assemble_pro_track

    track = "25-edge-26.04" if expected.startswith("25-edge") else "1.2-22.04"
    assert _assemble_pro_track(track, services) == expected
