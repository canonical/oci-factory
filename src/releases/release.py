#!/usr/bin/env python3

"""
Takes a releases trigger file and created a mapping of all the
OCI tags that are marked to be release.
"""

import argparse
import json
import os
import re
import subprocess

from collections import defaultdict
from utils import utils, schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--releases-trigger",
        help="Path to the releases trigger file.",
        required=True,
    )
    parser.add_argument(
        "--image-name",
        help="Image name. Will infer from --releases-trigger if not provided.",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--all-released-tags",
        help="Path to the _tags.json file.",
        required=True,
    )
    parser.add_argument(
        "--all-revision-tags",
        help="Comma-separated list of all revision (<track>_<revision>) tags for this image.",
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
        else os.path.abspath(args.releases_trigger).split("/")[-2]
    )

    print(
        f"Preparing to release revision tags for {img_name}:\n{args.all_revision_tags}"
    )
    all_revision_tags = args.all_revision_tags.rstrip(",").lstrip(",").split(",")
    revision_to_track = {}
    for track_revision in all_revision_tags:
        track, revision = track_revision.split("_")
        if revision in revision_to_track:
            msg = (
                "Each revision can only have 1 canonical tag, "
                f"but revision {revision} is associated with tracks "
                f"{track} and {revision_to_track['revision']}!"
            )
            raise utils.BadChannel(msg)

        revision_to_track[int(revision)] = track

    print(
        f"Revision tags grouped by revision:\n{json.dumps(revision_to_track, indent=2)}"
    )
    utils.assert_releases_trigger_filename(args.releases_trigger)

    print(f"Parsing releases trigger {args.releases_trigger}")
    curr_releases = utils.parse_releases_trigger(args.releases_trigger)

    tag_mapping_from_trigger = {}
    for track, risks in curr_releases.channels.items():
        for risk, value in risks.dict(exclude_none=True).items():
            if risk not in schema.triggers.KNOWN_RISKS_ORDERED:
                print(f"Skipping unkown risk {risk} in track {track}")
                continue

            tag = f"{track}_{risk}"
            print(f"Channel {tag} points to {value}")
            tag_mapping_from_trigger[tag] = value

    print(f"Reading all existing tag mappings from {args.all_released_tags}...")
    try:
        with open(args.all_released_tags) as all_released_tags_fd:
            all_released_tags = json.load(all_released_tags_fd)

        # map the existing tags into a structure similar to tag_mapping_from_trigger
        tag_mapping_from_all_released_tags = {
            t: all_released_tags[t]["revision"] for t in all_released_tags
        }
    except FileNotFoundError:
        all_released_tags = {}
        tag_mapping_from_all_released_tags = {}

    # combine all tags
    all_tags_mapping = {
        **tag_mapping_from_all_released_tags,
        **tag_mapping_from_trigger,
    }

    tag_to_revision = tag_mapping_from_trigger.copy()
    for tag, value in tag_mapping_from_trigger.items():
        # assert for channels that are following other channels that don't exist
        if value == tag:
            msg = f"A tag cannot follow itself ({value})"
            raise utils.BadChannel(msg)

        # we need to map tags to a revision number,
        # even those that point to other tags
        follow_tag = value
        followed_tags = []
        while not follow_tag.isdigit():
            # does the parent tag exist?
            if follow_tag not in all_tags_mapping:
                msg = (
                    f"The tag {tag} wants to follow channel {follow_tag},"
                    " which is undefined and doesn't point to a revision"
                )
                raise utils.BadChannel(msg)

            if follow_tag in followed_tags:
                # then we have a circular dependency, tags are following each
                # other but we cannot pinpoint the exact revision
                msg = (
                    f"The tag {tag} was caught is a circular dependency,"
                    " following tags that follow themselves. Cannot pin a revision."
                )
                raise utils.BadChannel(msg)
            followed_tags.append(follow_tag)

            # follow the parent tag until it is a digit (ie. revision number)
            try:
                parent_tag = all_tags_mapping[follow_tag]
            except KeyError as err:
                msg = (
                    f"Tag {tag} wants to follow tag {follow_tag}, but it doesn't exist."
                )
                raise utils.BadChannel(msg) from err

            print(f"Tag {follow_tag} is following tag {parent_tag}.")
            follow_tag = parent_tag

        if int(follow_tag) not in revision_to_track:
            msg = f"The tag {tag} points to revision {follow_tag}, which doesn't exist!"
            raise utils.BadChannel(msg)

        tag_to_revision[tag] = int(follow_tag)

    # if we get here, it is a valid (tag, revision)

    # we now need to add tag aliases
    release_tags = tag_to_revision.copy()
    for base_tag, revision in tag_to_revision.items():
        # "latest" is a special tag for OCI
        if re.match(
            rf"latest_({'|'.join(schema.triggers.KNOWN_RISKS_ORDERED)})$", base_tag
        ):
            latest_alias = base_tag.split("_")[0]
            print(f"Exceptionally converting tag {base_tag} to {latest_alias}.")
            release_tags.pop(base_tag)
            release_tags[latest_alias] = revision

        # stable risks have an alias with any risk string
        if base_tag.endswith("_stable"):
            alias = "_".join(base_tag.split("_")[:-1])
            print(f"Adding stable tag alias {alias} for {base_tag}")
            release_tags[alias] = revision

    # we finally have all the OCI tags to be released,
    # and which revisions to release for each tag. Let's release!
    group_by_revision = defaultdict(list)
    for tag, revision in sorted(release_tags.items()):
        group_by_revision[revision].append(tag)

    for revision, tags in group_by_revision.items():
        track_of_revision = revision_to_track[revision]
        source_img = f"docker://ghcr.io/{args.ghcr_repo}/{img_name}:{track}_{revision}"
        this_dir = os.path.dirname(__file__)
        print(f"Releasing {source_img} with tags:\n{tags}")
        subprocess.check_call(
            [f"{this_dir}/tag_and_publish.sh", source_img, img_name] + tags
        )
        for t in tags:
            tag_mapping_from_all_released_tags[t] = {"revision": revision}

    print(f"Updating {args.all_released_tags} file")
    with open(args.all_released_tags, "w") as fd:
        json.dump(tag_mapping_from_all_released_tags, fd, indent=4)
