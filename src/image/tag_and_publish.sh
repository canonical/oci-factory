#!/bin/bash -ex

source "$(dirname "$0")/../shared/logs.sh"

# SUITE="{{ suite }}"
# RELEASE="{{ release }}"

# GIT_URL='git+ssh://{{ configuration["launchpad"]["username"] }}@{{ configuration["oci"]["git_repo"] }}'

# DOCS_GIT_URL='git+ssh://{{ configuration["launchpad"]["username"] }}@{{ configuration["oci"]["docs_repo"] }}'

trace_suspend() {
    case "$-" in *x*)
        set +x
        __resume_trace=1
        ;;
    esac 2>/dev/null
}

source_img="${1}"
image_name="${2}"
shift 2
# The tag names are handled by the CI
tag_names=("$@")

publish_with_auth_token()
{
    local token=$1 name=$2
    shift 2
    log_info "Publishing to Docker registry repository $name ..."
    REGISTRY_AUTH=$token "$(dirname "$0")/../uploads/oci_registry_upload.py" \
        "${source_img}" "$name" "$@"
    log_info "Publishing to Docker registry repository $name finished"
}

publish_with_username_password()
{
    local username=$1 password=$2
    shift 2
    local token
    token=$(echo -n "$username:$password" | base64 -w0)
    publish_with_auth_token "$token" "$@"
}

publish_to_aws_ecr_public()
{
    local key_id=$1 key=$2 name="public.ecr.aws/$3"
    shift 3

    log_info "Getting credentials for AWS Public ECR repository $name"
    local token
    token=$(
        AWS_ACCESS_KEY_ID=$key_id AWS_SECRET_ACCESS_KEY=$key \
        aws ecr-public get-authorization-token \
            --region us-east-1 \
            --output=text \
            --query 'authorizationData.authorizationToken'
    )

    publish_with_auth_token "$token" "$name" "$@"
}


# # get the documentation templates
# docs_dir_git=templates
# rm -rf $docs_dir_git
# git clone --depth 1 -b main "$DOCS_GIT_URL" $docs_dir_git
# # get the RenderDown tool used to generate the docs
# git clone --depth 1 -b master https://github.com/valentinviennot/RenderDown

# # use a venv for installing awscli (the .deb and .snap are both outdated and do not contain the ecr-public subcommand)
# create_python3_virtualenv venv
# activate_virtualenv venv
# pip install -U -r $docs_dir_git/requirements.txt -r RenderDown/requirements.txt

# get the OCI image from swift (previously built
# and committed by the "OCI-Build" job)
# oci_archive_name=oci-${SUITE}-${RELEASE}.tar.gz
# download_from_swift $SUITE $SERIAL oci image/oci/$oci_archive_name $oci_archive_name
# mkdir -p ubuntu-base

# mv ubuntu-base/oci/* ${oci_images}/

# infer the available architectures
# AVAILABLE_ARCHS="$(infer_archs_from_oci_image ${oci_images})"

# init_vars

# We pass lots of credentials around and some of them can't be redacted by

# From env
ghcr_repo_name="${GHCR_REPO}/${image_name}"
docker_hub_repo_name="${DOCKER_HUB_NAMESPACE}/${image_name}"
acr_repo_name="${ACR_NAMESPACE}/${image_name}"
ecr_repo_name="${ECR_NAMESPACE}/${image_name}"
# ecr_lts_repo_name="${ECR_LTS_NAMESPACE}/${image_name}"

log_info "Publishing ${image_name} to registries with tags: ${tag_names[*]}"

trace_suspend
if [ ! -z $GHCR_REPO ]; then
    # When this env variable is set we only upload to GHCR and stop
    ## DOCKER HUB
    publish_with_username_password \
        "$GHCR_USERNAME" \
        "$GHCR_PASSWORD" \
        ${ghcr_repo_name} \
        "${tag_names[@]}"
    
    exit 0
fi

docker login -u $DOCKER_HUB_CREDS_USR -p $DOCKER_HUB_CREDS_PSW
## DOCKER HUB
publish_with_username_password \
    "$DOCKER_HUB_CREDS_USR" \
    "$DOCKER_HUB_CREDS_PSW" \
    ${docker_hub_repo_name} \
    "${tag_names[@]}"

# # publish the docs for Docker Hub
# # 1) generate the ubuntu.yaml data file
# $docs_dir_git/generate_ubuntu_yaml.py --provider docker \
#     --username "$DOCKER_USERNAME" \
#     --password "$DOCKER_PASSWORD" \
#     --repository-basename "ubuntu" \
#     --data-dir $docs_dir_git/ubuntu_dh \
#     --unpublished-suite $SUITE \
#     --unpublished-tags "$(echo ${UBUNTU_TAGS[@]})" \
#     --unpublished-archs "${AVAILABLE_ARCHS}"
# # 2) build the docs
# (cd ${docs_dir_git} && make DATADIR=ubuntu_dh dockerhub-docs)

# dh_jw_token=$(curl -X POST  https://hub.docker.com/v2/users/login \
#                 -H "Content-Type: application/json" \
#                 -d '{"username":"'$DOCKER_USERNAME'","password":"'$DOCKER_PASSWORD'"}' | jq -r .token)
# # 3) build and ship the doc payload
# cat >dockerhub-docs.json <<EOF
# {
# "full_description": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/docker.io/ubuntu/ubuntu.md | sed 's/"/\\"/g')"
# }
# EOF
# ## we could also add "description" to the payload, for the image's
# ## short summary, but that's unlikely to ever change, so no need to 
# ## keep overwriting it on every build.
# curl -X PATCH https://hub.docker.com/v2/repositories/ubuntu/ubuntu \
#     -H "Authorization: JWT $dh_jw_token" \
#     -H "Content-Type: application/json" \
#     -d @dockerhub-docs.json

