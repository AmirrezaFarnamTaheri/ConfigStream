import asyncio
from pathlib import Path
import pytest
import respx
from httpx import Response

from configstream.pipeline import run_full_pipeline
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_pipeline_full_run(tmp_path: Path, respx_mock: respx.MockRouter):
    """
    Tests a full end-to-end run of the pipeline with mocked network requests.
    """
    # 1. Setup mock data and files
    source_content = "http://mock-source.com/proxies.txt"
    source_file = tmp_path / "sources.txt"
    source_file.write_text(source_content)
    output_dir = tmp_path / "output"

    proxy_config = "http://user:pass@1.2.3.4:8080"

    # 2. Mock network requests
    # Mock the source fetch
    respx_mock.get("http://mock-source.com/proxies.txt").mock(
        return_value=Response(200, text=proxy_config)
    )
    # Mock the proxy test (latency check)
    respx_mock.get("https://www.google.com/generate_204").mock(
        return_value=Response(204)
    )

    # 3. Run the pipeline
    result = await run_full_pipeline(
        sources=[str(source_file)],
        output_dir=str(output_dir),
        timeout=5,
        dry_run=True,
    )

    # 4. Assert the results
    assert result.success is True
    assert result.error is None
    assert result.stats["fetched_sources"] == 1
    assert result.stats["parsed"] > 0
    assert result.stats["tested"] > 0
    assert result.stats["working"] > 0
    assert result.stats["final_count"] > 0

    # Verify output files were created
    summary_file = output_dir / "summary.json"
    clash_file = output_dir / "clash.yaml"
    singbox_file = output_dir / "singbox.json"

    assert summary_file.exists()
    assert clash_file.exists()
    assert singbox_file.exists()

    # Verify clash config has proxies
    clash_content = clash_file.read_text()
    assert "proxies:" in clash_content
    assert "proxy-groups:" in clash_content
