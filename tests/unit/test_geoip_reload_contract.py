# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import threading
from pathlib import Path

import pytest

import configstream.geoip as geoip_module
from configstream.config import AppSettings
from configstream.geoip import GeoData, GeoIPResolver


def _resolver_without_singleton() -> GeoIPResolver:
    resolver = object.__new__(GeoIPResolver)
    resolver.settings = AppSettings()
    resolver.reader_city = None
    resolver.reader_asn = None
    resolver._lookup_lock = None
    resolver._reader_lock = threading.RLock()
    resolver._last_mtime = 0.0
    resolver._last_asn_mtime = 0.0
    resolver._next_reload_check = 0.0
    resolver._uses_c_extension = True
    resolver._initialized = True
    return resolver


@pytest.mark.asyncio
async def test_c_extension_lookup_still_checks_for_database_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _resolver_without_singleton()
    reload_calls: list[bool] = []
    monkeypatch.setattr(geoip_module.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        resolver, "_check_reload_needed", lambda: reload_calls.append(True)
    )
    monkeypatch.setattr(resolver, "_do_lookup", lambda _ip: GeoData(country_code="US"))

    first = await resolver.lookup("1.1.1.1")
    second = await resolver.lookup("1.1.1.1")

    assert first.country_code == "US"
    assert second.country_code == "US"
    assert reload_calls == [True]


def test_database_load_resets_stale_mtimes_after_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolver = _resolver_without_singleton()
    resolver._last_mtime = 123.0
    resolver._last_asn_mtime = 456.0
    monkeypatch.setattr(
        resolver.settings, "GEOIP_CITY_DB_PATH", str(tmp_path / "missing-city.mmdb")
    )
    monkeypatch.setattr(
        resolver.settings, "GEOIP_ASN_DB_PATH", str(tmp_path / "missing-asn.mmdb")
    )

    resolver._load_databases()

    assert resolver.reader_city is None
    assert resolver.reader_asn is None
    assert resolver._last_mtime == 0.0
    assert resolver._last_asn_mtime == 0.0
