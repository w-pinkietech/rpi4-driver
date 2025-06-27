"""Device Detector - Minimal privileged container for udev monitoring"""
import time
import json
import logging
import pyudev
import redis
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DeviceDetector:
    """Minimal device detector for udev events - privileged container component"""
    
    def __init__(self, redis_host: str = 'redis'):
        """Initialize device detector
        
        Args:
            redis_host: Redis server hostname
        """
        self.redis_host = redis_host
        self.redis_client: Optional[redis.Redis] = None
        self.context: Optional[pyudev.Context] = None
        self.monitor: Optional[pyudev.Monitor] = None
    
    def parse_event(self, device: pyudev.Device) -> Dict[str, Any]:
        """Parse udev device event into standardized format
        
        Args:
            device: pyudev Device object
            
        Returns:
            Dictionary containing event data
        """
        try:
            return {
                'action': device.action,
                'path': device.device_node,
                'timestamp': time.time(),
                'properties': dict(device.properties)
            }
        except Exception as e:
            logger.error(f"Failed to parse device event: {e}")
            raise
    
    def should_process(self, action: str) -> bool:
        """Determine if device action should be processed
        
        Args:
            action: udev action (add, remove, change, etc.)
            
        Returns:
            True if action should be processed
        """
        return action in ['add', 'remove']
    
    def should_monitor_subsystem(self, subsystem: str) -> bool:
        """Determine if subsystem should be monitored
        
        Args:
            subsystem: Device subsystem (tty, usb, block, etc.)
            
        Returns:
            True if subsystem should be monitored
        """
        return subsystem in ['tty', 'usb']
    
    def publish_event(self, event_data: Dict[str, Any]) -> None:
        """Publish device event to Redis
        
        Args:
            event_data: Event data dictionary
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized, skipping event publish")
            return
            
        try:
            message = json.dumps(event_data)
            self.redis_client.publish('device_events', message)
            logger.debug(f"Published event: {event_data['action']} - {event_data['path']}")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise
    
    def setup_monitor(self) -> None:
        """Setup udev monitor with filters"""
        if self.monitor:
            self.monitor.filter_by('tty')
            self.monitor.filter_by('usb')
    
    def process_single_event(self) -> bool:
        """Process a single device event (for testing)
        
        Returns:
            True if event was processed successfully
        """
        if not self.monitor:
            logger.warning("Monitor not initialized")
            return False
            
        try:
            device = self.monitor.poll()
            if device and self.should_process(device.action):
                event_data = self.parse_event(device)
                self.publish_event(event_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error processing device event: {e}")
            raise