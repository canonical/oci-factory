#!/usr/bin/env python3

"""
This script will take an Ubuntu release as an input.

With that, it will scan all the released ROCK channels in OCI Factory
and select the images which are based said Ubuntu release.

Those will be the images to be scheduled for an automatic update (aka rebuild).
"""

import base64
import glob
import io
import json
import logging
import os
import requests
import swiftclient
import sys
import tempfile
import time
import yaml
import zipfile


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
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
_, swift_oci_factory_objs = swift_conn.get_container(SWIFT_CONTAINER)

# Need the ROCKsBot GitHub token in order to dispatch workflows
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


def find_released_revisions(releases_json: dict) -> dict:
    """Given the contents of a _release.json file,
    find the image revision number that are currently released"""
    released_revisions = []
    for track, risks in releases_json.items():
        for risk, targets in risks.items():
            try:
                revision = int(targets["target"])
            except ValueError:
                # this target is following another tag and thus is not
                # a revision number
                continue

            if revision not in released_revisions:
                released_revisions.append(revision)

    return released_revisions


# Get the new Ubuntu release from the CLI args
ubuntu_release = str(sys.argv[1])
logging.info(f"Ubuntu release: {ubuntu_release}")

# We download the OCI Factory repo as a zip
oci_factory_gh_url = (
    "https://github.com/canonical/oci-factory/archive/refs/heads/main.zip"
)
# Download and extract the repo to the tmp folder
logging.info(f"Downloading {oci_factory_gh_url}")
repo_zip = requests.get(oci_factory_gh_url, stream=True)
z = zipfile.ZipFile(io.BytesIO(repo_zip.content))

with tempfile.TemporaryDirectory() as temp_dir:
    z.extractall(temp_dir)

    # Get the extracted repo's path
    repo = glob.glob(str(temp_dir).rstrip("/") + "/*")[0].rstrip("/")
    logging.info(f"Extrated OCI Factory repo to {repo}")
    oci_imgs_path = repo + "/oci"
    for image in os.listdir(oci_imgs_path):
        logging.info(f"#### Checking if {image} depends on {ubuntu_release}")
        try:
            # Check what is currently released for this image
            with open(f"{oci_imgs_path}/{image}/_releases.json") as rel:
                releases = json.load(rel)
        except FileNotFoundError:
            logging.info(f"{image} has not been released yet. Continuing...")
            continue

        # Get the released revision numbers so we can get their build data
        # from Swift
        released_revisions = find_released_revisions(releases)
        logging.info(
            f"Currently, the released revisions for {image} are: {released_revisions}"
        )

        # This is the metadata file we want to get from Swift
        build_metadata_file = "build_metadata.json"
        img_objs = list(
            filter(
                lambda o: o["name"].startswith(image)
                and o["name"].endswith(build_metadata_file),
                swift_oci_factory_objs,
            )
        )

        # If this image's build metadata isn't yet in Swift, continue
        if not img_objs:
            logging.warning(f"There's no build data for {image} in Swift yet!")
            continue

        # Let's use an uber image trigger file to trigger the CI rebuilds
        uber_img_trigger = {"version": 1, "upload": []}
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
            if base[-5:] == ubuntu_release[-5:]:
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
            }
            release_to = {}
            for tag in tags["imageTagDetails"]:
                if tag["imageDetail"].get("imageDigest") != revision_digest:
                    continue
                try:
                    to_track, to_risk = tag["imageTag"].rsplit("_", 1)
                except ValueError as err:
                    if "not enough values to unpack" in str(err):
                        to_track = "latest"
                        to_risk = tag["imageTag"]
                    else:
                        logging.exception(f"Unrecognized tag {tag['imageTag']}")
                        continue

                if to_track not in release_to:
                    release_to[str(to_track)] = {"risks": [to_risk]}
                else:
                    release_to[to_track]["risks"].append(to_risk)

            if release_to:
                build_and_upload_data["release"] = release_to

            uber_img_trigger["upload"].append(build_and_upload_data)

        if not uber_img_trigger["upload"]:
            # Nothing to rebuild here
            continue

        uber_img_trigger_yaml = yaml.safe_dump(
            uber_img_trigger, default_style=None, default_flow_style=False
        )
        logging.info(
            f"About to rebuild {image} with the trigger:\n{uber_img_trigger_yaml}"
        )

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
                "external_ref_id": f"workflow-engine-{image}-{int(time.time())}",
            },
        }
        wf_dispatch_url = str(
            "https://api.github.com/repos/"
            "canonical/oci-factory/"
            "actions/workflows/Image.yaml/dispatches"
        )

        # TODO: remove test condition
        if image == "mock-rock":
            dispatch = requests.post(wf_dispatch_url, headers=headers, json=inputs)
            try:
                dispatch.raise_for_status()
            except Exception as err:
                logging.exception(f"Failed to rebuild {image}: {str(err)}")
                continue

            logging.info(f"Dispatched image rebuild workflow for {image}")
