# OCI Factory — Agent Guide

The OCI Factory is the centralized gateway for Ubuntu OCI images published to
Docker Hub, ECR, and other registries under the ROCKS Team-maintained `ubuntu`
namespace. This file is the entry point for agents (and humans) working in the
repository: it explains the layout and conventions, then encodes the maintainer
review standard.

## Repository overview

- `oci/<name>/` — per-image maintainer files (the trigger surface most PRs
  touch):
  - `image.yaml` — image trigger: build/release definition, tracks, risks,
    `end-of-life`, and (v2) `ignored-vulnerabilities`.
  - `documentation.yaml` — documentation trigger consumed to render the image's
    published docs.
  - `contacts.yaml` — maintainer contacts.
- `src/` — the factory source (build/test/release automation) invoked by CI.
- `.github/workflows/` — reusable and top-level GitHub Actions workflows
  (e.g. `Build-Rock.yaml`, `Test-Rock.yaml`).
- `.github/ISSUE_TEMPLATE/` — issue intake, including the `onboarding` request
  form.
- `tools/` — helper scripts and utilities.
- `tests/` — factory test suites.

## Working conventions

- Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
  spec; squash commits by functional value.
- In-progress PRs must be marked **Draft**; non-trivial changes should open an
  issue first.
- A PR that changes files below `oci/` must affect only one `oci/<name>/`
  directory. It may update multiple versions, tracks, or maintainer files for
  that image, but changes for multiple images must be split into separate PRs.
- See [`CONTRIBUTING.md`](/CONTRIBUTING.md) and [`README.md`](/README.md) for the
  full authoring and project reference, and
  [`IMAGE_MAINTAINER_AGREEMENT.md`](/IMAGE_MAINTAINER_AGREEMENT.md) for
  maintainer obligations.

## Reviewing Pull Requests in OCI Factory

This section encodes the maintainer review standard for the OCI Factory
repository. It is derived from established review practice and is meant to guide
both human reviewers and AI review agents to a consistent bar.

### How to use this guide

