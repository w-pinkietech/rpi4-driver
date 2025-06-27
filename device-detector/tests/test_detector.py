"""Tests for Device Detector - TDD RED phase"""
import pytest
import json
import time
import redis
from unittest.mock import Mock
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
        """デバイスイベントのパースエラーをテスト"""
        # Given: 不正なデバイスオブジェクト
        detector = DeviceDetector()
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = None  # Noneを設定してエラーを発生させる
        mock_device.properties = Mock(side_effect=Exception("Property error"))
        
        # When/Then: パース時に例外が発生
        with pytest.raises(Exception):
            detector.parse_event(mock_device)
    
    def test_publish_event_without_redis_client(self):
        """Redisクライアントなしでのイベント発行をテスト"""
        # Given: Redisクライアントが設定されていないDetector
        detector = DeviceDetector()
        detector.redis_client = None
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {}
        }
        
        # When/Then: 例外は発生せず、警告ログが出力される
        detector.publish_event(event_data)  # Should not raise exception
    
    def test_publish_event_redis_connection_error(self, mock_redis):
        """Redis接続エラー時のイベント発行をテスト"""
        # Given: Redis接続エラーを発生させる設定
        detector = DeviceDetector()
        mock_redis.publish.side_effect = redis.ConnectionError("Connection lost")
        detector.redis_client = mock_redis
        
        event_data = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {}
        }
        
        # When/Then: ConnectionErrorが再発生
        with pytest.raises(redis.ConnectionError):
            detector.publish_event(event_data)
    
    def test_process_single_event_without_monitor(self):
        """モニターなしでのイベント処理をテスト"""
        # Given: モニターが初期化されていないDetector
        detector = DeviceDetector()
        detector.monitor = None
        
        # When: イベント処理を試行
        result = detector.process_single_event()
        
        # Then: Falseが返される
        assert result is False
    
    def test_process_single_event_error_handling(self, mock_pyudev_monitor, mock_redis):
        """イベント処理中のエラーをテスト"""
        # Given: エラーを発生させるモニター
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        mock_pyudev_monitor.poll.side_effect = Exception("Monitor error")
        
        # When/Then: 例外が再発生
        with pytest.raises(Exception):
            detector.process_single_event()
    
    def test_publish_event_json_error(self, mock_redis):
        """イベントのJSONシリアライズエラーをテスト"""
        # Given: JSONシリアライズできないデータ
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
            # When/Then: TypeErrorが発生
            with pytest.raises(TypeError):
                detector.publish_event(event_data)
        finally:
            # Restore original json.dumps
            json.dumps = original_dumps
    
    def test_process_single_event_poll_error(self, mock_pyudev_monitor, mock_redis):
        """モニターのpollエラーをテスト"""
        # Given: pollで例外を発生させるモニター
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        # pollが特定の例外を発生させる
        mock_pyudev_monitor.poll.side_effect = RuntimeError("Poll error")
        
        # When/Then: RuntimeErrorが再発生
        with pytest.raises(RuntimeError):
            detector.process_single_event()
    
    def test_process_single_event_no_device(self, mock_pyudev_monitor, mock_redis):
        """デバイスがない場合のイベント処理をテスト"""
        # Given: pollがNoneを返すモニター
        detector = DeviceDetector()
        detector.monitor = mock_pyudev_monitor
        detector.redis_client = mock_redis
        
        # pollがNoneを返すように設定
        mock_pyudev_monitor.poll.return_value = None
        
        # When: イベント処理を実行
        result = detector.process_single_event()
        
        # Then: Falseが返され、Redis発行は呼ばれない
        assert result is False
        mock_redis.publish.assert_not_called()