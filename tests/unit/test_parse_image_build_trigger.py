from src.image.parse_image_build_trigger import *
import pytest

@pytest.fixture
def rockcraft_yaml(tmpdir):
    rockcraft_file = tmpdir.join("rockcraft.yaml")
    rockcraft_file.write(
        """
name: mock_rock
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
    
    assert rockcraft_metadata["name"] == "mock_rock"
    assert rockcraft_metadata["version"] == "1.2"
    assert rockcraft_metadata["base"] == "22.04"


def test_prepare_publish_matrix():
    builds = [
        {
            "location": "mock_rock/1.2",
            "name": "mock_rock",
            "artifact-name": "mock_rock_1.2-22.04",
            "tag": "1.2-22.04",
            "pro": "pro1,pro2",
            "repositories": [
                {"registry": "registry1.com", "namespace": "namespace1"},
                {"registry": "registry2.azurecr.io", "namespace": "namespace2"}
            ],
            "risks": ["candidate", "beta", "edge"]
        }
    ]
    
    publish_matrix = prepare_publish_matrix(builds)
    
    assert len(publish_matrix["include"]) == 2
    assert publish_matrix["include"] == [
        {
            "name": "mock_rock",
            "tags": "1.2-22.04_candidate 1.2-22.04_beta 1.2-22.04_edge",
            "artifact-name": "mock_rock_1.2-22.04",
            "registry": "registry1.com",
            "namespace": "namespace1",
            "secret-prefix": "REGISTRY1_COM_CRED_",
        },
        {
            "name": "mock_rock",
            "tags": "1.2-22.04_candidate 1.2-22.04_beta 1.2-22.04_edge",
            "artifact-name": "mock_rock_1.2-22.04",
            "registry": "registry2.azurecr.io",
            "namespace": "namespace2",
            "secret-prefix": "REGISTRY2_AZURECR_IO_CRED_",
        }
    ]
