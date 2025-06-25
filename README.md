# RPi4 Interface Drivers

A lightweight, containerized driver system for monitoring Raspberry Pi 4 hardware interfaces (GPIO, I2C, SPI, UART) and streaming raw data to other containers.

## Features

- 🔌 **Universal Interface Support**: GPIO, I2C, SPI, and UART interfaces
- ⚡ **True Plug & Play**: Zero-configuration device detection and connection
- 🔍 **Smart Device Recognition**: Automatic device identification and protocol detection
- 🔄 **Hot-plug Support**: Real-time device add/remove detection via udev
- 🚀 **Real-time Streaming**: Low-latency data streaming via MQTT/WebSocket
- 🛡️ **Security First**: Privilege separation with minimal privileged code focused on security
- 📦 **Microservices Architecture**: Isolated, scalable service components
- 🐳 **Docker Native**: Designed for containerized environments
- 🔄 **Auto-reconnection**: Automatic recovery from device disconnections
- 📊 **Smart Protocol Handling**: 70% auto-detection + guaranteed raw passthrough for unknowns

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

This project uses a **security-first microservices architecture** with privilege separation:

```
Device Detector (privileged, minimal implementation)
        ↓ Redis Events
Device Manager (standard privileges)  
        ↓ Device Configs
Data Processor (standard privileges)
        ↓ MQTT/WebSocket
Your Applications
```

**Key Benefits:**
- **Security**: Minimal privileged code surface focused on essential functions
- **Compatibility**: 70% auto-detection + 100% raw passthrough guarantee
- **Scalability**: Multi-platform support (RPi4, Jetson, BeagleBone, x86)
- **Extensibility**: User-defined custom protocols and community sharing

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

### 🏗️ **Design Documentation**
- [Architecture Overview](docs/design/) - All architecture and design documents
  - [Final Architecture](docs/design/FINAL_ARCHITECTURE.md) - Complete system design and rationale
  - [Design Document](docs/design/DESIGN.md) - Detailed architecture and specifications
  - [Microservices Architecture](docs/design/MICROSERVICES_ARCHITECTURE.md) - Security-first architecture
  - [Plug & Play Guide](docs/design/PLUGPLAY.md) - Zero-configuration setup and hot-plug support
  - [Custom Protocols](docs/design/CUSTOM_PROTOCOLS.md) - 70% auto-detection + custom protocol support
  - [Implementation Details](docs/design/PLUGPLAY_IMPLEMENTATION.md) - Technical implementation guide
  - [Architecture Review](docs/design/ARCHITECTURE_REVIEW.md) - Design decisions and feedback

### 📋 **Development Process**
- [Development Process Guide](docs/process/) - Development guidelines and workflows
  - [Development Rules](docs/process/DEVELOPMENT_RULES.md) - 開発ルールブック
  - [PR Guidelines](docs/process/PR_GUIDELINES.md) - Pull Request submission guidelines
- [Claude Instructions](CLAUDE.md) - Project-specific AI assistant instructions (at root for AI access)

### 🛠️ **Technical References**
- [Configuration Guide](docs/configuration.md) - Advanced configuration options
- [API Reference](docs/api.md) - Data format and protocol details
- [Examples](examples/) - Sample implementations

## Platform Support

- **Primary**: Raspberry Pi 4
- **Planned**: Jetson Nano, BeagleBone Black, Generic x86 Linux
- **Requirements**: Docker and Docker Compose
- **Permissions**: Hardware interface access (`/dev/*`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 [Report Issues](https://github.com/w-pinkietech/rpi4-driver/issues)
- 💬 [Discussions](https://github.com/w-pinkietech/rpi4-driver/discussions)
- 📧 Contact: github.cycling777@gmail.com