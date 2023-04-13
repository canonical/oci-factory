import json
import os
import yaml

from utils.schema.triggers import ReleasesSchema, KNOWN_RISKS_ORDERED


class BadChannel(Exception):
    """Error validating release channel."""
    
    
def file_exists(path: str) -> bool:
    """Check is a file exists."""

    return os.path.exists(path)


def assert_releases_trigger_filename(path: str) -> None:
    """Check if the provided trigger file is properly named."""

    assert path.endswith(
        ("releases.yaml", "releases.yml")
    ), "The releases trigger file must be named releases.yaml"


def parse_releases_trigger(path: str) -> dict:
    """Read and validate the releases trigger, returning its content as JSON."""

    with open(path) as trigger:
        content = yaml.safe_load(trigger)

    return ReleasesSchema(**content)


def backfill_higher_risks(track_name: str, track: dict) -> dict:
    """Parses a releases Channel and adds the missing higher risks."""

    # from the most to the least stable
    for i, risk in enumerate(KNOWN_RISKS_ORDERED):
        if risk not in track:
            if risk == "stable":  # same as i == 0
                # stable never follows other risks, as it is already
                # the lowest one
                continue

            # if there a lower risk to follow?
            if KNOWN_RISKS_ORDERED[i - 1] in track:
                track[risk] = f"{track_name}_{KNOWN_RISKS_ORDERED[i-1]}"

    return track


def overwrite_releases_trigger_file(path: str, content: ReleasesSchema) -> None:
    """Creates (or overwrites if it already exists) the releases trigger file."""

    content_dict = content.dict(exclude_none=True)

    print(f"Overwriting {path} with:\n{json.dumps(content_dict, indent=4)}")
    with open(path, "w") as tf:
        yaml.dump(
            content_dict,
            tf,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
