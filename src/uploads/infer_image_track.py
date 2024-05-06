#!/usr/bin/env python3

import argparse
import os
import logging
import subprocess
import sys
import yaml

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "image")
    )
)

from image.utils import custom_yaml

logging.basicConfig()


def get_release_from_codename(codename: str) -> str:
    """Uses distro-info tools to infer the Ubuntu release from its codename."""
    all_releases = subprocess.check_output(
        ["ubuntu-distro-info", "--fullname", "--all"], universal_newlines=True
    ).splitlines()

    return list(filter(lambda x: codename.lower() in x.lower(), all_releases))[
        0
    ].split()[1]


parser = argparse.ArgumentParser()
parser.add_argument(
    "--recipe-dirname",
    help="Path to the directory where rockcraft.yaml is",
    required=True,
)
args = parser.parse_args()

with open(
    f"{args.recipe_dirname.rstrip('/')}/rockcraft.yaml", encoding="UTF-8"
) as rockcraft_file:
    rockcraft_yaml = yaml.safe_load(rockcraft_file)

rock_base = (
    rockcraft_yaml["base"]
    if rockcraft_yaml["base"] != "bare"
    else rockcraft_yaml["build-base"]
)

try:
    base_release = float(rock_base.replace(":", "@").split("@")[-1])
except ValueError:
    logging.warning(
        f"Could not infer ROCK's base release from {rock_base}. Trying with codename."
    )
    base_release = float(
        get_release_from_codename(rock_base.replace(":", "@").split("@")[-1])
    )

version = rockcraft_yaml["version"]

track = f"{version}-{base_release}"
print(f"rock track: {track}")

with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
    print(f"track={track}", file=gh_out)
    print(f"base=ubuntu:{base_release}", file=gh_out)
