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

from ..shared.github_output import GithubStepSummary
from ..shared.logs import get_logger
from .utils.encoders import DateTimeEncoder
from .utils.eol_utils import (
    generate_base_eol_exceed_warning,
    track_eol_exceeds_base_eol,
)
from .utils.schema.triggers import KNOWN_RISKS_ORDERED, ImageSchema

logger = get_logger()

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
    required=False,
)
parser.add_argument(
    "--update-releases-json",
    help="Update the releases JSON file.",
    action="store_true",
    default=False,
)


def remove_eol_tags(tag_to_revision, all_releases):
    """Remove all EOL tags from tag to revision mapping."""

    filtered_tag_to_revision = tag_to_revision.copy()
    for base_tag, _ in tag_to_revision.items():
        path = []  # track revisions to prevent inf loop
        tag = base_tag  # init state
        while True:
            if tag in path:
                raise shared.BadChannel(
                    f"Circular tracks found in release JSON:\n {all_releases}"
                )

            path.append(tag)

            # if we find a numeric revision, break since we reached the end of the path
            if tag.isdigit():
                break

            # we allways expect len == 2 unless we reach the final numeric tag
            if not len(split := tag.split("_")) == 2:
                raise shared.BadChannel(
                    f"Malformed tag. Expected format is <track>_<risk>. Found tag {repr(tag)}."
                )

            track, risk = split

            # if we do not end on a numeric revision, we have a dangling tag.
            if track not in all_releases or risk not in all_releases[track]:
                raise shared.BadChannel(
                    f"Dangling tag found. Tag {repr(tag)} does not point to any revision."
                )

            # if EOL date is specified and expired, pop the tag from the map
            if (
                "end-of-life" in all_releases[track]
                and (eol_date := all_releases[track]["end-of-life"])
                < execution_timestamp
                and base_tag in filtered_tag_to_revision
            ):
                logger.warning(
                    f"Warning: Removing EOL tag {repr(base_tag)}, date: {eol_date}"
                )
                filtered_tag_to_revision.pop(base_tag)

            # prep next iteration
            tag = all_releases[track][risk]["target"]

    return filtered_tag_to_revision


def find_tracks_has_eol_exceeding_base_eol(all_releases):
    """Finds all tracks that have EOL dates exceeding the base EOL date."""
    tracks = []

    # find all tracks with EOL dates
    tracks_with_eol = {
        track: release["end-of-life"]
        for track, release in all_releases.items()
        if "end-of-life" in release
    }

    for track, track_eol in tracks_with_eol.items():
        if eols := track_eol_exceeds_base_eol(track, track_eol):
            tracks.append(eols)

    return tracks


