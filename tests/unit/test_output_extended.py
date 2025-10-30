"""Extended tests for output.py to improve coverage."""

import json
import tempfile
from pathlib import Path

import pytest

from configstream.models import Proxy
from configstream.output import generate_categorized_outputs


def test_generate_categorized_outputs_with_security_failures():
    """Test output generation with security-failed proxies."""
    # Create test proxies with security issues
    working_proxy = Proxy(
        config="vmess://test1",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="test-uuid-1",
        remarks="Working Proxy",
        country="US",
        country_code="us",
        city="New York",
        asn="AS15169",
        latency=100.0,
        is_working=True,
        is_secure=True,
        security_issues={},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    security_failed_proxy = Proxy(
        config="vmess://test2",
        protocol="vmess",
        address="192.168.1.1",
        port=8080,
        uuid="test-uuid-2",
        remarks="Security Failed",
        country="Unknown",
        country_code="unknown",
        city="Unknown",
        asn="Unknown",
        latency=None,
        is_working=False,
        is_secure=False,
        security_issues={"ADDRESS_PRIVATE": ["Private IP address"]},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    connectivity_failed_proxy = Proxy(
        config="vmess://test3",
        protocol="vmess",
        address="5.6.7.8",
        port=443,
        uuid="test-uuid-3",
        remarks="Connection Failed",
        country="Unknown",
        country_code="unknown",
        city="Unknown",
        asn="Unknown",
        latency=None,
        is_working=False,
        is_secure=True,
        security_issues={},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    proxies = [working_proxy, security_failed_proxy, connectivity_failed_proxy]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_files = generate_categorized_outputs(proxies, output_dir)

        # Verify working proxy output - should have protocol and country files
        assert "protocol_vmess" in output_files
        assert "country_us" in output_files
        vmess_path = Path(output_files["protocol_vmess"])
        assert vmess_path.exists()

        # Verify rejected directory was created
        rejected_dir = output_dir / "rejected"
        assert rejected_dir.exists()

        # Verify security category file was created
        assert "rejected_ADDRESS_PRIVATE" in output_files
        security_category_file = Path(output_files["rejected_ADDRESS_PRIVATE"])
        assert security_category_file.exists()

        # Verify all security issues file
        assert "rejected_security_all" in output_files
        all_security_file = Path(output_files["rejected_security_all"])
        assert all_security_file.exists()

        # Verify connectivity failed file
        assert "rejected_connectivity" in output_files
        connectivity_file = Path(output_files["rejected_connectivity"])
        assert connectivity_file.exists()

        # Verify summary file and its contents
        assert "summary" in output_files
        summary_path = Path(output_files["summary"])
        assert summary_path.exists()

        summary_data = json.loads(summary_path.read_text())
        assert summary_data["total_tested"] == 3
        assert summary_data["passed"] == 1
        assert summary_data["rejected"]["total_security_issues"] == 1
        assert summary_data["rejected"]["no_response"] == 1
        assert "ADDRESS_PRIVATE" in summary_data["rejected"]["security_by_category"]
        assert summary_data["rejected"]["security_by_category"]["ADDRESS_PRIVATE"] == 1


def test_generate_categorized_outputs_multiple_security_categories():
    """Test output generation with multiple security categories."""
    proxy1 = Proxy(
        config="vmess://test1",
        protocol="vmess",
        address="192.168.1.1",
        port=8080,
        uuid="test-uuid-1",
        remarks="Private IP",
        country="Unknown",
        country_code="unknown",
        city="Unknown",
        asn="Unknown",
        latency=None,
        is_working=False,
        is_secure=False,
        security_issues={"ADDRESS_PRIVATE": ["Private IP"]},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    proxy2 = Proxy(
        config="vmess://test2",
        protocol="vmess",
        address="1.2.3.4",
        port=23,
        uuid="test-uuid-2",
        remarks="Unsafe Port",
        country="Unknown",
        country_code="unknown",
        city="Unknown",
        asn="Unknown",
        latency=None,
        is_working=False,
        is_secure=False,
        security_issues={"PORT_UNSAFE": ["Dangerous port"]},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    proxies = [proxy1, proxy2]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_files = generate_categorized_outputs(proxies, output_dir)

        # Verify both security category files were created
        assert "rejected_ADDRESS_PRIVATE" in output_files
        assert "rejected_PORT_UNSAFE" in output_files

        rejected_dir = output_dir / "rejected"
        assert (rejected_dir / "ADDRESS_PRIVATE.json").exists()
        assert (rejected_dir / "PORT_UNSAFE.json").exists()

        # Verify summary has both categories
        summary_path = Path(output_files["summary"])
        summary_data = json.loads(summary_path.read_text())
        assert summary_data["rejected"]["security_by_category"]["ADDRESS_PRIVATE"] == 1
        assert summary_data["rejected"]["security_by_category"]["PORT_UNSAFE"] == 1


def test_generate_categorized_outputs_empty_list():
    """Test output generation with empty proxy list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_files = generate_categorized_outputs([], output_dir)

        # Should still create summary file
        assert "summary" in output_files
        summary_path = Path(output_files["summary"])
        assert summary_path.exists()

        summary_data = json.loads(summary_path.read_text())
        assert summary_data["total_tested"] == 0
        assert summary_data["passed"] == 0


def test_generate_categorized_outputs_all_working():
    """Test output generation with all working proxies."""
    working_proxy = Proxy(
        config="vmess://test1",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        uuid="test-uuid-1",
        remarks="Working Proxy",
        country="US",
        country_code="us",
        city="New York",
        asn="AS15169",
        latency=100.0,
        is_working=True,
        is_secure=True,
        security_issues={},
        tested_at="2025-01-01T00:00:00Z",
        details={},
    )

    proxies = [working_proxy]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_files = generate_categorized_outputs(proxies, output_dir)

        # Verify working proxy output exists
        assert "protocol_vmess" in output_files
        assert "country_us" in output_files
        assert Path(output_files["protocol_vmess"]).exists()
        assert Path(output_files["country_us"]).exists()

        # Rejected directory should not have security files
        rejected_dir = output_dir / "rejected"
        if rejected_dir.exists():
            security_files = list(rejected_dir.glob("*.json"))
            # Should be empty
            assert len(security_files) == 0

        # Verify summary
        summary_path = Path(output_files["summary"])
        summary_data = json.loads(summary_path.read_text())
        assert summary_data["total_tested"] == 1
        assert summary_data["passed"] == 1
        assert summary_data["rejected"]["total_security_issues"] == 0
        assert summary_data["rejected"]["no_response"] == 0
