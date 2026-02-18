#!/bin/bash -e
#
# A script to encrypt or decrypt files using GPG with a passphrase.
#
# PREREQUISITES:
# - GPG must be installed on the system.
# - The passphrase should be securely stored (e.g., in GitHub Secrets).
#
# USAGE:
#   ./crypt-artifact.sh <encrypt|decrypt> [options]
#
# OPTIONS:
#   --input-path, -i          Path to the file to encrypt/decrypt. If a pattern is provided, it must match exactly one file.
#   --passphrase, -p          Passphrase for encryption/decryption.
#   --output-path, -o         (Optional) Path to save the encrypted/decrypted file. Defaults to the same directory as the input file.
#   --preserve-original, -s   (Optional) If set, the original file will not be deleted after encryption/decryption.
#
# EXAMPLE:
#   Encrypt a file:
#     ./crypt-artifact.sh encrypt -i /path/to/file.txt -p "mysecretpassphrase"
#   Decrypt a file:
#     ./crypt-artifact.sh decrypt -i /path/to/file.txt.gpg -p "mysecretpassphrase"
#

source $(dirname $0)/../../../src/shared/logs.sh

help() {
    echo "Usage: $0 <encrypt|decrypt> --input-path <path> --passphrase <passphrase> [--output-path <path>]"
    echo ""
    echo "Options:"
    echo "  --input-path, -i          Path to the file to encrypt/decrypt. If a pattern is provided, it must match exactly one file."
    echo "  --passphrase, -p          Passphrase for encryption/decryption."
    echo "  --output-path, -o         (Optional) Path to save the encrypted/decrypted file. Defaults to the same directory as the input file."
    echo "  --preserve-original, -s   (Optional) If set, the original file will not be deleted after encryption/decryption."
    exit 1
}

#
# Parse the command-line arguments and set the appropriate variables for encryption/decryption
#
parse_args() {
    mode="$1"
    shift

    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --input-path|-i) input_path="$2"; shift ;;
            --passphrase|-p) passphrase="$2"; shift ;;
            --output-path|-o) output_path="$2"; shift ;;
            --preserve-original|-s) preserve_original=true; shift ;;    
            *) log_error "Unknown parameter passed: $1"; help ;;
        esac
        shift
    done

    if [ -z "$input_path" ] || [ -z "$passphrase" ]; then
        log_error "Input path and passphrase are required."
        help
    fi
}

#
# Validate the input arguments and check for potential issues before proceeding with encryption/decryption
#
validate_args() {
    if [ "$mode" != "encrypt" ] && [ "$mode" != "decrypt" ]; then
        log_error "Invalid mode: $mode. Use 'encrypt' or 'decrypt'."
        exit 1
    fi

    files=$(ls -la $input_path 2>/dev/null)
    if [[ $(wc -l <<< "$files") -gt 1 ]]; then
        log_error "There are multiple files matching the input path: $input_path. Please specify a single file."
        exit 1
    fi

    input_file=$(ls -la $input_path 2>/dev/null | awk '{print $NF}')
    if [ ! -f "$input_file" ]; then
        log_error "Input path does not exist: $input_path"
        exit 1
    fi

    if [ "$mode" = "decrypt" ] && ! file "$input_file" | grep -q "PGP symmetric key encrypted data"; then
        log_error "Input file is not a valid GPG encrypted file: $input_file"
        exit 1
    fi
}

#
# Encrypt the file and check for encryption errors
#
encrypt_file() {
    local output_file="${output_path:-${input_file}.gpg}"

    gpg --batch --yes --passphrase "$passphrase" -c --cipher-algo AES256 -o "$output_file" "$input_file"
    log_info "Encrypted file: $input_file into $output_file"
    [ -z "$preserve_original" ] && rm -f "$input_file"
}

#
# Decrypt the file and check for decryption errors
#
decrypt_file() {
    local output_file="${output_path:-${input_file%.gpg}}"

    output=$(gpg --batch --yes --passphrase "$passphrase" -o "$output_file" -d "$input_file" 2>&1)
    
    if echo "$output" | grep -q "gpg: decryption failed:"; then
        log_error "Decryption failed for file: $input_file. Bad passphrase."
        exit 1
    else
        log_info "Decrypted file: $input_file into $output_file"
        [ -z "$preserve_original" ] && rm -f "$input_file"
    fi
}

#
# Main program execution
#
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_args "$@"
    validate_args

    if [ "$mode" = "encrypt" ]; then
        encrypt_file
    else
        decrypt_file
    fi
fi
