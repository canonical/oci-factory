#!/usr/bin/env python3

"""
This module provides functions for parsing and processing 
data related to _release.json and revision tags.
"""

import argparse
import json
from collections import defaultdict

from ..image.utils.schema.triggers import KNOWN_RISKS_ORDERED


class BadChannel(Exception):
    """Error validating release channel."""


def read_json_file(json_file: str) -> dict:
    """
    Reads a JSON file and returns the parsed data.
    """
    try:
        with open(json_file, encoding="UTF-8") as fd:
            return json.load(fd)
    except FileNotFoundError:
        return {}


def get_tag_mapping_from_all_releases(all_releases_dict: dict) -> dict:
    """
    Iterates over the provided dictionary
    with all the releases (_releases.json)
    and extracts the tags in this format
    track_risk. The resulting tag mapping
    associates each tag with its
    corresponding target value.
    Example: {"latest_beta":"87"}
    """
    mapping_from_all_releases = {}
    for track, risks in all_releases_dict.items():
        for risk, values in risks.items():
            if risk in KNOWN_RISKS_ORDERED:
                tag = f"{track}_{risk}"

                mapping_from_all_releases[tag] = values["target"]
    return mapping_from_all_releases


def get_all_revision_tags(file_all_revision_tags: str) -> list:
    """
    Reads the specified file (which must contain
    1 text line with all the revision tags,
    eg. '1.0-22.04_1,1.2-20.04_76') and processes
    its contents to extract revision tags.
    The tags are returned as a list after
    removing leading and trailing commas
    and any leading or trailing whitespace.
    """
    with open(file_all_revision_tags, encoding="UTF-8") as rev_tags_f:
        return rev_tags_f.read().strip().rstrip(",").lstrip(",").split(",")


def get_revision_to_track(all_revisions_tags: list) -> dict:
    """
    Iterates over a list of track_revision
    tags (aka revision/canonical tags)
    and builds a dictionary that maps
    each revision number to its corresponding
    track. If a revision number is associated
    with multiple tracks, an exception of type
    BadChannel is raised.
    """
    revision_track = {}
    for track_revision in all_revisions_tags:
        track, revision = track_revision.rsplit("_", 1)
        revision = int(revision)
        if revision in revision_track:
            msg = (
                "Each revision can only have 1 canonical tag, "
                f"but revision {revision} is associated with tracks "
                f"{track} and {revision_track[revision]}!"
            )
            raise BadChannel(msg)

        revision_track[revision] = track
    return revision_track


def _find_alias_revision(tag_mapping_from_all_releases: dict, rev: str, visited: set, tag: str) -> str:
    if rev in visited:
        raise BadChannel(
            f"Tag {tag} was caught in a circular dependency, "
            "following tags that follow themselves. Cannot pin a revision."
        )
    visited.add(rev)
    if not rev.isdigit():
        return _find_alias_revision(
            tag_mapping_from_all_releases, tag_mapping_from_all_releases[rev], visited, tag
        )
    return rev

def get_revision_to_released_tags(all_releases: dict) -> dict:
    """
    Iterates over the provided dictionary with all the releases
    and extracts the revision numbers and their corresponding
    released tags. The resulting dictionary maps each revision
    number to a list of released tags.
    """
    revision_to_released_tags = defaultdict(list)
    tag_mapping_from_all_releases = get_tag_mapping_from_all_releases(all_releases)
    for tag, revision in tag_mapping_from_all_releases.items():
        if not revision.isdigit():
            visited = set()
            revision = _find_alias_revision(tag_mapping_from_all_releases, revision, visited, tag)
        revision = int(revision)
        revision_to_released_tags[revision].append(tag)

    for revision, tags in revision_to_released_tags.items():
        revision_to_released_tags[revision] = sorted(tags)

    return dict(revision_to_released_tags)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "function",
        help="The function to run",
        choices=["get_revision_to_released_tags"],
    )

    parser.add_argument(
        "--all-releases",
        help="Path to the _releases.json file",
    )

    args = parser.parse_args()

    if args.function == "get_revision_to_released_tags":
        print(
            json.dumps(
                (get_revision_to_released_tags(read_json_file(args.all_releases)))
            )
        )


if __name__ == "__main__":
    main()
