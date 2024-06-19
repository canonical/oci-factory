#!/usr/bin/env python3

"""
This script validates that the image trigger entry is unique in the
given image.yaml file. This is necessary to avoid having multiple
entries for the same image trigger, which would lead to ambiguous
results when using the combination of {source}_{commit}_{directory}
as the cache key for the Image workflow runs.
"""

import argparse
import yaml

from utils.schema.triggers import ImageSchema


def main(args):
    print(f"Validating unique upload entry for {args.image_trigger}")
    with open(args.image_trigger, encoding="UTF-8") as trigger:
        image_trigger = yaml.load(trigger, Loader=yaml.BaseLoader)

    schema = ImageSchema(**image_trigger)
    unique_triggers = set()
    for upload in  schema.upload:
        trigger = f"{upload.source}_{upload.commit}_{upload.directory}"
        if trigger in unique_triggers:
            raise ValueError(f"Image trigger {trigger} is not unique.")
        unique_triggers.add(trigger)
    print("OK")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-trigger",
        help="Path to the image trigger file.",
        required=True,
    )
    args = parser.parse_args()
    
    main(args)
