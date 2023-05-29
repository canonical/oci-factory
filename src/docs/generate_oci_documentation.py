#!/usr/bin/env python3
"""
This module contains functions for generating documentation
for OCI build with the oci-factory
"""
import argparse
import base64
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List
import yaml
import pydantic
from schema.triggers import DocSchema


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, ".."))
import shared.functions as shared


class GenerateOciYaml:
    """
    A class representing an object to build documentation for OCI image:
    Attributes:
        - username (str): Your username on the Dockerhub.
        - password (str): Your password/token on the Dockerhub.
        - data_dir (str): The folder name where the file will be stored.
        - name_of_oci (str): Name of the OCI image.
        - repository (str): The repository name of the OCI image on Dockerhub.
        - image_trigger (path): Path to the image trigger file.
        - all_releases (path): Path to the _releases.json file.
        - all_revision_tags (path): File w/ comma-separated list of all revision (<track>_<rev>) tags.

        Methods:
        - cli_args: Parse the arguments passed in from the command line.
        - validate_arguments: Validate the arguments.
        - build_image_endpoint: Build the URL using DockerHub and your information.
        - add_yaml_representer: Permit to write data on multiple lines on the output YAML.
        - process_run: Permit to run shell commands.
        - run_skopeo_command: Permit to run skopeo commands.
        - get_arches: Permit to get the arches associated with an image tag.
        - get_lowest_risk: Permit to get the lowest risk associated with an image tag.
        - get_canonical_tags: Permit to get the canonical tag associated to a revision.
        - build_releases_data: Build the releases section of the YAML file.
        - read_data_template: Read the template file for the documentation.
        - create_data_dir: Create the output directory if it doesn't exist.
        - write_data_file: Write the documentation generated into the template.
        - main: Permit to generate and output the documentation to a file.
    """

    def __init__(self):
        self.username = None
        self.data_dir = "oci"
        self.name_of_oci = None
        self.repository = None
        self.password = None
        self.image_trigger = None
        self.all_releases = None
        self.all_revision_tags = None
        self.validate_args()
        self.add_yaml_representer()
        self.build_image_endpoint()

    @staticmethod
    def cli_args() -> argparse.ArgumentParser:
        """Argument parser"""
        parser = argparse.ArgumentParser(
            description="""
            Generate documentation of OCI image builds on OCI-Factory.
            """
        )

        parser.add_argument(
            "--username",
            dest="username",
            help="username on DockerHub",
        )

        parser.add_argument(
            "--password",
            dest="password",
            help="password/token on DockerHub",
        )

        parser.add_argument(
            "--repository-basename",
            dest="repository",
            required=True,
            help="repository basename on DockerHub",
        )

        parser.add_argument(
            "--oci-image-name",
            dest="name_of_oci",
            required=True,
            help="name of the OCI image",
        )

        parser.add_argument(
            "--image-trigger",
            help="Path to the image trigger file.",
            dest="image_trigger",
            required=True,
        )

        parser.add_argument(
            "--all-releases",
            help="Path to the _releases.json file.",
            dest="all_releases",
            required=True,
        )
        parser.add_argument(
            "--all-revision-tags",
            help="File w/ comma-separated list of all revision (<track>_<rev>) tags.",
            dest="all_revision_tags",
            required=True,
        )

        parser.add_argument(
            "--data-dir",
            default="oci",
            dest="data_dir",
            help="Where the output file will be stored",
        )

        return parser

    def validate_args(self) -> None:
        """Parse and validate the CLI arguments"""
        parser = self.cli_args()
        parser.parse_args(namespace=self)
        if (
            self.repository is None
            or self.name_of_oci is None
            or self.image_trigger is None
            or self.all_releases is None
            or self.all_revision_tags is None
        ):
            parser.error("""One of the required variable is empty""")

    def build_image_endpoint(self) -> None:
        """Define the image's registry URL"""
        self.url = f"docker.io/{self.repository}/{self.name_of_oci}"
        logging.info("Using %s to collect information", self.url)

    @staticmethod
    def add_yaml_representer() -> None:
        """
        Add a presenter to be able to
        deal with multiline
        """

        def str_presenter(dumper, data):
            """
            Permit to format
            multiline string into
            yaml file
            """

            str_tag_yaml = "tag:yaml.org,2002:str"
            if len(data.splitlines()) > 1:  # check for multiline string
                return dumper.represent_scalar(str_tag_yaml, data, style="|")
            return dumper.represent_scalar(str_tag_yaml, data)

        yaml.add_representer(str, str_presenter)
        yaml.representer.SafeRepresenter.add_representer(str, str_presenter)

    @staticmethod
    def process_run(command: List[str], **kwargs) -> str:
        """Run a command and handle its output."""
        logging.info("Execute process: %s, kwargs=%s", repr(command), repr(kwargs))
        try:
            out = subprocess.run(
                command,
                **kwargs,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as err:
            msg = f"Failed to run command: {command!s}"
            if err.stderr:
                msg += f" ({err.stderr.strip()!s})"
            raise subprocess.CalledProcessError(err.returncode, msg)

        return out.stdout.strip()

    def run_skopeo_command(self, cmd: str, args: List[str]) -> Dict:
        """Builds the Skopeo command and runs it"""
        command = ["skopeo", cmd]

        with tempfile.TemporaryDirectory() as tmp_dir:
            if self.username is not None and self.password is not None:
                _skopeo_auth_token = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                auth_config = {"auths": {self.url: {"auth": _skopeo_auth_token}}}
                auth_file = os.path.join(tmp_dir, "auth.json")
                with open(auth_file, "w", encoding="UTF-8") as file:
                    os.fchmod(file.fileno(), 0o600)
                    json.dump(auth_config, file)
                command += ["--authfile", auth_file]
            command += args

            return json.loads(self.process_run(command))

    def get_arches(self, tag: str, arches_list: List[Dict]) -> List[str]:
        """
        Permit to get the arches associated to the tag
        """
        logging.info("Getting the arches for %s", tag)
        arches = []
        for arch in arches_list:
            arches.append(arch["platform"]["architecture"])
        return arches

    def get_lowest_risk(self, tags: List[str]) -> str:
        """
        Get the lowest risk associated with the tag
        """
        risk_sorted = ["stable", "candidate", "beta", "edge"]

        all_tags_str = " ".join(tags)
        for risk in risk_sorted:
            if risk in all_tags_str:
                return risk

        return "edge"

    @staticmethod
    def get_canonical_tags(all_tags_by_revision, track_by_revision, key_to_search):
        """
        permit to find the canonical tag associated to a revision
        """
        canonical_tag = None
        pattern = r"^\d+\.\d+-\d+\.\d+$"
        for tag in all_tags_by_revision[key_to_search]:
            if re.match(pattern, tag):
                canonical_tag = tag
                return canonical_tag
        return track_by_revision[key_to_search]

    def build_releases_data(
        self,
        group_by_revision,
        revision_to_track,
    ) -> List[Dict]:
        """Build the releases info data structure"""
        releases = []
        tracks_base = []
        for tag in group_by_revision:
            canonical_tag = self.get_canonical_tags(
                group_by_revision, revision_to_track, tag
            )
            release_data = {}
            track = canonical_tag.split("-")[0]
            base = canonical_tag.split("-")[1]

            if canonical_tag.split("_")[0] in tracks_base:
                continue

            tracks_base.append(canonical_tag.split("_")[0])
            release_data["track"] = track
            release_data["base"] = base

            manifest_list = self.run_skopeo_command(
                "inspect",
                [f"docker://{self.url}:" + group_by_revision[tag][0], "--raw"],
            )

            if "manifests" in manifest_list:
                release_data["architectures"] = self.get_arches(
                    tag, manifest_list["manifests"]
                )
            else:
                manifest_list = self.run_skopeo_command(
                    "inspect", [f"docker://{self.url}:" + group_by_revision[tag][0]]
                )

                release_data["architectures"] = [manifest_list["Architecture"]]

            release_data["tags"] = group_by_revision[tag]

            release_data["risk"] = self.get_lowest_risk(release_data["tags"])
            releases.append(release_data)

        return releases

    def read_data_template(self) -> Dict:
        """Reads and parses the YAML contents of the data template"""
        template_file = f"{self.data_dir}/{self.name_of_oci}/documentation.yaml"
        logging.info("Opening the template file %s", template_file)
        with open(template_file, "r", encoding="UTF-8") as file:
            try:
                template_data = DocSchema(**yaml.safe_load(file) or {}).dict(
                    exclude_none=True
                )
            except (yaml.YAMLError, pydantic.ValidationError) as exc:
                logging.error("Error when loading the documentation template file")
                raise exc
        return template_data

    @staticmethod
    def create_data_dir(path: str) -> None:
        """Create data dir if it doesn't exist"""
        if not os.path.exists(path):
            logging.info("Creating the %s folder", path)

            os.makedirs(path)

    @staticmethod
    def write_data_file(file_path: str, content: Dict) -> None:
        """Write the YAML content into the output file path"""
        with open(file_path, "w", encoding="UTF-8") as file:
            logging.info("Create the yaml file %s", file_path)
            yaml.dump(content, file, sort_keys=False)

    def main(self) -> None:
        """Main function for generating the documentation"""
        logging.info("Opening the documentation.yaml file")

        dict_file = self.read_data_template()

        logging.info("Get the tag for %s", self.name_of_oci)
        all_revision_tags = shared.get_all_revision_tags(self.all_revision_tags)

        revision_to_track = shared.get_revision_to_track(all_revision_tags)

        all_releases = shared.get_all_releases(self.all_releases)

        tag_mapping_from_all_releases = shared.get_tag_mapping_from_all_releases(
            all_releases
        )

        image_trigger = shared.get_image_trigger(self.image_trigger)
        tag_mapping_from_trigger, all_releases = shared.get_tag_mapping_from_trigger(
            image_trigger, all_releases
        )
        # combine all tags
        all_tags_mapping = {
            **tag_mapping_from_all_releases,
            **tag_mapping_from_trigger,
        }

        tag_to_revision = shared.get_tag_to_revision(
            tag_mapping_from_trigger, all_tags_mapping, revision_to_track
        )
        release_tags = shared.get_releases_tags(tag_to_revision)
        group_by_revision = shared.get_group_by_revision(release_tags)
        logging.info("Building releases info")

        releases = self.build_releases_data(group_by_revision, revision_to_track)

        dict_file["repo"] = self.name_of_oci
        dict_file["releases"] = releases
        dict_file["debug"] = dict_file.get("debug")
        dict_file["parameters"] = dict_file.get("parameters")
        dict_file["docker"] = dict_file.get("docker")
        dict_file["microk8s"] = dict_file.get("microk8s")
        dict_file["is_chiselled"] = dict_file.get("is_chiselled", False)
        self.create_data_dir(self.data_dir)

        output_data_file = f"{self.data_dir}/{self.name_of_oci}/_documentation.yaml"
        self.write_data_file(output_data_file, dict_file)


if __name__ == "__main__":
    runner = GenerateOciYaml()
    runner.main()
