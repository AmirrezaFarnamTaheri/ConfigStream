import pytest
from unittest.mock import AsyncMock, patch
import json
import asyncio
from datetime import timedelta

from configstream.scheduler import RetestScheduler


@pytest.fixture
def mock_run_full_pipeline():
    """Fixture for a mock run_full_pipeline function."""
    with patch("configstream.scheduler.run_full_pipeline", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "success": True,
            "metrics": {
                "proxies_tested": 1,
                "proxies_working": 1,
            },
        }
        yield mock_run


@pytest.fixture
def proxies_file(tmp_path):
    """Fixture to create a temporary proxies file."""
    file_path = tmp_path / "proxies.json"
    proxy_data = [
        {"config": "vmess://config", "protocol": "vmess", "address": "test.com", "port": 443}
    ]
    file_path.write_text(json.dumps(proxy_data))
    return file_path


@pytest.mark.asyncio
async def test_retest_scheduler_run_once(mock_run_full_pipeline, proxies_file):
    """Test that the scheduler runs the pipeline once successfully."""
    scheduler = RetestScheduler(str(proxies_file))
    result = await scheduler.run_once()

    mock_run_full_pipeline.assert_called_once()
    assert result.success is True
    assert result.proxies_tested == 1
    assert result.proxies_working == 1


@pytest.mark.asyncio
async def test_retest_scheduler_proxies_file_not_found(mock_run_full_pipeline, tmp_path):
    """Test that the scheduler handles a missing proxies file."""
    non_existent_file = tmp_path / "non_existent.json"
    scheduler = RetestScheduler(str(non_existent_file))
    result = await scheduler.run_once()

    mock_run_full_pipeline.assert_not_called()
    assert result.success is False
    assert result.proxies_tested == 0
    assert result.proxies_working == 0


@pytest.mark.asyncio
async def test_retest_scheduler_empty_proxies_file(mock_run_full_pipeline, tmp_path):
    """Test that the scheduler handles an empty proxies file."""
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("[]")
    scheduler = RetestScheduler(str(empty_file))
    result = await scheduler.run_once()

    mock_run_full_pipeline.assert_not_called()
    assert result.success is False
    assert result.proxies_tested == 0
    assert result.proxies_working == 0


@pytest.mark.asyncio
async def test_retest_scheduler_start_and_stop(mock_run_full_pipeline, proxies_file):
    """Test that the scheduler can be started and stopped."""
    scheduler = RetestScheduler(str(proxies_file), interval=timedelta(milliseconds=1))

    with patch.object(scheduler, "run_once", new_callable=AsyncMock) as mock_run_once:
        scheduler.start()
        await asyncio.sleep(0.01)
        scheduler.stop()
        await asyncio.sleep(0.01)  # Allow task to cancel

        mock_run_once.assert_called()
        assert scheduler._task.done()


@pytest.mark.asyncio
async def test_retest_scheduler_start_already_running(mock_run_full_pipeline, proxies_file):
    """Test that starting an already running scheduler does nothing."""
    scheduler = RetestScheduler(str(proxies_file), interval=timedelta(milliseconds=1))

    with patch.object(scheduler, "_loop", new_callable=AsyncMock) as _mock_loop:  # noqa: F841
        scheduler.start()
        first_task = scheduler._task
        scheduler.start()  # Call start again
        second_task = scheduler._task

        assert first_task is second_task

        scheduler.stop()
        await asyncio.sleep(0.01)
