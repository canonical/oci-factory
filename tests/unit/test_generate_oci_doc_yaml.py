import pytest
import yaml

import tempfile
from copy import deepcopy
from textwrap import dedent
from unittest.mock import Mock

from src.docs.generate_oci_doc_yaml import MOCK_RELEASE, OCIDocumentationData


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


@pytest.fixture
def documentation_file(tmp_path):
    path = tmp_path / "example" / "documentation.yaml"
    path.parent.mkdir()
    path.write_text(dedent("""\
        version: 2
        application: Example
        description: Example image
        website: https://example.com/
        docker:
          run-conclusion: The service is running.
        """))
    return path


@pytest.mark.parametrize("field", ["override-tracks", "override_tracks"])
@pytest.mark.parametrize("legacy", [True, False])
def test_read_legacy_flag(documentation_file, field, legacy):
    with documentation_file.open("a") as stream:
        stream.write(yaml.safe_dump({field: {"8.0-22.04": {
            "end-of-life": "2099-04-01", "legacy": legacy,
        }}}))
    data = OCIDocumentationData.read_documentation_yaml(documentation_file)
    assert data["override_tracks"] == {
        "8.0-22.04": {"end_of_life": "2099-04-01", "legacy": legacy},
    }
    assert "override-tracks" not in data


@pytest.mark.parametrize("entry", [
    {"legacy": True},
    {"end-of-life": "invalid", "legacy": True},
    {"end-of-life": "2099-04-01", "legacy": "invalid"},
    {"end-of-life": "2099-04-01", "legacy": []},
    {"end-of-life": "2099-04-01", "legacy": {}},
])
def test_invalid_track_override(documentation_file, entry):
    with documentation_file.open("a") as stream:
        stream.write(yaml.safe_dump({"override-tracks": {"8.0-22.04": entry}}))
    with pytest.raises(Exception, match="Error loading"):
        OCIDocumentationData.read_documentation_yaml(documentation_file)


def test_omitted_legacy_flag_preserves_schema(documentation_file):
    assert OCIDocumentationData.read_documentation_yaml(documentation_file)["override_tracks"] is None
    with documentation_file.open("a") as stream:
        stream.write('override-tracks:\n  "8.0-22.04":\n    end-of-life: "2099-04-01"\n')
    assert OCIDocumentationData.read_documentation_yaml(documentation_file)["override_tracks"] == {
        "8.0-22.04": {"end_of_life": "2099-04-01"},
    }


def test_v1_does_not_accept_legacy_flag(documentation_file):
    documentation_file.write_text(yaml.safe_dump({
        "version": 1, "application": "Example",
        "override_tracks": {"8.0-22.04": {"end-of-life": "2099-04-01", "legacy": True}},
    }))
    with pytest.raises(Exception, match="Error loading"):
        OCIDocumentationData.read_documentation_yaml(documentation_file)


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("legacy", [None, False, True])
def test_legacy_flag_pass_through_preserves_releases(documentation_file, monkeypatch, dry_run, legacy):
    override = {"end-of-life": "2000-01-01T00:00:00Z"}
    if legacy is not None:
        override["legacy"] = legacy
    with documentation_file.open("a") as stream:
        stream.write(yaml.safe_dump({"override-tracks": {"9.20-25.04": override}}))
    tracks = ["9.20-25.04", "9.20-26.04", "9.21-26.04", "10-26.04"]
    mocked_releases = [
        {"track": track.rsplit("-", 1)[0], "base": track.rsplit("-", 1)[1],
         "risk": "stable", "tags": [f"{track}_edge"], "architectures": ["amd64", "arm64"],
         "support": {"until": "03/2099"}}
        for track in tracks
    ]
    mocked_releases[0]["support"] = {"until": "01/2000"}
    mocked_releases[0]["deprecated"] = {"date": "01/2000"}
    original = deepcopy(mocked_releases)
    monkeypatch.setattr("src.docs.generate_oci_doc_yaml.MOCK_RELEASE", mocked_releases)
    monkeypatch.setenv("GITHUB_OUTPUT", str(documentation_file.parent / "github-output"))
    runner = OCIDocumentationData("", "", str(documentation_file.parent), "ubuntu", dry_run=True)
    runner.dry_run = dry_run
    if not dry_run:
        # Include a lower-risk alias for the same digest to verify that passing
        # through the flag does not affect representative channel selection.
        pages = [{"imageTagDetails": [
            {"imageDetail": {"imageDigest": str(i)}, "imageTag": f"{track}_{risk}"}
            for i, track in enumerate(tracks) for risk in ("stable", "edge")
        ], "nextToken": "next"}, {"imageTagDetails": [
            {"imageDetail": {"imageDigest": "1"}, "imageTag": "9-24.04_edge"}
        ]}]
        runner.ecr_client = Mock()
        runner.ecr_client.describe_image_tags.side_effect = pages
        eol_dates = {track: "2099-03-25T00:00:00Z" for track in tracks}
        # The override must still supply the expired EOL for this track.
        monkeypatch.setattr(runner, "get_all_tracks", lambda **kwargs: eol_dates)
    runner.main(str(documentation_file.parent / "output"))
    output = documentation_file.parent / "output" / "example_doc_data.yaml"
    data = yaml.safe_load(output.read_text())
    expected_override = {"end_of_life": override["end-of-life"]}
    if legacy is not None:
        expected_override["legacy"] = legacy
    assert data["override_tracks"] == {"9.20-25.04": expected_override}
    expected = deepcopy(original)
    if not dry_run:
        expected[1]["tags"].append("9-24.04_edge")
        assert runner.ecr_client.describe_image_tags.call_count == 2
    assert data["releases"] == expected
    assert mocked_releases == original
    if dry_run:
        first_output = output.read_text()
        runner.main(str(output.parent))
        assert output.read_text() == first_output
        assert mocked_releases == original


