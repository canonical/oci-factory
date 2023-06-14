#!/usr/bin/env python3
"""
Takes a list of job and their results, and generates a small
one-liner summary message with the job names and their final statuses.
"""

import argparse
import json
import os


parser = argparse.ArgumentParser(
    description="""
    Generate workflow summary message from the jobs results.
    """
)

parser.add_argument(
    "--jobs-file",
    required=True,
    help="path to a file where the jobs, in JSON format, are described",
)

args = parser.parse_args()
with open(args.jobs_file, encoding="UTF-8") as jf:
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

with open(os.environ["GITHUB_OUTPUT"], "a") as gh_out:
    print(f"summary={' | '.join(summary)}", file=gh_out)
