"""Tests for configstream package __init__ module."""

import sys

import pytest


def test_lazy_import_proxy():
    """Test lazy loading of Proxy class."""
    import configstream

    # Access Proxy through lazy loading
    Proxy = configstream.Proxy

    # Should be the actual Proxy class
    from configstream.models import Proxy as DirectProxy

    assert Proxy is DirectProxy


def test_lazy_import_singbox_tester():
    """Test lazy loading of SingBoxTester class."""
    import configstream

    # Access SingBoxTester through lazy loading
    SingBoxTester = configstream.SingBoxTester

    # Should be the actual SingBoxTester class
    from configstream.testers import SingBoxTester as DirectSingBoxTester

    assert SingBoxTester is DirectSingBoxTester


def test_lazy_import_parse_config():
    """Test lazy loading of parse_config function."""
    import configstream

    # Access parse_config through lazy loading
    parse_config = configstream.parse_config

    # Should be the actual parse_config function
    from configstream.core import parse_config as DirectParseConfig

    assert parse_config is DirectParseConfig


def test_lazy_import_run_full_pipeline():
    """Test lazy loading of run_full_pipeline function."""
    import configstream

    # Access run_full_pipeline through lazy loading
    run_full_pipeline = configstream.run_full_pipeline

    # Should be the actual run_full_pipeline function
    from configstream.pipeline import run_full_pipeline as DirectRunFullPipeline

    assert run_full_pipeline is DirectRunFullPipeline


def test_lazy_import_app_settings():
    """Test lazy loading of AppSettings class."""
    import configstream

    # Access AppSettings through lazy loading
    AppSettings = configstream.AppSettings

    # Should be the actual AppSettings class
    from configstream.config import AppSettings as DirectAppSettings

    assert AppSettings is DirectAppSettings


def test_lazy_import_invalid_attribute():
    """Test that invalid attribute raises AttributeError."""
    import configstream

    with pytest.raises(
        AttributeError, match="module 'configstream' has no attribute 'InvalidAttribute'"
    ):
        _ = configstream.InvalidAttribute


def test_version_and_author():
    """Test that version and author are available."""
    import configstream

    assert hasattr(configstream, "__version__")
    assert hasattr(configstream, "__author__")
    assert isinstance(configstream.__version__, str)
    assert isinstance(configstream.__author__, str)


def test_all_exports():
    """Test that __all__ exports are correct."""
    import configstream

    expected_exports = [
        "Proxy",
        "SingBoxTester",
        "parse_config",
        "run_full_pipeline",
        "AppSettings",
        "__version__",
        "__author__",
    ]

    assert configstream.__all__ == expected_exports


def test_windows_event_loop_policy():
    """Test Windows event loop policy is set on Windows platforms."""
    import asyncio

    import configstream  # noqa: F401

    # On Windows, the event loop policy should be WindowsSelectorEventLoopPolicy
    if sys.platform.startswith("win"):
        policy = asyncio.get_event_loop_policy()
        assert isinstance(policy, asyncio.WindowsSelectorEventLoopPolicy)
    else:
        # On non-Windows, should use default policy
        policy = asyncio.get_event_loop_policy()
        # Just verify we can get a policy without error
        assert policy is not None
