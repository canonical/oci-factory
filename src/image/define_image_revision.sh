#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

# Does image already exist in Swift?
# If not, then this is immediately revision number 1
swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME/ | grep $IMAGE_NAME || \
    (echo "revision=1" >> "$GITHUB_OUTPUT" && exit 0)

# If the script gets here, then it means this image already has revisions
highest_revision=$(swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME/ \
                    | sort -t / -k 3 -V \
                    | tail -1 \
                    | awk -F'/' '{print $3}')

REVISION=$(( $highest_revision + 1 ))
echo "revision=${REVISION}" >> "$GITHUB_OUTPUT"
