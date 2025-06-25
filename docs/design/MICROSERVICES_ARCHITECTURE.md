# Microservices Architecture (Revised)

## Overview

Based on security review feedback, the architecture has been revised to implement a **privilege separation model** using microservices. This approach minimizes security risks while maintaining the plug-and-play functionality.

## Architecture Components

### 1. Device Detector (Privileged - Minimal)
**Role**: Device event detection only  
**Privileges**: Privileged container (udev access)  
**Code Size**: Minimal implementation focused on security  
**Responsibility**: Detect device connection/disconnection and publish events

```python
#!/usr/bin/env python3
"""
Device Detector - Minimal privileged container
Responsibility: Only detect and notify device events
Key principles:
- Minimal code for security
- Proper error handling for production use
- Clear separation of concerns
"""
# Implementation focuses on:
# 1. Device event monitoring (udev)
# 2. Event filtering (relevant subsystems only)
# 3. Event publishing (Redis)
# 4. Basic lifecycle management
# 5. Health monitoring capability
```

### 2. Device Manager (Standard Privileges)
**Role**: Device identification and configuration  
**Privileges**: Standard container (read-only /dev access)  
**Responsibility**: VID/PID lookup, profile management, configuration generation

### 3. Data Processor (Standard Privileges)
**Role**: Data processing and streaming  
**Privileges**: Standard container (specific device access)  
**Responsibility**: Protocol handling, data streaming, MQTT/WebSocket publishing

### 4. Support Services
- **Redis**: Event bus for inter-service communication
- **MQTT Broker**: Data distribution
- **Config Store**: Centralized configuration management

## System Configuration

### docker-compose.yml (Revised)
```yaml
version: '3.8'

services:
  # Device detection - minimal privileged container
  device-detector:
    build: ./services/detector
    privileged: true
    volumes:
      - /run/udev:/run/udev:ro
    environment:
      - ROLE=detection_only
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-h", "redis", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Device management - standard privileges
  device-manager:
    build: ./services/manager
    volumes:
      - /dev:/dev:ro  # Read-only device access
      - ./config/profiles:/app/profiles:ro
    environment:
      - REDIS_URL=redis://redis:6379
      - PROFILE_PATH=/app/profiles
    depends_on:
      - device-detector
      - redis
    restart: unless-stopped

  # Data processing - standard privileges
  data-processor:
    build: ./services/processor
    # Only specific devices (managed dynamically)
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/i2c-1:/dev/i2c-1
    environment:
      - REDIS_URL=redis://redis:6379
      - MQTT_BROKER=mqtt://mqtt-broker:1883
    depends_on:
      - device-manager
      - mqtt-broker
    restart: unless-stopped

  # Event bus
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    restart: unless-stopped

  # MQTT broker
  mqtt-broker:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./config/mosquitto:/mosquitto/config
      - mosquitto-data:/mosquitto/data
    restart: unless-stopped

volumes:
  redis-data:
  mosquitto-data:

networks:
  default:
    name: rpi4-driver-network
```

## Data Flow

### 1. Device Connection Flow
```
Device Connected (USB)
        ↓
Device Detector (privileged)
  - Detects udev event
  - Publishes to Redis: "device_events"
        ↓
Device Manager (standard)
  - Receives event
  - Extracts VID/PID
  - Looks up device profile
  - Generates configuration
  - Publishes to Redis: "device_configs"
        ↓
Data Processor (standard)
  - Receives configuration
  - Establishes connection
  - Starts data streaming
  - Publishes to MQTT/WebSocket
```

### 2. Event Messages

#### Device Event (Detector → Manager)
```json
{
  "timestamp": 1736931234.567890,
  "action": "add",
  "path": "/dev/ttyUSB0",
  "subsystem": "tty",
  "properties": {
    "ID_VENDOR_ID": "2341",
    "ID_PRODUCT_ID": "0043",
    "ID_VENDOR": "Arduino LLC",
    "ID_MODEL": "Arduino_Uno"
  }
}
```

