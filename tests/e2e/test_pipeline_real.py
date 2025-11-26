import asyncio
from pathlib import Path

import pytest

from configstream.pipeline import run_full_pipeline


@pytest.mark.asyncio
async def test_full_pipeline_with_local_source(tmp_path, monkeypatch):
    """
    Lightweight integration test that runs the real producer/consumer pipeline
    against a local source file, using the dry-run tester to avoid external
    dependencies.
    """

    # 1. Create a minimal valid VLESS Reality config that the parser accepts
    src_file = tmp_path / "source.txt"
    src_file.write_text(
        "vless://11111111-1111-1111-1111-111111111111@1.1.1.1:443"
        "?security=reality&pbk=pubkey&sid=shortid#Test-Source\n",
        encoding="utf-8",
    )

    # 2. Avoid network I/O for blocklist updates and heavy output generation
    async def fake_update():
        return None

    async def fake_generate_outputs(optimized_proxies, output_path, stats, history):
        # Write a minimal marker file so the pipeline has something to report
        marker = Path(output_path) / "pipeline_success.txt"
        marker.write_text(f"{len(optimized_proxies)} proxies", encoding="utf-8")
        return {"marker": str(marker)}

    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)
    monkeypatch.setattr(
        "configstream.pipeline_core.output_handler.generate_pipeline_outputs",
        fake_generate_outputs,
    )

    # 3. Run full pipeline with dry_run tester to skip real network tests
    result = await run_full_pipeline(
        sources=[str(src_file)],
        output_dir=str(tmp_path / "out"),
        dry_run=True,
    )

    assert result.success is True
    # We should have at least one proxy flowing through the pipeline in dry-run mode
    assert result.stats.final_count >= 1
