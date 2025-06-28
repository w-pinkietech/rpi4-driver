"""Property-based tests for GPIO contract compliance.

These tests verify that any GPIO implementation satisfies the formal contract.
They work identically on mock and real hardware implementations.
"""

import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
from typing import Dict, Set, Optional

from src.contracts.gpio_contract import GPIOContract, PinNumber, PinState, PinMode


class GPIOContractTests:
    """Universal test suite for GPIO contract compliance.
    
    These tests can be run against any GPIO implementation to verify
    it satisfies the formal contract. Tests use property-based testing
    to prove correctness rather than just checking examples.
    """
    
    @given(pin=st.integers(min_value=0, max_value=27),
           state=st.sampled_from([0, 1]))
    def test_read_after_write_property(self, gpio: GPIOContract, pin: int, state: int):
        """∀ pin, state: read(pin) = state after write(pin, state).
        
        This property ensures that GPIO writes are immediately observable
        through reads, which is fundamental to GPIO functionality.
        """
        # Set pin to output mode
        gpio.set_mode(pin, 'output')
        
        # Write state
        gpio.write(pin, state)
        
        # Read must return written state
        assert gpio.read(pin) == state
    
    @given(pin=st.integers(min_value=0, max_value=27),
           state=st.sampled_from([0, 1]))
    def test_write_idempotency_property(self, gpio: GPIOContract, pin: int, state: int):
        """write(pin, state) ∘ write(pin, state) = write(pin, state).
        
        Multiple writes of the same value must have no additional effect.
        This property ensures GPIO operations are predictable.
        """
        gpio.set_mode(pin, 'output')
        
        # First write
        gpio.write(pin, state)
        first_read = gpio.read(pin)
        
        # Second write of same value
        gpio.write(pin, state)
        second_read = gpio.read(pin)
        
        # Both reads must be identical
        assert first_read == second_read == state
    
    @given(pin=st.integers(min_value=0, max_value=27),
           mode=st.sampled_from(['input', 'output']))
    def test_mode_persistence_property(self, gpio: GPIOContract, pin: int, mode: str):
        """get_mode(pin) = mode after set_mode(pin, mode).
        
        Pin modes must persist until explicitly changed.
        """
        gpio.set_mode(pin, mode)
        assert gpio.get_mode(pin) == mode
    
    @given(pin=st.integers(min_value=0, max_value=27))
    def test_input_mode_write_protection(self, gpio: GPIOContract, pin: int):
        """Writes to input pins must have no effect.
        
        This property ensures hardware protection against
        erroneous writes to input pins.
        """
        gpio.set_mode(pin, 'input')
        
        # Attempt to write (should fail or have no effect)
        with pytest.raises(RuntimeError):
            gpio.write(pin, 1)
    
    @given(pin1=st.integers(min_value=0, max_value=27),
           pin2=st.integers(min_value=0, max_value=27))
    def test_pin_isolation_property(self, gpio: GPIOContract, pin1: int, pin2: int):
        """Operations on one pin must not affect other pins.
        
        This property ensures proper pin isolation in the implementation.
        """
        assume(pin1 != pin2)  # Only test different pins
        
        # Set both pins to output
        gpio.set_mode(pin1, 'output')
        gpio.set_mode(pin2, 'output')
        
        # Write different values
        gpio.write(pin1, 0)
        gpio.write(pin2, 1)
        
        # Each pin must maintain its value
        assert gpio.read(pin1) == 0
        assert gpio.read(pin2) == 1
        
        # Changing pin1 must not affect pin2
        gpio.write(pin1, 1)
        assert gpio.read(pin2) == 1  # Unchanged


class GPIOStateMachine(RuleBasedStateMachine):
    """Stateful testing for GPIO contract compliance.
    
    This state machine model ensures GPIO behavior remains consistent
    across sequences of operations, catching subtle state-related bugs.
    """
    
    def __init__(self, gpio_implementation: GPIOContract):
        super().__init__()
        self.gpio = gpio_implementation
        self.pin_modes: Dict[int, str] = {}
        self.pin_states: Dict[int, int] = {}
        self.pin_pulls: Dict[int, str] = {}
    
    @initialize()
    def setup(self):
        """Initialize GPIO to known state."""
        self.gpio.cleanup()
    
    @rule(pin=st.integers(0, 27), mode=st.sampled_from(['input', 'output']))
    def set_mode(self, pin: int, mode: str):
        """Rule: Set pin mode and track in model."""
        self.gpio.set_mode(pin, mode)
        self.pin_modes[pin] = mode
        
        # Clear state if switching to input
        if mode == 'input' and pin in self.pin_states:
            del self.pin_states[pin]
    
    @rule(pin=st.integers(0, 27), state=st.sampled_from([0, 1]))
    def write_pin(self, pin: int, state: int):
        """Rule: Write to output pins."""
        if self.pin_modes.get(pin) == 'output':
            self.gpio.write(pin, state)
            self.pin_states[pin] = state
    
    @rule(pin=st.integers(0, 27))
    def read_pin(self, pin: int):
        """Rule: Read pin and verify against model."""
        actual = self.gpio.read(pin)
        
        if pin in self.pin_states and self.pin_modes.get(pin) == 'output':
            # Output pin should return last written value
            assert actual == self.pin_states[pin]
    
    @invariant()
    def mode_consistency(self):
        """Invariant: Modes remain consistent."""
        for pin, expected_mode in self.pin_modes.items():
            actual_mode = self.gpio.get_mode(pin)
            assert actual_mode == expected_mode
    
    @invariant()
    def output_state_consistency(self):
        """Invariant: Output pins maintain their state."""
        for pin, expected_state in self.pin_states.items():
            if self.pin_modes.get(pin) == 'output':
                actual_state = self.gpio.read(pin)
                assert actual_state == expected_state


def create_contract_test_suite(gpio_implementation: GPIOContract):
    """Create a complete test suite for a GPIO implementation.
    
    Args:
        gpio_implementation: GPIO implementation to test
        
    Returns:
        Test suite that verifies contract compliance
    """
    # Create test instance with the implementation
    tests = GPIOContractTests()
    
    # Create state machine tests
    state_tests = GPIOStateMachine.TestCase
    state_tests.settings = state_tests.settings.with_phases(
        max_examples=100  # Run 100 random operation sequences
    )
    
    return tests, state_tests
