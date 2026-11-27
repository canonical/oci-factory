#!/bin/bash -e

# Source Swift config
source $(dirname $0)/../configs/swift.public.novarc

if [[ "$RUNNER_DEBUG" == "1" ]]; then
  set -x
fi

# Only <image>/<track>/<revision>/... objects are revisions. The image prefix
# also holds the upload lockfile while another build is running.
canonical_tags=$(swift list $SWIFT_CONTAINER_NAME -p $IMAGE_NAME/ \
    | awk -F '/' '$3 ~ /^[0-9]+$/ {print $2"_"$3}' | uniq | sort | tr '\n' ',')

echo "canonical-tags=${canonical_tags}" >> "$GITHUB_OUTPUT"

echo "${canonical_tags}" > canonical-tags-file.txt
echo "canonical-tags-file=canonical-tags-file.txt" >> "$GITHUB_OUTPUT"
