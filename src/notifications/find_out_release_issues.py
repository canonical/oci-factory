import argparse
import json
import sys

from ..shared.release_info import get_revision_to_released_tags


def get_issues_not_in_released_tracks(
    revision_to_released_tags: dict, issue_list: list
) -> list:
    """
    Compares the list of released tracks with the issue titles and returns a list of issue numbers that do not contain any of the released tracks in their title.
    """
    released_tracks = set()
    for revision, tags in revision_to_released_tags.items():
        for tag in tags:
            track = tag.split("_")[0]
            released_tracks.add(f"{track}_{revision}")

    issues_not_in_released_tracks = []
    for issue in issue_list:
        issue_number = issue["number"]
        issue_title = issue["title"]
        if not any(track in issue_title for track in released_tracks):
            issues_not_in_released_tracks.append(issue_number)

    return issues_not_in_released_tracks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "releases_json",
        help="Path to the _releases.json file",
    )
    parser.add_argument(
        "issue_list_json",
        help="JSON string of the issue list obtained from 'gh issue list --json number,title'",
    )

    args = parser.parse_args()

    with open(args.releases_json, "r") as f:
        all_releases = json.load(f)

    if not args.issue_list_json:
        return

    issue_list = json.loads(args.issue_list_json)

    revision_to_released_tags = get_revision_to_released_tags(all_releases)

    issues_not_in_released_tracks = get_issues_not_in_released_tracks(
        revision_to_released_tags, issue_list
    )
    for issue_number in issues_not_in_released_tracks:
        print(issue_number)


if __name__ == "__main__":
    main()
