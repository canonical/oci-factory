# from pathlib import Path
# import pytest

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from src.image.prepare_single_image_build_matrix import main as prepare_build_matrix

from .. import DATA_DIR


@pytest.fixture
def prep_execution(tmpdir, monkeypatch, request):

    image_trigger_sample = getattr(request, "param", None)

    # configure files/env requried for the test
    github_output = tmpdir / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    github_step_summary = tmpdir / "github_step_summary"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(github_step_summary))

    revision_data_dir = tmpdir / "revision-data"
    revision_data_dir.mkdir()

    oci_trigger_dir = tmpdir / "image_trigger"
    oci_trigger_dir.mkdir()
    shutil.copy(
        image_trigger_sample,
        oci_trigger_dir / "image.yaml",
    )

    # patch the arv for the test. script.py can be anything
    args = (
        f"--oci-path {oci_trigger_dir} --revision-data-dir {revision_data_dir}".split(
            " "
        )
    )
    monkeypatch.setattr(sys, "argv", ["script.py"] + args)

    return revision_data_dir, github_output, github_step_summary


@pytest.mark.parametrize(
    "prep_execution, expected_release_to, expected_release_count",
    [
        (DATA_DIR / "image_all_eol_tracks_with_release.yaml", True, 0),
        (DATA_DIR / "image_all_eol_tracks.yaml", False, 0),
        (DATA_DIR / "image_no_track_releases.yaml", False, 0),
        (DATA_DIR / "image_single_track_release.yaml", True, 1),
        (DATA_DIR / "image_with_release.yaml", True, 3),
        (DATA_DIR / "image_without_release.yaml", True, 3),
    ],
    indirect=["prep_execution"],
)
def test_release_to(prep_execution, expected_release_to, expected_release_count):
    """Test state of release-to in github output after running prepare_single_image_build_matrix"""
    revision_data_dir, github_output, _ = prep_execution

    # run main from prepare_single_image_build_matrix
    prepare_build_matrix()

    github_output_content = github_output.read_text("utf8")

    assert re.search(
        f'^release-to={"true" if expected_release_to else ""}$',
        github_output_content,
        re.M,
    ), "Invalid release-to value"

    revision_files = Path(revision_data_dir).glob("*")

    release_count = 0

    for file in revision_files:
        revision_data = json.loads(file.read_text())
        if release_list := revision_data.get("release"):
            release_count += len(release_list)
    # run main from prepare_single_image_build_matrix
    prepare_build_matrix()

    github_output_content = github_output.read_text("utf8")
    assert (
        expected_release_count == release_count
    ), "Invalid number of builds to release"


@pytest.mark.parametrize(
    "prep_execution",
    [DATA_DIR / "image_v2_ignored_vuln.yaml"],
    indirect=["prep_execution"],
)
def test_ignored_vulnerabilities(prep_execution):
    _, github_output, _ = prep_execution

    # run main from prepare_single_image_build_matrix
    prepare_build_matrix()

    github_output_content = github_output.read_text("utf8")

    assert re.search(
        r'build-matrix=\{"include": \[.*"directory": "mock_rock/1.2", .*"ignored-vulnerabilities": "CVE-2023-1234 CVE-2024-5678".*\]\}',
        github_output_content,
        re.M,
    )

    assert re.search(
        r'build-matrix=\{"include": \[.*"directory": "mock_rock/1.1", .*"ignored-vulnerabilities": "".*\]\}',
        github_output_content,
        re.M,
    )
