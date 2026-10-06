# OCI Factory — Agent Guide

OCI Factory publishes Ubuntu OCI images (rocks) to Docker Hub and ECR under the
`ubuntu` namespace, and to ACR under `ubuntu-pro`. Each image has maintainer
files in `oci/<name>/`: `image.yaml` (the image trigger: builds and releases),
`documentation.yaml` and `contacts.yaml`. Business logic lives in `src/`, CI in
`.github/workflows/`.

Read [README.md](README.md) for the repository introduction and
[CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Working conventions

- Conventional Commits; squash commits by functional value; mark in-progress PRs
  as Draft.
- A PR that changes files below `oci/` must touch only one `oci/<name>/`
  directory (several versions or tracks of that image are fine).

## Reviewing pull requests

When reviewing a pull request or local changes, use the
[code-review skill](.agents/skills/code-review/SKILL.md).
