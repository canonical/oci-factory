import pytest
from io import StringIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory


@pytest.fixture
def str_buff():
    """String IO fixture for simulating a file object"""
    with StringIO() as buffer:
        yield buffer


@pytest.fixture
def github_output(monkeypatch):

    with TemporaryDirectory() as tmp:

        env_path = Path(tmp) / "env"
        env_path.touch()

        monkeypatch.setitem(os.environ, "GITHUB_OUTPUT", str(env_path))

        yield env_path
