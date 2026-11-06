import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from tools import download_sboms


NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def test_read_revisions_reuses_eol_filter_and_alias_resolution(monkeypatch):
    from src.tests import get_released_revisions

    monkeypatch.setattr(
        get_released_revisions, "datetime", SimpleNamespace(now=lambda tz: NOW)
    )
    releases = {
        "boundary": {
            "end-of-life": "2026-10-08T00:00:00Z",
            "stable": {"target": "42"},
            "edge": {"target": "boundary_stable"},
        },
        "old": {
            "end-of-life": "2026-10-07T00:00:00Z",
            "stable": {"target": "1"},
        },
        "latest": {
            "beta": {"target": "old_stable"},
            "edge": {"target": "latest_edge"},
        },
    }

    def git(command, **kwargs):
        if command[1] == "rev-parse":
            return "abc123"
        if command[1] == "ls-tree":
            return "oci/example/_releases.json"
        return json.dumps(releases)

    monkeypatch.setattr(download_sboms.subprocess, "check_output", git)
    assert download_sboms.read_revisions("origin/_releases") == {
        ("example", "42"): {"boundary_stable", "boundary_edge"}
    }


def test_swift_connection_requires_sourced_credentials(monkeypatch):
    for name in ("OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD",
                 "OS_PROJECT_NAME", "OS_STORAGE_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="Source your novarc"):
        download_sboms.get_swift_connection()


@pytest.mark.parametrize("ref", [None, "origin/_releases"])
@pytest.mark.parametrize("include_pro", [False, True])
def test_read_revisions_pins_snapshot_and_deduplicates(monkeypatch, ref, include_pro):
    calls = []

    def check_output(command, **kwargs):
        calls.append(command)
        if command[1] == "rev-parse":
            return "abc123\n"
        if command[1] == "ls-tree":
            return (
                "oci/example/_releases.json\n"
                "oci/example/_pro_releases.json\n"
                "oci/example/image.yaml\n"
            )
        if command[2] == "abc123:oci/example/_pro_releases.json":
            assert include_pro
            return json.dumps({"latest": {
                "edge": {"target": "42"}, "beta": {"target": "43"}
            }})
        assert command[2] == "abc123:oci/example/_releases.json"
        return json.dumps({"latest": {"stable": {"target": "42"}}})

    fetches = []
    monkeypatch.setattr(download_sboms.subprocess, "check_output", check_output)
    monkeypatch.setattr(
        download_sboms.subprocess, "run", lambda command, **kwargs: fetches.append(command)
    )

    expected = {("example", "42"): {"stable"}}
    if include_pro:
        expected = {("example", "42"): {"stable", "edge"},
                    ("example", "43"): {"beta"}}
    assert download_sboms.read_revisions(ref, include_pro=include_pro) == expected
    assert bool(fetches) == (ref is None)
    assert calls[0][-1] == f"{ref or 'FETCH_HEAD'}^{{commit}}"


def test_download_sboms_matches_exact_revision_and_deduplicates(tmp_path, monkeypatch):
    names = [
        "example_canonical_42.amd64.sbom_preview.spdx.json",
        "example_canonical_42.arm64.chiselled.sbom_preview.spdx.json",
        "example_canonical_142.amd64.sbom_preview.spdx.json",
        "other_canonical_42.amd64.sbom_preview.spdx.json",
        "../example_canonical_42.amd64.sbom_preview.spdx.json",
        "example_canonical_42.build_metadata.json",
    ]
    downloads = []
    assets = [{"name": name, "id": index} for index, name in enumerate(names)]
    assets.append(assets[0])

    def download(command, stdout, **kwargs):
        downloads.append(command[4])
        stdout.write(b"SBOM JSON")

    monkeypatch.setattr(
        download_sboms.subprocess, "check_output",
        lambda *args, **kwargs: json.dumps({"draft": False, "assets": assets})
    )
    monkeypatch.setattr(download_sboms.subprocess, "run", download)
    assert download_sboms.download_sboms(
        {("example", "42"): {"track_beta", "track_edge"}}, tmp_path
    ) == 0
    assert downloads == [
        "repos/canonical/oci-factory/releases/assets/0",
        "repos/canonical/oci-factory/releases/assets/1",
    ]
    assert (tmp_path / "example" / "42" / names[0]).read_bytes() == b"SBOM JSON"
    assert len(list(tmp_path.rglob("*.json"))) == 2
    assert not list(tmp_path.rglob("*.part"))


def test_download_sboms_reports_failures_and_continues(tmp_path, caplog, monkeypatch):
    names = [
        "example_track_42.amd64.sbom_preview.spdx.json",
        "example_track_43.amd64.sbom_preview.spdx.json",
    ]
    existing = tmp_path / "example" / "42" / names[0]
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing archive")

    def download(command, stdout, **kwargs):
        stdout.write(b"partial download")
        if command[4].endswith("/0"):
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(
        download_sboms.subprocess, "check_output", lambda *args, **kwargs: json.dumps(
            {"draft": False, "assets": [
                {"name": name, "id": index} for index, name in enumerate(names)
            ]}
        )
    )
    monkeypatch.setattr(download_sboms.subprocess, "run", download)
    assert download_sboms.download_sboms(
        {("example", "42"): {"beta"}, ("example", "43"): {"edge"},
         ("missing", "1"): {"stable"}},
        tmp_path,
    ) == 2
    assert existing.read_bytes() == b"existing archive"
    assert (tmp_path / "example" / "43" / names[1]).read_bytes() == b"partial download"
    assert not list(tmp_path.rglob("*.part"))
    assert "No SBOM assets for missing revision 1" in caplog.text


@pytest.mark.parametrize("failures", [0, 1])
def test_main_exit_status(monkeypatch, tmp_path, failures):
    monkeypatch.setattr(
        download_sboms, "read_revisions", lambda *args, **kwargs: {("rock", "1"): {"edge"}}
    )
    monkeypatch.setattr(download_sboms, "download_sboms", lambda *args: failures)
    assert download_sboms.main(["--output-dir", str(tmp_path)]) == failures


def test_main_handles_git_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git", "fetch"])

    monkeypatch.setattr(download_sboms, "read_revisions", fail)
    assert download_sboms.main([]) == 1


def test_download_sboms_falls_back_to_another_channel(tmp_path, monkeypatch):
    name = "example_track_42.amd64.sbom_preview.spdx.json"
    responses = iter([
        subprocess.CalledProcessError(1, ["gh", "api"]),
        {"draft": True, "assets": [{"name": name, "id": 1}]},
        {"draft": False, "assets": [
            {"name": "example_track_142.amd64.sbom_preview.spdx.json", "id": 2}
        ]},
        {"draft": False, "assets": [{"name": name, "id": 3}]},
    ])

    def check_output(*args, **kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response)

    def download(command, stdout, **kwargs):
        assert command[4].endswith("/3")
        stdout.write(b"SBOM")

    monkeypatch.setattr(download_sboms.subprocess, "check_output", check_output)
    monkeypatch.setattr(download_sboms.subprocess, "run", download)
    assert download_sboms.download_sboms(
        {("example", "42"): {"a", "b", "c", "d"}}, tmp_path
    ) == 0
    assert (tmp_path / "example" / "42" / name).read_bytes() == b"SBOM"


def test_download_swift_sboms_matches_revisions_and_continues(tmp_path, caplog):
    names = [
        "example/track/42/example_track_42.sbom_preview.spdx.zip",
        "example/track/43/example_track_43.sbom_preview.spdx.zip",
        "example/track/142/example_track_142.sbom_preview.spdx.zip",
        "example/../43/unsafe.sbom_preview.spdx.zip",
        "example/track/43/build_metadata.json",
    ]
    existing = tmp_path / names[0]
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old archive")
    downloaded = []

    def get_object(container, name):
        assert container == "custom"
        downloaded.append(name)
        if name == names[0]:
            raise OSError("download failed")
        return {}, b"complete ZIP"

    connection = SimpleNamespace(
        get_container=lambda container, **kwargs: ({}, [{"name": n} for n in names]),
        get_object=get_object,
    )
    assert download_sboms.download_swift_sboms(
        connection, "custom", {("example", "42"), ("example", "43"), ("missing", "1")},
        tmp_path,
    ) == 2
    assert downloaded == names[:2]
    assert existing.read_bytes() == b"old archive"
    assert (tmp_path / names[1]).read_bytes() == b"complete ZIP"
    assert not list(tmp_path.rglob("*.part"))
    assert "No SBOM archive for missing revision 1" in caplog.text


def test_swift_listing_failure():
    def fail(*args, **kwargs):
        raise OSError("authentication failed")

    with pytest.raises(RuntimeError, match="Could not list Swift container"):
        download_sboms.download_swift_sboms(
            SimpleNamespace(get_container=fail), "test", {}, None
        )


@pytest.mark.parametrize("failures", [0, 1])
def test_main_swift_mode(monkeypatch, tmp_path, failures):
    connection = object()
    revisions = {("example", "42"): {"edge"}}

    def read(ref, include_pro=False):
        assert include_pro
        return revisions

    def download(conn, container, selected, output):
        assert conn is connection
        assert container == "custom"
        assert selected == revisions
        assert output == tmp_path
        return failures

    monkeypatch.setattr(download_sboms, "read_revisions", read)
    monkeypatch.setattr(download_sboms, "get_swift_connection", lambda: connection)
    monkeypatch.setattr(download_sboms, "download_swift_sboms", download)
    assert download_sboms.main([
        "--swift", "--container", "custom", "--output-dir", str(tmp_path)
    ]) == failures
