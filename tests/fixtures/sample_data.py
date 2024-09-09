import pytest
import xml.etree.ElementTree as ET
import yaml
from .. import DATA_DIR


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
