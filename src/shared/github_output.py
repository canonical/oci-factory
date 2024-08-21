#!/usr/bin/env python3

from io import TextIOBase
import json

"""This module provides support for writing Github Outputs."""


def write(output:TextIOBase = None, **kwargs):
    """Format kwargs for Github Outputs and write to `output` File Object"""

    for key, value in kwargs.items():

        formatted_value = format_value(value)
        print(f"{key}={formatted_value}", file=output)


def format_value(value):
    """Format `value` such that it can be stored as a github output"""

    if isinstance(value, str):
        # str is an exception to casting with json.dumps as we do
        # not need to represent the string itself, but just the data
        return value
    else:
        json_value = json.dumps(value)
        return json_value
    
