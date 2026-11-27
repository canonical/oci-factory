#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
from functools import cache
from urllib.request import urlopen

import yaml

from ..shared.logs import get_logger
from ..shared.rockcraft_recipe_metadata import get_builder_archs

logger = get_logger()

BUILDD_DAILY_FEED = (
    "https://cloud-images.ubuntu.com/buildd/daily/streams/v1/"
    "com.ubuntu.cloud:daily:download.json"
)


@cache
def get_devel_release(arches: frozenset[str]) -> str:
    """Resolve Rockcraft's buildd daily devel alias across architectures."""
    with urlopen(BUILDD_DAILY_FEED, timeout=30) as response:
        products = json.load(response)["products"]

    # Filter products to find the devel release for the specified architectures
    # We expect exactly one devel release for the given architectures
    releases = {
        product["version"]
        for product in products.values()
        if "devel" in product.get("aliases", "").split(",")
        and product["arch"] in arches
    }
    if len(releases) != 1:
        raise ValueError(f"buildd devel release has mixed versions: {sorted(releases)}")
    return releases.pop()


def get_release_from_codename(codename: str) -> str:
    """Uses distro-info tools to infer the Ubuntu release from its codename."""
    all_releases = subprocess.check_output(
        ["ubuntu-distro-info", "--fullname", "--all"], universal_newlines=True
    ).splitlines()

    return list(filter(lambda x: codename.lower() in x.lower(), all_releases))[
        0
    ].split()[1]


def get_base_and_track(
    rockcraft_yaml, declared_tracks: list[str] | None = None
) -> tuple[str, str]:
    rock_base = (
        rockcraft_yaml["base"]
        if rockcraft_yaml["base"] != "bare"
        else rockcraft_yaml["build-base"]
    )

    if rock_base == "devel":
        builder_arches = frozenset(get_builder_archs(rockcraft_yaml))
        rock_base = get_devel_release(builder_arches)

    try:
        base_release = float(rock_base.replace(":", "@").split("@")[-1])
    except ValueError:
        logger.warning(
            f"Could not infer ROCK's base release from {rock_base}. Trying with codename."
        )
        base_release = float(
            get_release_from_codename(rock_base.replace(":", "@").split("@")[-1])
        )

    version = rockcraft_yaml["version"]
    track = f"{version}-{base_release:.2f}"

    # devel moves on every ubuntu release, so a recipe still on it can silently
    # build for a different release than the tracks it is published to.
    if rockcraft_yaml.get("build-base") == "devel":
        stale = [
            t for t in declared_tracks or [] if t.rsplit("-", 1)[-1] != f"{base_release:.2f}"
        ]
        if stale:
            raise ValueError(
                f"build-base devel now resolves to ubuntu {base_release:.2f}, but the "
                f"image is released to {sorted(stale)}. pin build-base in "
                "rockcraft.yaml to the intended ubuntu release."
            )

    return f"{base_release:.2f}", track


if __name__ == "__main__":
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
        rockcraft_yaml = yaml.load(rockcraft_file, Loader=yaml.BaseLoader)

    base_release, track = get_base_and_track(rockcraft_yaml)

    logger.info(f"rock track: {track}")

    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"track={track}", file=gh_out)
        print(f"base=ubuntu:{base_release}", file=gh_out)
