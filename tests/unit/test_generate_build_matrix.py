#!/usr/bin/env python3

from src.build_rock.configure.generate_build_matrix import (
    get_target_archs,
    configure_matrices,
    MissingArchSupport,
    set_build_config_outputs,
)
from pathlib import Path
import pytest
from tempfile import TemporaryDirectory


def test_get_target_archs():
    """Test extraction of target architectures from rockcraft project configuration"""
    project = {
        "name": "hello-world",
        "title": "Hello World",
        "summary": "An Hello World rock",
        "description": "This is just an example of a Rockcraft project\nfor a Hello World rock.\n",
        "version": "latest",
        "base": "bare",
        "build-base": "ubuntu@22.04",
        "license": "Apache-2.0",
        "run-user": "_daemon_",
        "environment": {"FOO": "bar"},
        "services": {
            "hello": {
                "override": "replace",
                "command": "/usr/bin/hello -t",
                "environment": {"VAR1": "value", "VAR2": "other value"},
            }
        },
        "platforms": {
            "amd64": None,
            "armhf": {"build-for": ["armhf", "arm64"]},
            "ibm": {"build-on": ["s390x"], "build-for": "s390x"},
        },
        "parts": {"hello": {"plugin": "nil", "stage-packages": ["hello"]}},
    }

    arches = get_target_archs(project)
    assert arches == {"arm64", "armhf", "amd64"}


def test_configure_matrices():
    """Test correct configuration of build matrices from project's target arches"""

    build_matrices = configure_matrices(["amd64"], {"amd64": "ubuntu-22.04"}, False)
    expected_result = {
        "runner-build-matrix": {
            "include": [{"architecture": "amd64", "runner": "ubuntu-22.04"}]
        },
        "lpci-build-matrix": {"include": []},
    }

    assert build_matrices == expected_result


def test_configure_matrices_fallback_exception():
    """Test proper exception is raised when target arch is not buildable"""
    with pytest.raises(MissingArchSupport):
        configure_matrices(["arm64"], {"amd64": "ubuntu-22.04"}, False)


def test_configure_matrices_lpci_fallback():
    """Test lpci fallback logic when target cannot be built on a runner"""
    build_matrices = configure_matrices(["arm64"], {"amd64": "ubuntu-22.04"}, True)
    expected_result = {
        "runner-build-matrix": {"include": []},
        "lpci-build-matrix": {"include": [{"architecture": "arm64"}]},
    }

    assert build_matrices == expected_result


def test_set_build_config_outputs():
    """Test correct generation of build matrices."""

    test_build_matrices = {
        "runner-build-matrix": {
            "include": [{"architecture": "amd64", "runner": "ubuntu-22.04"}]
        },
        "lpci-build-matrix": {"include": []},
    }

    with TemporaryDirectory() as tmp:

        env_path = Path(tmp) / "env"

        set_build_config_outputs("test", test_build_matrices, output_path=env_path)

        with open(env_path, "r") as fh:
            gh_output = fh.read()

    expected_result = """rock-name=test
runner-build-matrix={"include": [{"architecture": "amd64", "runner": "ubuntu-22.04"}]}
lpci-build-matrix={"include": []}
"""

    assert gh_output == expected_result
