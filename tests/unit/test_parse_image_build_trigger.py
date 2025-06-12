import pytest

from src.image.parse_image_build_trigger import *


@pytest.fixture
def rockcraft_yaml(tmpdir):
    rockcraft_file = tmpdir.join("rockcraft.yaml")
    rockcraft_file.write(
        """
name: mock-rock
version: 1.2
base: bare
build-base: ubuntu@22.04
"""
    )
    return rockcraft_file


def test_backfill_higher_risks():
    risks = ["candidate"]
    risks = backfill_higher_risks(risks)

    assert risks == ["candidate", "beta", "edge"]


def test_get_image_rockcraft_metadata(rockcraft_yaml):
    rockcraft_metadata = get_image_rockcraft_metadata(Path(rockcraft_yaml.dirname))

    assert rockcraft_metadata["name"] == "mock-rock"
    assert rockcraft_metadata["version"] == "1.2"
    assert rockcraft_metadata["base"] == "22.04"


def test_unfold_publish_matrix():
    builds = [
        {
            "location": "mock-rock/1.2",
            "image-name": "mock-rock",
            "artifact-name": "mock-rock_1.2",
            "tags": "1.2-22.04_candidate 1.2-22.04_beta 1.2-22.04_edge",
            "pro": "pro1,pro2",
            "repos": [
                {
                    "domain": "registry1.com",
                    "namespace": "namespace1",
                    "username": "REGISTRY1_USERNAME",
                    "password": "REGISTRY1_PASSWORD",
                },
                {
                    "domain": "registry2.azurecr.io",
                    "namespace": "namespace2",
                    "username": "REGISTRY2_USERNAME",
                    "password": "REGISTRY2_PASSWORD",
                },
            ],
        }
    ]

    publish_matrix = unfold_publish_matrix(builds)

    assert len(publish_matrix) == 2
    assert publish_matrix == [
        {
            "image-name": "mock-rock",
            "tags": "1.2-22.04_candidate 1.2-22.04_beta 1.2-22.04_edge",
            "artifact-name": "mock-rock_1.2",
            "registry": "registry1.com",
            "namespace": "namespace1",
            "username": "REGISTRY1_USERNAME",
            "password": "REGISTRY1_PASSWORD",
        },
        {
            "image-name": "mock-rock",
            "tags": "1.2-22.04_candidate 1.2-22.04_beta 1.2-22.04_edge",
            "artifact-name": "mock-rock_1.2",
            "registry": "registry2.azurecr.io",
            "namespace": "namespace2",
            "username": "REGISTRY2_USERNAME",
            "password": "REGISTRY2_PASSWORD",
        },
    ]