def test_dry_run_does_not_contaminate_later_generation(documentation_file, monkeypatch):
    original = deepcopy(MOCK_RELEASE)
    monkeypatch.setenv("GITHUB_OUTPUT", str(documentation_file.parent / "github-output"))
    runner = OCIDocumentationData("", "", str(documentation_file.parent), "ubuntu", dry_run=True)
    initial_doc = documentation_file.read_text()
    documentation_file.write_text(initial_doc + yaml.safe_dump({"override-tracks": {
        "23.456-20.04": {"end-of-life": "2099-04-01", "legacy": True},
    }}))
    runner.main(str(documentation_file.parent / "output"))
    documentation_file.write_text(initial_doc)
    runner.main(str(documentation_file.parent / "output"))
    data = yaml.safe_load((documentation_file.parent / "output" / "example_doc_data.yaml").read_text())
    assert data["releases"] == original
    assert MOCK_RELEASE == original


def test_release_fixture_requires_dry_run(documentation_file, monkeypatch):
    def no_connection(*args):
        pytest.fail("Fixture validation must happen before registry authentication")

    monkeypatch.setattr(OCIDocumentationData, "_ecr_connect", no_connection)
    with pytest.raises(ValueError, match="requires --dry-run"):
        OCIDocumentationData("", "", str(documentation_file.parent), "ubuntu", releases_file="fixture.yaml")


@pytest.mark.parametrize("records", [[], [{
    "track": "8.0.10", "base": "24.04", "risk": "stable", "tags": ["latest"],
    "architectures": ["amd64"], "support": {"until": "04/2099"},
}]])
def test_release_fixture_is_used_and_marked_dry_run(documentation_file, monkeypatch, records):
    path = documentation_file.parent / "releases.yaml"
    path.write_text(yaml.safe_dump(records))
    monkeypatch.setenv("GITHUB_OUTPUT", str(documentation_file.parent / "github-output"))
    runner = OCIDocumentationData("", "", str(documentation_file.parent), "ubuntu",
                                  dry_run=True, releases_file=str(path))
    runner.main(str(documentation_file.parent / "output"))
    data = yaml.safe_load((documentation_file.parent / "output/example_doc_data.yaml").read_text())
    assert data["releases"] == records
    assert data["dry_run"] is True


@pytest.mark.parametrize("records", [None, {}, ["invalid"], [{"track": "8.0"}], [{
    "track": "8.0", "base": "invalid", "risk": "stable", "tags": [], "architectures": [],
}]])
def test_invalid_release_fixture(documentation_file, records):
    from pydantic import ValidationError

    path = documentation_file.parent / "releases.yaml"
    path.write_text(yaml.safe_dump(records))
    runner = OCIDocumentationData("", "", str(documentation_file.parent), "ubuntu",
                                  dry_run=True, releases_file=str(path))
    with pytest.raises(ValidationError):
        runner.main(str(documentation_file.parent / "output"))
