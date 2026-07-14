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
from .pro import get_track_from_tag
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
parser.add_argument(
    "--pro-release-sources",
    help="Directory containing decrypted Pro OCI archive release sources.",
    required=False,
    default="",
)


def remove_eol_tags(tag_to_revision, all_releases):
    """Remove all EOL tags from tag to revision mapping."""

    filtered_tag_to_revision = tag_to_revision.copy()
    for base_tag, target_value_data in tag_to_revision.items():
        if isinstance(target_value_data, dict) and isinstance(
            target_value_data["revision"], int
        ):
            track, _ = output_tag(base_tag).rsplit("_", 1)
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
            continue

        path = []  # track revisions to prevent inf loop
        tag = base_tag  # init state
        while True:
            if tag in path:
                raise shared.BadChannel(
                    f"Circular tracks found in release JSON:\n {all_releases}"
                )

            path.append(tag)

            # if we find a numeric revision, break since we reached the end of the path
            if isinstance(tag, dict):
                tag = str(tag["revision"])

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


def group_release_tags_by_revision_and_destination(release_tags, image_trigger):
    """Group tags by revision and publish destination."""
    group_by_revision = defaultdict(lambda: defaultdict(list))
    for _, release_data in sorted(release_tags.items()):
        revision = release_data["revision"]
        destination = release_data["destination"]
        group_by_revision[revision][destination].append(release_data["tag"])

    return group_by_revision


def validate_unique_destination_tags(release_tags):
    """Ensure one destination/tag points to only one revision."""
    seen = {}
    for _, release_data in release_tags.items():
        key = (release_data["destination"], release_data["tag"])
        revision = release_data["revision"]
        if key in seen and seen[key] != revision:
            raise shared.BadChannel(
                "Multiple release variants target the same destination/tag: "
                f"{key[0]}:{key[1]} points to both revisions {seen[key]} and {revision}."
            )
        seen[key] = revision


def get_or_create_pro_variant(track_release: dict, services: list[str], pro_config: dict) -> dict:
    """Return the _releases.json Pro variant matching services, creating it if needed."""
    services = sorted(services)
    for variant in track_release.setdefault("pro-variants", []):
        if sorted(variant["services"]) == services:
            return variant
    variant = {"services": services}
    track_release["pro-variants"].append(variant)
    return variant


def target_value(value):
    """Return the release target string from a scalar or target object."""
    if isinstance(value, dict):
        return value["target"]
    return value


def output_tag(map_key: str) -> str:
    """Return the registry tag represented by an internal release map key."""
    if map_key.startswith("pro:"):
        return map_key.split(":", 2)[2]
    return map_key


def release_entry(revision, destination, tag=None, track=None):
    """Return release routing metadata for a concrete revision."""
    if tag is not None and track is None:
        track = get_track_from_tag(tag)
    return {
        "revision": revision,
        "destination": destination,
        "tag": tag,
        "track": track,
    }


