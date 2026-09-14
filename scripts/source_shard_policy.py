# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared scheduling policy for canonical source batches and runtime shards."""

# Recent production timing evidence includes a single source that consumes nearly
# four hours by itself. Nine runtime parts keep the measured worst shard within
# the 4h soft + 15m hard budget without weakening the fail-closed timeout.
RUNTIME_SHARD_PARTS = 9
RUNTIME_SHARD_SOFT_LIMIT_SECONDS = 14_400
RUNTIME_SHARD_GRACE_SECONDS = 900
RUNTIME_SHARD_HARD_LIMIT_SECONDS = (
    RUNTIME_SHARD_SOFT_LIMIT_SECONDS + RUNTIME_SHARD_GRACE_SECONDS
)
CANONICAL_BATCH_TARGET_SECONDS = RUNTIME_SHARD_PARTS * RUNTIME_SHARD_SOFT_LIMIT_SECONDS
