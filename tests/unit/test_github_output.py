#!/usr/bin/env python3

from src.shared.github_output import GithubOutput, GithubStepSummary

from ..fixtures.buffers import github_output, github_step_summary


def test_write(github_output):
    """Test github_output write function"""

    outputs = {
        "hello-world": 42,
    }
    expected_result = "hello-world=42\n"

    with GithubOutput() as output:

        output.write(**outputs)

    with open(github_output, "r") as fh:
        result = fh.read()

    assert result == expected_result


def test_format_value_string():
    """Test formatting of string for outputs"""

    expected_result = "foo"
    result = GithubOutput.format_value("foo")

    assert expected_result == result


def test_format_value_number():
    """Test formatting of number for outputs"""

    expected_result = "1"
    result = GithubOutput.format_value(1)

    assert expected_result == result


def test_format_value_json():
    """Test formatting of JSON for outputs"""

    expected_result = '{"foo": "bar"}'
    result = GithubOutput.format_value({"foo": "bar"})

    assert expected_result == result


def test_write_step_summary(github_step_summary):
    """Test github_output write function to step_summary"""

    outputs = {
        "hello-world": 42,
    }
    expected_result = "hello-world=42\n"

    with GithubStepSummary() as output:

        output.write(**outputs)

    with open(github_step_summary, "r") as fh:
        result = fh.read()

    assert result == expected_result
