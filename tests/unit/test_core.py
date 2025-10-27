import unittest
from unittest.mock import MagicMock, patch
from configstream.core import (
    _infer_country_from_remarks,
    geolocate_proxy,
    parse_config,
    parse_config_batch,
    _lookup_geoip_http,
)
from configstream.models import Proxy
import asyncio
import geoip2.errors
import httpx

class TestCore(unittest.TestCase):
    def test_infer_country_from_remarks_with_flag(self):
        # Test with a flag emoji
        remarks = '🇺🇸 US Server'
        result = _infer_country_from_remarks(remarks)
        self.assertEqual(result, {'country_code': 'US', 'country': 'United States'})

    def test_infer_country_from_remarks_with_country_code(self):
        # Test with a country code
        remarks = 'US Server'
        result = _infer_country_from_remarks(remarks)
        self.assertEqual(result, {'country_code': 'US', 'country': 'United States'})

    def test_infer_country_from_remarks_with_no_country(self):
        # Test with no country information
        remarks = 'Test Server'
        result = _infer_country_from_remarks(remarks)
        self.assertIsNone(result)

    def test_geolocate_proxy_with_valid_country_code(self):
        async def run_test():
            # Create a proxy with a valid country code
            proxy = Proxy(country_code='US', config='ss://dummy', protocol='ss', port=12345, address='1.2.3.4')
            # Call the function to be tested
            await geolocate_proxy(proxy)
            # Assert that the proxy's country is correctly updated
            self.assertEqual(proxy.country, 'United States')

        asyncio.run(run_test())

    @patch('geoip2.database.Reader')
    def test_geolocate_proxy_with_real_ip(self, mock_reader):
        async def run_test():
            # Create a mock GeoIP2 reader
            mock_reader.return_value.city.return_value.country.iso_code = 'US'
            mock_reader.return_value.city.return_value.country.name = 'United States'
            mock_reader.return_value.city.return_value.city.name = 'Mountain View'
            # Create a proxy with a real IP address
            proxy = Proxy(address='8.8.8.8', config='ss://dummy', protocol='ss', port=12345)
            # Call the function to be tested
            await geolocate_proxy(proxy, mock_reader.return_value)
            # Assert that the proxy's location is correctly updated
            self.assertEqual(proxy.country_code, 'US')
            self.assertEqual(proxy.country, 'United States')
            self.assertEqual(proxy.city, 'Mountain View')

        asyncio.run(run_test())

    def test_parse_config_with_valid_config(self):
        # Create a valid proxy configuration
        config = 'ss://chacha20-ietf-poly1305:password@1.2.3.4:12345'
        # Call the function to be tested
        proxy = parse_config(config)
        # Assert that the proxy is correctly parsed
        self.assertEqual(proxy.protocol, 'shadowsocks')
        self.assertEqual(proxy.address, '1.2.3.4')
        self.assertEqual(proxy.port, 12345)

    def test_parse_config_with_invalid_config(self):
        # Create an invalid proxy configuration
        config = 'invalid-config'
        # Call the function to be tested
        proxy = parse_config(config)
        # Assert that the function returns None
        self.assertIsNone(proxy)

    def test_parse_config_batch(self):
        # Create a list of proxy configurations
        configs = [
            'ss://chacha20-ietf-poly1305:password@1.2.3.4:12345',
            'invalid-config',
            'vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICIiLAogICJhZGQiOiAiMS5yb3V0ZXIud29ybGQiLAogICJwb3J0IjogIjQ0MyIsCiAgImlkIjogIjNkYjM2Y2QyLWU3ZDEtNGI2ZC1hY2EzLTYwMDIxMDI3YzA2YiIsCiAgImFpZCI6ICIwIiwKICAibmV0IjogIndzIiwKICAidHlwZSI6ICJub25lIiwKICAiaG9zdCI6ICIxLnJvdXRlci53b3JsZCIsCiAgInBhdGgiOiAiL2FyaWVzIiwKICAidGxzIjogInRscyIKfQo=',
        ]
        # Call the function to be tested
        proxies = parse_config_batch(configs)
        # Assert that the function returns the correct number of proxies
        self.assertEqual(len(proxies), 2)
        self.assertEqual(proxies[0].protocol, 'shadowsocks')
        self.assertEqual(proxies[1].protocol, 'vmess')

    @patch('configstream.core.get_client')
    def test_lookup_geoip_http_with_valid_ip(self, mock_get_client):
        async def run_test():
            # Create a mock HTTP client
            mock_client = unittest.mock.AsyncMock()
            mock_client.__aenter__.return_value.get.return_value.json.return_value = {
                'status': 'success',
                'country': 'United States',
                'countryCode': 'US',
                'city': 'Mountain View',
            }
            mock_get_client.return_value = mock_client
            # Call the function to be tested
            result = await _lookup_geoip_http('8.8.8.8')
            # Assert that the function returns the correct location
            self.assertEqual(result, {
                'country': 'United States',
                'country_code': 'US',
                'city': 'Mountain View',
                'asn': None
            })

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()