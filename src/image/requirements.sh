#!/bin/bash -e

sudo apt update
sudo apt install -y distro-info

# Install aws cli if not already installed
if ! command -v aws &> /dev/null; then
    sudo snap install aws-cli --classic
fi
