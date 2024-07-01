import json
import os
import requests

channel_id = "yax1c3pmm7natd5ebw3cngyrpw"
mattermost_server = "https://chat.canonical.com"
posts_url = f"{mattermost_server}/api/v4/posts"


def send_message(message: str):
    payload = {
        "channel_id": channel_id,
        "message": message,
    }

    headers = {
        "Authorization": f"Bearer {os.environ['MATTERMOST_TOKEN']}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")
    res = requests.post(posts_url, headers=headers, data=data, timeout=10)
    res.raise_for_status()
