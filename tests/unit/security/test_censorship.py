import pytest
from unittest.mock import MagicMock, patch
import requests
from src.configstream.security.censorship import CensorshipLab

@pytest.fixture
def lab():
    return CensorshipLab()

def test_initialization(lab):
    assert lab.results == {}
    assert len(lab.SENSITIVE_SITES) > 0

@patch('requests.get')
def test_check_connectivity_success(mock_get, lab):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    results = lab.check_connectivity(['https://example.com'])

    assert 'https://example.com' in results
    assert results['https://example.com']['status'] == 'reachable'
    assert results['https://example.com']['code'] == 200

@patch('requests.get')
def test_check_connectivity_failure(mock_get, lab):
    # Raise a requests exception which the code catches
    mock_get.side_effect = requests.RequestException("Connection refused")

    results = lab.check_connectivity(['https://example.com'])

    assert 'https://example.com' in results
    assert results['https://example.com']['status'] == 'blocked'

def test_report_generation(lab):
    lab.results = {
        'site1': {'status': 'reachable'},
        'site2': {'status': 'blocked'}
    }

    report = lab.get_censorship_report()

    assert report['total_sites'] == 2
    assert report['blocked_count'] == 1
    assert report['censorship_score'] == 50.0
