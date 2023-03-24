#!/usr/bin/env python3

import os
import logging
import subprocess
import yaml

DOCKERFILE_IMAGE_VERSION = os.getenv("DOCKERFILE_IMAGE_VERSION", None)


def get_release_from_codename(codename: str) -> str:
    """Uses distro-info tools to infer the Ubuntu release from its codename."""
    all_releases = subprocess.check_output(
        ["ubuntu-distro-info", "--fullname", "--all"], universal_newlines=True
    ).splitlines()

    return list(filter(lambda x: codename.lower() in x.lower(), all_releases))[
        0
    ].split()[1]


if DOCKERFILE_IMAGE_VERSION:
    with open("Dockerfile") as dockerfile:
        dockerfile_content = dockerfile.read().splitlines()

    base = list(filter(lambda x: "FROM" in x, dockerfile_content))[-1]

    try:
        base_release = float(base.split(":")[-1])
    except ValueError:
        logging.warning(
            f"Could not infer Ubuntu release from {base}. Trying with codename."
        )
        base_release = float(get_release_from_codename(base.split(":")[-1]))

    version = DOCKERFILE_IMAGE_VERSION
else:
    with open("rockcraft.yaml") as rockcraft_file:
        rockcraft_yaml = yaml.safe_load(rockcraft_file)

    rock_base = (
        float(rockcraft_yaml["base"])
        if rockcraft_yaml["base"] != "bare"
        else float(rockcraft_yaml["build-base"])
    )

    try:
        base_release = float(rock_base.split(":")[-1])
    except ValueError:
        logging.warning(
            f"Could not infer ROCK's base release from {rock_base}. Trying with codename."
        )
        base_release = float(get_release_from_codename(rock_base.split(":")[-1]))

    version = rockcraft_yaml["version"]

track = f"{version}-{base_release}"
print(f"ROCK track: {track}")

with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
    print(f"track={track}", file=gh_out)
