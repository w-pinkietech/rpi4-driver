#!/bin/bash
# Verify base environment consistency between bare metal and Docker

echo "=== Base Environment Verification ==="
echo "Comparing bare metal vs Docker container environment"
echo

# Function to check environment
check_environment() {
    local env_name=$1
    echo "--- $env_name ---"
    
    # Check udev service status
    echo "1. udev service:"
    systemctl status systemd-udevd --no-pager 2>/dev/null || echo "systemd not available"
    
    # Check udev socket
    echo -e "\n2. udev socket:"
    ls -la /run/udev/control 2>/dev/null || echo "/run/udev/control not found"
    
    # Check existing USB devices
    echo -e "\n3. Existing USB devices:"
    ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices"
    ls -la /dev/ttyACM* 2>/dev/null || echo "No ACM devices"
    
    # Check device subsystems
    echo -e "\n4. TTY subsystem devices:"
    ls /sys/class/tty/ | grep -E "(USB|ACM)" || echo "No USB TTY devices in sysfs"
    
    # Check udev monitor capability
    echo -e "\n5. udev monitor test (5 seconds):"
    timeout 5 udevadm monitor --kernel --subsystem-match=tty 2>&1 || echo "udevadm monitor failed"
    
    echo -e "\n6. Process visibility:"
    ps aux | grep -E "(udev|systemd-udevd)" | grep -v grep || echo "No udev processes visible"
}

# Test on bare metal
echo "========================================"
echo "BARE METAL ENVIRONMENT"
echo "========================================"
check_environment "Bare Metal"

# Test in Docker container
echo -e "\n\n========================================"
echo "DOCKER CONTAINER ENVIRONMENT"
echo "========================================"
docker run --rm \
  --privileged \
  -v /run/udev:/run/udev:ro \
  -v /dev:/dev:ro \
  -v /sys:/sys:ro \
  python:3.11-slim bash -c "
    apt-get update -qq && apt-get install -qq -y udev procps >/dev/null 2>&1
    $(declare -f check_environment)
    check_environment 'Docker Container'
"

echo -e "\n\n========================================"
echo "CRITICAL DIFFERENCES TO CHECK:"
echo "========================================"
echo "1. Can container see /run/udev/control?"
echo "2. Are udev processes visible in container?"
echo "3. Does udevadm monitor work in container?"
echo "4. Are /sys/class/tty entries accessible?"
echo ""
echo "If any of these differ, the Device Detector won't work!"