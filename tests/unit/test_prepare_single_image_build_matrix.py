import json
import subprocess
import sys
from glob import glob
from pathlib import Path
from types import SimpleNamespace

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


def test_pro_directory_identifier_is_deterministic():
    first = {
        "directory": "mock_rock/1.2/",
        "pro": {"services": ["esm-infra", "esm-apps"]},
    }
    second = {
        "directory": "mock_rock/1.2",
        "pro": {"services": ["esm-apps", "esm-infra"]},
    }

    assert prep_matrix._get_dir_identifier(first) == (
        "mock_rock_1.2_esm-apps-esm-infra"
    )
    assert prep_matrix._get_dir_identifier(first) == prep_matrix._get_dir_identifier(
        second
    )


def test_inject_pro_metadata_is_matrix_friendly():
    builds = [
        {"directory": "public"},
        {
            "directory": "pro",
            "pro": {"services": ["ros-updates", "esm-infra"]},
        },
    ]

    result = prep_matrix.inject_pro_metadata(builds)

    assert result[0]["pro-services"] == ""
    assert result[1]["pro-services"] == "esm-infra,ros-updates"
    assert "pro-services" not in builds[0]


def test_matrix_supports_sources_with_different_visibility(tmp_path, monkeypatch):
    oci_path = tmp_path / "example"
    oci_path.mkdir()
    uploads = [
        {"source": "canonical/public", "commit": "first", "directory": "."},
        {"source": "canonical/internal", "commit": "second", "directory": "."},
        {"source": "canonical/private", "commit": "third", "directory": "."},
        {"source": "canonical/public", "commit": "fourth", "directory": "."},
    ]
    (oci_path / "image.yaml").write_text(
        yaml.safe_dump({"version": 1, "upload": uploads})
    )
    revision_dir = tmp_path / "revisions"
    revision_dir.mkdir()
    output_path = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prepare",
            "--oci-path",
            str(oci_path),
            "--revision-data-dir",
            str(revision_dir),
        ],
    )
    lookups = []

    def lookup_visibility(command, text):
        lookups.append(command)
        return command[2].rsplit("/", 1)[-1] + "\n"

    def clone_source(url, destination):
        (Path(destination) / "rockcraft.yaml").write_text(
            "name: example\nversion: '1.0'\nbase: bare\nbuild-base: ubuntu@24.04\n"
        )
        return SimpleNamespace(git=SimpleNamespace(checkout=lambda commit: None))

    monkeypatch.setattr(prep_matrix.subprocess, "check_output", lookup_visibility)
    monkeypatch.setattr(prep_matrix.Repo, "clone_from", clone_source)
    prep_matrix.main()

    outputs = dict(line.split("=", 1) for line in output_path.read_text().splitlines())
    builds = json.loads(outputs["build-matrix"])["include"]
    assert [build["source-visibility"] for build in builds] == [
        "public",
        "internal",
        "private",
        "public",
    ]
    assert [build["source"] for build in builds] == [
        upload["source"] for upload in uploads
    ]
    assert len(lookups) == 3
    assert all(command[:2] == ["gh", "api"] for command in lookups)


def test_source_visibility_preserves_external_sources(monkeypatch):
    def unexpected_lookup(*args, **kwargs):
        pytest.fail("External sources must not use the GitHub API")

    monkeypatch.setattr(prep_matrix.subprocess, "check_output", unexpected_lookup)
    assert prep_matrix.get_source_visibility("https://git.launchpad.net/example") == ""


def test_source_visibility_lookup_failure_stops_preparation(monkeypatch):
    def failed_lookup(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(prep_matrix.subprocess, "check_output", failed_lookup)
    with pytest.raises(subprocess.CalledProcessError):
        prep_matrix.get_source_visibility("https://github.com/canonical/internal.git")
