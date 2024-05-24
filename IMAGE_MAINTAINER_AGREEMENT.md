# Bring Your Own Ubuntu Image

Onboarding your rocks and Ubuntu-based OCI images to the official “ubuntu”
registry namespace.

## Table of Contents

- [Bring Your Own Ubuntu Image](#bring-your-own-ubuntu-image)
  - [Table of Contents](#table-of-contents)
  - [Glossary](#glossary)
  - [Abstract](#abstract)
  - [Rationale](#rationale)
  - [Maintainer agreement](#maintainer-agreement)
    - [Verify eligibility](#verify-eligibility)
    - [Acknowledge accountability](#acknowledge-accountability)
    - [Make the Ubuntu Rock’s Git project public](#make-the-ubuntu-rocks-git-project-public)
    - [Join the `~ubuntu-docker-images` team](#join-the-ubuntu-docker-images-team)
    - [Request the creation of a new registry repository](#request-the-creation-of-a-new-registry-repository)
    - [Enable security monitoring](#enable-security-monitoring)
    - [Acknowledge the delay to address issues](#acknowledge-the-delay-to-address-issues)
    - [Provide documentation](#provide-documentation)
    - [Acknowledge the OCI tagging convention](#acknowledge-the-oci-tagging-convention)
    - [Understand the Ubuntu Rock’s stability commitments](#understand-the-ubuntu-rocks-stability-commitments)
    - [Test before contributing](#test-before-contributing)
  - [Contributing](#contributing)
  - [Feedback](#feedback)

## Glossary

|  |  |
|---|---|
| CI/CD | Continuous Integration and Continuous Deployment |
| Maintainer | Canonical entity who owns and is responsible for an Ubuntu Rock/Image. |
| OCI image | Currently limited to rock images only. |
| Registry | An OCI container registry, as [defined](https://oras.land/#what-are-oci-registries) by the OCI specification. |
| Rocks | Canonical’s OCI images, built via Rockcraft. See the definition [here](https://canonical-rockcraft.readthedocs-hosted.com/en/latest/explanation.html#what-is-a-rock). |
| Rockcraft | A craft tool to create rocks. Read more about it [here](https://canonical-rockcraft.readthedocs-hosted.com/en/latest/index.html). |
| Ubuntu Rocks | Canonical-maintained, curated rocks collection, based on Ubuntu. |
| “ubuntu” namespace | The public registries’ organisation name under which Ubuntu Rocks are published. Example: <https://hub.docker.com/u/ubuntu>. |
|  |  |

## Abstract

This document details the process for Canonical teams to publish Ubuntu Rocks
to our official registry namespaces (like the “ubuntu” repository on Docker
Hub). It is written from the perspective of the ROCKS team, who owns and
manages said namespaces.

## Rationale

Ubuntu Rocks is a collection of curated and vendor-maintained container images,
based on the Ubuntu distribution. The aim of this collection is to provide
developers and IT managers with a trusted source of containers, removing the stress and risks associated with using open-source software. Additionally,
publishers can leverage the managed dependencies and distribution system to
focus on their code & added value.

The latest development tracks and some LTS versions of the Ubuntu Rocks
portfolio are accessible for free, to anyone. Long-term maintained tracks (up to 10 years, LTS+ESM), hardened flavours (FIPS, CIS, etc.), and other Ubuntu Pro rocks are distributed under authenticated access gated to Canonical customers as part of the Ubuntu Pro offering.

From the end consumer perspective (developers and IT managers/C-suite), the principal value proposition is the confidence and stability that comes with using a trusted and vendor-maintained collection of consistent container images. Ubuntu Rocks are appliance-type container images, completed with a set of Ubuntu and chiselled Ubuntu base images. Canonical commercially supports Ubuntu Rocks collections.

For publishers (ISVs and open source projects), Ubuntu Rocks provide managed dependencies and a distribution system that enables them to focus on their added value instead of worrying about dependencies.  Publishers would bring in their source code, and map it with existing or newly-added software dependencies from the collection. Being part of a collection allows for easy distribution of software across all platforms, in a consistent and developer-friendly manner. By leveraging this system, publishers can ensure that their software is available to end-users, consistently, without having to worry about the complexity of software distribution.

Ubuntu Rocks are built with a stable version of Rockcraft. The building and testing infrastructure for these rocks will be owned by the ROCKS team.

To cover the immediate need to gatekeep the images under the "ubuntu"
namespace, a temporary rocks build system will be put in place by the ROCKS team. With this central infrastructure in place, we will be able to advertise early Ubuntu Rocks and use this work to adapt and evolve the rocks tooling and offering.

## Maintainer agreement

We require contributors to abide by certain rules and conventions, in order to ensure the quality promised by the Ubuntu Rocks offering & vision.

By participating in this program, contributors agree to keep up with the following quality standards and procedures and any further updates. Additionally, contributors understand that the infrastructure hereby provided by the ROCKS team will continuously adapt to the evolution of the rocks story
within Canonical, potentially affecting their workflows.

**TL,DR checklist**

- [ ] Verify eligibility
- [ ] Acknowledge accountability
- [ ] Share the Maintainer’s contact information
- [ ] Make the Ubuntu Rock’s Git project public
- [ ] Join the ~ubuntu-docker-images team on Launchpad
- [ ] Request the creation of a new registry repository
- [ ] Enable security monitoring
- [ ] Send an email to the Security team
- [ ] Ensure the needed security manifests are added to the Ubuntu Rock
- [ ] Acknowledge the delay to address issues
- [ ] Provide documentation
- [ ] Acknowledge the OCI tagging convention
- [ ] Understand the Ubuntu Rock’s stability commitments
- [ ] Test before contributing

### Verify eligibility

This [Maintainer Agreement](#maintainer-agreement) is only eligible for individuals/teams whose proposed OCI images abide by the following rule:

- it is a rock, i.e. built by a Canonical-maintained version of Rockcraft.

### Acknowledge accountability

The ROCKS team **does not own** the rocks published by other Canonical teams.

The ROCKS team is responsible for the processes, tooling and infrastructure that lead to a recognized Ubuntu Rock being built, tested and published.

The contributing team **owns** and **is responsible** for the Ubuntu Rock, and thus must be clearly identified as the Maintainer (for which **contact information must be provided**). The Maintainer commits to maintaining the Ubuntu Rock for the duration of the associated commitments and claimed stability.

### Make the Ubuntu Rock’s Git project public

The infrastructure provided by the ROCKS team for building, testing and publishing Ubuntu Rocks relies on the sources of said rocks to be available via a public Git repository, as this will help with the provenance attestation and version control.

The Maintainer **must** ensure that Ubuntu rock project is public and on a Git-based version control system. If this is not possible, exceptional cases can still be onboarded, but must first be discussed with the rocks’ Engineering and Product teams.

### Join the `~ubuntu-docker-images` team

There is a Launchpad [team](https://launchpad.net/~ubuntu-docker-images) that is used as a catch-all for everything related to the Ubuntu Rocks. It is the driver for the [Ubuntu Docker Images](https://launchpad.net/ubuntu-docker-images) project, and is meant for

- reporting bugs,
- issuing security notifications,
- sending general announcements,
- serving Launchpad-hosted rocks projects.

The Maintainer (be it in the form of a team mailing list or individual users), **must** ask the ROCKS team to be added to this team.

### Request the creation of a new registry repository

For each new Ubuntu Rock, a corresponding repository must be manually initialised.

The Maintainer **must** ask the ROCKS team to create the said repository, making sure that

- its name matches the one from the Ubuntu Rock, and
- one repository is created per registry of interest (i.e. Docker Hub, ECR, ACR, etc.)

### Enable security monitoring

Prior to releasing an Ubuntu rock to any channel, the Maintainer **must** declare the image and its dependencies to the Security team so that they can be notified when a security patch becomes available.

The security team owns multiple security notification services which are relevant to the security maintenance of the Ubuntu Rocks. Although these services might not cover all contents within one’s rock, better security coverage is expected in the future.

To enable security monitoring for an Ubuntu Rock, the Maintainer must:

- contact the ROCKS Team (either directly, through an [issue](https://github.com/canonical/oci-factory/issues), or via <rocks@canonical.com>) with the subject being "Enable security monitoring",
and stating:
  - the Ubuntu Rock name;
  - the URL for the corresponding repository in Docker Hub;
  - the contact information of the recipients who should get the notifications;
    - this can simply be <ubuntu-docker-images@lists.launchpad.net> if the recipients represent the Maintainer and have already been added to the `~ubuntu-docker-images` in Launchpad;
- **if** the Ubuntu Rock has additional `.deb` packages on top of the Ubuntu base, then it **must** include a security manifest `/usr/share/rocks/dpkg.query`. It can be generated by

    ```bash
    mkdir -p /usr/share/rocks/; \
    (echo "# os-release" && cat /etc/os-release && echo "# dpkg-query" && dpkg-query -f '${db:Status-Abbrev},${binary:Package},${Version},${source:Package},${Source:Version}\n' -W) > /usr/share/rocks/dpkg.query;
    ```
  
  - here's an example of how you'd apply the above snippet in a `rockcraft.yaml`
  file:

    ```yaml
    parts:
      deb-security-manifest:
        plugin: nil
        after:
          - # make this run after all other parts that install overlay packages
        override-prime: |
          set -x
          mkdir -p $CRAFT_PRIME/usr/share/rocks/
          (echo "# os-release" && cat /etc/os-release && echo "# dpkg-query" && dpkg-query --admindir=$CRAFT_PRIME/var/lib/dpkg/ -f '${db:Status-Abbrev},${binary:Package},${Version},${source:Package},${Source:Version}\n' -W) > $CRAFT_PRIME/usr/share/rocks/dpkg.query
    ```

  - if this deb-based security manifest is not present, the Maintainer **acknowledges** that it *might* be automatically added by the Build system, consequently adding a new OCI layer to the Ubuntu Rock.
- **if** the Ubuntu Rock reuses content from a Snap, then it **must** include the Snap’s `snapcraft.yaml` and `manifest.yaml`, under `/usr/share/rocks/`.
- **if** the Ubuntu Rock is based on other upstream source code, it **must** also include a security manifest. Currently, there is no convention for what this security manifest should look like. You **must** reach out to the Security team and discuss this on a case per case basis. As an example, the (now deprecated) [ubuntu/cortex](https://hub.docker.com/r/ubuntu/cortex) image [produces](https://git.launchpad.net/~ubuntu-docker-images/ubuntu-docker-images/+git/utils/tree/golang-manifest-builder.py) this custom security
[manifest](https://git.launchpad.net/~ubuntu-docker-images/ubuntu-docker-images/+git/cortex/tree/oci/Dockerfile.ubuntu?h=1.7-21.04#n58).

### Acknowledge the delay to address issues

The infrastructure provided by the ROCKS team will progressively become more autonomous when it comes to addressing the “need to update an Ubuntu Rock”. Nonetheless, and mainly in the event of a security patch (e.g. USN), the Maintainer **must** be able to address and update if needed, the affected Ubuntu Rocks in less than 24h. The build and publish process are designed to allow for a quick response delay to Maintainer-driven build requests (builds are triggered as soon as the build request is accepted). This very short timeline is designed to target a 24h average response time to critical CVEs from CVE fix available to the patched image availability.

We acknowledge that this is a difficult 24/7 target and that it might be missed until better build infrastructure becomes available (especially for updates driven by software which doesn’t come from the Ubuntu archives or the Snap
store). We ask Maintainers to plan accordingly, automating as much as possible.

### Provide documentation

The Maintainer **is responsible** for maintaining up-to-date, accurate, and complete documentation for their Ubuntu Rocks. We require this documentation to match a predefined template, in order to maintain a sense of consistency and developer experience across all Ubuntu Rocks.

A template for managing your image’s documentation will be provided to Maintainers in the build system’s user guide.

The ROCKS team will then ensure that the proper docs are being published to the right places (Docker Hub and ECR).

### Acknowledge the OCI tagging convention

Note that the target vision is to only use Ubuntu LTS “base” series.

For consistency and alignment with the target, we **require** the Maintainer to **acknowledge** that the OCI tags will:

- follow the concepts of semantic channels as described in [snapcraft.io/docs/channels](https://snapcraft.io/docs/channels),
- be dynamically generated by the ROCKS team’s build infrastructure, based on the information provided by the Ubuntu Rock’s metadata and the Trigger files submitted by the Maintainer.

What to expect:

- all rocks are *uploaded* into a staging (not “ubuntu”) registry after each build,
  - these images will have a **revision tag**, such as `X.Y-A.B_#`
- all Ubuntu Rocks that are requested to be released to the “ubuntu” namespace (in Docker Hub and ECR) will take an existing rock with a *revision tag* and assign a [*risk*](https://snapcraft.io/docs/channels#heading--risk-levels) to it, resulting in a **semantic channel tag** structured in the following way,

    <center>
    X.Y-A.B_< risk >
    </center>

- the *risk* can later be updated to a more stable one (similar to the *promotion* process with Snaps) using Trigger files,
- released Ubuntu Rocks can also be assigned additional OCI tag **aliases**, according to the values allowed in the Trigger files (for example: the “latest” and equivalent “edge”, “beta” tags...),
- only **semantic channels** should be advertised in documentation
(i.e. `X.Y-A.B_<risk>`)

where:

- `X.Y-A.B` is the semantic versioning *default track* (aka *canonical track*),
- `X.Y` is the rock's version, as specified in its *rockcraft.yaml* file,
- `A.B` is the Ubuntu series as *base* (*build-base*) in rockcraft.yaml,
- `#` is the rock's *revision* number, an incremental arbitrary number generated by the build system
- `<track>` is the release channel’s track, and
- `<risk>` is the release channel’s risk.

### Understand the Ubuntu Rock’s stability commitments

*Please first read [snapcraft.io/docs/channels](https://snapcraft.io/docs/channels)*.

At the moment, we can’t truly enforce the same promotion concepts and rules as for Snaps.
<u>Discipline will thus be essential for early publishers</u>.

**Here’s the commitments we’re making to our users:**

- Channel Tag shows the most stable channel for that track. A track is a combination of both the application version and the underlying Ubuntu series, e.g. `1.0-22.04`.
  - *This means in documentation we recommend pulling our images using the most stable semantic channel tag available.*
- Channels are ordered from the most stable to the least stable: *stable, candidate, beta,* and *edge*. More risky channels are always implicitly available. So if *beta* is listed, you can also pull the *edge* channel. If a *candidate* is listed, you can pull *beta* and *edge*. When *stable* is listed, all four are available.
  - *From the user perspective, the ‘risk’ is the highest risk level they are willing to take. A user pulling ‘edge’ explicitly acknowledges their acceptance of API-breaking releases.*
  - *From the publisher's perspective, making a release available in a ‘candidate’ channel will also make it available to users requesting ‘beta’ and ‘edge’ risks, unless another specific release is explicitly delivered to them through this track.*
- <u>Images are guaranteed to progress through the sequence *edge, beta, candidate* before *stable*.</u>

This last statement is quite important as users might rely on this affirmation. An image build must always be made available and tagged as “edge” first. Then, it can progress through the different risks up to “stable”. It must go through all possible risks and be in order. **No rebuild should happen when an image is moved from one risk to another**.

- *Take the situation with a user continuously pulling ‘1.2-22.04_beta’. They are willing to accept the ‘beta’ risk. At some point, release 1.2-22.04 is going to be stable and only receive security patches.
If the ‘beta’ channel was pinned to a specific revision and security patches were directly delivered to ‘stable’, this user would continuously miss security updates.*

  *Therefore, it is important to make sure all builds are in order (or simultaneously) made available to all four risks.*

We recommend the following risk usage:

- ***Edge*** should map with your code versioning tool (eg “Git”). You can automatically trigger builds for *edge* on code changes. No need for QA, no API promises, and no feature promises.
- ***Beta*** is the next step right after *edge*. We recommend some sort of automated QA gate from *edge* to *beta*, including functional testing. These releases may still have unfinished parts. Breaking changes and regressions are still relatively common here. You could map successful outputs of your CI to the *beta* channel.
- ***Candidate*** is the first level with some sense of stability. It’s for users who need to test updates prior to stable deployment, or those verifying whether a specific issue has been resolved. We recommend publishing there when you’re ready to move to *stable* but want some more real-world experimentation and manual testing. Moving from *beta* to *candidate* should likely be a manual process. Breaking changes should be avoided as much as possible but can still happen.
- ***Stable*** risk is dedicated to production environments. Any content published here should be **production-ready**. When we publish something as *stable* to our official namespaces, there’s an implied support commitment as per our Service Terms (read the Ubuntu Pro Service Description). **Publishing software as stable = committing to supporting it in production**.

  - <u>Tracks with a *stable* channel should get an “end of life” timeframe commitment from their Maintainer team (as documented in Trigger files). This end-of-life date is the minimal support timeframe the Maintainer commits to.
    - For releases documented as ‘LTS’, the end of life should match the underlying Ubuntu series.</u>

We consider as Breaking changes any mismatch with the initially packed application version’s API or any non-compatible change in the container image usage/configuration.

### Test before contributing

This is an item that must be continuously checked and adopted as a best practice. In order to maintain the aforementioned high standards and stability commitments, we urge the Maintainer to **continuously test** the Ubuntu Rock before making build and release requests to the ROCKS team’s infrastructure.

## Contributing

Upon conforming with the Maintainer Agreement, the Maintainer is ready to start submitting requests for building and releasing their OCI images. The Maintainer is expected to follow the [CONTRIBUTING](/CONTRIBUTING.md) guidelines.

## Feedback

Becoming a Maintainer gives the contributors a certain number of benefits in exchange for the important constraints listed before. These benefits must not be abused.

- Authority of the “ubuntu” namespace on Docker Hub and Amazon ECR Public and any further registry that we might publish to,
- “Verified Publisher” status on Docker Hub with unrestricted pulls for end users,
- Be a part of the Ubuntu Rocks early product stages, leading to external visibility and advanced features usage,
- ROCKS team expertise and support through Mattermost channel, meetings/ workshops, support JIRA tickets if needed

We kindly ask Maintainers to provide the ROCKS team with feedback on the tooling, product usage and value proposition.
