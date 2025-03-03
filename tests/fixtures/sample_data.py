import json
import xml.etree.ElementTree as ET

import pytest
import yaml

from .. import DATA_DIR


@pytest.fixture
def release_json():
    """Load a sample of _release.json from mock-rock"""
    release_str = (DATA_DIR / "mock-rock_release.json").read_text()
    return json.loads(release_str)


@pytest.fixture
def circular_release_json():
    """Load a sample of _release.json from mock-rock"""
    release_str = (DATA_DIR / "mock-rock_circular_release.json").read_text()
    return json.loads(release_str)


@pytest.fixture
def junit_with_failure():
    """Load ET of junit xml report with failure."""
    sample_file = DATA_DIR / "junit_xml_failure.xml"

    tree = ET.parse(sample_file)
    root = tree.getroot()
    return root


@pytest.fixture
def rockcraft_project():
    """Get sample rockcraft project file for testing."""

    sample = DATA_DIR / "rockcraft.yaml"

    with open(sample) as rf:
        project = yaml.safe_load(rf)

    return project
