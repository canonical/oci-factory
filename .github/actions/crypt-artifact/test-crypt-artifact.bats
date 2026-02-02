#!/usr/bin/env bats

SOURCE_SCRIPT="${BATS_TEST_DIRNAME}/crypt-artifact.sh"

# Setup the test environment
setup() {
  export workdir=$(mktemp -d)
  
  echo "This is File A's content." > "$workdir/file_a.txt"
  echo "Content for File B." > "$workdir/file_b.dat"
  
  export TEST_PASSPHRASE="SuperSecretPass123"
}

# Teardown the test environment
teardown() {
  rm -rf "$workdir"
}

## ---------------------------------------------
## Test Suite for crypt-artifact.sh
## ---------------------------------------------

@test "encrypt mode works for multiple files" {
  local file_a="$workdir/file_a.txt"
  local file_b="$workdir/file_b.dat"
  local encrypted_a="${file_a}.gpg"
  local encrypted_b="${file_b}.gpg"
  
  # Encrypt the files
  run bash "$SOURCE_SCRIPT" "encrypt" "$workdir" "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$?" -eq 0 ]]
  
  # Check that the original files are removed
  ! [ -f "$file_a" ]
  ! [ -f "$file_b" ]
  
  # Check that the encrypted files exist
  [ -f "$encrypted_a" ]
  [ -f "$encrypted_b" ]
  
  # Verify that the file content is actually encrypted (i.e., not readable plain text)
  ! grep -q "This is File A's content." "$encrypted_a"
  ! grep -q "Content for File B." "$encrypted_b"
}

@test "decrypt mode works for encrypted files" {
  local file_a="$workdir/file_a.txt"
  local file_b="$workdir/file_b.dat"
  local encrypted_a="${file_a}.gpg"
  local encrypted_b="${file_b}.gpg"
  
  # Encrypt the files first
  run bash "$SOURCE_SCRIPT" "encrypt" "$workdir" "$TEST_PASSPHRASE"
  
  # Decrypt the files
  run bash "$SOURCE_SCRIPT" "decrypt" "$workdir" "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$status" -eq 0 ]]
  
  # Check that the original decrypted files now exist
  [ -f "$file_a" ]
  [ -f "$file_b" ]
  
  # Check that the encrypted files are removed
  ! [ -f "$encrypted_a" ]
  ! [ -f "$encrypted_b" ]
  
  # Verify that the content is correctly decrypted
  grep -q "This is File A's content." "$file_a"
  grep -q "Content for File B." "$file_b"
}

@test "decrypt mode skips non-gpg files" {
  local file_a="$workdir/file_a.txt"
  local file_c="$workdir/file_c.log"
  local encrypted_a="${file_a}.gpg"

  # Encrypt file_a and leave a non-encrypted file_c
  echo "Some log content" > "$file_c"
  local HASHED_PASSPHRASE=$(echo -n "$TEST_PASSPHRASE" | sha256sum | cut -d' ' -f1)
  gpg --batch --yes --passphrase "$HASHED_PASSPHRASE" -c --cipher-algo AES256 -o "$encrypted_a" "$file_a"
  rm -f "$file_a"
  
  # Decrypt
  run bash "$SOURCE_SCRIPT" "decrypt" "$workdir" "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$status" -eq 0 ]]
  
  # Check that file_c.log was *not* removed (it was skipped)
  [ -f "$file_c" ]
  grep -q "Skipping non-encrypted file: $file_c" <<< "$output"
}

@test "encryption fails with incorrect passphrase on decryption attempt" {
  local file_a="$workdir/file_a.txt"
  local encrypted_a="${file_a}.gpg"
  local INCORRECT_PASSPHRASE="WrongPassword"
  
  # Encrypt the file correctly
  run bash "$SOURCE_SCRIPT" "encrypt" "$workdir" "$TEST_PASSPHRASE"
  
  # Attempt to decrypt with the wrong passphrase
  {
    run bash "$SOURCE_SCRIPT" "decrypt" "$workdir" "$INCORRECT_PASSPHRASE" 2>&1
  } || true

  # Check that the decryption failed
  [[ "$status" -eq 1 ]]
  
  # Check that the original file was not recreated, and the encrypted file remains
  ! [ -f "$file_a" ]
  [ -f "$encrypted_a" ]
}

@test "invalid mode causes script to exit with error" {
  local INVALID_MODE="zip"
  
  # Execute the script with an invalid mode
  {
    run bash "$SOURCE_SCRIPT" "$INVALID_MODE" "$workdir" "$TEST_PASSPHRASE"
  } || true
  
  # Check that the script exited with status 1
  [[ "$status" -eq 1 ]]
  
  # Check for the expected error message
  [[ "$output" =~ "Invalid mode: $INVALID_MODE. Use 'encrypt' or 'decrypt'." ]]
}
