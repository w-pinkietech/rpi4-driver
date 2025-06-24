#!/usr/bin/env python3
"""Test Device Detector base functionality without USB devices"""

import time
import pyudev
import sys

def test_base_environment():
    """Test if base udev environment is accessible"""
    
    print("=== Device Detector Base Environment Test ===\n")
    
    # Test 1: pyudev Context
    print("1. Testing pyudev Context creation...")
    try:
        context = pyudev.Context()
        print("✓ pyudev Context created successfully")
    except Exception as e:
        print(f"✗ Failed to create pyudev Context: {e}")
        return False
    
    # Test 2: Monitor creation
    print("\n2. Testing Monitor creation...")
    try:
        monitor = pyudev.Monitor.from_netlink(context)
        print("✓ Monitor created successfully")
    except Exception as e:
        print(f"✗ Failed to create Monitor: {e}")
        return False
    
    # Test 3: Filter application
    print("\n3. Testing filter application...")
    try:
        monitor.filter_by('tty')
        monitor.filter_by('usb')
        print("✓ Filters applied successfully")
    except Exception as e:
        print(f"✗ Failed to apply filters: {e}")
        return False
    
    # Test 4: List existing devices
    print("\n4. Listing existing TTY devices...")
    tty_devices = list(context.list_devices(subsystem='tty'))
    print(f"Found {len(tty_devices)} TTY devices")
    
    usb_tty_devices = [d for d in tty_devices if 'USB' in str(d.device_node)]
    if usb_tty_devices:
        print("USB TTY devices found:")
        for device in usb_tty_devices:
            print(f"  - {device.device_node}")
    else:
        print("No USB TTY devices currently connected (this is OK)")
    
    # Test 5: Monitor for events (non-blocking)
    print("\n5. Testing event monitoring (5 seconds)...")
    print("Monitoring for device events...")
    
    monitor.start()
    start_time = time.time()
    event_count = 0
    
    try:
        while time.time() - start_time < 5:
            device = monitor.poll(timeout=0.1)
            if device:
                event_count += 1
                print(f"Event detected: {device.action} - {device.device_node}")
        
        if event_count == 0:
            print("No events detected (this is normal if no devices were connected/disconnected)")
        else:
            print(f"Detected {event_count} events")
            
    except Exception as e:
        print(f"✗ Error during monitoring: {e}")
        return False
    
    print("\n✓ All base environment tests passed!")
    return True

def compare_environments():
    """Compare bare metal vs container execution"""
    
    print("\n=== Environment Information ===")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Check if running in container
    try:
        with open('/proc/1/cgroup', 'r') as f:
            if 'docker' in f.read():
                print("Running in: Docker container")
            else:
                print("Running in: Bare metal")
    except:
        print("Running in: Unknown environment")
    
    # Check key paths
    print("\nKey paths:")
    paths = [
        '/run/udev/control',
        '/sys/class/tty',
        '/dev'
    ]
    
    for path in paths:
        try:
            import os
            if os.path.exists(path):
                print(f"✓ {path} exists")
            else:
                print(f"✗ {path} NOT FOUND")
        except Exception as e:
            print(f"✗ {path} check failed: {e}")

if __name__ == "__main__":
    compare_environments()
    print("\n" + "="*50 + "\n")
    
    success = test_base_environment()
    
    if not success:
        print("\n❌ Base environment tests FAILED!")
        print("The Device Detector will NOT work in this environment.")
        sys.exit(1)
    else:
        print("\n✅ Base environment is compatible with Device Detector")
        sys.exit(0)