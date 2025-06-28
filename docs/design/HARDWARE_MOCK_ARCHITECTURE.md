# Hardware Mock-Driven Testing Architecture

## Executive Summary

This document outlines a comprehensive hardware mock architecture that enables complete hardware independence, sub-millisecond test execution, and sophisticated failure simulation capabilities. The approach prioritizes speed, accuracy, and developer experience.

## Core Principles

1. **Zero Hardware Dependency**: All tests run without physical hardware
2. **Speed First**: Mock operations complete in microseconds, not milliseconds
3. **Failure-Rich Testing**: Simulate edge cases impossible on real hardware
4. **Protocol Accuracy**: Bit-perfect protocol simulation
5. **Time-Travel Debugging**: Replay and inspect hardware interactions

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Environment                         │
├─────────────────────────────────────────────────────────────┤
│                  Hardware Mock Layer                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐│
│  │GPIO Virtual │ │I2C Protocol │ │SPI Protocol │ │UART    ││
│  │State Machine│ │ Simulator   │ │ Simulator   │ │Emulator││
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘│
├─────────────────────────────────────────────────────────────┤
│                Virtual Device Registry                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Device Templates │ Timing Engine │ Event Sequencer  │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              Mock Infrastructure Core                       │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐     │
│  │Event Bus │ │State Manager │ │Performance Monitor │     │
│  └──────────┘ └──────────────┘ └────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Component Specifications

### 1. GPIO Virtual State Machine

**Purpose**: Simulate GPIO pin states with nanosecond precision

**Features**:
- Pin state tracking (HIGH/LOW/FLOATING/PULL_UP/PULL_DOWN)
- Edge detection with configurable debounce
- Interrupt simulation with priority levels
- Power consumption modeling
- Pin conflict detection

**Implementation**:
```python
class GPIOVirtualPin:
    def __init__(self, pin_number: int):
        self._state = PinState.FLOATING
        self._listeners = []
        self._last_transition = time.perf_counter_ns()
        self._power_draw_ma = 0.0
    
    def set_state(self, state: PinState, timestamp_ns: int = None):
        # Sub-microsecond state transitions
        pass
```

### 2. I2C Protocol Simulator

**Purpose**: Full I2C protocol simulation with bus arbitration

**Features**:
- Multi-master support with collision detection
- Clock stretching simulation
- NAK/ACK timing accurate to protocol spec
- Bus capacitance effects
- Address collision detection
- 10-bit addressing support

**Key Scenarios**:
- Device not responding (timeout)
- Clock stretching by slow devices
- Multi-master arbitration conflicts
- Electrical noise injection
- Partial byte transmission failures

### 3. SPI Protocol Simulator

**Purpose**: Bidirectional SPI communication with timing accuracy

**Features**:
- All 4 SPI modes (CPOL/CPHA combinations)
- Variable clock speeds with jitter simulation
- Multi-slave support with chip select
- MISO/MOSI collision detection
- DMA transfer simulation
- Clock phase relationship modeling

### 4. UART Emulator

**Purpose**: Serial communication with realistic timing

**Features**:
- Baud rate mismatch detection
- Framing error injection
- Parity error simulation
- Buffer overflow scenarios
- Break condition handling
- Hardware flow control (RTS/CTS)

## Virtual Device Registry

### Device Template System

Pre-built device templates for common components:

```yaml
# Example: BME280 Temperature Sensor Template
bme280:
  type: i2c
  addresses: [0x76, 0x77]
  registers:
    0xD0: 0x60  # Chip ID
    0xF4: 0x00  # Control register
  timing:
    conversion_time_ms: 113.25
    startup_time_ms: 2
  behaviors:
    - on_write: [0xF4, 0x27]  # Start measurement
      after_ms: 113.25
      update_registers:
        0xF7: [temp_msb, temp_lsb, temp_xlsb]
```

### Timing Engine

**Precision**: Nanosecond resolution using `time.perf_counter_ns()`

**Features**:
- Deterministic timing for reproducible tests
- Time dilation for slow-motion debugging
- Fast-forward for long-duration tests
- Synchronized multi-device timing

### Event Sequencer

Record and replay hardware interaction sequences:

```python
sequence = EventSequence()
sequence.add(0, I2CWrite(0x76, [0xF4, 0x27]))
sequence.add(113_250_000, I2CRead(0x76, 0xF7, count=6))
sequence.play(speed_multiplier=1000)  # 1000x faster
```

## Mock Infrastructure Core

### Event Bus

