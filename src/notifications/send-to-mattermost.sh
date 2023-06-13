#!/bin/bash -eux
#
# Send custom notifications to a Mattermost channel.
#

set -o pipefail

# If not given as an env, script will fail
MM_CHANNEL_ID=${MM_CHANNEL_ID:-}
MM_AUTHOR=${MM_AUTHOR:-"bot"}
MM_BOT_TOKEN=${MM_BOT_TOKEN:-}
MM_SERVER=${MM_SERVER:-}

if [ -z "$MM_CHANNEL_ID" ] || [ -z "$MM_BOT_TOKEN" ] || [ -z "$MM_SERVER" ]
then
    echo "ERROR: \$MM_CHANNEL_ID, \$MM_BOT_TOKEN and \$MM_SERVER must be provided"
    exit 1
fi

# The message payload
PAYLOAD_FILE="${PWD}/payload.json"

# # What's the status of the job/pipeline that triggered this script?
FINAL_STATUS=${FINAL_STATUS:-"unkown"}

# Set "grey" for unknown states, "red" and "green" for error and success, respectively
COLOR="#B0B0B0"
MM_AUTHOR_ICON="${MM_SERVER}/api/v4/emoji/dspgf84kwidqzg1ujahyx1yqeh/image"
TITLE="Inconclusive ending for job ${WORKFLOW_NAME}"
if [[ "${FINAL_STATUS}" == "success" ]]
then
    COLOR="#33CC33"
    MM_AUTHOR_ICON="${MM_SERVER}/api/v4/emoji/uz544kdh43nstyy5rnw1oc9sio/image"
    TITLE="Successfully finished job ${WORKFLOW_NAME}"
elif [[ "${FINAL_STATUS}" == "fail"* ]]
then
    COLOR="#CC0000"
    MM_AUTHOR_ICON="${MM_SERVER}/api/v4/emoji/qy1jz413bf8zbyterhxe719xyh/image"
    TITLE="Job ${WORKFLOW_NAME} ended in ERROR"
fi


TEXT="[$(date)] This is [${WORKFLOW_NAME}](${URL})'s \
build number [#${RUN_ID}](${URL}). ${SUMMARY}.\
See the [logs](${URL})"

cat>${PAYLOAD_FILE} <<EOF
{
    "channel_id": "${MM_CHANNEL_ID}",
    "props": {
        "attachments": [
            {
                "fallback": "MM notification for job ${WORKFLOW_NAME}",
                "text": "${TEXT}",
                "color": "${COLOR}",
                "author_name": "${MM_AUTHOR}",
                "author_icon": "${MM_AUTHOR_ICON}",
                "title": "${TITLE}", 
                "title_link": "${URL}",
                "fields": [
                    {
                        "short": true,
                        "title": "Image",
                        "value": "${IMAGE_NAME}"
                    }
                ],
                "footer": "Started by ${TRIGGERED_BY} on $(date)"
            }
        ]
    },
    "message": "###### ${WORKFLOW_NAME} has finished with \`${FINAL_STATUS}\`"
}
EOF

echo "Posting message to Mattermost channel ${MM_CHANNEL_ID}"

curl_out=$(mktemp)
HTTP_CODE=$(curl -i -o ${curl_out} --write-out "%{http_code}" \
    -X POST -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $MM_BOT_TOKEN" \
    "${MM_SERVER}/api/v4/posts" \
    -d @${PAYLOAD_FILE})

if [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]] ; then
    echo "ERROR: unable to post message into Mattermost channel"
    cat $curl_out
    exit 22
fi
