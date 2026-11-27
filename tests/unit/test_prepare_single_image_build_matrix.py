import io
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
from src.uploads import infer_image_track


@pytest.mark.parametrize(
    "builders,versions,expected_error",
    [
        (["amd64", "arm64"], [], True),
        (["amd64", "arm64"], ["26.10", "27.04"], True),
        (["amd64", "arm64"], ["26.10", "26.10"], False),
        ("amd64", ["26.10", "27.04"], False),
    ],
)
def test_devel_track_requires_one_buildd_release(
    monkeypatch, builders, versions, expected_error
):
    products = {
        "stable": {"arch": "amd64", "aliases": "24.04,noble", "version": "24.04"}
    }
    for arch, version in zip(["amd64", "arm64"], versions):
        products[arch] = {
            "arch": arch,
            "aliases": f"{version},devel",
            "version": version,
        }
    feed = json.dumps({"products": products})
    monkeypatch.setattr(infer_image_track, "urlopen", lambda url, timeout: io.StringIO(feed))
    infer_image_track.get_devel_release.cache_clear()
    recipe = {
        "base": "bare",
        "build-base": "devel",
        "version": "1.0",
        "platforms": {"arm64": {"build-on": builders, "build-for": "arm64"}},
    }

    if expected_error:
        with pytest.raises(ValueError, match="buildd devel release has mixed versions"):
            infer_image_track.get_base_and_track(recipe)
    else:
        assert infer_image_track.get_base_and_track(recipe) == ("26.10", "1.0-26.10")
    infer_image_track.get_devel_release.cache_clear()


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


@pytest.mark.parametrize(
    "tracks,expected_error",
    [
        (["1.0-27.04"], False),
        (["1.0-26.10"], True),
        ([], False),
        (["1.0-27.04", "1.0-26.10"], True),
        (["1-27.04"], False),
        (["devel", "2"], False),
        (["devel", "1.0-26.10"], True),
    ],
)
def test_devel_track_must_match_declared_release_tracks(
    monkeypatch, tracks, expected_error
):
    monkeypatch.setattr(infer_image_track, "get_devel_release", lambda arches: "27.04")
    recipe = {
        "base": "bare",
        "build-base": "devel",
        "version": "1.0",
        "platforms": {"amd64": None},
    }

    if expected_error:
        with pytest.raises(ValueError, match="pin build-base"):
            infer_image_track.get_base_and_track(recipe, tracks)
    else:
        assert infer_image_track.get_base_and_track(recipe, tracks) == (
            "27.04",
            "1.0-27.04",
        )


def test_devel_check_only_applies_when_the_base_is_devel(monkeypatch):
    def unexpected_lookup(arches):
        pytest.fail("A recipe with its own base must not resolve devel")

    monkeypatch.setattr(infer_image_track, "get_devel_release", unexpected_lookup)
    recipe = {
        "base": "ubuntu@24.04",
        "build-base": "devel",
        "version": "1.0",
        "platforms": {"amd64": None},
    }

    assert infer_image_track.get_base_and_track(recipe, ["1.0-26.10"]) == (
        "24.04",
        "1.0-24.04",
    )


@pytest.mark.parametrize(
    "stale_track_eol,expected_error",
    [
        ("2000-01-01T00:00:00Z", False),
        ("2100-01-01T00:00:00Z", True),
    ],
)
def test_expired_tracks_are_not_checked_against_devel(
    monkeypatch, stale_track_eol, expected_error
):
    def clone_source(url, destination):
        (Path(destination) / "rockcraft.yaml").write_text(
            "name: example\nversion: '1.0'\nbase: bare\nbuild-base: devel\n"
            "platforms:\n  amd64:\n    build-on: [amd64]\n    build-for: amd64\n"
        )
        return SimpleNamespace(git=SimpleNamespace(checkout=lambda commit: None))

    monkeypatch.setattr(infer_image_track, "get_devel_release", lambda arches: "27.04")
    monkeypatch.setattr(prep_matrix, "get_source_visibility", lambda url: "public")
    monkeypatch.setattr(prep_matrix.Repo, "clone_from", clone_source)
    builds = [
        {
            "source": "canonical/example",
            "commit": "0" * 40,
            "directory": ".",
            "release": {
                "1.0-26.10": {"end-of-life": stale_track_eol, "risks": ["edge"]},
                "1.0-27.04": {"end-of-life": "2100-01-01T00:00:00Z", "risks": ["edge"]},
            },
        }
    ]

    if expected_error:
        with pytest.raises(ValueError, match="pin build-base"):
            prep_matrix.inject_metadata(builds, 1, Path("oci/example"))
    else:
        injected = prep_matrix.inject_metadata(builds, 1, Path("oci/example"))
        assert injected[0]["track"] == "1.0-27.04"
