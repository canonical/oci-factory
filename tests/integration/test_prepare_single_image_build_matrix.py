# from pathlib import Path
# import pytest

# from src.image.utils.schema.triggers import ImageTriggerValidationError
# import yaml
# from glob import glob
from src.image.prepare_single_image_build_matrix import main as prepare_build_matrix
import pytest
import re
import shutil
import sys

from .. import DATA_DIR


@pytest.fixture
def prep_execution(tmpdir, monkeypatch, request):

    image_trigger_sample = getattr(request, "param", None)

    # configure files/env requried for the test
    github_output = tmpdir / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

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

    return revision_data_dir, github_output


@pytest.mark.parametrize(
    "prep_execution, release_to",
    [
        (DATA_DIR / "image_all_eol_tracks_with_release.yaml", True),
        (DATA_DIR / "image_all_eol_tracks.yaml", False),
        (DATA_DIR / "image_no_track_releases.yaml", False),
        (DATA_DIR / "image_single_track_release.yaml", True),
        (DATA_DIR / "image_with_release.yaml", True),
        (DATA_DIR / "image_without_release.yaml", True),
    ],
    indirect=["prep_execution"],
)
def test_release_to(prep_execution, release_to):
    """Test state of release-to in github output after running prepare_single_image_build_matrix"""
    _, github_output = prep_execution

    # run main from prepare_single_image_build_matrix
    prepare_build_matrix()

    github_output_content = github_output.read_text("utf8")
    
    assert re.search(
                f'^release-to={"true" if release_to else ""}$' , github_output_content, re.M
            ), \
        "Invalid release-to value"
