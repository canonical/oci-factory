import json
import os
import yaml

from schema.triggers import ReleasesSchema, KNOWN_RISKS_ORDERED


def file_exists(path: str) -> bool:
    """Check is a file exists."""

    return os.path.exists(path)


def parse_releases_trigger(path: str) -> dict:
    """Read and validate the releases trigger, returning its content as JSON."""

    with open(path) as trigger:
        content = yaml.safe_load(trigger)

    return ReleasesSchema(**content)


def backfill_higher_risks(track: str, channel_risks: dict) -> dict:
    """Parses a releases Channel and adds the missing higher risks."""

    # from the most to the least stable
    for i, risk in enumerate(KNOWN_RISKS_ORDERED):
        if risk not in channel_risks:
            if risk == "stable":  # same as i == 0
                # stable never follows other risks, as it is already
                # the lowest one
                continue

            # if there a lower risk to follow?
            if KNOWN_RISKS_ORDERED[i - 1] in channel_risks:
                channel_risks[risk] = f"{track}_{KNOWN_RISKS_ORDERED[i-1]}"

    return channel_risks


def overwrite_releases_trigger_file(path: str, content: ReleasesSchema) -> None:
    """Creates (or overwrites if it already exists) the releases trigger file."""

    with open(path, "w") as tf:
        tf.write(json.dumps(content.__dict__))
