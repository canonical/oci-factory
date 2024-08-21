#! /bin/env python3

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from io import StringIO

import format_markdown_report as report


@pytest.fixture
def sample_failure():
    """Load ET of sample junit xml report with failure"""
    sample_path = Path(__file__).parent / "data/sample_failure.xml"

    tree = ET.parse(sample_path)
    root = tree.getroot()
    return root


@pytest.fixture
def str_buff():
    """String IO fixture for simulating a filehandle"""
    with StringIO() as buffer:
        yield buffer


def test_print_redirection(sample_failure, str_buff, capsys):
    """Ensure that the report is entirely redirected when needed"""

    report.print_junit_report(sample_failure, str_buff)
    report.print_junit_report(sample_failure, None)  # print report to stdout

    str_buff.seek(0)
    str_buff_content = str_buff.read()

    captured = capsys.readouterr()
    stdout_content = captured.out

    assert stdout_content == str_buff_content, "Printing to multiple locations."

