#!/usr/bin/env bats

setup() {
  workdir=$(mktemp -d "${BATS_TEST_TMPDIR}/tag-and-publish.XXXXXX")
  script_tree="${workdir}/tree"
  stub_bin="${workdir}/bin"
  export CALL_LOG="${workdir}/calls.log"

  mkdir -p \
    "${script_tree}/src/image" \
    "${script_tree}/src/shared" \
    "${script_tree}/src/uploads" \
    "$stub_bin"
  cp "${BATS_TEST_DIRNAME}/tag_and_publish.sh" "${script_tree}/src/image/"
  cp "${BATS_TEST_DIRNAME}/../shared/logs.sh" "${script_tree}/src/shared/"
  : > "$CALL_LOG"

  cat > "${script_tree}/src/uploads/oci_registry_upload.py" <<'EOF'
#!/usr/bin/env bash
printf 'uploader|%s|%s|%s\n' "$1" "$2" "${*:3}" >> "$CALL_LOG"
EOF
  cat > "${stub_bin}/docker" <<'EOF'
#!/usr/bin/env bash
printf 'docker|%s\n' "$*" >> "$CALL_LOG"
EOF
  cat > "${stub_bin}/aws" <<'EOF'
#!/usr/bin/env bash
printf 'aws|%s|%s|%s\n' "${AWS_ACCESS_KEY_ID:-}" "${AWS_SECRET_ACCESS_KEY:-}" "$*" >> "$CALL_LOG"
printf '%s\n' stub-ecr-token
EOF
  chmod +x \
    "${script_tree}/src/image/tag_and_publish.sh" \
    "${script_tree}/src/uploads/oci_registry_upload.py" \
    "${stub_bin}/docker" \
    "${stub_bin}/aws"

  export PATH="${stub_bin}:${PATH}"
  export GHCR_REPO=""
  export GHCR_USERNAME="ghcr-user"
  export GHCR_PASSWORD="ghcr-password"
  export DOCKER_HUB_NAMESPACE="docker.example/library"
  export DOCKER_HUB_CREDS_USR="docker-user"
  export DOCKER_HUB_CREDS_PSW="docker-password"
  export ECR_NAMESPACE="ecr-namespace"
  export ECR_CREDS_USR="ecr-key-id"
  export ECR_CREDS_PSW="ecr-secret"
  export ACR_REGISTRY="acr.example"
  export ACR_CREDS_USR="acr-user"
  export ACR_CREDS_PSW="acr-password"
  script="${script_tree}/src/image/tag_and_publish.sh"
}

teardown() {
  if [[ -n "${workdir:-}" && "$workdir" == "${BATS_TEST_TMPDIR}"/* ]]; then
    rm -rf -- "$workdir"
  fi
}

call_count() {
  local kind=$1
  local count=0
  local line
  while IFS= read -r line; do
    if [[ "$line" == "${kind}|"* ]]; then
      ((count += 1))
    fi
  done < "$CALL_LOG"
  printf '%s\n' "$count"
}

@test "Pro publishes only to ACR" {
  run "$script" image.tar ubuntu --pro 24.04 latest

  [[ "$status" -eq 0 ]]
  [[ "$(call_count uploader)" -eq 1 ]]
  grep -F 'uploader|image.tar|acr.example/ubuntu|24.04 latest' "$CALL_LOG"
  [[ "$(call_count docker)" -eq 0 ]]
  [[ "$(call_count aws)" -eq 0 ]]
}

@test "public publishes to Docker Hub and ECR without ACR" {
  run "$script" image.tar ubuntu 24.04 latest

  [[ "$status" -eq 0 ]]
  [[ "$(call_count uploader)" -eq 2 ]]
  grep -F 'docker|login -u docker-user -p docker-password' "$CALL_LOG"
  grep -F 'uploader|image.tar|docker.example/library/ubuntu|24.04 latest' "$CALL_LOG"
  grep -F 'aws|ecr-key-id|ecr-secret|ecr-public get-authorization-token' "$CALL_LOG"
  grep -F 'uploader|image.tar|public.ecr.aws/ecr-namespace/ubuntu|24.04 latest' "$CALL_LOG"
  ! grep -F 'acr.example/ubuntu' "$CALL_LOG"
}

@test "Pro with GHCR configured is rejected before publishing" {
  export GHCR_REPO="ghcr.io/example"

  run "$script" image.tar ubuntu --pro latest

  [[ "$status" -ne 0 ]]
  [[ "$output" == *"Pro images cannot be published to GHCR."* ]]
  [[ ! -s "$CALL_LOG" ]]
}

@test "at least one tag is required" {
  run "$script" image.tar ubuntu

  [[ "$status" -ne 0 ]]
  [[ "$output" == *"At least one tag is required."* ]]
  [[ ! -s "$CALL_LOG" ]]
}
