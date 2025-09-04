#!/usr/bin/env bats

SOURCE_DIR=$(dirname -- "${BASH_SOURCE[0]}")

load '/usr/lib/bats/bats-support/load.bash'
load '/usr/lib/bats/bats-assert/load.bash'

setup_file() {
  echo "setup" >&3
  workdir=$(mktemp -d)
  pushd $workdir
  git clone https://github.com/canonical/oci-factory.git oci-factory-releases -b _releases --depth 1
  popd
  export workdir
}

@test "copy single existing _releases.json file" {
  run ${BATS_TEST_DIRNAME}/copy-releases-files.sh mock-rock "${workdir}/oci-factory-releases"
  assert_success
  [[ -f "oci/mock-rock/_releases.json" ]]
}

@test "copy single non-existing _releases.json file" {
  run ${BATS_TEST_DIRNAME}/copy-releases-files.sh mock-nonexistent "${workdir}/oci-factory-releases"
  assert_success
  [[ ! -f "oci/mock-nonexistent/_releases.json" ]]
}

@test "copy all _releases.json files" {
  run ${BATS_TEST_DIRNAME}/copy-releases-files.sh "*" "${workdir}/oci-factory-releases"
  assert_success
  for dir in $(find "oci/" -mindepth 1 -maxdepth 1 -type d); do
    [[ -f "$dir/_releases.json" ]]
  done
  assert_equal \
    $(find "oci/" -mindepth 1 -maxdepth 1 -type d | wc -l) \
    $(find "${workdir}/oci-factory-releases/oci/" -mindepth 1 -maxdepth 1 -type d | wc -l)
}

teardown_file() {
  find . -name "_releases.json" -exec rm {} \;
}