- Zero-copy message passing between mock components
- Event recording for debugging
- Time-travel debugging support
- Performance metrics collection

### State Manager

- Global hardware state snapshot/restore
- Conflict detection between interfaces
- Power budget tracking
- Thermal modeling (optional)

### Performance Monitor

- Mock operation timing statistics
- Overhead measurement
- Test execution profiling
- Bottleneck identification

## Failure Injection Capabilities

### Electrical Failures
- Voltage brownouts
- Ground loops
- EMI injection
- Pull-up resistor failures

### Protocol Failures
- Bit flips during transmission
- Clock glitches
- Arbitration losses
- Timing violations

### System Failures
- Kernel driver crashes
- File descriptor exhaustion
- Memory pressure scenarios
- CPU throttling effects

## Performance Targets

| Operation | Target Latency | Current (Real HW) |
|-----------|---------------|-------------------|
| GPIO Read | < 100ns | ~1µs |
| GPIO Write | < 100ns | ~1µs |
| I2C Transaction | < 1µs | ~100µs |
| SPI Transfer (1KB) | < 10µs | ~1ms |
| UART Byte | < 500ns | ~87µs (@115200) |

## Integration with Existing Architecture

### Minimal Changes Required

1. **Device Detector**: Add mock device injection
2. **Data Processor**: No changes needed
3. **Device Manager**: No changes needed

### Configuration

```yaml
# config/mock_hardware.yaml
mock_mode:
  enabled: true
  timing_mode: "deterministic"  # or "realistic"
  performance_target: "maximum"  # or "realistic"
  
devices:
  - type: gpio
    pins: [17, 27, 22]
    initial_states: ["high", "low", "floating"]
    
  - type: i2c
    bus: 1
    devices:
      - template: bme280
        address: 0x76
```

## Testing Patterns

### Pattern 1: Time-Critical Testing
```python
async def test_gpio_interrupt_latency():
    gpio = MockGPIO()
    latencies = []
    
    async def interrupt_handler():
        latencies.append(gpio.get_last_edge_timestamp())
    
    gpio.on_edge(17, Edge.RISING, interrupt_handler)
    
    # Generate 1000 interrupts
    for _ in range(1000):
        await gpio.set_pin(17, HIGH)
        await gpio.set_pin(17, LOW)
    
    assert max(latencies) < 100  # nanoseconds
```

### Pattern 2: Failure Injection
```python
def test_i2c_recovery_from_stuck_bus():
    i2c = MockI2C()
    i2c.inject_fault(FaultType.CLOCK_STUCK_LOW, duration_ms=10)
    
    # Your recovery code here
    result = i2c_driver.recover_from_stuck_bus()
    
    assert result == RecoveryStatus.SUCCESS
    assert i2c.get_bus_state() == BusState.IDLE
```

### Pattern 3: Protocol Verification
```python
def test_spi_mode_3_timing():
    spi = MockSPI(mode=3)  # CPOL=1, CPHA=1
    trace = spi.enable_protocol_trace()
    
    spi.transfer([0xAA, 0x55])
    
    # Verify clock is high when idle
    assert trace.clock_idle_state == HIGH
    # Verify data is sampled on falling edge
    assert trace.sample_edge == Edge.FALLING
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- Event bus and state manager
- Basic timing engine
- Performance monitoring framework

### Phase 2: GPIO Implementation (Week 3)
- Virtual state machine
- Edge detection and interrupts
- Basic failure injection

### Phase 3: I2C Implementation (Week 4)
- Protocol state machine
- Multi-master support
- Common device templates

### Phase 4: SPI Implementation (Week 5)
- Full duplex simulation
- DMA support
- Timing accuracy verification

### Phase 5: UART Implementation (Week 6)
- Baud rate simulation
- Error injection
- Flow control

### Phase 6: Integration (Week 7-8)
- CI/CD integration
- Performance optimization
- Documentation and examples

## Success Metrics

1. **Test Execution Speed**: 100x faster than hardware tests
2. **Coverage**: 100% of hardware interaction paths tested
3. **Failure Scenarios**: 50+ unique failure modes testable
4. **Developer Experience**: < 5 minutes to add new device mock
5. **CI/CD Time**: Full test suite < 30 seconds

## Future Enhancements

1. **WebAssembly Compilation**: Run mocks in browser for demos
2. **Hardware Trace Import**: Import real hardware traces for replay
3. **AI-Driven Fuzzing**: ML-based failure scenario generation
4. **Visual Debugger**: Web UI for hardware state inspection
5. **Cross-Platform Support**: Mock RPi4 on x86 development machines