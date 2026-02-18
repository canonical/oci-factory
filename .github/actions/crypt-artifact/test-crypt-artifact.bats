#!/usr/bin/env bats

SOURCE_SCRIPT="${BATS_TEST_DIRNAME}/crypt-artifact.sh"

# Setup the test environment
setup() {
  export workdir=$(mktemp -d)
  
  echo "This is Test file's content." > "$workdir/test_file.txt"
  
  export TEST_PASSPHRASE="SuperSecretPass123"
}

# Teardown the test environment
teardown() {
  rm -rf "$workdir"
}

## ---------------------------------------------
## Test Suite for crypt-artifact.sh
## ---------------------------------------------

@test "encrypt mode works for a single file (without output path)" {
  local input_path="$workdir/test_file.txt"
  
  # Encrypt the file without passing the output path
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$input_path" -p "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$?" -eq 0 ]]

  # Check that the original file is removed
  ! [ -f "$input_path" ]
   
  # Check that the encrypted file exists with .gpg extension
  [ -f "${input_path}.gpg" ]
 
  # Verify that the file content is actually encrypted (i.e., not readable plain text)
  file "${input_path}.gpg" | grep -q "PGP symmetric key encrypted data"
  ! grep -q "This is Test file's content." "${input_path}.gpg"
}

@test "encrypt mode works for a single file (with output path)" {
  local input_path="$workdir/test_file.txt"
  local output_path="$my_encrypted_file.gpg"
  
  # Encrypt the file passing the output path
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$input_path" -p "$TEST_PASSPHRASE" -o "$output_path"
  
  # Check script exit status
  [[ "$?" -eq 0 ]]

  # Check that the original files are removed
  ! [ -f "$input_path" ]
   
  # Check that the encrypted files exist
  [ -f "$output_path" ]
  
  # Verify that the file content is actually encrypted (i.e., not readable plain text)
  file "$output_path" | grep -q "PGP symmetric key encrypted data"
  ! grep -q "This is Test file's content." "$output_path"
}

@test "encrypt mode works for a single file (using pattern)" {
  local input_path="$workdir/test_file.txt"
  
  # Encrypt the file using a pattern that matches the file
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$workdir/test_file*.txt" -p "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$?" -eq 0 ]]

  # Check that the original file is removed
  ! [ -f "$input_path" ]
   
  # Check that the encrypted file exists with .gpg extension
  [ -f "${input_path}.gpg" ]
 
  # Verify that the file content is actually encrypted (i.e., not readable plain text)
  file "${input_path}.gpg" | grep -q "PGP symmetric key encrypted data"
  ! grep -q "This is Test file's content." "${input_path}.gpg"
}

@test "encrypt mode works for a single file (preserve-original)" {
  local input_path="$workdir/test_file.txt"
  local output_path="$my_encrypted_file.gpg"
  
  # Encrypt the file with preserve-original flag
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$input_path" -p "$TEST_PASSPHRASE" -o "$output_path" --preserve-original
  
  # Check script exit status
  [[ "$?" -eq 0 ]]

  # Check that the original file still exists
  [ -f "$input_path" ]
   
  # Check that the encrypted file exists with .gpg extension
  [ -f "$output_path" ]
  
  # Verify that the file content is actually encrypted (i.e., not readable plain text)
  file "$output_path" | grep -q "PGP symmetric key encrypted data"
  ! grep -q "This is Test file's content." "$output_path"
}

@test "decrypt mode works for a single file (without output path)" {
  local test_file="$workdir/test_file.txt"
  local expected_output="${test_file}.gpg"

  # Encrypt the file first
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$test_file" -p "$TEST_PASSPHRASE"
  
  # Decrypt the files
  run bash "$SOURCE_SCRIPT" "decrypt" -i "$expected_output" -p "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$status" -eq 0 ]]
  
  # Check that the original decrypted files now exist
  [ -f "$test_file" ]
  
  # Check that the encrypted files are removed
  ! [ -f "$expected_output" ]
  
  # Verify that the content is correctly decrypted
  grep -q "This is Test file's content." "$test_file"
}

@test "decrypt mode works for a single file (with output path)" {
  local test_file="$workdir/test_file.txt"
  local encrypted_file="${test_file}.gpg"
  local decrypted_output="$workdir/my_decrypted_file.txt"

  # Encrypt the file first
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$test_file" -p "$TEST_PASSPHRASE" -o "$encrypted_file"
  
  # Decrypt the file with output path
  run bash "$SOURCE_SCRIPT" "decrypt" -i "$encrypted_file" -p "$TEST_PASSPHRASE" -o "$decrypted_output"
  
  # Check script exit status
  [[ "$status" -eq 0 ]]
  
  # Check that the decrypted file exists
  [ -f "$decrypted_output" ]
  
  # Check that the encrypted file is removed
  ! [ -f "$encrypted_file" ]
  
  # Verify that the content is correctly decrypted
  grep -q "This is Test file's content." "$decrypted_output"
}

