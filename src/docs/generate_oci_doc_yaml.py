#!/usr/bin/env python3
"""
This module contains functions for generating documentation
for OCI images within the oci-factory
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
import pydantic
import yaml
from dateutil import parser

import src.shared.release_info as shared
from src.docs.schema.v1 import DocSchema as DocSchemaV1
from src.docs.schema.v2 import DocSchema as DocSchemaV2

from ..shared.logs import get_logger

logger = get_logger()


def cli_args() -> argparse.ArgumentParser:
    """Arguments parser"""
    parser = argparse.ArgumentParser(
        description="""
        Generate documentation of OCI images in OCI Factory.
        """
    )

    parser.add_argument(
        "--ecr-api-key",
        dest="username",
        help="username on ECR",
    )

    parser.add_argument(
        "--all-revision-tags",
        help="File w/ comma-separated list of all revision (<track>_<rev>) tags",
        required=True,
    )

    parser.add_argument(
        "--ecr-api-secret",
        dest="password",
        help="password/token on ECR",
    )

    parser.add_argument(
        "--repository",
        default="ubuntu",
        help="repository name on ECR",
    )

    parser.add_argument(
        "--oci-image-path",
        dest="image_path",
        required=True,
        help="path to the OCI image",
    )

    parser.add_argument(
        "--doc-data-dir",
        default="data",
        dest="doc_data_dir",
        help="Where the output YAML file will be stored",
    )

    return parser.parse_args()


class OCIDocumentationData:
    """
    The OCIDocumentationData class provides functionality
    to generate documentation data files in YAML format
    for the OCI images in the OCI Factory.
    """

    def __init__(self, username, password, image_path, repository, all_revision_tags):
        self.username = username
        self.image_path = image_path
        self.image_name = image_path.rstrip("/").split("/")[-1]
        self.repository = repository
        self.password = password
        self.all_revision_tags = all_revision_tags
        self.ecr_client = self._ecr_connect(self.username, self.password)
        self.skopeo_auth_token = self.ecr_client.get_authorization_token()[
            "authorizationData"
        ]["authorizationToken"]
        self.registry_url = f"public.ecr.aws/{self.repository}/{self.image_name}"
        self.add_yaml_representer()

    @staticmethod
    def _ecr_connect(api_key: str, api_secret: str) -> boto3.Session.client:
        """Open an authenticated client session with ECR public"""
        session = boto3.Session(
            region_name="us-east-1",
            aws_access_key_id=api_key,
            aws_secret_access_key=api_secret,
        )

        return session.client("ecr-public")

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
        logger.info("Execute process: %s, kwargs=%s", repr(command), repr(kwargs))
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            auth_config = {
                "auths": {self.registry_url: {"auth": self.skopeo_auth_token}}
            }
            auth_file = os.path.join(tmp_dir, "auth.json")
            with open(auth_file, "w", encoding="UTF-8") as file:
                os.fchmod(file.fileno(), 0o600)
                json.dump(auth_config, file)

            command = ["skopeo", cmd] + ["--authfile", auth_file] + args

            return json.loads(self.process_run(command))

    def get_arches(self, tag: str) -> List[str]:
        """
        Permit to get the arches associated with the tag
        """
        logger.info("Getting the arches for %s", tag)

        manifest_list = self.run_skopeo_command(
            "inspect", [f"docker://{self.registry_url}:" + tag, "--raw"]
        )

        if "manifests" in manifest_list:
            arch_list = []
            for arch in manifest_list["manifests"]:
                if arch["platform"]["architecture"] == "unknown":
                    continue
                arch_list.append(arch["platform"]["architecture"])
        else:
            arch_list = [
                self.run_skopeo_command(
                    "inspect", [f"docker://{self.registry_url}:" + tag]
                )["Architecture"]
            ]

        return arch_list

    @staticmethod
    def find_channel_tag(tags: List[str]) -> str:
        """
        This function finds tags that follow the channel tag pattern
        <version>-<base>_<risk>, eg. 1.0-22.04_edge. After all, all digests
        must have at least one of these tags, as enforced by the OCI Factory
        """
        suffix_pattern = f"((?:{')|(?:'.join(shared.KNOWN_RISKS_ORDERED)}))"
        pattern = r".+-\d{2}\.\d{2}_" + rf"{suffix_pattern}$"

        channel_tags = []
        for tag in tags:
            if re.match(pattern, tag):
                channel_tags.append(tag)

        if len(channel_tags) == 0:
            return ""

        # Now that we have the list of channel tags, we want to choose the
        # most stable one
        most_stable_channel_tags = []
        for risk in shared.KNOWN_RISKS_ORDERED:
            if most_stable_channel_tags:
                # Exit the loop whenever we find the most stable tags
                break

            for ch_tag in channel_tags:
                if risk in ch_tag:
                    most_stable_channel_tags.append(ch_tag)

        # Finally, if a digest ever has multiple channel tags with the same
        # risk, then we simply default to the latest one in alphabetical order
        most_stable_channel_tags.sort()

        return most_stable_channel_tags[-1]

    def build_releases_data(
        self,
        all_tracks: Dict[str, str],
        all_ecr_tags: Dict[str, Any],
    ) -> List[Dict]:
        """Build the releases info data structure"""
        logger.info(f"All available tracks:\n{list(all_tracks.keys())}")

        ecr_tag_details = all_ecr_tags["imageTagDetails"]
        ecr_tag_names = []
        # Get all unique digests as those map to revisions, and that's how
        # we should group the documentation table: 1 row per digest, with
        # multiple tags associated with it
        ecr_digests = []
        tags_by_digest = {}  # Eg. {"sha256:abc": ["tag1", "latest"]}
        for single_tag_details in ecr_tag_details:
            digest = single_tag_details["imageDetail"]["imageDigest"]
            tag = single_tag_details["imageTag"]

            if tag not in ecr_tag_names:
                ecr_tag_names.append(tag)
            if digest not in ecr_digests:
                ecr_digests.append(digest)

            tags_by_digest.setdefault(digest, []).append(tag)

        ecr_tag_names.sort()
        logger.info(f"All available OCI tags in ECR:\n{ecr_tag_names}")
        logger.info(f"{len(ecr_digests)} available digests in ECR")

        releases = []  # section to be added to the final YAML file
        for digest, digest_tags in tags_by_digest.items():
            release_data = {}
            # For each digest, we want to find the most stable OCI channel tag,
            # i.e. something like 1.0-22.04_stable
            channel_tag = self.find_channel_tag(digest_tags)
            if channel_tag == "":
                logger.warning(f"No canonical tag found for digest {digest}")
                continue
            track_base, release_data["risk"] = channel_tag.split("_")
            release_data["track"], release_data["base"] = track_base.split("-")
            release_data["tags"] = digest_tags.remove(channel_tag) or digest_tags
            # Get architecture list
            release_data["architectures"] = self.get_arches(channel_tag)
            # Set the support date
            if all_tracks.get(track_base):
                eol = parser.parse(all_tracks[track_base])
                release_data["support"] = {"until": eol.strftime("%m/%Y")}

                if eol < datetime.now(timezone.utc):
                    release_data["deprecated"] = {"date": eol.strftime("%m/%Y")}

            releases.append(release_data)

        return releases

    @staticmethod
    def read_documentation_yaml(doc_file: str) -> Dict:
        """Reads and parses the YAML contents of the documentation trigger file"""
        logger.info("Opening file %s", doc_file)
        with open(doc_file, "r", encoding="UTF-8") as file:
            try:
                yaml_file = yaml.load(file, Loader=yaml.BaseLoader) or {}

                if yaml_file.get("version") == 1:
                    base_doc_data = DocSchemaV1(**yaml_file).model_dump(exclude_none=True)
                elif yaml_file.get("version") == 2:
                    base_doc_data = DocSchemaV2(**yaml_file).model_dump(exclude_none=True)
                else:
                    raise ValueError(
                        f"Unsupported documentation.yaml version: {yaml_file.get('version')}"
                    )
            except (yaml.YAMLError, pydantic.ValidationError) as exc:
                msg = f"Error loading the {doc_file} file"
                raise Exception(msg) from exc
        return base_doc_data

    @staticmethod
    def create_data_dir(path: str) -> None:
        """Create doc data dir if it doesn't exist"""
        if not os.path.exists(path):
            logger.info("Creating the '%s' docs data folder", path)

            os.makedirs(path)

    @staticmethod
    def write_data_file(file_path: str, content: Dict) -> None:
        """Write the YAML content into the output file path"""
        with open(file_path, "w", encoding="UTF-8") as fp:
            logger.info("Create the doc data YAML file '%s'", file_path)
            yaml.dump(content, fp, sort_keys=False)

    @staticmethod
    def get_all_tracks(
        all_revision_tags: list, releases_file: str = ""
    ) -> Dict[str, str]:
        """
        Given a list of all the existing revision tags for a rock, get the
        corresponding track names and their end-of-life dates.

        It returns a Dict {"track": "eol", ...}.

        :param all_revision_tags: all existing revision tags for a rock
        :param release_file: the path to the _releases.json file for that rock
        """
        _releases = {}
        if releases_file:
            try:
                with open(releases_file) as rf:
                    _releases = json.load(rf)
            except FileNotFoundError:
                logger.warning(f"Unable to load _releases.json and EOL dates")
                pass

        all_tracks = {}
        for track in set(map(lambda t: t.rsplit("_", 1)[0], all_revision_tags)):
            all_tracks[track] = _releases.get(track, {}).get("end-of-life")

        return all_tracks

    def main(self, doc_data_dir: str) -> None:
        """Main function for generating the documentation data YAML file"""

        logger.info("Opening the documentation.yaml file")
        base_doc_yaml = self.read_documentation_yaml(
            f"{self.image_path}/documentation.yaml"
        )

        # Get a list of all revision tags, eg. ["1.0-22.04_1", "1.1-23.04_42", ...]
        all_revision_tags = shared.get_all_revision_tags(self.all_revision_tags)

        # Extract a unique set of tracks, and their EOL, from that list
        all_tracks = self.get_all_tracks(
            all_revision_tags, releases_file=f"{self.image_path}/_releases.json"
        )

        override_tracks = base_doc_yaml.get("override_tracks", {})
        logger.info(f"Override tracks from documentation.yaml: {override_tracks}")
        all_tracks.update({k: v["end_of_life"] for k, v in override_tracks.items()})

        # Get all the published OCI tags from ECR
        all_ecr_tags = {"imageTagDetails": []}
        desc_img_tags_resp = self.ecr_client.describe_image_tags(
            repositoryName=self.image_name
        )
        all_ecr_tags["imageTagDetails"] = desc_img_tags_resp.get("imageTagDetails", [])
        while next_token := desc_img_tags_resp.get("nextToken"):
            desc_img_tags_resp = self.ecr_client.describe_image_tags(
                repositoryName=self.image_name, nextToken=next_token
            )
            all_ecr_tags["imageTagDetails"].extend(
                desc_img_tags_resp.get("imageTagDetails", [])
            )

        logger.info("Building releases section for doc data YAML file")

        releases = self.build_releases_data(all_tracks, all_ecr_tags)

        base_doc_yaml["repo"] = self.image_name
        base_doc_yaml["releases"] = releases
        # Making optional values explicitly "null" if they were not given
        base_doc_yaml["debug"] = base_doc_yaml.get("debug")
        base_doc_yaml["parameters"] = base_doc_yaml.get("parameters")
        base_doc_yaml["docker"] = base_doc_yaml.get("docker")
        base_doc_yaml["microk8s"] = base_doc_yaml.get("microk8s")
        base_doc_yaml["is_chiselled"] = base_doc_yaml.get("is_chiselled", False)
        self.create_data_dir(doc_data_dir)

        name_doc_file = f"{self.image_name}_doc_data.yaml"
        output_data_file = f"{doc_data_dir}/{name_doc_file}"
        self.write_data_file(output_data_file, base_doc_yaml)
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="UTF-8") as gh_out:
            print(f"name_doc_file={name_doc_file}", file=gh_out)
            print(f"image_doc_folder={doc_data_dir}", file=gh_out)


if __name__ == "__main__":
    args = cli_args()
    runner = OCIDocumentationData(
        args.username,
        args.password,
        args.image_path,
        args.repository,
        args.all_revision_tags,
    )
    runner.main(args.doc_data_dir)
