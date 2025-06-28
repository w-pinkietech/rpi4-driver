# Contract-Based Testing Strategy for RPi4 Interface Drivers

## Philosophy: "The Interface IS the Test"

This document outlines a contract-based testing approach where interface specifications serve as executable truths. Every hardware interface behavior is expressed as mathematical properties that must hold true for both mock and real implementations.

## Core Principles

1. **Contracts as First-Class Citizens**: Interface contracts are the primary source of truth
2. **Property-Based Testing**: Express behavior as mathematical properties, not example-based tests
3. **Compile-Time Verification**: Where possible, enforce contracts at compile time
4. **Self-Documenting**: Contracts serve as both tests and documentation
5. **Implementation Agnostic**: Tests work identically on mocks and real hardware

## Formal Specification Language

We adopt a three-layer specification approach:

```python
# Layer 1: Type Contracts (Static)
# Layer 2: Behavioral Contracts (Runtime)
# Layer 3: Temporal Contracts (Time-based)
```

## Interface Specifications

### GPIO Contract Specification

```python
from abc import ABC, abstractmethod
from typing import Literal, Callable, Optional
from datetime import timedelta
import hypothesis.strategies as st
from hypothesis import given, assume

class GPIOContract(ABC):
    """Formal specification for GPIO interface."""
    
    # Type Contracts
    PinNumber = int  # Constrained: 0 <= pin <= 27
    PinState = Literal[0, 1]
    PinMode = Literal['input', 'output']
    PullMode = Literal['up', 'down', 'none']
    EdgeType = Literal['rising', 'falling', 'both']
    
    # Behavioral Contracts
    @abstractmethod
    def set_mode(self, pin: PinNumber, mode: PinMode) -> None:
        """Contract: pin mode must be observable immediately after setting."""
        pass
    
    @abstractmethod
    def read(self, pin: PinNumber) -> PinState:
        """Contract: read() after write(pin, state) must return state."""
        pass
    
    @abstractmethod
    def write(self, pin: PinNumber, state: PinState) -> None:
        """Contract: write is idempotent - writing same state twice has no additional effect."""
        pass
    
    # Temporal Contracts
    @abstractmethod
    def set_edge_detect(self, pin: PinNumber, edge: EdgeType, 
                       callback: Callable[[PinNumber], None],
                       bounce_time: Optional[timedelta] = None) -> None:
        """Contract: callback must be called within 1ms of edge detection."""
        pass

# Property-Based Test Example
class GPIOContractTest:
    """Universal test suite for any GPIO implementation."""
    
    @given(pin=st.integers(min_value=0, max_value=27),
           state=st.sampled_from([0, 1]))
    def test_read_after_write_property(self, gpio: GPIOContract, pin: int, state: int):
        """Property: ∀ pin, state: read(pin) = state after write(pin, state)"""
        gpio.set_mode(pin, 'output')
        gpio.write(pin, state)
        assert gpio.read(pin) == state
    
    @given(pin=st.integers(min_value=0, max_value=27))
    def test_idempotency_property(self, gpio: GPIOContract, pin: int):
        """Property: write(pin, state) ∘ write(pin, state) = write(pin, state)"""
        gpio.set_mode(pin, 'output')
        gpio.write(pin, 1)
        first_read = gpio.read(pin)
        gpio.write(pin, 1)  # Write same value again
        second_read = gpio.read(pin)
        assert first_read == second_read
```

### I2C Contract Specification

```python
class I2CContract(ABC):
    """Formal specification for I2C interface."""
    
    # Type Contracts
    Address = int  # Constrained: 0x08 <= addr <= 0x77 (7-bit addressing)
    Speed = Literal[100_000, 400_000, 1_000_000]  # Hz
    Data = bytes
    
    # Behavioral Contracts
    @abstractmethod
    def write(self, address: Address, data: Data) -> None:
        """Contract: write must complete or raise exception within timeout."""
        pass
    
    @abstractmethod
    def read(self, address: Address, length: int) -> Data:
        """Contract: len(returned_data) == length or exception raised."""
        pass
    
    @abstractmethod
    def write_read(self, address: Address, write_data: Data, read_length: int) -> Data:
        """Contract: atomic write-then-read operation."""
        pass
    
    # Protocol Contracts
    def scan(self) -> list[Address]:
        """Contract: returned addresses must respond to read probe."""
        pass

# Property-Based Test
class I2CContractTest:
    @given(address=st.integers(min_value=0x08, max_value=0x77),
           data=st.binary(min_size=1, max_size=32))
    def test_write_read_consistency(self, i2c: I2CContract, address: int, data: bytes):
        """Property: data written can be read back (for memory devices)."""
        assume(self.is_memory_device(address))  # Filter for memory devices
        i2c.write(address, data)
        read_data = i2c.read(address, len(data))
        assert read_data == data
```

### SPI Contract Specification

