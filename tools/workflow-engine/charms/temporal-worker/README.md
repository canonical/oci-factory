# Charm: Temporal Worker for the OCI Factory

This folder provides the Temporal Workflows and Activities for the existing
[Temporal Worker
Charm](https://charmhub.io/temporal-worker-k8s?channel=latest/edge).

- [Charm: Temporal Worker for the OCI Factory](#charm-temporal-worker-for-the-oci-factory)
  - [Prerequisites](#prerequisites)
  - [Deploying the charm with Terraform](#deploying-the-charm-with-terraform)
    - [Additional prerequisites](#additional-prerequisites)
    - [Deploy](#deploy)
  - [Deploying the charm manually (testing)](#deploying-the-charm-manually-testing)
    - [From the PS6 dedicated instance (admins only)](#from-the-ps6-dedicated-instance-admins-only)
    - [From your workstation](#from-your-workstation)
    - [Note for future self](#note-for-future-self)
    - [Troubleshooting](#troubleshooting)
  - [Triggering a workflow](#triggering-a-workflow)

## Prerequisites

1. `juju` (>=3.0, >=3.1.5 recommended).
2. `poetry` (>= 1.5.1)
3. an existing MicroK8s cluster and the Juju controller for it. If you don't have one already, you have 2
options:
    1. quickly set up a local one (ideal for testing), by following this
    [tutorial](<https://juju.is/docs/juju/tutorial#heading--set-up-create-your-test-environment>),
       - **NOTE:** if you are deploying the charm with Terraform from outside
        the cluster, you might need to configure the Juju controller as follows:

         ```bash
         juju bootstrap my-microk8s-cloud <controller-name> \
             --config controller-service-type=loadbalancer \
             --config controller-external-ips='[<nodeIP>,...]'
         ```

         <a name="external-ip"></a>

         This is because
         Terraform will rely on the controller's `api-endpoints` which, by
         default, are only set with a `ClusterIP` and are thus
         **not reachable** from outside the cluster. By using these
         `--config` options, you can tell Kubernetes to expose the
         controller on the VM's IP, which should
         be reachable from your machine. References:
         - <https://bugs.launchpad.net/juju/+bug/1883006>
         - <https://juju.is/docs/juju/juju-bootstrap>
         - <https://discourse.charmhub.io/t/juju-add-k8s-in-openstack-no-route-to-controller/3625>

       or
    2. use [our production one](../../README.md). In this case, you can simply
    SSH into the OpenStack environment and run `juju clouds`, to get something
    like:

        ```
        Clouds available on the client:
        Cloud      Regions  Default    Type  Credentials  Source    Description
        localhost  1        localhost  lxd   0            built-in  LXD Container Hypervisor
        microk8s   0                   k8s   0            built-in  A local Kubernetes context
        ```

        - the Juju controller for this microk8s cloud will be on a dedicated
        VM, so if you're an admin, just `ssh ubuntu@<rocks-ps6-juju-client-ip>`
        (see how this instance is configured [here](../../README.md)). If you're
        not an admin, read "[From your workstation](#from-your-workstation)" to
        know how to register the existing controller in your workstation.

4. If the worker is deployed in a Canonical infrastructure, you also need to ensure that
the proper squid proxy and firewall configurations are set to allow traffics between the
cluster and the Temporal staging, the Grafana, Karapace, Kafka, Github, AWS ECR and
Google-OIDC-related servers are permitted.

## Deploying the charm with Terraform

This is the preferred option (Terraform should already be installed, but if not,
run `sudo snap install terraform --classic`).

### Additional prerequisites

- **if** you are managing an already existing deployment, **you need**
to request and copy the corresponding `terraform.tfstate` file into this
directory. NOTE: this file may contain sensitive information so please do not
commit or share it.

### Deploy

> TIP: create a `variables.tfvars` key-value file with your test input
> parameters
> defined so you don't always have to pass them to `terraform apply`, using
> instead `terraform apply -var-file="variables.tfvars"`. Don't worry, this file
> is ignored by Git (see `.gitignore`).

Start by running:

```bash
terraform init
```

In `charm.tf` you'll find two different settings for the Juju provider:

**JUJU SETTINGS 1**: relies on the Juju controller having already been
configured/used in the local machine where you are running Terraform (e.g. as
shown below in the "[From your workstation](#from-your-workstation)" section).
I.e.:

  1. the following environment variables, that correspond to the configuration
  fields indicated above, are present:
     - JUJU_CONTROLLER_ADDRESSES
     - JUJU_USERNAME
     - JUJU_PASSWORD
     - JUJU_CA_CERT

     or

  2. you have used this Juju controller locally before. This is the most straightforward solution. Remember, that it will use the configuration
  used by the CLI at that moment. I.e. the fields are populated using the
  output from running the command: `juju show-controller --show-password`
  (which prints the contents of ~/.local/share/juju/)

 **JUJU SETTINGS 2**: if you're running Terraform on a machine where you've
never configured the Juju controller, then please comment "JUJU SETTINGS 1" and
uncomment "JUJU SETTINGS 2" in `charm.tf`!

Then, make sure your configs are good with a dry-run:

```bash
terraform plan -var-file="variables.tfvars"
```

If everything is good, proceed with the deployment:

```bash
terraform apply
```

**NOTE**: remember to update the `terraform.tfstate` in the same place where you
first found it :)

## Deploying the charm manually (testing)

Ideally, the charm is deployed with Terraform (see above).

However, for debugging and/or quick testing purposes, you might need to use
Juju directly to deploy this charm manually. This section describes that
process.

### From the [PS6 dedicated instance]((../../README.md)) (admins only)

1. the Juju controller and model should already exist. If not, set them (see
[Prerequisites](#prerequisites) 3)

    ```bash
    juju show-controller microk8s-rocks-ps6-controller
    juju show-model admin/microk8s-rocks-ps6-model
    ```

2. deploy the upstream `temporal-worker-k8s` charm

    ```bash
    juju deploy temporal-worker-k8s
    ```

    **NOTE:** the application won't yet be functional (as reported by
    `juju status`) because it still needs to be configured with our workflows.

3. clone this repo

    ```bash
    # Only set the https_proxy when running inside the cloud environment
    https_proxy="http://squid.internal:3128" git clone https://github.com/canonical/oci-factory
    cd oci-factory/tools/workflow-engine/charms/temporal-worker/
    ``````

4. use the [existing Python env](../../README.md) and generate a wheel file
with our Temporal workflows

    ```bash
    . ~/venv/bin/activate
    # If the venv doesn't exist already, then run:
    # $ virtualenv venv
    # $ . venv/bin/activate
    poetry build -f wheel
    # You should now have a new "dist" folder with the wheel file inside
    ```

5. copy the `config.yml.template` file to `config.yml` and edit it. This is
the charm configuration file, containing the deployment settings. You'll need
your own OIDC credentials for this.

6. configure the deployed charm

    ```bash
    juju config temporal-worker-k8s --file config.yml
    ```

     - if some information has been left out of the `config.yml` file
     then you should add each key individually. For example:

        ```bash
        juju config temporal-worker-k8s \
            oidc-auth-uri="https://accounts.google.com/o/oauth2/auth" \
            oidc-token-uri="https://oauth2.googleapis.com/token" \
            oidc-auth-cert-url="https://www.googleapis.com/oauth2/v1/certs" \
            queue="test.rocks.team"
        ```

       **NOTE:** make sure at least one message has already been sent to the
       selected queue, with the proper schemas, otherwise the workflow will
       complain about
       `"Subject '<queueName>-value' not found. (HTTP status code 404...)"`.

7. copy the `oci_factory/.env.template` file to
`oci_factory/.env` and edit it. These are the
workflow-specific configurations for the `consumer` activities
8. attach the environment file to the application

    ```bash
    juju attach-resource temporal-worker-k8s env-file=oci_factory/.env
    ```

9. attach the workflow wheel file to the charm application

    ```bash
    juju attach-resource temporal-worker-k8s workflows-file=./dist/oci_factory_workflows-0.0.1-py3-none-any.whl
    ```

10. Configure `no-proxy` for `.canonical.com` hosts
    ```bash
    juju config temporal-worker-k8s no-proxy=".canonical.com"
    ```

11. check the application status and wait for it to be up and running

    ```bash
    juju status --watch 2s
    ```

Once the application is up and running, your charmed worker will be connected
to the Temporal server and ready to execute the workflows.

See the [section below](#triggering-a-workflow) to learn how to manually
trigger the execution of a workflow.

### From your workstation

The Juju controller must already exist, so **ask an admin (superuser)** to add
you as a new Juju user:

```bash
# Do this operation with "admin" rights on the cluster
# and make sure the desired controller is selected
juju add-user <your-username>
juju grant <your-username> write <existing-model-name>
juju grant <your-username> admin <existing-application-name-if-already-deployed>
```

The `juju add-user` command above will provide a unique token that the admin
must provide to you.

On your workstation, **make sure you're connected to the VPN** and type:

```bash
# On your local workstation
juju register --replace --debug <token>
# You'll need to pick a password for your user.
# If you ever lose this password, ask you admin to reset it from the admin
# instance, via the `juju change-user-password` command
```

And you're good to go (see `juju controllers` and `juju status`).

*From here, you can repeat exactly the same steps as in the
[previous section](#from-the-ps6-dedicated-instance-admins-only) as if you are connected to the PS6 bastion.*

### Note for future self

When running `juju register...`, if you see the following issue:

```
ERROR cannot connect to k8s api server; try running 'juju update-k8s --client <k8s cloud name>': starting proxy for api connection: connecting k8s proxy: Get "https://<ip>:<port>/api/v1/namespaces/<controller-name>/services/controller-service": dial tcp <ip>:<port>: connect: no route to host
```

then it is most likely because the controller wasn't bootstrapped with
`--config controller-service-type=loadbalancer` (see the bootstrap instructions
[here]((../../README.md))). If you **cannot** re-bootstrap the controller with
the correct `service-type`, then you'll need to work around this error (which is
actually a bug, being investigated [here](https://bugs.launchpad.net/juju/+bug/2052711)).

The workaround is:

1. Ask an admin for the controller's `proxy-config.config.api-host` value. This
can be found within the admin instance's `.local/share/juju/controllers.yaml`
file.

1. Once you are given that value, open the same file
(`.local/share/juju/controllers.yaml`) within your workstation and replace the
`api-host` field with it.

1. Then, from your workstation:

    ```bash
    juju controllers --refresh
    # It should be ok now
    juju controllers
    # Make sure you are using that controller and model
    juju switch microk8s-rocks-ps6-controller
    juju switch microk8s-rocks-ps6-controller:admin/microk8s-rocks-ps6-model
    ```


### Troubleshooting

If after configuring your application, its unit still shows up in error, here
are a few things you can do to debug and fix it:

- `juju resolve temporal-worker-k8s/0` will try to resume the application unit,
- `juju run temporal-worker-k8s/0 restart` is a charm-specific action that
will restart the unit,
- `juju debug-log` will print the `juju` logs, including your unit's, where you
can possibly find any application-specific exception that might be preventing
your unit from starting.
- ``juju run --unit <unit in `juju status` from cluster bastion> -- microk8s kubectl -n microk8s-rocks-ps6-model logs <unit in `juju status` from juju client> -c temporal-worker``
from the PS6 bastion to obtain the runtime log of the worker container.

If the errors are application-related, then upon fixing them, don't forget to
rebuild the wheel file and re-attach it to the Juju application.

<a name="trigger-a-workflow"></a>

## Triggering a workflow

There are a few ways to interact with Temporal. The most popular ones are the
`temporal` and `tctl` [CLI commands](https://docs.temporal.io/cli/), and
language-specific [SDKs](https://docs.temporal.io/dev-guide/).

SDKs are better suited for automation, in cases where your workflows are being
triggered by other programs.

In this case, and for testing purposes, we recommend using `tctl` (installed
from [here](https://snapcraft.io/tctl)).

If this is the first time using `tctl`, you'll need to login:

```bash
tctl.stg login
# Follow the URL, login, and the tctl will capture the necessary cookies
```

For non-interactive login, you might need to experiment with [these instructions](https://github.com/canonical/temporal-lib-samples/blob/main/docs/tctl.md#staging).

Then you can execute a workflow with the following command:

```bash
tctl.stg --address=temporal.staging.commercial-systems.canonical.com:443 \
    --tls-server-name=temporal.staging.commercial-systems.canonical.com \
    -n rocks \
    workflow execute \
    --task-queue tests.oci-factory \
    --type ConsumeEventsWorkflow \
    --input '"<strArg1>"' \
    --input '"<strArg2>"'
```

The command will trigger the workflow and wait for its completion.
