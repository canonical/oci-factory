import argparse
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from ..shared.github_output import GithubOutput
from ..shared.logs import get_logger
from ..uploads.infer_image_track import get_base_and_track
from .utils.schema.triggers import (KNOWN_RISKS_ORDERED,
                                    ExternalCiConfigSchema,
                                    ImageTestConfigSchema)

logger = get_logger()


def load_image_trigger(image_yaml_path: Path) -> ExternalCiConfigSchema:
    """Load the image trigger YAML file and return an ExternalImageTriggerSchema object."""
    with open(image_yaml_path, encoding="UTF-8") as bf:
        image_trigger = yaml.load(bf, Loader=yaml.BaseLoader)
    _ = ExternalCiConfigSchema(**image_trigger)
    return image_trigger


def get_image_rockcraft_metadata(image_dir: Path) -> dict[str, str]:
    """Extract metadata from the rockcraft.yaml file in the image directory."""
    rockcraft_file = image_dir / "rockcraft.yaml"
    if not rockcraft_file.exists():
        raise FileNotFoundError(f"rockcraft.yaml not found in {image_dir}")

    with open(rockcraft_file, encoding="UTF-8") as f:
        rockcraft_yaml = yaml.load(f, Loader=yaml.BaseLoader)

    base, _ = get_base_and_track(rockcraft_yaml)

    return {
        "name": rockcraft_yaml.get("name", ""),
        "version": rockcraft_yaml.get("version", ""),
        "base": base,
    }


def backfill_higher_risks(risks: list[str]) -> list[str]:
    """Ensure that all risks are present in the list, filling in missing higher risks."""
    if not risks:
        return ["edge"]
    for i, risk in enumerate(KNOWN_RISKS_ORDERED):
        if risk not in risks:
            if risk == "stable":
                continue
            elif KNOWN_RISKS_ORDERED[i - 1] in risks:
                risks.append(risk)

    return sorted(risks, key=KNOWN_RISKS_ORDERED.index)


def get_all_registries(image_trigger: dict[str, Any]) -> list[dict[str, str]]:
    """Extract registry information from the image trigger."""
    registries = {}
    for registry, registry_info in image_trigger.get("registries", {}).items():
        domain, namespace = registry_info.get("uri", "").split("/", 1)
        registries[registry] = {
            "domain": domain,
            "namespace": namespace,
            "username": registry_info.get("action-secrets", {}).get("username", ""),
            "password": registry_info.get("action-secrets", {}).get("password", ""),
        }

    return registries


def artifact_name(image_metadata: dict[str, str]) -> str:
    """Generate the artifact name based on image metadata."""
    return f"{image_metadata['name']}_{image_metadata['version']}"


def upload_to_ghcr(
    image_trigger: dict[str, Any]):
    """Check if the image trigger has a configuration for uploading to GitHub Container Registry."""
    return image_trigger['ghcr']['upload']


def prepare_image_build_matrix(
    image_trigger: dict[str, Any], image_dirs_to_process: set[Path]
) -> list[dict[str, Any]]:
    builds = []

    all_registries = get_all_registries(image_trigger)
    logger.debug(f"Found registries: {get_all_registries}")

    for image in image_trigger.get("images", []):
        image_dir = Path(image["directory"])
        if image_dirs_to_process and image_dir not in image_dirs_to_process:
            continue

        if not image_dir.exists():
            raise FileNotFoundError(f"Image directory {image_dir} does not exist.")

        image_metadata = get_image_rockcraft_metadata(image_dir)

        registries = []
        for registry in image.get("registries", []):
            logger.debug(f"Processing registry: {registry}")
            registry_info = all_registries.get(registry)
            if not registry_info:
                logger.warning(
                    f"Registry {registry} not found in image trigger."
                )
                continue
            registries.append(
                {
                    "domain": registry_info["domain"],
                    "namespace": registry_info["namespace"],
                    "username": f"{registry_info['username']}",
                    "password": f"{registry_info['password']}",
                }
            )

        build = {
            "location": str(image_dir),
            "image-name": image_metadata["name"],
            "tags": f"{image_metadata['version']}-{image_metadata['base']}_edge",
            "artifact-name": artifact_name(image_metadata),
            "pro": ",".join(image.get("pro", [])),
            "registries": registries,
        }
        builds.append(build)

    return builds


def unfold_publish_matrix(builds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unfold the publish matrix to include all combinations of tags and registries."""
    unfolded_builds = []
    for build in builds:
        for registry in build["registries"]:
            unfolded_builds.append(
                {
                    "image-name": build["image-name"],
                    "tags": build["tags"],
                    "artifact-name": build["artifact-name"],
                    "domain": registry["domain"],
                    "namespace": registry["namespace"],
                    "username": registry["username"],
                    "password": registry["password"],
                }
            )
    return unfolded_builds


def main():
    parser = argparse.ArgumentParser(
        description="Prepare image build matrix and revision data for a single image."
    )
    parser.add_argument(
        "--image-trigger",
        help="Path to the image trigger file (image.yaml)",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--image-dirs",
        help="Comma-separated paths to the image directory containing rockcraft.yaml to be built.",
        type=str,
        required=False,
    )
    args = parser.parse_args()

    image_trigger = load_image_trigger(Path(args.image_trigger))

    image_dirs_to_process = (
        {Path(d) for d in args.image_dirs.split(",")} if args.image_dirs else set()
    )
    if not image_dirs_to_process:
        logger.info("Processing all image directories from the trigger.")

    builds = prepare_image_build_matrix(image_trigger, image_dirs_to_process)

    # Here you would typically call the function to prepare the build matrix
    # and write revision data, e.g.:
    # prepare_single_image_build_matrix(image_build_trigger, rockcraft_metadata)
    if not builds:
        logger.warning("No images found in the ci config.")

    logger.debug(f"Generating matrix for following builds: \n {builds}")

    with GithubOutput() as gh_output:
        gh_output.write(
            **{
                "build-matrix": {
                    "include": [
                        {k: v for k, v in build.items() if k != "registries"}
                        for build in builds
                    ]
                },
                "publish-matrix": {"include": unfold_publish_matrix(builds)},
                "upload-to-ghcr": upload_to_ghcr(image_trigger),
            }
        )


if __name__ == "__main__":
    main()
