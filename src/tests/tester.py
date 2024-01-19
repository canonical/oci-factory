# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
import docker
import logging
import os
import subprocess
from typing import Literal

from pydantic import BaseModel, PrivateAttr


class TestingError(Exception):
    """Error when any of the tests fail"""


class Test(BaseModel):
    """Sets the ground for all tests"""

    # Name of the rock, or path if provided in OCI formats
    image: str
    # Format of the provided image
    image_format: Literal["docker-daemon", "oci-archive", "fs"]
    # Constant Docker client
    _docker_client: object = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._docker_client = docker.from_env()

        # Validates the image
        if self.image_format == "docker-daemon":
            # check that image exists
            self._docker_client.images.get(self.image)
        else:
            self.image = os.path.abspath(self.image)

        if self.image_format == "oci-archive":
            # then it's a file
            assert os.path.isfile(
                self.image
            ), f"Cannot find OCI archive file {self.image}."

        if self.image_format == "fs":
            # then it's a directory
            assert os.path.isdir(
                self.image
            ), f"Cannot find image filesystem directory {self.image}."

    def convert(
        self, origin: str, origin_format: str, dest: str, dest_format: str
    ) -> None:
        logging.info(f"Copying from {origin_format}:{origin} to {dest_format}:{dest}")
        try:
            if not origin_format.startswith("docker"):
                mounted_origin = f"/rootfs{os.path.abspath(origin)}"
            if not dest_format.startswith("docker"):
                mounted_dest = f"/rootfs{os.path.abspath(dest)}"

            copy_cmd = (
                f"copy {origin_format}:{mounted_origin} {dest_format}:{mounted_dest}"
            )
            skopeo = self._docker_client.containers.run(
                "quay.io/skopeo/stable:v1.8",
                working_dir="/rock",
                volumes={
                    "/": {"bind": "/rootfs"},
                    "/var/run/docker.sock": {"bind": "/var/run/docker.sock"},
                },
                command=copy_cmd,
                detach=True,
            )
            skopeo.wait()
            logging.info(skopeo.logs().decode())
        except Exception as skopeoerror:
            logging.warning(f"Failed to run Skopeo as a container: {skopeoerror}")
            logging.info("Attempting to run Skopeo from the underlying system...")
            copy_cmd = f"skopeo copy {origin_format}:{origin} {dest_format}:{dest}"
            output = subprocess.check_output(
                copy_cmd.split((" ")), universal_newlines=True
            )
            logging.info(output)

        return dest
