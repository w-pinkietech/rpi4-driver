#!/bin/bash
# Compare USB device detection between bare metal and Docker

echo "=== USB Device Detection Comparison ==="
echo

echo "1. Bare Metal Environment:"
echo "-------------------------"
# List USB devices
lsusb
echo
# Show USB serial devices
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"
echo
# Monitor udev events (requires root)
echo "To monitor udev events on bare metal, run:"
echo "sudo udevadm monitor --environment --udev"
echo

echo "2. Docker Container Environment:"
echo "-------------------------------"
# Test inside container
docker run --rm --privileged \
  -v /run/udev:/run/udev:ro \
  -v /dev:/dev:ro \
  alpine:latest sh -c '
    echo "Inside container:"
    ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"
    echo
    echo "Checking /run/udev access:"
    ls -la /run/udev/ | head -5
'

echo
echo "3. Key Differences:"
echo "------------------"
echo "- Bare metal: Direct access to all devices"
echo "- Docker: Requires explicit volume mounts and privileges"
echo "- Hot-plug: Works differently in containers"
echo
echo "Recommendation: Test with actual USB device connected"