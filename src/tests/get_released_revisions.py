#!/usr/bin/env python3

"""Scans the OCI images directory and, for each image, looks up the currently
released revisions. For each unique revision it builds a matrix entry pointing
to the image that must be (re)scanned.

Public images are resolved against GHCR in their canonical format, i.e.:
    ghcr.io/canonical/oci-factory/<img-name>:<canonical-track>_<revision>

Pro images are private and only published to ACR. Since _pro_releases.json is
tightly tracked with the images in ACR, the released tags can be assembled
directly from the keys in that file (<track>_<risk>), so the unique image is
located as ${ACR_REGISTRY}/<img-name> together with its released tags.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import docker

from ..image.utils.schema.triggers import KNOWN_RISKS_ORDERED
from ..shared import release_info
from ..shared.logs import get_logger
from ..shared.skopeo import DEFAULT_SKOPEO_IMAGE

SKOPEO_IMAGE = os.getenv("SKOPEO_IMAGE", DEFAULT_SKOPEO_IMAGE)
REGISTRY = "ghcr.io/canonical/oci-factory"

logger = get_logger(stream=sys.stdout, level="INFO")


def get_image_name_in_registry(img_name: str, revision: str) -> str:
    """For a given revision number, search the registry for that image's tag

    :param img_name: name of the container image
    :param revision: revision number of the tag we're looking for
    """

    d_client = docker.from_env()

    revision = str(revision)
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
        if tag.rsplit("_", 1)[-1] == revision:
            return f"{tagless_image_name}:{tag}"


def _is_end_of_life(risks: dict) -> bool:
    """Whether a track (its risks dict) has reached its end of life."""
    eol = risks.get("end-of-life")
    return bool(eol and eol < datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def _active_tracks(releases: dict) -> dict:
    """Return only the tracks that have not reached their end of life."""
    active = {}
    for track, risks in releases.items():
        if _is_end_of_life(risks):
            logger.info(
                f"Skipping track {track} because it reached its end of life"
                f": {risks['end-of-life']}"
            )
            continue
        if not risks.get("end-of-life"):
            logger.warning(f"Track {track} is missing its end-of-life field")
        active[track] = risks
    return active


def get_released_public_images(img_name: str, releases: dict) -> list:
    """Build scan matrix entries for the released public revisions of an image.

    Each unique revision is resolved to its canonical GHCR tag.
    """
    images = []
    seen_revisions = set()
    for risks in _active_tracks(releases).values():
        for risk, target in risks.items():
            if risk not in KNOWN_RISKS_ORDERED:
                continue
            try:
                revision = int(target["target"])
            except ValueError:
                # this target follows another tag and is not a revision number
                continue
            if revision in seen_revisions:
                continue
            seen_revisions.add(revision)
            images.append(
                {
                    "name": img_name,
                    "source-image": get_image_name_in_registry(
                        img_name, target["target"]
                    ),
                    "revision": revision,
                    "released-tags": [],
                    "pro": False,
                    "release-file": "_releases.json",
                }
            )
    return images


def _normalize_tag(tag: str) -> str:
    """Drop the implicit `latest` track from a tag (e.g. latest_beta -> beta)."""
    track, risk = tag.rsplit("_", 1)
    return risk if track == "latest" else tag


def get_released_pro_images(img_name: str, releases: dict, acr_registry: str) -> list:
    """Build scan matrix entries for the released Pro revisions of an image.

    Pro images live only in ACR. Tags are assembled from the keys in
    _pro_releases.json and grouped by the revision they resolve to.
    """
    active = _active_tracks(releases)
    tag_mapping = release_info.get_tag_mapping_from_all_releases(active)

    revision_to_tags = defaultdict(list)
    for tag, target in tag_mapping.items():
        try:
            revision = release_info._find_alias_revision(
                tag_mapping, target, set(), tag
            )
        except (KeyError, release_info.BadChannel):
            # the tag follows another tag that is no longer released (e.g. it
            # pointed at an end-of-life track), so it cannot be pinned
            logger.warning(f"Skipping tag {tag}: unable to resolve to a revision")
            continue
        revision_to_tags[int(revision)].append(tag)

    images = []
    for revision in sorted(revision_to_tags):
        released_tags = sorted(_normalize_tag(t) for t in revision_to_tags[revision])
        images.append(
            {
                "name": img_name,
                "source-image": f"{acr_registry}/{img_name}",
                "revision": revision,
                "released-tags": released_tags,
                "pro": True,
                "release-file": "_pro_releases.json",
            }
        )
    return images


def main(argv: list = None) -> None:
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
    parser.add_argument(
        "--acr-registry",
        default="",
        help="ACR registry hosting the private Pro images",
    )

    args = parser.parse_args(argv)

    logger.info(f"Looping through OCI images in {args.oci_images_path}")

    matrix_include = []
    for img in sorted(os.listdir(args.oci_images_path)):
        public_file = f"{args.oci_images_path}/{img}/_releases.json"
        if os.path.isfile(public_file):
            with open(public_file) as rf:
                matrix_include += get_released_public_images(img, json.load(rf))

        pro_file = f"{args.oci_images_path}/{img}/_pro_releases.json"
        if os.path.isfile(pro_file):
            with open(pro_file) as rf:
                matrix_include += get_released_pro_images(
                    img, json.load(rf), args.acr_registry
                )

    logger.info(f"Released revisions to scan: {json.dumps(matrix_include, indent=2)}")

    matrix = {"include": matrix_include}
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"released-revisions-matrix={json.dumps(matrix)}", file=gh_out)


if __name__ == "__main__":
    main()
