#!/usr/bin/env python3

import argparse
import json
import os
import os.path
import sys
import tempfile
from pathlib import Path
from subprocess import check_call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.logs import get_logger

logger = get_logger()


def parse_args():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument("source_uri")
    argp.add_argument("target_name")
    argp.add_argument("target_tags", nargs="+")
    argp.add_argument("--registry-auth")
    args = argp.parse_args()
    if not args.registry_auth:
        args.registry_auth = os.getenv("REGISTRY_AUTH")
    return args


def main():
    args = parse_args()
    base_cmd = ["skopeo", "copy", "--preserve-digests", args.source_uri]

    with tempfile.TemporaryDirectory() as tmp_dir:
        if args.registry_auth:
            auth_config = {"auths": {args.target_name: {"auth": args.registry_auth}}}
            auth_file = os.path.join(tmp_dir, "auth.json")
            with open(auth_file, "w") as f:
                os.fchmod(f.fileno(), 0o600)
                json.dump(auth_config, f)
            base_cmd += ["--authfile", auth_file]

        target_uri = "docker://" + args.target_name + ":" + args.target_tags[0]
        cmd = base_cmd + ["--multi-arch", "all", target_uri]
        logger.info(" ".join(cmd))
        check_call(cmd)

        for tag in args.target_tags[1:]:
            target_uri = "docker://" + args.target_name + ":" + tag
            cmd = base_cmd + ["--multi-arch", "index-only", target_uri]
            logger.info(" ".join(cmd))
            check_call(cmd)


if __name__ == "__main__":
    main()
