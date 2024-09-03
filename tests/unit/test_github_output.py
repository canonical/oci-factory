#!/usr/bin/env python3

from src.shared.github_output import write, format_value
from io import StringIO
import pytest


@pytest.fixture
def text_buffer():
    with StringIO() as buffer:
        yield buffer


def test_write(text_buffer):
    """Test github_output write function"""

    outputs = {
        "hello-world": 42,
    }
    expected_result = "hello-world=42\n"

    write(text_buffer, **outputs)

    text_buffer.seek(0)
    result = text_buffer.read()

    assert result == expected_result


def test_format_value_string():
    """Test formatting of string for outputs"""

    expected_result = "foo"
    result = format_value("foo")

    assert expected_result == result


def test_format_value_number():
    """Test formatting of number for outputs"""

    expected_result = "1"
    result = format_value(1)

    assert expected_result == result


def test_format_value_json():
    """Test formatting of JSON for outputs"""

    expected_result = '{"foo": "bar"}'
    result = format_value({"foo": "bar"})

    assert expected_result == result
