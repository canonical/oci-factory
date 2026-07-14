#!/usr/bin/env python3

import argparse
from typing import Any

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


def normalize_services(services: list[str]) -> list[str]:
    """Return a deterministic Pro services list."""
    return sorted(services)


def non_esm_services(services: list[str]) -> list[str]:
    """Return Pro services that must be represented in published tags."""
    return [service for service in normalize_services(services) if not service.startswith("esm-")]


def get_published_track(track: str, pro: dict[str, Any] | None = None) -> str:
    """Return the public tag track for a release track and optional Pro config."""
    if not pro:
        return track

    tag_services = non_esm_services(pro.get("services", []))
    if not tag_services:
        return track

    version, base = track.rsplit("-", 1)
    return f"{version}-{'-'.join(tag_services)}-{base}"


def get_release_tracks(image_trigger: dict) -> list[dict]:
    """Return all release track definitions from an image trigger."""
    release_tracks = list(image_trigger.get("release", {}).values())
    for upload in image_trigger.get("upload", []) or []:
        for release in upload.get("release", {}).values():
            if upload.get("pro") and not release.get("pro"):
                release = {**release, "pro": upload["pro"]}
            release_tracks.append(release)

    return release_tracks


def get_pro_variants(image_trigger: dict) -> list[dict]:
    """Return all merged Pro variants from the release section."""
    variants = []
    for track, release in image_trigger.get("release", {}).items():
        for variant in release.get("pro-variants", []) or []:
            variants.append({**variant, "track": track})
    return variants


def has_public_tracks(image_trigger: dict) -> bool:
    """Return whether the image trigger has any non-Pro release tracks."""
    root_releases = image_trigger.get("release", {}).values()
    if any(
        any(risk in release for risk in KNOWN_RISKS_ORDERED)
        for release in root_releases
    ):
        return True

    release_tracks = []
    for upload in image_trigger.get("upload", []) or []:
        for release in upload.get("release", {}).values():
            if upload.get("pro") and not release.get("pro"):
                release = {**release, "pro": upload["pro"]}
            release_tracks.append(release)

    if not release_tracks:
        return not has_pro_tracks(image_trigger)

    return any(not release.get("pro") for release in release_tracks)


def has_pro_tracks(image_trigger: dict) -> bool:
    """Return whether the image trigger has any Pro release tracks."""
    return bool(get_pro_variants(image_trigger)) or any(
        release.get("pro") for release in get_release_tracks(image_trigger)
    )


def get_pro_artifact_passphrase_secret(image_trigger: dict) -> str:
    """Return the unique artifact passphrase secret name for Pro release tracks."""
    secrets = {
        release["pro"]["config"]["artifact-passphrase"].removeprefix("secrets.")
        for release in get_release_tracks(image_trigger)
        if release.get("pro")
    }
    secrets.update(
        variant["pro"]["config"]["artifact-passphrase"].removeprefix("secrets.")
        for variant in get_pro_variants(image_trigger)
        if variant.get("pro")
    )

    if not secrets:
        return ""

    if len(secrets) != 1:
        raise ValueError(
            "All Pro release tracks must use the same artifact passphrase."
        )

    return secrets.pop()


def get_pro_revision_refs(
    image_trigger: dict, all_revision_tags: list[str]
) -> list[str]:
    """Return canonical <source-track>_<revision> refs for Pro revisions."""
    pro_revisions = set()
    for variant in get_pro_variants(image_trigger):
        for risk in KNOWN_RISKS_ORDERED:
            target = variant.get(risk)
            if isinstance(target, dict):
                target = target.get("target")
            if target and str(target).isdigit():
                pro_revisions.add(str(target))

    refs = []
    for revision_ref in all_revision_tags:
        if not revision_ref:
            continue
        _, revision = revision_ref.rsplit("_", 1)
        if revision in pro_revisions:
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
