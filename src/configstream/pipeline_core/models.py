# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional


from configstream.pipeline_core.stats import PipelineStats


class PipelineResult:
    def __init__(
        self,
        success: bool,
        stats: PipelineStats,
        output_files: dict,
        error: Optional[str] = None,
    ):
        self.success = success
        self.stats = stats
        self.output_files = output_files
        self.error = error
