#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: $0 --archive <oci-archive-path>"
}

archive=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archive)
            archive="$2"
            shift 2
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

if [[ -z "${archive}" ]]; then
    usage
    exit 1
fi

if [[ ! -f "${archive}" ]]; then
    echo "OCI archive does not exist: ${archive}" >&2
    exit 1
fi

layer_indexes() {
    local layer_count="$1"

    if [[ -z "${layer_count}" || "${layer_count}" == "null" ]]; then
        echo "Unable to determine OCI image layers to encrypt." >&2
        exit 1
    fi

    if [[ "${layer_count}" -le 0 ]]; then
        echo "Cannot encrypt image with no layers." >&2
        exit 1
    fi

    seq -s, 0 "$((layer_count - 1))"
}

archive_layout=""
raw_manifest=""
if ! raw_manifest=$(skopeo inspect --raw "oci-archive:${archive}" 2>/dev/null); then
    archive_layout="$(mktemp -d)"
    trap 'rm -rf "${archive_layout}"' EXIT
    tar -xf "${archive}" -C "${archive_layout}"
    raw_manifest=$(jq . "${archive_layout}/index.json")
fi

if jq -e 'has("layers")' <<< "${raw_manifest}" > /dev/null; then
    layer_indexes "$(jq -r '.layers | length' <<< "${raw_manifest}")"
    exit 0
fi

if ! jq -e 'has("manifests")' <<< "${raw_manifest}" > /dev/null; then
    echo "Unsupported OCI archive manifest: expected layers or manifests." >&2
    exit 1
fi

if [[ -z "${archive_layout}" ]]; then
    archive_layout="$(mktemp -d)"
    trap 'rm -rf "${archive_layout}"' EXIT
    tar -xf "${archive}" -C "${archive_layout}"
fi

layer_counts=$(
    jq -r '.manifests[].digest' <<< "${raw_manifest}" |
    while read -r digest; do
        blob="${digest#sha256:}"
        jq '.layers | length' "${archive_layout}/blobs/sha256/${blob}"
    done | sort -n | uniq
)

if [[ -z "${layer_counts}" ]]; then
    echo "Unable to determine OCI image layers to encrypt." >&2
    exit 1
fi

if [[ "$(wc -l <<< "${layer_counts}")" -ne 1 ]]; then
    echo "Cannot encrypt all layers: manifests have different layer counts: ${layer_counts}" >&2
    exit 1
fi

layer_indexes "${layer_counts}"
