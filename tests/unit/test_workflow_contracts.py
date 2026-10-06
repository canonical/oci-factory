import os
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHANGED_WORKFLOW_AND_ACTION_FILES = (
    ".github/workflows/Build-Rock.yaml",
    ".github/workflows/Continuous-Testing.yaml",
    ".github/workflows/Image.yaml",
    ".github/workflows/Release.yaml",
    ".github/workflows/Test-Rock.yaml",
    ".github/workflows/Vulnerability-Scan.yaml",
    ".github/actions/check-kev/action.yaml",
    ".github/actions/commit-releases-json/action.yaml",
    ".github/actions/fetch-releases-json/action.yaml",
)


def load_yaml(relative_path: str) -> dict[str, Any]:
    with (ROOT / relative_path).open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=yaml.BaseLoader)


def iter_uses(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uses":
                yield child
            yield from iter_uses(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_uses(child)


def step_named(
    workflow: dict[str, Any], job_name: str, step_name: str
) -> dict[str, Any]:
    steps = workflow["jobs"][job_name]["steps"]
    return next(step for step in steps if step.get("name") == step_name)


def test_local_uses_references_in_changed_files_exist() -> None:
    missing = []
    for relative_path in CHANGED_WORKFLOW_AND_ACTION_FILES:
        document = load_yaml(relative_path)
        for reference in iter_uses(document):
            if not reference.startswith("./"):
                continue
            target = ROOT / reference.removeprefix("./")
            if not target.exists():
                missing.append(f"{relative_path}: {reference}")
            elif target.is_dir() and not any(
                (target / action_file).is_file()
                for action_file in ("action.yaml", "action.yml")
            ):
                missing.append(f"{relative_path}: {reference} has no action metadata")

    assert not missing, "Missing local uses targets:\n" + "\n".join(missing)


def test_image_uses_fixed_pro_secret_names() -> None:
    workflow = load_yaml(".github/workflows/Image.yaml")
    build_secrets = workflow["jobs"]["build-rock"]["secrets"]
    test_secrets = workflow["jobs"]["test-rock"]["secrets"]

    assert "secrets.ROCKS_PRO_TOKEN" in build_secrets["pro-token"]
    assert (
        "secrets.ROCKS_PRO_ARTIFACT_PASSPHRASE"
        in build_secrets["pro-artifact-passphrase"]
    )
    assert (
        "secrets.ROCKS_PRO_ARTIFACT_PASSPHRASE"
        in test_secrets["pro-artifact-passphrase"]
    )

    secret_values = "\n".join(
        value
        for value in (*build_secrets.values(), *test_secrets.values())
        if isinstance(value, str)
    )
    assert not re.search(r"secrets\s*\[\s*matrix\.", secret_values)


def test_release_steps_keep_public_and_pro_release_files_separate() -> None:
    workflow = load_yaml(".github/workflows/Release.yaml")

    pro_publish = step_named(
        workflow, "do-releases", "Do Pro releases from ${{ inputs.oci-image-name }}"
    )["run"]
    pro_update = step_named(workflow, "do-releases", "Update _pro_releases.json")["run"]
    public_publish = step_named(
        workflow, "do-releases", "Do releases from ${{ inputs.oci-image-name }}"
    )["run"]
    public_update = step_named(workflow, "do-releases", "Update _releases.json")["run"]

    for command in (pro_publish, pro_update):
        assert (
            "--all-releases oci/${INPUTS_OCI_IMAGE_NAME}/_pro_releases.json" in command
        )
        assert "--pro" in command

    for command in (public_publish, public_update):
        assert "--all-releases oci/${INPUTS_OCI_IMAGE_NAME}/_releases.json" in command
        assert "_pro_releases.json" not in command


def test_image_publishing_depends_on_successful_tests() -> None:
    jobs = load_yaml(".github/workflows/Image.yaml")["jobs"]

    assert jobs["test-rock"]["uses"] == "./.github/workflows/Test-Rock.yaml"
    assert "test-rock" in jobs["prepare-upload"]["needs"]
    assert "prepare-upload" in jobs["upload"]["needs"]


def test_test_rock_caches_encrypted_archive_and_decrypts_per_job() -> None:
    workflow = load_yaml(".github/workflows/Test-Rock.yaml")

    # The `encrypted-artifact` input is gone; Pro is detected via the passphrase.
    assert "encrypted-artifact" not in workflow["on"]["workflow_call"]["inputs"]

    # configure-tests caches the (possibly gpg-encrypted) archive as-is, never a
    # decrypted/unpacked layout, under the run-scoped key.
    cache_step = step_named(workflow, "configure-tests", "Cache Rock")
    assert cache_step["uses"].startswith("actions/cache/save@")
    cache_path = cache_step["with"]["path"]
    assert "${{ inputs.oci-archive-name }}" in cache_path
    assert "${{ inputs.oci-archive-name }}.gpg" in cache_path

    consuming_jobs = (
        "test-oci-compliance",
        "test-black-box",
        "test-efficiency",
        "test-vulnerabilities",
        "test-malware",
    )
    for job_name in consuming_jobs:
        steps = workflow["jobs"][job_name]["steps"]

        # Each consuming job decrypts locally, gated on the passphrase presence
        # (not on any removed encrypted-artifact flag).
        decrypt = next(step for step in steps if step.get("name") == "Decrypt Rock")
        assert decrypt["uses"] == "./.github/actions/crypt-artifact"
        assert decrypt["if"] == "${{ env.ARTIFACT_PASSPHRASE != '' }}"
        assert decrypt["with"]["input-path"] == "${{ inputs.oci-archive-name }}.gpg"

        # No leftovers from the previous per-job composite / gating approach.
        for step in steps:
            assert step.get("uses") != "./.github/actions/prepare-rock-for-testing"
            assert "encrypted-artifact" not in str(step.get("if", ""))

    # The composite action it replaced must be gone.
    assert not (ROOT / ".github/actions/prepare-rock-for-testing").exists()


def test_commit_release_action_handles_public_and_pro_state_independently() -> None:
    action = load_yaml(".github/actions/commit-releases-json/action.yaml")
    commit_step = next(
        step
        for step in action["runs"]["steps"]
        if step.get("name") == "commit _releases.json"
    )
    script = commit_step["run"]

    assert "for release_file in _releases.json _pro_releases.json" in script
    assert 'if [[ -f "$path" ]]' in script
    assert 'git add -- "${release_files[@]}"' in script


def test_vulnerability_scan_pro_inputs_are_optional_and_backward_compatible() -> None:
    workflow = load_yaml(".github/workflows/Vulnerability-Scan.yaml")
    inputs = workflow["on"]["workflow_call"]["inputs"]

    # The new Pro inputs must be optional with defaults that reproduce the
    # existing (public) behavior, so external callers are not affected.
    for name, default in (("pro", "false"), ("released-tags", "")):
        assert inputs[name]["required"] == "false"
        assert inputs[name]["default"] == default

    # Pre-existing inputs must remain untouched (no removed/newly-required ones).
    assert inputs["oci-image-name"]["required"] == "true"
    for name in (
        "oci-image-path",
        "trivyignore-path",
        "date-last-scan",
        "create-issue",
    ):
        assert inputs[name]["required"] == "false"
    assert inputs["date-last-scan"]["type"] == "string"
    assert inputs["date-last-scan"]["default"] == "9999-12-31T23:59:59"


def test_vulnerability_scan_uses_acr_credentials_only_for_pro() -> None:
    workflow = load_yaml(".github/workflows/Vulnerability-Scan.yaml")
    configure_step = next(
        step
        for step in workflow["jobs"]["configure-scan"]["steps"]
        if step.get("id") == "configure"
    )
    script = configure_step["run"]

    assert 'if [ "${INPUTS_PRO}" = "true" ]' in script
    assert configure_step["env"]["ACR_CREDS_USR"] == "${{ secrets.ACR_CREDS_USR }}"
    assert configure_step["env"]["ACR_CREDS_PSW"] == "${{ secrets.ACR_CREDS_PSW }}"


def test_vulnerability_workflow_scans_once_and_uploads_enriched_predicate() -> None:
    workflow = load_yaml(".github/workflows/Test-Rock.yaml")
    steps = workflow["jobs"]["test-vulnerabilities"]["steps"]
    scan = step_named(workflow, "test-vulnerabilities", "Scan for vulnerabilities")
    scans = [
        step
        for step in steps
        if step.get("uses", "").startswith("aquasecurity/trivy-action@")
    ]
    assert scans == [scan]
    assert not any(
        step.get("uses") == "./.github/actions/check-trivyignore" for step in steps
    )
    assert scan["with"]["format"] == "json"
    assert scan["with"]["ignore-unfixed"] == "false"
    assert scan["with"]["list-all-pkgs"] == "true"
    assert "trivyignores" not in scan["with"]
    assert "skip-files" not in scan["with"]
    assert "severity" not in scan["with"]
    assert scan["with"]["exit-code"] == "0"
    assert scan["env"]["TRIVY_IGNOREFILE"] == "/dev/null"
    convert = step_named(
        workflow, "test-vulnerabilities", "Convert vulnerability reports"
    )
    assert "trivy convert --format cosign-vuln" in convert["run"]
    assert "trivy convert --format sarif" in convert["run"]
    assert 'embed "$SARIF_REPORT" "$COSIGN_REPORT"' in convert["run"]
    assert convert["env"]["TRIVY_IGNOREFILE"] == "/dev/null"

    process = step_named(
        workflow, "test-vulnerabilities", "Process SARIF vulnerability report"
    )
    assert '--trivyignore "$TRIVYIGNORE_PATH"' in process["run"]
    assert process["env"]["TRIVYIGNORE_PATH"] == (
        "${{ steps.configure-trivy.outputs.trivyignore-path }}"
    )
    upload = step_named(
        workflow, "test-vulnerabilities", "Upload enriched vulnerability report"
    )
    gate = step_named(workflow, "test-vulnerabilities", "Enforce vulnerability policy")
    assert steps.index(process) < steps.index(upload) < steps.index(gate)
    assert upload["with"]["path"] == "${{ steps.configure-trivy.outputs.report-name }}"
    assert "steps.process-sarif-report.outcome == 'success'" in upload["if"]
    assert "steps.process-sarif-report.outputs.blocking-found == 'true'" in gate["if"]


def test_daily_scan_consumes_the_embedded_sarif_artifact() -> None:
    workflow = load_yaml(".github/workflows/Vulnerability-Scan.yaml")
    downloads = [
        step
        for step in workflow["jobs"]["parse-results"]["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    ]
    assert len(downloads) == 1
    process = step_named(workflow, "parse-results", "Process report")
    assert 'findings "$VULNERABILITY_REPORT"' in process["run"]
    assert "--notification-report" not in process["run"]


@pytest.mark.parametrize(
    "issue_exists, notify, operation",
    [
        ("false", "true", "create"),
        ("false", "false", "create"),
        ("true", "true", "edit"),
        ("true", "false", "nop"),
    ],
)
def test_vulnerability_findings_create_or_update_issue(
    issue_exists: str, notify: str, operation: str
) -> None:
    workflow = load_yaml(".github/workflows/Vulnerability-Scan.yaml")
    step = step_named(workflow, "issue", "Notify via GitHub issue")
    assert step["if"] == (
        "${{ steps.create-markdown.outputs.vulnerability-exists == 'true' && inputs.create-issue }}"
    )
    assert step["env"]["NEEDS_PARSE_RESULTS_OUTPUTS_NOTIFY"] == (
        "${{ needs.parse-results.outputs.notify }}"
    )
    result = subprocess.run(
        ["bash", "-e", "-c", 'gh() { printf "%s\\n" "$@"; };\n' + step["run"]],
        env={
            **os.environ,
            "RUNNER_DEBUG": "0",
            "NEEDS_PARSE_RESULTS_OUTPUTS_NOTIFY": notify,
            "STEPS_ISSUE_EXISTS_OUTPUTS_ISSUE_EXISTS": issue_exists,
            "STEPS_ISSUE_EXISTS_OUTPUTS_ISSUE_NUMBER": "42",
            "STEPS_GET_IMAGE_REPO_OUTPUTS_IMG_REPO": "canonical/image",
            "STEPS_CREATE_MARKDOWN_OUTPUTS_ISSUE_TITLE": "Vulnerabilities found",
            "STEPS_CREATE_MARKDOWN_OUTPUTS_ISSUE_BODY_FILE": "issue.md",
        },
        check=True,
        capture_output=True,
        text=True,
    )
    expected = (
        []
        if operation == "nop"
        else [
            "issue",
            operation,
            *(["42"] if issue_exists == "true" else []),
            "--repo",
            "canonical/image",
            "--title",
            "Vulnerabilities found",
            "--body-file",
            "issue.md",
        ]
    )
    assert result.stdout.splitlines() == expected


def test_continuous_testing_forwards_pro_matrix_fields() -> None:
    workflow = load_yaml(".github/workflows/Continuous-Testing.yaml")

    prepare = step_named(workflow, "prepare-test-matrix", "Prepare test matrix")
    assert "--acr-registry" in prepare["run"]
    assert prepare["env"]["ACR_REGISTRY"] == "${{ secrets.ACR_REGISTRY }}"

    run_tests_with = workflow["jobs"]["run-tests"]["with"]
    assert run_tests_with["pro"] == "${{ matrix.pro }}"
    assert run_tests_with["released-tags"] == "${{ join(matrix.released-tags, ',') }}"
    # Pro images are pulled with an explicit tag; public keep the bare source.
    assert "matrix.released-tags[0]" in run_tests_with["oci-image-name"]
    assert (
        workflow["jobs"]["run-tests"]["uses"]
        == "./.github/workflows/Vulnerability-Scan.yaml"
    )
    assert workflow["jobs"]["run-tests"]["secrets"] == "inherit"
