#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import glob
import json
import os
import pydantic
import yaml

from utils.schema.triggers import ImageSchema


def validate_image_trigger(data: dict) -> None:
    """Loads the image.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("image.yaml data cannot be loaded into a dictionary")

    _ = ImageSchema(**data)

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oci-path",
        help="Local path to the image's folder hosting the image.yaml file",
        required=True,
    )
    parser.add_argument(
        "--revision-data-dir",
        help="Path where to save the revision data files for each build",
        required=True,
    )
    parser.add_argument(
        "--next-revision",
        help="Next revision number",
        default=1,
    )
    parser.add_argument(
        "--infer-image-track",
        help="Infer the track corresponding to the releases",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    image_trigger_file = glob.glob(f"{args.oci_path}/image.y*ml")[0]

    print(f"Generating build matrix for {image_trigger_file}")
    with open(image_trigger_file, encoding="UTF-8") as bf:
        image_trigger = yaml.load(bf, Loader=yaml.BaseLoader)
        try:
            validate_image_trigger(image_trigger)
        except pydantic.error_wrappers.ValidationError as err:
            raise Exception(f"Bad schema for {image_trigger_file}") from err

    builds = image_trigger.get("upload", [])

    release_to = "true" if "release" in image_trigger else ""

    img_number = 0
    # inject some extra metadata into the matrix data
    while img_number < len(builds):
        builds[img_number]["name"] = args.oci_path.rstrip("/").split("/")[-1]
        builds[img_number]["path"] = args.oci_path
        builds[img_number]["revision"] = img_number + int(args.next_revision)

        if args.infer_image_track:
            import sys

            sys.path.append("src/")
            from git import Repo
            from tempfile import TemporaryDirectory as tempdir
            from uploads.infer_image_track import get_base_and_track

            with tempdir() as d:
                url = f"https://github.com/{builds[img_number]['source']}.git"
                repo = Repo.clone_from(url, d)
                repo.git.checkout(builds[img_number]["commit"])
                # get the base image from the rockcraft.yaml file
                with open(
                    f"{d}/{builds[img_number]['directory']}/rockcraft.yaml",
                    encoding="UTF-8",
                ) as rockcraft_file:
                    rockcraft_yaml = yaml.load(rockcraft_file, Loader=yaml.BaseLoader)

            base_release, track = get_base_and_track(rockcraft_yaml)
            builds[img_number]["track"] = track
            builds[img_number]["base"] = f"ubuntu:{base_release}"

        with open(
            f"{args.revision_data_dir}/{builds[img_number]['revision']}",
            "w",
            encoding="UTF-8",
        ) as data_file:
            json.dump(builds[img_number], data_file)

        # Add dir_identifier to assemble the cache key and artefact path
        # No need to write it to rev data file since it's only used in matrix
        builds[img_number]["dir_identifier"] = (
            builds[img_number]["directory"].rstrip("/").replace("/", "_")
        )

        # set an output as a marker for later knowing if we need to release
        if "release" in builds[img_number]:
            min_eol = datetime.strptime(
                min(v["end-of-life"] for v in builds[img_number]["release"].values()),
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            if min_eol < datetime.now(timezone.utc):
                print("Track skipped because it reached its end of life")
                del builds[img_number]
                continue
            else:
                release_to = "true"
                # the workflow GH matrix has a problem parsing nested JSON dicts
                # so let's remove this field since we don't need it for the builds
                builds[img_number]["release"] = "true"
        else:
            builds[img_number]["release"] = ""

        img_number += 1

    matrix = {"include": builds}
    print(f"{args.oci_path} - build matrix:\n{json.dumps(matrix, indent=4)}")
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"build-matrix={matrix}", file=gh_out)
        print(f"release-to={release_to}", file=gh_out)
        print(f"revision-data-dir={args.revision_data_dir}", file=gh_out)
