#!/usr/bin/env bats

SOURCE_DIR=$(dirname -- "${BASH_SOURCE[0]}")

setup() {
  workdir=$(mktemp -d)
  mkdir -p $workdir/img
  echo -n "*       @code-owner" > $workdir/CODEOWNERS
  echo -e "maintainers:\n  - maintainer" > $workdir/img/contacts.yaml
}

@test "blocks non-code-owner-non-maintainer user" {
  {
    output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "random" "true" $workdir "img" 2>&1)
    exit_status=$?
  } || true
  [[ $exit_status -eq 1 ]]
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is triggered by a user neither as a code owner nor a maintainer of the image img" ]]
}

@test "allows code owner" {
  output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "code-owner" "true" $workdir "img" 2>&1)
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is triggered by code-owner as the code owner" ]]
}

@test "allows image maintainer" {
  output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "maintainer" "true" $workdir "img")
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is triggered by maintainer as a maintainer of the image img" ]]
}

@test "allows non-code-owner-non-maintainer user" {
  output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "random" "false" $workdir "img")
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is not restricted to non-code-owner or non-maintainer users" ]]
}

@test "user as both code-owner and maintainer is triggered as code owner" {
  echo -n " @maintainer" >> $workdir/CODEOWNERS
  output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "maintainer" "true" $workdir "img")
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is triggered by maintainer as the code owner" ]]
}

@test "teams are expanded to team members" {
  echo -n "@canonical/rocks" >> $workdir/CODEOWNERS
  output=$(${BATS_TEST_DIRNAME}/validate-actor.sh "ROCKsBot" "true" $workdir "img")
  [[ $(echo "${output}" | tail -n 1) =~ "The workflow is triggered by ROCKsBot as the code owner" ]]
}
