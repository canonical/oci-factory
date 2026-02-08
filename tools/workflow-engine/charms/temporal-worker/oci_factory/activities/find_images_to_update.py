#!/usr/bin/env python3

"""
This script will take an Ubuntu release as an input.

With that, it will scan all the released rock channels in OCI Factory
and select the images which are based said Ubuntu release.

Those will be the images to be scheduled for an automatic update (aka rebuild).
"""

import argparse
import base64
import glob
import io
import json
import logging
import os
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from fnmatch import fnmatchcase

import requests
import swiftclient
import yaml


# TODO:
# - Future improvement: merge the functions below with similar code in temporal worker into its own module.
def find_released_revisions(releases_json: dict) -> list:
    """Given the contents of a _release.json file,
    find the image revision number that are currently released"""
    released_revisions = []
    for track, risks in releases_json.items():
        for risk, targets in risks.items():
            try:
                revision = int(targets["target"])
            except (ValueError, TypeError):
                # this target is following another tag and thus is not
                # a revision number
                continue

            if revision not in released_revisions:
                released_revisions.append(revision)

    return released_revisions


def trigger_triplet(trigger: dict) -> str:
    """Given a trigger, return the triplet of source, directory and commit"""
    return f"{trigger['source']}_{trigger['commit']}_{trigger['directory']}"


