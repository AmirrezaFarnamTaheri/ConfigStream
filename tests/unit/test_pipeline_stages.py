# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.pipeline.producer import source_producer
from configstream.pipeline.consumer import processing_consumer
from configstream.pipeline_stats import PipelineStats, PipelineResult
from configstream.models import Proxy
from configstream.fetcher_worker import FetchResult


@pytest.fixture
def mock_dependencies():
    queue = asyncio.Queue()
    quality = MagicMock()
    quality.should_fetch.return_value = True
    anomaly = MagicMock()
    anomaly.is_safe.return_value = (True, "Safe")

    tester = MagicMock()
    tester.go_tester.available = False
    tester.test = AsyncMock()  # For python fallback
    tester.test_batch = AsyncMock()  # For go tester

    scheduler = MagicMock()
    scheduler.should_retest.return_value = True  # Force retest by default

    test_cache = MagicMock()
    test_cache.get.return_value = None

    concurrency = MagicMock()
    concurrency.start_tuner = MagicMock()
    concurrency.stop_tuner = AsyncMock()
    concurrency.get_semaphore.return_value = AsyncMock()
    concurrency.record = AsyncMock()

    # Make semaphore a context manager
    sem = AsyncMock()
    sem.__aenter__.return_value = None
    sem.__aexit__.return_value = None
    concurrency.get_semaphore.return_value = sem

    geoip = MagicMock()
    # Return a plain object with string attributes — not a bare MagicMock —
    # so that Pydantic's validate_assignment does not reject MagicMock values
    # when the consumer assigns p.country / p.city / p.asn / p.org (P1-4 fix).
    _geo_result = MagicMock(spec=[
        "country_code", "country_name", "city", "asn", "org",
    ])
    _geo_result.country_code = "US"
    _geo_result.country_name = "United States"
    _geo_result.city = "TestCity"
    _geo_result.asn = "123"
    _geo_result.org = "TestOrg"
    geoip.lookup = AsyncMock(return_value=_geo_result)

    tracker = MagicMock()
    tracker.phase.return_value = MagicMock()
    tracker.phase.return_value.__enter__.return_value = None
    tracker.phase.return_value.__exit__.return_value = None

    history = MagicMock()
    history.record_test_result = MagicMock()

    return {
        "queue": queue,
        "quality": quality,
        "anomaly": anomaly,
        "tester": tester,
        "scheduler": scheduler,
        "test_cache": test_cache,
        "concurrency": concurrency,
        "geoip": geoip,
        "tracker": tracker,
        "history": history,
    }


@pytest.mark.asyncio
async def test_pipeline_stats():
    s = PipelineStats()
    d = s.to_dict()
    assert d["fetched_sources"] == 0

    res = PipelineResult(True, s, {}, None)
    assert res.success


@pytest.mark.asyncio
async def test_source_producer_supplied_proxies(mock_dependencies):
    queue = mock_dependencies["queue"]
    p = Proxy(protocol="vmess", address="1.1.1.1", port=80, config="vmess://test")

    await source_producer(
        sources=[],
        work_queue=queue,
        proxies=[p],
        quality_tracker=mock_dependencies["quality"],
        anomaly_detector=mock_dependencies["anomaly"],
        event_stream=None,
        progress=None,
        task_fetch=None,
    )

    item = await queue.get()
    assert item[0] == "supplied-proxies"
    assert "vmess://test" in item[1]


@pytest.mark.asyncio
async def test_source_producer_local_files(mock_dependencies):
    queue = mock_dependencies["queue"]
    sources = ["sources/batch_1.txt"]

    with patch("configstream.producer.read_multiple_files_async") as mock_read:
        mock_read.return_value = [("sources/batch_1.txt", "vmess://file")]

        await source_producer(
            sources=sources,
            work_queue=queue,
            proxies=None,
            quality_tracker=mock_dependencies["quality"],
            anomaly_detector=mock_dependencies["anomaly"],
            event_stream=None,
            progress=None,
            task_fetch=None,
        )

    item = await queue.get()
    assert item[0] == "sources/batch_1.txt"
    assert "vmess://file" in item[1]


@pytest.mark.asyncio
async def test_source_producer_remote_urls(mock_dependencies):
    queue = mock_dependencies["queue"]
    sources = [
        "http://web.com/sub",
        "ssconf://web.com/sub2",
        "ss://direct-config",
        "vmess://direct-config",
    ]

    # Mock fetcher
    with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:
        mock_fetch.return_value = {
            "http://web.com/sub": FetchResult(True, "s1", content="vmess://line1"),
            "https://web.com/sub2": FetchResult(True, "s2", content="vmess://line2"),
        }

        # Mock read_multiple_files_async to prevent it from trying to read ss:// as file and logging warnings
        with patch(
            "configstream.producer.read_multiple_files_async",
            return_value=[],
        ):
            await source_producer(
                sources=sources,
                work_queue=queue,
                proxies=None,
                quality_tracker=mock_dependencies["quality"],
                anomaly_detector=mock_dependencies["anomaly"],
                event_stream=None,
                progress=None,
                task_fetch=None,
            )

    items = []
    while not queue.empty():
        i = await queue.get()
        if i is not None:
            items.append(i)

    # Check direct config
    direct = next((i for i in items if i[0] == "supplied-config"), None)
    assert direct is not None
    assert "ss://direct-config" in direct[1]

    # Check fetched
    fetched1 = next((i for i in items if i[0] == "http://web.com/sub"), None)
    assert fetched1 is not None

    # Check ssconf converted
    fetched2 = next((i for i in items if i[0] == "https://web.com/sub2"), None)
    assert fetched2 is not None


