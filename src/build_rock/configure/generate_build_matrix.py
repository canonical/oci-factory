#!/usr/bin/env python3

import yaml
import os
import argparse
import json
from enum import Enum
from ...shared.github_output import GithubOutput
from pydantic import TypeAdapter


class MATRIX_NAMES(Enum):
    RUNNER = "runner-build-matrix"
    LPCI = "lpci-build-matrix"


class MissingArchSupport(Exception):
    pass


def get_target_archs(rockcraft: dict) -> list:
    """get list of target architectures from rockcraft project definition"""

    rock_platforms = rockcraft["platforms"]

    target_archs = set()

    for platf, values in rock_platforms.items():

        if isinstance(values, dict) and "build-for" in values:
            if isinstance(arches := values["build-for"], list):
                target_archs.update(arches)
            elif isinstance(values, str):
                target_archs.add(arches)
        else:
            target_archs.add(platf)

    return target_archs


def configure_matrices(target_archs: list, arch_map: dict, lp_fallback: bool) -> dict:
    """Sort build into appropriate build matrices"""

    # map configuration to individual job matrices
    build_matrices = {name.value: {"include": []} for name in MATRIX_NAMES}

    # Check if we have runners for all supported architectures
    if missing_archs := set(target_archs) - set(arch_map):

        # raise exception if we cannot fallback to LP builds
        if not lp_fallback:
            raise MissingArchSupport(
                f"Missing support for runner arches: {missing_archs}"
            )

        # configure LP build
        build_matrices[MATRIX_NAMES.LPCI.value]["include"].append(
            {"architecture": "-".join(set(target_archs))}
        )

    else:
        # configure runner matrix for list of supported runners
        for runner_arch, runner_name in arch_map.items():
            if runner_arch in target_archs:
                build_matrices[MATRIX_NAMES.RUNNER.value]["include"].append(
                    {"architecture": runner_arch, "runner": runner_name}
                )

    return build_matrices


def set_build_config_outputs(rock_name: str, build_matrices: dict):
    """Update GITHUB_OUTPUT with build configuration."""

    outputs = {"rock-name": rock_name, **build_matrices}

    with GithubOutput() as github_output:
        github_output.write(**outputs)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--rockfile-directory",
        help="Path where to directory containing rockcraft.yaml.",
        required=True,
    )

    parser.add_argument(
        "--lpci-fallback",
        help="Revert to lpci if architectures are not supported. <true|false>",
        required=True,
        type=TypeAdapter(bool).validate_python,
    )

    parser.add_argument(
        "--config",
        help="JSON mapping arch to runner for matrix generation.",
        required=True,
    )

    args = parser.parse_args()

    # get configuration form rockcraft yaml
    with open(f"{args.rockfile_directory}/rockcraft.yaml") as rf:
        rockcraft_yaml = yaml.safe_load(rf)

    # load config
    arch_map = json.loads(args.config)

    target_archs = get_target_archs(rockcraft_yaml)
    build_matrices = configure_matrices(target_archs, arch_map, args.lpci_fallback)

    # set github outputs for use in later steps
    set_build_config_outputs(rockcraft_yaml["name"], build_matrices)


if __name__ == "__main__":
    main()
