# Sub-Issue: SPI Protocol Simulator Implementation

## Title
Create High-Speed SPI Protocol Simulator with Full-Duplex Support

## Description
Build a comprehensive SPI bus simulator supporting all SPI modes, variable clock speeds, multi-slave configurations, and DMA-style bulk transfers.

## Background
As part of the Hardware Mock-Driven Testing Strategy (#28), we need an SPI simulator that can:
- Support all 4 SPI modes (CPOL/CPHA combinations)
- Handle full-duplex communication
- Simulate realistic timing with nanosecond precision
- Enable testing of high-speed transfers and edge cases

## Requirements

### Protocol Features
- [ ] All SPI modes (0, 1, 2, 3)
- [ ] Configurable clock speeds (up to 50MHz)
- [ ] Full-duplex operation
- [ ] Multi-slave support
- [ ] Chip select management
- [ ] MSB/LSB first options

### Timing Simulation
- [ ] Clock generation with jitter
- [ ] Setup/hold time enforcement
- [ ] Propagation delay modeling
- [ ] Clock-to-output delays
- [ ] Inter-byte gaps

### Advanced Features
- [ ] DMA-style bulk transfers
- [ ] Hardware CS timing
- [ ] 3-wire mode support
- [ ] Daisy-chain topology
- [ ] Clock phase relationships

### Failure Modes
- [ ] Clock glitches
- [ ] CS timing violations
- [ ] MISO/MOSI collisions
- [ ] Setup/hold violations
- [ ] Clock frequency drift
- [ ] Bit corruption

## Technical Approach

### SPI Mode Definitions
```python
class SPIMode:
    def __init__(self, mode: int):
        self.cpol = (mode & 0x02) >> 1  # Clock polarity
        self.cpha = mode & 0x01         # Clock phase
        self.idle_state = self.cpol
        self.sample_edge = Edge.FALLING if (self.cpol ^ self.cpha) else Edge.RISING
        self.shift_edge = Edge.RISING if (self.cpol ^ self.cpha) else Edge.FALLING
```

### Timing Engine
```python
class SPITimingEngine:
    def __init__(self, clock_hz: int):
        self.period_ns = 1_000_000_000 // clock_hz
        self.half_period_ns = self.period_ns // 2
        self.setup_time_ns = max(10, self.period_ns // 20)  # 5% of period
        self.hold_time_ns = max(10, self.period_ns // 20)
        self.cs_setup_ns = 50
        self.cs_hold_ns = 50
```

### Transfer Simulation
```python
class SPITransfer:
    async def full_duplex_byte(self, mosi_byte: int) -> int:
        miso_byte = 0
        for bit in range(8):
            # Set MOSI
            await self.set_mosi(bool(mosi_byte & (0x80 >> bit)))
            
            # Generate clock edge
            await self.clock_edge(self.mode.shift_edge)
            
            # Sample MISO
            if await self.get_miso():
                miso_byte |= (0x80 >> bit)
            
            # Complete clock cycle
            await self.clock_edge(self.mode.sample_edge)
        
        return miso_byte
```

## Implementation Tasks

1. **Core Protocol Engine** (2 days)
   - SPI mode handling
   - Clock generation
   - Bit-level transfers

2. **Timing Simulator** (2 days)
   - Nanosecond precision timing
   - Setup/hold checking
   - Jitter injection

3. **Multi-Slave Support** (1 day)
   - CS decoder logic
   - Slave selection
   - Daisy-chain support

4. **DMA Simulation** (2 days)
   - Bulk transfer optimization
   - FIFO modeling
   - Interrupt generation

5. **Device Templates** (2 days)
   - Common SPI devices
   - Response scripting
   - Timing profiles

6. **Integration** (1 day)
   - spidev compatibility
   - Performance optimization
   - Test migration

## Device Templates to Include

### Display Controllers
- ILI9341 (TFT display)
- SSD1351 (OLED display)
- MAX7219 (LED matrix)

### Sensors
- MPU9250 (9-axis IMU)
- MAX31855 (thermocouple)
- MCP3008 (ADC)

### Memory
- W25Q64 (Flash memory)
- 23LC1024 (SRAM)

### Communication
- MCP2515 (CAN controller)
- ENC28J60 (Ethernet)

## Performance Optimization

### Strategies
1. **Bit-banging optimization**
   - Pre-compute bit patterns
   - Unroll inner loops
   - Use bitwise operations

2. **Bulk transfers**
   - Vectorized operations
   - Memory-mapped buffers
   - Zero-copy transfers

3. **Caching**
   - Device response caching
   - Timing parameter caching
   - State machine optimization

## Success Criteria
- [ ] All 4 SPI modes working correctly
- [ ] Support for 125MHz simulated clock
- [ ] < 10µs overhead for 1KB transfer
- [ ] 15+ device templates
- [ ] Timing accuracy within 1ns
- [ ] Multi-slave configurations working

## Performance Targets
| Operation | Target | Notes |
|-----------|---------|-------|
| Single byte | < 200ns | Overhead only |
| 1KB transfer | < 10µs | At 10MHz clock |
| 1MB transfer | < 10ms | With DMA simulation |
| Mode switch | < 100ns | Between transfers |

## Testing Strategy

### Unit Tests
- Mode behavior verification
- Timing accuracy tests
- Edge case handling

### Integration Tests
- Multi-slave scenarios
- Long transfers
- Mode switching

### Stress Tests
- 1M transfers without memory leaks
- Concurrent multi-slave access
- Maximum clock rates

## Dependencies
- Python 3.11+
- NumPy (for bulk operations)
- Hardware Mock Core (#28)

## Estimated Effort
10 developer days

## Labels
`mock-implementation`, `spi`, `testing`, `competitor-1`