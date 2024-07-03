import json
import logging
import os
import requests
import time
from typing import Optional


COLORS = {
    "success": "#33CC33",
    "failure": "#CC0000",
    "unknown": "#B0B0B0",
}

channel_id = os.environ.get(
    "MATTERMOST_CHANNEL_ID", "yax1c3pmm7natd5ebw3cngyrpw"
)  # `ROCKS Bot Test` by default
mattermost_server = "https://chat.canonical.com"
posts_url = f"{mattermost_server}/api/v4/posts"
headers = {
    "Authorization": f"Bearer {os.environ['MATTERMOST_TOKEN']}",
    "Content-Type": "application/json",
}

logging.basicConfig(level=os.environ.get("TWC_LOG_LEVEL", "info").upper())


def send_message(title: str, message: str) -> str:
    payload = {
        "channel_id": channel_id,
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

    token = os.environ.get("MATTERMOST_TOKEN", None)
    if token is None:
        logging.warning("Unable to notify on Mattermost, MATTERMOST_TOKEN is not set!")

    data = json.dumps(payload).encode("utf-8")
    res = requests.post(posts_url, headers=headers, data=data, timeout=10)
    res.raise_for_status()
    return res.json()["id"]


# Update the message conditionally based on the success of the operation
def update_status_and_message(
    message_id: str, success: bool, message: Optional[str] = None
) -> None:
    post_res = requests.get(
        f"{posts_url}/{message_id}",
        headers={
            "Authorization": f"Bearer {os.environ['MATTERMOST_TOKEN']}",
            "Content-Type": "application/json",
        },
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

    token = os.environ.get("MATTERMOST_TOKEN", None)
    if token is None:
        logging.warning("Unable to notify on Mattermost, MATTERMOST_TOKEN is not set!")

    data = json.dumps(payload).encode("utf-8")
    res = requests.put(
        f"{posts_url}/{message_id}/patch", headers=headers, data=data, timeout=10
    )
    res.raise_for_status()


if __name__ == "__main__":
    message = "**Release**: 100.04\n**Status**: Triggered"
    title = "[OCI Factory Temporal Worker] Image Rebuild on New Ubuntu Release"
    id = send_message(title, message)
    time.sleep(5)
    update_status_and_message(
        id, 0, message="**Release**: 100.04\n**Status**: Failed"
    )
    time.sleep(5)
    update_status_and_message(
        id, 1, message="**Release**: 100.04\n**Status**: Success"
    )
