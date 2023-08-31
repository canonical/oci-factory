# Charm: Temporal Worker for the OCI Factory

This folder provides the Temporal Workflows and Activities for the existing
[Temporal Worker
Charm](https://charmhub.io/temporal-worker-k8s?channel=latest/edge).

## Prerequisites

1. `juju` (>=3.0, >=3.1.5 recommended).
2. `poetry` (>= 1.5.1)
3. an existing MicroK8s cluster. If you don't have one already, you have 2
options:
    1. quickly set up a local one (ideal for testing):
       - deploy a Multipass VM with enough memory (>=3G), cpu (>=2) and disk
       (>=20G). You can use any other cloud instance or even an LXC instance if
       you prefer,
       - log in to the instance,
       - install MicroK8s, exactly as instructed [here](
       <https://juju.is/docs/juju/get-started-with-juju#heading--prepare-your-cloud>),

        or
    2. use [Terraform to deploy the cluster on Scalingstack](../../README.md).
4. a Juju controller for the K8s cloud
    - if doing this for the first time, you'll need to add the K8s cloud to
    Juju. If you're running `juju` from inside the MicroK8s cluster, then it should automatically detect the underlying Kubernetes cloud (check `juju
    clouds`), otherwise you'll need to add it manually:
      - from the MicroK8s cluster, get the Kubernetes configuration via
      `kubectl config view --raw`, and copy it,
      - on the `juju` machine, save the above configuration into a file (e.g.
      `$HOME/.kube/microk8s-config`),
          - if the config's server IP is private, change it to an IP
          your `juju` machine can reach. For example, if you have MicroK8s
          running in Multipass, take the K8s control plane machine IP from
          `multipass list`. Similarly, for MicroK8s running on Scalingstack,
          you can take the control plane's IP from `openstack server list`,
      - add the Kubernetes cloud:
      `KUBECONFIG=/path/to/config juju add-k8s my-microk8s-cloud --client`,
    - if you don't yet have a controller for the MicroK8s cluster from above (
    see `juju controllers`), then you must bootstrap it:

        ```bash
        juju bootstrap my-microk8s-cloud <controller-name> \
            --config controller-service-type=loadbalancer \
            --config controller-external-ips='[<nodeIP>,...]'
        ```

        <a name="external-ip"></a>

        **NOTE:** the `--config` options are only required when deploying the
        charm with Terraform from outside the cluster. This is because
        Terraform will rely on the controller's `api-endpoints` which, by
        default, are only set with a `ClusterIP` and are thus **not reachable**
        from outside the cluster. By using these `--config` options, you can
        tell Kubernetes to expose the controller on the VM's IP, which should
        be reachable from your machine. References:
         - <https://bugs.launchpad.net/juju/+bug/1883006>
         - <https://juju.is/docs/juju/juju-bootstrap>
         - <https://discourse.charmhub.io/t/juju-add-k8s-in-openstack-no-route-to-controller/3625>

## Deploying the charm with Terraform

This is the preferred option.

### Additional prerequisites

- `terraform` (>=v1.5.5)
- this TF configuration is designed to use the MicroK8s cluster deployed
[here](../../README.md). Before proceeding, make sure you:
  - connect to the VPN,
  - forward all the necessary remote endpoints to your `localhost``, with:

      ```bash
      ssh -L 5000:<keystoneUrl>:<keystonePort> -L ...<username>@<internalOSServer>
      ```

    this is needed because of Bastion,
- (optional) if you are managing an already existing deployment, **you need**
to request and copy the corresponding `terraform.tfstate` file into this
directory. NOTE: this file may contain sensitive information so please do not
commit or share it.

`terraform apply`

TIP: create a `variables.tfvars` key-value file with your test input parameters
defined so you don't always have to pass them to `terraform apply`, using
instead `terraform apply -var-file="variables.tfvars"`. Don't worry, this file
is ignored by Git (see `.gitignore`).

### Troubleshooting

> │ Error: dial tcp 10.152.183.75:17070: i/o timeout  
> │  
> │   with provider["registry.terraform.io/juju/juju"],  
> │   on charm.tf line 32, in provider "juju":  
> │   32: provider "juju" {}  
> │  
> │ Connection error, please check the controller_addresses property set on the
provider

If this happens, you're likely running Terraform from a host outside the
MicroK8s cluster. In this case, you'll want to double-check your Juju
controller's network configuration, making sure it is being exposed to an
external IP your host can reach. See [how to configure the controller](#external-ip) above.

## Deploying the charm manually (testing)

Ideally, the charm is deployed alongside the underlying MicroK8s infrastructure
and thus described as IaC, with Terraform.

However, for debugging and/or quick testing purposes, you might need to use
Juju directly to deploy this charm manually. This section describes that
process.

1. start by adding a new model

    ```bash
    juju add-model oci-factory-apps
    ```

2. deploy the upstream `temporal-worker-k8s` charm

    ```bash
    juju deploy temporal-worker-k8s --channel edge
    ```

    **NOTE:** the application won't yet be functional (as reported by
    `juju status`) because it still needs to be configured with our workflows.

3. generate a wheel file with our Temporal workflows

    ```bash
    poetry build -f wheel
    # You should now have a new "dist" folder with the wheel file inside
    ```

4. copy the `config.yml.template` file to `config.yml` and edit it. These is
the charm configuration file, containing the deployment settings
1. configure the deployed charm

    ```bash
    juju config temporal-worker-k8s --file config.yml
    ```

     - if some information has been left out of the `config.yml` file
     then you should add each key individually. For example:

        ```bash
        juju config temporal-worker-k8s \
            candid-private-key="foo" \
            candid-public-key="bar" \
            candid-username="baz" \
            queue="test.rocks.team"
        ```

       **NOTE:** make sure at least one message has already been sent to the
       selected queue, with the proper schemas, otherwise the workflow will
       complain about
       `"Subject '<queueName>-value' not found. (HTTP status code 404...)"`.

2. copy the `oci_factory/activities/consumer/.env.template` file to
`oci_factory/activities/consumer/.env` and edit it. These are the
workflow-specific configurations for the `consumer` activities
1. attach the environment file to the application

    ```bash
    juju attach-resource temporal-worker-k8s env-file=oci_factory/activities/consumer/.env
    ```

2. attach the workflows wheel file to the charm application

    ```bash
    juju attach-resource temporal-worker-k8s workflows-file=./dist/oci_factory_workflows-0.0.1-py3-none-any.whl
    ```

3. check the application status and wait for it to be up and running

    ```bash
    juju status --watch 2s
    ```

Once the application is up and running, your charmed worker will be connected
to the Temporal server and ready to execute the workflows.

See the [section below](#triggering-a-workflow) to learn how to manually
trigger the execution of a workflow.

#### Troubleshooting

If after configuring your application, its unit still shows up in error, here
are a few things you can do to debug and fix it:

- `juju resolve temporal-worker-k8s/0` will try to resume the application unit,
- `juju run temporal-worker-k8s/0 restart` is a charm-specific action that
will restart the unit,
- `juju debug-log` will print the `juju` logs, including your unit's, where you
can possibly find any application-specific exception that might be preventing
your unit from starting.

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
from [here](https://github.com/canonical/temporal-k8s/tree/main/tctl-snap)).

If this is the first time using `tctl`, you'll need to login:

```bash
tctl login
# Follow the URL, login, and the tctl will capture the necessary cookies
```

For non-interactive login, you might need to experiment with [these instructions](https://github.com/canonical/temporal-lib-samples/blob/main/docs/tctl.md#staging).

Then you can execute a workflow with the following command:

```bash
tctl -n <namespace> workflow execute \
    --task-queue <temporal-queue-name> \
    --type <workflow-name> \
    --input '"<strArg1>"' \
    --input '"<strArg2>"'
```

The command will trigger the workflow and wait for its completion.
