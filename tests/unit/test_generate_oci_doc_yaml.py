import pytest

import tempfile
from textwrap import dedent

from src.docs.generate_oci_doc_yaml import OCIDocumentationData


REVISION_TAGS = ["3.1.0-24.04_1", "3.1.0-24.04_2", "3.1.0-24.04_3"]


# Mock the OCIDocumentationData.get_arches to return ["amd64", "arm64"] for testing purposes using pytest's monkeypatch fixture
@pytest.fixture(autouse=True)
def mock_get_arches(monkeypatch):
    def mock_get_arches(self, _):
        return ["amd64", "arm64"]

    monkeypatch.setattr(OCIDocumentationData, "get_arches", mock_get_arches)


@pytest.fixture
def releases_json():
    f = tempfile.NamedTemporaryFile(delete=False)
    json_content = dedent(
        """\
        {
            "3-24.04": {
                "end-of-life": "2099-03-25T00:00:00Z",
                "edge": {
                    "target": "3"
                }
            },
            "3.1-24.04": {
                "end-of-life": "2099-03-25T00:00:00Z",
                "edge": {
                    "target": "3"
                },
                "beta": {
                    "target": "3"
                }
            }
        }
        """
    )
    f.write(json_content.encode())
    f.flush()
    f.close()
    return f.name


@pytest.fixture
def release_json_track_has_alias():
    f = tempfile.NamedTemporaryFile(delete=False)
    json_content = dedent(
        """\
        {
            "3-24.04": {
                "end-of-life": "2099-03-25T00:00:00Z",
                "edge": {
                    "target": "3"
                }
            },
            "3.1-24.04": {
                "end-of-life": "2099-03-25T00:00:00Z",
                "edge": {
                    "target": "3-24.04"
                },
                "beta": {
                    "target": "3-24.04"
                }
            }
        }
        """
    )
    f.write(json_content.encode())
    f.flush()
    f.close()
    return f.name


# TODO: This test case won't be used in this PR for now, as this is pending
# the feature of grouping the tags by sha and eol.
@pytest.fixture
def release_json_same_target_has_different_eol():
    f = tempfile.NamedTemporaryFile(delete=False)
    json_content = dedent(
        """\
        {
            "3-24.04": {
                "end-of-life": "2099-03-25T00:00:00Z",
                "edge": {
                    "target": "3"
                }
            },
            "3.1-24.04": {
                "end-of-life": "2098-03-25T00:00:00Z",
                "edge": {
                    "target": "3"
                },
                "beta": {
                    "target": "3"
                }
            }
        }
        """
    )
    f.write(json_content.encode())
    f.flush()
    f.close()
    return f.name


@pytest.mark.parametrize(
    ("releases_file", "expected_releases"),
    [
        (
            "releases_json",
            [
                {
                    "risk": "beta",
                    "track": "3.1",
                    "base": "24.04",
                    "tags": ["3-24.04_edge", "3.1-24.04_edge"],
                    "architectures": ["amd64", "arm64"],
                    "support": {"until": "03/2099"},
                }
            ],
        ),
        (
            "release_json_track_has_alias",
            [
                {
                    "risk": "beta",
                    "track": "3.1",
                    "base": "24.04",
                    "tags": ["3-24.04_edge", "3.1-24.04_edge"],
                    "architectures": ["amd64", "arm64"],
                    "support": {"until": "03/2099"},
                }
            ],
        ),
    ],
)
def test_get_oci_doc_yaml_data(releases_file, request, expected_releases):
    releases_file = request.getfixturevalue(releases_file)
    all_tracks = OCIDocumentationData.get_all_tracks(releases_file)

    all_ecr_tags = {
        "imageTagDetails": [
            {
                "imageDetail": {"imageDigest": "sha256:abc"},
                "imageTag": "3-24.04_edge",
            },
            {
                "imageDetail": {"imageDigest": "sha256:abc"},
                "imageTag": "3.1-24.04_beta",
            },
            {
                "imageDetail": {"imageDigest": "sha256:abc"},
                "imageTag": "3.1-24.04_edge",
            },
        ]
    }

    runner = OCIDocumentationData(
        username="test_user",
        password="test_password",
        image_path="test/image/path",
        repository="test_repository",
        dry_run=True,
    )

    releases = runner.build_releases_data(all_tracks, all_ecr_tags)

    assert releases == expected_releases
