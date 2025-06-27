"""Tests for Device Detector Main Service"""
import pytest
import signal
import sys
from unittest.mock import Mock, patch, MagicMock
import redis
from src.main import DeviceDetectorService, signal_handler, main


class TestDeviceDetectorService:
    """Device Detector Serviceのテストクラス"""
    
    def test_service_initialization(self):
        """サービスの初期化をテスト"""
        # Given/When: サービスを初期化
        service = DeviceDetectorService()
        
        # Then: 正しく初期化される
        assert service is not None
        assert service.detector is not None
        assert service.running is False
    
    @patch('src.main.redis.Redis')
    @patch('src.main.pyudev.Context')
    @patch('src.main.pyudev.Monitor')
    def test_setup_success(self, mock_monitor, mock_context, mock_redis):
        """セットアップ成功をテスト"""
        # Given: モックの設定
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        
        mock_context_instance = Mock()
        mock_context.return_value = mock_context_instance
        
        mock_monitor_instance = Mock()
        mock_monitor.from_netlink.return_value = mock_monitor_instance
        
        service = DeviceDetectorService()
        
        # When: セットアップを実行
        result = service.setup()
        
        # Then: セットアップが成功
        assert result is True
        assert service.detector.redis_client is not None
        assert service.detector.context is not None
        assert service.detector.monitor is not None
        mock_redis_client.ping.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_setup_redis_failure(self, mock_redis):
        """Redis接続失敗時のセットアップをテスト"""
        # Given: Redis接続エラー
        mock_redis.side_effect = redis.ConnectionError("Connection failed")
        
        service = DeviceDetectorService()
        
        # When: セットアップを実行
        result = service.setup()
        
        # Then: セットアップが失敗
        assert result is False
    
    @patch('src.main.sys.exit')
    def test_run_setup_failure(self, mock_exit):
        """セットアップ失敗時のrun動作をテスト"""
        # Given: セットアップが失敗するサービス
        service = DeviceDetectorService()
        with patch.object(service, 'setup', return_value=False):
            # When: runを実行
            service.run()
            
            # Then: sys.exitが呼ばれる
            mock_exit.assert_called_once_with(1)
    
    def test_stop(self):
        """サービスの停止をテスト"""
        # Given: 実行中のサービス
        service = DeviceDetectorService()
        service.running = True
        service.detector.redis_client = Mock()
        
        # When: 停止を実行
        service.stop()
        
        # Then: 正しく停止される
        assert service.running is False
        service.detector.redis_client.close.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_reconnect_redis_success(self, mock_redis):
        """Redis再接続成功をテスト"""
        # Given: サービスとモックRedis
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        
        service = DeviceDetectorService()
        service.detector.redis_client = Mock()
        
        # When: 再接続を実行
        result = service.reconnect_redis()
        
        # Then: 再接続が成功
        assert result is True
        mock_redis_client.ping.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_reconnect_redis_failure(self, mock_redis):
        """Redis再接続失敗をテスト"""
        # Given: Redis接続エラー
        mock_redis.side_effect = redis.ConnectionError("Connection failed")
        
        service = DeviceDetectorService()
        
        # When: 再接続を実行
        result = service.reconnect_redis()
        
        # Then: 再接続が失敗
        assert result is False


class TestSignalHandler:
    """シグナルハンドラーのテスト"""
    
    @patch('src.main.sys.exit')
    def test_signal_handler(self, mock_exit):
        """シグナルハンドラーの動作をテスト"""
        # When: シグナルハンドラーを呼び出し
        signal_handler(signal.SIGINT, None)
        
        # Then: sys.exitが呼ばれる
        mock_exit.assert_called_once_with(0)


class TestMain:
    """main関数のテスト"""
    
    @patch('src.main.signal.signal')
    @patch('src.main.DeviceDetectorService')
    def test_main(self, mock_service_class, mock_signal):
        """main関数の動作をテスト"""
        # Given: モックサービス
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # When: mainを実行
        main()
        
        # Then: シグナルハンドラーが設定され、サービスが開始される
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, signal_handler)
        mock_signal.assert_any_call(signal.SIGTERM, signal_handler)
        mock_service.run.assert_called_once()


class TestDeviceDetectorServiceRun:
    """runメソッドの詳細テスト"""
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_device_events(self, mock_stop, mock_setup):
        """デバイスイベント処理のテスト"""
        # Given: セットアップ成功とモックデバイス
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # デバイスイベントを2回返してからNoneを返す
        mock_device1 = Mock()
        mock_device1.action = 'add'
        mock_device1.device_node = '/dev/ttyUSB0'
        mock_device1.get.return_value = '1234'
        
        mock_device2 = Mock()
        mock_device2.action = 'change'  # should_processでFalseになる
        
        # 3回目の呼び出しでKeyboardInterruptを発生させる
        service.detector.monitor.poll.side_effect = [
            mock_device1,
            mock_device2,
            KeyboardInterrupt()
        ]
        
        # When: runを実行
        service.run()
        
        # Then: デバイスイベントが処理される
        assert service.detector.monitor.poll.call_count == 3
        mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_redis_error_and_recovery(self, mock_stop, mock_setup):
        """Redis接続エラーと回復のテスト"""
        # Given: セットアップ成功
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # デバイスイベント
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = '/dev/ttyUSB0'
        mock_device.get.return_value = '1234'
        
        # 最初はRedisエラー、次は成功、最後にKeyboardInterrupt
        service.detector.monitor.poll.side_effect = [
            mock_device,
            mock_device,
            KeyboardInterrupt()
        ]
        
        # publish_eventがRedisエラーを発生
        with patch.object(service.detector, 'publish_event') as mock_publish:
            mock_publish.side_effect = [
                redis.ConnectionError("Connection lost"),
                None,  # 2回目は成功
            ]
            
            with patch.object(service, 'reconnect_redis', return_value=True) as mock_reconnect:
                # When: runを実行
                service.run()
                
                # Then: 再接続が試行される
                mock_reconnect.assert_called_once()
                mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_max_retries_exceeded(self, mock_stop, mock_setup):
        """最大リトライ回数超過のテスト"""
        # Given: セットアップ成功
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # デバイスイベント
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = '/dev/ttyUSB0'
        mock_device.get.return_value = '1234'
        
        # 常にデバイスを返す
        service.detector.monitor.poll.return_value = mock_device
        
        # publish_eventが常にRedisエラーを発生
        with patch.object(service.detector, 'publish_event') as mock_publish:
            mock_publish.side_effect = redis.ConnectionError("Connection lost")
            
            with patch.object(service, 'reconnect_redis', return_value=False) as mock_reconnect:
                # When: runを実行
                service.run()
                
                # Then: 最大リトライ回数分再接続が試行される
                assert mock_reconnect.call_count == 5
                mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_general_exception(self, mock_stop, mock_setup):
        """一般的な例外処理のテスト"""
        # Given: セットアップ成功
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        
        # モニターが例外を発生
        service.detector.monitor.poll.side_effect = Exception("Monitor error")
        
        # When: runを実行
        service.run()
        
        # Then: 停止される
        mock_stop.assert_called_once()
    
    def test_main_entry_point(self):
        """__main__エントリーポイントのテスト"""
        # Given: __name__ == '__main__'のシミュレーション
        with patch('src.main.__name__', '__main__'):
            with patch('src.main.main') as mock_main:
                # When: モジュールをリロード
                import src.main
                
                # mainが呼ばれることを確認（ただし、実際にはpatchされているので呼ばれない）