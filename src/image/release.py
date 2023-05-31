#!/usr/bin/env python3

"""
Takes a releases trigger file and created a mapping of all the
OCI tags that are marked to be release.
"""

import argparse
import json
import os
import src.shared.functions as shared

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-trigger",
        help="Path to the image trigger file.",
        required=True,
    )
    parser.add_argument(
        "--image-name",
        help="Image name. Will infer from --image-trigger if not provided.",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--all-releases",
        help="Path to the _releases.json file.",
        required=True,
    )
    parser.add_argument(
        "--all-revision-tags",
        help="File w/ comma-separated list of all revision (<track>_<rev>) tags.",
        required=True,
    )
    parser.add_argument(
        "--ghcr-repo",
        help="GHCR repo where the image was originally uploaded.",
        required=True,
    )

    args = parser.parse_args()

    img_name = (
        args.image_name
        if args.image_name
        else os.path.abspath(args.image_trigger).split("/")[-2]
    )

    print(f"Preparing to release revision tags for {img_name}")
    all_revision_tags = shared.get_all_revision_tags(args.all_revision_tags)
    revision_to_track = shared.get_revision_to_track(all_revision_tags)
    print(
        "Revision (aka 'canonical') tags grouped by revision:\n"
        f"{json.dumps(revision_to_track, indent=2)}"
    )
    print(f"Reading all previous releases from {args.all_releases}...")
    all_releases = shared.get_all_releases(args.all_releases)
    tag_mapping_from_all_releases = shared.get_tag_mapping_from_all_releases(
        all_releases
    )
    print(f"Parsing image trigger {args.image_trigger}")
    image_trigger = shared.get_image_trigger(args.image_trigger)
    tag_mapping_from_trigger, all_releases = shared.get_tag_mapping_from_trigger(
        image_trigger, all_releases
    )
    print(
        "Going to update channels according to the following:\n"
        f"{json.dumps(tag_mapping_from_trigger, indent=2)}"
    )

    # combine all tags
    all_tags_mapping = {
        **tag_mapping_from_all_releases,
        **tag_mapping_from_trigger,
    }
    tag_to_revision = shared.get_tag_to_revision(
        tag_mapping_from_trigger, all_tags_mapping, revision_to_track
    )
    release_tags = shared.get_releases_tags(tag_to_revision)
    group_by_revision = shared.get_group_by_revision(release_tags)
    print(
        "Processed tag aliases and ready to release the following revisions:\n"
        f"{json.dumps(group_by_revision, indent=2)}"
    )
    this_dir = os.path.dirname(__file__)
    shared.upload_image(
        group_by_revision, revision_to_track, args.ghcr_repo, img_name, this_dir
    )
    print(
        f"Updating {args.all_releases} file with:\n"
        f"{json.dumps(all_releases, indent=2)}"
    )

    shared.write_release_to_file(args.all_releases, all_releases)