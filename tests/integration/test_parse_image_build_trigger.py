import pytest
from src.image.parse_image_build_trigger import *
import yaml
import os

@pytest.fixture
def image_trigger(tmpdir):
    image_trigger_file = tmpdir.join("image.yaml")
    trigger = {
        "version": 1,
        "build": [
            {
                "directory": "mock_rock/1.2",
                "tag": "1.2-22.04",
                "pro": ["pro1", "pro2"],
                "deploy": {
                    "repositories": [
                        {
                            "registry": "registry1",
                            "namespace": "namespace1",
                        },
                        {
                            "registry": "registry2",
                            "namespace": "namespace2",
                        },
                    ],
                    "risks": ["candidate", "beta"],
                }
            },
            {
                "directory": "mock_rock/2.0",
                "tag": "2.0-22.04",
                "pro": [],
            },
        ]
    }
    with open(image_trigger_file, "w", encoding="UTF-8") as f:
        yaml.dump(trigger, f)
    return image_trigger_file

@pytest.fixture
def rockcraft_yaml(tmpdir):
    mock_rock_dir = tmpdir.mkdir("mock_rock")
    rockcraft_file_12 = mock_rock_dir.mkdir("1.2").join("rockcraft.yaml")
    rockcraft_content = """
name: mock_rock
version: 1.2
base: bare
build-base: ubuntu@22.04
"""
    rockcraft_file_12.write(rockcraft_content)

    rockcraft_file_20 = mock_rock_dir.mkdir("2.0").join("rockcraft.yaml")
    rockcraft_content_20 = """
name: mock_rock
version: 2.0
base: ubuntu@24.04
"""
    rockcraft_file_20.write(rockcraft_content_20)

    return mock_rock_dir

def test_prepare_image_build_matrix(image_trigger, rockcraft_yaml):
    os.chdir(rockcraft_yaml.dirname)
    builds = prepare_image_build_matrix(yaml.safe_load(image_trigger.read()), {})

    assert len(builds) == 2

    build_12 = builds[0]
    assert build_12["location"] == "mock_rock/1.2"
    assert build_12["image-name"] == "mock_rock"
    assert build_12["tag"] == "1.2-22.04"
    assert build_12["pro"] == "pro1,pro2"
    assert build_12["repositories"] == [
        {
            "registry": "registry1",
            "namespace": "namespace1"
        },
        {
            "registry": "registry2",
            "namespace": "namespace2"
        }
    ]
    assert build_12["risks"] == ["candidate", "beta", "edge"]

    build_20 = builds[1]
    assert build_20["location"] == "mock_rock/2.0"
    assert build_20["image-name"] == "mock_rock"
    assert build_20["tag"] == "2.0-22.04"
    assert build_20["pro"] == ""

def test_prepare_image_build_matrix_with_filter(image_trigger, rockcraft_yaml):
    # Only process the 1.2 directory
    image_dirs_to_process = {Path("mock_rock/1.2")}
    os.chdir(rockcraft_yaml.dirname)
    builds = prepare_image_build_matrix(yaml.safe_load(image_trigger.read()), image_dirs_to_process)

    assert len(builds) == 1

    assert builds[0]["location"] == "mock_rock/1.2"
