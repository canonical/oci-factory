import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
ACTION_DIR = ROOT / ".github/actions/check-kev"
CLASSIFIER_SCRIPT = ACTION_DIR / "check_kev.py"
REPORT_SCRIPT = ROOT / "src/tests/vulnerability_report.py"
TESTDATA = ACTION_DIR / "testdata"
CATALOG = TESTDATA / "catalog.json"


def run_script(
    script: Path, *arguments: str | Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(script), *(str(argument) for argument in arguments)],
        cwd=ROOT,
        env=process_env,
        check=False,
        capture_output=True,
        text=True,
    )


def read_outputs(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


@pytest.fixture
def report_path(tmp_path: Path) -> Path:
    report = tmp_path / "report.sarif"
    shutil.copyfile(TESTDATA / "report.sarif", report)
    return report


@pytest.fixture
def empty_report_path(tmp_path: Path) -> Path:
    report = tmp_path / "empty-report.sarif"
    shutil.copyfile(TESTDATA / "empty-report.sarif", report)
    return report


def classify(
    tmp_path: Path,
    cve_ids: str,
    *,
    catalog: Path = CATALOG,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    output = tmp_path / "classifier-output"
    result = run_script(
        CLASSIFIER_SCRIPT,
        "--cve-ids",
        cve_ids,
        "--catalog-source",
        catalog,
        env={"GITHUB_OUTPUT": str(output)},
    )
    return result, read_outputs(output)


def process_report(
    tmp_path: Path,
    report: Path,
    *,
    image_name: str = "example-image",
    catalog: Path = CATALOG,
) -> tuple[dict[str, str], dict[str, str], Path]:
    collected = run_script(REPORT_SCRIPT, "cve-ids", report)
    assert collected.returncode == 0, collected.stderr

    classified, classifier_outputs = classify(
        tmp_path, collected.stdout.strip(), catalog=catalog
    )
    assert classified.returncode == 0, classified.stderr

    process_output = tmp_path / "process-output"
    summary = tmp_path / "github-summary"
    processed = run_script(
        REPORT_SCRIPT,
        "process",
        report,
        classifier_outputs["kev-results"],
        classifier_outputs["catalog-source"],
        classifier_outputs["catalog-version"],
        classifier_outputs["catalog-release-date"],
        image_name,
        env={
            "GITHUB_OUTPUT": str(process_output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )
    assert processed.returncode == 0, processed.stderr
    return classifier_outputs, read_outputs(process_output), summary


def test_extracts_normalized_cve_aliases_from_active_sarif_results(
    report_path: Path,
) -> None:
    result = run_script(REPORT_SCRIPT, "cve-ids", report_path)

    assert result.returncode == 0
    assert json.loads(result.stdout) == [
        "CVE-2024-1000",
        "CVE-2024-1001",
        "CVE-2024-1002",
        "CVE-2024-2000",
        "CVE-2024-2001",
        "CVE-2024-2002",
        "CVE-2024-2003",
    ]
    assert "CVE-2024-2004" not in result.stdout


def test_classifies_each_unique_normalized_cve_id(tmp_path: Path) -> None:
    summary = tmp_path / "github-summary"
    output = tmp_path / "classifier-output"
    result = run_script(
        CLASSIFIER_SCRIPT,
        "--cve-ids",
        '["CVE-2024-1000","CVE-2024-2000","cve-2024-2001","CVE-2024-2000"]',
        "--catalog-source",
        CATALOG,
        env={
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )

    assert result.returncode == 0
    assert read_outputs(output) == {
        "kev-results": (
            '{"CVE-2024-1000":false,"CVE-2024-2000":true,' '"CVE-2024-2001":true}'
        ),
        "catalog-source": str(CATALOG),
        "catalog-version": "2026.09.14",
        "catalog-release-date": "2026-09-14T00:00:00Z",
    }
    assert not summary.exists()


def test_classifies_an_empty_cve_list(tmp_path: Path) -> None:
    result, outputs = classify(tmp_path, "[]")

    assert result.returncode == 0
    assert outputs["kev-results"] == "{}"


def test_warns_about_and_skips_non_conforming_cve_entries(tmp_path: Path) -> None:
    result, outputs = classify(tmp_path, '["GHSA-not-a-cve",42,"CVE-2024-2000"]')

    assert result.returncode == 0
    assert "::warning::Ignoring non-conforming CVE entry: 'GHSA-not-a-cve'" in (
        result.stderr
    )
    assert "::warning::Ignoring non-conforming CVE entry: 42" in result.stderr
    assert outputs["kev-results"] == '{"CVE-2024-2000":true}'


def test_enriches_and_filters_sarif_results_after_classification(
    tmp_path: Path, report_path: Path
) -> None:
    process_report(tmp_path, report_path)
    results = load_json(report_path)["runs"][0]["results"]

    assert [result["ruleId"] for result in results] == [
        "CVE-2024-1000",
        "CVE-2024-2000",
        "GHSA-vend-orid-test",
        "GHSA-prim-aryu-rl00",
        "GHSA-refe-renc-e000",
        "CVE-2024-2000",
    ]
    assert [
        result["properties"]["ociFactory/knownExploited"] for result in results
    ] == [False, True, True, True, True, True]


def test_keeps_kev_extension_data_in_sarif_property_bags(
    tmp_path: Path, report_path: Path
) -> None:
    process_report(tmp_path, report_path)
    report = load_json(report_path)
    run = report["runs"][0]

    assert report["version"] == "2.1.0"
    assert run["properties"]["imageName"] == "example-image"
    assert run["properties"]["ociFactory/kev"] == {
        "source": str(CATALOG),
        "catalogVersion": "2026.09.14",
        "dateReleased": "2026-09-14T00:00:00Z",
    }
    for result in run["results"]:
        assert "KnownExploited" not in result
        assert isinstance(result["properties"]["ociFactory/knownExploited"], bool)
        assert isinstance(result["properties"]["ociFactory/matchedKevIds"], list)


def test_reports_unique_kev_outputs_and_a_blocking_finding(
    tmp_path: Path, report_path: Path
) -> None:
    _, outputs, _ = process_report(tmp_path, report_path)

    assert outputs == {
        "kev-found": "true",
        "kev-count": "4",
        "kev-ids": (
            '["CVE-2024-2000","CVE-2024-2001",' '"CVE-2024-2002","CVE-2024-2003"]'
        ),
        "blocking-found": "true",
    }


def test_renders_markdown_table_from_enriched_sarif(
    tmp_path: Path, report_path: Path
) -> None:
    _, _, summary = process_report(tmp_path, report_path)
    markdown = summary.read_text()

    assert "## Vulnerabilities found for example-image\n" in markdown
    assert "| ID | Target | Severity | Package | KEV |\n" in markdown
    assert "| CVE-2024-1000 | /example | HIGH | fixed-high | No |" in markdown
    assert "| CVE-2024-2000 | /example | MEDIUM | direct-kev | Yes |" in markdown


def test_does_not_surface_suppressed_kev_findings(
    tmp_path: Path, report_path: Path
) -> None:
    classifier_outputs, _, summary = process_report(tmp_path, report_path)
    results = load_json(report_path)["runs"][0]["results"]

    assert "CVE-2024-2004" not in classifier_outputs["kev-results"]
    assert "ignored-kev" not in summary.read_text()
    assert not any(result["ruleId"] == "CVE-2024-2004" for result in results)


def test_empty_sarif_report_has_no_table_or_policy_violation(
    tmp_path: Path, empty_report_path: Path
) -> None:
    classifier_outputs, outputs, summary = process_report(
        tmp_path, empty_report_path, image_name="empty-image"
    )

    assert classifier_outputs["kev-results"] == "{}"
    assert outputs == {
        "kev-found": "false",
        "kev-count": "0",
        "kev-ids": "[]",
        "blocking-found": "false",
    }
    assert not summary.exists()


def test_ordinary_lower_severity_and_unfixed_high_results_do_not_block(
    tmp_path: Path, report_path: Path
) -> None:
    report = load_json(report_path)
    report["runs"][0]["results"] = [
        result
        for result in report["runs"][0]["results"]
        if result["ruleId"] in {"CVE-2024-1001", "CVE-2024-1002"}
    ]
    write_json(report_path, report)

    _, outputs, _ = process_report(tmp_path, report_path)

    assert load_json(report_path)["runs"][0]["results"] == []
    assert outputs["blocking-found"] == "false"


def test_fixable_high_result_blocks_without_being_marked_as_kev(
    tmp_path: Path, report_path: Path
) -> None:
    report = load_json(report_path)
    report["runs"][0]["results"] = [
        result
        for result in report["runs"][0]["results"]
        if result["ruleId"] == "CVE-2024-1000"
    ]
    write_json(report_path, report)

    _, outputs, _ = process_report(tmp_path, report_path)
    result = load_json(report_path)["runs"][0]["results"][0]

    assert outputs["kev-found"] == "false"
    assert outputs["blocking-found"] == "true"
    assert result["ruleId"] == "CVE-2024-1000"
    assert result["properties"]["ociFactory/knownExploited"] is False
    assert result["properties"]["ociFactory/matchedKevIds"] == []


def test_accepts_free_form_vulnerability_ids_in_sarif_results(
    tmp_path: Path, report_path: Path
) -> None:
    report = load_json(report_path)
    run = report["runs"][0]
    run["tool"]["driver"]["rules"] = [
        {
            "id": "GO-2024-1234",
            "properties": {"tags": ["vulnerability", "security", "HIGH"]},
        }
    ]
    run["results"] = [
        {
            "ruleId": "GO-2024-1234",
            "ruleIndex": 0,
            "level": "error",
            "message": {
                "text": "Package: go-package\nSeverity: HIGH\nFixed Version: 1.1"
            },
            "locations": [
                {"physicalLocation": {"artifactLocation": {"uri": "example"}}}
            ],
        }
    ]
    write_json(report_path, report)
    output = tmp_path / "process-output"
    summary = tmp_path / "github-summary"

    processed = run_script(
        REPORT_SCRIPT,
        "process",
        report_path,
        (
            '{"GHSA-abcd-1234-5678":false,"GO-2024-1234":false,'
            '"SNYK-EXAMPLE-123":false}'
        ),
        "source",
        "version",
        "release",
        "example-image",
        env={
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )

    assert processed.returncode == 0
    result = load_json(report_path)["runs"][0]["results"][0]
    assert result["ruleId"] == "GO-2024-1234"
    assert result["properties"]["ociFactory/knownExploited"] is False


def test_exports_normalized_downstream_findings_from_sarif(
    tmp_path: Path, report_path: Path
) -> None:
    process_report(tmp_path, report_path)
    output = tmp_path / "findings-output"

    exported = run_script(
        REPORT_SCRIPT,
        "findings",
        report_path,
        "--date-last-scan",
        "2026-09-13T00:00:00Z",
        "--notification-report",
        TESTDATA / "notification-report.json",
        env={"GITHUB_OUTPUT": str(output)},
    )

    assert exported.returncode == 0
    outputs = read_outputs(output)
    assert outputs["notify"] == "true"
    findings = json.loads(outputs["vulnerabilities"])
    assert len(findings) == 6
    assert findings[0] == {
        "Target": "example",
        "LastModifiedDate": None,
        "VulnerabilityID": "CVE-2024-1000",
        "PkgName": "fixed-high",
        "Severity": "HIGH",
        "KnownExploited": False,
    }


def test_fails_closed_for_invalid_sarif_report(tmp_path: Path) -> None:
    report = tmp_path / "invalid-report.sarif"
    report.write_text('{"version":"2.1.0","runs":null}\n')

    result = run_script(REPORT_SCRIPT, "cve-ids", report)

    assert result.returncode != 0
    assert "Invalid SARIF vulnerability report" in result.stderr


def test_fails_closed_when_report_cve_has_no_classification(
    tmp_path: Path, report_path: Path
) -> None:
    original_hash = hashlib.sha256(report_path.read_bytes()).digest()
    output = tmp_path / "process-output"
    summary = tmp_path / "github-summary"

    result = run_script(
        REPORT_SCRIPT,
        "process",
        report_path,
        "{}",
        "source",
        "version",
        "release",
        "example-image",
        env={
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )

    assert result.returncode != 0
    assert "Missing KEV classifications" in result.stderr
    assert hashlib.sha256(report_path.read_bytes()).digest() == original_hash


def test_fails_closed_for_malformed_catalog(tmp_path: Path, report_path: Path) -> None:
    original_hash = hashlib.sha256(report_path.read_bytes()).digest()
    catalog = load_json(CATALOG)
    catalog["count"] = 999
    invalid_catalog = tmp_path / "invalid-catalog.json"
    write_json(invalid_catalog, catalog)
    collected = run_script(REPORT_SCRIPT, "cve-ids", report_path)

    result, _ = classify(tmp_path, collected.stdout.strip(), catalog=invalid_catalog)

    assert result.returncode != 0
    assert "Invalid CISA KEV catalog" in result.stderr
    assert hashlib.sha256(report_path.read_bytes()).digest() == original_hash


def test_fails_closed_when_catalog_cannot_be_loaded(
    tmp_path: Path, report_path: Path
) -> None:
    collected = run_script(REPORT_SCRIPT, "cve-ids", report_path)

    result, _ = classify(
        tmp_path,
        collected.stdout.strip(),
        catalog=tmp_path / "missing-catalog.json",
    )

    assert result.returncode != 0
    assert "KEV catalog not found" in result.stderr
