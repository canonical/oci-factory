#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

IMAGE_NAME=$(echo ${TRIGGER_PATH} | rev | cut -d '/' -f 2 | rev)
canonical_tags=$(swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME | awk -F '/' '{print $2"_"$3}' | uniq | tr '\n' ',')

echo "canonical-tags=${canonical_tags}" >> "$GITHUB_OUTPUT"
