"""pytest configuration for device detector tests"""
import pytest
from unittest.mock import Mock, patch
import redis


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch('redis.Redis') as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_pyudev_context():
    """Mock pyudev Context for testing"""
    with patch('pyudev.Context') as mock_context:
        yield mock_context


@pytest.fixture
def mock_pyudev_monitor():
    """Mock pyudev Monitor for testing"""
    with patch('pyudev.Monitor') as mock_monitor:
        mock_monitor_instance = Mock()
        mock_monitor.from_netlink.return_value = mock_monitor_instance
        yield mock_monitor_instance


@pytest.fixture
def mock_device():
    """Mock pyudev Device for testing"""
    mock_device = Mock()
    mock_device.action = 'add'
    mock_device.device_node = '/dev/ttyUSB0'
    mock_device.properties = {
        'ID_VENDOR_ID': '1234',
        'ID_MODEL_ID': '5678',
        'DEVNAME': '/dev/ttyUSB0',
        'SUBSYSTEM': 'tty'
    }
    return mock_device