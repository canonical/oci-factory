import logging
from datetime import datetime, timezone
from typing import Any, Optional


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
        logging.warning(f'Removing EOL track "{track_name}", EOL: {eol_date}')

    return is_eol


def calculate_base_eol(base_year: int, base_month: int) -> datetime:
    """Calculate the end-of-life date of the base image.

    Args:
        base_year (int): The year of the base image.
        base_month (int): The month of the base image.
    Returns:
        datetime: The end-of-life date of the base image.
    """
    if base_year < 2000:
        base_year += 2000
    if base_year % 2 == 0 and base_month == 4:  # LTS
        year = base_year + 5
        month = base_month
    else:
        year = base_year + 1
        month = (base_month + 9) % 12

    return datetime(
        year=year,
        month=month,
        day=1,
        tzinfo=timezone.utc,
    )


def generate_base_eol_exceed_warning(tracks_eol_exceed_base_eol: list[dict[str, Any]]):
    """Generates markdown table for the tracks that exceed the base image EOL date.

    Args:
        tracks_eol_exceed_base_eol (list[dict[str, Any]]): List of tracks with EOL date exceeding base image's EOL date.
            This list contains dictionaries with keys: 'track', 'base', 'eol_date', and 'base_eol'.
    Returns:
        tuple: A tuple containing the title and text for the warning.
    """
    title = "Found tracks with EOL date exceeding base image's EOL date\n"
    text = "Following tracks have an EOL date that exceeds the base image's EOL date:\n"
    text += "Please check the EOL date of the base image and the track.\n"
    table = "| Track | Base | EOL Date | Base Image EOL Date |\n"
    table += "|-------|------|----------|---------------------|\n"
    for build in tracks_eol_exceed_base_eol:
        table += f"| {build['track']} | {build['base']} | {build['eol_date']} | {build['base_eol']} |\n"
    return title, text + table


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
    base_year, base_month = map(int, base_version_id.split("."))
    base_eol = calculate_base_eol(base_year, base_month)
    eol_date = datetime.strptime(
        track_eol,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)

    if eol_date > base_eol:
        logging.warning(
            f"Track {track} has an EOL date {eol_date} that exceeds the base image EOL date {base_eol}"
        )

        return {
            "track": track,
            "base": f"ubuntu:{base_version_id}",
            "eol_date": eol_date,
            "base_eol": base_eol,
        }

    return None
