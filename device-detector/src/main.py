#!/usr/bin/env python3
"""Main entry point for Device Detector - Minimal privileged container"""

import logging
import os
import signal
import sys

import pyudev
import redis

from .detector import DeviceDetector


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeviceDetectorService:
    """Service wrapper for Device Detector with lifecycle management"""
    
    def __init__(self):
        self.detector = DeviceDetector(
            redis_host=os.getenv('REDIS_HOST', 'redis')
        )
        self.running = False
        
    def setup(self) -> bool:
        """Setup detector with Redis and udev connections
        
        Returns:
            True if setup successful
        """
        try:
            # Setup Redis connection
            self.detector.redis_client = redis.Redis(
                host=self.detector.redis_host,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test Redis connection
            self.detector.redis_client.ping()
            logger.info(f"Connected to Redis at {self.detector.redis_host}")
            
            # Setup udev context and monitor
            self.detector.context = pyudev.Context()
            self.detector.monitor = pyudev.Monitor.from_netlink(self.detector.context)
            self.detector.setup_monitor()
            
            logger.info("Device monitor initialized")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def run(self) -> None:
        """Main event loop for device monitoring"""
        if not self.setup():
            sys.exit(1)
            
        logger.info("Starting device detection service...")
        self.running = True
        
        try:
            # Start monitoring udev events
            for device in iter(self.detector.monitor.poll, None):
                if not self.running:
                    break
                    
                if self.detector.should_process(device.action):
                    event_data = self.detector.parse_event(device)
                    self.detector.publish_event(event_data)
                    
                    logger.info(
                        f"Event: {device.action} - {device.device_node} "
                        f"({device.get('ID_VENDOR_ID', 'unknown')})"
                    )
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the service gracefully"""
        logger.info("Stopping device detection service...")
        self.running = False
        
        if self.detector.redis_client:
            self.detector.redis_client.close()


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main() -> None:
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start service
    service = DeviceDetectorService()
    service.run()


if __name__ == '__main__':
    main()