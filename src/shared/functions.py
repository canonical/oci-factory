#!/usr/bin/env -S python3 -m src.image.utils.schema.triggers

"""
Takes a releases trigger file and created a mapping of all the
OCI tags that are marked to be release.
"""

import json
import os
import re
import subprocess
from collections import defaultdict
import yaml
from src.image.utils.schema.triggers import ImageSchema, KNOWN_RISKS_ORDERED


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BadChannel(Exception):
    """Error validating release channel."""


def get_all_revision_tags(file_all_revision_tags):
    """
    This function permits to get all the revision tags.
    """
    with open(file_all_revision_tags, encoding="UTF-8") as rev_tags_f:
        return rev_tags_f.read().strip().rstrip(",").lstrip(",").split(",")


def get_all_releases(file_all_releases):
    """
    This function permits to get all the releases.
    """
    try:
        with open(file_all_releases, encoding="UTF-8") as all_releases_fd:
            return json.load(all_releases_fd)
    except FileNotFoundError:
        return {}


def get_image_trigger(file_image_trigger):
    """
    This function permits to parse and validate the image_trigger file.
    """
    with open(file_image_trigger, encoding="UTF-8") as trigger:
        return ImageSchema(**yaml.safe_load(trigger))


def get_tag_mapping_from_all_releases(all_releases_dict):
    """
    This function permits to map the tag from all_releases
    """
    mapping_from_all_releases = {}
    for track, risks in all_releases_dict.items():
        for risk, values in risks.items():
            if risk in KNOWN_RISKS_ORDERED:
                tag = f"{track}_{risk}"

                mapping_from_all_releases[tag] = values["target"]
    return mapping_from_all_releases


def get_revision_to_track(all_revision):
    """
    This function permits the conversion of the revision to track.
    """
    revision_track = {}
    for track_revision in all_revision:
        track, revision = track_revision.split("_")
        if revision in revision_track:
            msg = (
                "Each revision can only have 1 canonical tag, "
                f"but revision {revision} is associated with tracks "
                f"{track} and {revision_track['revision']}!"
            )
            raise BadChannel(msg)

        revision_track[int(revision)] = track
    return revision_track


def get_tag_mapping_from_trigger(image, all_releases_info):
    """
    This function permits to get the tag_mapping from image
    """
    mapping_from_trigger = {}
    for track, risks in image.release.items():
        if track not in all_releases_info:
            print(f"Track {track} will be created for the 1st time")
            all_releases_info[track] = {}

        for risk, value in risks.dict(exclude_none=True).items():
            if risk == "end-of-life":
                all_releases_info[track]["end-of-life"] = value
                continue

            if risk not in KNOWN_RISKS_ORDERED:
                print(f"Skipping unkown risk {risk} in track {track}")
                continue

            all_releases_info[track][risk] = {"target": value}
            tag = f"{track}_{risk}"
            print(f"Channel {tag} points to {value}")
            mapping_from_trigger[tag] = value
    return mapping_from_trigger, all_releases_info


def get_tag_to_revision(mapping_from_trigger, all_tags_map, revision_track):
    """
    This function permits to get the tag to revision.
    """
    tag_revision = mapping_from_trigger.copy()
    for channel_tag, target in mapping_from_trigger.items():
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
            if follow_tag not in all_tags_map:
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
            parent_tag = all_tags_map[follow_tag]

            print(f"Tag {follow_tag} is following tag {parent_tag}.")
            follow_tag = parent_tag

        if int(follow_tag) not in revision_track:
            msg = str(
                f"The tag {channel_tag} points to revision {follow_tag}, "
                "which doesn't exist!"
            )
            raise BadChannel(msg)

        tag_revision[channel_tag] = int(follow_tag)
    return tag_revision


def get_releases_tags(tag_revision):
    """
    This function permits to get the releases tags.
    """
    # we now need to add tag aliases
    release_tag = tag_revision.copy()
    for base_tag, revision in tag_revision.items():
        # "latest" is a special tag for OCI
        if re.match(
            rf"latest_({'|'.join(KNOWN_RISKS_ORDERED)})$",
            base_tag,
        ):
            latest_alias = base_tag.split("_")[-1]
            print(f"Exceptionally converting tag {base_tag} to {latest_alias}.")
            release_tag[latest_alias] = revision
            release_tag.pop(base_tag)

        # stable risks have an alias with any risk string
        if base_tag.endswith("_stable"):
            stable_alias = "_".join(base_tag.split("_")[:-1])
            print(f"Adding stable tag alias {stable_alias} for {base_tag}")
            release_tag[stable_alias] = revision
    return release_tag


def get_group_by_revision(release_tag):
    """
    This function permits to group of the tags by revision
    """
    group_tags_by_revision = defaultdict(list)
    for tag, revision in sorted(release_tag.items()):
        group_tags_by_revision[revision].append(tag)
    return group_tags_by_revision


def upload_image(
    group_tags_by_revision,
    revision_track,
    ghcr_repo,
    image_name,
    dir_of_tag_and_publish,
):
    """
    This function permits to upload the image to the registry
    """
    for revision, tags in group_tags_by_revision.items():
        revision_track = revision_track[revision]
        source_img = (
            "docker://ghcr.io/" f"{ghcr_repo}/{image_name}:{revision_track}_{revision}"
        )
        print(f"Releasing {source_img} with tags:\n{tags}")
        subprocess.check_call(
            [f"{dir_of_tag_and_publish}/tag_and_publish.sh", source_img, image_name]
            + tags
        )


def write_release_to_file(file_all_releases, releases):
    """
    This function permits to write all_releases on the _releases.json file
    """
    with open(file_all_releases, "w", encoding="UTF-8") as all_releases_fd:
        json.dump(releases, all_releases_fd, indent=4)
