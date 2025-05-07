#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

if [[ "$RUNNER_DEBUG" == "1" ]]; then
  set -x
fi

REVISION_DATA_DIR=$1

staging_area=$(mktemp -d)

for revision in $(ls ${REVISION_DATA_DIR}); do
    image_name=$(jq -r '.name' "${REVISION_DATA_DIR}/${revision}")
    track=$(jq -r '.track' "${REVISION_DATA_DIR}/${revision}")
    mkdir -p "${staging_area}/${image_name}/${track}/${revision}"
    touch "${staging_area}/${image_name}/${track}/${revision}/dummy.txt"
done

pushd "${staging_area}"

# SWIFT_CONTAINER_NAME comes from env
swift upload "$SWIFT_CONTAINER_NAME" "${IMAGE_NAME}"
