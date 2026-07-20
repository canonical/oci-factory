import base64
import importlib.util
from pathlib import Path

import yaml


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools/workflow-engine/charms/temporal-worker/oci_factory/activities/"
    "find_images_to_update.py"
)
SPEC = importlib.util.spec_from_file_location("find_images_to_update", MODULE_PATH)
updates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updates)


class SwiftConnection:
    def __init__(self, metadata):
        self.metadata = metadata

    def get_object(self, _container, _name):
        return {}, self.metadata.encode()


class Response:
    def __init__(self, content=b""):
        self.content = content

    def raise_for_status(self):
        return None


def test_find_released_pro_channels_resolves_aliases_and_skips_eol():
    releases = {
        "1.2-22.04": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "services": ["esm-apps"],
            "beta": {"target": "42"},
            "edge": {"target": "1.2-22.04_beta"},
        },
        "old-22.04": {
            "end-of-life": "2000-01-01T00:00:00Z",
            "services": ["esm-apps"],
            "stable": {"target": "1"},
        },
    }

    assert updates.find_released_pro_channels(releases) == {
        42: {
            "1.2-22.04": {
                "end-of-life": "2999-01-01T00:00:00Z",
                "risks": ["beta", "edge"],
                "services": ["esm-apps"],
            }
        }
    }


def test_trigger_pro_rebuild_uses_swift_metadata_without_registry_digest(monkeypatch):
    metadata = """{
        "source": "canonical/example-rock",
        "commit": "deadbeef",
        "directory": "rock",
        "track": "1.2-22.04",
        "base": "ubuntu:22.04",
        "pro-services": "esm-infra,fips",
        "ignored-vulnerabilities": "CVE-1 CVE-2"
    }"""
    monkeypatch.setattr(updates, "image", "example", raising=False)
    monkeypatch.setattr(
        updates,
        "swift_oci_factory_objs",
        [{"name": "example/1.2-22.04/42/build_metadata.json"}],
        raising=False,
    )
    monkeypatch.setattr(
        updates, "swift_conn", SwiftConnection(metadata), raising=False
    )
    monkeypatch.setattr(updates, "SWIFT_CONTAINER", "oci-factory", raising=False)
    monkeypatch.setattr(updates, "ubuntu_release", "22.04", raising=False)
    monkeypatch.setattr(updates, "external_ref_id_prefix", "test", raising=False)
    monkeypatch.setattr(updates, "GITHUB_TOKEN", "token", raising=False)
    monkeypatch.setattr(updates.time, "sleep", lambda _seconds: None)
    request = {}

    def post(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(updates.requests, "post", post)

    updates.trigger_image_rebuild(
        {
            "1.2-fips-22.04": {
                "end-of-life": "2999-01-01T00:00:00Z",
                "services": ["fips", "esm-infra"],
                "beta": {"target": "42"},
                "edge": {"target": "1.2-fips-22.04_beta"},
            }
        },
        pro=True,
    )

    trigger = yaml.safe_load(
        base64.b64decode(request["json"]["inputs"]["b64-image-trigger"])
    )
    assert trigger == {
        "version": 2,
        "upload": [
            {
                "source": "canonical/example-rock",
                "commit": "deadbeef",
                "directory": "rock",
                "pro": {"services": ["esm-infra", "fips"]},
                "ignored-vulnerabilities": ["CVE-1", "CVE-2"],
                "release": {
                    "1.2-22.04": {
                        "end-of-life": "2999-01-01T00:00:00Z",
                        "risks": ["beta", "edge"],
                    }
                },
            }
        ],
    }
    assert request["json"]["ref"] == "main"
    assert request["json"]["inputs"]["upload"] is True
    assert request["json"]["inputs"]["external_ref_id"].startswith(
        "test-pro-example-"
    )
    assert request["url"].endswith("actions/workflows/Image.yaml/dispatches")


def test_public_rebuild_keeps_ecr_channel_discovery(monkeypatch):
    metadata = """{
        "source": "canonical/example-rock",
        "commit": "deadbeef",
        "directory": "rock",
        "track": "1.2-22.04",
        "base": "ubuntu:22.04",
        "ignored-vulnerabilities": "CVE-1",
        "digest": "sha256:abc"
    }"""
    monkeypatch.setattr(updates, "image", "example", raising=False)
    monkeypatch.setattr(
        updates,
        "swift_oci_factory_objs",
        [{"name": "example/1.2-22.04/42/build_metadata.json"}],
        raising=False,
    )
    monkeypatch.setattr(
        updates, "swift_conn", SwiftConnection(metadata), raising=False
    )
    monkeypatch.setattr(updates, "SWIFT_CONTAINER", "oci-factory", raising=False)
    monkeypatch.setattr(updates, "ubuntu_release", "22.04", raising=False)
    monkeypatch.setattr(updates, "external_ref_id_prefix", "test", raising=False)
    monkeypatch.setattr(updates, "GITHUB_TOKEN", "token", raising=False)
    monkeypatch.setattr(updates.time, "sleep", lambda _seconds: None)
    requests = []

    def post(url, **kwargs):
        requests.append((url, kwargs))
        if url.endswith("describeImageTags"):
            return Response(
                b'{"imageTagDetails": [{"imageTag": "1.2-22.04_beta", '
                b'"imageDetail": {"imageDigest": "sha256:abc"}}]}'
            )
        return Response()

    monkeypatch.setattr(updates.requests, "post", post)

    updates.trigger_image_rebuild(
        {
            "1.2-22.04": {
                "end-of-life": "2999-01-01T00:00:00Z",
                "beta": {"target": "42"},
            }
        }
    )

    assert requests[0] == (
        "https://api.us-east-1.gallery.ecr.aws/describeImageTags",
        {
            "json": {
                "repositoryName": "example",
                "maxResults": 1000,
                "registryAliasName": "ubuntu",
            }
        },
    )
    trigger = yaml.safe_load(
        base64.b64decode(requests[1][1]["json"]["inputs"]["b64-image-trigger"])
    )
    assert "pro" not in trigger["upload"][0]
    assert trigger["upload"][0]["release"] == {
        "1.2-22.04": {
            "end-of-life": "2999-01-01T00:00:00Z",
            "risks": ["beta"],
        }
    }
    assert requests[1][1]["json"]["inputs"]["external_ref_id"].startswith(
        "test-example-"
    )
