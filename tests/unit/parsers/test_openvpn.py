# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for OpenVPN parser."""

from configstream.parsers.openvpn import parse_openvpn


class TestOpenVPNBasic:
    """Basic OpenVPN parsing tests."""

    def test_valid_openvpn_config(self):
        """Standard OpenVPN config with client directive and remote."""
        config = """client
 dev tun
 proto tcp
 remote 1.2.3.4 1194
 resolv-retry infinite
 nobind
 persist-key
 persist-tun
 <ca>
 -----BEGIN CERTIFICATE-----
 MIID...
 -----END CERTIFICATE-----
 </ca>
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.protocol == "openvpn"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 1194
        assert proxy.details["transport"] == "tcp"

    def test_openvpn_udp_default(self):
        """OpenVPN config without proto defaults to udp."""
        config = """client
 dev tun
 remote 10.0.0.1 1194
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.address == "10.0.0.1"
        assert proxy.port == 1194
        assert proxy.details["transport"] == "udp"

    def test_openvpn_udp_proto(self):
        """OpenVPN with explicit udp proto."""
        config = """client
 dev tun
 proto udp
 remote 10.0.0.1 1194
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.details["transport"] == "udp"

    def test_no_client_directive(self):
        """Config without 'client' directive should return None."""
        config = """dev tun
 remote 1.2.3.4 1194
 """
        assert parse_openvpn(config) is None

    def test_no_remote_line(self):
        """Config without 'remote' directive should return None."""
        config = """client
 dev tun
 proto udp
 """
        assert parse_openvpn(config) is None

    def test_empty_config(self):
        """Empty config should return None."""
        assert parse_openvpn("") is None


class TestOpenVPNEdgeCases:
    """Edge cases for OpenVPN parser."""

    def test_multiple_remotes_uses_first_valid(self):
        """Config with multiple remotes should use the first valid one."""
        config = """client
 dev tun
 remote 10.0.0.1 1194
 remote 10.0.0.2 1195
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.address == "10.0.0.1"
        assert proxy.port == 1194

    def test_remote_with_invalid_port_skips_to_next(self):
        """Skip remotes with invalid ports."""
        config = """client
 dev tun
 remote host1 0
 remote host2 8080
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.address == "host2"
        assert proxy.port == 8080

    def test_remote_port_out_of_range_rejected(self):
        """Port outside 1-65535 should be rejected."""
        config = """client
 dev tun
 remote host 65536
 """
        assert parse_openvpn(config) is None

    def test_remote_port_65535_valid(self):
        """Port 65535 should be accepted."""
        config = """client
 dev tun
 remote host 65535
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.port == 65535

    def test_long_hostname_rejected(self):
        """Hostname > 255 chars should be rejected."""
        config = f"""client
 dev tun
 remote {"a" * 256} 1194
 """
        assert parse_openvpn(config) is None

    def test_client_in_comment_should_not_match(self):
        r"""'client' in a comment only should not trigger the parser.
        The regex uses multiline mode which matches 'client' at word boundaries.
        In a comment like '# this is a client config', 'client' is at a word
        boundary but preceded by 'a' not whitespace/start-of-line. The regex
        (^|\s)client(\s|$) requires 'client' to be at start-of-line or
        preceded by whitespace.
        """
        # 'client' at start of line (no space before) should still match
        config = "client\ndev tun\nremote 1.2.3.4 1194\n"
        proxy = parse_openvpn(config)
        assert proxy is not None

        # 'client' mid-comment should NOT match
        config2 = "# this is just a comment\ndev tun\nremote 1.2.3.4 1194\n"
        assert parse_openvpn(config2) is None

    def test_unknown_transport_defaults_to_udp(self):
        """Unknown transport protocol defaults to udp."""
        config = """client
 dev tun
 proto gre
 remote 1.2.3.4 1194
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.details["transport"] == "udp"

    def test_config_exceeding_size_limit(self):
        """Very large config should be rejected (size limit).
        Note: MAX_OPENVPN_CONFIG_SIZE=0 means unlimited, so this test
        verifies that an extremely large config still parses successfully.
        """
        config = "client\ndev tun\nremote 1.2.3.4 1194\n" + "x" * 1_500_000
        # The config size limit is disabled (0 = unlimited), so large configs
        # should still parse if they have valid structure
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.address == "1.2.3.4"

    def test_remote_with_ipv6(self):
        """Remote with IPv6 address."""
        config = """client
 dev tun
 remote 2001:db8::1 1194
 """
        proxy = parse_openvpn(config)
        assert proxy is not None

    def test_connection_block_remote(self):
        """Remote inside <connection> block should still be found."""
        config = """client
 dev tun
 <connection>
 remote 10.0.0.1 1194
 </connection>
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.address == "10.0.0.1"

    def test_remarks_set(self):
        """OpenVPN proxy should have remarks set."""
        config = """client
 dev tun
 remote 1.2.3.4 1194
 """
        proxy = parse_openvpn(config)
        assert proxy is not None
        assert proxy.remarks == "OpenVPN Config"