def trigger_image_rebuild():
    # Get the released revision numbers so we can get their build data
    # from Swift
    released_revisions = find_released_revisions(releases)
    logging.info(
        f"Currently, the released revisions for {image} are: {released_revisions}"
    )

    # This is the metadata file we want to get from Swift
    # match objects with name <IMAGE_NAME>/<TRACK>/<REVISION>/build_metadata.json
    img_objs = list(
        filter(
            lambda o: fnmatchcase(o["name"], f"{image}/*/*/build_metadata.json"),
            swift_oci_factory_objs,
        )
    )

    # Sort the objects by revision number
    img_objs.sort(key=lambda o: int(o["name"].split("/")[2]))

    # If this image's build metadata isn't yet in Swift, continue
    if not img_objs:
        logging.warning(f"There's no build data for {image} in Swift yet!")
        return

    # Let's use an uber image trigger file to trigger the CI rebuilds
    uber_img_trigger = {"version": 2, "upload": []}
    uploads = {}  # key: trigger triplet, value: uber_image_trigger["upload"] entry
    # We'll also need to find which tags (channels) to release the new
    # rebuilds to
    # TODO: Get rid of this once we have a proper DB where to store all the
    # image information.
    # This is a bit nasty as these APIs return paginated results
    # and don't offer enough querying parameters to filter the results.
    ecr_tags_url = "https://api.us-east-1.gallery.ecr.aws/describeImageTags"
    body = {"repositoryName": image, "maxResults": 1000}
    if image.startswith("mock-"):
        body["registryAliasName"] = "rocksdev"
    else:
        body["registryAliasName"] = "ubuntu"
    tags = json.loads(requests.post(ecr_tags_url, json=body).content.decode())
    # Each Swift object corresponds to an image revision (<=> build)
    for image_revision in img_objs:
        _, _, revision, _ = image_revision["name"].split("/")
        if int(revision) not in released_revisions:
            continue

        try:
            _, build_metadata_raw = swift_conn.get_object(
                SWIFT_CONTAINER, image_revision["name"]
            )
        except swiftclient.exceptions.ClientException:
            logging.exception(f"Unable to get {image_revision['name']} from Swift")
            continue

        build_metadata = json.loads(build_metadata_raw.decode())
        base = build_metadata.get("base")
        revision_digest = build_metadata["digest"]
        revision_info = str(
            f"{image} | revision: {revision} "
            f"| base: {base} | digest: {revision_digest}"
        )

        if ubuntu_release == "*" or base[-5:] == ubuntu_release[-5:]:
            logging.info(f"MATCH - {revision_info}")
        else:
            logging.info(f"NOMATCH - {revision_info}")
            continue

        logging.info(f"{image}: marking revision {revision} for a rebuild")

        # If we go here, then we can start building the uber image trigger
        build_and_upload_data = {
            "source": build_metadata["source"],
            "commit": build_metadata["commit"],
            "directory": build_metadata["directory"],
            "ignored-vulnerabilities": build_metadata.get(
                "ignored-vulnerabilities", ""
            ).split(),
        }
        release_to = {}
        imageTagDetails = tags.get("imageTagDetails", {})
        if not imageTagDetails:
            logging.warning(
                f"{tags.get('message', 'Image tags not found in registry')}. Skip!"
            )
            continue

        tags_matched = False
        for tag in imageTagDetails:
            if tag["imageDetail"].get("imageDigest") != revision_digest:
                continue
            tags_matched = True

            if tag["imageTag"] in ["edge", "beta", "candidate", "stable"]:
                to_track = "latest"
                to_risk = tag["imageTag"]
            else:
                try:
                    to_track, to_risk = tag["imageTag"].rsplit("_", 1)
                except ValueError as err:
                    if "not enough values to unpack" in str(err):
                        # These cases are driven by the <track> alias which
                        # is created for tags like <track>_stable
                        to_track = tag["imageTag"]
                        to_risk = "stable"
                    else:
                        logging.exception(f"Unrecognized tag {tag['imageTag']}")
                        continue

            if releases[to_track].get("end-of-life"):
                if releases[to_track]["end-of-life"] < datetime.now(
                    timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"):
                    logging.info(
                        f"Skipping track {to_track} because it reached its "
                        f"end of life: {releases[to_track]['end-of-life']}"
                    )
                    continue
                else:
                    if to_track not in release_to:
                        release_to[str(to_track)] = {"risks": [to_risk]}
                    else:
                        release_to[to_track]["risks"].append(to_risk)
                    release_to[to_track]["end-of-life"] = releases[to_track][
                        "end-of-life"
                    ]
            else:
                logging.warning(f"Track {to_track} is missing its end-of-" "life field")

        if not tags_matched:
            logging.warning(
                f"Unable to find a tag for {image} revision {revision} in ECR"
            )
            continue

        triplet = trigger_triplet(build_and_upload_data)

        if triplet in uploads:
            # Since img_objs is sorted by revision number, we can safely
            # assume "release_to" is always newer than uploads[triplet]["release"]
            # and therefore we can merge them with "release_to" overwriting
            # the duplicated entries.
            uploads[triplet]["release"] = (
                uploads[triplet].get("release", {}) | release_to
            )
        else:
            if release_to:
                build_and_upload_data["release"] = release_to
                uploads[triplet] = build_and_upload_data

    uber_img_trigger["upload"] = [trigger for trigger in uploads.values()]

    if not uber_img_trigger["upload"]:
        logging.info(f"{image}: skipping revision {revision}, nothing to rebuild")
        # Nothing to rebuild here
        return

    uber_img_trigger_yaml = yaml.safe_dump(
        uber_img_trigger, default_style=None, default_flow_style=False
    )
    logging.info(f"About to rebuild {image} with the trigger:\n{uber_img_trigger_yaml}")

    uber_img_trigger_b64 = base64.b64encode(uber_img_trigger_yaml.encode())

    # Let's trigger the rebuild
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    inputs = {
        "ref": "main",
        "inputs": {
            "oci-image-name": image,
            "b64-image-trigger": uber_img_trigger_b64.decode(),
            "upload": True,
            "external_ref_id": f"{external_ref_id_prefix}-{image}-{int(time.time())}",
        },
    }
    wf_dispatch_url = str(
        "https://api.github.com/repos/"
        "canonical/oci-factory/"
        "actions/workflows/Image.yaml/dispatches"
    )

    dispatch = requests.post(wf_dispatch_url, headers=headers, json=inputs)
    try:
        dispatch.raise_for_status()
    except Exception as err:
        logging.exception(f"Failed to rebuild {image}: {str(err)}")
        return

    logging.info(f"Dispatched image rebuild workflow for {image}")
    time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    parser = argparse.ArgumentParser(description="Find images to update in OCI Factory")
    parser.add_argument(
        "ubuntu_release",
        help="The Ubuntu release to check for images to update",
        nargs="?",
        default="*",
    )
    parser.add_argument(
        "--image-name",
        help="The image name to check for updates",
        default="*",
    )
    parser.add_argument(
        "--ext-ref-prefix",
        help="The prefix to use for the external reference ID",
        default="workflow-engine",
    )
    args = parser.parse_args()
    ubuntu_release = args.ubuntu_release
    image = args.image_name
    external_ref_id_prefix = args.ext_ref_prefix

    logging.info(f"Checking for image {image} to update for release {ubuntu_release}")

    # Make sure we can connect to Swift
    swift_conn = swiftclient.client.Connection(
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
    # Check the connection: get all objects from the 'oci-factory' Swift container
    SWIFT_CONTAINER = "oci-factory"
    prefix = None
    if image != "*":
        prefix = f"{image}/"

    _, swift_oci_factory_objs = swift_conn.get_container(
        SWIFT_CONTAINER, prefix=prefix, full_listing=True
    )

    # Need the ROCKsBot GitHub token in order to dispatch workflows
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

    # We download the OCI Factory repo as a zip
    oci_factory_gh_url = (
        "https://github.com/canonical/oci-factory/archive/refs/heads/_releases.zip"
    )
    # Download and extract the repo to the tmp folder
    logging.info(f"Downloading {oci_factory_gh_url}")
    repo_zip = requests.get(oci_factory_gh_url, stream=True)
    zf = zipfile.ZipFile(io.BytesIO(repo_zip.content))

    with tempfile.TemporaryDirectory() as temp_dir:
        zf.extractall(temp_dir)

        # Get the extracted repo's path
        repo = glob.glob(str(temp_dir).rstrip("/") + "/*")[0].rstrip("/")
        logging.info(f"Extracted OCI Factory repo to {repo}")
        oci_imgs_path = repo + "/oci"

        images_to_check = os.listdir(oci_imgs_path) if image == "*" else [image]

        for image in images_to_check:
            logging.info(
                f"#### Checking if {image} depends on release {ubuntu_release}"
            )
            try:
                # Check what is currently released for this image
                with open(f"{oci_imgs_path}/{image}/_releases.json") as rel:
                    releases = json.load(rel)
            except FileNotFoundError:
                logging.info(f"{image} has not been released yet. Continuing...")
                continue

            trigger_image_rebuild()
