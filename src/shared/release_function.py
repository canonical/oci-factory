#!/usr/bin/env python3

"""
Takes a releases trigger file and created a mapping of all the
OCI tags that are marked to be release.
"""

import json
from src.image.utils.schema.triggers import KNOWN_RISKS_ORDERED


class BadChannel(Exception):
    """Error validating release channel."""


def get_all_releases(file_all_releases):
    """
    Reads a JSON file and returns the parsed data.
    """
    try:
        with open(file_all_releases, encoding="UTF-8") as all_releases_fd:
            return json.load(all_releases_fd)
    except FileNotFoundError:
        return {}


def get_tag_mapping_from_all_releases(all_releases_dict):
    """
    Iterates over the provided dictionary 
    and extracts the tags in this format 
    track_risk. The resulting tag mapping 
    associates each tag with its 
    corresponding target value. 
    example: {"latest_beta":"87"}
    """
    mapping_from_all_releases = {}
    for track, risks in all_releases_dict.items():
        for risk, values in risks.items():
            if risk in KNOWN_RISKS_ORDERED:
                tag = f"{track}_{risk}"

                mapping_from_all_releases[tag] = values["target"]
    return mapping_from_all_releases


def get_all_revision_tags(file_all_revision_tags):
    """
    Reads the specified file and processes 
    its contents to extract revision tags. 
    The tags are returned as a list after 
    removing leading and trailing commas 
    and any leading or trailing whitespace.
    """
    with open(file_all_revision_tags, encoding="UTF-8") as rev_tags_f:
        return rev_tags_f.read().strip().rstrip(",").lstrip(",").split(",")


def get_revision_to_track(all_revisions_tags):
    """
    Iterates over a list of track_revision 
    tags and builds a dictionary that maps 
    each revision number to its corresponding 
    track. If a revision number is associated 
    with multiple tracks, an exception of type 
    BadChannel is raised.
    """
    revision_track = {}
    for track_revision in all_revisions_tags:
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