def get_release_source(destination, revision_track, revision, img_name, ghcr_repo, pro_sources):
    """Return the skopeo source image reference for a release destination."""
    if destination == "pro-acr":
        source_path = os.path.join(pro_sources, f"{img_name}_{revision_track}_{revision}")
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Pro release source not found: {source_path}")
        return f"oci-archive:{source_path}"

    return f"docker://ghcr.io/{ghcr_repo}/{img_name}:{revision_track}_{revision}"


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
    tag_destination = {}
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

            if risk == "pro-variants":
                for variant in value or []:
                    stored_variant = get_or_create_pro_variant(
                        all_releases[track], variant["services"], variant["pro"]
                    )
                    for variant_risk in KNOWN_RISKS_ORDERED:
                        variant_value = variant.get(variant_risk)
                        if variant_value is None:
                            continue
                        stored_variant[variant_risk] = {
                            "target": target_value(variant_value)
                        }
                        tag = f"{track}_{variant_risk}"
                        map_key = f"pro:{','.join(variant['services'])}:{tag}"
                        logger.info(
                            f"Pro channel {tag} points to {target_value(variant_value)}"
                        )
                        tag_mapping_from_trigger[map_key] = target_value(variant_value)
                        tag_destination[map_key] = "pro-acr"
                continue

            if risk not in KNOWN_RISKS_ORDERED:
                logger.warning(f"Skipping unknown risk {risk} in track {track}")
                continue

            all_releases[track][risk] = {"target": target_value(value)}
            tag = f"{track}_{risk}"
            logger.info(f"Channel {tag} points to {target_value(value)}")
            tag_mapping_from_trigger[tag] = target_value(value)
            tag_destination[tag] = "public"

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
    tag_to_revision = {
        tag: release_entry(
            target,
            tag_destination[tag],
            tag=output_tag(tag),
            track=get_track_from_tag(output_tag(tag)),
        )
        for tag, target in tag_mapping_from_trigger.items()
    }
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

        tag_to_revision[channel_tag] = release_entry(
            int(follow_tag),
            tag_destination[channel_tag],
            tag=output_tag(channel_tag),
            track=get_track_from_tag(output_tag(channel_tag)),
        )

    # if we get here, it is a valid (tag, revision)

    # remove all EOL tags to be released
    filtered_tag_to_revision = remove_eol_tags(tag_to_revision, all_releases)

    # we now need to add tag aliases
    release_tags = filtered_tag_to_revision.copy()
    for base_tag, release_data in tag_to_revision.items():
        revision = release_data["revision"]
        destination = release_data["destination"]
        # "latest" is a special tag for OCI
        if re.match(
            rf"latest_({'|'.join(KNOWN_RISKS_ORDERED)})$",
            base_tag,
        ):
            base_output_tag = output_tag(base_tag)
            latest_alias = base_output_tag.split("_")[-1]
            logger.info(f"Exceptionally converting tag {base_tag} to {latest_alias}.")
            alias_key = f"{base_tag}:alias:{latest_alias}"
            release_tags[alias_key] = release_entry(
                revision, destination, tag=latest_alias, track="latest"
            )
            release_tags.pop(base_tag)

        # stable risks have an alias with any risk string
        if output_tag(base_tag).endswith("_stable"):
            base_output_tag = output_tag(base_tag)
            stable_alias = "_".join(base_output_tag.split("_")[:-1])
            logger.info(f"Adding stable tag alias {stable_alias} for {base_tag}")
            alias_key = f"{base_tag}:alias:{stable_alias}"
            release_tags[alias_key] = release_entry(
                revision, destination, tag=stable_alias, track=stable_alias
            )

    # we finally have all the OCI tags to be released,
    # and which revisions to release for each tag. Let's release!
    validate_unique_destination_tags(release_tags)
    group_by_revision = group_release_tags_by_revision_and_destination(
        release_tags, image_trigger
    )

    if not args.update_releases_json:
        logger.info(
            "Processed tag aliases and ready to release the following revisions:\n"
            f"{json.dumps(group_by_revision, indent=2)}"
        )

        github_tags = []
        for revision, tags_by_destination in group_by_revision.items():
            revision_track = revision_to_track[revision]
            this_dir = os.path.dirname(__file__)
            for destination, tags in tags_by_destination.items():
                source_img = get_release_source(
                    destination,
                    revision_track,
                    revision,
                    img_name,
                    args.ghcr_repo,
                    args.pro_release_sources,
                )
                logger.info(
                    f"Releasing {source_img} to {destination} with tags:\n{tags}"
                )
                env = os.environ.copy()
                env["PUBLISH_DESTINATION"] = destination
                subprocess.check_call(
                    [f"{this_dir}/tag_and_publish.sh", source_img, img_name] + tags,
                    env=env,
                )

            for tags in tags_by_destination.values():
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
