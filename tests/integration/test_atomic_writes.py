import json
from pathlib import Path
from unittest.mock import patch

import pytest

from configstream.serialize import dump_to_path


def test_atomic_write_interruption(tmp_path):
    """
    Test that an interruption during an atomic write does not corrupt the final file.
    """
    output_path = tmp_path / "output.json"
    old_data = {"version": 1}
    new_data = {"version": 2}

    # Create an initial version of the file
    output_path.write_text(json.dumps(old_data))

    # Patch pathlib.Path.replace to simulate an interruption after the temp file is written
    with patch("pathlib.Path.replace", side_effect=OSError("Simulated interruption")):
        with pytest.raises(OSError):
            dump_to_path(output_path, new_data)

    # The original file should be untouched
    assert json.loads(output_path.read_text()) == old_data