@test "decrypt mode works for a single file (using pattern)" {
  local test_file="$workdir/test_file.txt"
  local encrypted_file="${test_file}.gpg"

  # Encrypt the file first
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$test_file" -p "$TEST_PASSPHRASE" -o "$encrypted_file"
  
  # Decrypt the file using a pattern that matches the file
  run bash "$SOURCE_SCRIPT" "decrypt" -i "$workdir/test_file*.gpg" -p "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$status" -eq 0 ]]
  
  # Check that the original decrypted files now exist
  [ -f "$test_file" ]
  
  # Check that the encrypted files are removed
  ! [ -f "$encrypted_file" ]
  
  # Verify that the content is correctly decrypted
  grep -q "This is Test file's content." "$test_file"
}

@test "decrypt mode works for a single file (preserve-original)" {
  local test_file="$workdir/test_file.txt"
  local encrypted_file="${test_file}.gpg"
  local decrypted_output="$workdir/my_decrypted_file.txt"

  # Encrypt the file first
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$test_file" -p "$TEST_PASSPHRASE" -o "$encrypted_file"
  
  # Decrypt the file with preserve-original flag
  run bash "$SOURCE_SCRIPT" "decrypt" -i "$encrypted_file" -p "$TEST_PASSPHRASE" -o "$decrypted_output" --preserve-original
 
  # Check script exit status
  [[ "$?" -eq 0 ]]
  
  # Check that the decrypted file exists
  [ -f "$decrypted_output" ]
  
  # Check that the encrypted file still exists
  [ -f "$encrypted_file" ]
  
  # Verify that the content is correctly decrypted
  grep -q "This is Test file's content." "$decrypted_output"
}

@test "decrypt fails if the input file is not a valid GPG encrypted file" {
  local test_file="$workdir/test_file_1.log"
  echo "This is not an encrypted file." > "$test_file"

  # Attempt to decrypt
  run bash "$SOURCE_SCRIPT" "decrypt" -i "$test_file" -p "$TEST_PASSPHRASE"
  
  # Check script exit status
  [[ "$status" -eq 1 ]]
 
  # Check that test_file_1.log was *not* removed (it was skipped)
  [ -f "$test_file" ]
  grep -q "Input file is not a valid GPG encrypted file: $test_file" <<< "$output"
}

@test "encryption fails with incorrect passphrase on decryption attempt" {
  local test_file="$workdir/test_file.txt"
  local encrypted_file="${test_file}.gpg"
  local INCORRECT_PASSPHRASE="WrongPassword"
  
  # Encrypt the file correctly
  run bash "$SOURCE_SCRIPT" "encrypt" -i "$test_file" -p "$TEST_PASSPHRASE" -o "$encrypted_file"
  
  # Attempt to decrypt with the wrong passphrase
  {
    run bash "$SOURCE_SCRIPT" "decrypt" -i "$encrypted_file" -p "$INCORRECT_PASSPHRASE" 2>&1
  } || true

  # Check that the decryption failed
  [[ "$status" -eq 1 ]]
  
  # Check that the original file was not recreated, and the encrypted file remains
  ! [ -f "$test_file" ]
  [ -f "$encrypted_file" ]
}

@test "invalid mode causes script to exit with error" {
  local INVALID_MODE="zip"
  
  # Execute the script with an invalid mode
  {
    run bash "$SOURCE_SCRIPT" "$INVALID_MODE" -i "$workdir/test_file.txt" -p "$TEST_PASSPHRASE"
  } || true
  
  # Check that the script exited with status 1
  [[ "$status" -eq 1 ]]
  
  # Check for the expected error message
  [[ "$output" =~ "Invalid mode: $INVALID_MODE. Use 'encrypt' or 'decrypt'." ]]
}

@test "missing required arguments causes script to exit with error" {
  # Execute the script without required arguments
  {
    run bash "$SOURCE_SCRIPT" "encrypt" -i "$workdir/test_file.txt"
  } || true
  
  # Check that the script exited with status 1
  [[ "$status" -eq 1 ]]
  
  # Check for the expected error message
  [[ "$output" =~ "Input path and passphrase are required." ]]
}

@test "non-existent input file causes script to exit with error" {
  local NON_EXISTENT_FILE="$workdir/non_existent_file.txt"
  
  # Execute the script with a non-existent input file
  {
    run bash "$SOURCE_SCRIPT" "encrypt" -i "$NON_EXISTENT_FILE" -p "$TEST_PASSPHRASE"
  } || true
 
  # Check that the script exited with status 1
  [[ "$status" -eq 1 ]]
 
  # Check for the expected error message
  [[ "$output" =~ "Input path does not exist: $NON_EXISTENT_FILE" ]]
}

@test "multiple files matching input path causes script to exit with error" {
  local file1="$workdir/test_file1.txt"
  local file2="$workdir/test_file2.txt"
  
  echo "File 1 content." > "$file1"
  echo "File 2 content." > "$file2"
  
  # Execute the script with an input path that matches multiple files
  {
    run bash "$SOURCE_SCRIPT" "encrypt" -i "$workdir/test_file*.txt" -p "$TEST_PASSPHRASE"
  } || true
  
  # Check that the script exited with status 1
  [[ "$status" -eq 1 ]]

  # Check for the expected error message
  [[ "$output" =~ "There are multiple files matching the input path:" ]]
}
