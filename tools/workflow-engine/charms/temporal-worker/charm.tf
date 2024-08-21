terraform {
  required_providers {
    juju = {
      version = "~> 0.13.0"
      source  = "juju/juju"
    }
  }
}

variable "juju_username" {}
variable "juju_password" {}

# The "JUJU SETTINGS 1" relies on the Juju controller having had already been
# configured/used in the local machine where you are running Terraform. I.e.:
#  1) the following environment variables, that correspond to the configuration
#     fields indicated above, are present:
#      - JUJU_CONTROLLER_ADDRESSES
#      - JUJU_USERNAME
#      - JUJU_PASSWORD
#      - JUJU_CA_CERT
#   
# or
# 
#  2) you have used this Juju controller locally before. This is the most
#     straight-forward solution. Remember, that it will use the configuration
#     used by the CLI at that moment. I.e. the fields are populated using the
#     output from running the command: `juju show-controller --show-password`
#     (which prints the contents of ~/.local/share/juju/)
#
# If you're running Terraform on a machine where you've never configured the
# Juju controller, then please comment "JUJU SETTINGS 1" and uncomment
# "JUJU SETTINGS 2"!

#### JUJU SETTINGS 1 ####
provider "juju" {
  username = var.juju_username
  password = var.juju_password
}
#### JUJU SETTINGS 1 - end ####

#### JUJU SETTINGS 2 ####
# variable "juju_controller_addresses" {}
# variable "juju_ca_certificate_file" {}

# provider "juju" {
#     controller_addresses = var.juju_controller_addresses
#     username = var.juju_username
#     password = var.juju_password
#     ca_certificate = file(var.juju_ca_certificate_file)
# }
#### JUJU SETTINGS 2 - end ####

# resource "juju_model" "oci-factory-model" {
#   name = "admin/microk8s-rocks-ps6-model"

#   cloud {
#     name = var.juju_cloud_name
#   }
# }

resource "juju_application" "temporal-worker-k8s" {
  name  = var.juju_application_name
  model = var.oci-factory-model

  charm {
    name    = var.juju_application_name
    channel = var.juju_application_channel
    base    = "ubuntu@22.04"
  }

  units = 2

  config = {
    # Authentication details
    auth-provider = "candid"
    # The candid authentication details are sensitive and individual,
    # and should only be set at deployment time
    candid-private-key = var.config_candid_private_key
    candid-public-key  = var.config_candid_public_key
    candid-username    = var.config_candid_username
    candid-url         = var.config_candid_url
    # Server settings
    host      = var.config_temporal_host
    queue     = var.config_temporal_queue
    namespace = "rocks"
    # Only needed if deploying under a proxy
    http-proxy  = var.config_temporal_proxy
    https-proxy = var.config_temporal_proxy
    # Charmed workflows
    # The "workflows-file-name" must match the wheel file created with poetry
    workflows-file-name = basename(var.config_temporal_workflows_file_path)
    # To support all defined workflows and activities, use the 'all' keyword
    supported-workflows  = "all"
    supported-activities = "all"
  }

  provisioner "local-exec" {
    command = <<EOT
set -ex
echo "Building wheel file..."
poetry build -f wheel
test -f ${var.config_temporal_workflows_file_path}

echo "Setting up env-file..."
# Cannot copy the .env file to a tmp path because Juju won't have access to it
env_file=".env"
trap "rm $env_file" EXIT
cp oci_factory/.env.template $env_file
set +x
sed -i 's/<username-replace-me>/"${var.env_eventbus_consumer_username}"/' $env_file
sed -i 's/<password-replace-me>/"${var.env_eventbus_consumer_password}"/' $env_file
set -x

# We need the full model name here!
full_model_name="$(juju show-model \
  | grep ' name:' \
  | grep '${var.oci-factory-model}' \
  | awk -F' ' '{print $NF}')"

echo "Attaching the env-file to the Juju application..."
juju attach-resource -m $full_model_name ${self.name} \
    env-file=$env_file

echo "Attaching the workflows-file to the Juju application..."
juju attach-resource -m $full_model_name ${self.name} \
    workflows-file=${var.config_temporal_workflows_file_path}

set +x
echo '
#############################################################################
You can now track the deployment status with:
    "juju status --watch 2s" 
#############################################################################
'
EOT
  }
}
