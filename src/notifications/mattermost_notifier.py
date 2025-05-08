import argparse
import json
import os
import sys
import tempfile

import requests

from ..shared.github_output import GithubOutput
from ..shared.logs import get_logger


COLOR_MAP = {
    "unknown": "#B0B0B0",
    "success": "#33CC33",
    "failure": "#CC0000",
}

logger = get_logger()

def summarize(jobs_file: str) -> None:
    """Summarize the jobs results and return a summary string."""
    with open(jobs_file, encoding="UTF-8") as jf:
        previous_jobs = json.load(jf)

    summary = []
    for job, details in previous_jobs.items():
        if "fail" in details["result"]:
            icon = ":gh-failure-octicon-xcirclefillicon:"
        elif "skip" in details["result"]:
            icon = ":gh-skip-octicon-skipicon:"
        elif "cancel" in details["result"]:
            icon = ":gh-cancelled-octicon-stopicon:"
        elif "succe" in details["result"]:
            icon = ":gh-success-octicon-checkcirclefillicon:"
        else:
            icon = ":grey_question:"

        summary.append(f"{icon} {job}")

    with GithubOutput() as github_output:
        github_output.write(
            summary=" | ".join(summary),
        )

def send() -> None:
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


def main():
    parser = argparse.ArgumentParser(
        description="Send a message to Mattermost or summarize the jobs results."
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Summarize the jobs results.",
    )
    summarize_parser.add_argument(
        "jobs_file",
        help="Path to a file where the jobs, in JSON format, are described.",
    )
    _ = subparsers.add_parser(
        "send",
        help="Send a message to Mattermost.",
    )
    args = parser.parse_args()

    if args.command == "summarize":
        summarize(args.jobs_file)
    elif args.command == "send":
        send()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
