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
  than one `oci/<name>/` directory. Any `[blocker]` means `Request changes`, even
  if it predates the diff (e.g. a missing manifest in a touched `upload[]` item).
  Otherwise use `Comment` for advisory findings, or `Approve` with no findings,
  subject to applicable gates.
- Ground every request-changes on evidence (CI run, upstream source, docs).
  Never approve on intent alone. Cite existing lines in the reviewed files;
  for a deletion, cite the previous file rather than inventing a new-file line.
- Write one short finding per distinct concern, tagged `[blocker]` or `[nit]`;
  use GitHub `suggestion` blocks for fixes. Correct changes belong in summaries,
  not findings. Advisory verification is not a merge prerequisite.

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
Unassessed recipe checks remain outstanding for a reviewer; do not claim that
CI will perform them or treat missing evidence alone as a policy violation.

Output:

- **Verdict:** `Request changes` / `Comment` / `Approve`, plus one sentence.
- **Inline comments:** `` `path:line` — [blocker] note (§N) `` or `[nit]`, with
  a `suggestion` block where useful.
- **Gates:** one line; established violation = fail, insufficient evidence =
  not assessed, established inapplicability = n/a, assessed compliance = pass:
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
- **EOL cap (MUST).** First establish whether the main application is built from
  a directly-pulled upstream source (§3), citing its build part and source.
  Evidence of inapplicability, such as an archive-staged application, means
  `n/a`; unavailable provenance means *not assessed*, never assumed archive
  sourcing. A trigger repository, manifest source, PPA declaration or missing
  support plan alone does not establish applicability. ONLY when applicable,
  calculate review date + 3 calendar months. This is a maximum, not a minimum:
  an `end-of-life` on/before the cutoff passes; a later date blocks unless a
  human listed in `CODEOWNERS` has accepted a support plan. Do not assess it
  yourself.
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
- **Upstream-sourced.** The main application built from an external repository
  (`source:` on GitHub/Launchpad with `source-type: git`, or a plugin compiling
  upstream code) triggers the §2 EOL cap, even under `canonical`. Helper parts
  such as the security manifest do not count as the main application.
- **Additional package repositories (advisory).** If the recipe declares
  `package-repositories`, flag it as potentially upstream-sourced and ask which
  shipped packages, if any, come from those repositories. The declaration alone
  does not establish package provenance and MUST NOT trigger the §2 EOL cap.
- **Recipe change summary.** Compare both recipes for each source bump: summarize
  changes to parts/services, packages/slices and scripts, including permissions
  and ownership; distinguish version-only from content/runtime changes. A trigger
  commit bump alone proves no recipe delta. If either recipe is unavailable,
  mark the comparison *not assessed*; infer no changes.
- **Part/service removal (blocker).** If a source bump (new `commit` or
  `directory`) drops a `parts:` or `services:` entry the previous recipe had,
  request changes until it is restored or the author confirms in the PR that the
  removal is intentional (an upstream commit message is not that confirmation);
  meanwhile keep the revision at `edge` (§2).

  This confirmation rule applies to removal of a whole `parts:` or `services:`
  entry, NOT a package/slice within an existing part or an edit to a script.
- **Other recipe changes.** Inspect package/slice removals and script changes,
  including permissions and ownership. Block only with evidence connecting the
  change to concrete broken behavior; keep the revision at `edge` until a fix
  or counterevidence resolves it. Author intent or a promised future fix does
  not resolve demonstrated breakage. Unknown impact warrants a non-blocking
  `[nit]` suggesting verification and a *not assessed* regression gate, not a
  merge prerequisite or demand for proof of non-use. With only this uncertainty,
  use `Comment`, not `Request changes`. Proven harmless changes belong in the
  summary.

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
