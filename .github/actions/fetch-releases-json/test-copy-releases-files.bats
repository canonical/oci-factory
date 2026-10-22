#!/usr/bin/env bats

setup() {
  original_pwd=$PWD
  workdir=$(mktemp -d "${BATS_TEST_TMPDIR}/copy-releases.XXXXXX")
  releases_dir="${workdir}/releases"
  output_dir="${workdir}/output"
  mkdir -p \
    "${releases_dir}/oci/public-only" \
    "${releases_dir}/oci/pro-only" \
    "${releases_dir}/oci/both" \
    "${output_dir}/oci/public-only" \
    "${output_dir}/oci/pro-only" \
    "${output_dir}/oci/both"

  printf '%s\n' '{"source":"public-only"}' > "${releases_dir}/oci/public-only/_releases.json"
  printf '%s\n' '{"source":"pro-only"}' > "${releases_dir}/oci/pro-only/_pro_releases.json"
  printf '%s\n' '{"source":"both-public"}' > "${releases_dir}/oci/both/_releases.json"
  printf '%s\n' '{"source":"both-pro"}' > "${releases_dir}/oci/both/_pro_releases.json"
  printf '%s\n' '{"ignored":true}' > "${releases_dir}/oci/both/metadata.json"

  cd "$output_dir" || return 1
}

teardown() {
  cd "$original_pwd" || return 1
  if [[ -n "${workdir:-}" && "$workdir" == "${BATS_TEST_TMPDIR}"/* ]]; then
    rm -rf -- "$workdir"
  fi
}

@test "copies a public-only release file" {
  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" public-only "$releases_dir"

  [[ "$status" -eq 0 ]]
  cmp "${releases_dir}/oci/public-only/_releases.json" "oci/public-only/_releases.json"
  [[ ! -e "oci/public-only/_pro_releases.json" ]]
}

@test "copies a Pro-only release file" {
  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" pro-only "$releases_dir"

  [[ "$status" -eq 0 ]]
  cmp "${releases_dir}/oci/pro-only/_pro_releases.json" "oci/pro-only/_pro_releases.json"
  [[ ! -e "oci/pro-only/_releases.json" ]]
}

@test "copies both public and Pro release files" {
  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" both "$releases_dir"

  [[ "$status" -eq 0 ]]
  cmp "${releases_dir}/oci/both/_releases.json" "oci/both/_releases.json"
  cmp "${releases_dir}/oci/both/_pro_releases.json" "oci/both/_pro_releases.json"
}

@test "wildcard copies all public and Pro release files only" {
  rm -rf -- "${output_dir}/oci"

  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" "*" "$releases_dir"

  [[ "$status" -eq 0 ]]
  cmp "${releases_dir}/oci/public-only/_releases.json" "oci/public-only/_releases.json"
  cmp "${releases_dir}/oci/pro-only/_pro_releases.json" "oci/pro-only/_pro_releases.json"
  cmp "${releases_dir}/oci/both/_releases.json" "oci/both/_releases.json"
  cmp "${releases_dir}/oci/both/_pro_releases.json" "oci/both/_pro_releases.json"
  [[ ! -e "oci/both/metadata.json" ]]
}

@test "missing image succeeds without creating release files" {
  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" missing "$releases_dir"

  [[ "$status" -eq 0 ]]
  [[ ! -e "oci/missing/_releases.json" ]]
  [[ ! -e "oci/missing/_pro_releases.json" ]]
}

@test "wildcard fails for an invalid releases directory" {
  run "${BATS_TEST_DIRNAME}/copy-releases-files.sh" "*" "${workdir}/missing-releases"

  [[ "$status" -ne 0 ]]
}
