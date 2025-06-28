#!/usr/bin/env python3
"""
Property-Based Contract Tests
Tests that verify interface implementations satisfy their contracts
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
import time
from typing import Dict, List, Any

# Import contract framework
from src.contracts.contract_verifier import (
    InterfaceContract,
    ContractVerifier,
    GPIOContractVerifier
)
from src.contracts.mock_generator import create_contract_compliant_mock


class GPIOStateMachine(RuleBasedStateMachine):
    """
    Property-based test for GPIO contract.
    Generates random sequences of GPIO operations and verifies contract.
    """
    
    def __init__(self):
        super().__init__()
        # Create contract-compliant mock
        self.gpio = create_contract_compliant_mock("GPIO")
        self.contract = InterfaceContract("contracts/gpio.contract.yaml")
        self.verifier = GPIOContractVerifier(self.contract, self.gpio)
        
        # Track state for test
        self.initialized = False
        self.pin_states = {}
        
        # Valid RPi4 pins from contract
        self.valid_pins = list(range(2, 28))
    
    @rule()
    def initialize(self):
        """Test GPIO initialization"""
        if not self.initialized:
            result, success = self.verifier.execute_with_verification("initialize")
            assert success, f"Contract violation: {self.verifier.violations[-1]}"
            self.initialized = True
    
    @precondition(lambda self: self.initialized)
    @rule(pin=st.integers(min_value=2, max_value=27),
          direction=st.sampled_from(['INPUT', 'OUTPUT']))
    def set_direction(self, pin: int, direction: str):
        """Test setting pin direction"""
        result, success = self.verifier.execute_with_verification(
            "set_direction", pin_id=pin, direction=direction
        )
        assert success, f"Contract violation: {self.verifier.violations[-1]}"
        
        # Track state
        if pin not in self.pin_states:
            self.pin_states[pin] = {}
        self.pin_states[pin]['direction'] = direction
        
        # Verify postcondition: OUTPUT pins start LOW
        if direction == 'OUTPUT':
            state = self.gpio.get_state()
            assert state['pins'][pin]['value'] == 'LOW'
    
    @precondition(lambda self: self.initialized)
    @rule(pin=st.integers(min_value=2, max_value=27))
    def read_pin(self, pin: int):
        """Test reading pin value"""
        result, success = self.verifier.execute_with_verification(
            "read", pin_id=pin
        )
        assert success, f"Contract violation: {self.verifier.violations[-1]}"
        assert result in ['HIGH', 'LOW'], f"Invalid read result: {result}"
    
    @precondition(lambda self: self.initialized)
    @rule(pin=st.integers(min_value=2, max_value=27),
          value=st.sampled_from(['HIGH', 'LOW']))
    def write_pin(self, pin: int, value: str):
        """Test writing to pins"""
        # First check if pin is OUTPUT
        state = self.gpio.get_state()
        if state['pins'].get(pin, {}).get('direction') != 'OUTPUT':
            # Try to write to non-OUTPUT pin - should fail
            with pytest.raises(RuntimeError) as exc_info:
                self.gpio.execute_operation("write", pin_id=pin, value=value)
            assert "INVALID_DIRECTION" in str(exc_info.value)
        else:
            # Should succeed
            result, success = self.verifier.execute_with_verification(
                "write", pin_id=pin, value=value
            )
            assert success, f"Contract violation: {self.verifier.violations[-1]}"
            
            # Verify we can read back the written value
            read_result, _ = self.verifier.execute_with_verification("read", pin_id=pin)
            assert read_result == value, f"Read after write mismatch"
    
    @precondition(lambda self: self.initialized)
    @rule(pin=st.integers(min_value=2, max_value=27),
          pull=st.sampled_from(['PULL_UP', 'PULL_DOWN', 'NONE']))
    def set_pull(self, pin: int, pull: str):
        """Test setting pull resistors"""
        state = self.gpio.get_state()
        if state['pins'].get(pin, {}).get('direction') != 'INPUT':
            # Should fail on OUTPUT pins
            with pytest.raises(RuntimeError) as exc_info:
                self.gpio.execute_operation("set_pull", pin_id=pin, pull=pull)
            assert "INVALID_DIRECTION" in str(exc_info.value)
        else:
            result, success = self.verifier.execute_with_verification(
                "set_pull", pin_id=pin, pull=pull
            )
            assert success, f"Contract violation: {self.verifier.violations[-1]}"
    
    @invariant()
    def all_invariants_hold(self):
        """Verify all GPIO invariants hold after each operation"""
        if self.initialized:
            assert self.verifier.verify_invariants(), \
                f"Invariant violation: {self.verifier.violations[-1]}"
    
    @invariant()
    def pin_independence(self):
        """Verify operations on one pin don't affect others"""
        if self.initialized and len(self.pin_states) > 1:
            state = self.gpio.get_state()
            for pin, expected in self.pin_states.items():
                actual = state['pins'].get(pin, {})
                if 'direction' in expected:
                    assert actual.get('direction') == expected['direction'], \
                        f"Pin {pin} direction changed unexpectedly"


