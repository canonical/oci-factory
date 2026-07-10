import importlib.util


spec = importlib.util.spec_from_file_location(
    "find_images_to_update",
    "tools/workflow-engine/charms/temporal-worker/oci_factory/activities/find_images_to_update.py",
)
find_images_to_update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(find_images_to_update)


def test_find_release_channels_preserves_pro_from_releases_json():
    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }
    releases = {
        "1.0-24.04": {
            "end-of-life": "2030-05-01T00:00:00Z",
            "stable": {"target": "7"},
            "candidate": {"target": "1.0-24.04_stable"},
            "pro": pro_config,
        },
        "latest": {
            "end-of-life": "2030-05-01T00:00:00Z",
            "stable": {"target": "8"},
        },
    }

    assert find_images_to_update.find_release_channels(releases, 7) == {
        "1.0-24.04": {
            "risks": ["stable", "candidate"],
            "end-of-life": "2030-05-01T00:00:00Z",
            "pro": pro_config,
        }
    }
