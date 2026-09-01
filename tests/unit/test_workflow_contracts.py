import re
from pathlib import Path
from typing import Any, Iterator

import yaml


ROOT = Path(__file__).resolve().parents[2]
CHANGED_WORKFLOW_AND_ACTION_FILES = (
    ".github/workflows/Build-Rock.yaml",
    ".github/workflows/Image.yaml",
    ".github/workflows/Release.yaml",
    ".github/workflows/Test-Rock.yaml",
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


def step_named(workflow: dict[str, Any], job_name: str, step_name: str) -> dict[str, Any]:
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
    assert "secrets.ROCKS_PRO_ARTIFACT_PASSPHRASE" in test_secrets[
        "pro-artifact-passphrase"
    ]

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
    pro_update = step_named(workflow, "do-releases", "Update _pro_releases.json")[
        "run"
    ]
    public_publish = step_named(
        workflow, "do-releases", "Do releases from ${{ inputs.oci-image-name }}"
    )["run"]
    public_update = step_named(workflow, "do-releases", "Update _releases.json")[
        "run"
    ]

    for command in (pro_publish, pro_update):
        assert "--all-releases oci/${INPUTS_OCI_IMAGE_NAME}/_pro_releases.json" in command
        assert "--pro" in command

    for command in (public_publish, public_update):
        assert "--all-releases oci/${INPUTS_OCI_IMAGE_NAME}/_releases.json" in command
        assert "_pro_releases.json" not in command


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
        step for step in action["runs"]["steps"] if step.get("name") == "commit _releases.json"
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
        "ignored-vulnerabilities",
        "date-last-scan",
        "create-issue",
    ):
        assert inputs[name]["required"] == "false"


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


def test_continuous_testing_forwards_pro_matrix_fields() -> None:
    workflow = load_yaml(".github/workflows/Continuous-Testing.yaml")

    prepare = step_named(
        workflow, "prepare-test-matrix", "Prepare test matrix"
    )
    assert "--acr-registry" in prepare["run"]
    assert prepare["env"]["ACR_REGISTRY"] == "${{ secrets.ACR_REGISTRY }}"

    run_tests_with = workflow["jobs"]["run-tests"]["with"]
    assert run_tests_with["pro"] == "${{ matrix.pro }}"
    assert run_tests_with["released-tags"] == "${{ join(matrix.released-tags, ',') }}"
    # Pro images are pulled with an explicit tag; public keep the bare source.
    assert "matrix.released-tags[0]" in run_tests_with["oci-image-name"]


def test_continuous_testing_keeps_the_swift_build_metadata_lookup() -> None:
    workflow = load_yaml(".github/workflows/Continuous-Testing.yaml")
    prepare_job = workflow["jobs"]["prepare-test-matrix"]

    # Swift is only reachable from the private endpoint runners.
    assert prepare_job["runs-on"] == "self-hosted-linux-amd64-noble-private-endpoint-small"

    # The matrix builder needs both the ACR registry (Pro images) and the Swift
    # credentials (v2 'ignored-vulnerabilities' from the build metadata).
    env = step_named(workflow, "prepare-test-matrix", "Prepare test matrix")["env"]
    for name in (
        "OS_AUTH_URL",
        "OS_USERNAME",
        "OS_PASSWORD",
        "OS_PROJECT_NAME",
        "OS_STORAGE_URL",
    ):
        assert env[name].startswith("${{ secrets.SWIFT_")
    assert env["SWIFT_CONTAINER_NAME"] == "${{ vars.SWIFT_CONTAINER_NAME }}"


def test_continuous_testing_keeps_trivyignore_and_ignored_vulns_exclusive() -> None:
    # Test-Rock.yaml hard-fails when both are set, so the matrix must only ever
    # forward one of them.
    run_tests_with = load_yaml(".github/workflows/Continuous-Testing.yaml")["jobs"][
        "run-tests"
    ]["with"]

    assert run_tests_with["ignored-vulnerabilities"] == (
        "${{ matrix.ignored-vulnerabilities }}"
    )
    assert run_tests_with["trivyignore-path"] == (
        "${{ matrix.ignored-vulnerabilities == '' "
        "&& format('oci/{0}/.trivyignore', matrix.name) || '' }}"
    )

