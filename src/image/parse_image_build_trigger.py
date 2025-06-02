import argparse
from pathlib import Path
from typing import Any

import yaml

from ..shared.github_output import GithubOutput
from ..shared.logs import get_logger
from ..uploads.infer_image_track import get_base_and_track
from .prepare_single_image_build_matrix import validate_image_trigger
from .utils.schema.triggers import KNOWN_RISKS_ORDERED, ImageSchema

logger = get_logger()


def load_image_trigger(image_yaml_path: Path) -> ImageSchema:
    """Load the image trigger YAML file and return an ImageSchema object."""
    with open(image_yaml_path, encoding="UTF-8") as bf:
        image_trigger = yaml.load(bf, Loader=yaml.BaseLoader)
    validate_image_trigger(image_trigger)
    assert "build" in image_trigger, "Image trigger must contain 'build' key"
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

    return sorted(risks, key=lambda x: KNOWN_RISKS_ORDERED.index(x))


def prepare_image_build_matrix(image_trigger: ImageSchema, image_dirs_to_process: set[Path]) -> list[dict[str, Any]]:
    builds = []

    for image in image_trigger.get("build", []):
        image_dir = Path(image["directory"])
        print(image_dirs_to_process)
        print(image_dir)
        if image_dirs_to_process and image_dir not in image_dirs_to_process:
            continue

        if not image_dir.exists():
            raise FileNotFoundError(f"Image directory {image_dir} does not exist.")

        image_metadata = get_image_rockcraft_metadata(image_dir)

        build = {
            "location": str(image_dir),
            "name": image_metadata["name"],
            "tag": image["tag"],
            "pro": ",".join(image.get("pro", [])),
            "repositories": image.get("deploy", {}).get("repositories", []),
            "risks": backfill_higher_risks(image.get("deploy", {}).get("risks", [])),
        }
        builds.append(build)

    return builds

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
        "--image-dir",
        help="Path to the image directory containing rockcraft.yaml to be build."
        " With same format of `directory` in image triggers. Can be called multiple times.",
        action="append",
        default=[],
    )
    args = parser.parse_args()

    image_trigger = load_image_trigger(Path(args.image_trigger))

    image_dirs_to_process = {Path(d) for d in args.image_dir}
    if not image_dirs_to_process:
        logger.info("Processing all image directories from the trigger.")

    builds = prepare_image_build_matrix(
        image_trigger, image_dirs_to_process
    )

        # Here you would typically call the function to prepare the build matrix
        # and write revision data, e.g.:
        # prepare_single_image_build_matrix(image_build_trigger, rockcraft_metadata)
    if not builds:
        logger.warning("No builds found in the image trigger.")

    build_matrix = {"include": builds}

    with GithubOutput() as gh_output:
        gh_output.write("build-matrix", build_matrix)


if __name__ == "__main__":
    main()
