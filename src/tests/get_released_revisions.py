#!/usr/bin/env python3

"""Scans the OCI images directory, and for each one, looks up the currently
released revision numbers. From that number, it queries GHCR in order to
form and return a list of image names in their canonical format, i.e.:
    ghcr.io/canonical/oci-factory/<img-name>:<canonical-track>_<revision>
    ...

TODO: this script could eventually be adjusted and converted to a Temporal
Activity that runs from within a scheduled workflow.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import docker

from ..shared.logs import get_logger

SKOPEO_IMAGE = os.getenv("SKOPEO_IMAGE", "quay.io/skopeo/stable:v1.20.0")
REGISTRY = "ghcr.io/canonical/oci-factory"

logger = get_logger(stream=sys.stdout, level="INFO")


def get_image_name_in_registry(img_name: str, revision: str) -> str:
    """For a given revision number, search the registry for that image's tag

    :param img_name: name of the container image
    :param revision: revision number of the tag we're looking for
    """

    d_client = docker.from_env()

    tagless_image_name = f"{REGISTRY}/{img_name}"
    cmd = f"list-tags docker://{tagless_image_name}"
    logger.info(f"Running Skopeo with '{cmd}'")
    try:
        all_tags = json.loads(
            d_client.containers.run(
                SKOPEO_IMAGE,
                command=cmd,
                remove=True,
            ).strip()
        )["Tags"]
    except docker.errors.ContainerError as err:
        if "timeout" not in str(err):
            raise
        logger.error(
            f"Timed out while listing tags for {tagless_image_name}: {str(err)}"
        )

    for tag in all_tags:
        if tag.endswith(revision):
            return f"{tagless_image_name}:{tag}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=str(
            "Goes through all the OCI images and "
            "gets the revision tags for the released images"
        )
    )
    parser.add_argument(
        "--oci-images-path",
        required=True,
        help="absolute path to the OCI folder where all images are",
    )

    args = parser.parse_args()

    logger.info(f"Looping through OCI images in {args.oci_images_path}")

    released_revisions = {}
    ghcr_images = []
    for img in os.listdir(args.oci_images_path):
        _releases_file = f"{args.oci_images_path}/{img}/_releases.json"
        if not os.path.isfile(_releases_file):
            continue

        with open(_releases_file) as rf:
            releases = json.load(rf)

        released_revisions[img] = []
        for track, risks in releases.items():
            if risks.get("end-of-life") and risks["end-of-life"] < datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"):
                logger.info(
                    f"Skipping track {track} because it reached its end of life"
                    f": {risks['end-of-life']}"
                )
                continue
            elif not risks.get("end-of-life"):
                logger.warning(f"Track {track} is missing its end-of-life field")

            for key, targets in risks.items():
                if key == "end-of-life":
                    continue
                try:
                    if int(targets["target"]) in released_revisions[img]:
                        continue
                except ValueError:
                    # this target is following another tag and thus is not
                    # a revision number
                    continue

                released_revisions[img].append(int(targets["target"]))
                ghcr_images.append(
                    {
                        "name": img,
                        "source-image": get_image_name_in_registry(
                            img, targets["target"]
                        ),
                    }
                )

    logger.info(f"Released revisions: {json.dumps(released_revisions, indent=2)}")
    logger.info(f"Released revisions in GHCR: {ghcr_images}")

    matrix = {"include": ghcr_images}
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"released-revisions-matrix={matrix}", file=gh_out)
