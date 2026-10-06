---
name: code-review
description: >-
  Review OCI Factory pull requests and local diffs against the maintainer
  review standard. Use for PR reviews or requested pre-submission self-reviews.
---

# OCI Factory code review

- Pick the checklist by what the diff touches: `oci/<name>/image.yaml` ->
  §1-§3; `oci/<name>/documentation.yaml` -> §4; `.github/`, `src/` or `tools/`
  -> §5.
- Request changes when a MUST in this guide is violated, or the PR touches more
  than one `oci/<name>/` directory. Approve only when none is. Any `[blocker]`
  means `Request changes`, even when the problem predates the diff (e.g. a
  missing manifest in a touched `upload[]` item); `Comment` is for nits only.
- Ground every request-changes on evidence (CI run, upstream source, docs).
  Never approve on intent alone.
- Tag every inline note `[blocker]` or `[nit]`, optional ones included
  (`[nit] Not a blocker, but ...`). Keep comments short and use GitHub
  `suggestion` blocks for concrete fixes.

## Local dry run

Authors can run this review on their working changes before pushing, e.g.
*"Review my staged changes as an OCI Factory PR reviewer using the
code-review skill."* Diff against the branch point with upstream main:
`git diff --merge-base <remote>/main`, where `<remote>` tracks
`canonical/oci-factory` (often `upstream` in a fork, not `origin`), or
`git diff --cached` for staged-only changes. The vulnerability scan is CI-only
and stays out of the local verdict; the static §1 rules still apply. Fetch
recipes (§3) when the network allows, otherwise mark the recipe gates
*not assessed*. A local `Approve` only means the locally-checkable gates passed.

Output:

- **Verdict:** `Request changes` / `Comment` / `Approve`, plus one sentence.
- **Inline comments:** `` `path:line` — [blocker] note (§N) `` or `[nit]`, with
  a `suggestion` block where useful.
- **Gates:** one line, each gate pass / ⚠ / ❌ and reporting only its own rule:
  `**Gates:** one-image ✅ · edge-first ✅ · EOL cap n/a · track naming ✅ ·
  docs n/a · CVE justification ✅ · .trivyignore ✅ · deb-manifest ✅ ·
  recipe-regression ✅ · vuln scan -> not assessed locally; verify in CI`

## 1. Security & vulnerability gating

- In a real PR review the vulnerability scan blocks: don't approve until the
  latest run passes. If it reports findings, request changes, link the run and
  apply the `pending cve` label.
- Findings are ignored via `upload[].ignored-vulnerabilities`, which requires a
  `version: 2` trigger; a `version: 1` trigger that adds the field MUST switch.
- The comment of every new or modified entry MUST name the affected
  package/source and ecosystem (for other Trivy finding types: the
  file/component and rule category) AND the maintainer's risk disposition: an
  image-specific reason the finding can be accepted. Description, CVSS, Ubuntu
  priority or a status such as `Needs evaluation` are context, not a
  disposition. For deb packages link `https://ubuntu.com/security/<CVE-ID>`; for
  language packages state the upstream fix status and link an advisory if one
  exists. Untouched existing entries need no rewrite.

  ```yaml
  ignored-vulnerabilities:
    - CVE-XXXX-XXXXX  # libfoo (deb): temporarily accepted pending an Ubuntu fix | Ubuntu tracker: https://ubuntu.com/security/CVE-XXXX-XXXXX
    - CVE-YYYY-YYYYY  # google.golang.org/grpc (Go): temporarily accepted; no fixed upstream release is available
  ```

- `.trivyignore` is deprecated: reject new files and new rules. A non-empty
  `ignored-vulnerabilities` list replaces `.trivyignore` for that build (an
  empty or omitted list still falls back to it), so a migration MUST move every
  still-applicable rule, not only the changed ones: when a build gains a
  non-empty list, open its `oci/<name>/.trivyignore` and require every rule that
  still applies to move over. The old file may stay for previously released
  revisions.

## 2. Release policy

- **Edge-first (MUST).** The first release of a new rock, a new track or a new
  base is `- edge` only, never `candidate` or `stable`.
