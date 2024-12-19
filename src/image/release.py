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
from datetime import datetime, timezone

import yaml

import src.shared.release_info as shared

from .utils.encoders import DateTimeEncoder
from .utils.schema.triggers import KNOWN_RISKS_ORDERED, ImageSchema

# generate single date for consistent EOL checking
execution_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

all_releases = shared.read_json_file(args.all_releases)
tag_mapping_from_all_releases = shared.get_tag_mapping_from_all_releases(all_releases)

print(f"Parsing image trigger {args.image_trigger}")
with open(args.image_trigger, encoding="UTF-8") as trigger:
    image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

_ = ImageSchema(**image_trigger)

tag_mapping_from_trigger = {}
for track, risks in image_trigger["release"].items():
    if track not in all_releases:
        print(f"Track {track} will be created for the 1st time")
        all_releases[track] = {}

    for risk, value in risks.items():
        if value is None:
            continue

        if risk in ["end-of-life", "end_of_life"]:
            all_releases[track]["end-of-life"] = value
            continue

        if risk not in KNOWN_RISKS_ORDERED:
            print(f"Skipping unknown risk {risk} in track {track}")
            continue

        all_releases[track][risk] = {"target": value}
        tag = f"{track}_{risk}"
        print(f"Channel {tag} points to {value}")
        tag_mapping_from_trigger[tag] = value

# update EOL dates from upload dictionary
for upload in image_trigger["upload"] or []:
    for track, upload_release_dict in (upload["release"] or {}).items():
        if track not in all_releases:
            print(f"Track {track} will be created for the 1st time")
            all_releases[track] = {}

        if (
            isinstance(upload_release_dict, dict)
            and "end-of-life" in upload_release_dict
        ):
            all_releases[track]["end-of-life"] = upload_release_dict["end-of-life"]

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
eol_targets = []
for channel_tag, target in tag_mapping_from_trigger.items():
    # a target cannot follow its own tag
    if target == channel_tag:
        msg = f"A tag cannot follow itself ({target})"
        raise shared.BadChannel(msg)

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
            raise shared.BadChannel(msg)

        if follow_tag in followed_tags:
            # then we have a circular dependency, tags are following each
            # other but we cannot pinpoint the exact revision
            msg = (
                f"The tag {channel_tag} was caught is a circular dependency, "
                "following tags that follow themselves. Cannot pin a revision."
            )
            raise shared.BadChannel(msg)
        followed_tags.append(follow_tag)

        # follow the parent tag until it is a digit (ie. revision number)
        parent_tag = all_tags_mapping[follow_tag]

        print(f"Tag {follow_tag} is following tag {parent_tag}.")
        follow_tag = parent_tag

    # check if any of the followed tags are eol
    is_eol = False
    print("followed_tags", followed_tags)
    for tag in followed_tags:

        track = tag.split("_")[0]

        # check if eol data exists, if not skip ahead
        if "end-of-life" not in all_releases[track]:
            continue

        # TODO: we should be parsing the timetamp to unix time for comparison
        # this can be dangerous if the timestamp formatting changes. Also see:
        # src/image/prepare_single_image_build_matrix.py
        # oci-factory/tools/workflow-engine/charms/temporal-worker/oci_factory/activities/find_images_to_update.py
        if all_releases[track]["end-of-life"] < execution_timestamp and tag not in eol_targets:
            print(f'Found eol {track} {all_releases[track]["end-of-life"]}')
            eol_targets.append(target)

    if int(follow_tag) not in revision_to_track:
        msg = str(
            f"The tag {channel_tag} points to revision {follow_tag}, "
            "which doesn't exist!"
        )
        raise shared.BadChannel(msg)

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
print("eol_tags", eol_targets)
for tag, revision in sorted(release_tags.items()):

    if tag in eol_targets:
        print(f"Warning: Skipping release of {tag} since it is end of life.")
        continue

    group_by_revision[revision].append(tag)

print(
    "Processed tag aliases and ready to release the following revisions:\n"
    f"{json.dumps(group_by_revision, indent=2)}"
)
github_tags = []
for revision, tags in group_by_revision.items():

    revision_track = revision_to_track[revision]
    source_img = (
        "docker://ghcr.io/" f"{args.ghcr_repo}/{img_name}:{revision_track}_{revision}"
    )
    this_dir = os.path.dirname(__file__)
    print(f"Releasing {source_img} with tags:\n{tags}")
    subprocess.check_call(
        [f"{this_dir}/tag_and_publish.sh", source_img, img_name] + tags
    )

    for tag in tags:
        gh_release_info = {}
        gh_release_info["canonical-tag"] = f"{img_name}_{revision_track}_{revision}"
        gh_release_info["release-name"] = f"{img_name}_{tag}"
        gh_release_info["name"] = f"{img_name}"
        gh_release_info["revision"] = f"{revision}"
        gh_release_info["channel"] = f"{tag}"
        gh_release_info["end-of-life"] = f"{tag}"
        github_tags.append(gh_release_info)

print(
    f"Updating {args.all_releases} file with:\n"
    f"{json.dumps(all_releases, indent=2, cls=DateTimeEncoder)}"
)

with open(args.all_releases, "w", encoding="UTF-8") as fd:
    json.dump(all_releases, fd, indent=4, cls=DateTimeEncoder)

matrix = {"include": github_tags}

with open(os.environ["GITHUB_OUTPUT"], "a", encoding="UTF-8") as gh_out:
    print(f"gh-releases-matrix={matrix}", file=gh_out)
