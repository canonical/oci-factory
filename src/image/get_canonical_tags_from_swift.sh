#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

canonical_tags=$(swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME/ \
    | awk -F '/' '{print $2"_"$3}' | uniq | sort | tr '\n' ',')

echo "canonical-tags=${canonical_tags}" >> "$GITHUB_OUTPUT"

echo "${canonical_tags}" > canonical-tags-file.txt
echo "canonical-tags-file=canonical-tags-file.txt" >> "$GITHUB_OUTPUT"
