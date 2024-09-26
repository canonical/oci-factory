#!/bin/bash -eu

# LP configurations
mkdir -p $HOME/.ssh
chmod 700 $HOME/.ssh

ssh-keyscan -H git.launchpad.net | tee $HOME/.ssh/known_hosts

echo "${ROCKS_DEV_LP_SSH_PRIVATE}" >$HOME/.ssh/id_rsa

set -x
chmod 600 $HOME/.ssh/id_rsa

## To avoid installing Snaps, just take the needed Python script
## for later tagging and publishing rocks
git init /tmp/cpc-build-tools
pushd /tmp/cpc-build-tools
git remote add origin git+ssh://${ROCKS_DEV_LP_USERNAME}@${CPC_BUILD_TOOLS_REPO}
# using main instead of ${CPC_BUILD_TOOLS_REPO_REF} because of an unexpected
# new issue with Launchpad: 
# error: Server does not allow request for unadvertised object 9b716ed8a8ba728d036b54b1bb17a8f49dbda434
git fetch --depth 1 origin main # ${CPC_BUILD_TOOLS_REPO_REF}
git checkout FETCH_HEAD

sudo mv /tmp/cpc-build-tools/* /usr/local/bin/
sudo chmod +x /usr/local/bin/oci_registry_upload.py
ln -s oci_registry_upload.py /usr/local/bin/cpc-build-tools.oci-registry-upload
popd
##

## Install Skopeo
git clone -b ${SKOPEO_BRANCH} --depth 1 ${SKOPEO_URL} /tmp/skopeo
pushd /tmp/skopeo

docker run -v $PWD:/src -w /src -e DISABLE_DOCS=1 \
    golang:1.18 sh -c 'apt update; apt install -y libgpgme-dev libassuan-dev libbtrfs-dev libdevmapper-dev pkg-config; make'

sudo mv bin/skopeo /usr/local/bin/
sudo chmod +x /usr/local/bin/skopeo
popd
