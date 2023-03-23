#!/usr/bin/env python3

import argparse
import glob
import json
import os
import pydantic
import yaml

from typing import Dict, List, Literal, Optional


class BuildsImageDockerfileSchema(pydantic.BaseModel):
    """Schema of the optional dockerfile-build section."""

    version: str
    platforms: List[str]

    class Config:
        extra = pydantic.Extra.forbid


class BuildsImageSchema(pydantic.BaseModel):
    """Schema of the Images within the builds.yaml files."""

    source: str
    commit: str
    directory: str
    dockerfile_build: Optional[BuildsImageDockerfileSchema] = pydantic.Field(
        alias="dockerfile-build"
    )
    release_to: Optional[
        Dict[Literal["risks"], List[Literal["edge", "beta", "candidate", "stable"]]]
    ] = pydantic.Field(alias="release-to")

    class Config:
        extra = pydantic.Extra.forbid


class BuildsSchema(pydantic.BaseModel):
    """Validates the schema of the builds.yaml files"""

    version: str
    images: List[BuildsImageSchema]

    class Config:
        extra = pydantic.Extra.forbid


def validate_buids_trigger(data: dict) -> None:
    """Loads the builds.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("builds.yaml data cannot be loaded into a dictionary")

    _ = BuildsSchema(**data)

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Expect the JSON file output from tj-actions/changed-files@v35
    parser.add_argument(
        "--oci-dirs-file",
        help="Path to JSON file where OCI dirs are listed",
        required=True,
    )

    args = parser.parse_args()

    print(f"Loading target OCI directories from {args.oci_dirs_file}")
    with open(args.oci_dirs_file) as odf:
        oci_dirs = json.load(odf)

    all_builds = []

    for oci_image in oci_dirs:
        builds_file = glob.glob(f"{oci_image}/builds.y*ml")[0]

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
            update_with = {
                "name": oci_image.rstrip("/").split("/")[-1],
                "path": oci_image,
            }
            # Guarantee the new keys are added to the beginning of the dict
            builds[img_number] = {**update_with, **builds[img_number]}

        all_builds += builds

    build_matrix = {"include": all_builds}
    print(f"Setting the following build matrix: \n{json.dumps(build_matrix, indent=4)}")
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"build-matrix={build_matrix}", file=gh_out)
