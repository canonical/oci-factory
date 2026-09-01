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

For both kinds of image, the v2 'ignored-vulnerabilities' are recovered from
the build metadata that the build workflow persists in Swift.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from fnmatch import fnmatchcase

import docker
import swiftclient

from ..image.utils.schema.triggers import KNOWN_RISKS_ORDERED
from ..shared import release_info
from ..shared.logs import get_logger
from ..shared.skopeo import DEFAULT_SKOPEO_IMAGE

SKOPEO_IMAGE = os.getenv("SKOPEO_IMAGE", DEFAULT_SKOPEO_IMAGE)
REGISTRY = "ghcr.io/canonical/oci-factory"
SWIFT_CONTAINER = os.getenv("SWIFT_CONTAINER_NAME", "oci-factory")

logger = get_logger(stream=sys.stdout, level="INFO")


def get_swift_connection() -> swiftclient.client.Connection:
    """Open a connection to the Swift object storage holding the build metadata."""
    return swiftclient.client.Connection(
        authurl=os.environ["OS_AUTH_URL"],
        user=os.environ["OS_USERNAME"],
        key=os.environ["OS_PASSWORD"],
        os_options={
            "user_domain_name": os.getenv("OS_USER_DOMAIN_NAME", "Default"),
            "project_domain_name": os.getenv("OS_PROJECT_DOMAIN_NAME", "Default"),
            "project_name": os.environ["OS_PROJECT_NAME"],
            "object_storage_url": os.environ["OS_STORAGE_URL"],
        },
        auth_version=os.getenv("OS_IDENTITY_API_VERSION", "3"),
    )


def get_ignored_vulnerabilities(
    swift_conn: swiftclient.client.Connection,
    swift_objs: list,
    img_name: str,
    revision: str | int,
) -> str:
    """Read the space-separated 'ignored-vulnerabilities' string for a given
    image revision from its build_metadata.json in Swift.

    Revisions are globally unique per image, so we match the build metadata
    object regardless of the track it was built under, i.e.:
        <img-name>/<track>/<revision>/build_metadata.json

    :param swift_conn: an open connection to Swift
    :param swift_objs: the listing of objects in the Swift container
    :param img_name: name of the container image
    :param revision: revision number of the image to look up
    """
    matches = [
        obj
        for obj in swift_objs
        if fnmatchcase(obj["name"], f"{img_name}/*/{revision}/build_metadata.json")
    ]
    if not matches:
        logger.warning(
            f"No build metadata in Swift for {img_name} revision {revision}; "
            "assuming no ignored vulnerabilities"
        )
        return ""

    try:
        _, build_metadata_raw = swift_conn.get_object(
            SWIFT_CONTAINER, matches[0]["name"]
        )
    except swiftclient.exceptions.ClientException:
        logger.exception(f"Unable to get {matches[0]['name']} from Swift")
        return ""

    build_metadata = json.loads(build_metadata_raw.decode())
    return build_metadata.get("ignored-vulnerabilities", "") or ""


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


def get_released_public_images(
    img_name: str,
    releases: dict,
    swift_conn: swiftclient.client.Connection,
    swift_objs: list,
) -> list:
    """Build scan matrix entries for the released public revisions of an image.

    Each unique revision is resolved to its canonical GHCR tag.

    :param img_name: name of the container image
    :param releases: the contents of the image's _releases.json
    :param swift_conn: an open connection to Swift, for the build metadata
    :param swift_objs: the listing of objects in the Swift container
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
                    "ignored-vulnerabilities": get_ignored_vulnerabilities(
                        swift_conn, swift_objs, img_name, revision
                    ),
                }
            )
    return images


def _normalize_tag(tag: str) -> str:
    """Drop the implicit `latest` track from a tag (e.g. latest_beta -> beta)."""
    track, risk = tag.rsplit("_", 1)
    return risk if track == "latest" else tag


def get_released_pro_images(
    img_name: str,
    releases: dict,
    acr_registry: str,
    swift_conn: swiftclient.client.Connection,
    swift_objs: list,
) -> list:
    """Build scan matrix entries for the released Pro revisions of an image.

    Pro images live only in ACR. Tags are assembled from the keys in
    _pro_releases.json and grouped by the revision they resolve to.

    :param img_name: name of the container image
    :param releases: the contents of the image's _pro_releases.json
    :param acr_registry: ACR registry hosting the private Pro images
    :param swift_conn: an open connection to Swift, for the build metadata
    :param swift_objs: the listing of objects in the Swift container
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
                "ignored-vulnerabilities": get_ignored_vulnerabilities(
                    swift_conn, swift_objs, img_name, revision
                ),
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

    # We need the build metadata (stored in Swift) to recover the v2
    # 'ignored-vulnerabilities' for each released revision.
    swift_conn = get_swift_connection()
    _, swift_objs = swift_conn.get_container(SWIFT_CONTAINER, full_listing=True)

    matrix_include = []
    for img in sorted(os.listdir(args.oci_images_path)):
        public_file = f"{args.oci_images_path}/{img}/_releases.json"
        if os.path.isfile(public_file):
            with open(public_file) as rf:
                matrix_include += get_released_public_images(
                    img, json.load(rf), swift_conn, swift_objs
                )

        pro_file = f"{args.oci_images_path}/{img}/_pro_releases.json"
        if os.path.isfile(pro_file):
            with open(pro_file) as rf:
                matrix_include += get_released_pro_images(
                    img, json.load(rf), args.acr_registry, swift_conn, swift_objs
                )

    logger.info(f"Released revisions to scan: {json.dumps(matrix_include, indent=2)}")

    matrix = {"include": matrix_include}
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"released-revisions-matrix={json.dumps(matrix)}", file=gh_out)


if __name__ == "__main__":
    main()
