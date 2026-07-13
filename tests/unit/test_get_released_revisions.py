import json

import yaml

import src.tests.get_released_revisions as released


def test_build_released_revisions_matrix_marks_pro_tracks(tmp_path, monkeypatch):
    image_dir = tmp_path / "mock-rock"
    image_dir.mkdir()
    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }
    (image_dir / "image.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "release": {
                    "1.0-24.04": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "stable": "1",
                        "pro": pro_config,
                    },
                    "latest": {
                        "end-of-life": "2030-05-01T00:00:00Z",
                        "stable": "2",
                    },
                },
            }
        )
    )
    (image_dir / "_releases.json").write_text(
        json.dumps(
            {
                "1.0-24.04": {
                    "end-of-life": "2030-05-01T00:00:00Z",
                    "stable": {"target": "1"},
                },
                "latest": {
                    "end-of-life": "2030-05-01T00:00:00Z",
                    "stable": {"target": "2"},
                },
            }
        )
    )
    monkeypatch.setattr(
        released,
        "get_image_name_in_registry",
        lambda image, revision: f"ghcr.io/canonical/oci-factory/{image}:tag-{revision}",
    )

    _, matrix = released.build_released_revisions_matrix(str(tmp_path))

    assert matrix == [
        {
            "name": "mock-rock",
            "source-image": "ghcr.io/canonical/oci-factory/mock-rock:tag-1",
            "encrypted-source-image": True,
        },
        {
            "name": "mock-rock",
            "source-image": "ghcr.io/canonical/oci-factory/mock-rock:tag-2",
            "encrypted-source-image": False,
        },
    ]
