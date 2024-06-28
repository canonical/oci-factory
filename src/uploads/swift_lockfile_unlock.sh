#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

IMAGE_NAME=$1

# check if the ${IMAGE_NAME}/lockfile.lock exists in the swift container
# if it does, remove it
# if it does not, emit an error
# SWIFT_CONTAINER_NAME comes from env
LOCKFILE="${IMAGE_NAME}/lockfile.lock"
swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME | grep "$LOCKFILE" && \
    (swift delete $SWIFT_CONTAINER_NAME "$LOCKFILE" && echo "Lock file removed successfully.") || \
    echo "Lock file does not exist."
