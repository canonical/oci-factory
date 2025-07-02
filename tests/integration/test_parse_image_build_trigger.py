import os

import pytest
import yaml

from src.image.parse_external_ci_config import *


@pytest.fixture
def image_trigger(tmpdir):
    image_trigger_file = tmpdir.join("image.yaml")
    trigger = {
        "version": 1,
        "ghcr": {
            "upload": True,
            "enable-continuous-security-scanning": True,
        },
        "images": [
            {
                "directory": "mock-rock/1.2",
                "registries": ["registry1", "registry2"],
            },
            {
                "directory": "mock-rock/2.0",
            },
        ],
        "registries": {
            "registry1": {
                "uri": "docker.io/namespace1",
                "action-secrets": {
                    "username": "REGISTRY1_USERNAME",
                    "password": "REGISTRY1_PASSWORD",
                },
            },
            "registry2": {
                "uri": "registry2.azurecr.io/namespace2",
                "action-secrets": {
                    "username": "REGISTRY2_USERNAME",
                    "password": "REGISTRY2_PASSWORD",
                },
            },
            # Additional registries are not included
            "registry3": {
                "uri": "registry3.azurecr.io/namespace3",
                "action-secrets": {
                    "username": "REGISTRY2_USERNAME",
                    "password": "REGISTRY2_PASSWORD",
                },
            },
        },
    }

    with open(image_trigger_file, "w", encoding="UTF-8") as f:
        yaml.dump(trigger, f)
    return image_trigger_file


@pytest.fixture
def rockcraft_yaml(tmpdir):
    mock_rock_dir = tmpdir.mkdir("mock-rock")
    rockcraft_file_12 = mock_rock_dir.mkdir("1.2").join("rockcraft.yaml")
    rockcraft_content = """
name: mock-rock
version: 1.2
base: bare
build-base: ubuntu@22.04
"""
    rockcraft_file_12.write(rockcraft_content)

    rockcraft_file_20 = mock_rock_dir.mkdir("2.0").join("rockcraft.yaml")
    rockcraft_content_20 = """
name: mock-rock
version: 2.0
base: ubuntu@24.04
"""
    rockcraft_file_20.write(rockcraft_content_20)

    return mock_rock_dir


def test_prepare_image_build_matrix(image_trigger, rockcraft_yaml):
    os.chdir(rockcraft_yaml.dirname)
    image_trigger = load_image_trigger(image_trigger)
    builds = prepare_image_build_matrix(image_trigger, {})

    assert len(builds) == 2

    build_12 = builds[0]
    assert build_12["location"] == "mock-rock/1.2"
    assert build_12["image-name"] == "mock-rock"
    assert build_12["tags"]== "1.2-22.04_edge"
    assert build_12["registries"] == [
        {
            "domain": "docker.io",
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
    ]
    assert build_12["artifact-name"] == "mock-rock_1.2"
    assert build_12["pro"] == ""
    assert list(build_12.keys()) == [
        "location",
        "image-name",
        "tags",
        "artifact-name",
        "pro",
        "registries",
    ]

    build_20 = builds[1]
    assert build_20["location"] == "mock-rock/2.0"
    assert build_20["image-name"] == "mock-rock"
    assert build_20["tags"] == "2.0-24.04_edge"
    assert build_20["registries"] == []
    assert build_20["artifact-name"] == "mock-rock_2.0"
    assert build_20["pro"] == ""
    assert list(build_20.keys()) == [
        "location",
        "image-name",
        "tags",
        "artifact-name",
        "pro",
        "registries",]


def test_prepare_image_build_matrix_with_filter(image_trigger, rockcraft_yaml):
    # Only process the 1.2 directory
    image_dirs_to_process = {Path("mock-rock/1.2")}
    os.chdir(rockcraft_yaml.dirname)
    builds = prepare_image_build_matrix(
        yaml.safe_load(image_trigger.read()), image_dirs_to_process
    )

    assert len(builds) == 1

    assert builds[0]["location"] == "mock-rock/1.2"
