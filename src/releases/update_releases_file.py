#!/usr/bin/env python3

import argparse

from typing import List
from utils import utils, schema


def form_new_track(track_name: str, risks: List, revision: str) -> dict:
    """Forms a new track from scratch."""

    track = {}
    for risk in risks:
        track[risk] = revision

    track = utils.backfill_higher_risks(track_name, track)

    return track


def form_new_releases_trigger(
    track_name: str, risks: List, revision: str
) -> schema.triggers.ReleasesSchema:
    """Create a new releases.yaml content from scratch."""

    new_trigger = {
        "version": schema.triggers.LATEST_SCHEMA_VERSION,
        "channels": {track_name: {}},
    }

    new_trigger["channels"][track_name].update(
        form_new_track(track_name, risks, revision)
    )

    return schema.triggers.ReleasesSchema(**new_trigger)


def update_track_risks(track: dict, risks: List) -> dict:
    """Takes an existing track and updates its risks."""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--releases-trigger",
        help="Path to the releases trigger file.",
        required=True,
    )
    parser.add_argument(
        "--release-to-risks",
        help="Comma-separated risks to release the given revision to.",
        required=True,
    )
    parser.add_argument(
        "--revision",
        help="Image revision number being released.",
        required=True,
    )
    parser.add_argument(
        "--release-to-track",
        help="Track where to release the given revision to.",
        required=True,
    )

    args = parser.parse_args()

    utils.assert_releases_trigger_filename(args.releases_trigger)
    release_to_risks = args.release_to_risks.split(",")

    if not utils.file_exists(args.releases_trigger):
        # If file doesn't exist then we create one
        print(f"Creating new releases.yaml file at {args.releases_trigger} with:")
        print(f" - track: {args.release_to_track}")
        print(f" - risks: {release_to_risks}")
        print(f" - revision: {args.revision}")
        curr_releases = form_new_releases_trigger(
            args.release_to_track, release_to_risks, args.revision
        )
    else:
        # Read and validate releases file
        print(f"Getting existing releases trigger from {args.releases_trigger}")
        curr_releases = utils.parse_releases_trigger(args.releases_trigger)

        # does this track already exist?
        if args.release_to_track in curr_releases.channels:
            print(
                f"Updating track {args.release_to_track} with revision {args.revision}"
            )
            existing_track = curr_releases.channels[args.release_to_track].dict(
                exclude_none=True
            )

            for risk in release_to_risks:
                existing_track[risk] = args.revision

            updated_track = utils.backfill_higher_risks(
                args.release_to_track, existing_track
            )
        else:
            print(f"Forming new channel track {args.release_to_track}")
            updated_track = form_new_track(
                args.release_to_track, args.release_to_risks.split(","), args.revision
            )

        curr_releases.channels[args.release_to_track] = schema.triggers.ChannelsSchema(
            **updated_track
        )

    utils.overwrite_releases_trigger_file(args.releases_trigger, curr_releases)
