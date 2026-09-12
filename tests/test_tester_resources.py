# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from configstream.testers import utils


def test_config_permission_failure_closes_descriptor(tmp_path):
    fd, path = tempfile.mkstemp(dir=tmp_path)
    with (
        patch.object(utils.tempfile, "mkstemp", return_value=(fd, path)),
        patch.object(utils.os, "chmod", side_effect=PermissionError("denied")),
    ):
        with pytest.raises(PermissionError):
            with utils.SecureConfigContext("secret"):
                pytest.fail("permission failure must prevent startup")
    with pytest.raises(OSError):
        os.fstat(fd)
    assert not Path(path).exists()
    assert path not in utils._TEMP_FILES


def test_config_unlink_failure_is_retried_at_shutdown():
    with utils.SecureConfigContext("secret") as path:
        with patch.object(utils.os, "unlink", side_effect=PermissionError("busy")):
            utils._remove_temp_file(path)
        assert path in utils._TEMP_FILES
        assert Path(path).read_text() == "secret"
        utils._cleanup_temp_files()
        assert path not in utils._TEMP_FILES
        assert not Path(path).exists()
