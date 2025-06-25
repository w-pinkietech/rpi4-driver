# Device Detector

Minimal privileged container for monitoring udev device events and publishing them to Redis.

## Overview

The Device Detector is the **privileged component** of the RPi4 Interface Drivers system. It monitors udev events for device connections/disconnections and publishes events to Redis for consumption by other unprivileged services.

### Security Design

- **Minimal privileged code**: <100 lines of core logic
- **Event-driven**: Only publishes events, no device control
- **Isolated**: Runs in separate container with minimal attack surface

## Quick Start

```bash
# Build and start services
docker-compose up -d

# View device events (testing)
docker-compose --profile testing up event-consumer

# Check logs
docker-compose logs -f device-detector
```

## Architecture

```
┌─────────────────────┐    Redis Events    ┌─────────────────────┐
│   Device Detector   │ ─────────────────→ │  Device Manager     │
│   (privileged)      │                    │  (unprivileged)     │
│                     │                    │                     │
│ ┌─────────────────┐ │                    │ ┌─────────────────┐ │
│ │ udev monitor    │ │                    │ │ Event consumer  │ │
│ │ TTY/USB filter  │ │                    │ │ Device configs  │ │
│ │ Redis publisher │ │                    │ │ Interface mgmt  │ │
│ └─────────────────┘ │                    │ └─────────────────┘ │
└─────────────────────┘                    └─────────────────────┘
```

## Event Format

Device events are published to the `device_events` Redis channel:

```json
{
  "action": "add",
  "path": "/dev/ttyUSB0", 
  "timestamp": 1736931234.567890,
  "properties": {
    "ID_VENDOR_ID": "0403",
    "ID_MODEL_ID": "6001", 
    "DEVNAME": "/dev/ttyUSB0",
    "SUBSYSTEM": "tty"
  }
}
```

### Filtered Events

- **Actions**: Only `add` and `remove` events
- **Subsystems**: Only `tty` and `usb` devices
- **Properties**: All udev properties preserved

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis server hostname |
| `LOG_LEVEL` | `INFO` | Logging level |

### Docker Compose Override

Create `docker-compose.override.yml` for custom configuration:

```yaml
version: '3.8'
services:
  device-detector:
    environment:
      - LOG_LEVEL=DEBUG
    # Additional custom settings
```

## Development

### Running Tests

```bash
cd device-detector
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v --cov=src
```

### Test Coverage

Current coverage: **94%** (target: ≥90%)

```
Name              Stmts   Miss  Cover
-------------------------------------
src/detector.py      34     2    94%
TOTAL               34     2    94%
```

## Monitoring

### Health Checks

```bash
# Check container health
docker-compose ps

# Manual health check
docker exec rpi4-device-detector python -c "import redis; redis.Redis(host='redis').ping()"
```

### Logs

```bash
# Service logs
docker-compose logs -f device-detector

# Redis logs
docker-compose logs -f redis
```

## Troubleshooting

### Common Issues

#### "Permission denied" accessing `/dev/`
- Ensure container runs with `privileged: true`
- Check volume mounts for `/dev` and `/run/udev`

#### "Connection refused" to Redis
- Verify Redis container is healthy: `docker-compose ps`
- Check network connectivity: `docker-compose exec device-detector ping redis`

#### No device events appearing
- Check if devices are actually connecting/disconnecting
- Verify udev is running on host: `systemctl status udev`
- Enable debug logging: `LOG_LEVEL=DEBUG`

### Debug Commands

```bash
# Test Redis connection
docker-compose exec device-detector python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# List udev devices manually
docker-compose exec device-detector python -c "import pyudev; ctx=pyudev.Context(); [print(d) for d in ctx.list_devices(subsystem='tty')]"

# Monitor Redis events manually
docker-compose exec redis redis-cli SUBSCRIBE device_events
```

## Security Considerations

- Container runs as non-root user despite privileged access
- Minimal dependencies and attack surface
- No shell access in production image
- Read-only access to host devices

## Performance

- **Memory usage**: ~20MB
- **CPU usage**: <1% idle, ~5% during device events
- **Event latency**: <10ms from udev to Redis

## License

MIT License - see [LICENSE](../LICENSE) file.