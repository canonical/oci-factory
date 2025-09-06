#!/usr/bin/env bash

# if number of args is not 2, exit with error
if [[ "$#" -ne 2 ]]; then
    echo "Usage: $0 <image-name> <directory>"
    exit 1
fi

image_name="$1"
directory="$2"

if [[ "$RUNNER_DEBUG" == "1" ]]; then
    set -x
fi

if [[ "$image_name" = "*" ]]; then
    echo "Copying all _releases.json files"
    cd "$directory" || exit 1
    find . -name "_releases.json" -exec cp --parents {} "$OLDPWD" \;
    cd "$OLDPWD" || exit 1
elif [[ -f "$directory/oci/$image_name/_releases.json" ]]; then
    cp "$directory/oci/$image_name/_releases.json" "oci/$image_name/_releases.json"
fi
