"""Integration tests for Device Detector full flow"""
import json
import time
import threading
from typing import Optional, Dict, Any
import pytest
import redis
from unittest.mock import Mock

# Note: These tests require Redis to be running
# Run with: docker-compose up redis -d


class TestDeviceDetectionFlow:
    """Integration tests for device detection and Redis event publishing"""
    
    @pytest.fixture
    def redis_client(self):
        """Redis client fixture with cleanup"""
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test connection
        try:
            client.ping()
        except redis.ConnectionError:
            pytest.skip("Redis not available for integration tests")
            
        # Cleanup before test
        client.flushall()
        
        yield client
        
        # Cleanup after test
        client.flushall()
        client.close()
    
    @pytest.fixture
    def event_subscriber(self, redis_client):
        """Redis event subscriber fixture"""
        pubsub = redis_client.pubsub()
        pubsub.subscribe('device_events')
        
        # Skip subscription confirmation message
        message = pubsub.get_message(timeout=1)
        assert message['type'] == 'subscribe'
        
        yield pubsub
        pubsub.close()
    
    def test_redis_connection_available(self, redis_client):
        """Test that Redis is available for integration tests"""
        assert redis_client.ping() == True
        
        # Test basic pub/sub functionality
        pubsub = redis_client.pubsub()
        pubsub.subscribe('test_channel')
        
        redis_client.publish('test_channel', 'test_message')
        
        # Skip subscription confirmation
        pubsub.get_message(timeout=1)
        
        message = pubsub.get_message(timeout=1)
        assert message is not None
        assert message['data'] == 'test_message'
        
        pubsub.close()
    
    def test_device_event_publishing_format(self, redis_client, event_subscriber):
        """Test that device events are published in correct format"""
        
        # Simulate device detector publishing an event
        test_event = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {
                'ID_VENDOR_ID': '0403',
                'ID_MODEL_ID': '6001',
                'DEVNAME': '/dev/ttyUSB0',
                'SUBSYSTEM': 'tty'
            }
        }
        
        # Publish event
        redis_client.publish('device_events', json.dumps(test_event))
        
        # Receive and validate event
        message = event_subscriber.get_message(timeout=5)
        assert message is not None
        assert message['type'] == 'message'
        assert message['channel'] == 'device_events'
        
        # Parse and validate event data
        received_event = json.loads(message['data'])
        
        assert received_event['action'] == 'add'
        assert received_event['path'] == '/dev/ttyUSB0'
        assert 'timestamp' in received_event
        assert isinstance(received_event['timestamp'], (int, float))
        assert received_event['properties']['ID_VENDOR_ID'] == '0403'
        assert received_event['properties']['SUBSYSTEM'] == 'tty'
    
    def test_multiple_device_events(self, redis_client, event_subscriber):
        """Test handling multiple device events"""
        
        # Simulate multiple device events
        events = [
            {
                'action': 'add',
                'path': '/dev/ttyUSB0',
                'timestamp': time.time(),
                'properties': {'SUBSYSTEM': 'tty', 'ID_VENDOR_ID': '0403'}
            },
            {
                'action': 'add', 
                'path': '/dev/ttyUSB1',
                'timestamp': time.time(),
                'properties': {'SUBSYSTEM': 'tty', 'ID_VENDOR_ID': '10c4'}
            },
            {
                'action': 'remove',
                'path': '/dev/ttyUSB0', 
                'timestamp': time.time(),
                'properties': {'SUBSYSTEM': 'tty', 'ID_VENDOR_ID': '0403'}
            }
        ]
        
        # Publish events with small delays
        for event in events:
            redis_client.publish('device_events', json.dumps(event))
            time.sleep(0.1)
        
        # Collect all events
        received_events = []
        for _ in range(len(events)):
            message = event_subscriber.get_message(timeout=2)
            assert message is not None
            received_events.append(json.loads(message['data']))
        
        # Validate events
        assert len(received_events) == 3
        
        # Check add events
        add_events = [e for e in received_events if e['action'] == 'add']
        assert len(add_events) == 2
        assert add_events[0]['path'] == '/dev/ttyUSB0'
        assert add_events[1]['path'] == '/dev/ttyUSB1'
        
        # Check remove event
        remove_events = [e for e in received_events if e['action'] == 'remove']
        assert len(remove_events) == 1
        assert remove_events[0]['path'] == '/dev/ttyUSB0'
    
    def test_event_consumer_pattern(self, redis_client):
        """Test typical event consumer pattern"""
        
        # Simulate a consumer that processes device events
        received_events = []
        
        def event_consumer():
            """Sample event consumer function"""
            pubsub = redis_client.pubsub()
            pubsub.subscribe('device_events')
            
            # Skip subscription confirmation
            pubsub.get_message(timeout=1)
            
            # Process events for a short time
            start_time = time.time()
            while time.time() - start_time < 2:
                message = pubsub.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    event = json.loads(message['data'])
                    received_events.append(event)
                    
                    # Simulate processing
                    if event['action'] == 'add':
                        print(f"Device connected: {event['path']}")
                    elif event['action'] == 'remove':
                        print(f"Device disconnected: {event['path']}")
            
            pubsub.close()
        
        # Start consumer in background thread
        consumer_thread = threading.Thread(target=event_consumer)
        consumer_thread.start()
        
        # Give consumer time to start
        time.sleep(0.1)
        
        # Publish test events
        test_events = [
            {'action': 'add', 'path': '/dev/ttyUSB0', 'timestamp': time.time(), 'properties': {}},
            {'action': 'remove', 'path': '/dev/ttyUSB0', 'timestamp': time.time(), 'properties': {}}
        ]
        
        for event in test_events:
            redis_client.publish('device_events', json.dumps(event))
            time.sleep(0.1)
        
        # Wait for consumer to finish
        consumer_thread.join()
        
        # Validate received events
        assert len(received_events) == 2
        assert received_events[0]['action'] == 'add'
        assert received_events[1]['action'] == 'remove'
    
    def test_event_data_validation(self, redis_client, event_subscriber):
        """Test validation of event data structure"""
        
        # Test event with all required fields
        valid_event = {
            'action': 'add',
            'path': '/dev/ttyUSB0',
            'timestamp': time.time(),
            'properties': {
                'ID_VENDOR_ID': '0403',
                'ID_MODEL_ID': '6001',
                'DEVNAME': '/dev/ttyUSB0',
                'SUBSYSTEM': 'tty',
                'BUSNUM': '001',
                'DEVNUM': '007'
            }
        }
        
        redis_client.publish('device_events', json.dumps(valid_event))
        
        message = event_subscriber.get_message(timeout=5)
        assert message is not None
        
        event = json.loads(message['data'])
        
        # Validate required fields
        assert 'action' in event
        assert 'path' in event  
        assert 'timestamp' in event
        assert 'properties' in event
        
        # Validate data types
        assert isinstance(event['action'], str)
        assert isinstance(event['path'], str)
        assert isinstance(event['timestamp'], (int, float))
        assert isinstance(event['properties'], dict)
        
        # Validate action values
        assert event['action'] in ['add', 'remove']
        
        # Validate path format
        assert event['path'].startswith('/dev/')
        
        # Validate timestamp is reasonable (not in far future/past)
        now = time.time()
        assert abs(event['timestamp'] - now) < 86400  # Within 24 hours