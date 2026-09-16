import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.tests import vulnerability_report as vr

ROOT = Path(__file__).resolve().parents[2]
ACTION_DIR = ROOT / ".github/actions/check-kev"
CLASSIFIER_SCRIPT = ACTION_DIR / "check_kev.py"
REPORT_MODULE = "src.tests.vulnerability_report"
TESTDATA = ACTION_DIR / "testdata"
CATALOG = TESTDATA / "catalog.json"


def run_script(
    script: Path | str, *arguments: str | Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.update(env or {})
    command = [str(script)] if isinstance(script, Path) else ["-m", script]
    return subprocess.run(
        [sys.executable, *command, *(str(argument) for argument in arguments)],
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


@pytest.fixture
def report_path(tmp_path: Path) -> Path:
    report = tmp_path / "report.sarif"
    shutil.copyfile(TESTDATA / "report.sarif", report)
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


def test_sarif_policy_pipeline(tmp_path: Path, report_path: Path) -> None:
    collected = run_script(REPORT_MODULE, "cve-ids", report_path)
    assert collected.returncode == 0, collected.stderr
    assert json.loads(collected.stdout) == [
        "CVE-2024-1000",
        "CVE-2024-1001",
        "CVE-2024-1002",
        "CVE-2024-2000",
        "CVE-2024-2002",
    ]

    classified, classifications = classify(tmp_path, collected.stdout.strip())
    assert classified.returncode == 0, classified.stderr
    assert json.loads(classifications["kev-results"]) == {
        "CVE-2024-1000": False,
        "CVE-2024-1001": False,
        "CVE-2024-1002": False,
        "CVE-2024-2000": True,
        "CVE-2024-2002": True,
    }

    output = tmp_path / "process-output"
    summary = tmp_path / "github-summary"
    processed = run_script(
        REPORT_MODULE,
        "process",
        report_path,
        classifications["kev-results"],
        classifications["catalog-source"],
        classifications["catalog-version"],
        classifications["catalog-release-date"],
        "example-image",
        env={"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert processed.returncode == 0, processed.stderr
    assert read_outputs(output) == {"blocking-found": "true"}

    report = vr.load_report(report_path)
    run = report["runs"][0]
    assert report["version"] == "2.1.0"
    assert run["properties"] == {
        "imageName": "example-image",
        "ociFactory/kev": {
            "source": str(CATALOG),
            "catalogVersion": "2026.09.14",
            "dateReleased": "2026-09-14T00:00:00Z",
        },
    }
    assert [result["ruleId"] for result in run["results"]] == [
        "CVE-2024-1000",
        "CVE-2024-1001",
        "CVE-2024-2000",
        "GHSA-prim-aryu-rl00",
        "GO-2024-1234",
        "CVE-2024-2000",
    ]
    for result, kev_ids in zip(
        run["results"],
        [[], [], ["CVE-2024-2000"], ["CVE-2024-2002"], [], ["CVE-2024-2000"]],
        strict=True,
    ):
        assert "KnownExploited" not in result
        assert result["properties"]["ociFactory/knownExploited"] is bool(kev_ids)
        assert result["properties"]["ociFactory/matchedKevIds"] == kev_ids

    findings_output = tmp_path / "findings-output"
    exported = run_script(
        REPORT_MODULE,
        "findings",
        report_path,
        env={"GITHUB_OUTPUT": str(findings_output)},
    )
    assert exported.returncode == 0, exported.stderr
    outputs = read_outputs(findings_output)
    assert outputs["notify"] == "true"
    findings = json.loads(outputs["vulnerabilities"])
    assert len(findings) == 6
    assert findings[0] == {
        "Target": "example",
        "VulnerabilityID": "CVE-2024-1000",
        "PkgName": "fixed-high",
        "Severity": "HIGH",
        "KnownExploited": False,
    }
    assert all("LastModifiedDate" not in finding for finding in findings)

    issue = tmp_path / "issue.md"
    rendered = run_script(
        REPORT_MODULE,
        "markdown",
        "--findings",
        outputs["vulnerabilities"],
        "--image-name",
        "example-image",
        "--output",
        issue,
    )
    assert rendered.returncode == 0, rendered.stderr
    markdown = summary.read_text()
    assert issue.read_text() == markdown
    assert "## Vulnerabilities found for example-image\n" in markdown
    assert "| ID | Target | Severity | Package | KEV |\n" in markdown
    assert "| CVE-2024-1000 | /example | HIGH | fixed-high | No |" in markdown
    assert "| CVE-2024-1001 | /example | HIGH | unfixed-high | No |" in markdown
    assert "| CVE-2024-2000 | /example | MEDIUM | direct-kev | Yes |" in markdown
    assert "| GO-2024-1234 | /example | HIGH | go-package | No |" in markdown
    assert "ignored-kev" not in markdown
    assert "ordinary-medium" not in markdown


@pytest.mark.parametrize(
    "severity,fixed,kev,suppressed,blocking",
    [
        ("HIGH", "1.1", False, False, 1),
        ("HIGH", "", False, False, 1),
        ("CRITICAL", "1.1", False, False, 1),
        ("CRITICAL", "", False, False, 1),
        ("MEDIUM", "1.1", True, False, 1),
        ("MEDIUM", "", True, False, 1),
        ("LOW", "1.1", True, False, 1),
        ("LOW", "", True, False, 1),
        ("UNKNOWN", "1.1", True, False, 1),
        ("UNKNOWN", "", True, False, 1),
        ("HIGH", "1.1", False, True, 0),
        ("LOW", "", True, True, 0),
        ("CRITICAL", "1.1", True, True, 0),
        ("MEDIUM", "1.1", False, False, 0),
        ("LOW", "", False, False, 0),
        ("UNKNOWN", "", False, False, 0),
    ],
)
def test_enrich_report_policy(
    report_path: Path,
    severity: str,
    fixed: str,
    kev: bool,
    suppressed: bool,
    blocking: int,
) -> None:
    report = vr.load_report(report_path)
    run = report["runs"][0]
    result = run["results"][0]
    result["message"]["text"] = f"Severity: {severity}\nFixed Version: {fixed}"
    if suppressed:
        result["suppressions"] = [{"kind": "external", "status": "accepted"}]
    run["results"] = [result]

    count = vr.enrich_report(
        report,
        {} if suppressed else {"CVE-2024-1000": kev},
        "source",
        "version",
        "date",
    )

    assert type(count) is int
    assert count == blocking
    assert run["results"] == ([result] if blocking else [])
    if blocking:
        assert result["properties"]["ociFactory/knownExploited"] is kev
        assert result["properties"]["ociFactory/matchedKevIds"] == (
            ["CVE-2024-1000"] if kev else []
        )


@pytest.mark.parametrize(
    "result,rule,expected",
    [
        ({"ruleId": "cve-2024-2000"}, None, {"CVE-2024-2000"}),
        ({"ruleIndex": 0}, {"id": "CVE-2024-2000"}, {"CVE-2024-2000"}),
        (
            {"ruleId": "GHSA-prim-aryu-rl00"},
            {"helpUri": "https://example.test/cve-2024-2002"},
            {"CVE-2024-2002"},
        ),
        (
            {"ruleId": "GO-2024-1234", "message": {"text": "Unlike CVE-2024-2000"}},
            {"fullDescription": {"text": "Related to CVE-2024-2002"}},
            set(),
        ),
    ],
)
def test_cve_extraction_uses_only_finding_id_and_help_uri(
    result: dict[str, Any], rule: dict[str, Any] | None, expected: set[str]
) -> None:
    assert vr.cve_aliases(result, rule) == expected


@pytest.mark.parametrize("kind", ["kev-only", "high-only", "clean", "suppressed"])
def test_findings_notify_on_every_scan(
    tmp_path: Path, report_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    report = vr.load_report(report_path)
    run = report["runs"][0]
    run["results"] = {
        "kev-only": [run["results"][3]],
        "high-only": [run["results"][1]],
        "clean": [],
        "suppressed": [run["results"][-1]],
    }[kind]
    for result in run["results"]:
        result.setdefault("properties", {})["ociFactory/knownExploited"] = (
            kind != "high-only"
        )
    expected = vr.normalized_findings(report)
    assert bool(expected) is (kind in {"kev-only", "high-only"})

    for scan in range(2):
        output = tmp_path / f"findings-output-{scan}"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
        vr.emit_findings(report)
        outputs = read_outputs(output)
        assert outputs["notify"] == str(bool(expected)).lower()
        assert json.loads(outputs["vulnerabilities"]) == expected


def test_empty_report_has_no_policy_violation_or_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = vr.load_report(TESTDATA / "empty-report.sarif")
    summary = tmp_path / "github-summary"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    assert vr.report_cve_ids(report) == []
    assert vr.enrich_report(report, {}, "source", "version", "date") == 0
    assert vr.normalized_findings(report) == []
    vr.append_summary(report, "empty-image")
    assert not summary.exists()


def test_classifies_each_unique_normalized_cve_id(tmp_path: Path) -> None:
    summary = tmp_path / "github-summary"
    output = tmp_path / "classifier-output"
    result = run_script(
        CLASSIFIER_SCRIPT,
        "--cve-ids",
        '["CVE-2024-1000","CVE-2024-2000","cve-2024-2002","CVE-2024-2000"]',
        "--catalog-source",
        CATALOG,
        env={"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)},
    )

    assert result.returncode == 0, result.stderr
    outputs = read_outputs(output)
    assert json.loads(outputs.pop("kev-results")) == {
        "CVE-2024-1000": False,
        "CVE-2024-2000": True,
        "CVE-2024-2002": True,
    }
    assert outputs == {
        "catalog-source": str(CATALOG),
        "catalog-version": "2026.09.14",
        "catalog-release-date": "2026-09-14T00:00:00Z",
    }
    assert not summary.exists()


def test_classifies_an_empty_cve_list(tmp_path: Path) -> None:
    result, outputs = classify(tmp_path, "[]")
    assert result.returncode == 0, result.stderr
    assert json.loads(outputs["kev-results"]) == {}


def test_warns_about_and_skips_non_conforming_cve_entries(tmp_path: Path) -> None:
    result, outputs = classify(tmp_path, '["GHSA-not-a-cve",42,"CVE-2024-2000"]')
    assert result.returncode == 0, result.stderr
    assert "::warning::Ignoring non-conforming CVE entry: 'GHSA-not-a-cve'" in (
        result.stderr
    )
    assert "::warning::Ignoring non-conforming CVE entry: 42" in result.stderr
    assert json.loads(outputs["kev-results"]) == {"CVE-2024-2000": True}


@pytest.mark.parametrize("value", ["{", "[]", '{"CVE-2024-2000":"true"}'])
def test_rejects_malformed_classifications(value: str) -> None:
    with pytest.raises(vr.ReportError, match="Invalid KEV classifications"):
        vr.parse_kev_classifications(value)


@pytest.mark.parametrize("findings", ["[]", '[{"VulnerabilityID":"CVE-2024-1000"}]'])
def test_markdown_command_handles_empty_or_invalid_findings(
    tmp_path: Path, findings: str
) -> None:
    issue = tmp_path / "issue.md"
    rendered = run_script(
        REPORT_MODULE,
        "markdown",
        "--findings",
        findings,
        "--image-name",
        "example-image",
        "--output",
        issue,
    )
    if findings == "[]":
        assert rendered.returncode == 0, rendered.stderr
        assert issue.read_text() == ""
    else:
        assert rendered.returncode != 0
        assert "Invalid findings: expected normalized vulnerability findings" in (
            rendered.stderr
        )
        assert not issue.exists()


def test_fails_closed_for_invalid_sarif_report(tmp_path: Path) -> None:
    report = tmp_path / "invalid-report.sarif"
    report.write_text('{"version":"2.1.0","runs":null}\n')
    result = run_script(REPORT_MODULE, "cve-ids", report)
    assert result.returncode != 0
    assert "Invalid SARIF vulnerability report" in result.stderr


def test_fails_closed_when_report_cve_has_no_classification(
    tmp_path: Path, report_path: Path
) -> None:
    original = report_path.read_bytes()
    output = tmp_path / "process-output"
    summary = tmp_path / "github-summary"
    result = run_script(
        REPORT_MODULE,
        "process",
        report_path,
        "{}",
        "source",
        "version",
        "release",
        "example-image",
        env={"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert result.returncode != 0
    assert "Missing KEV classifications" in result.stderr
    assert report_path.read_bytes() == original
    assert read_outputs(output) == {}
    assert not summary.exists()


def test_fails_closed_for_malformed_catalog(tmp_path: Path) -> None:
    catalog = json.loads(CATALOG.read_text())
    catalog["count"] = 999
    invalid_catalog = tmp_path / "invalid-catalog.json"
    invalid_catalog.write_text(json.dumps(catalog))
    result, outputs = classify(tmp_path, '["CVE-2024-2000"]', catalog=invalid_catalog)
    assert result.returncode != 0
    assert "Invalid CISA KEV catalog" in result.stderr
    assert outputs == {}


def test_fails_closed_when_catalog_cannot_be_loaded(tmp_path: Path) -> None:
    result, outputs = classify(
        tmp_path, '["CVE-2024-2000"]', catalog=tmp_path / "missing-catalog.json"
    )
    assert result.returncode != 0
    assert "KEV catalog not found" in result.stderr
    assert outputs == {}