def main():
    args = parser.parse_args()
    if not args.update_releases_json and not args.ghcr_repo:
        parser.error(
            "If not updating the releases JSON, --ghcr-repo must be specified."
        )
    img_name = (
        args.image_name
        if args.image_name
        else os.path.abspath(args.image_trigger).split("/")[-2]
    )

    logger.info(f"Preparing to release revision tags for {img_name}")
    all_revision_tags = shared.get_all_revision_tags(args.all_revision_tags)
    revision_to_track = shared.get_revision_to_track(all_revision_tags)

    logger.debug(
        "Revision (aka 'canonical') tags grouped by revision:\n"
        f"{json.dumps(revision_to_track, indent=2)}"
    )

    logger.info(f"Reading all previous releases from {args.all_releases}...")

    all_releases = shared.read_json_file(args.all_releases)
    tag_mapping_from_all_releases = shared.get_tag_mapping_from_all_releases(
        all_releases
    )

    logger.info(f"Parsing image trigger {args.image_trigger}")
    with open(args.image_trigger, encoding="UTF-8") as trigger:
        image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

    _ = ImageSchema(**image_trigger)

    tag_mapping_from_trigger = {}
    for track, risks in image_trigger["release"].items():
        if track not in all_releases:
            logger.info(f"Track {track} will be created for the 1st time")
            all_releases[track] = {}

        for risk, value in risks.items():
            if value is None:
                continue

            if risk in ["end-of-life", "end_of_life"]:
                all_releases[track]["end-of-life"] = value
                continue

            if risk not in KNOWN_RISKS_ORDERED:
                logger.warning(f"Skipping unknown risk {risk} in track {track}")
                continue

            all_releases[track][risk] = {"target": value}
            tag = f"{track}_{risk}"
            logger.info(f"Channel {tag} points to {value}")
            tag_mapping_from_trigger[tag] = value

    # update EOL dates from upload dictionary
    for upload in image_trigger["upload"] or []:
        for track, upload_release_dict in upload.get("release", {}).items():
            if track not in all_releases:
                logger.info(f"Track {track} will be created for the 1st time")
                all_releases[track] = {}

            if (
                isinstance(upload_release_dict, dict)
                and "end-of-life" in upload_release_dict
            ):
                all_releases[track]["end-of-life"] = upload_release_dict["end-of-life"]

    logger.info(
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

            logger.info(f"Tag {follow_tag} is following tag {parent_tag}.")
            follow_tag = parent_tag

        if int(follow_tag) not in revision_to_track:
            msg = str(
                f"The tag {channel_tag} points to revision {follow_tag}, "
                "which doesn't exist!"
            )
            raise shared.BadChannel(msg)

        tag_to_revision[channel_tag] = int(follow_tag)

    # if we get here, it is a valid (tag, revision)

    # remove all EOL tags to be released
    filtered_tag_to_revision = remove_eol_tags(tag_to_revision, all_releases)

    # we now need to add tag aliases
    release_tags = filtered_tag_to_revision.copy()
    for base_tag, revision in tag_to_revision.items():
        # "latest" is a special tag for OCI
        if re.match(
            rf"latest_({'|'.join(KNOWN_RISKS_ORDERED)})$",
            base_tag,
        ):
            latest_alias = base_tag.split("_")[-1]
            logger.info(f"Exceptionally converting tag {base_tag} to {latest_alias}.")
            release_tags[latest_alias] = revision
            release_tags.pop(base_tag)

        # stable risks have an alias with any risk string
        if base_tag.endswith("_stable"):
            stable_alias = "_".join(base_tag.split("_")[:-1])
            logger.info(f"Adding stable tag alias {stable_alias} for {base_tag}")
            release_tags[stable_alias] = revision

    # we finally have all the OCI tags to be released,
    # and which revisions to release for each tag. Let's release!
    group_by_revision = defaultdict(list)
    for tag, revision in sorted(release_tags.items()):
        group_by_revision[revision].append(tag)

    if not args.update_releases_json:
        logger.info(
            "Processed tag aliases and ready to release the following revisions:\n"
            f"{json.dumps(group_by_revision, indent=2)}"
        )

        github_tags = []
        for revision, tags in group_by_revision.items():
            revision_track = revision_to_track[revision]
            source_img = (
                "docker://ghcr.io/"
                f"{args.ghcr_repo}/{img_name}:{revision_track}_{revision}"
            )
            this_dir = os.path.dirname(__file__)
            logger.info(f"Releasing {source_img} with tags:\n{tags}")
            subprocess.check_call(
                [f"{this_dir}/tag_and_publish.sh", source_img, img_name] + tags
            )

            for tag in tags:
                gh_release_info = {}
                gh_release_info["canonical-tag"] = (
                    f"{img_name}_{revision_track}_{revision}"
                )
                gh_release_info["release-name"] = f"{img_name}_{tag}"
                gh_release_info["name"] = f"{img_name}"
                gh_release_info["revision"] = f"{revision}"
                gh_release_info["channel"] = f"{tag}"
                github_tags.append(gh_release_info)

        matrix = {"include": github_tags}

        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="UTF-8") as gh_out:
            print(f"gh-releases-matrix={matrix}", file=gh_out)

    else:
        # Write warnings to the summary
        tracks_eol_exceeding_base_eol = find_tracks_has_eol_exceeding_base_eol(all_releases)
        if tracks_eol_exceeding_base_eol:
            title, text = generate_base_eol_exceed_warning(tracks_eol_exceeding_base_eol)
            title = f"## Release: {title}"
            with GithubStepSummary() as summary:
                summary.write(title, text)

        logger.info(
            f"Updating {args.all_releases} file with:\n"
            f"{json.dumps(all_releases, indent=2, cls=DateTimeEncoder)}"
        )

        with open(args.all_releases, "w", encoding="UTF-8") as fd:
            json.dump(all_releases, fd, indent=4, cls=DateTimeEncoder)


if __name__ == "__main__":
    main()
