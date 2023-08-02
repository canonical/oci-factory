#!/bin/bash -eux
#
# Send custom notifications to a Mattermost channel.
#

set -o pipefail

# If not given as an env, script will fail
MM_CHANNEL_ID=${MM_CHANNEL_ID:-}
MM_BOT_TOKEN=${MM_BOT_TOKEN:-}
MM_SERVER=${MM_SERVER:-}

if [ -z "$MM_CHANNEL_ID" ] || [ -z "$MM_BOT_TOKEN" ] || [ -z "$MM_SERVER" ]
then
    echo "ERROR: \$MM_CHANNEL_ID, \$MM_BOT_TOKEN and \$MM_SERVER must be provided"
    exit 1
fi

# The message payload
PAYLOAD_FILE="${PWD}/payload.json"

# What's the status of the job/pipeline that triggered this script?
FINAL_STATUS=${FINAL_STATUS:-"unkown"}

# Set "grey" for unknown states, "red" and "green" for error and success, respectively
COLOR="#B0B0B0"
if [[ "${FINAL_STATUS}" == "success" ]]
then
    COLOR="#33CC33"
elif [[ "${FINAL_STATUS}" == "fail"* ]]
then
    COLOR="#CC0000"
fi

cat>${PAYLOAD_FILE} <<EOF
{
    "channel_id": "${MM_CHANNEL_ID}",
    "props": {
        "attachments": [
            {
                "fallback": "${SUMMARY}",
                "text": "${SUMMARY}",
                "color": "${COLOR}",
                "title": "${TITLE}", 
                "title_link": "${URL}",
                "footer": "${FOOTER}"
            }
        ]
    }
}
EOF

echo "Posting message to Mattermost's channel ${MM_CHANNEL_ID}"

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
