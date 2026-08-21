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
from fnmatch import fnmatchcase

import docker
import swiftclient

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
    revision: str,
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

    # We need the build metadata (stored in Swift) to recover the v2
    # 'ignored-vulnerabilities' for each released revision.
    swift_conn = get_swift_connection()
    _, swift_objs = swift_conn.get_container(SWIFT_CONTAINER, full_listing=True)

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
                        "ignored-vulnerabilities": get_ignored_vulnerabilities(
                            swift_conn, swift_objs, img, targets["target"]
                        ),
                    }
                )

    logger.info(f"Released revisions: {json.dumps(released_revisions, indent=2)}")
    logger.info(f"Released revisions in GHCR: {ghcr_images}")

    matrix = {"include": ghcr_images}
    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
        print(f"released-revisions-matrix={matrix}", file=gh_out)
