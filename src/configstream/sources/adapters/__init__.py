# SPDX-License-Identifier: AGPL-3.0-or-later
"""External source acquisition adapters."""

from .github_blob import AcquiredSnapshot, GitHubBlobAdapter

__all__ = ["AcquiredSnapshot", "GitHubBlobAdapter"]