```python
class SPIContract(ABC):
    """Formal specification for SPI interface."""
    
    # Type Contracts
    ChipSelect = int  # CS pin number
    Speed = int  # Constrained: 1 <= speed <= 50_000_000
    Mode = Literal[0, 1, 2, 3]  # SPI modes
    BitOrder = Literal['msb', 'lsb']
    
    # Behavioral Contracts
    @abstractmethod
    def transfer(self, tx_data: bytes) -> bytes:
        """Contract: len(rx_data) == len(tx_data) (full duplex)."""
        pass
    
    @abstractmethod
    def write(self, data: bytes) -> None:
        """Contract: write is transfer with rx_data ignored."""
        pass
    
    @abstractmethod
    def read(self, length: int) -> bytes:
        """Contract: read is transfer with tx_data = zeros."""
        pass
    
    # Timing Contracts
    @abstractmethod
    def set_speed(self, speed: Speed) -> None:
        """Contract: actual_speed <= requested_speed."""
        pass

# Property-Based Test
class SPIContractTest:
    @given(data=st.binary(min_size=1, max_size=4096))
    def test_full_duplex_property(self, spi: SPIContract, data: bytes):
        """Property: SPI is always full duplex - every TX has RX."""
        rx_data = spi.transfer(data)
        assert len(rx_data) == len(data)
```

### UART Contract Specification

```python
class UARTContract(ABC):
    """Formal specification for UART interface."""
    
    # Type Contracts
    BaudRate = Literal[9600, 19200, 38400, 57600, 115200]
    DataBits = Literal[5, 6, 7, 8]
    StopBits = Literal[1, 1.5, 2]
    Parity = Literal['none', 'even', 'odd']
    
    # Behavioral Contracts
    @abstractmethod
    def write(self, data: bytes) -> int:
        """Contract: returns number of bytes written."""
        pass
    
    @abstractmethod
    def read(self, max_bytes: int, timeout: Optional[float] = None) -> bytes:
        """Contract: len(data) <= max_bytes."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Contract: after flush(), tx buffer is empty."""
        pass
    
    # Auto-detection Contract
    @abstractmethod
    def auto_detect_baudrate(self) -> Optional[BaudRate]:
        """Contract: detected rate must successfully communicate."""
        pass

# Property-Based Test
class UARTContractTest:
    @given(data=st.binary(min_size=1, max_size=1024))
    def test_loopback_property(self, uart: UARTContract, data: bytes):
        """Property: In loopback mode, written data equals read data."""
        assume(self.is_loopback_mode(uart))
        written = uart.write(data)
        read_data = uart.read(written, timeout=1.0)
        assert read_data == data[:written]
```

## Contract Verification Tools

### 1. Static Contract Verification (Compile-Time)

```python
# Using Python type checkers with Protocol classes
from typing import Protocol, runtime_checkable

@runtime_checkable
class GPIOProtocol(Protocol):
    """Static contract verification using Protocol."""
    def set_mode(self, pin: int, mode: Literal['input', 'output']) -> None: ...
    def read(self, pin: int) -> Literal[0, 1]: ...
    def write(self, pin: int, state: Literal[0, 1]) -> None: ...

# Type checker will verify implementations match protocol
```

### 2. Runtime Contract Verification

```python
from contracts import contract, new_contract

# Define custom contracts
new_contract('gpio_pin', lambda x: 0 <= x <= 27)
new_contract('pin_state', lambda x: x in [0, 1])

class GPIOWithContracts:
    @contract(pin='gpio_pin', state='pin_state')
    def write(self, pin: int, state: int) -> None:
        """Runtime contract verification."""
        pass
```

### 3. Property-Based Testing Framework

```python
# Hypothesis for property-based testing
from hypothesis import given, strategies as st, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class GPIOStateMachine(RuleBasedStateMachine):
    """State machine testing for GPIO."""
    
    def __init__(self):
        super().__init__()
        self.gpio = self.get_gpio_implementation()
        self.pin_states = {}
    
    @rule(pin=st.integers(0, 27), mode=st.sampled_from(['input', 'output']))
    def set_mode(self, pin, mode):
        self.gpio.set_mode(pin, mode)
        self.pin_states[pin] = {'mode': mode}
    
    @invariant()
    def check_consistency(self):
        """Invariant: pin states must be consistent."""
        for pin, state in self.pin_states.items():
            if state.get('mode') == 'output' and 'value' in state:
                assert self.gpio.read(pin) == state['value']
```

## Implementation Strategy

### Phase 1: Contract Definition
1. Define formal contracts for each interface
2. Express timing constraints mathematically
3. Create protocol classes for static verification

### Phase 2: Test Generation
1. Implement property-based test generators
2. Create state machine models for stateful testing
3. Build contract compliance test suites

### Phase 3: Mock Implementation
1. Create contract-compliant mock implementations
2. Verify mocks pass all contract tests
3. Use mocks for development testing

### Phase 4: Hardware Validation
1. Run same contract tests on real hardware
2. Measure and document timing variations
3. Refine contracts based on hardware reality

## Success Metrics

1. **Specification Coverage**: 100% of interface behaviors specified
2. **Contract Compliance**: Both mocks and hardware pass same tests
3. **Property Coverage**: All behavioral properties tested
4. **Proof Strength**: Tests prove correctness, not just check examples
5. **Documentation**: Contracts serve as complete interface documentation

## Tools and Frameworks

### Recommended Stack
- **Hypothesis**: Property-based testing
- **PyContracts**: Runtime contract verification
- **mypy/pyright**: Static type checking
- **deal**: Design by contract for Python
- **icontract**: Another DbC library with better performance

### Alternative Approaches
- **Alloy**: Formal specification language
- **TLA+**: Temporal logic specifications
- **Z3**: SMT solver for constraint verification

## Next Steps

1. Create sub-issues for each interface contract implementation
2. Set up property-based testing infrastructure
3. Implement contract verification tooling
4. Create reference mock implementations
5. Document contract testing best practices
