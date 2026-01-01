# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.cli import main
from unittest.mock import patch
import sys


def test_cli_help():
    with patch.object(sys, "argv", ["configstream", "--help"]):
        with pytest.raises(SystemExit):
            main()


def test_cli_no_args():
    # Should probably print help or error
    with patch.object(sys, "argv", ["configstream"]):
        # It calls fire.Fire(ConfigStreamCLI)
        # Fire usually prints help if no command and raises SystemExit(0) or similar.
        with pytest.raises(SystemExit):
            main()


def test_cli_merge_help():
    with patch.object(sys, "argv", ["configstream", "merge", "--help"]):
        with pytest.raises(SystemExit):
            main()
