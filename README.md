# RPi4 Interface Drivers

A lightweight, containerized driver system for monitoring Raspberry Pi 4 hardware interfaces (GPIO, I2C, SPI, UART) and streaming raw data to other containers.

## Features

- 🔌 **Universal Interface Support**: GPIO, I2C, SPI, and UART interfaces
- ⚡ **True Plug & Play**: Zero-configuration device detection and connection
- 🔍 **Smart Device Recognition**: Automatic device identification and protocol detection
- 🔄 **Hot-plug Support**: Real-time device add/remove detection via udev
- 🚀 **Real-time Streaming**: Low-latency data streaming via MQTT/WebSocket
- 🐳 **Docker Native**: Designed for containerized environments
- 🔄 **Auto-reconnection**: Automatic recovery from device disconnections
- 📦 **Raw Data Transfer**: Transparent data forwarding without protocol interpretation

## Quick Start

```bash
# Clone the repository
git clone https://github.com/w-pinkietech/rpi4-driver.git
cd rpi4-driver

# Run with Docker Compose
docker-compose up -d
```

## Zero Configuration

```yaml
# config.yaml (optional - works without any config!)
version: 1
mode: auto
```

That's it! Just connect your devices and they'll be automatically detected, configured, and monitored. No configuration files needed for basic operation.

## Architecture

This project acts as a bridge between RPi4 hardware interfaces and your applications:

```
RPi4 Hardware → Interface Driver Container → MQTT/WebSocket → Your Application
```

## Supported Interfaces

- **GPIO**: Digital input/output with edge detection
- **I2C**: Master mode with auto-discovery (0x08-0x77)
- **SPI**: Full-duplex communication up to 10MHz
- **UART**: Auto-baudrate detection (9600-115200)

## Output Modes

1. **Raw Only**: Pure binary data (minimal overhead)
2. **Tagged**: Timestamp + raw data (recommended)
3. **Structured**: JSON format with metadata (debugging)

## Documentation

- [Design Document](DESIGN.md) - Detailed architecture and specifications
- [Plug & Play Guide](PLUGPLAY.md) - Zero-configuration setup and hot-plug support
- [Implementation Details](docs/PLUGPLAY_IMPLEMENTATION.md) - Technical implementation guide
- [Architecture Review](docs/ARCHITECTURE_REVIEW.md) - Design decisions and feedback request
- [Configuration Guide](docs/configuration.md) - Advanced configuration options
- [API Reference](docs/api.md) - Data format and protocol details
- [Examples](examples/) - Sample implementations

## Requirements

- Raspberry Pi 4
- Docker and Docker Compose
- Access to hardware interfaces (`/dev/*`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 [Report Issues](https://github.com/w-pinkietech/rpi4-driver/issues)
- 💬 [Discussions](https://github.com/w-pinkietech/rpi4-driver/discussions)
- 📧 Contact: github.cycling777@gmail.com