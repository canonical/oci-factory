#!/usr/bin/env bats

SOURCE_DIR=$(dirname -- "${BASH_SOURCE[0]}")

load '/usr/lib/bats/bats-support/load.bash'
load '/usr/lib/bats/bats-assert/load.bash'

@test "report extra trivyignore entries" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/positive.json" "${BATS_TEST_DIRNAME}/testdata/extra.trivyignore"
  assert_success
  assert_output "::notice file=${BATS_TEST_DIRNAME}/testdata/extra.trivyignore,line=5::CVE-2024-34156 not present anymore, can be safely removed."
}

@test "do not report when trivyignore entries match vulnerabilities" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/positive.json" "${BATS_TEST_DIRNAME}/testdata/exact.trivyignore"
  assert_success
  assert_output ""
}

@test "do not fail when no packages found" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/empty.json" "${BATS_TEST_DIRNAME}/testdata/extra.trivyignore"
  assert_success
  assert_output --partial "::notice file=${BATS_TEST_DIRNAME}/testdata/extra.trivyignore,line=2::CVE-2025-47907 not present anymore, can be safely removed."
  assert_output --partial "::notice file=${BATS_TEST_DIRNAME}/testdata/extra.trivyignore,line=5::CVE-2024-34156 not present anymore, can be safely removed."
}

@test "do not fail when no vulnerabilities found" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/negative.json" "${BATS_TEST_DIRNAME}/testdata/extra.trivyignore"
  assert_success
  assert_output --partial "::notice file=${BATS_TEST_DIRNAME}/testdata/extra.trivyignore,line=2::CVE-2025-47907 not present anymore, can be safely removed."
  assert_output --partial "::notice file=${BATS_TEST_DIRNAME}/testdata/extra.trivyignore,line=5::CVE-2024-34156 not present anymore, can be safely removed."
}

@test "do not fail when trivyignore is empty" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/positive.json" "${BATS_TEST_DIRNAME}/testdata/empty.trivyignore"
  assert_success
  assert_output ""
}

@test "fail when scan result cannot be parsed" {
  run ${BATS_TEST_DIRNAME}/check-trivyignore-entries.sh "${BATS_TEST_DIRNAME}/testdata/error.json" "${BATS_TEST_DIRNAME}/testdata/extra.trivyignore"
  assert_failure
  assert_output "Unable to parse scan result."
}
