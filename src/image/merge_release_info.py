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
from .utils.schema.revision_data import RevisionDataSchema
from .utils.schema.triggers import (
    KNOWN_RISKS_ORDERED,
    ImageSchema,
    ImageTriggerValidationError,
)

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


def _assemble_pro_track(_track: str, _pro_services: list[str]) -> str:
    """Assembles the track name with the pro services."""
    # Remove any esm- services from the pro services to form the tag,
    # as they are excluded from the pro track names.
    _pro_services = [ps for ps in _pro_services if not ps.startswith("esm-")]

    if not _pro_services:
        return _track

    version, base = _track.rsplit("-", 1)

    return f"{version}-{'-'.join(sorted(_pro_services))}-{base}"


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

    logger.info(f"Getting pre-release from {args.revision_data_file}")
    with open(args.revision_data_file, encoding="UTF-8") as revision_data_f:
        revision_data = json.load(revision_data_f)

    _ = RevisionDataSchema(**revision_data)

    new_revision_releases = revision_data["release"]
    new_revision = revision_data["revision"]

    pro_entry = revision_data.get("pro", {})
    if not pro_entry:
        logger.info("No pro entry found in revision data.")
        pro_services = []
    else:
        pro_services = pro_entry.get("services", [])

    user_releases = (
        image_trigger.get("pro-release", {})
        if pro_services
        else image_trigger.get("release", {})
    )

    # Update "release" from image trigger with new revision releases
    for track, val in new_revision_releases.items():
        if pro_services:
            track = _assemble_pro_track(track, pro_services)

        if track not in user_releases:
            user_releases[track] = {}

        if pro_services:
            existing_services = user_releases[track].get("services")
            if existing_services and sorted(existing_services) != sorted(pro_services):
                raise ImageTriggerValidationError(
                    f"Pro track '{track}' cannot have different pro service combinations:"
                    f"already got {sorted(existing_services)}, now have {sorted(pro_services)}."
                )

        if "end-of-life" in val:
            user_releases[track]["end-of-life"] = val["end-of-life"]

        for risk in val["risks"]:
            user_releases[track][risk] = str(new_revision)

        if pro_services:
            user_releases[track]["services"] = pro_services

    # For every track, we need to backfill the risks
    backfill_higher_risks(user_releases)

    # Overwrite the image trigger with the new release value
    if pro_services:
        image_trigger["pro-release"] = user_releases
    else:
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
