import pytest

from src.notifications.find_out_release_issues import \
    get_issues_not_in_released_tracks


@pytest.mark.parametrize(
    "revision_to_released_tags, issue_list, issues_to_close",
    [
        (
            {
                143: ["3-24.04_edge", "3.5-24.04_edge", "3.5.8-24.04_edge"],
            },
            [
                {
                    "number": 1,
                    "title": "Vulnerabilities found for mock-rock:3.5.8-24.04_143",
                },
                {
                    "number": 2,
                    "title": "Vulnerabilities found for mock-rock:2.1-24.04_159",
                },
            ],
            [2],
        ),
        (
            {
                143: ["3-24.04_edge", "3.5-24.04_edge", "3.5.8-24.04_edge"],
                159: ["2.1-24.04_edge"],
            },
            [
                {
                    "number": 1,
                    "title": "Vulnerabilities found for mock-rock:3.5.8-24.04_143",
                },
                {
                    "number": 2,
                    "title": "Vulnerabilities found for mock-rock:2.1-24.04_159",
                },
            ],
            [],
        ),
    ],
)
def test_get_issues_not_in_released_tracks(
    revision_to_released_tags, issue_list, issues_to_close
):
    issues_not_in_released_tracks = get_issues_not_in_released_tracks(
        revision_to_released_tags, issue_list
    )
    assert issues_not_in_released_tracks == issues_to_close
