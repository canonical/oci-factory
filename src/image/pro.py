#!/usr/bin/env python3

import argparse

import yaml

from .utils.schema.triggers import KNOWN_RISKS_ORDERED, ImageSchema


def get_track_from_tag(tag: str) -> str:
    """Return the release track represented by a channel tag or stable alias."""
    if tag in KNOWN_RISKS_ORDERED:
        return "latest"

    try:
        track, risk = tag.rsplit("_", 1)
    except ValueError:
        return tag

    if risk in KNOWN_RISKS_ORDERED:
        return track

    return tag


def is_pro_track(image_trigger: dict, track: str) -> bool:
    """Return whether a release track is configured for Ubuntu Pro."""
    return bool(image_trigger.get("release", {}).get(track, {}).get("pro"))


def has_public_tracks(image_trigger: dict) -> bool:
    """Return whether the image trigger has any non-Pro release tracks."""
    release_tracks = list(image_trigger.get("release", {}).values())
    for upload in image_trigger.get("upload", []) or []:
        release_tracks.extend(upload.get("release", {}).values())

    if not release_tracks:
        return True

    return any(not release.get("pro") for release in release_tracks)


def load_image_trigger(image_trigger_path: str) -> dict:
    """Load and validate an image trigger file."""
    with open(image_trigger_path, encoding="UTF-8") as trigger:
        image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

    _ = ImageSchema(**image_trigger)
    return image_trigger


def main():
    parser = argparse.ArgumentParser(description="Inspect Pro settings in image.yaml")
    parser.add_argument("function", choices=["has_public_tracks"])
    parser.add_argument("--image-trigger", required=True)
    args = parser.parse_args()

    image_trigger = load_image_trigger(args.image_trigger)
    if args.function == "has_public_tracks":
        print("true" if has_public_tracks(image_trigger) else "false")


if __name__ == "__main__":
    main()
