#!/usr/bin/env python3

"""
A pre-release is an informative data model meant to flag that there is
a new revision of an image that has been requested to be released.
This mechanism is necessary since one cannot know the revision number
of an image that has not yet been built. Thus, upon inferring the new
revision number and build said new image, the CI creates a pre-release
with the necessary information for the following jobs to be able to know
which revision number to release where.

NOTE: this is only necessary because the builds happen in parallel in a
GH matrix, which makes it difficult to sync and exchange information
between build. Thus pre-release data files are created for post-build
analysis.
"""

import argparse
import json
import yaml

from utils import schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-trigger",
        help="Path to the image trigger file.",
        required=True,
    )
    parser.add_argument(
        "--revision-data-file",
        help="Path to the revision data file.",
        required=True,
    )

    args = parser.parse_args()

    print(f"Getting existing image trigger from {args.image_trigger}")
    with open(args.image_trigger) as trigger:
        image_trigger = yaml.safe_load(trigger)

    _ = schema.triggers.ImageSchema(**image_trigger)

    user_releases = image_trigger.get("release", {})

    print(f"Getting pre-release from {args.revision_data_file}")
    with open(args.revision_data_file) as revision_data_f:
        revision_data = json.load(revision_data_f)

    _ = schema.revision_data.RevisionDataSchema(**revision_data)

    new_revision_releases = revision_data["release"]
    new_revision = revision_data["revision"]

    # Update "release" from image trigger with pre-releases
    for track, val in new_revision_releases.items():
        if "end-of-life" in val:
            user_releases[track]["end-of-life"] = val["end-of-life"]

        for risk in val["risks"]:
            user_releases[track][risk] = new_revision

    # Overwrite the image trigger with the new release value
    image_trigger["release"] = user_releases

    print(f"Finished merging pre releases:\n{json.dumps(image_trigger)}")
    print(f"Overwriting {args.image_trigger}...")
    with open(args.image_trigger, "w") as trigger:
        yaml.dump(
            image_trigger,
            trigger,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
