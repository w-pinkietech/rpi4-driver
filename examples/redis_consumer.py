#!/usr/bin/env python3
"""Example Redis event consumer for Device Detector events

This example shows how to consume device events from the Device Detector
and process them in your own application.

Usage:
    python examples/redis_consumer.py

Requirements:
    pip install redis
"""

import json
import signal
import sys
import time
from typing import Dict, Any
import redis


class DeviceEventConsumer:
    """Example consumer for device events from Device Detector"""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        """Initialize event consumer
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.pubsub = None
        self.running = False
        
        # Device registry to track connected devices
        self.connected_devices = {}
    
    def connect(self) -> bool:
        """Connect to Redis and subscribe to device events
        
        Returns:
            True if connection successful
        """
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_keepalive=True
            )
            
            # Test connection
            self.redis_client.ping()
            print(f"✓ Connected to Redis at {self.redis_host}:{self.redis_port}")
            
            # Subscribe to device events
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe('device_events')
            
            # Skip subscription confirmation message
            message = self.pubsub.get_message(timeout=1)
            if message and message['type'] == 'subscribe':
                print(f"✓ Subscribed to 'device_events' channel")
            
            return True
            
        except redis.ConnectionError as e:
            print(f"✗ Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return False
    
    def process_device_event(self, event: Dict[str, Any]) -> None:
        """Process a single device event
        
        Args:
            event: Device event dictionary
        """
        action = event.get('action')
        path = event.get('path')
        properties = event.get('properties', {})
        timestamp = event.get('timestamp')
        
        # Extract device information
        vendor_id = properties.get('ID_VENDOR_ID', 'unknown')
        model_id = properties.get('ID_MODEL_ID', 'unknown')
        subsystem = properties.get('SUBSYSTEM', 'unknown')
        
        if action == 'add':
            print(f"🔌 Device CONNECTED: {path}")
            print(f"   Type: {subsystem}")
            print(f"   Vendor: {vendor_id}")
            print(f"   Model: {model_id}")
            print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(timestamp))}")
            
            # Store device information
            self.connected_devices[path] = {
                'vendor_id': vendor_id,
                'model_id': model_id,
                'subsystem': subsystem,
                'connected_at': timestamp
            }
            
            # Custom processing based on device type
            self.handle_device_connection(path, properties)
            
        elif action == 'remove':
            print(f"🔌 Device DISCONNECTED: {path}")
            print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(timestamp))}")
            
            # Remove from registry
            if path in self.connected_devices:
                device_info = self.connected_devices.pop(path)
                duration = timestamp - device_info['connected_at']
                print(f"   Duration: {duration:.1f} seconds")
            
            # Custom processing for disconnection
            self.handle_device_disconnection(path, properties)
        
        print()  # Add blank line for readability
    
    def handle_device_connection(self, path: str, properties: Dict[str, Any]) -> None:
        """Handle device connection - customize this for your application
        
        Args:
            path: Device path (e.g., /dev/ttyUSB0)
            properties: Device properties from udev
        """
        subsystem = properties.get('SUBSYSTEM')
        vendor_id = properties.get('ID_VENDOR_ID')
        
        # Example: Special handling for specific devices
        if subsystem == 'tty':
            if vendor_id == '0403':  # FTDI devices
                print(f"   → FTDI serial device detected")
                # Example: Auto-configure for specific baudrate
                print(f"   → Suggested config: 115200 8N1")
            elif vendor_id == '10c4':  # Silicon Labs devices
                print(f"   → Silicon Labs CP210x detected")
                print(f"   → Suggested config: 9600 8N1")
            else:
                print(f"   → Generic TTY device")
        
        elif subsystem == 'usb':
            print(f"   → USB device detected")
            # Could trigger USB device enumeration here
    
    def handle_device_disconnection(self, path: str, properties: Dict[str, Any]) -> None:
        """Handle device disconnection - customize this for your application
        
        Args:
            path: Device path that was disconnected
            properties: Device properties from udev
        """
        # Example: Cleanup any resources associated with the device
        print(f"   → Cleaning up resources for {path}")
        
        # Example: Log disconnection for monitoring
        # logger.info(f"Device {path} disconnected")
    
    def show_status(self) -> None:
        """Show current status and connected devices"""
        print(f"\n📊 Status:")
        print(f"   Connected devices: {len(self.connected_devices)}")
        
        if self.connected_devices:
            print(f"   Device list:")
            for path, info in self.connected_devices.items():
                duration = time.time() - info['connected_at']
                print(f"     {path} ({info['subsystem']}) - {duration:.0f}s")
        else:
            print(f"   No devices currently connected")
        print()
    
    def run(self) -> None:
        """Main event loop"""
        if not self.connect():
            sys.exit(1)
        
        print("🚀 Device Event Consumer started")
        print("   Monitoring for device connections/disconnections...")
        print("   Press Ctrl+C to stop\n")
        
        self.running = True
        last_status_time = time.time()
        
        try:
            while self.running:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=1)
                
                if message and message['type'] == 'message':
                    try:
                        # Parse device event
                        event = json.loads(message['data'])
                        self.process_device_event(event)
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Invalid JSON in device event: {e}")
                    except Exception as e:
                        print(f"⚠️  Error processing device event: {e}")
                
                # Show periodic status
                if time.time() - last_status_time > 30:  # Every 30 seconds
                    self.show_status()
                    last_status_time = time.time()
                    
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the consumer gracefully"""
        print("🔄 Stopping device event consumer...")
        self.running = False
        
        if self.pubsub:
            self.pubsub.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        print("✅ Device event consumer stopped")


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals"""
    print(f"\n📡 Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments (basic example)
    import argparse
    parser = argparse.ArgumentParser(description='Device Event Consumer Example')
    parser.add_argument('--redis-host', default='localhost', 
                       help='Redis server hostname (default: localhost)')
    parser.add_argument('--redis-port', type=int, default=6379,
                       help='Redis server port (default: 6379)')
    
    args = parser.parse_args()
    
    # Start consumer
    consumer = DeviceEventConsumer(
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    consumer.run()


if __name__ == '__main__':
    main()