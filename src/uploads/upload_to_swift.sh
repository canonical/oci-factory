#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

set -x

IMAGE_NAME=$1
TRACK=$2
REVISION=$3
BUILD_METADATA_FILE=$4
SBOM_FILE=$5
VULN_REPORT_FILE=$6

staging_area=$(mktemp -d)

mkdir -p "${staging_area}/${IMAGE_NAME}/${TRACK}/${REVISION}"

cp "$BUILD_METADATA_FILE" "$SBOM_FILE" "$VULN_REPORT_FILE" \
    "${staging_area}/${IMAGE_NAME}/${TRACK}/${REVISION}"

pushd "${staging_area}"

# SWIFT_CONTAINER_NAME comes from env
swift upload "$SWIFT_CONTAINER_NAME" "${IMAGE_NAME}" 
