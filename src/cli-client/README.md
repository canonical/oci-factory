
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

```bash
# Install
git clone https://github.com/canonical/oci-factory.git
cd oci-factory/src/cli-client
go install github.com/canonical/oci-factory/cli-client/cmd/oci-factory
```

```bash
# Trigger workflows
cd <directory containing rockcraft.yaml>
# Run `oci-factory upload --help` for more help
oci-factory upload --release ...
```

## How to debug the CLI client

The debug log can be enabled with the following command

```bash
export LOGGER_DEBUG=1
```