#!/usr/bin/env bats

SCRIPT="${BATS_TEST_DIRNAME}/get_encrypt_layers_from_oci_archive.sh"

setup() {
  workdir="$(mktemp -d)"
}

teardown() {
  rm -rf "${workdir}"
}

sha() {
  sha256sum "$1" | cut -d' ' -f1
}

write_blob() {
  local layout="$1"
  local file="$2"
  local digest
  digest="$(sha "${file}")"
  mkdir -p "${layout}/blobs/sha256"
  cp "${file}" "${layout}/blobs/sha256/${digest}"
  echo "sha256:${digest}"
}

make_config() {
  local layout="$1"
  local config_file="${layout}/config.json"
  printf '{}' > "${config_file}"
  write_blob "${layout}" "${config_file}"
}

make_layer() {
  local layout="$1"
  local number="$2"
  local layer_file="${layout}/layer-${number}.tar"
  printf 'layer-%s' "${number}" > "${layer_file}"
  write_blob "${layout}" "${layer_file}"
}

make_manifest() {
  local layout="$1"
  local layer_count="$2"
  local manifest_file="$3"
  local config_digest layer_digest layers_json

  config_digest="$(make_config "${layout}")"
  layers_json="[]"
  for ((i=0; i<layer_count; i++)); do
    layer_digest="$(make_layer "${layout}" "${i}")"
    layers_json="$(jq --arg digest "${layer_digest}" '. + [{mediaType: "application/vnd.oci.image.layer.v1.tar+gzip", digest: $digest, size: 7}]' <<< "${layers_json}")"
  done

  jq -n \
    --arg config_digest "${config_digest}" \
    --argjson layers "${layers_json}" \
    '{schemaVersion: 2, mediaType: "application/vnd.oci.image.manifest.v1+json", config: {mediaType: "application/vnd.oci.image.config.v1+json", digest: $config_digest, size: 2}, layers: $layers}' \
    > "${manifest_file}"
  write_blob "${layout}" "${manifest_file}"
}

make_archive() {
  local layout="$1"
  local archive="$2"
  tar -C "${layout}" -cf "${archive}" .
}

make_single_manifest_archive() {
  local archive="$1"
  local layer_count="$2"
  local layout="${workdir}/layout"
  mkdir -p "${layout}"
  printf '{"imageLayoutVersion":"1.0.0"}' > "${layout}/oci-layout"
  manifest_digest="$(make_manifest "${layout}" "${layer_count}" "${layout}/manifest.json")"
  jq -n --arg digest "${manifest_digest}" '{schemaVersion: 2, manifests: [{mediaType: "application/vnd.oci.image.manifest.v1+json", digest: $digest, size: 1, annotations: {"org.opencontainers.image.ref.name": "test"}}]}' > "${layout}/index.json"
  make_archive "${layout}" "${archive}"
}

make_index_archive() {
  local archive="$1"
  local first_count="$2"
  local second_count="$3"
  local layout="${workdir}/layout"
  mkdir -p "${layout}"
  printf '{"imageLayoutVersion":"1.0.0"}' > "${layout}/oci-layout"
  first_digest="$(make_manifest "${layout}" "${first_count}" "${layout}/manifest-amd64.json")"
  second_digest="$(make_manifest "${layout}" "${second_count}" "${layout}/manifest-arm64.json")"
  jq -n \
    --arg first_digest "${first_digest}" \
    --arg second_digest "${second_digest}" \
    '{schemaVersion: 2, mediaType: "application/vnd.oci.image.index.v1+json", manifests: [{mediaType: "application/vnd.oci.image.manifest.v1+json", digest: $first_digest, size: 1, platform: {os: "linux", architecture: "amd64"}}, {mediaType: "application/vnd.oci.image.manifest.v1+json", digest: $second_digest, size: 1, platform: {os: "linux", architecture: "arm64"}}]}' \
    > "${layout}/index.json"
  make_archive "${layout}" "${archive}"
}

@test "single manifest with one layer returns 0" {
  archive="${workdir}/single-one.oci"
  make_single_manifest_archive "${archive}" 1

  run "${SCRIPT}" --archive "${archive}"

  [ "${status}" -eq 0 ]
  [ "${output}" = "0" ]
}

@test "single manifest with three layers returns comma-separated indexes" {
  archive="${workdir}/single-three.oci"
  make_single_manifest_archive "${archive}" 3

  run "${SCRIPT}" --archive "${archive}"

  [ "${status}" -eq 0 ]
  [ "${output}" = "0,1,2" ]
}

@test "index with consistent child layer counts returns indexes" {
  archive="${workdir}/index.oci"
  make_index_archive "${archive}" 2 2

  run "${SCRIPT}" --archive "${archive}"

  [ "${status}" -eq 0 ]
  [ "${output}" = "0,1" ]
}

@test "index with mismatched child layer counts fails" {
  archive="${workdir}/index-mismatch.oci"
  make_index_archive "${archive}" 2 3

  run "${SCRIPT}" --archive "${archive}"

  [ "${status}" -eq 1 ]
  [[ "${output}" == *"manifests have different layer counts"* ]]
}

@test "manifest with no layers fails" {
  archive="${workdir}/empty.oci"
  make_single_manifest_archive "${archive}" 0

  run "${SCRIPT}" --archive "${archive}"

  [ "${status}" -eq 1 ]
  [[ "${output}" == *"Cannot encrypt image with no layers"* ]]
}
