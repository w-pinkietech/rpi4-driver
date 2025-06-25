# RPi4 Interface Drivers Project

## Overview
This project provides drivers to monitor and access Raspberry Pi 4 interfaces from Docker containers.

## Documentation Reference Guide

### 📐 Design and Architecture
When working on **design or architecture** tasks, refer to:
- `docs/design/` - All design and architecture documents
- Start with `docs/design/README.md` for document index and reading order

### 🛠️ Development Process
When working on **development tasks**, refer to:
- `docs/process/` - Development guidelines and workflows
- `docs/process/DEVELOPMENT_RULES.md` - Coding standards and Git workflow
- `docs/process/README.md` for process overview

### 🔍 Code Review
When performing **code reviews or PR submissions**, refer to:
- `docs/process/PR_GUIDELINES.md` - Pull request guidelines
- `docs/design/ARCHITECTURE_REVIEW.md` - Past review examples and feedback
- `docs/design/REVIEW_RESPONSE.md` - How to respond to reviews

## Supported Interfaces
- GPIO (General Purpose Input/Output)
- I2C (Inter-Integrated Circuit)
- SPI (Serial Peripheral Interface)
- UART (Universal Asynchronous Receiver/Transmitter)

## Development Requirements
- Raspberry Pi 4
- Docker and Docker Compose
- Python 3.11+
- Access to /dev devices from Docker containers

## Testing Commands
```bash
# Run tests
python -m pytest tests/

# Lint code
python -m flake8 src/

# Type check
python -m mypy src/
```

## Docker Device Access
Docker containers need privileged access or specific device mappings:
- GPIO: /dev/gpiomem
- I2C: /dev/i2c-*
- SPI: /dev/spidev*
- UART: /dev/ttyAMA0, /dev/ttyS0

## Architecture
The driver system uses a modular approach with separate handlers for each interface type, unified under a common monitoring framework.