@pytest.mark.asyncio
async def test_source_producer_anomaly_block(mock_dependencies):
    queue = mock_dependencies["queue"]
    sources = ["http://bad.com"]

    mock_dependencies["anomaly"].is_safe.return_value = (False, "Malicious")

    with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:
        mock_fetch.return_value = {
            "http://bad.com": FetchResult(True, "s1", content="bad-line")
        }

        await source_producer(
            sources=sources,
            work_queue=queue,
            proxies=None,
            quality_tracker=mock_dependencies["quality"],
            anomaly_detector=mock_dependencies["anomaly"],
            event_stream=None,
            progress=None,
            task_fetch=None,
            stop_event=asyncio.Event(),
        )

    # Queue should only contain None (sentinel)
    item = await queue.get()
    assert item is None


@pytest.mark.asyncio
async def test_processing_consumer_basic_flow(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    # Add work item
    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)  # Sentinel

    # Mock parse_config to return a valid proxy
    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")
    with patch("configstream.consumer.parse_config", return_value=p):
        # Mock tester to succeed
        res = Proxy(
            protocol="vmess", address="1.2.3.4", port=443, config="vmess://test"
        )
        res.latency = 100
        res.is_working = True
        mock_dependencies["tester"].test.return_value = res

        # Mock validate_batch_configs
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 1
    assert stats.working == 1
    assert final_proxies[0].country_code == "US"  # From GeoIP mock


@pytest.mark.asyncio
async def test_processing_consumer_cached_hit(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)

    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")
    cached_p = p.model_copy()
    cached_p.is_working = True
    cached_p.latency = 50

    # Simulate retest FALSE -> Cache HIT
    mock_dependencies["scheduler"].should_retest.return_value = False
    mock_dependencies["test_cache"].get.return_value = cached_p

    with patch("configstream.consumer.parse_config", return_value=p):
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 1
    assert stats.tested == 0  # Was cached
    assert final_proxies[0].latency == 50


@pytest.mark.asyncio
async def test_processing_consumer_cache_miss(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)

    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")

    # Simulate retest FALSE but Cache MISS -> Retest
    mock_dependencies["scheduler"].should_retest.return_value = False
    mock_dependencies["test_cache"].get.return_value = None

    res = p.model_copy()
    res.is_working = True
    res.latency = 100
    mock_dependencies["tester"].test.return_value = res

    with patch("configstream.consumer.parse_config", return_value=p):
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 1
    assert stats.cache_misses == 1
    assert stats.tested == 1


@pytest.mark.asyncio
async def test_processing_consumer_go_tester(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)

    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")

    # Enable Go Tester
    mock_dependencies["tester"].go_tester.available = True

    # Mock test_batch updates objects in place
    async def side_effect(batch):
        for x in batch:
            x.is_working = True
            x.latency = 20

    mock_dependencies["tester"].test_batch.side_effect = side_effect

    with patch("configstream.consumer.parse_config", return_value=p):
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 1
    assert stats.tested == 1


@pytest.mark.asyncio
async def test_processing_consumer_filters(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)

    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")

    # Mock Python tester returns working but HIGH latency
    res = p.model_copy()
    res.is_working = True
    res.latency = 5000
    mock_dependencies["tester"].test.return_value = res

    with patch("configstream.consumer.parse_config", return_value=p):
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=2000,  # Latency Filter
                country_filter=None,
                leniency=False,
            )

    assert len(final_proxies) == 0  # Filtered by latency
    assert stats.working == 0


@pytest.mark.asyncio
async def test_processing_consumer_country_filter(mock_dependencies):
    queue = mock_dependencies["queue"]
    stats = PipelineStats()
    seen_keys = set()
    final_proxies = []

    await queue.put(("test-source", ["vmess://test"]))
    await queue.put(None)

    p = Proxy(protocol="vmess", address="1.2.3.4", port=443, config="vmess://test")

    res = p.model_copy()
    res.is_working = True
    res.latency = 100
    mock_dependencies["tester"].test.return_value = res

    # GeoIP returns US
    _geo_cn = MagicMock(spec=["country_code", "country_name", "city", "asn", "org"])
    _geo_cn.country_code = "US"
    _geo_cn.country_name = "United States"
    _geo_cn.city = ""
    _geo_cn.asn = ""
    _geo_cn.org = ""
    mock_dependencies["geoip"].lookup = AsyncMock(return_value=_geo_cn)

    with patch("configstream.consumer.parse_config", return_value=p):
        with patch(
            "configstream.consumer.validate_batch_configs",
            return_value=[p],
        ):
            await processing_consumer(
                work_queue=queue,
                stats=stats,
                seen_keys=seen_keys,
                final_proxies=final_proxies,
                tester=mock_dependencies["tester"],
                scheduler=mock_dependencies["scheduler"],
                test_cache=mock_dependencies["test_cache"],
                concurrency=mock_dependencies["concurrency"],
                geoip=mock_dependencies["geoip"],
                tracker=mock_dependencies["tracker"],
                event_stream=None,
                quality_tracker=mock_dependencies["quality"],
                history=mock_dependencies["history"],
                progress=None,
                task_process=None,
                max_latency=None,
                country_filter="CN",  # Filter for CN
                leniency=False,
            )

    assert len(final_proxies) == 0  # Filtered by latency
