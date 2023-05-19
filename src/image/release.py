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
import yaml

from collections import defaultdict
from utils.schema.triggers import ImageSchema, KNOWN_RISKS_ORDERED


class BadChannel(Exception):
    """Error validating release channel."""


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
    help="Path to the _releases.yaml file.",
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
with open(args.all_revision_tags) as rev_tags_f:
    all_revision_tags = (
        rev_tags_f.read().strip().rstrip(",").lstrip(",").split(",")
    )
revision_to_track = {}
for track_revision in all_revision_tags:
    track, revision = track_revision.split("_")
    if revision in revision_to_track:
        msg = (
            "Each revision can only have 1 canonical tag, "
            f"but revision {revision} is associated with tracks "
            f"{track} and {revision_to_track['revision']}!"
        )
        raise BadChannel(msg)

    revision_to_track[int(revision)] = track

print(
    "Revision tags grouped by revision:\n"
    f"{json.dumps(revision_to_track, indent=2)}"
)

print(f"Reading all previous releases from {args.all_releases}...")
tag_mapping_from_all_releases = {}
try:
    with open(args.all_releases) as all_releases_fd:
        all_releases = yaml.safe_load(all_releases_fd).get("channels", {})

    # map the existing tags into a struct similar to tag_mapping_from_trigger
    for track, risks in all_releases.items():
        for risk, values in risks.items():
            if risk not in KNOWN_RISKS_ORDERED:
                continue

            tag = f"{track}_{risk}"

            tag_mapping_from_all_releases[tag] = values["target"]
except FileNotFoundError:
    all_releases = {}

print(f"Parsing image trigger {args.image_trigger}")
with open(args.image_trigger) as trigger:
    image_trigger = ImageSchema(**yaml.safe_load(trigger))

tag_mapping_from_trigger = {}
for track, risks in image_trigger.release.items():
    if track not in all_releases:
        print(f"Track {track} will be created for the 1st time")
        all_releases[track] = {}

    for risk, value in risks.dict(exclude_none=True).items():
        if risk == "end-of-life":
            all_releases[track]["end-of-life"] = value
            continue

        if risk not in KNOWN_RISKS_ORDERED:
            print(f"Skipping unkown risk {risk} in track {track}")
            continue

        all_releases[track][risk] = {"target": value}
        tag = f"{track}_{risk}"
        print(f"Channel {tag} points to {value}")
        tag_mapping_from_trigger[tag] = value

print(
    "Going to update channels according to the following:\n"
    f"{json.dumps(tag_mapping_from_trigger, indent=2)}"
)

# combine all tags
all_tags_mapping = {
    **tag_mapping_from_all_releases,
    **tag_mapping_from_trigger,
}

# we need to validate the release request, to make sure that:
# - the target revisions exist
# - the target tags (when following) do not incur in a circular dependency
# - the target tags (when following) exist
tag_to_revision = tag_mapping_from_trigger.copy()
for channel_tag, target in tag_mapping_from_trigger.items():
    # a target cannot follow its own tag
    if target == channel_tag:
        msg = f"A tag cannot follow itself ({target})"
        raise BadChannel(msg)

    # we need to map tags to a revision number,
    # even those that point to other tags
    follow_tag = target
    followed_tags = []
    while not follow_tag.isdigit():
        # does the parent tag exist?
        if follow_tag not in all_tags_mapping:
            msg = (
                f"The tag {channel_tag} wants to follow channel {follow_tag},"
                " which is undefined and doesn't point to a revision"
            )
            raise BadChannel(msg)

        if follow_tag in followed_tags:
            # then we have a circular dependency, tags are following each
            # other but we cannot pinpoint the exact revision
            msg = (
                f"The tag {channel_tag} was caught is a circular dependency, "
                "following tags that follow themselves. Cannot pin a revision."
            )
            raise BadChannel(msg)
        followed_tags.append(follow_tag)

        # follow the parent tag until it is a digit (ie. revision number)
        parent_tag = all_tags_mapping[follow_tag]

        print(f"Tag {follow_tag} is following tag {parent_tag}.")
        follow_tag = parent_tag

    if int(follow_tag) not in revision_to_track:
        msg = str(
            f"The tag {channel_tag} points to revision {follow_tag}, "
            "which doesn't exist!"
        )
        raise BadChannel(msg)

    tag_to_revision[channel_tag] = int(follow_tag)

# if we get here, it is a valid (tag, revision)

# we now need to add tag aliases
release_tags = tag_to_revision.copy()
for base_tag, revision in tag_to_revision.items():
    # "latest" is a special tag for OCI
    if re.match(
        rf"latest_({'|'.join(KNOWN_RISKS_ORDERED)})$",
        base_tag,
    ):
        latest_alias = base_tag.split("_")[-1]
        print(f"Exceptionally converting tag {base_tag} to {latest_alias}.")
        release_tags[latest_alias] = revision
        release_tags.pop(base_tag)

    # stable risks have an alias with any risk string
    if base_tag.endswith("_stable"):
        stable_alias = "_".join(base_tag.split("_")[:-1])
        print(f"Adding stable tag alias {stable_alias} for {base_tag}")
        release_tags[stable_alias] = revision

# we finally have all the OCI tags to be released,
# and which revisions to release for each tag. Let's release!
group_by_revision = defaultdict(list)
for tag, revision in sorted(release_tags.items()):
    group_by_revision[revision].append(tag)

print(
    "Processed tag aliases and ready to release the following revisions:\n"
    f"{json.dumps(group_by_revision, indent=2)}"
)
for revision, tags in group_by_revision.items():
    track_of_revision = revision_to_track[revision]
    source_img = (
        f"docker://ghcr.io/{args.ghcr_repo}/{img_name}:{track}_{revision}"
    )
    this_dir = os.path.dirname(__file__)
    print(f"Releasing {source_img} with tags:\n{tags}")
    subprocess.check_call(
        [f"{this_dir}/tag_and_publish.sh", source_img, img_name] + tags
    )

print(
    f"Updating {args.all_releases} file with:\n"
    f"{json.dumps(all_releases, indent=2)}"
)
with open(args.all_releases, "w") as fd:
    json.dump(all_releases, fd, indent=4)
