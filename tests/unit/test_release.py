import json
import sys

import pytest
import yaml

import src.shared.release_info as shared
from src.image.release import main, remove_eol_tags

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


def _pro_release_files(tmp_path, services=None, previous_releases=None):
    services = services or ["esm-apps", "esm-infra"]
    trigger = tmp_path / "image.yaml"
    releases = tmp_path / "_pro_releases.json"
    revision_tags = tmp_path / "revision-tags.txt"
    github_output = tmp_path / "github-output.txt"
    summary = tmp_path / "summary.txt"

    trigger.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "upload": [],
                "pro-release": {
                    "1.2-22.04": {
                        "end-of-life": "2099-01-01T00:00:00Z",
                        "services": services,
                        "beta": "7",
                    }
                },
            },
            sort_keys=False,
        )
    )
    releases.write_text(json.dumps(previous_releases or {}))
    revision_tags.write_text("1.2-22.04_7")
    return trigger, releases, revision_tags, github_output, summary


def _run_pro_release(monkeypatch, files, *extra_args):
    trigger, releases, revision_tags, github_output, summary = files
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release.py",
            "--image-trigger",
            str(trigger),
            "--image-name",
            "mock-rock",
            "--all-releases",
            str(releases),
            "--all-revision-tags",
            str(revision_tags),
            "--pro",
            *extra_args,
        ],
    )
    main()


def test_pro_release_uses_local_archive(monkeypatch, tmp_path):
    files = _pro_release_files(tmp_path)
    calls = []
    monkeypatch.setattr("subprocess.check_call", calls.append)

    _run_pro_release(monkeypatch, files)

    assert len(calls) == 1
    assert calls[0][1:] == [
        "oci-archive:mock-rock_1.2-22.04_7",
        "mock-rock",
        "--pro",
        "1.2-22.04_beta",
    ]
    assert not files[3].exists()


def test_validate_only_has_no_side_effects(monkeypatch, tmp_path):
    files = _pro_release_files(tmp_path)
    original_releases = files[1].read_text()
    calls = []
    monkeypatch.setattr("subprocess.check_call", calls.append)

    _run_pro_release(monkeypatch, files, "--validate-only")

    assert calls == []
    assert files[1].read_text() == original_releases
    assert not files[3].exists()


def test_update_pro_release_state(monkeypatch, tmp_path):
    files = _pro_release_files(tmp_path, services=["esm-infra", "esm-apps"])

    _run_pro_release(monkeypatch, files, "--update-releases-json")

    state = json.loads(files[1].read_text())
    assert state["1.2-22.04"]["services"] == ["esm-apps", "esm-infra"]
    assert state["1.2-22.04"]["beta"] == {"target": "7"}


def test_pro_release_rejects_historical_service_conflict(monkeypatch, tmp_path):
    files = _pro_release_files(
        tmp_path,
        services=["esm-infra"],
        previous_releases={
            "1.2-22.04": {
                "end-of-life": "2027-01-01T00:00:00Z",
                "services": ["esm-apps"],
                "beta": {"target": "6"},
            }
        },
    )

    with pytest.raises(shared.BadChannel, match="already uses services"):
        _run_pro_release(monkeypatch, files, "--validate-only")


def test_pro_and_ghcr_modes_are_mutually_exclusive(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release.py",
            "--image-trigger",
            "unused",
            "--all-releases",
            "unused",
            "--all-revision-tags",
            "unused",
            "--pro",
            "--ghcr-repo",
            "canonical/oci-factory",
        ],
    )

    with pytest.raises(SystemExit):
        main()


def test_public_release_ignores_pro_upload_eol(monkeypatch, tmp_path):
    trigger = tmp_path / "image.yaml"
    releases = tmp_path / "_releases.json"
    revision_tags = tmp_path / "revision-tags.txt"
    summary = tmp_path / "summary.txt"
    trigger.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "release": {
                    "1.2-22.04": {
                        "end-of-life": "2027-01-01T00:00:00Z",
                        "beta": "7",
                    }
                },
                "upload": [
                    {
                        "source": "canonical/rocks-toolbox",
                        "commit": "public",
                        "directory": "mock_rock/1.2",
                        "release": {
                            "1.2-22.04": {
                                "end-of-life": "2027-01-01T00:00:00Z",
                                "risks": ["beta"],
                            }
                        },
                    },
                    {
                        "source": "canonical/rocks-toolbox",
                        "commit": "pro",
                        "directory": "mock_rock/1.2",
                        "pro": {"services": ["esm-apps"]},
                        "release": {
                            "1.2-22.04": {
                                "end-of-life": "2030-01-01T00:00:00Z",
                                "risks": ["beta"],
                            }
                        },
                    },
                ],
            },
            sort_keys=False,
        )
    )
    releases.write_text("{}")
    revision_tags.write_text("1.2-22.04_7")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release.py",
            "--image-trigger",
            str(trigger),
            "--image-name",
            "mock-rock",
            "--all-releases",
            str(releases),
            "--all-revision-tags",
            str(revision_tags),
            "--update-releases-json",
        ],
    )

    main()

    state = json.loads(releases.read_text())
    assert state["1.2-22.04"]["end-of-life"] == "2027-01-01T00:00:00Z"
