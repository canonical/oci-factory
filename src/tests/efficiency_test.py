#!/usr/bin/env python3

import argparse
import logging
import sys
import utils.helpers as helper_functions

from tester import Test, TestingError


class BlackBoxTest(Test):
    def image_efficiency(self, docker_image_name: str) -> None:
        try:
            dive_output = helper_functions.dive_efficiency_test(
                docker_image_name, docker_client=self._docker_client
            )
        except Exception as err:
            raise TestingError from err

        logging.info(f"Image efficienty test result:\n{dive_output}")


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Runs Black-Box (generic) tests on the provided ROCK"
    )
    parser.add_argument(
        "--oci-archive",
        dest="oci_archive",
        default=None,
        help="path to the ROCK's OCI archive file",
    )
    parser.add_argument(
        "--docker-image",
        dest="docker_image",
        default=None,
        help="name of the Docker image, when --rock-oci-archive is not provided",
    )

    args = parser.parse_args()

    # Ideally, we should have a test where an output is captured for any
    # given input (true black box test), but for ROCKs this is hard

    if args.oci_archive:
        tests_runner = BlackBoxTest(image=args.oci_archive, image_format="oci-archive")

        logging.info(
            f"Copying the ROCK OCI archive {args.oci_archive} to the Docker daemon..."
        )
        image_basename = args.oci_archive.split("/")[-1]
        container_image = image_basename.replace(".", "_") + ":latest"
        image = tests_runner.convert(
            args.oci_archive,
            "oci-archive",
            container_image,
            "docker-daemon",
        )
    elif args.docker_image:
        tests_runner = BlackBoxTest(
            image=args.docker_image, image_format="docker-daemon"
        )
        image = args.docker_image
    else:
        parser.error("Need at least one argument")

    logging.info(f"Check that the image {image} exists")
    tests_runner._docker_client.images.get(image)

    logging.info(f"Checking the image's ({image}) efficiency")
    tests_runner.image_efficiency(image)
