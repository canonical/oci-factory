import json

import swiftclient

from src.tests import get_released_revisions


class FakeSwift:
    """Minimal stand-in for a swiftclient Connection backed by a dict.

    Keys are Swift object names (<img>/<track>/<revision>/build_metadata.json)
    and values are the build metadata each of them holds.
    """

    def __init__(self, objects: dict = None):
        self.objects = objects or {}
        self.requested = []

    @property
    def listing(self) -> list:
        return [{"name": name} for name in self.objects]

    def get_container(self, _container: str, **_kwargs) -> tuple:
        return {}, self.listing

    def get_object(self, _container: str, name: str) -> tuple:
        self.requested.append(name)
        content = self.objects[name]
        if isinstance(content, Exception):
            raise content
        return {}, json.dumps(content).encode()


def build_metadata(ignored_vulnerabilities: str = "") -> dict:
    return {"name": "example", "ignored-vulnerabilities": ignored_vulnerabilities}


def test_get_released_pro_images_groups_tags_by_revision_and_skips_eol():
    releases = {
        "1.2-22.04": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "services": ["esm-apps", "esm-infra"],
            "beta": {"target": "42"},
            "edge": {"target": "1.2-22.04_beta"},
        },
        "old-22.04": {
            "end-of-life": "2000-01-01T00:00:00Z",
            "services": ["esm-apps"],
            "stable": {"target": "7"},
        },
        "active-alias": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "services": ["esm-apps"],
            "beta": {"target": "old-22.04_stable"},
        },
    }
    swift = FakeSwift(
        {"example/1.2-22.04/42/build_metadata.json": build_metadata("CVE-1 CVE-2")}
    )

    assert get_released_revisions.get_released_pro_images(
        "example", releases, "ubuntu.azurecr.io", swift, swift.listing
    ) == [
        {
            "name": "example",
            "source-image": "ubuntu.azurecr.io/example",
            "revision": 42,
            "released-tags": ["1.2-22.04_beta", "1.2-22.04_edge"],
            "pro": True,
            "release-file": "_pro_releases.json",
            "ignored-vulnerabilities": "CVE-1 CVE-2",
        }
    ]


def test_get_released_pro_images_normalizes_latest_tags():
    releases = {
        "latest": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "services": ["esm-apps"],
            "beta": {"target": "42"},
            "edge": {"target": "latest_beta"},
        }
    }
    swift = FakeSwift()

    images = get_released_revisions.get_released_pro_images(
        "example", releases, "ubuntu.azurecr.io", swift, swift.listing
    )

    assert images[0]["released-tags"] == ["beta", "edge"]


def test_get_released_pro_images_find_metadata_under_the_undecorated_track():
    # _pro_releases.json is keyed by the decorated Pro track, while Swift stores
    # the build metadata under the undecorated one. Revisions are unique per
    # image, so the lookup must not assume the two tracks match.
    releases = {
        "1.2-fips-22.04": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "services": ["fips-updates"],
            "beta": {"target": "42"},
        }
    }
    swift = FakeSwift(
        {"example/1.2-22.04/42/build_metadata.json": build_metadata("CVE-1")}
    )

    images = get_released_revisions.get_released_pro_images(
        "example", releases, "ubuntu.azurecr.io", swift, swift.listing
    )

    assert images[0]["ignored-vulnerabilities"] == "CVE-1"


def test_get_released_public_images_uses_resolved_active_revisions(monkeypatch):
    monkeypatch.setattr(
        get_released_revisions,
        "get_image_name_in_registry",
        lambda image, revision: f"ghcr.io/canonical/oci-factory/{image}:1.2_{revision}",
    )
    releases = {
        "1.2": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "beta": {"target": "42"},
            "edge": {"target": "1.2_beta"},
        }
    }
    swift = FakeSwift(
        {"example/1.2/42/build_metadata.json": build_metadata("CVE-1 CVE-2")}
    )

    assert get_released_revisions.get_released_public_images(
        "example", releases, swift, swift.listing
    ) == [
        {
            "name": "example",
            "source-image": "ghcr.io/canonical/oci-factory/example:1.2_42",
            "revision": 42,
            "released-tags": [],
            "pro": False,
            "release-file": "_releases.json",
            "ignored-vulnerabilities": "CVE-1 CVE-2",
        }
    ]


def test_get_ignored_vulnerabilities_defaults_to_empty_when_metadata_is_missing():
    swift = FakeSwift({"other/1.2/42/build_metadata.json": build_metadata("CVE-1")})

    assert (
        get_released_revisions.get_ignored_vulnerabilities(
            swift, swift.listing, "example", 42
        )
        == ""
    )
    assert swift.requested == []


def test_get_ignored_vulnerabilities_defaults_to_empty_when_swift_fails():
    swift = FakeSwift(
        {
            "example/1.2/42/build_metadata.json": swiftclient.exceptions.ClientException(
                "boom"
            )
        }
    )

    assert (
        get_released_revisions.get_ignored_vulnerabilities(
            swift, swift.listing, "example", 42
        )
        == ""
    )


def test_registry_lookup_matches_the_exact_revision(monkeypatch):
    class Containers:
        @staticmethod
        def run(*_args, **_kwargs):
            return b'{"Tags": ["1.2_12", "1.2_2"]}'

    class Client:
        containers = Containers()

    monkeypatch.setattr(get_released_revisions.docker, "from_env", Client)

    assert get_released_revisions.get_image_name_in_registry("example", 2) == (
        "ghcr.io/canonical/oci-factory/example:1.2_2"
    )


def test_main_builds_combined_public_and_pro_matrix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        get_released_revisions,
        "get_image_name_in_registry",
        lambda image, revision: f"ghcr.io/canonical/oci-factory/{image}:1.0_{revision}",
    )
    swift = FakeSwift(
        {
            "example/1.0/5/build_metadata.json": build_metadata("CVE-1"),
            "example/1.0-22.04/42/build_metadata.json": build_metadata("CVE-2 CVE-3"),
        }
    )
    monkeypatch.setattr(
        get_released_revisions, "get_swift_connection", lambda: swift
    )

    img_dir = tmp_path / "oci" / "example"
    img_dir.mkdir(parents=True)
    (img_dir / "_releases.json").write_text(
        json.dumps(
            {
                "1.0": {
                    "end-of-life": "2999-01-01T00:00:00Z",
                    "stable": {"target": "5"},
                }
            }
        )
    )
    (img_dir / "_pro_releases.json").write_text(
        json.dumps(
            {
                "1.0-22.04": {
                    "end-of-life": "2999-01-01T00:00:00Z",
                    "services": ["esm-apps"],
                    "beta": {"target": "42"},
                }
            }
        )
    )

    output = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    get_released_revisions.main(
        [
            "--oci-images-path",
            str(tmp_path / "oci"),
            "--acr-registry",
            "ubuntu.azurecr.io",
        ]
    )

    line = output.read_text().strip()
    assert line.startswith("released-revisions-matrix=")
    matrix = json.loads(line.split("=", 1)[1])
    assert matrix == {
        "include": [
            {
                "name": "example",
                "source-image": "ghcr.io/canonical/oci-factory/example:1.0_5",
                "revision": 5,
                "released-tags": [],
                "pro": False,
                "release-file": "_releases.json",
                "ignored-vulnerabilities": "CVE-1",
            },
            {
                "name": "example",
                "source-image": "ubuntu.azurecr.io/example",
                "revision": 42,
                "released-tags": ["1.0-22.04_beta"],
                "pro": True,
                "release-file": "_pro_releases.json",
                "ignored-vulnerabilities": "CVE-2 CVE-3",
            },
        ]
    }
