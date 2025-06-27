"""Tests for Device Detector Main Service"""
import signal
from unittest.mock import Mock, patch
import redis
from src.main import DeviceDetectorService, signal_handler, main


class TestDeviceDetectorService:
    """Test class for Device Detector Service"""
    
    def test_service_initialization(self):
        """Test service initialization"""
        # Given/When: Initialize service
        service = DeviceDetectorService()
        
        # Then: Service is correctly initialized
        assert service is not None
        assert service.detector is not None
        assert service.running is False
        assert service.max_retries == 5  # Default value
    
    @patch('src.main.redis.Redis')
    @patch('src.main.pyudev.Context')
    @patch('src.main.pyudev.Monitor')
    def test_setup_success(self, mock_monitor, mock_context, mock_redis):
        """Test successful setup"""
        # Given: Mock configuration
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        
        mock_context_instance = Mock()
        mock_context.return_value = mock_context_instance
        
        mock_monitor_instance = Mock()
        mock_monitor.from_netlink.return_value = mock_monitor_instance
        
        service = DeviceDetectorService()
        
        # When: Execute setup
        result = service.setup()
        
        # Then: Setup succeeds
        assert result is True
        assert service.detector.redis_client is not None
        assert service.detector.context is not None
        assert service.detector.monitor is not None
        mock_redis_client.ping.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_setup_redis_failure(self, mock_redis):
        """Test setup during Redis connection failure"""
        # Given: Redis connection error
        mock_redis.side_effect = redis.ConnectionError("Connection failed")
        
        service = DeviceDetectorService()
        
        # When: Execute setup
        result = service.setup()
        
        # Then: Setup fails
        assert result is False
    
    @patch('src.main.sys.exit')
    def test_run_setup_failure(self, mock_exit):
        """Test run behavior when setup fails"""
        # Given: Service with failing setup
        service = DeviceDetectorService()
        with patch.object(service, 'setup', return_value=False):
            # When: Execute run
            service.run()
            
            # Then: sys.exit is called
            mock_exit.assert_called_once_with(1)
    
    def test_stop(self):
        """Test service stop"""
        # Given: Running service
        service = DeviceDetectorService()
        service.running = True
        service.detector.redis_client = Mock()
        
        # When: Execute stop
        service.stop()
        
        # Then: Service is correctly stopped
        assert service.running is False
        service.detector.redis_client.close.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_reconnect_redis_success(self, mock_redis):
        """Test successful Redis reconnection"""
        # Given: Service and mock Redis
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        
        service = DeviceDetectorService()
        service.detector.redis_client = Mock()
        
        # When: Execute reconnection
        result = service.reconnect_redis()
        
        # Then: Reconnection succeeds
        assert result is True
        mock_redis_client.ping.assert_called_once()
    
    @patch('src.main.redis.Redis')
    def test_reconnect_redis_failure(self, mock_redis):
        """Test Redis reconnection failure"""
        # Given: Redis connection error
        mock_redis.side_effect = redis.ConnectionError("Connection failed")
        
        service = DeviceDetectorService()
        
        # When: Execute reconnection
        result = service.reconnect_redis()
        
        # Then: Reconnection fails
        assert result is False


class TestSignalHandler:
    """Test class for signal handler"""
    
    @patch('src.main.sys.exit')
    def test_signal_handler(self, mock_exit):
        """Test signal handler behavior"""
        # When: Call signal handler
        signal_handler(signal.SIGINT, None)
        
        # Then: sys.exit is called
        mock_exit.assert_called_once_with(0)


class TestMain:
    """Test class for main function"""
    
    @patch('src.main.signal.signal')
    @patch('src.main.DeviceDetectorService')
    def test_main(self, mock_service_class, mock_signal):
        """Test main function behavior"""
        # Given: Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # When: Execute main
        main()
        
        # Then: Signal handlers are configured and service is started
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, signal_handler)
        mock_signal.assert_any_call(signal.SIGTERM, signal_handler)
        mock_service.run.assert_called_once()


class TestDeviceDetectorServiceRun:
    """Detailed tests for run method"""
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_device_events(self, mock_stop, mock_setup):
        """Test device event processing"""
        # Given: Successful setup and mock devices
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # Return device events twice then None
        mock_device1 = Mock()
        mock_device1.action = 'add'
        mock_device1.device_node = '/dev/ttyUSB0'
        mock_device1.get.return_value = '1234'
        mock_device1.properties = {}
        
        mock_device2 = Mock()
        mock_device2.action = 'change'  # should_process returns False
        mock_device2.properties = {}
        
        # Trigger KeyboardInterrupt on third call
        service.detector.monitor.poll.side_effect = [
            mock_device1,
            mock_device2,
            KeyboardInterrupt()
        ]
        
        # When: Execute run
        service.run()
        
        # Then: Device events are processed
        assert service.detector.monitor.poll.call_count == 3
        mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_redis_error_and_recovery(self, mock_stop, mock_setup):
        """Test Redis connection error and recovery"""
        # Given: Successful setup
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # Device event
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = '/dev/ttyUSB0'
        mock_device.get.return_value = '1234'
        mock_device.properties = {}
        
        # First Redis error, then success, finally KeyboardInterrupt
        service.detector.monitor.poll.side_effect = [
            mock_device,
            mock_device,
            KeyboardInterrupt()
        ]
        
        # publish_event raises Redis error
        with patch.object(service.detector, 'publish_event') as mock_publish:
            mock_publish.side_effect = [
                redis.ConnectionError("Connection lost"),
                None,  # Second attempt succeeds
            ]
            
            with patch.object(service, 'reconnect_redis', return_value=True) as mock_reconnect:
                # When: Execute run
                service.run()
                
                # Then: Reconnection is attempted
                mock_reconnect.assert_called_once()
                mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_max_retries_exceeded(self, mock_stop, mock_setup):
        """Test maximum retry count exceeded"""
        # Given: Successful setup
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        service.detector.redis_client = Mock()
        
        # Device event
        mock_device = Mock()
        mock_device.action = 'add'
        mock_device.device_node = '/dev/ttyUSB0'
        mock_device.get.return_value = '1234'
        mock_device.properties = {}
        
        # Always return device
        service.detector.monitor.poll.return_value = mock_device
        
        # publish_event always raises Redis error
        with patch.object(service.detector, 'publish_event') as mock_publish:
            mock_publish.side_effect = redis.ConnectionError("Connection lost")
            
            with patch.object(service, 'reconnect_redis', return_value=False) as mock_reconnect:
                # When: Execute run
                service.run()
                
                # Then: Reconnection is attempted max retry times
                assert mock_reconnect.call_count == 5
                mock_stop.assert_called_once()
    
    @patch('src.main.DeviceDetectorService.setup')
    @patch('src.main.DeviceDetectorService.stop')
    def test_run_with_general_exception(self, mock_stop, mock_setup):
        """Test general exception handling"""
        # Given: Successful setup
        mock_setup.return_value = True
        
        service = DeviceDetectorService()
        service.detector.monitor = Mock()
        
        # Monitor raises exception
        service.detector.monitor.poll.side_effect = Exception("Monitor error")
        
        # When: Execute run
        service.run()
        
        # Then: Service is stopped
        mock_stop.assert_called_once()
    
    def test_main_entry_point(self):
        """Test __main__ entry point"""
        # This test verifies the entry point exists but doesn't test execution
        # since the module is already imported
        pass