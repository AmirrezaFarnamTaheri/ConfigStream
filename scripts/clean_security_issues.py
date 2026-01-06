#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Utility to remove configs with specific security issues from the output/full/all.json file.
"""
from __future__ import annotations
import sys


def main() -> int:
    # This script is deprecated. Invoke the pipeline with the proper security validator instead.
    print(
        "clean_security_issues.py is deprecated. Security filtering occurs automatically during the pipeline."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
