import json
import os
import sys
import tempfile

import requests

from ..shared.logs import get_logger

COLOR_MAP = {
    "unknown": "#B0B0B0",
    "success": "#33CC33",
    "failure": "#CC0000",
}

logger = get_logger()


def main():
    env_vars = {
        "MM_CHANNEL_ID": None,
        "MM_BOT_TOKEN": None,
        "MM_SERVER": None,
        "SUMMARY": None,
        "TITLE": None,
        "URL": None,
        "FOOTER": None,
        "FINAL_STATUS": "unknown",
    }

    for var, default in env_vars.items():
        v = os.environ.get(var, default)
        if var.startswith("MM_") and not v:
            logger.error(f"Missing required environment variable: {var}")
            sys.exit(1)
        env_vars[var] = v

    color = COLOR_MAP.get(env_vars["FINAL_STATUS"].lower(), COLOR_MAP["unknown"])

    payload = {
        "channel_id": env_vars["MM_CHANNEL_ID"],
        "props": {
            "attachments": [
                {
                    "fallback": env_vars["SUMMARY"],
                    "text": env_vars["SUMMARY"],
                    "color": color,
                    "title": env_vars["TITLE"],
                    "title_link": env_vars["URL"],
                    "footer": env_vars["FOOTER"],
                }
            ]
        },
    }

    logger.debug(
        f"Message to be sent to Mattermost: {json.dumps(payload['props'], indent=2)}"
    )

    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        json.dump(payload, f)
        f.flush()
        payload_file = f.name

    logger.info(f"Posting message to Mattermost's channel {env_vars["MM_CHANNEL_ID"]}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {env_vars["MM_BOT_TOKEN"]}",
    }
    url = f"{env_vars["MM_SERVER"]}/api/v4/posts"

    with open(payload_file, "r") as f:
        response = requests.post(url, headers=headers, data=f.read())

    if not response.ok:
        logger.error("unable to post message into Mattermost channel")
        logger.error(response.text, file=sys.stderr)
        sys.exit(22)


if __name__ == "__main__":
    main()