class I2CStateMachine(RuleBasedStateMachine):
    """
    Property-based test for I2C contract.
    Tests bus state transitions and device operations.
    """
    
    def __init__(self):
        super().__init__()
        self.i2c = create_contract_compliant_mock("I2C")
        self.initialized = False
        self.known_devices = set()
    
    @rule(speed=st.sampled_from([100000, 400000, 1000000]))
    def initialize(self, speed: int):
        """Test I2C initialization with different speeds"""
        if not self.initialized:
            try:
                self.i2c.execute_operation("initialize", bus_id=1, speed=speed)
                self.initialized = True
            except RuntimeError as e:
                if "ALREADY_INITIALIZED" in str(e):
                    # Expected if already initialized
                    pass
                else:
                    raise
    
    @precondition(lambda self: self.initialized)
    @rule()
    def scan_bus(self):
        """Test I2C bus scanning"""
        devices = self.i2c.execute_operation("scan")
        
        # Verify contract postconditions
        assert isinstance(devices, list)
        assert all(0x08 <= addr <= 0x77 for addr in devices)
        
        # Update known devices
        self.known_devices.update(devices)
    
    @precondition(lambda self: self.initialized and len(self.known_devices) > 0)
    @rule(length=st.integers(min_value=1, max_value=32))
    def read_from_device(self, length: int):
        """Test reading from I2C devices"""
        device = next(iter(self.known_devices))
        
        try:
            data = self.i2c.execute_operation("read", address=device, length=length)
            
            # Verify contract postconditions
            assert isinstance(data, bytes)
            assert len(data) == length
            assert all(0 <= b <= 255 for b in data)
        except RuntimeError as e:
            # NACK is acceptable if device doesn't exist
            assert "NACK" in str(e)
    
    @precondition(lambda self: self.initialized)
    @rule(address=st.integers(min_value=0x08, max_value=0x77),
          data=st.binary(min_size=1, max_size=32))
    def write_to_device(self, address: int, data: bytes):
        """Test writing to I2C devices"""
        try:
            bytes_written = self.i2c.execute_operation(
                "write", address=address, data=data
            )
            
            # If successful, device exists
            if address not in self.known_devices:
                self.known_devices.add(address)
            
            # Verify postcondition
            assert bytes_written == len(data)
        except RuntimeError as e:
            # NACK is acceptable for non-existent devices
            assert "NACK" in str(e)
    
    @invariant()
    def bus_state_valid(self):
        """Verify bus is in valid state"""
        if self.initialized:
            state = self.i2c.get_state()
            assert state['bus']['state'] in ['IDLE', 'BUSY', 'ERROR']


# Property: Timing Constraints
@given(num_operations=st.integers(min_value=10, max_value=100))
def test_gpio_timing_constraints(num_operations: int):
    """Test that all GPIO operations meet timing constraints"""
    gpio = create_contract_compliant_mock("GPIO")
    contract = InterfaceContract("contracts/gpio.contract.yaml")
    
    gpio.execute_operation("initialize")
    
    for _ in range(num_operations):
        # Random operation
        pin = 17  # Use a fixed pin
        
        # Measure timing
        start = time.perf_counter()
        gpio.execute_operation("set_direction", pin_id=pin, direction="OUTPUT")
        duration_us = (time.perf_counter() - start) * 1e6
        
        # Check against contract
        timing = contract.get_timing_constraints("set_direction")
        assert duration_us <= timing['max_latency_us']