- **EOL cap (MUST).** If the main application is built from a directly-pulled
  upstream source (a part's own `source:` repository, §3) and no support plan
  has been accepted by a human in `CODEOWNERS`, `end-of-life` is at most today +
  3 months. Ask for a support plan; don't judge it yourself.
- **Track naming (MUST).** New or modified track keys are `<version>-<base>`
  (e.g. `1.27-26.04`), where `<version>` is the application's version. SemVer
  applications omit the patch: `1.27.3` -> `1.27-26.04`, not `1.27.3-26.04`.
  Non-SemVer versions follow the application's own scheme. Don't ask to rename
  unchanged legacy patch-level tracks. A major-only alias track (e.g. `8-26.04`
  next to `8.18-26.04`) is a valid key, and still a new track: edge-first
  applies.
- **Suspected regression (MUST).** While a recipe regression (§3) is
  unresolved, the new revision is released to `edge` only.
- Be cautious promoting to `stable`; require a tracking ticket for any intended
  later promotion. Flag concurrent PRs that write the same track.

## 3. Source recipe (`rockcraft.yaml`)

Review the recipe behind every image-trigger change, not just the trigger:
whatever the diff touches, fetch the `rockcraft.yaml` of each `upload[]` item at
its `source` + `commit` (under `directory`), plus the previous one for a source
bump. If it can't be fetched, say so and skip these checks.

- **Deb security manifest (MUST).** A rock that adds `.deb` content beyond its
  base (via `stage-packages`, or `apt` / `apt-get` / `dpkg` in build or overlay
  scripts) must include a part sourced from
  `https://github.com/canonical/rocks-security-manifest`, wired as its README
  documents (the part name may differ):

  ```yaml
  deb-security-manifest:
    plugin: make
    source: https://github.com/canonical/rocks-security-manifest
    source-type: git
    source-branch: main
    override-prime: gen_manifest
  ```

  The only exemption is a bare-based rock with purely static binaries and no deb
  content at all; using even `base-files` requires the manifest.
- **Upstream-sourced.** A part built from an external repository (`source:` on
  GitHub/Launchpad with `source-type: git`, or a plugin compiling upstream code)
  makes the rock upstream-sourced for the §2 EOL cap, even under the `canonical`
  org. The security-manifest part doesn't count.
- **Recipe regression (blocker).** If a source bump (new `commit` or
  `directory`) drops a `parts:` or `services:` entry the previous recipe had,
  request changes until it is restored or the author confirms in the PR that the
  removal is intentional (an upstream commit message is not that confirmation);
  meanwhile keep the revision at `edge` (§2).

## 4. Documentation (`documentation.yaml`)

- US English spelling, correct product capitalization, no informal phrasing;
  service configuration headings are h2 (`##`). Spelling-only issues are nits.
- Document a default only when the program really sets it; verify it against
  upstream and link the source. An unverified or wrong default is a blocker.
- Run flags belong in `parameters`, not `run_cmd` (`run-cmd` in v2 docs).
- Don't duplicate content the template already provides.
- Document every user-configurable runtime setting a `docker run -e` value can
  reach (check `rockcraft.yaml` `environment:`, Pebble services and entrypoint
  scripts), with examples; skip values fixed by `services.<name>.environment`.
- The documented `docker run ...` must actually work; a broken one is a blocker.
- A v1 -> v2 migration must not lose anything the v1 doc had.

## 5. CI / GitHub Actions

- **Pin external actions (MUST).** Every external `uses:` reference is a full
  commit SHA (a tag comment is fine), never a mutable ref such as `@v4` or
  `@main`.
- **Least privilege (MUST).** The inherited `GITHUB_TOKEN` default is read-only;
  don't add a `permissions` block only to restate it. A declared block is
  exhaustive (omitted scopes become `none`), so it lists every scope the job
  needs and nothing more; `write` implies `read`.
- **Tokens (MUST).** Use `GITHUB_TOKEN` instead of `ROCKSBOT_TOKEN` whenever it
  suffices. Flag tags or commits pushed with a PAT: that bypasses GitHub's
  protection against recursive workflow runs.
- A caller job must grant a reusable workflow the permissions it needs.
- Cite GitHub docs for permission and token decisions; don't churn working
  workflows.
