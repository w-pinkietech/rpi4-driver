"""Tests for Device Detector - TDD RED phase"""
import pytest
import json
import time
from unittest.mock import Mock, patch
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
        assert detector.should_monitor_subsystem('tty') == True
        
        # USBデバイスは処理対象
        assert detector.should_monitor_subsystem('usb') == True
        
        # その他は処理対象外
        assert detector.should_monitor_subsystem('block') == False
        assert detector.should_monitor_subsystem('net') == False
    
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
        assert processed == True
        mock_redis.publish.assert_called_once()
        
        # 発行されたイベントの内容を確認
        call_args = mock_redis.publish.call_args
        published_data = json.loads(call_args[0][1])
        assert published_data['action'] == 'add'
        assert published_data['path'] == '/dev/ttyUSB0'