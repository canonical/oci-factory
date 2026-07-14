#!/usr/bin/env python3

"""
A pre-release is an informative data model meant to flag that there is
a new revision of an image that has been requested to be released.
This mechanism is necessary since one cannot know the revision number
of an image that has not yet been built. Thus, upon inferring the new
revision number and build said new image, the CI creates a pre-release
with the necessary information for the following jobs to be able to know
which revision number to release where.

NOTE: this is only necessary because the builds happen in parallel in a
GH matrix, which makes it difficult to sync and exchange information
between build. Thus pre-release data files are created for post-build
analysis.
"""

import argparse
import json

import yaml

from ..shared.logs import get_logger
from .pro import get_published_track, normalize_services
from .utils.schema.revision_data import RevisionDataSchema
from .utils.schema.triggers import KNOWN_RISKS_ORDERED, ImageSchema

logger = get_logger()


def backfill_higher_risks(channels: dict) -> None:
    """Parses all the risks in all tracks, adding the missing higher risks."""

    for track, val in channels.items():
        # from the most to the least stable
        for i, risk in enumerate(KNOWN_RISKS_ORDERED):
            if risk not in val:
                if risk == "stable":  # same as i == 0
                    # stable never follows other risks, as it is already
                    # the lowest one
                    continue

                # if there a lower risk to follow?
                if KNOWN_RISKS_ORDERED[i - 1] in val:
                    val[risk] = f"{track}_{KNOWN_RISKS_ORDERED[i-1]}"


def backfill_higher_risks_for_variant(track: str, variant: dict) -> None:
    """Backfill risks inside a Pro variant."""
    for i, risk in enumerate(KNOWN_RISKS_ORDERED):
        if risk not in variant:
            if risk == "stable":
                continue
            if KNOWN_RISKS_ORDERED[i - 1] in variant:
                variant[risk] = variant[KNOWN_RISKS_ORDERED[i - 1]]


def find_or_create_pro_variant(track_release: dict, pro_config: dict) -> dict:
    """Return the Pro variant matching the given config, creating it if needed."""
    services = normalize_services(pro_config["services"])
    for variant in track_release.setdefault("pro-variants", []):
        if normalize_services(variant["services"]) == services:
            return variant

    variant = {"services": services, "pro": {**pro_config, "services": services}}
    track_release["pro-variants"].append(variant)
    return variant


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-trigger",
        help="Path to the image trigger file.",
        required=True,
    )
    parser.add_argument(
        "--revision-data-file",
        help="Path to the revision data file.",
        required=True,
    )

    args = parser.parse_args()

    logger.info(f"Getting existing image trigger from {args.image_trigger}")
    with open(args.image_trigger, encoding="UTF-8") as trigger:
        image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

    _ = ImageSchema(**image_trigger)

    user_releases = image_trigger.get("release", {})

    logger.info(f"Getting pre-release from {args.revision_data_file}")
    with open(args.revision_data_file, encoding="UTF-8") as revision_data_f:
        revision_data = json.load(revision_data_f)

    _ = RevisionDataSchema(**revision_data)

    new_revision_releases = revision_data["release"]
    new_revision = revision_data["revision"]
    new_revision_pro = revision_data.get("pro")

    # Update "release" from image trigger with new revision releases
    for track, val in new_revision_releases.items():
        pro_config = val.get("pro") or new_revision_pro
        published_track = get_published_track(track, pro_config)
        if published_track not in user_releases:
            user_releases[published_track] = {}

        if "end-of-life" in val:
            user_releases[published_track]["end-of-life"] = val["end-of-life"]

        if pro_config:
            variant = find_or_create_pro_variant(user_releases[published_track], pro_config)
            for risk in val["risks"]:
                variant[risk] = str(new_revision)
            backfill_higher_risks_for_variant(published_track, variant)
            continue

        for risk in val["risks"]:
            user_releases[published_track][risk] = str(new_revision)

    # For every track, we need to backfill the risks
    backfill_higher_risks(user_releases)

    # Overwrite the image trigger with the new release value
    image_trigger["release"] = user_releases

    logger.info(f"Finished merging pre releases:\n{json.dumps(image_trigger)}")
    logger.info(f"Overwriting {args.image_trigger}...")
    with open(args.image_trigger, "w") as trigger:
        yaml.dump(
            image_trigger,
            trigger,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
