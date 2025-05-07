import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ...shared.logs import get_logger

UBUNTU_DISTRO_INFO = "/usr/share/distro-info/ubuntu.csv"

logger = get_logger()


def is_track_eol(track_value: str, track_name: str | None = None) -> bool:
    """Test if track is EOL, or still valid. Log warning if track_name is provided.

    Args:
        track_value (str): The value of the track, a dictionary containing 'end-of-life'.
        track_name (str | None): The name of the track. Defaults to None.
    Returns:
        bool: True if the track is EOL, False otherwise.
    """
    eol_date = datetime.strptime(
        track_value["end-of-life"],
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    is_eol = eol_date < datetime.now(timezone.utc)

    if is_eol and track_name is not None:
        logger.warning(f'Removing EOL track "{track_name}", EOL: {eol_date}')

    return is_eol


def get_base_eol(base: str) -> datetime:
    """Find the EOL of the Ubuntu base image by reading /usr/share/distro-info/ubuntu.csv.

    Args:
        base (str): The version ID of the base image, e.g., "22.04".
    Returns:
        datetime: The end-of-life date of the base image.
    Raises:
        ValueError: If the base image is not found in the CSV file.
    """
    ubuntu_distros = Path(UBUNTU_DISTRO_INFO).read_text(encoding="UTF-8")
    reader = csv.DictReader(ubuntu_distros.splitlines(), delimiter=",")
    for row in reader:
        if row["version"].rstrip("LTS").strip() == base:
            eol_date = datetime.strptime(
                row["eol"],
                "%Y-%m-%d",
            ).replace(tzinfo=timezone.utc)
            return eol_date

    raise ValueError(f"Base image {base} not found in {UBUNTU_DISTRO_INFO}")


def generate_base_eol_exceed_warning(tracks_eol_exceed_base_eol: list[dict[str, Any]]):
    """Generates markdown table for the tracks that exceed the base image EOL date.

    Args:
        tracks_eol_exceed_base_eol (list[dict[str, Any]]): List of tracks with EOL date exceeding base image's EOL date.
            This list contains dictionaries with keys: 'track', 'base', 'track_eol', and 'base_eol'.
    Returns:
        tuple: A tuple containing the title and text for the warning.
    """
    title = "Found tracks with EOL date exceeding base image's EOL date\n"
    text = "Following tracks have an EOL date that exceeds the base image's EOL date:\n"
    table = "| Track | Base | Track EOL Date | Base EOL Date |\n"
    table += "|-------|------|----------------|---------------|\n"
    for build in tracks_eol_exceed_base_eol:
        table += f"| {build['track']} | {build['base']} | {build['track_eol']} | {build['base_eol']} |\n"
    text += table
    text += "\nPlease check the EOL date of the base image and the track.\n"
    return title, text


def track_eol_exceeds_base_eol(track: str, track_eol: str) -> Optional[dict[str, Any]]:
    """Check if the track EOL date exceeds the base image EOL date.

    Args:
        track (str): The name of the track, e.g., "1.0-22.04".
        track_eol (str): The end-of-life date of the track, e.g., "2024-04-30T00:00:00Z".

    Returns:
        Optional[dict[str, Any]]: Dictionary containing the track name, base image, EOL date, and base image EOL date if the track EOL exceeds the base image EOL date.
        None: If the track EOL date does not exceed the base image EOL date.
    """
    base_version_id = track.split("-")[-1]
    base_eol = get_base_eol(base_version_id)
    eol_date = datetime.strptime(
        track_eol,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)

    if eol_date > base_eol:
        logger.warning(
            f"Track {track} has an EOL date {eol_date} that exceeds the base image EOL date {base_eol}"
        )

        return {
            "track": track,
            "base": f"ubuntu:{base_version_id}",
            "track_eol": eol_date.strftime("%Y-%m-%d"),
            "base_eol": base_eol.strftime("%Y-%m-%d"),
        }

    return None