### ECR
publish_to_aws_ecr_public \
    "$ECR_CREDS_USR" \
    "$ECR_CREDS_PSW" \
    ${ecr_repo_name} \
    "${tag_names[@]}"

# # publish the docs for ECR
# # 1) generate the ubuntu.yaml data file
# $docs_dir_git/generate_ubuntu_yaml.py --provider aws \
#     --username "$AWS_UBUNTU_KEY_ID" \
#     --password "$AWS_UBUNTU_SECRET" \
#     --repository-basename "ubuntu" \
#     --data-dir $docs_dir_git/ubuntu_ecr \
#     --unpublished-suite $SUITE \
#     --unpublished-tags "$(echo ${UBUNTU_TAGS[@]})" \
#     --unpublished-archs "${AVAILABLE_ARCHS}"
# # 2) build the docs
# (cd ${docs_dir_git} && make DATADIR=ubuntu_ecr ecr-docs)
# # 3) build and ship the doc payload
# # ECR accepts architecture data, but it needs to abide by their naming conventions:
# # https://docs.aws.amazon.com/cli/latest/reference/ecr-public/put-repository-catalog-data.html#options
# ecr_archs="${AVAILABLE_ARCHS} $(echo ${AVAILABLE_ARCHS} | sed 's/armhf/arm/g' | tr '[:lower:]' '[:upper:]' | sed 's/AMD64/x86-64/g')"
# if [[ "${ecr_archs}" == *"ARM64"* ]]
# then
#     ecr_archs_mapped="$(echo $ecr_archs | jq -R 'split(" ")' | jq '. |= . + ["ARM 64"]')"
# else
#     ecr_archs_mapped="$(echo $ecr_archs | jq -R 'split(" ")')"
# fi
# cat >ecr-docs.json <<EOF
# {
# "architectures": ["Linux"],
# "operatingSystems": ${ecr_archs_mapped},
# "usageText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/ubuntu/usage/ubuntu.md | sed 's/"/\\"/g')",
# "aboutText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/ubuntu/ubuntu.md | sed 's/"/\\"/g')"
# }
# EOF
# AWS_SECRET_ACCESS_KEY=$AWS_UBUNTU_SECRET AWS_ACCESS_KEY_ID=$AWS_UBUNTU_KEY_ID \
#     aws --region us-east-1 ecr-public put-repository-catalog-data \
#         --registry-id="099720109477" --repository-name ubuntu --catalog-data "$(cat ecr-docs.json)"

### ACR
# publish_with_username_password \
#     "$ACR_CREDS_USR" \
#     "$ACR_CREDS_PSW" \
#     ${acr_repo_name} \
#     "${tag_names[@]}"

# ### OCIR
# publish_with_username_password \
#     "$OCIR_USERNAME" \
#     "$OCIR_PASSWORD" \
#     phx.ocir.io/intcanonical/ubuntu \
#     "${UBUNTU_TAGS[@]}"

# ### ECR LTS
# if (( SUITE_IS_LTS )); then
#     echo "Publishing to LTS registries with tags: ${LTS_TAGS[@]}"

#     publish_to_aws_ecr_public \
#         "$AWS_LTS_KEY_ID" \
#         "$AWS_LTS_SECRET" \
#         lts/ubuntu \
#         "${LTS_TAGS[@]}"

#     # publish the docs for ECR LTS
#     # 1) generate the ubuntu.yaml data file
#     $docs_dir_git/generate_ubuntu_yaml.py --provider aws \
#         --username "$AWS_LTS_KEY_ID" \
#         --password "$AWS_LTS_SECRET" \
#         --repository-basename "lts" \
#         --data-dir $docs_dir_git/ubuntu_ecr_lts \
#         --unpublished-suite $SUITE \
#         --unpublished-tags "$(echo ${UBUNTU_TAGS[@]})" \
#         --unpublished-archs "${AVAILABLE_ARCHS}"
#     # 2) build the docs
#     (cd ${docs_dir_git} && make DATADIR=ubuntu_ecr_lts ecr-lts-docs)
#     # 3) build and ship the doc payload
#     # ECR archs are already mapped from the ECR push above
#     cat >ecr-lts-docs.json <<EOF
# {
# "architectures": ["Linux"],
# "operatingSystems": ${ecr_archs_mapped},
# "usageText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/lts/usage/ubuntu.md | sed 's/"/\\"/g')",
# "aboutText": "$(awk '{printf "%s\\n", $0}' ${docs_dir_git}/docs/public.ecr.aws/lts/ubuntu.md | sed 's/"/\\"/g')"
# }
# EOF
#     AWS_SECRET_ACCESS_KEY=$AWS_LTS_SECRET AWS_ACCESS_KEY_ID=$AWS_LTS_KEY_ID \
#         aws --region us-east-1 ecr-public put-repository-catalog-data \
#             --registry-id="271607439846" --repository-name ubuntu --catalog-data "$(cat ecr-lts-docs.json)"
# fi

# trace_resume

# # We need to stored this artifacts to get the digest for the OCI-Attach-artefacts jobs
# # in order to attach sbom to the oci images.

# skopeo inspect --raw oci:${oci_images} > manifest_list.json
# # NOTE: due to "venv/bin/activate: line 11: _OLD_VIRTUAL_PYTHONHOME: unbound variable"
# set +u
# deactivate
# set -u

# clear_proxies
