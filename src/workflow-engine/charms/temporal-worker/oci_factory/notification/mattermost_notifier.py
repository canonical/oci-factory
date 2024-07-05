import json
import logging
import os
import sys
from typing import Optional

import requests

logging.basicConfig(level=os.environ.get("TWC_LOG_LEVEL", "info").upper())

COLORS = {
    "success": "#33CC33",
    "failure": "#CC0000",
    "unknown": "#B0B0B0",
}

REQUIRED_ENVS = ["MATTERMOST_CHANNEL_ID", "MATTERMOST_TOKEN", "MATTERMOST_SERVER"]

missing_envs = [env for env in REQUIRED_ENVS if os.environ.get(env) is None]
if missing_envs:
    logging.error(
        f"Unable to notify on Mattermost, missing environment variables: {missing_envs}"
    )
    sys.exit(1)

MATTERMOST_CHANNEL_ID = os.environ.get("MATTERMOST_CHANNEL_ID")
MATTERMOST_TOKEN = os.environ.get("MATTERMOST_TOKEN")
MATTERMOST_SERVER = os.environ.get("MATTERMOST_SERVER")

POST_URL = f"{MATTERMOST_SERVER}/api/v4/posts"
PATCH_URL = POST_URL + "/{}/patch"

HEADERS = {
    "Authorization": f"Bearer {MATTERMOST_TOKEN}",
    "Content-Type": "application/json",
}


def send_message(title: str, message: str) -> str:
    payload = {
        "channel_id": MATTERMOST_CHANNEL_ID,
        "props": {
            "attachments": [
                {
                    "fallback": message,
                    "title": title,
                    "text": message,
                    "color": COLORS["unknown"],
                }
            ]
        },
    }

    data = json.dumps(payload).encode("utf-8")
    res = requests.post(POST_URL, headers=HEADERS, data=data, timeout=10)
    res.raise_for_status()
    return res.json()["id"]


# Update the message conditionally based on the success of the operation
def update_status_and_message(
    message_id: str, success: bool, message: Optional[str] = None
) -> None:
    post_res = requests.get(
        f"{POST_URL}/{message_id}",
        headers=HEADERS,
        timeout=10,
    )
    post_res.raise_for_status()
    props = post_res.json()["props"]

    props["attachments"][0]["color"] = (
        COLORS["success"] if success else COLORS["failure"]
    )

    if message:
        props["attachments"][0]["text"] = message

    payload = {"id": message_id, "props": props}

    data = json.dumps(payload).encode("utf-8")
    res = requests.put(
        PATCH_URL.format(message_id), headers=HEADERS, data=data, timeout=10
    )
    res.raise_for_status()
