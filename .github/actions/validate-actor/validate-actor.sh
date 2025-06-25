#!/bin/bash -e

source $(dirname $0)/../../../src/shared/logs.sh

actor=$1
admin_only=$2
workspace=$3
image_path=$4

log_debug "github.actor: ${actor}"
actor=$(echo "$actor" | sed 's/\[/\\[/g;s/\]/\\]/g') # Escape square brackets for actors like renovate[bot]
log_debug "admin-only: ${admin_only}"
if [[ ${admin_only} == true ]]; then
    exit_status=0
    log_debug "Expanding team mentions in the CODEOWNERS file"
    codeowners_file=$(mktemp)
    cp ${workspace}/CODEOWNERS ${codeowners_file}
    teams=$(grep -oE '@[[:alnum:]_.-]+\/[[:alnum:]_.-]+' ${codeowners_file} || true | sort | uniq)

    for team in ${teams}; do
        org=$(echo ${team} | cut -d'/' -f1 | sed 's/@//')
        team_name=$(echo ${team} | cut -d'/' -f2)
        members=$(gh api "/orgs/${org}/teams/${team_name}/members" | jq -r '.[].login')
        replacement=$(echo "${members}" | xargs -I {} echo -n "@{} " | awk '{$1=$1};1')
        sed -i "s|${team}|${replacement}|g" ${codeowners_file}
    done

    if grep -wq "@${actor}" ${codeowners_file}; then
        log_info "The workflow is triggered by ${actor} as the code owner"
    elif cat ${workspace}/${image_path}/contacts.yaml | yq ".maintainers" | grep "\- " | grep -wq "${actor}"; then
        log_info "The workflow is triggered by ${actor} as a maintainer of the image ${image_path}"
    else
        log_info "The workflow is triggered by a user neither as a code owner nor a maintainer of the image ${image_path}"
        exit_status=1
    fi
    exit ${exit_status}
else
    log_info "The workflow is not restricted to non-code-owner or non-maintainer users"
fi
