#!/usr/bin/env python3

import argparse
import os
import logging
import subprocess
import yaml

from typing import List
from utils import utils, schema


def form_new_releases_trigger(
    track: str, risks: List, revision: str
) -> schema.triggers.ReleasesSchema:
    """Create a new releases.yaml content from scratch."""
    new_trigger = {
        "version": schema.triggers.LATEST_SCHEMA_VERSION,
        "channels": {track: {}},
    }

    for risk in risks:
        new_trigger["channels"][track][risk] = revision

    new_trigger = utils.backfill_higher_risks(track, new_trigger["channels"][track])

    return schema.triggers.ReleasesSchema(**new_trigger)


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

    if not utils.file_exists(args.releases_trigger):
        # If file doesn't exist then we create one
        curr_releases = form_new_releases_trigger(
            args.release_to_track, args.release_to_risks.split(","), args.revision
        )

        utils.overwrite_releases_trigger_file(
            args.releases_trigger,
            curr_releases
        )
    else:
        # Read and validate releases file
        curr_releases = utils.parse_releases_trigger(
            args.releases_trigger
        )
