# Sub-Issue: I2C Protocol Simulator Implementation

## Title
Build I2C Protocol Simulator with Multi-Master and Timing Accuracy

## Description
Develop a comprehensive I2C bus simulator that accurately models the I2C protocol including multi-master arbitration, clock stretching, and various failure modes.

## Background
As part of the Hardware Mock-Driven Testing Strategy (#28), we need an I2C simulator that can:
- Model complete I2C protocol state machine
- Support multi-master scenarios
- Enable testing of protocol edge cases
- Provide device template system

## Requirements

### Protocol Features
- [ ] START/STOP condition generation
- [ ] 7-bit and 10-bit addressing
- [ ] ACK/NAK handling
- [ ] Clock stretching by slaves
- [ ] Multi-master arbitration
- [ ] Repeated START support

### Bus Simulation
- [ ] Configurable bus speeds (100kHz, 400kHz, 1MHz, 3.4MHz)
- [ ] Bus capacitance effects
- [ ] Rise/fall time simulation
- [ ] Pull-up resistor modeling
- [ ] SDA/SCL line states

### Device Templates
- [ ] Template system for common I2C devices
- [ ] Register-based device modeling
- [ ] Auto-increment address support
- [ ] Device-specific timing
- [ ] Power state modeling

### Failure Modes
- [ ] Device not responding (timeout)
- [ ] Address conflicts
- [ ] Arbitration loss
- [ ] Clock stuck low/high
- [ ] Data corruption
- [ ] Partial byte transmission

## Technical Approach

### Protocol State Machine
```python
class I2CProtocolState(Enum):
    IDLE = "idle"
    START = "start"
    ADDRESS = "address"
    ACK_ADDRESS = "ack_address"
    DATA = "data"
    ACK_DATA = "ack_data"
    STOP = "stop"
    REPEATED_START = "repeated_start"
```

### Bus Timing Model
```python
class I2CBusTiming:
    def __init__(self, speed_hz: int):
        self.period_ns = 1_000_000_000 // speed_hz
        self.setup_time_ns = 250  # START setup time
        self.hold_time_ns = 250   # START hold time
        self.rise_time_ns = 1000  # Max rise time
        self.fall_time_ns = 300   # Max fall time
```

### Device Template System
```yaml
# Device template example
pca9685:  # 16-channel PWM driver
  type: i2c_device
  addresses: [0x40-0x7F]  # Configurable address range
  registers:
    0x00: mode1
    0x01: mode2
    0x06-0x45: channel_registers
    0xFA: prescale
  behaviors:
    - on_write: [0x00, 0x10]  # Sleep bit
      side_effect: stop_oscillator
    - on_read: [0x00]
      return: compute_mode1_value
```

## Implementation Tasks

1. **Protocol Engine** (3 days)
   - State machine implementation
   - Timing enforcement
   - Bus arbitration logic

2. **Device Template System** (2 days)
   - YAML template parser
   - Register modeling
   - Behavior scripting

3. **Bus Physics Simulation** (1 day)
   - Capacitance effects
   - Rise/fall times
   - Clock stretching

4. **Multi-Master Support** (2 days)
   - Arbitration detection
   - Master switching
   - Collision handling

5. **Failure Injection** (1 day)
   - Fault injection API
   - Common I2C failures
   - Timing violations

6. **Integration** (1 day)
   - smbus/smbus2 compatibility
   - Test migration
   - Performance optimization

## Device Templates to Include

### High Priority
- BME280/BMP280 (temp/pressure sensors)
- PCA9685 (PWM driver)
- ADS1115 (ADC)
- SSD1306 (OLED display)
- PCF8574 (I/O expander)

### Medium Priority
- MPU6050 (accelerometer/gyro)
- DS3231 (RTC)
- EEPROM (24LC256)
- MCP23017 (I/O expander)

## Success Criteria
- [ ] Protocol compliance with I2C specification
- [ ] < 1µs per transaction overhead
- [ ] Support for 32 simultaneous devices
- [ ] 20+ device templates included
- [ ] Multi-master arbitration working
- [ ] All failure modes testable

## Performance Targets
| Operation | Target | Notes |
|-----------|---------|-------|
| Single byte read | < 500ns | Overhead only |
| Single byte write | < 500ns | Overhead only |
| 100-byte transfer | < 5µs | At 400kHz simulation |
| Device template load | < 1ms | Per device |

## Dependencies
- Python 3.11+
- PyYAML (for templates)
- Hardware Mock Core (#28)

## Estimated Effort
10 developer days

## Labels
`mock-implementation`, `i2c`, `testing`, `competitor-1`