# Property: State Machine Transitions
def test_i2c_state_transitions():
    """Test that I2C state machine follows contract transitions"""
    i2c = create_contract_compliant_mock("I2C")
    
    # Initial state should be uninitialized
    with pytest.raises(RuntimeError):
        i2c.execute_operation("scan")  # Should fail when not initialized
    
    # After init, should be IDLE
    i2c.execute_operation("initialize", bus_id=1, speed=100000)
    state = i2c.get_state()
    assert state['bus']['state'] == 'IDLE'
    
    # During scan, state transitions through BUSY
    devices = i2c.execute_operation("scan")
    state = i2c.get_state()
    assert state['bus']['state'] == 'IDLE'  # Back to IDLE after scan


# Property: Contract Composition
class MultiInterfaceStateMachine(RuleBasedStateMachine):
    """Test multiple interfaces working together (GPIO + I2C)"""
    
    def __init__(self):
        super().__init__()
        self.gpio = create_contract_compliant_mock("GPIO")
        self.i2c = create_contract_compliant_mock("I2C")
        self.gpio_initialized = False
        self.i2c_initialized = False
    
    @rule()
    def initialize_both(self):
        """Initialize both interfaces"""
        if not self.gpio_initialized:
            self.gpio.execute_operation("initialize")
            self.gpio_initialized = True
        
        if not self.i2c_initialized:
            self.i2c.execute_operation("initialize", bus_id=1, speed=100000)
            self.i2c_initialized = True
    
    @precondition(lambda self: self.gpio_initialized and self.i2c_initialized)
    @rule()
    def simulate_i2c_device_with_interrupt(self):
        """Simulate I2C device that uses GPIO for interrupts"""
        # Set GPIO pin as input for interrupt
        interrupt_pin = 17
        self.gpio.execute_operation(
            "set_direction", pin_id=interrupt_pin, direction="INPUT"
        )
        self.gpio.execute_operation(
            "set_pull", pin_id=interrupt_pin, pull="PULL_UP"
        )
        
        # Scan for I2C devices
        devices = self.i2c.execute_operation("scan")
        
        if devices:
            # Read from first device
            data = self.i2c.execute_operation(
                "read", address=devices[0], length=4
            )
            
            # Check interrupt pin
            interrupt_state = self.gpio.execute_operation(
                "read", pin_id=interrupt_pin
            )
            
            # Both operations should succeed without affecting each other
            assert isinstance(data, bytes)
            assert interrupt_state in ['HIGH', 'LOW']


# Test contract violation detection
def test_contract_violation_detection():
    """Test that contract violations are properly detected"""
    gpio = create_contract_compliant_mock("GPIO")
    contract = InterfaceContract("contracts/gpio.contract.yaml")
    verifier = GPIOContractVerifier(contract, gpio)
    
    # Try to write without initializing - should violate precondition
    result, success = verifier.execute_with_verification(
        "write", pin_id=17, value="HIGH"
    )
    
    assert not success
    assert len(verifier.violations) > 0
    assert verifier.violations[0].violation_type == "precondition"


# Performance test for contract verification overhead
@pytest.mark.benchmark
def test_contract_verification_overhead(benchmark):
    """Measure overhead of contract verification"""
    gpio = create_contract_compliant_mock("GPIO")
    gpio.execute_operation("initialize")
    gpio.execute_operation("set_direction", pin_id=17, direction="OUTPUT")
    
    def write_operation():
        gpio.execute_operation("write", pin_id=17, value="HIGH")
        gpio.execute_operation("write", pin_id=17, value="LOW")
    
    # Benchmark without verification
    result = benchmark(write_operation)


# Run property tests with different settings
TestGPIO = GPIOStateMachine.TestCase
TestGPIO.settings = settings(max_examples=100, deadline=None)

TestI2C = I2CStateMachine.TestCase
TestI2C.settings = settings(max_examples=50, deadline=None)

TestMulti = MultiInterfaceStateMachine.TestCase
TestMulti.settings = settings(max_examples=25, deadline=None)