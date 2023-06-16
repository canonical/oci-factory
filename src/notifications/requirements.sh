#!/bin/bash -ex

YQ_VERSION=${YQ_VERSION:-"v4.32.2"}
YQ_BINARY=${YQ_BINARY:-"yq_linux_amd64"}

wget -q "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY}"
sudo mv "${YQ_BINARY}" /usr/bin/yq
sudo chmod +x /usr/bin/yq
