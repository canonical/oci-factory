
# The OCI Factory CLI Client

A CLI client that triggers GitHub workflows for building, uploading and releasing images in 
[OCI Factory](https://github.com/canonical/oci-factory).

## How to use

### New User

See ["How to Contribute as a Maintainer"](https://github.com/canonical/oci-factory?tab=readme-ov-file#as-a-maintainer--).

Upon finishing the onboarding, the user should receive a GitHub Personal Access Token. This token grants you proper
permissions to trigger the build, upload and release of your rocks. This token should never be shared with 
third-parties, nor put anywhere that is publicly available.

The user will be asked to input the GitHub Personal Access Token upon triggering a workflow. For a non-interactive
terminal, it is possible to assign the token to the environmental variable `export GITHUB_TOKEN=<your token>`, and pass
`-y` to confirm the triggering by default.

### Install using Snap

```bash
sudo snap install oci-factory
```

### Install using Go

#### Dependencies

```bash
# install git
sudo apt update && sudo apt install -y git
```

Golang-go can be installed either with APT or Snap:

```bash
# install golang-go with apt
sudo apt update && sudo apt install -y golang-go
```

```bash
# install golang-go with snap
sudo snap install go --classic
```

Now install the CLI client
```bash
go install github.com/canonical/oci-factory/src/cli-client/cmd/oci-factory
```

# Triggering workflows
Note: The workflow can only be triggered for the rocks owned by Canonical, i.e., whose repository
belong to the organization Canonical in GitHub.
```bash
cd <directory containing rockcraft.yaml>
# Run `oci-factory upload --help` for more help
oci-factory upload --release track=<release track>,risks=<risk1>[,<risk2>...],eol=yyyy-mm-dd
```

## How to debug the CLI client

The debug log can be enabled with the following command

```bash
export LOGGER_DEBUG=1
```
