#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import glob
import json
import pydantic
import yaml
from typing import Any
from pathlib import Path
from git import Repo
from tempfile import TemporaryDirectory as tempdir
from copy import deepcopy
import logging


from src.uploads.infer_image_track import get_base_and_track
from src.shared.github_output import GithubOutput
from src.image.utils.schema.triggers import ImageSchema

# TODO: 
# - inject_metadata uses a static github url, does this break builds that are sourced
#   from non-gh repos?

parser = argparse.ArgumentParser()
parser.add_argument(
    "--oci-path",
    help="Local path to the image's folder hosting the image.yaml file",
    type=Path,
    required=True,
)
parser.add_argument(
    "--revision-data-dir",
    help="Path where to save the revision data files for each build",
    type=Path,
    required=True,
)
parser.add_argument(
    "--next-revision",
    help="Next revision number",
    type=int,
    default=1,
)
parser.add_argument(
    "--infer-image-track",
    help="Infer the track corresponding to the releases",
    action="store_true",
    default=False,
)

class AmbiguousConfigFileError(Exception):
    """Raised when multiple trigger image.y*ml files are found."""
    pass

class InvalidSchemaError(Exception):
    """Raised when image.yaml schema is found."""
    pass



def validate_image_trigger(data: dict) -> None:
    """Loads the image.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("image.yaml data cannot be loaded into a dictionary")

    _ = ImageSchema(**data)

    return None


def is_track_eol(track_value: str, track_name: str|None = None) -> bool:
    """Test if track is EOL, or still valid. Log warning if track_name is provided."""
    eol_date = datetime.strptime(track_value['end-of-life'],"%Y-%m-%dT%H:%M:%SZ",).replace(tzinfo=timezone.utc)
    is_eol = eol_date < datetime.now(timezone.utc)

    if is_eol and track_name is not None:
        logging.warning(f"Removing EOL track \"{track_name}\", EOL: {eol_date}")

    return is_eol

def filter_eol_tracks(build: dict[str, Any]) -> dict[str, Any]:
    """Filter EOL tracks from build."""
    build['release'] = {
            key:value 
            for key, value in build['release'].items() 
            if not is_track_eol(value, track_name=f"{key}:{build['name']}")
        }

    return build

def filter_empty_release(builds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter any builds with no tracks specified."""

    # remove any end of life tracks
    builds = [filter_eol_tracks(build) for build in builds]

    return [build for build in builds if len(build['release'])]

def write_build(data_dir: Path, build: dict[str, Any]):
    with open(data_dir / str(build['revision']), "w", encoding="UTF-8") as fh:
        json.dump(build, fh)


def locate_trigger_yaml(oci_path: Path) -> Path:
    """Locate image trigger file if that is image.yaml or image.yml"""

    oci_path_yaml_files = glob.glob(str(oci_path / "image.y*ml"))

    if len(oci_path_yaml_files) == 0:
        raise FileNotFoundError(f"image.y*ml not found in {oci_pat}")
    elif len(oci_path_yaml_files) > 1:
        raise AmbiguousConfigFileError(f"More than one image.y*ml not found in {oci_pat}")

    return Path(oci_path_yaml_files[0])

def load_trigger_yaml(oci_path: Path) -> dict[str, Any]:
    """Load image trigger file (image.yaml) located in oci_path directory."""

    image_trigger_file = locate_trigger_yaml(oci_path)

    with open(image_trigger_file, encoding="UTF-8") as bf:
        image_trigger = yaml.load(bf, Loader=yaml.BaseLoader)

    try:
        validate_image_trigger(image_trigger)
    except pydantic.error_wrappers.ValidationError as err:
        raise InvalidSchemaError(f"Bad schema for {image_trigger_file}") from err

    return image_trigger

def write_github_output(release_to: bool, builds: list[dict[str, Any]], revision_data_dir: Path):
    """Write script result to GITHUB_OUTPUT."""
    
    outputs = {
        'build-matrix':
            {
                'include': builds
             },
        'release-to': release_to,
        'revision-data-dir': str(revision_data_dir)
    }
    print(outputs)
    # with GithubOutput() as github_output:
    #     github_output.write(**outputs)

def inject_metadata(builds: list[dict[str, Any]], next_revision: int, oci_path: Path):
    """Inject additional metadata (name, path, revision, directory, dir_identifier, 
    track, base) into build dicts.
    """
    
    _builds = deepcopy(builds)

    # inject some extra metadata into the matrix data
    for img_number, build in enumerate(_builds):
        build["name"] = str(oci_path).rstrip("/").split("/")[-1]
        build["path"] = str(oci_path)

        # used in setting the path where the build info is saved
        build["revision"] = img_number + int(next_revision)

        # Add dir_identifier to assemble the cache key and artefact path
        # No need to write it to rev data file since it's only used in matrix
        build["dir_identifier"] = (
            build["directory"].rstrip("/").replace("/", "_")
        )

        with tempdir() as d:
            url = f"https://github.com/{build['source']}.git"
            repo = Repo.clone_from(url, d)
            repo.git.checkout(build["commit"])
            # get the base image from the rockcraft.yaml file
            with open(
                f"{d}/{build['directory']}/rockcraft.yaml",
                encoding="UTF-8",
            ) as rockcraft_file:
                rockcraft_yaml = yaml.load(rockcraft_file, Loader=yaml.BaseLoader)

        base_release, track = get_base_and_track(rockcraft_yaml)
        build["track"] = track
        build["base"] = f"ubuntu:{base_release}"

    return _builds

def main():
    """Executed when script is called directly."""
    args = parser.parse_args()

    # locate and load image.yaml
    image_trigger = load_trigger_yaml(args.oci_path)

    # extract builds to upload
    builds = image_trigger.get("upload", [])

    # inject additional meta data into builds
    builds = inject_metadata(builds, args.next_revision, args.oci_path)

    # remove any builds without valid tracks
    builds = filter_empty_release(builds)

    # pretty print builds
    logging.info(f"Generating matrix for following builds: \n {json.dumps(builds, indent=4)}")

    for build in builds:
        write_build(args.revision_data_dir, build)

        # the workflow GH matrix has a problem parsing nested JSON dicts
        # so let's remove this field since we don't need it for the builds
        del build["release"]

    release_to = "true" if "release" in image_trigger else ""

    write_github_output(release_to, builds, args.revision_data_dir)


if __name__ == "__main__":
    main()
