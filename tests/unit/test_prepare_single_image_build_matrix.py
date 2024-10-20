from pathlib import Path
import pytest

import src.image.prepare_single_image_build_matrix as prep_matrix


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
