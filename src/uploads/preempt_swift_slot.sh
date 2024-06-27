#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

IMAGE_NAME=$1
TRACK=$2
REVISION=$3

staging_area=$(mktemp -d)

mkdir -p "${staging_area}/${IMAGE_NAME}/${TRACK}/${REVISION}"

touch "${staging_area}/${IMAGE_NAME}/${TRACK}/${REVISION}/dummy.txt"

pushd "${staging_area}"

# SWIFT_CONTAINER_NAME comes from env
swift upload "$SWIFT_CONTAINER_NAME" "${IMAGE_NAME}" 
