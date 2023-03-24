#!/bin/bash -e

# Source Swift config
. $(dirname $0)/../configs/swift.public.novarc

# Does image already exist in Swift?
# If not, then this is immediately revision number 1
swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME | grep $IMAGE_NAME || \
    (REVISION=1 && \
        mkdir -p ${IMAGE_NAME}/${REVISION} && \
        swift upload $SWIFT_CONTAINER_NAME ${IMAGE_NAME} && \
        echo "revision=${REVISION}" >> "$GITHUB_OUTPUT" && exit 0)

# If the script gets here, then it means this image already has revisions
highest_revision=$(swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME \
                    | sort -t / -k 2 -V \
                    | tail -1 \
                    | awk -F'/' '{print $2}')

REVISION=$(( $highest_revision + 1 ))
mkdir -p ${IMAGE_NAME}/${REVISION}
swift upload $SWIFT_CONTAINER_NAME ${IMAGE_NAME}/${REVISION}
echo "revision=${REVISION}" >> "$GITHUB_OUTPUT"