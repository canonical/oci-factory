#!/usr/bin/env python3

import json
from os import environ

"""This module provides support for writing Github Outputs."""

# TODO: write custom json serializer to handle pathlib.Path


class GithubOutput:

    def __init__(self):

        self.output_path = environ["GITHUB_OUTPUT"]

    def __enter__(self):

        self.file_handler = open(self.output_path, "a")

        return self

    def __exit__(self, exc_type, exc_value, traceback):

        self.file_handler.close()
        del self.file_handler

    def write(self, **kwargs):
        """Format kwargs for Github Outputs and write to `output` File Object"""

        if not getattr(self, "file_handler", None):
            raise AttributeError(
                "file_handler not available. Please use in context block."
            )

        for key, value in kwargs.items():

            formatted_value = self.format_value(value)
            print(f"{key}={formatted_value}", file=self.file_handler)

    @staticmethod
    def format_value(value):
        """Format `value` such that it can be stored as a github output"""

        if isinstance(value, str):
            # str is an exception to casting with json.dumps as we do
            # not need to represent the string itself, but just the data
            return value
        else:
            json_value = json.dumps(value)
            return json_value


class GithubStepSummary(GithubOutput):
    """Write to the GITHUB_STEP_SUMMARY file"""

    def __init__(self):
        self.output_path = environ["GITHUB_STEP_SUMMARY"]
