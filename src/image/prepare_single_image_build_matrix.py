#!/usr/bin/env python3

import argparse
import glob
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory as tempdir
from typing import Any

import pydantic
import yaml
from git import Repo

from ..shared.github_output import GithubOutput, GithubStepSummary
from ..shared.logs import get_logger
from ..shared.source_url import get_source_url
from ..uploads.infer_image_track import get_base_and_track
from .utils.eol_utils import (
    generate_base_eol_exceed_warning,
    is_track_eol,
    track_eol_exceeds_base_eol,
)
from .utils.schema.revision_data import RevisionDataSchema
from .utils.schema.triggers import ImageSchema


# TODO:
# - inject_metadata uses a static github url, does this break builds that are sourced
#   from non-gh repos?

logger = get_logger()

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

parser.add_argument(
    "--warn-image-eol-exceeds-base-eol",
    help="Warn if the end-of-life date exceeds the LTS date",
    action="store_true",
    default=False,
)


class RevisionDataSchemaFilter(RevisionDataSchema):
    """A subclass of RevisionDataSchema to prepare data for serialization."""

    model_config = pydantic.ConfigDict(extra="ignore")

    @pydantic.model_validator(mode="before")
    def _warn_extra_fields(cls, data: Any) -> Any:  # pylint: disable=no-self-argument
        for extra_field in data.keys() - cls.model_fields.keys():
            logger.warning(
                f'Field "{extra_field}" removed from {data["name"]} revision data'
            )

        return data


class AmbiguousConfigFileError(Exception):
    """Raised when multiple trigger image.y*ml files are found."""


class InvalidSchemaError(Exception):
    """Raised when image.yaml schema is found."""


def validate_image_trigger(data: dict) -> None:
    """Loads the image.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("image.yaml data cannot be loaded into a dictionary")

    _ = ImageSchema(**data)


def filter_eol_tracks(build: dict[str, Any]) -> dict[str, Any]:
    """Filter EOL tracks from build."""
    build["release"] = {
        key: value
        for key, value in build["release"].items()
        if not is_track_eol(value, track_name=f"{key}:{build['name']}")
    }

    return build


def filter_eol_builds(builds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove any builds with eol tracks."""

    # if no release exists and therefore no eol is specified, do nothing
    non_release_builds = [build for build in builds if "release" not in build]

    # if we have release info, then filter based on eol
    release_builds = [
        filtered_build
        for build in builds
        if "release" in build
        and (filtered_build := filter_eol_tracks(build))["release"]
    ]

    return non_release_builds + release_builds


def write_revision_data(data_dir: Path, build: dict[str, Any]):
    """Prepare and dump revision data from build dict. Ignore any fields not included in RevisionDataSchema"""
    revision_data = RevisionDataSchemaFilter(**build)
    with open(data_dir / str(build["revision"]), "w", encoding="UTF-8") as fh:
        fh.write(revision_data.model_dump_json(by_alias=True))


def locate_trigger_yaml(oci_path: Path) -> Path:
    """Locate image trigger file if that is image.yaml or image.yml"""

    oci_path_yaml_files = glob.glob(str(oci_path / "image.y*ml"))

    if len(oci_path_yaml_files) == 0:
        raise FileNotFoundError(f"image.y*ml not found in {oci_path}")
    elif len(oci_path_yaml_files) > 1:
        raise AmbiguousConfigFileError(
            f"More than one image.y*ml not found in {oci_path}"
        )

    return Path(oci_path_yaml_files[0])


def load_trigger_yaml(oci_path: Path) -> dict[str, Any]:
    """Load image trigger file (image.yaml) located in oci_path directory."""
    image_trigger_file = locate_trigger_yaml(oci_path)

    with open(image_trigger_file, encoding="UTF-8") as bf:
        image_trigger = yaml.load(bf, Loader=yaml.BaseLoader)

    try:
        validate_image_trigger(image_trigger)
    except pydantic.ValidationError as err:
        raise InvalidSchemaError(f"Bad schema for {image_trigger_file}") from err

    return image_trigger


def write_github_output(
    release_to: bool, builds: list[dict[str, Any]], revision_data_dir: Path
):
    """Write script result to GITHUB_OUTPUT."""
    outputs = {
        "build-matrix": {"include": builds},
        "release-to": "true" if release_to else "",
        "revision-data-dir": str(revision_data_dir),
    }
    with GithubOutput() as github_output:
        github_output.write(**outputs)


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
        build["dir_identifier"] = build["directory"].rstrip("/").replace("/", "_")

        with tempdir() as d:
            url = get_source_url(build["source"])
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


def find_eol_exceed_base_eol(builds: list[dict[str, Any]]):
    """Check if any of the builds have an EOL date that exceeds the EOL date of the base image."""
    tracks_eol_exceed_base_eol = []
    for build in builds:
        if "release" in build:
            for (
                track,
                track_value,
            ) in build["release"].items():
                if eols := track_eol_exceeds_base_eol(
                    track,
                    track_value["end-of-life"],
                    build["base"] if "base" in build else None,
                ):
                    tracks_eol_exceed_base_eol.append(eols)
    return tracks_eol_exceed_base_eol


def flatten_ignored_vulnerabilities(builds: list[dict[str, Any]]) -> None:
    """Flatten ignored-vulnerabilities field for GH Actions matrix."""
    for build in builds:
        build["ignored-vulnerabilities"] = " ".join(
            build.get("ignored-vulnerabilities", [])
        )


def main():
    """Executed when script is called directly."""
    args = parser.parse_args()

    # locate and load image.yaml
    image_trigger = load_trigger_yaml(args.oci_path)

    # extract builds to upload
    builds = image_trigger.get("upload", [])

    # inject additional meta data into builds
    builds = inject_metadata(builds, args.next_revision, args.oci_path)

    # check if any of the builds have an EOL date that exceeds the EOL date of the base image
    if args.warn_image_eol_exceeds_base_eol:
        if tracks_eol_exceed_base_eol := find_eol_exceed_base_eol(builds):
            title, text = generate_base_eol_exceed_warning(tracks_eol_exceed_base_eol)
            title = f"## Image: {title}"
            with GithubStepSummary() as summary:
                summary.write(title, text)

    # remove any builds without valid tracks
    builds = filter_eol_builds(builds)

    # pretty print builds
    logger.info(
        f"Generating matrix for following builds: \n {json.dumps(builds, indent=4)}"
    )

    # trigger a release if specified in the image_trigger root
    release = "release" in image_trigger

    for build in builds:
        write_revision_data(args.revision_data_dir, build)

        if "release" in build:
            # trigger a release if specified in any of the builds
            release = True

            # the workflow GH matrix has a problem parsing nested JSON dicts
            # so let's remove this field since we don't need it for the builds themselves
            del build["release"]

    flatten_ignored_vulnerabilities(builds)

    write_github_output(release, builds, args.revision_data_dir)


if __name__ == "__main__":
    main()
