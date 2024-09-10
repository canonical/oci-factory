# Workflow Engine

The OCI Factory is complemented by a workflow engine which takes care of
actuating upon events of interest. To put it in simple terms, the workflow
engine has the intelligence to decide what happens, and when. On the other
hand, the GitHub workflows in the OCI Factory's repository are simply a set of
loosely coupled jobs for continuously testing and delivering OCI images.

Having said that, the OCI Factory's workflow engine is composed of Temporal Workflows. These Workflows need Temporal Workers and therefore an underlying
infrastructure to host them.

The Temporal server infrastructure already exists, so this directory hosts the
configurations and scripts necessary to deploy:

- [Infrastructure: MicroK8s cluster on OpenStack](#infra)

<a name="infra"></a>

## Infrastructure: MicroK8s cluster on OpenStack

The OpenStack VMs will host the MicroK8s cluster where the Temporal Workers
will be deployed.

### Prerequisites

The team already has an OpenStack environment for this. So make sure you have
access to
[it](https://canonical-rocks-team-docs.readthedocs-hosted.com/en/latest/openstack_at_canonical.html#ps6-bos03).

### Deploy a new MicroK8s cluster

See the instructions
[here](https://rt.admin.canonical.com/Ticket/Display.html?id=161278#txn-3692567)
for deploying a brand new, self-managed, K8s cluster in an existing OpenStack
environment.

NOTE: although the majority of this process is self-served, the infrastructure
can only be maintained by IS, which means we must **always open a request if
we need to alter the cluster (e.g. add/remove units)**.

#### Check the MicroK8s deployment

Once deployed, you should be able to reproduce the following steps from [within
the OpenStack environment where the K8s cluster was
deployed](https://canonical-rocks-team-docs.readthedocs-hosted.com/en/latest/openstack_at_canonical.html#ps6-bos03):

- check that there are VMs deployed and `ACTIVE` with `openstack server list`
- confirm that the MicroK8s Juju deployment is healthy with `juju status
microk8s`. You should see something like:

    ```
    Model                   Controller              Cloud/Region            Version  SLA          Timestamp
    model-name              prodstack-controller    cloud/region            3.1.6    unsupported  08:18:04Z

    App       Version  Status  Scale  Charm     Channel      Rev  Exposed  Message
    microk8s  1.28.3   active      3  microk8s  1.28/stable  213  yes      node is ready

    Unit         Workload  Agent  Machine  Public address   Ports                     Message
    microk8s/3*  active    idle   3        1.1.1.1          80/tcp,443/tcp,16443/tcp  node is ready
    microk8s/4   active    idle   4        1.1.1.2          80/tcp,443/tcp,16443/tcp  node is ready
    microk8s/5   active    idle   5        1.1.1.3          80/tcp,443/tcp,16443/tcp  node is ready

    Machine  State    Address           Inst id                               Series  AZ                   Message
    3        started  1.1.1.1           59708835-f5aa-46b7-90a2-95221d8b13db  jammy   availability-zone-3  ACTIVE
    4        started  1.1.1.2           855ffa20-6e15-4218-9e85-c494aa5fbbe8  jammy   availability-zone-1  ACTIVE
    5        started  1.1.1.3           ef04939a-a312-4405-a9a3-8afcec7fc8c0  jammy   availability-zone-2  ACTIVE
    ```

- try running a command inside one of the worker nodes: `juju run --unit
microk8s/3 -- microk8s kubectl get nodes`. You'll see something like:

    ```
    NAME                                   STATUS   ROLES    AGE   VERSION
    juju-2d57ab-prod-rocks-oci-factory-3   Ready    <none>   19h   v1.28.3
    juju-2d57ab-prod-rocks-oci-factory-4   Ready    <none>   19h   v1.28.3
    juju-2d57ab-prod-rocks-oci-factory-5   Ready    <none>   19h   v1.28.3
    ```

    Here are some other useful commands to help you assert that the cluster is
    health: `juju run --unit microk8s/3 -- microk8s status` and `juju run
    --unit microk8s/3 -- microk8s kubectl get po -A`.

- the cluster nodes should also be accessible via SSH: `juju ssh microk8s/3` or
`ssh ubuntu@<ip>`.

### Deploy a dedicated VM for the microk8s' Juju Controller

In order to deploy Kubernetes charms to the above microk8s cluster, we'll need
to bootstrap a Juju controller for that cloud.
In theory, we could use PS6 Juju client for this, but it is better not to
pollute that environment. So let's create a dedicated VM,
`rocks-ps6-juju-client`:

```bash
# From inside the PS6 environment, with the openstack credentials loaded
openstack keypair list
# If there isn't a "rocks-ps6-keypair" entry, create one with:
#   openstack keypair create --private-key .ssh/rocks-ps6-key rocks-ps6-keypair

openstack server create --flavor production-cpu2-ram4-disk20 \
    --image <take-an-ID-from-openstack image list> \
    --key-name rocks-ps6-keypair \
    --security-group <same-as-one-of-microk8s-instances> \
    rocks-ps6-juju-client

# Copy the microk8s KUBECONFIG file to the VM (we'll need it for Juju)
scp .kube/config ubuntu@<rocks-ps6-juju-client-ip>:/home/ubuntu/.kube/config

# SSH into the instance
ssh ubuntu@<rocks-ps6-juju-client-ip>

# Put the KUBECONFIG file in the right path and set up Juju
mkdir .kube
mv config .kube/
sudo snap install juju
mkdir -p ~/.local/share/juju

# You should now see microk8s listed in the Juju clouds
juju clouds

# Bootstrap the Juju controller for the microk8s cloud
# NOTE: we need to treat this as an external cloud, so follow this:
# https://juju.is/docs/juju/manage-clouds#heading--add-a-kubernetes-cloud
/snap/juju/current/bin/juju add-k8s microk8s-rocks-ps6
juju clouds
juju bootstrap microk8s-rocks-ps6 microk8s-rocks-ps6-controller --config controller-service-type=loadbalancer
juju controllers

# Add the Juju model
juju add-model microk8s-rocks-ps6-model

# NOTE: typically, we'll use Terraform to manage Juju charms, so install it too
sudo snap install terraform --classic

# We might also need poetry to build the wheel file for the charm, so...
sudo apt update
sudo apt install python3-virtualenv
virtualenv venv
. venv/bin/activate
# Drop the https_proxy is not running on PS6
https_proxy="http://squid.internal:3128" pip install poetry
```
