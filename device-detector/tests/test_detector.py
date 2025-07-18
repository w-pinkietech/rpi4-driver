"""Tests for Device Detector - TDD RED phase"""
import pytest
import json
import time
import redis
from unittest.mock import Mock, PropertyMock, patch
from src.detector import DeviceDetector


class TestDeviceDetector:
    """Device Detectorのテストクラス"""
    
    def test_detector_initialization(self, mock_redis):
        """デバイス検出器の初期化をテスト"""
        # Given: Redis hostが指定される
        redis_host = 'test-redis'
        
        # When: DeviceDetectorを初期化
        detector = DeviceDetector(redis_host=redis_host)
        
        # Then: 正しく初期化される
        assert detector is not None
        assert detector.redis_host == redis_host
    
    def test_parse_device_event(self, mock_device):
        """デバイスイベントのパースをテスト"""
        # Given: モックデバイスイベント
        detector = DeviceDetector()
        
        # When: デバイスイベントをパース
        event = detector.parse_event(mock_device)
        
        # Then: 正しいフォーマットのイベントが生成される
        assert event['action'] == 'add'
        assert event['path'] == '/dev/ttyUSB0'
        assert 'timestamp' in event
        assert 'properties' in event
        assert event['properties']['ID_VENDOR_ID'] == '1234'
    
    @pytest.mark.parametrize("action,expected", [
        ('add', True),
        ('remove', True),
        ('change', False),
        ('bind', False),
        ('unbind', False),
    ])
    def test_should_process_event(self, action, expected):
        """処理すべきイベントの判定をテスト"""
        detector = DeviceDetector()
        assert detector.should_process(action) == expected
    
    def test_filter_device_types(self):
        """デバイスタイプフィルタリングをテスト"""
        detector = DeviceDetector()
        
        # TTYデバイスは処理対象
        assert detector.should_monitor_subsystem('tty')
        
        # USBデバイスは処理対象
        assert detector.should_monitor_subsystem('usb')
        
        # その他は処理対象外
        assert not detector.should_monitor_subsystem('block')
        assert not detector.should_monitor_subsystem('net')
    
    def test_publish_event_to_redis(self, mock_redis):
        """Redisへのイベント発行をテスト"""
        # Given: DeviceDetectorとモックイベント
        detector = DeviceDetector()
        detector.redis_client = mock_redis
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {'ID_VENDOR_ID': '1234'}
        }
        
        # When: イベントを発行
        detector.publish_event(event_data)
        
        # Then: Redisにイベントが発行される
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        
        assert call_args[0][0] == 'device_events'  # チャンネル名
        published_data = json.loads(call_args[0][1])
        assert published_data['action'] == 'add'
        assert published_data['path'] == '/dev/ttyUSB0'
    
    def test_setup_monitor_filters(self, mock_pyudev_monitor):
        """モニターフィルターの設定をテスト"""
        # Given: DeviceDetectorとモックモニター
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        
        # When: モニターフィルターを設定
        detector.setup_monitor()
        
        # Then: 正しいフィルターが設定される
        mock_pyudev_monitor.filter_by.assert_any_call('tty')
        mock_pyudev_monitor.filter_by.assert_any_call('usb')
    
    def test_run_monitor_loop(self, mock_pyudev_monitor, mock_redis, mock_device):
        """モニターループの実行をテスト"""
        # Given: DeviceDetectorとモックデバイスイベント
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        # モニターが1回だけデバイスを返すように設定
        mock_pyudev_monitor.poll.return_value = mock_device
        
        # When: 1回のイベント処理をシミュレート
        processed = detector.process_single_event()
        
        # Then: イベントが正しく処理される
        assert processed
        mock_redis.publish.assert_called_once()
        
        # 発行されたイベントの内容を確認
        call_args = mock_redis.publish.call_args
        published_data = json.loads(call_args[0][1])
        assert published_data['action'] == 'add'
        assert published_data['path'] == '/dev/ttyUSB0'
    
    def test_parse_event_error_handling(self):
        """Test device event parsing error handling"""
        # Given: Device object that raises error when time.time() fails (simulated)
        detector = DeviceDetector()
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = '/dev/ttyUSB0'
        mock_device.properties = {}
        
        # Patch time.time to raise an exception
        with patch('src.detector.time.time', side_effect=RuntimeError("Time error")):
            # When/Then: Exception occurs during parsing
            with pytest.raises(RuntimeError):
                detector.parse_event(mock_device)
    
    def test_publish_event_without_redis_client(self):
        """Test event publishing without Redis client"""
        # Given: Detector without Redis client configured
        detector = DeviceDetector()
        detector.redis_client = None
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {}
        }
        
        # When/Then: No exception occurs, warning log is output
        detector.publish_event(event_data)  # Should not raise exception
    
    def test_publish_event_redis_connection_error(self, mock_redis):
        """Test event publishing during Redis connection error"""
        # Given: Configuration that triggers Redis connection error
        detector = DeviceDetector()
        mock_redis.publish.side_effect = redis.ConnectionError("Connection lost")
        detector.redis_client = mock_redis
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {}
        }
        
        # When/Then: ConnectionError is re-raised
        with pytest.raises(redis.ConnectionError):
            detector.publish_event(event_data)
    
    def test_process_single_event_without_monitor(self):
        """Test event processing without monitor"""
        # Given: Detector without initialized monitor
        detector = DeviceDetector()
        detector.monitor = None
        
        # When: Attempt event processing
        result = detector.process_single_event()
        
        # Then: False is returned
        assert result is False
    
    def test_process_single_event_error_handling(self, mock_pyudev_monitor, mock_redis):
        """Test error handling during event processing"""
        # Given: Monitor that raises errors
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        mock_pyudev_monitor.poll.side_effect = RuntimeError("Monitor error")
        
        # When/Then: Exception is re-raised
        with pytest.raises(RuntimeError):
            detector.process_single_event()
    
    def test_publish_event_json_error(self, mock_redis):
        """Test JSON serialization error for events"""
        # Given: Data that cannot be JSON serialized
        detector = DeviceDetector()
        detector.redis_client = mock_redis
        
        # Mock json.dumps to raise exception
        import json
        original_dumps = json.dumps
        json.dumps = Mock(side_effect=TypeError("JSON serialize error"))
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {}
        }
        
        try:
            # When/Then: TypeError occurs
            with pytest.raises(TypeError):
                detector.publish_event(event_data)
        finally:
            # Restore original json.dumps
            json.dumps = original_dumps
    
    def test_process_single_event_poll_error(self, mock_pyudev_monitor, mock_redis):
        """Test monitor poll error"""
        # Given: Monitor that raises exception on poll
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        # poll raises specific exception
        mock_pyudev_monitor.poll.side_effect = RuntimeError("Poll error")
        
        # When/Then: RuntimeError is re-raised
        with pytest.raises(RuntimeError):
            detector.process_single_event()
    
    def test_process_single_event_no_device(self, mock_pyudev_monitor, mock_redis):
        """Test event processing when no device is available"""
        # Given: Monitor that returns None on poll
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        # Configure poll to return None
        mock_pyudev_monitor.poll.return_value = None
        
        # When: Execute event processing
        result = detector.process_single_event()
        
        # Then: False is returned and Redis publish is not called
        assert result is False
        mock_redis.publish.assert_not_called()