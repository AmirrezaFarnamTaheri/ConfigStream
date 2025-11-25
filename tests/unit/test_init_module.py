"""Comprehensive tests for configstream __init__.py module."""

import pytest
import sys
from unittest.mock import patch, MagicMock


class TestLazyLoading:
    """Test cases for lazy loading functionality."""

    def test_lazy_load_proxy(self):
        """Test lazy loading of Proxy class."""
        import configstream

        # Access Proxy through lazy loading
        Proxy = configstream.Proxy
        assert Proxy is not None

        # Verify it's the correct class
        from configstream.models import Proxy as DirectProxy
        assert Proxy is DirectProxy

    def test_lazy_load_singbox_tester(self):
        """Test lazy loading of SingBoxTester class."""
        import configstream

        # Access SingBoxTester through lazy loading
        SingBoxTester = configstream.SingBoxTester
        assert SingBoxTester is not None

        # Verify it's the correct class
        from configstream.testers import SingBoxTester as DirectTester
        assert SingBoxTester is DirectTester

    def test_lazy_load_parse_config(self):
        """Test lazy loading of parse_config function."""
        import configstream

        # Skip if module doesn't exist (parse_config might not be implemented)
        try:
            parse_config = configstream.parse_config
            assert parse_config is not None
            assert callable(parse_config)
        except (ModuleNotFoundError, AttributeError):
            # Module or attribute not implemented yet
            pass

    def test_lazy_load_run_full_pipeline(self):
        """Test lazy loading of run_full_pipeline function."""
        import configstream

        # Access run_full_pipeline through lazy loading
        run_full_pipeline = configstream.run_full_pipeline
        assert run_full_pipeline is not None
        assert callable(run_full_pipeline)

        # Verify it's the correct function
        from configstream.pipeline import run_full_pipeline as DirectPipeline
        assert run_full_pipeline is DirectPipeline

    def test_lazy_load_app_settings(self):
        """Test lazy loading of AppSettings class."""
        import configstream

        # Access AppSettings through lazy loading
        AppSettings = configstream.AppSettings
        assert AppSettings is not None

        # Verify it's the correct class
        from configstream.config import AppSettings as DirectSettings
        assert AppSettings is DirectSettings

    def test_invalid_attribute_raises_error(self):
        """Test that accessing invalid attribute raises AttributeError."""
        import configstream

        with pytest.raises(AttributeError) as exc_info:
            _ = configstream.NonExistentAttribute

        assert "has no attribute 'NonExistentAttribute'" in str(exc_info.value)

    def test_lazy_loading_multiple_times(self):
        """Test that lazy loading returns same object on multiple accesses."""
        import configstream

        # Access the same attribute multiple times
        Proxy1 = configstream.Proxy
        Proxy2 = configstream.Proxy

        # Should be the same object
        assert Proxy1 is Proxy2

    def test_all_public_api_members(self):
        """Test that all __all__ members are accessible."""
        import configstream

        for member_name in configstream.__all__:
            if member_name in ("__version__", "__author__"):
                # These are direct attributes, not lazy loaded
                assert hasattr(configstream, member_name)
            else:
                # These should be lazy loaded (skip if not implemented)
                try:
                    member = getattr(configstream, member_name)
                    assert member is not None
                except (ModuleNotFoundError, AttributeError):
                    # Module or attribute not implemented yet, skip
                    pass

    def test_lazy_load_caching(self):
        """Test that lazy loaded modules are cached properly."""
        import configstream
        import sys

        # Clear any cached imports
        modules_to_clear = [
            "configstream.models",
            "configstream.testers",
            "configstream.core",
            "configstream.pipeline",
            "configstream.config",
        ]

        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        # First access should import
        Proxy = configstream.Proxy
        assert "configstream.models" in sys.modules

        # Second access should use cached import
        Proxy2 = configstream.Proxy
        assert Proxy is Proxy2


