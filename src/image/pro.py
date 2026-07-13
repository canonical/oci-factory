#!/usr/bin/env python3

import argparse

import yaml

import src.shared.release_info as shared

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


def get_release_tracks(image_trigger: dict) -> list[dict]:
    """Return all release track definitions from an image trigger."""
    release_tracks = list(image_trigger.get("release", {}).values())
    for upload in image_trigger.get("upload", []) or []:
        for release in upload.get("release", {}).values():
            if upload.get("pro") and not release.get("pro"):
                release = {**release, "pro": upload["pro"]}
            release_tracks.append(release)

    return release_tracks


def has_public_tracks(image_trigger: dict) -> bool:
    """Return whether the image trigger has any non-Pro release tracks."""
    release_tracks = get_release_tracks(image_trigger)

    if not release_tracks:
        return True

    return any(not release.get("pro") for release in release_tracks)


def has_pro_tracks(image_trigger: dict) -> bool:
    """Return whether the image trigger has any Pro release tracks."""
    return any(release.get("pro") for release in get_release_tracks(image_trigger))


def get_pro_artifact_passphrase_secret(image_trigger: dict) -> str:
    """Return the unique artifact passphrase secret name for Pro release tracks."""
    secrets = {
        release["pro"]["config"]["artifact-passphrase"].removeprefix("secrets.")
        for release in get_release_tracks(image_trigger)
        if release.get("pro")
    }

    if not secrets:
        return ""

    if len(secrets) != 1:
        raise ValueError("All Pro release tracks must use the same artifact passphrase.")

    return secrets.pop()


def get_pro_revision_refs(image_trigger: dict, all_revision_tags: list[str]) -> list[str]:
    """Return canonical <track>_<revision> refs whose track is configured for Pro."""
    refs = []
    for revision_ref in all_revision_tags:
        if not revision_ref:
            continue
        track, _ = revision_ref.rsplit("_", 1)
        if is_pro_track(image_trigger, track):
            refs.append(revision_ref)
    return refs


def load_image_trigger(image_trigger_path: str) -> dict:
    """Load and validate an image trigger file."""
    with open(image_trigger_path, encoding="UTF-8") as trigger:
        image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

    _ = ImageSchema(**image_trigger)
    return image_trigger


def main():
    parser = argparse.ArgumentParser(description="Inspect Pro settings in image.yaml")
    parser.add_argument(
        "function",
        choices=[
            "has_public_tracks",
            "has_pro_tracks",
            "pro_revision_refs",
            "pro_artifact_passphrase_secret",
        ],
    )
    parser.add_argument("--image-trigger", required=True)
    parser.add_argument("--all-revision-tags", required=False, default="")
    args = parser.parse_args()

    image_trigger = load_image_trigger(args.image_trigger)
    if args.function == "has_public_tracks":
        print("true" if has_public_tracks(image_trigger) else "false")
    elif args.function == "has_pro_tracks":
        print("true" if has_pro_tracks(image_trigger) else "false")
    elif args.function == "pro_revision_refs":
        for revision_ref in get_pro_revision_refs(
            image_trigger, shared.get_all_revision_tags(args.all_revision_tags)
        ):
            print(revision_ref)
    elif args.function == "pro_artifact_passphrase_secret":
        print(get_pro_artifact_passphrase_secret(image_trigger))


if __name__ == "__main__":
    main()
