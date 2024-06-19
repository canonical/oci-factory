import os
import pytest

from unittest.mock import patch
from io import StringIO
from tempfile import TemporaryDirectory as tempdir

from validate_unique_trigger_upload_entry import *

def test_validate_unique_trigger_entry():
    # Create a temporary image trigger file for testing
    image_trigger_data = {
        "version": 1,
        "upload": [
            {
                "source": "source1",
                "commit": "commit1",
                "directory": "directory1"
            },
            {
                "source": "source2",
                "commit": "commit2",
                "directory": "directory2"
            }
        ]
    }

    with tempdir() as tmp_dir:
        image_trigger_file = os.path.join(tmp_dir, "trigger.yaml")
        with open(image_trigger_file, "w") as f:
            yaml.dump(image_trigger_data, f)

        args = argparse.Namespace(image_trigger=image_trigger_file)
        main(args)


def test_validate_unique_trigger_entry_non_unique():
    # Create a temporary image trigger file for testing
    image_trigger_data = {
        "version": 1,
        "upload": [
            {
                "source": "source1",
                "commit": "commit1",
                "directory": "directory1"
            },
            {
                "source": "source2",
                "commit": "commit2",
                "directory": "directory2"
            },
            {
                "source": "source1",
                "commit": "commit1",
                "directory": "directory1"
            }
        ]
    }
    with tempdir() as tmp_dir:
        image_trigger_file = os.path.join(tmp_dir, "trigger.yaml")
        with open(image_trigger_file, "w") as f:
            yaml.dump(image_trigger_data, f)

        # Call the main function and assert that it raises a ValueError]
        args = argparse.Namespace(image_trigger=image_trigger_file)
        with pytest.raises(ValueError) as e:
            main(args)
            assert str(e.value) == "Image trigger source1_commit1_directory1 is not unique."
