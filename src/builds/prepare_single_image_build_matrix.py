#!/usr/bin/env python3

import argparse
import glob
import json
import os
import pydantic
import yaml

from schema.triggers import BuildsSchema


def validate_buids_trigger(data: dict) -> None:
    """Loads the builds.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("builds.yaml data cannot be loaded into a dictionary")

    _ = BuildsSchema(**data)

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oci-path",
        help="Local path to the image's folder hosting the builds.yaml file",
        required=True,
    )

    args = parser.parse_args()

    builds_file = glob.glob(f"{args.oci_path}/builds.y*ml")[0]

    print(f"Generating build matrix for {builds_file}")
    with open(builds_file) as bf:
        builds_data = yaml.safe_load(bf)
        try:
            validate_buids_trigger(builds_data)
        except pydantic.error_wrappers.ValidationError:
            print(f"Bad schema for {builds_file}")
            raise

    builds = builds_data.get("images", [])

    # inject some extra metadata into the matrix data
    for img_number, _ in enumerate(builds):
        builds[img_number]["name"] = args.oci_path.rstrip("/").split("/")[-1]
        builds[img_number]["path"] = args.oci_path
        # make sure every build of this image has a unique identifier
        # within the execution of the workflow
        builds[img_number]["id"] = img_number

    matrix = {"include": builds}
    print(f"{args.oci_path} - build matrix:\n{json.dumps(matrix, indent=4)}")
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"build-matrix={matrix}", file=gh_out)
