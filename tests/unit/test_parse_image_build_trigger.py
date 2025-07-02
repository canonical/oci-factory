import pytest

from src.image.parse_external_ci_config import *


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
            "tags": "1.2-22.04_edge",
            "pro": "pro1,pro2",
            "registries": [
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
            "tags": "1.2-22.04_edge",
            "artifact-name": "mock-rock_1.2",
            "domain": "registry1.com",
            "namespace": "namespace1",
            "username": "REGISTRY1_USERNAME",
            "password": "REGISTRY1_PASSWORD",
        },
        {
            "image-name": "mock-rock",
            "tags": "1.2-22.04_edge",
            "artifact-name": "mock-rock_1.2",
            "domain": "registry2.azurecr.io",
            "namespace": "namespace2",
            "username": "REGISTRY2_USERNAME",
            "password": "REGISTRY2_PASSWORD",
        },
    ]
