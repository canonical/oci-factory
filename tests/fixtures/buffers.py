import os
from io import StringIO
from pathlib import Path

import pytest


@pytest.fixture
def str_buff():
    """String IO fixture for simulating a file object"""
    with StringIO() as buffer:
        yield buffer


@pytest.fixture
def github_output(monkeypatch, tmp_path):

    env_path = tmp_path / "env"
    env_path.touch()

    monkeypatch.setitem(os.environ, "GITHUB_OUTPUT", str(env_path))

    yield env_path


@pytest.fixture
def github_step_summary(monkeypatch, tmp_path):

    env_path = tmp_path / "env-step-summary"
    env_path.touch()

    monkeypatch.setitem(os.environ, "GITHUB_STEP_SUMMARY", str(env_path))

    yield env_path
