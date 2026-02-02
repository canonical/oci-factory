#!/bin/bash -e

source $(dirname $0)/../../../src/shared/logs.sh

# Verify arguments
if [ "$#" -ne 3 ]; then
    log_error "Usage: $0 <encrypt|decrypt> <input_path> <passphrase>"
    exit 1
fi

mode=$1
input_path=$2
passphrase=$3


HASHED_PASSPHRASE=$(echo -n "$passphrase" | sha256sum | cut -d' ' -f1)
echo "::add-mask::$HASHED_PASSPHRASE"

for FILE in $input_path/* $input_path; do
    [ -f "$FILE" ] || continue  # skip if not a regular file

    if [ $mode = "encrypt" ]; then
        gpg --batch --yes --passphrase "$HASHED_PASSPHRASE" -c --cipher-algo AES256 -o "${FILE}.gpg" "$FILE"
        log_info "Encrypted file: ${FILE} into ${FILE}.gpg"
        rm -f "$FILE"
    elif [ $mode = "decrypt" ]; then
        if [[ "$FILE" != *.gpg ]]; then
            log_info "Skipping non-encrypted file: $FILE"
            continue
        fi

        output=$(gpg --batch --yes --passphrase "$HASHED_PASSPHRASE" -o "${FILE%.gpg}" -d "$FILE" 2>&1)
        
        # Check for the specific GnuPG failure message for a wrong passphrase
        if echo "$output" | grep -q "gpg: decryption failed:"; then
            log_error "Decryption failed for file: $FILE. Bad passphrase."
            exit 1
        else
            log_info "Decrypted file: $FILE"
            rm -f "$FILE"
        fi
    else
        log_error "Invalid mode: $mode. Use 'encrypt' or 'decrypt'."
        exit 1
    fi
done
