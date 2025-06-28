# Sub-Issue: UART Emulator Implementation

## Title
Develop UART Emulator with Realistic Serial Communication

## Description
Create a comprehensive UART emulator that simulates serial communication with accurate timing, error injection, and flow control support.

## Background
As part of the Hardware Mock-Driven Testing Strategy (#28), we need a UART emulator that can:
- Simulate various baud rates with timing accuracy
- Inject realistic communication errors
- Support hardware and software flow control
- Enable testing of edge cases and error recovery

## Requirements

### Core Features
- [ ] Configurable baud rates (300 - 4Mbps)
- [ ] Data bits (5, 6, 7, 8)
- [ ] Stop bits (1, 1.5, 2)
- [ ] Parity (None, Even, Odd, Mark, Space)
- [ ] Full-duplex operation
- [ ] Break signal support

### Flow Control
- [ ] Hardware flow control (RTS/CTS)
- [ ] Software flow control (XON/XOFF)
- [ ] DTR/DSR signaling
- [ ] Custom flow control protocols

### Error Injection
- [ ] Framing errors
- [ ] Parity errors
- [ ] Overrun errors
- [ ] Buffer overflow
- [ ] Baud rate mismatch
- [ ] Line noise simulation

### Advanced Features
- [ ] FIFO buffer simulation
- [ ] DMA support
- [ ] Multi-port support
- [ ] RS-485 mode
- [ ] Loopback testing

## Technical Approach

### UART Frame Structure
```python
class UARTFrame:
    def __init__(self, data: int, config: UARTConfig):
        self.start_bit = 0
        self.data_bits = data & ((1 << config.data_bits) - 1)
        self.parity_bit = self._calculate_parity(data, config.parity)
        self.stop_bits = 0b11 if config.stop_bits == 2 else 0b1
        self.frame_time_ns = self._calculate_frame_time(config)
```

### Timing Simulation
```python
class UARTTiming:
    def __init__(self, baud_rate: int):
        self.bit_time_ns = 1_000_000_000 // baud_rate
        self.byte_time_ns = self.bit_time_ns * 10  # 1 start + 8 data + 1 stop
        
    def add_jitter(self, base_time_ns: int, jitter_percent: float) -> int:
        jitter_ns = int(base_time_ns * jitter_percent / 100)
        return base_time_ns + random.randint(-jitter_ns, jitter_ns)
```

### Error Injection System
```python
class UARTErrorInjector:
    def inject_framing_error(self, frame: UARTFrame) -> UARTFrame:
        # Corrupt stop bit
        frame.stop_bits = 0
        return frame
    
    def inject_parity_error(self, frame: UARTFrame) -> UARTFrame:
        # Flip parity bit
        frame.parity_bit ^= 1
        return frame
    
    def inject_noise(self, data: bytes, ber: float) -> bytes:
        # Bit Error Rate injection
        result = bytearray(data)
        for i in range(len(result) * 8):
            if random.random() < ber:
                byte_idx = i // 8
                bit_idx = i % 8
                result[byte_idx] ^= (1 << bit_idx)
        return bytes(result)
```

### Flow Control Implementation
```python
class FlowController:
    def __init__(self, mode: FlowControlMode):
        self.mode = mode
        self.rts = True
        self.cts = True
        self.xoff_received = False
        
    def can_transmit(self) -> bool:
        if self.mode == FlowControlMode.HARDWARE:
            return self.cts
        elif self.mode == FlowControlMode.SOFTWARE:
            return not self.xoff_received
        return True
```

## Implementation Tasks

1. **Core UART Engine** (2 days)
   - Frame generation/parsing
   - Timing simulation
   - Configuration management

2. **Buffer Management** (1 day)
   - FIFO implementation
   - Overflow detection
   - DMA simulation

3. **Error Injection** (2 days)
   - Error generators
   - Statistical models
   - Recovery testing

4. **Flow Control** (1 day)
   - Hardware signals
   - Software protocol
   - Custom protocols

5. **Multi-Port Support** (1 day)
   - Port management
   - Cross-port testing
   - Loopback modes

6. **Integration** (1 day)
   - pySerial compatibility
   - Performance optimization
   - Test migration

## Test Scenarios

### Basic Communication
```python
def test_basic_transmission():
    uart1 = MockUART(baud=115200)
    uart2 = MockUART(baud=115200)
    uart1.connect(uart2)  # Virtual connection
    
    uart1.write(b"Hello, World!")
    data = uart2.read(13)
    assert data == b"Hello, World!"
```

### Error Recovery
```python
def test_framing_error_recovery():
    uart = MockUART(baud=9600)
    uart.inject_error_rate(ErrorType.FRAMING, 0.1)  # 10% error rate
    
    sent = b"Test data with errors"
    uart.write(sent)
    
    received = uart.read_with_error_detection(len(sent))
    assert received.error_count > 0
    assert received.recovered_data == sent
```

### Flow Control
```python
def test_hardware_flow_control():
    uart = MockUART(flow_control=FlowControl.RTS_CTS)
    
    # Simulate buffer full
    uart.set_cts(False)
    written = uart.write_nonblocking(b"x" * 1000)
    assert written < 1000  # Should stop when CTS goes low
    
    # Resume transmission
    uart.set_cts(True)
    remaining = uart.flush()
    assert remaining == 1000 - written
```

## Performance Targets

| Operation | Target | Notes |
|-----------|---------|-------|
| Byte transmission | < 500ns | Overhead at 115200 baud |
| 1KB transfer | < 100µs | At 115200 baud simulation |
| Error injection | < 10ns | Per bit |
| Flow control check | < 50ns | Per byte |

## Baud Rate Accuracy

| Baud Rate | Max Error | Notes |
|-----------|-----------|-------|
| 300 | ±0.01% | Low speed |
| 9600 | ±0.01% | Standard |
| 115200 | ±0.01% | High speed |
| 1M | ±0.1% | Very high speed |
| 4M | ±0.5% | Maximum |

## Device Profiles

### Common Devices
- GPS modules (NMEA protocol)
- GSM modems (AT commands)
- Arduino (Serial protocol)
- RS-485 devices
- Industrial sensors

### Protocol Templates
```yaml
gps_module:
  type: uart_device
  baud: 9600
  format: 8N1
  protocols:
    - nmea
  responses:
    - pattern: "\$GPGGA"
      response: "$GPGGA,123456.00,3723.46587,N,12202.26957,W,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
      timing: periodic_1hz
```

## Success Criteria
- [ ] All standard baud rates supported
- [ ] < 0.01% timing accuracy
- [ ] 10+ error injection modes
- [ ] Flow control working correctly
- [ ] pySerial compatibility
- [ ] Zero memory leaks

## Dependencies
- Python 3.11+
- Hardware Mock Core (#28)

## Estimated Effort
8 developer days

## Labels
`mock-implementation`, `uart`, `testing`, `competitor-1`