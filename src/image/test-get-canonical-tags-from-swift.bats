#!/usr/bin/env bats

setup() {
  workdir=$(mktemp -d "${BATS_TEST_TMPDIR}/canonical-tags.XXXXXX")
  script_tree="${workdir}/tree"
  stub_bin="${workdir}/bin"

  mkdir -p \
    "${script_tree}/src/image" \
    "${script_tree}/src/configs" \
    "$stub_bin"
  cp "${BATS_TEST_DIRNAME}/get_canonical_tags_from_swift.sh" "${script_tree}/src/image/"
  : > "${script_tree}/src/configs/swift.public.novarc"

  cat > "${stub_bin}/swift" <<'EOF'
#!/usr/bin/env bash
cat "$SWIFT_LISTING"
EOF
  chmod +x \
    "${script_tree}/src/image/get_canonical_tags_from_swift.sh" \
    "${stub_bin}/swift"

  export PATH="${stub_bin}:${PATH}"
  export SWIFT_LISTING="${workdir}/listing.txt"
  export SWIFT_CONTAINER_NAME="oci-factory"
  export IMAGE_NAME="ruby"
  export GITHUB_OUTPUT="${workdir}/github-output"
  : > "$GITHUB_OUTPUT"

  script="${script_tree}/src/image/get_canonical_tags_from_swift.sh"
  cd "$workdir"
}

@test "lists one canonical tag per revision" {
  cat > "$SWIFT_LISTING" <<'EOF'
ruby/3.2-24.04/25/build_metadata.json
ruby/3.2-24.04/25/ruby_3.2-24.04_25
ruby/3.3-26.04/27/build_metadata.json
EOF

  run "$script"

  [[ "$status" -eq 0 ]]
  [[ "$(cat canonical-tags-file.txt)" == "3.2-24.04_25,3.3-26.04_27," ]]
  grep -Fx 'canonical-tags=3.2-24.04_25,3.3-26.04_27,' "$GITHUB_OUTPUT"
}

@test "ignores the upload lockfile of a concurrent build" {
  cat > "$SWIFT_LISTING" <<'EOF'
ruby/3.2-24.04/25/build_metadata.json
ruby/3.3-26.04/27/build_metadata.json
ruby/lockfile.lock
EOF

  run "$script"

  [[ "$status" -eq 0 ]]
  [[ "$(cat canonical-tags-file.txt)" == "3.2-24.04_25,3.3-26.04_27," ]]
}
