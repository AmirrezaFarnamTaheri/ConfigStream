# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.logging_config import setup_logging
import logging


def test_setup_logging():
    setup_logging(level="DEBUG")
    logger = logging.getLogger("configstream")
    # Check effective level because basicConfig sets the root logger level
    assert logger.getEffectiveLevel() == logging.DEBUG
    # Check if handler is added (to root logger usually if basicConfig)
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
