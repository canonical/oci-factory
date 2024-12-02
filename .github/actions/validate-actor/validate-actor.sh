#!/bin/bash -e

actor=$1
admin_only=$2
workspace=$3
image_path=$4

echo "github.actor: ${actor}"
actor=$(echo "$actor" | sed 's/\[/\\[/g;s/\]/\\]/g') # Escape square brackets for actors like renovate[bot]
echo "admin-only: ${admin_only}"
if [[ ${admin_only} == true ]]; then
    exit_status=0
    echo "Expanding team mentions in the CODEOWNERS file"
    cp ${workspace}/CODEOWNERS ${workspace}/CODEOWNERS.chk
    teams=$(grep -oE '@[[:alnum:]_.-]+\/[[:alnum:]_.-]+' ${workspace}/CODEOWNERS.chk || true | sort | uniq)

    for team in ${teams}; do
        org=$(echo ${team} | cut -d'/' -f1 | sed 's/@//')
        team_name=$(echo ${team} | cut -d'/' -f2)
        members=$(gh api "/orgs/${org}/teams/${team_name}/members" | jq -r '.[].login')
        replacement=$(echo "${members}" | xargs -I {} echo -n "@{} " | awk '{$1=$1};1')
        sed -i "s|${team}|${replacement}|g" ${workspace}/CODEOWNERS.chk
    done

    if grep -wq "@${actor}" ${workspace}/CODEOWNERS.chk; then
        echo "The workflow is triggered by ${actor} as the code owner"
    elif cat ${workspace}/${image_path}/contacts.yaml | yq ".maintainers" | grep "\- " | grep -wq "${actor}"; then
        echo "The workflow is triggered by ${actor} as a maintainer of the image ${image_path}"
    else
        echo "The workflow is triggered by a user neither as a code owner nor a maintainer of the image ${image_path}"
        exit_status=1
    fi
    rm ${workspace}/CODEOWNERS.chk
    exit ${exit_status}
else
    echo "The workflow is not restricted to non-code-owner or non-maintainer users"
fi
