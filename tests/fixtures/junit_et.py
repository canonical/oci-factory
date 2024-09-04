import pytest
import xml.etree.ElementTree as ET
from .. import DATA_DIR


@pytest.fixture
def junit_with_failure():
    """Load ET of junit xml report with failure"""
    sample = DATA_DIR / "junit_xml_failure.xml"

    tree = ET.parse(sample)
    root = tree.getroot()
    return root
