#!/usr/bin/env python3
"""Download non-EOL rock SBOMs from GitHub, or public and Pro archives from Swift."""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

REPOSITORY = Path(__file__).resolve().parents[1]
# Allow direct execution as well as python3 -m tools.download_sboms.
if __package__ in (None, ""):
    sys.path.insert(0, str(REPOSITORY))

logger = logging.getLogger(__name__)
GITHUB_REPOSITORY = "canonical/oci-factory"


def read_revisions(ref, include_pro=False):
    """Read an immutable release-state snapshot without switching branches."""
    from src.tests.get_released_revisions import _active_tracks, _normalize_tag
    from src.shared import release_info

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=REPOSITORY, text=True
        ).strip()

    if ref is None:
        subprocess.run(
            ["git", "fetch", "origin", "_releases"], cwd=REPOSITORY, check=True
        )
        ref = "FETCH_HEAD"
    commit = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    logger.info("Reading release state at %s", commit)
    revisions = {}
    paths = git("ls-tree", "-r", "--name-only", commit, "oci").splitlines()
    release_files = {"_releases.json"}
    if include_pro:
        release_files.add("_pro_releases.json")
    for path in paths:
        parts = path.split("/")
        if len(parts) != 3 or parts[2] not in release_files:
            continue
        releases = json.loads(git("show", f"{commit}:{path}"))
        targets = release_info.get_tag_mapping_from_all_releases(_active_tracks(releases))
        for tag, target in targets.items():
            try:
                revision = release_info._find_alias_revision(targets, target, set(), tag)
            except (KeyError, release_info.BadChannel):
                logger.warning("Skipping unresolved channel %s", tag)
                continue
            revisions.setdefault((parts[1], str(int(revision))), set()).add(_normalize_tag(tag))
    return revisions


def download_sboms(revisions, output_dir):
    """Download revision-matched release assets once, across all channels."""
    downloaded = 0
    failures = 0
    for image, revision in sorted(revisions):
        # Channel releases are mutable; match the build revision in each filename.
        pattern = re.compile(
            rf"{re.escape(image)}_.+_{re.escape(revision)}"
            r"\.[^.]+(?:\.chiselled)?\.sbom_preview\.spdx\.json"
        )
        assets = {}
        for channel in sorted(revisions[(image, revision)]):
            tag = quote(f"{image}_{channel}", safe="")
            try:
                release = json.loads(subprocess.check_output(
                    ["gh", "api", "--hostname", "github.com",
                     f"repos/{GITHUB_REPOSITORY}/releases/tags/{tag}"],
                    text=True,
                ))
            except subprocess.CalledProcessError:
                logger.warning("Could not read release %s_%s", image, channel)
                continue
            if release["draft"]:
                continue
            for asset in release["assets"]:
                name = asset["name"]
                if "/" not in name and "\\" not in name and pattern.fullmatch(name):
                    assets[name] = asset["id"]
            if assets:
                break
        names = sorted(assets)
        if not names:
            logger.error("No SBOM assets for %s revision %s", image, revision)
            failures += 1
        for name in sorted(names):
            destination = output_dir / image / revision / name
            temporary = destination.with_suffix(destination.suffix + ".part")
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with temporary.open("wb") as stream:
                    subprocess.run(
                        ["gh", "api", "--hostname", "github.com",
                         f"repos/{GITHUB_REPOSITORY}/releases/assets/{assets[name]}",
                         "--header", "Accept: application/octet-stream"],
                        stdout=stream, check=True,
                    )
                temporary.replace(destination)
            except (OSError, subprocess.CalledProcessError) as error:
                temporary.unlink(missing_ok=True)
                logger.error("Could not download %s: %s", name, error)
                failures += 1
                continue
            downloaded += 1
            logger.info("Downloaded %s", destination)
    logger.info("Downloaded %d SBOMs; %d failures", downloaded, failures)
    return failures


def get_swift_connection():
    required = ("OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD",
                "OS_PROJECT_NAME", "OS_STORAGE_URL")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(
            f"Missing Swift credentials: {', '.join(missing)}. "
            "Source your novarc in the current shell: source /path/to/swift.novarc"
        )
    from src.tests.get_released_revisions import get_swift_connection as connect

    return connect()


def download_swift_sboms(connection, container, revisions, output_dir):
    """Download full SBOM ZIPs, preserving their canonical Swift paths."""
    try:
        _, objects = connection.get_container(container, full_listing=True)
    except Exception as error:
        raise RuntimeError(f"Could not list Swift container {container}: {error}") from error
    archives = defaultdict(list)
    for obj in objects:
        name = obj["name"]
        parts = name.split("/")
        if (len(parts) == 4
                and all(part and part not in (".", "..") for part in parts)
                and parts[3].endswith(".sbom_preview.spdx.zip")):
            archives[(parts[0], parts[2])].append(name)

    downloaded = 0
    failures = 0
    for image, revision in sorted(revisions):
        names = archives[(image, revision)]
        if not names:
            logger.error("No SBOM archive for %s revision %s", image, revision)
            failures += 1
        for name in sorted(names):
            destination = output_dir / name
            temporary = destination.with_suffix(destination.suffix + ".part")
            try:
                _, body = connection.get_object(container, name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_bytes(body)
                temporary.replace(destination)
            except Exception as error:
                temporary.unlink(missing_ok=True)
                logger.error("Could not download %s: %s", name, error)
                failures += 1
                continue
            downloaded += 1
            logger.info("Downloaded %s", destination)
    logger.info("Downloaded %d archives; %d failures", downloaded, failures)
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("sboms"),
        help="destination directory (default: sboms)",
    )
    parser.add_argument(
        "--releases-ref",
        help="use a local Git ref instead of fetching origin/_releases",
    )
    parser.add_argument(
        "--swift", action="store_true",
        help="download public and Pro SBOM ZIPs from Swift; source your novarc first",
    )
    parser.add_argument(
        "--container", default=os.getenv("SWIFT_CONTAINER_NAME", "oci-factory"),
        help="Swift container for --swift (default: SWIFT_CONTAINER_NAME or oci-factory)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        connection = get_swift_connection() if args.swift else None
        revisions = read_revisions(
            args.releases_ref, include_pro=args.swift
        )
        if not revisions:
            logger.error("No non-EOL released revisions found")
            return 1
        logger.info("Found %d unique released revisions", len(revisions))
        if args.swift:
            failures = download_swift_sboms(
                connection, args.container, revisions, args.output_dir
            )
        else:
            failures = download_sboms(revisions, args.output_dir)
        return int(bool(failures))
    except ImportError:
        logger.error("Install repository dependencies: python3 -m pip install -r src/tests/requirements.txt")
        return 1
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        logger.error("%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
