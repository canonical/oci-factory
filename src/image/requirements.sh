#!/bin/bash -e

sudo cp "$(dirname "$(realpath $0)")/../shared/logs.sh" /usr/local/bin/
sudo cp "$(dirname "$(realpath $0)")/../uploads/oci_registry_upload.py" /usr/local/bin/
ln -s oci_registry_upload.py /usr/local/bin/cpc-build-tools.oci-registry-upload

## Install Skopeo
git clone -b ${SKOPEO_BRANCH} --depth 1 ${SKOPEO_URL} /tmp/skopeo
pushd /tmp/skopeo

docker run -v $PWD:/src -w /src -e DISABLE_DOCS=1 \
    golang:1.18 sh -c 'apt update; apt install -y libgpgme-dev libassuan-dev libbtrfs-dev libdevmapper-dev pkg-config; make'

sudo mv bin/skopeo /usr/local/bin/
sudo chmod +x /usr/local/bin/skopeo
popd

sudo apt update
sudo apt install -y distro-info
