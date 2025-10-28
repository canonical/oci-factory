#!/bin/bash -e

## Install Skopeo
git clone -b ${SKOPEO_BRANCH} --depth 1 ${SKOPEO_URL} /tmp/skopeo
pushd /tmp/skopeo

docker run -v $PWD:/src -w /src -e DISABLE_DOCS=1 \
    golang:1.25 sh -c \
    'apt update; apt install -y libgpgme-dev libassuan-dev libbtrfs-dev libdevmapper-dev pkg-config; \
    git config --global --add safe.directory /src; make'

sudo mv bin/skopeo /usr/local/bin/
sudo chmod +x /usr/local/bin/skopeo
popd

sudo apt update
sudo apt install -y distro-info
