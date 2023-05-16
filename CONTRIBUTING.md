# Contributing

First and foremost, thank you for considering contributing to this project!

## Table of Contents

- [Contributing](#contributing)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Code of Conduct](#code-of-conduct)
  - [Canonical Contributor Agreement](#canonical-contributor-agreement)
  - [How to Contribute](#how-to-contribute)

## Getting Started

Before making any contributions, please take a moment to read through this
[CONTRIBUTING](/CONTRIBUTING.md) document and the project's
[README](/README.md), to understand how the project works.

This guideline applies to both Image Maintainers and OCI Factory Developers:

- **Image Maintainer**: also referred to as "**Maintainer**", is the Canonical
entity that owns and is responsible for an Ubuntu OCI image that is being
processed within this repository;
- **OCI Factory Developer**: anyone who contributes to the source code hosted
in this repository, which is being used to process the workflows and images
proposed by the **Maintainers**.

## Code of Conduct

This project and everyone participating in it must
follow a [Code of Conduct](/CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Please report unacceptable behaviour to <rocks@canonical.com>.

## Canonical Contributor Agreement

Before you contribute you should sign the
[Canonical contributor agreement](https://ubuntu.com/legal/contributors).
It's the easiest way for you to permit us to use your contributions.

## How to Contribute

Once comfortable with and abiding by the aforementioned concepts and practices,
please make sure you follow these guidelines when committing content for this
repository:

- format your commit messages according to the [Conventional Commits
specification](https://www.conventionalcommits.org/en/v1.0.0/). Example:

  ```console
  build(my-rock-name): build new version 1.3 of my-rock-name

  This is some additional and optional context explaining
  why this change is being made and what impact it will have. 
  ```

- if a PR has multiple commits, group (squash) them according to their
functional value, e.g. you shouldn't have multiple commits for fixing a single
bug within the same code block,
- if a PR is still being worked on, make sure to set it to "Draft",
- unless it's a trivial fix/improvement, it's generally worth [opening an
issue](https://github.com/canonical/oci-factory/issues) (making sure a similar
one doesn't exist already) to discuss the item before submitting a PR,
- if you are a **Maintainer**, you MUST acknowledge the conditions established
in the [Image Maintainer Agreement](/IMAGE_MAINTAINER_AGREEMENT.md).
