"""Verify real dry-run artifacts produced by the documentation preview workflow."""

import json
import os
from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("DOCS_PREVIEW_DIR"), reason="requires rendered preview artifacts"
)


@pytest.mark.parametrize("payload,field,markdown", [
    ("dockerhub-docs.json", "full_description", "doc-preview.md"),
    ("ecr-docs.json", "aboutText", "ecr-about-preview.md"),
    ("ecr-docs.json", "usageText", "ecr-usage-preview.md"),
])
def test_payload_preserves_markdown(payload, field, markdown):
    folder = Path(os.environ["DOCS_PREVIEW_DIR"])
    assert json.loads((folder / payload).read_text())[field] == (folder / markdown).read_text()


@pytest.mark.parametrize("filename", ["doc-preview.md", "ecr-usage-preview.md"])
def test_example_tags(filename):
    scenario = os.environ["DOCS_PREVIEW_SCENARIO"]
    text = (Path(os.environ["DOCS_PREVIEW_DIR"]) / filename).read_text()
    shell = "\n".join(re.findall(r"```sh\n(.*?)```", text, re.S))
    shell = re.sub(r"\s*\\+\n\s*", " ", shell)
    # The unchanged ECR path truncates the app version when flags are omitted.
    rock_tag = "8.0-24.04_stable" if scenario == "unmarked" and filename == "ecr-usage-preview.md" else "8.0.10-24.04_stable"
    assert f"{scenario}:{rock_tag} plan" in shell
    assert f"{scenario}:{rock_tag} --args service" in shell
    assert "7.0-20.04" not in shell
    if scenario == "eol-legacy":
        assert "For an older version" not in text
        assert "docker inspect" not in shell
        assert "legacy-service" not in shell
    else:
        legacy_tag = "8.0-22.04_stable" if scenario == "mixed" else rock_tag
        assert f"{scenario}:{legacy_tag} legacy-service" in shell
        assert "docker inspect" in shell
    assert "\\\\\n" not in text


@pytest.mark.parametrize("markdown,baseline", [
    ("doc-preview.md", "docker.io/ubuntu/unmarked_doc_data.md"),
    ("ecr-about-preview.md", "public.ecr.aws/ubuntu/unmarked_doc_data.md"),
    ("ecr-usage-preview.md", "public.ecr.aws/ubuntu/usage/unmarked_doc_data.md"),
])
def test_unmarked_matches_deployed_content(markdown, baseline):
    if os.environ["DOCS_PREVIEW_SCENARIO"] != "unmarked":
        pytest.skip("Baseline comparison is for the scenario without legacy flags")
    original = (Path(os.environ["DOCS_BASELINE_DIR"]) / baseline).read_text()
    encoded = "".join(line + "\\n" for line in original.splitlines()).replace('"', '\\"')
    previously_published = json.loads('{"text":"' + encoded + '"}')["text"]
    assert (Path(os.environ["DOCS_PREVIEW_DIR"]) / markdown).read_text() == previously_published