#### Device Configuration (Manager → Processor)
```json
{
  "device": "/dev/ttyUSB0",
  "profile": {
    "name": "Arduino Uno",
    "interface": "uart",
    "baudrate": 9600,
    "protocol": "arduino_serial"
  },
  "config": {
    "auto_reconnect": true,
    "buffer_size": 1024,
    "timeout": 5.0
  },
  "timestamp": 1736931240.123456
}
```

## Security Model

### Privilege Separation Matrix

| Service | Privileges | Device Access | Network | File System |
|---------|------------|---------------|---------|-------------|
| Device Detector | privileged | udev only | redis only | minimal |
| Device Manager | standard | /dev (read) | redis, http | read-only config |
| Data Processor | standard | specific devices | mqtt, websocket | minimal |

### Security Benefits

1. **Minimal Attack Surface**: Minimal privileged code focused on security
2. **Failure Isolation**: Service failures don't cascade
3. **Audit Simplicity**: Small privileged component is easy to review
4. **Principle of Least Privilege**: Each service has minimal required access

## Service Details

### Device Detector Service
```dockerfile
FROM python:3.11-alpine

# Minimal dependencies
RUN pip install pyudev redis

COPY detector.py /app/
WORKDIR /app

# Run as root (required for udev)
CMD ["python", "detector.py"]
```

### Device Manager Service
```dockerfile
FROM python:3.11-alpine

# Standard dependencies
RUN apk add --no-cache linux-headers
RUN pip install redis pyudev pyyaml

COPY manager/ /app/
WORKDIR /app

# Run as non-root
RUN adduser -D -s /bin/sh app
USER app

CMD ["python", "manager.py"]
```

## Implementation Phases

### Phase 1: Core Infrastructure (1 week)
- [x] Device Detector implementation (minimal security-focused)
- [x] Redis event bus setup
- [x] Basic event flow verification
- [ ] Container orchestration setup

### Phase 2: Device Management (2 weeks)
- [ ] Device Manager implementation
- [ ] VID/PID profile database
- [ ] Configuration generation engine
- [ ] Device lifecycle management

### Phase 3: Data Processing (2 weeks)
- [ ] Data Processor implementation
- [ ] Protocol handlers
- [ ] MQTT/WebSocket streaming
- [ ] Error handling and recovery

### Phase 4: Integration & Testing (1 week)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] Production readiness

## Monitoring and Observability

### Health Checks
```yaml
# Each service has appropriate health checks
healthcheck:
  test: ["CMD", "python", "health_check.py"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Logging Strategy
```python
# Structured logging for all services
import structlog

logger = structlog.get_logger()
logger.info("device_detected", 
           device="/dev/ttyUSB0", 
           vendor_id="2341", 
           product_id="0043")
```

### Metrics Collection
- Service health and uptime
- Device connection/disconnection rates
- Data throughput per device
- Error rates by service

## Development Guidelines

### 1. Single Responsibility
Each service has exactly one responsibility:
- **Detector**: Only detect events
- **Manager**: Only manage configurations  
- **Processor**: Only process data

### 2. Minimal Interfaces
Services communicate only through well-defined message formats via Redis.

### 3. Fail-Safe Design
- Services can restart independently
- Temporary Redis unavailability is handled gracefully
- Device disconnections don't affect other devices

### 4. Testing Strategy
```bash
# Unit tests for each service
cd services/detector && python -m pytest
cd services/manager && python -m pytest
cd services/processor && python -m pytest

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Migration Path

### From Monolithic to Microservices
1. **Start with Device Detector**: Implement minimal privileged service
2. **Add Event Bus**: Set up Redis for inter-service communication
3. **Extract Device Manager**: Move identification logic to separate service
4. **Add Data Processor**: Move data handling to separate service
5. **Remove Monolith**: Retire original privileged container

### Compatibility
- Existing MQTT topic structure maintained
- Data format remains unchanged
- API endpoints preserved where possible

## Conclusion

This revised microservices architecture provides:

1. **Enhanced Security**: Privileged code minimized for security
2. **Better Maintainability**: Clear service boundaries
3. **Improved Scalability**: Independent service scaling
4. **Fault Isolation**: Service failures don't cascade
5. **Development Efficiency**: Parallel development possible

The architecture balances security, functionality, and operational simplicity, making it suitable for production deployment while maintaining the ease of development and testing.