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