- Apply the checklist that matches the PR type (see [Triage](#1-triage-the-pr-first)).
- Ground every request-changes on **evidence**: link the exact CI run, the
  upstream source, or the relevant documentation. Never approve on intent alone.
- Distinguish **blockers** from **non-blockers** explicitly. Prefix optional
  feedback with `Not a blocker, but ...`.
- Keep comments concise: state the finding and only the reasoning needed to act
  on it. Link evidence instead of restating it, and don't repeat unchanged
  context or the diff back to the author.
- Prefer GitHub *suggestions* for concrete wording/format fixes so authors can
  apply them in one click.

### Running a local review before you push

Authors can dry-run this exact review locally, before pushing or opening the PR,
to catch blockers ahead of CI and reviewers. Run it on demand — no git hook
required — by asking an AI agent harness to review your working changes against
this guide.

**How to run it**

- Stage or commit your changes, then prompt the harness, e.g.
  *"Review my staged changes as an OCI Factory PR reviewer."*
- The harness scopes the diff (`git diff --merge-base origin/main`, or
  `git diff --cached` for staged-only), lists the touched files, and **triages
  by file path** — the `rock/*` labels don't exist yet, so use the fallback path
  column in [Triage](#1-triage-the-pr-first), as labels are only applied to
  actual PRs.
- It then applies the matching checklists ([§2](#2-security--vulnerability-gating-hard-gate)–[§7](#7-evidence--process-hygiene)).
  The vulnerability scan itself is **CI-only** and does not affect a local
  dry-run verdict. Locally, the harness checks the static requirements: trigger
  `version: 2` where `ignored-vulnerabilities` is used, sufficient comments on
  new or modified ignored entries, and `.trivyignore` deprecation (see
  [§2](#2-security--vulnerability-gating-hard-gate)). It also fetches each
  `upload[]` item's `rockcraft.yaml` (network permitting) to run the
  [§4](#4-source-recipe-rockcraftyaml-review) recipe checks, and marks them *not
  assessed* when the recipe cannot be retrieved. A local `Approve` means only
  that the locally-checkable gates passed; it is not an approval of a real PR and
  does not imply that its vulnerability scan is clean.

**Output format (mimics a GitHub PR review — keep it concise)**

- **Verdict** — one of `Request changes` / `Comment` / `Approve`, plus a
  one-sentence summary.
- **Inline comments** — one per finding, each `` `oci/<name>/image.yaml:line` ``
  followed by a one-line note prefixed `[blocker]` or `[nit]`, with a `(§N)`
  pointer to the governing section. Use GitHub ```` ```suggestion ```` blocks for
  concrete fixes.
- **Gate summary** — a compact pass / ⚠ / blocker checklist for the
  locally-checkable gates: one-image scope, edge-first, EOL cap, track naming,
  docs checklist, `ignored-vulnerabilities` justification, `.trivyignore`
  deprecation, deb security manifest, and recipe regression. Mark the
  deb-manifest and recipe-regression gates *not assessed* when the recipe cannot
  be fetched, and the vulnerability scan itself as *not assessed locally; verify
  in CI*.

**Example**

> **Request changes** — new track must start at `edge`, and the ignored CVE
> lacks a justification.
>
> `oci/foo/image.yaml:12` — [blocker] First release of a new track must be
> `- edge` only, not `stable`. (§3)
> ````suggestion
>         risks:
>           - edge
> ````
>
> `oci/foo/image.yaml:20` — [blocker] This new `ignored-vulnerabilities` entry
> lacks a sufficient justification; identify the affected package/source and
> state the image-specific reason the risk can be accepted. (§2)
>
> `oci/foo/image.yaml:5` — [blocker] The new track `1.2.3-24.04` includes a
> SemVer patch component; use `1.2-24.04`. (§3)
>
> **Gates:** one-image ✅ · edge-first ❌ · EOL cap ✅ · track naming ❌ · docs
> n/a · CVE justification ❌ · `.trivyignore` ✅ · deb-manifest ✅ ·
> recipe-regression ✅ · vuln scan → not assessed locally; verify in CI

### 1. Triage the PR first

Classify the PR before reviewing, then jump to the matching sections. Triage
primarily on the **type label** (`rock/*`, `onboarding`) — see
[section 8](#8-pr-labels) — falling back to the touched file path when the label
is missing (the `rock/*` labels are applied by maintainers, not auto-labeled):

| Label (fallback path) | PR / issue type | Primary sections |
| --- | --- | --- |
| `rock/update` (`oci/<name>/image.yaml`) | Existing image-trigger update | [2](#2-security--vulnerability-gating-hard-gate), [3](#3-release-policy-risk-tracks-eol-versioning), [4](#4-source-recipe-rockcraftyaml-review) |
| `rock/new` (new `oci/<name>/`, new track/base) | New rock / new track / new base | [2](#2-security--vulnerability-gating-hard-gate), [3](#3-release-policy-risk-tracks-eol-versioning), [4](#4-source-recipe-rockcraftyaml-review), [5](#5-documentation-documentationyaml-checklist) |
| `rock/docs` (`oci/<name>/documentation.yaml`) | Documentation change | [5](#5-documentation-documentationyaml-checklist) |
| `onboarding` (issue) | Image onboarding request (intake) | [3](#3-release-policy-risk-tracks-eol-versioning), [5](#5-documentation-documentationyaml-checklist) |
| no `rock/*` label (`.github/`, `src/`, `tools/`) | Factory source / CI workflow | [6](#6-ci--github-actions-review), [7](#7-evidence--process-hygiene) |

### 2. Security & vulnerability gating (hard gate)

For an actual GitHub PR review of an image change, the vulnerability scan is a
**blocking** gate. Inspect the latest relevant CI run and do not approve until
it succeeds. If the scan is pending or unavailable, withhold approval and
re-review when it completes. This CI-only result is excluded from local dry-run
verdicts as described above.

- If the scan reports findings, request changes and link the exact run. Use the
  canonical phrasing:

  > Please observe the CVE findings:
  > `https://github.com/canonical/oci-factory/actions/runs/<run-id>/attempts/<n>#summary-<summary-id>`

- Findings are addressed in the `ignored-vulnerabilities:` field of the image
  trigger. Every new or modified entry must have an explanatory comment that:
  identifies the affected package/source and ecosystem, and states the
  maintainer's actual risk disposition with an image-specific reason the
  finding may be ignored. Existing untouched entries do not need to be updated
  solely to meet this comment format.

  A package name, description, CVSS score, Ubuntu priority, or status such as
  `Needs evaluation` is useful supporting context, but is not by itself a risk
  disposition or justification. For deb packages, link the Ubuntu Security
  tracker at `https://ubuntu.com/security/<CVE-ID>` instead of creating an
  internal ROCKS ticket. CVEs in language packages are not currently tracked
  internally; state the upstream fix status and link an upstream advisory when
  one is available.

  ```yaml
  upload:
    - source: canonical/foo-rock
      commit: "<full-commit-sha>"
      directory: .
      ignored-vulnerabilities:
        - CVE-XXXX-XXXXX  # libfoo (deb): temporarily accepted pending an Ubuntu fix | Ubuntu tracker: https://ubuntu.com/security/CVE-XXXX-XXXXX
        - CVE-YYYY-YYYYY  # google.golang.org/grpc (Go): temporarily accepted; no fixed upstream release is available
  ```

  Prefer also including a short description, `CVSS: <score> (<severity>)`,
  `Ubuntu priority: <priority>`, `Status (<series>): <triage>`, and relevant
  upstream evidence. This metadata supplements, but does not replace, the risk
  disposition.

- When requesting changes for scan findings, apply the `pending cve` label (see
  [section 8](#8-pr-labels)); remove it once every finding is fixed or justified.

- Ask maintainers to add ignored entries **with proper justifications in the
  comment**, not to silence findings blindly.

- The `.trivyignore` file is **deprecated**. Do not accept new `.trivyignore`
  files. When migrating an affected build to `ignored-vulnerabilities`, require
  every still-applicable rule to move, not only the changed rules. Once
  `ignored-vulnerabilities` is present, that build no longer uses
  `.trivyignore`. The legacy file may remain temporarily because previously
  released revisions can still depend on it.
  Example wording:

  > Let's move every still-applicable rule to `ignored-vulnerabilities`; once
  > present, that build no longer uses `.trivyignore`. The legacy file may
  > remain for previously released revisions that still depend on it.

- `ignored-vulnerabilities` requires a `version: 2` trigger. A `version: 1`
  trigger may stay as-is only until it needs this field; then it MUST switch to
  `version: 2`.

### 3. Release policy: risk, tracks, EOL, versioning

- **Edge-first rule (MUST).** A new rock, a new track, or a new base image's
  *first* release must include only `- edge`. Do not land a first release
  directly at `candidate` or `stable`. Example:

  > `1.27-26.04` is a new track for this rock (and also a new base). Let's start
  > with risk edge.

- **EOL cap for upstream-sourced rocks.** If the main application is built from
  a directly-pulled upstream source **without a stated support plan**, cap the
  `end-of-life` at *merge day + 3 months* and ask the team to describe their
  support plan. Example:

  > Since this rock is built from upstream source without a support plan, please
  > reduce the EOL to "today + 3 months" at most.

- **Conservative stable promotion.** Be cautious bumping a rock to `stable`,
  especially when a known upstream/tooling issue affects the build. Because risk
  promotion is **not automated**, require an issue/Jira ticket to track any
  intended future promotion.

- **Canonical track naming (MUST).** New or modified image track keys use
  `<version>-<base>` (for example, `1.27-26.04`). Here, `<version>` is the
  application's track version, not the image trigger's top-level schema
  `version:` field. When the application follows SemVer, the track MUST omit
  the patch component: upstream `1.27.3` belongs to `1.27-26.04`, not
  `1.27.3-26.04`. Non-SemVer `<version>` values are exempt from the SemVer shape
  but must remain aligned with the application's versioning scheme. Do not
  require cleanup of unchanged legacy patch-level tracks in an otherwise
  unrelated update.

- **Track-conflict detection.** Flag concurrent PRs that write the same track;
  they cause the track to oscillate/overwrite between values. Mark the
  conflicting PRs invalid and coordinate which one proceeds. Example:

  > The image trigger file conflicts with #NNNN on the track `X-YY.MM`. Please
  > update either this one or the other so they won't overwrite each other.
  > Marking this PR and #NNNN as invalid for now.

### 4. Source recipe (`rockcraft.yaml`) review

For image-trigger changes (`rock/update`, `rock/new`), review the
build recipe behind the release, not just the trigger. For **each** `upload[]`
item, fetch the `rockcraft.yaml` at that item's pinned `source` repository and
`commit` (under the item's `directory` subpath when set) — via `gh`/`git` or the
repository web UI — and apply the caveats below. This fetch is external: in a
local dry-run it may be unavailable, so state that and skip the recipe checks
when the file cannot be retrieved.

- **deb security manifest (MUST).** If any part declares `stage-packages` — i.e.
  the rock layers additional `.deb` packages on top of the Ubuntu base — the
  recipe MUST include a security-manifest part whose `source` is
  `https://github.com/canonical/rocks-security-manifest`, wired exactly as that
  repository's README documents. The part name may differ, but the source and
  usage must match. This enforces the maintainer obligation in
  [`IMAGE_MAINTAINER_AGREEMENT.md`](/IMAGE_MAINTAINER_AGREEMENT.md#enable-security-monitoring).
  If a `stage-packages` rock is missing this part, or wires it differently,
  request changes:

  ```yaml
  parts:
    deb-security-manifest:
      plugin: make
      source: https://github.com/canonical/rocks-security-manifest
      source-type: git
      source-branch: main
      override-prime: gen_manifest
  ```

  > This rock stages `.deb` packages but the recipe does not include the
  > standardized security manifest. Please add the `deb-security-manifest` part
  > from `https://github.com/canonical/rocks-security-manifest`, wired per its
  > README.

- **External-source detection → EOL cap.** If any part is pulled and built
  directly from an external repository — e.g. a `source:` pointing at
  GitHub/Launchpad with `source-type: git`, or a plugin that compiles upstream
  code — treat the rock as upstream-sourced **even when the repository lives
  under the `canonical` org**. The sole exemption is a part sourced from
  `https://github.com/canonical/rocks-security-manifest`. Otherwise, apply the
  `end-of-life` cap from [§3](#3-release-policy-risk-tracks-eol-versioning); do
  not restate the rule here.

- **Recipe regression (blocker).** When the source is bumped (a new `commit` or
  `directory`) and the new recipe drops a `parts:` entry or a `services:` entry
  that the previously referenced recipe defined, treat it as a regression and
  request changes as a **[blocker]**. Hold until the removed part/service is
  restored, or the author confirms the removal is intentional and not a
  regression (see [§9](#9-approve-vs-request-changes-criteria), "regressions are
  ruled out"). Example:

  > This source bump removes the `<name>` <part|service> that the previous
  > revision shipped. Is this intentional? If so, please confirm it is not a
  > regression; otherwise restore it. Marking as a blocker until then.

### 5. Documentation (`documentation.yaml`) checklist

- **Language:** US English spelling throughout; correct product capitalization
  (e.g., do not write an uncapitalized product name); no informal phrasing.
- **Headings:** correct level — service configuration headings are h2 (`##`).
- **Verify defaults against upstream.** Do not document a default value that the
  program does not actually set. Confirm against upstream source and link it.
  Only state a default when it is real.
- **Field placement:** run flags belong in `parameters`, not `run_cmd`.
- **No template duplication:** remove content already provided by the template.
- **Completeness:** include all env/config the rock declares (cross-check the
  rock's `rockcraft.yaml` `environment:`), and provide concrete examples in env
  descriptions.
- **Runnable:** the documented `docker run ...` must actually work; verify it
  before approving.
- **Migrations (v1 -> v2) must not regress.** Approve a migration only when it
  is at least equivalent to the v1 doc and nothing is undermined. Example
  approval language:

  > It seems there are no regressions or undermines from this change to the
  > original documentation. Happy to move forward.

- Note: the GitHub web UI can mangle multi-line suggestions. If a suggestion is
  not applied correctly, ask the author to commit it manually.

### 6. CI / GitHub Actions review

- **Least privilege for `GITHUB_TOKEN`.** OCI Factory inherits the read-only
  default configured by Canonical's organizational workflow-permission
  controls. When no applicable `permissions` block is declared, do not add one
  solely to restate that inherited default. Once a `permissions` block is
  declared at workflow or job level, it is exhaustive: every omitted scope is
  set to `none`. List every read or write scope the job actually needs and no
  others; `write` already includes `read` for the same scope.
- **Prefer `GITHUB_TOKEN` over broad PATs.** Do not use `ROCKSBOT_TOKEN` where
  `GITHUB_TOKEN` suffices — the bot token carries far wider scope.
- **PAT-tag anti-pattern.** Pushing tags/commits with a PAT/bot identity
  bypasses GitHub's protection against triggering infinite downstream workflow
  runs. GitHub suppresses triggers for pushes made by `GITHUB_TOKEN` because it
  treats them as CI actions; a PAT push voids that protection. Flag this.
- **Reusable-workflow permission propagation.** A caller invoking a
  fully-capable reusable workflow must grant the required permissions in the
  caller job; the called workflow keeps default permissions when none are
  specified. Understand this before requesting permission changes.
- **Cite the docs.** Justify workflow-permission and token decisions with links
  to the relevant GitHub documentation.
- **Respect established patterns.** Avoid unnecessary changes to established,
  working workflows; remove genuinely dead code (e.g., retired build paths).

### 7. Evidence & process hygiene

- **Prove fixes.** Back a "fixed" or "works" claim with a link to a successful
  CI/test run or to upstream source. Example:

  > Test workflow succeeds after applying this patch: `<actions run link>`

- **Resolve linter warnings.** Do not leave yamllint (or other linter) warnings
  unaddressed — e.g., "too few spaces before comment".
- **Track deferred work.** File a follow-up issue (e.g., `ROCKS-####`) for items
  intentionally deferred, and reference it in the thread.
- **Close housekeeping PRs** that are stale (no activity for more than a month),
  outdated, or superseded by another PR — state the reason on close. Apply the
  `decaying` label after 2 weeks of no activity as an early warning (see
  [section 8](#8-pr-labels)) before closing.
- **Request a second reviewer** when the change is outside your area or warrants
  another set of eyes.

### 8. PR labels

Apply labels to make review state visible and to drive housekeeping. The repo
uses three families:

**Type labels** — set the review path (see [Triage](#1-triage-the-pr-first)):

- **`rock/new`** — a new rock, or a new track/base for an existing rock.
- **`rock/update`** — an existing rock's image trigger is modified (release or
  track change).
- **`rock/chore`** — maintainer contact changes in `contacts.yaml`.
- **`rock/docs`** — a rock's `documentation.yaml` change.
- **`onboarding`** — image onboarding request; auto-applied by the onboarding
  issue template.
- **`bug`** / **`duplicate`** — standard issue triage (`bug` also auto-applied
  by the bug-report template; `duplicate` when the item already exists).

  Note: `rock/*` labels are applied by maintainers, not auto-labeled; fall back
  to the touched file path when they are missing.

**Review-state labels** — track blockers and housekeeping:

- **`pending cve`** — apply to any PR whose vulnerability scan reports
  unresolved findings (see [section 2](#2-security--vulnerability-gating-hard-gate)).
  Keep it until every finding is either fixed or justified in
  `ignored-vulnerabilities`; remove it once the scan is clean.
- **`blocked`** — apply when the PR cannot make progress until an external or
  upstream dependency is resolved (e.g. a vuln fix pending in the base, an
  upstream/tooling bug). Do not merge while set; record what it is blocked on.
- **`do-not-merge`** — an explicit merge hold even if checks are green (e.g. a
  proposal/spike, or work that must land in a specific order). Never merge while
  set.
- **`decaying`** — apply to any PR with no update for **more than 2 weeks**. It
  is the early-warning step before closing: a `decaying` PR that stays inactive
  for more than a month should be closed as stale (see
  [section 7](#7-evidence--process-hygiene)).
- **`invalid`** — apply to PRs that cannot proceed as-is, e.g. conflicting
  concurrent PRs on the same track (see
  [section 3](#3-release-policy-risk-tracks-eol-versioning)).

**Priority labels** — `priority/critical`, `priority/high`, `priority/medium`,
`priority/low` communicate urgency for triage and scheduling; set at most one.

### 9. Approve vs. request-changes criteria

The following criteria govern actual GitHub PR reviews. For a local dry-run,
exclude the CI-only vulnerability-scan result from the verdict while retaining
all locally-checkable security requirements.

Request changes when any of the following holds:

- The vulnerability scan reports unresolved findings.
- The PR changes files below more than one distinct `oci/<name>/` directory.
- A new rock/track/base first release is not restricted to `edge`.
- The `end-of-life` exceeds the cap for an unsupported upstream-sourced rock.
- A rock stages `.deb` packages but its recipe omits the `rocks-security-manifest`
  part, or wires it differently (see [§4](#4-source-recipe-rockcraftyaml-review)).
- A source bump drops a `parts:` or `services:` entry the previous recipe defined,
  without the author confirming it is intentional (see
  [§4](#4-source-recipe-rockcraftyaml-review)).
- A documented default is unverified or wrong, or the documented run does not work.
- A workflow grants more token/permission scope than necessary, or uses a PAT
  where `GITHUB_TOKEN` suffices.
- Concurrent PRs conflict on the same track.

Never approve or merge while a `do-not-merge` or `blocked` label is set, even
when all checks are green. Approve only when the security gate is clean, the
release policy is satisfied, and regressions are ruled out. Keep approvals
concise and, where relevant, note that no regressions/undermines were
introduced.

### 10. Related project conventions

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for authoring rules the review should
enforce:

- Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) spec.
- Squash commits by functional value; no multiple commits fixing one issue in
  the same code block.
- In-progress PRs must be marked **Draft**.
- Non-trivial changes should open an issue for discussion before the PR.
- **Maintainers** must acknowledge the
  [Image Maintainer Agreement](/IMAGE_MAINTAINER_AGREEMENT.md).
