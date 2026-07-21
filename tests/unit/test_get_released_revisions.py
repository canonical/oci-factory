import json

from src.tests import get_released_revisions


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

    assert get_released_revisions.get_released_pro_images(
        "example", releases, "ubuntu.azurecr.io"
    ) == [
        {
            "name": "example",
            "source-image": "ubuntu.azurecr.io/example",
            "revision": 42,
            "released-tags": ["1.2-22.04_beta", "1.2-22.04_edge"],
            "pro": True,
            "release-file": "_pro_releases.json",
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

    images = get_released_revisions.get_released_pro_images(
        "example", releases, "ubuntu.azurecr.io"
    )

    assert images[0]["released-tags"] == ["beta", "edge"]


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

    assert get_released_revisions.get_released_public_images(
        "example", releases
    ) == [
        {
            "name": "example",
            "source-image": "ghcr.io/canonical/oci-factory/example:1.2_42",
            "revision": 42,
            "released-tags": [],
            "pro": False,
            "release-file": "_releases.json",
        }
    ]


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
            },
            {
                "name": "example",
                "source-image": "ubuntu.azurecr.io/example",
                "revision": 42,
                "released-tags": ["1.0-22.04_beta"],
                "pro": True,
                "release-file": "_pro_releases.json",
            },
        ]
    }
