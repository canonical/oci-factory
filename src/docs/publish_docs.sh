#!/bin/bash -ex

trace_suspend() {
    case "$-" in *x*)
        set +x
        __resume_trace=1
        ;;
    esac 2>/dev/null
}

trace_resume() {
    if [ "${__resume_trace:-0}" = 1 ]; then
        unset __resume_trace
        if [[ "$RUNNER_DEBUG" == "1" ]]; then
          set -x
        fi
    fi
}

source $(dirname $0)/../shared/logs.sh

DOCS_GIT_URL='https://git.launchpad.net/~ubuntu-docker-images/ubuntu-docker-images/+git/templates'
image_name="${1}"
image_doc_filename="${2}"
image_doc_folder="${3}"
err=""

AVAILABLE_ARCHS="$(yq -r '.releases[].architectures[]' < "${image_doc_folder}"/"${image_doc_filename}" | sort | uniq | paste -sd ',')"

# get the documentation templates
docs_dir_git=templates
git clone --depth 1 -b main "${DOCS_GIT_URL}" ${docs_dir_git}
# get the RenderDown tool used to generate the docs
git clone --depth 1 -b master https://github.com/valentinviennot/RenderDown
# install the dependencies for the RenderDown tool  
pip install -U -r ${docs_dir_git}/requirements.txt -r RenderDown/requirements.txt

# move the documentation file generated by the oci-factory to the templates/<mktemp folder generated> folder 
folder_of_data=$(cd ${docs_dir_git} && mktemp -d -p "${PWD}")
mv "${image_doc_folder}/${image_doc_filename}" "${folder_of_data}"
# the name of the markdown file generated by RenderDown:
markdown_filename="${image_doc_filename%.*}.md"

### DockerHub

# 1) build the docs
(cd ${docs_dir_git} && make DATADIR="${folder_of_data}" dockerhub-docs)

# 2) login using DockerHub API to get the token to publish the doc
dh_jw_token=$(curl -X POST  https://hub.docker.com/v2/users/login \
                -H "Content-Type: application/json" \
                -d '{"username":"'"${DOCKER_HUB_CREDS_USR_DOC}"'","password":"'"${DOCKER_HUB_CREDS_PSW_DOC}"'"}' | jq -r .token)

# 3) build and ship the doc payload
cat >dockerhub-docs.json <<EOF
{
"full_description": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/docker.io/ubuntu/"${markdown_filename}" | sed 's/"/\\"/g')"
}
EOF

# We need to remove the docker.io/ before the namespace
# because we only need the namespace for the API

DH_NAMESPACE="${DOCKER_HUB_NAMESPACE#docker.io/}"

# we could also add "description" to the payload, for the image's
# short summary, but that's unlikely to ever change, so no need to 
# keep overwriting it on every build.
trace_suspend
curl -X PATCH "https://hub.docker.com/v2/repositories/${DH_NAMESPACE}/${image_name}" \
    -H "Authorization: JWT ${dh_jw_token}" \
    -H "Content-Type: application/json" \
    -d @dockerhub-docs.json --fail-with-body || err="DockerHub"
trace_resume 

### ECR

# 1) build the docs
(cd ${docs_dir_git} && make DATADIR="${folder_of_data}" ecr-docs)

#  2) build and ship the doc payload
#  ECR accepts architecture data, but it needs to abide by their naming conventions:
#  https://docs.aws.amazon.com/cli/latest/reference/ecr-public/put-repository-catalog-data.html#options
if [ -z "$AVAILABLE_ARCHS" ]
then
    operating_systems=""
else
    ecr_archs="${AVAILABLE_ARCHS} $(echo "${AVAILABLE_ARCHS}" | sed 's/armhf/arm/g' | tr '[:lower:]' '[:upper:]' | sed 's/AMD64/x86-64/g')"
    if [[ "${ecr_archs}" == *"ARM64"* ]]
    then
        ecr_archs_mapped="$(echo "$ecr_archs" | jq -R 'split(" ")' | jq '. |= . + ["ARM 64"]')"
    else
        ecr_archs_mapped="$(echo "$ecr_archs" | jq -R 'split(" ")')"
    fi
    operating_systems="\"operatingSystems\": ${ecr_archs_mapped},"
fi

cat >ecr-docs.json <<EOF
{
"architectures": ["Linux"],
${operating_systems}
"usageText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/ubuntu/usage/"${markdown_filename}" | sed 's/"/\\"/g')",
"aboutText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/ubuntu/"${markdown_filename}" | sed 's/"/\\"/g')"
}
EOF

AWS_SECRET_ACCESS_KEY=${ECR_CREDS_PSW} AWS_ACCESS_KEY_ID=${ECR_CREDS_USR} \
aws --region us-east-1 ecr-public put-repository-catalog-data \
    --registry-id="${ECR_REGISTRY_ID}" --repository-name "${image_name}" --catalog-data "$(cat ecr-docs.json)" || err="${err}, ECR"

# Check for error
if [ -n "${err}" ]
then
   log_error "Failed to publish docs for ${image_name} in the following registries: ${err}"
   exit 1
fi
