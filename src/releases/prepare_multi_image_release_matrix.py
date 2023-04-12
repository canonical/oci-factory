#!/usr/bin/env python3

import argparse
import os


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oci-paths",
        help="Comma-separatec list of paths to the releases.yaml files.",
        required=True,
    )

    args = parser.parse_args()

    releases = []
    for index, oci_path in enumerate(args.oci_paths.split(",")):
        this_release = {}

        img_name = os.path.abspath(oci_path).rstrip("/").split("/")[-1]
        this_release["name"] = img_name
        this_release["all-tags-file"] = f"{oci_path}/_tags.json"
        this_release["release-number"] = index
        this_release["oci-path"] = oci_path
        this_release["trigger-name"] = f"{oci_path}/releases.yaml"
        this_release["is-production"] = "true" if "mock-" in oci_path else "false"

        releases.append(this_release)

    matrix = {"include": releases}

    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"multi-image-release-matrix={matrix}", file=gh_out)
