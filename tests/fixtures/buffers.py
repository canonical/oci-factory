import pytest
from io import StringIO


@pytest.fixture
def str_buff():
    """String IO fixture for simulating a file object"""
    with StringIO() as buffer:
        yield buffer
