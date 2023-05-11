#!/usr/bin/env python3

"""
This module allows you to extract the required information from images to create documentation.
"""
import argparse
import os

import yaml
import pydantic
from schema.triggers import DocSchema


def validate_documentation_trigger(data: dict) -> None:
    """Loads the documentation.yaml into the schema validation model."""
    if not isinstance(data, dict):
        raise TypeError("documentation.yaml data cannot be loaded into a dictionary")

    _ = DocSchema(**data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oci-paths",
        help="Comma-separated list of paths to the releases.yaml files.",
        required=True,
    )

    args = parser.parse_args()

    releases = []
    for index, oci_path in enumerate(args.oci_paths.split(",")):
        this_release = {}
        img_name = os.path.abspath(oci_path).rstrip("/").split("/")[-1]
        this_release["name"] = img_name
        this_release["all-tags-file"] = f"{oci_path}/_tags.json"
        this_release["oci-path"] = oci_path
        this_release["trigger-name"] = f"{oci_path}/_documentation.yaml"

        with open(f"{oci_path}/documentation.yaml", encoding="UTF-8") as bf:
            documentation_data = yaml.safe_load(bf) or {}
            try:
                validate_documentation_trigger(documentation_data)
            except pydantic.ValidationError:
                print("Bad schema for " + this_release["trigger-name"])
                raise

        releases.append(this_release)

    matrix = {"include": releases}

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="UTF-8") as gh_out:
        print(f"multi-image-documentation-matrix={matrix}", file=gh_out)
