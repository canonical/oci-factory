#!/usr/bin/env python3

import argparse
import glob
import json
import os
import yaml


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oci-dirs-file",
        help="Path to JSON file where OCI dirs are listed",
        required=True,
    )

    args = parser.parse_args()

    print(f"Loading target OCI directories from {args.oci_dirs}")
    with open(args.oci_dirs_file) as odf:
        oci_dirs = json.load(odf)

    all_builds = []

    for oci_image in oci_dirs:
        builds_file = glob.glob(f"{oci_image}/builds.y*ml")[0]

        print(f"Generating build matrix for {builds_file}")
        with open(builds_file) as bf:
            builds = yaml.safe_load(bf)

        all_builds += builds

    build_matrix = {"include": all_builds}
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"build-matrix={build_matrix}", file=gh_out)