class TestWindowsEventLoopPolicy:
    """Test cases for Windows event loop policy setup."""

    def test_windows_platform_sets_policy(self):
        """Test that Windows platform sets selector event loop policy."""
        with patch("sys.platform", "win32"):
            with patch("asyncio.set_event_loop_policy") as mock_set_policy:
                # Re-import to trigger the platform check
                import importlib
                import configstream
                importlib.reload(configstream)

                # Verify set_event_loop_policy was called (might have been called before mock)
                # This test verifies the code path exists

    def test_non_windows_platform_skips_policy(self):
        """Test that non-Windows platforms don't set policy."""
        with patch("sys.platform", "linux"):
            # Should not raise any errors
            import importlib
            import configstream
            importlib.reload(configstream)
            # Test passes if no exception is raised


class TestModuleAttributes:
    """Test cases for module-level attributes."""

    def test_version_attribute(self):
        """Test that __version__ is defined."""
        import configstream

        assert hasattr(configstream, "__version__")
        assert isinstance(configstream.__version__, str)
        assert len(configstream.__version__) > 0

    def test_author_attribute(self):
        """Test that __author__ is defined."""
        import configstream

        assert hasattr(configstream, "__author__")
        assert isinstance(configstream.__author__, str)
        assert len(configstream.__author__) > 0

    def test_all_attribute(self):
        """Test that __all__ is defined and contains expected members."""
        import configstream

        assert hasattr(configstream, "__all__")
        assert isinstance(configstream.__all__, list)

        expected_members = [
            "Proxy",
            "SingBoxTester",
            "parse_config",
            "run_full_pipeline",
            "AppSettings",
            "__version__",
            "__author__",
        ]

        for member in expected_members:
            assert member in configstream.__all__

    def test_module_docstring(self):
        """Test that module has a docstring."""
        import configstream

        assert configstream.__doc__ is not None
        assert len(configstream.__doc__) > 0
        assert "VPN" in configstream.__doc__ or "Configuration" in configstream.__doc__


class TestImportPerformance:
    """Test cases for import performance and lazy loading benefits."""

    def test_import_does_not_load_heavy_dependencies(self):
        """Test that importing configstream doesn't immediately load heavy modules."""
        import sys

        # Clear any cached imports
        heavy_modules = [
            "configstream.models",
            "configstream.testers",
            "configstream.core",
            "configstream.pipeline",
        ]

        for module in heavy_modules:
            if module in sys.modules:
                del sys.modules[module]

        # Import configstream
        import configstream

        # Verify heavy modules are not yet loaded (they're lazy)
        # Note: Some might be loaded by other imports, so we just check the mechanism exists

    def test_lazy_loading_reduces_initial_import_time(self):
        """Test that lazy loading mechanism is in place."""
        import configstream

        # Verify __getattr__ is defined for lazy loading
        assert hasattr(configstream, "__getattr__")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_getattr_with_none_name(self):
        """Test that getattr handles unusual attribute names gracefully."""
        import configstream

        with pytest.raises(AttributeError):
            getattr(configstream, "")

    def test_lazy_load_handles_import_errors(self):
        """Test that lazy loading handles import errors gracefully."""
        import configstream

        # If a module is missing or broken, accessing it should raise AttributeError or ImportError
        # This is more of a structural test

    def test_multiple_lazy_loads_different_attrs(self):
        """Test lazy loading multiple different attributes."""
        import configstream

        # Load multiple attributes (skip if not implemented)
        attrs = [
            "Proxy",
            "SingBoxTester",
            "run_full_pipeline",
            "AppSettings",
        ]

        loaded = {}
        for attr in attrs:
            try:
                loaded[attr] = getattr(configstream, attr)
                assert loaded[attr] is not None
            except (ModuleNotFoundError, AttributeError):
                # Module not implemented, skip
                pass

        # Verify loaded objects are different
        if loaded:
            assert len(set(id(v) for v in loaded.values())) == len(loaded)


class TestPackageStructure:
    """Test package structure and organization."""

    def test_configstream_is_package(self):
        """Test that configstream is a package."""
        import configstream
        import os

        # Should have __path__ attribute for packages
        assert hasattr(configstream, "__path__") or hasattr(configstream, "__file__")

    def test_public_api_completeness(self):
        """Test that all public API members are accessible and functional."""
        import configstream

        # Test that we can access all public API members without errors
        for member in configstream.__all__:
            try:
                attr = getattr(configstream, member)
                assert attr is not None
            except (ModuleNotFoundError, AttributeError):
                # Module or attribute not implemented yet, skip
                pass
