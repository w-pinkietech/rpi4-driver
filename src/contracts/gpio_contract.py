"""GPIO Interface Contract Specification.

This module defines the formal contract that all GPIO implementations must satisfy.
The contract serves as both documentation and executable specification.
"""

from abc import ABC, abstractmethod
from typing import Literal, Callable, Optional, Protocol, runtime_checkable
from datetime import timedelta
import logging

# Type definitions for GPIO interface
PinNumber = int  # Constrained: 0 <= pin <= 27 for RPi4
PinState = Literal[0, 1]
PinMode = Literal['input', 'output']
PullMode = Literal['up', 'down', 'none']
EdgeType = Literal['rising', 'falling', 'both']

logger = logging.getLogger(__name__)


class GPIOContract(ABC):
    """Formal contract specification for GPIO interface.
    
    This abstract base class defines the complete behavioral contract
    that any GPIO implementation must satisfy. The contract includes:
    
    1. Type contracts: Static type constraints on parameters
    2. Behavioral contracts: Runtime behavior guarantees
    3. Temporal contracts: Timing and ordering guarantees
    
    Implementations must ensure all contract conditions are met.
    """
    
    # Contract Constants
    MIN_PIN = 0
    MAX_PIN = 27  # RPi4 has 28 GPIO pins (0-27)
    MAX_EDGE_LATENCY_MS = 1.0  # Maximum edge detection latency
    
    @abstractmethod
    def set_mode(self, pin: PinNumber, mode: PinMode) -> None:
        """Set the mode of a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Post: get_mode(pin) == mode
        - Post: If mode == 'input', write operations on pin have no effect
        - Post: If mode == 'output', pin can be written to
        - Invariant: Mode changes do not affect other pins
        
        Args:
            pin: GPIO pin number (0-27)
            mode: Pin mode ('input' or 'output')
            
        Raises:
            ValueError: If pin is out of range
            RuntimeError: If pin cannot be configured
        """
        pass
    
    @abstractmethod
    def get_mode(self, pin: PinNumber) -> PinMode:
        """Get the current mode of a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Post: Returns current pin mode
        - Invariant: Reading mode does not change pin state
        
        Args:
            pin: GPIO pin number (0-27)
            
        Returns:
            Current pin mode
            
        Raises:
            ValueError: If pin is out of range
        """
        pass
    
    @abstractmethod
    def read(self, pin: PinNumber) -> PinState:
        """Read the current state of a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Post: Returns 0 or 1
        - Post: If pin mode is 'output', returns last written value
        - Invariant: Reading does not change pin state
        
        Args:
            pin: GPIO pin number (0-27)
            
        Returns:
            Pin state (0 or 1)
            
        Raises:
            ValueError: If pin is out of range
        """
        pass
    
    @abstractmethod
    def write(self, pin: PinNumber, state: PinState) -> None:
        """Write a state to a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Pre: get_mode(pin) == 'output'
        - Post: read(pin) == state
        - Idempotency: write(pin, state); write(pin, state) ≡ write(pin, state)
        
        Args:
            pin: GPIO pin number (0-27)
            state: Pin state to write (0 or 1)
            
        Raises:
            ValueError: If pin is out of range
            RuntimeError: If pin is not in output mode
        """
        pass
    
    @abstractmethod
    def set_pull(self, pin: PinNumber, pull: PullMode) -> None:
        """Set the pull resistor mode for a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Pre: get_mode(pin) == 'input'
        - Post: get_pull(pin) == pull
        - Post: Pull mode affects pin reading when not externally driven
        
        Args:
            pin: GPIO pin number (0-27)
            pull: Pull resistor mode
            
        Raises:
            ValueError: If pin is out of range
            RuntimeError: If pin is not in input mode
        """
        pass
    
    @abstractmethod
    def get_pull(self, pin: PinNumber) -> PullMode:
        """Get the pull resistor mode for a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Post: Returns current pull mode
        
        Args:
            pin: GPIO pin number (0-27)
            
        Returns:
            Current pull mode
            
        Raises:
            ValueError: If pin is out of range
        """
        pass
    
    @abstractmethod
    def set_edge_detect(
        self,
        pin: PinNumber,
        edge: EdgeType,
        callback: Callable[[PinNumber], None],
        bounce_time: Optional[timedelta] = None
    ) -> None:
        """Set edge detection with callback for a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Pre: get_mode(pin) == 'input'
        - Post: Callback is called when specified edge is detected
        - Temporal: Callback latency < MAX_EDGE_LATENCY_MS
        - Temporal: If bounce_time set, edges within bounce_time are ignored
        
        Args:
            pin: GPIO pin number (0-27)
            edge: Edge type to detect
            callback: Function called on edge detection
            bounce_time: Minimum time between edge detections
            
        Raises:
            ValueError: If pin is out of range
            RuntimeError: If pin is not in input mode
        """
        pass
    
    @abstractmethod
    def remove_edge_detect(self, pin: PinNumber) -> None:
        """Remove edge detection from a GPIO pin.
        
        Contract conditions:
        - Pre: MIN_PIN <= pin <= MAX_PIN
        - Post: No callbacks triggered for pin edges
        - Post: Safe to call even if no edge detection was set
        
        Args:
            pin: GPIO pin number (0-27)
            
        Raises:
            ValueError: If pin is out of range
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up GPIO resources.
        
        Contract conditions:
        - Post: All pins released to default state
        - Post: All edge detection callbacks removed
        - Post: Safe to call multiple times
        - Invariant: Does not affect other GPIO instances
        """
        pass


@runtime_checkable
class GPIOProtocol(Protocol):
    """Static protocol for type checking GPIO implementations.
    
    This protocol enables static type checking without inheritance.
    Any class implementing these methods satisfies the protocol.
    """
    
    def set_mode(self, pin: int, mode: Literal['input', 'output']) -> None: ...
    def get_mode(self, pin: int) -> Literal['input', 'output']: ...
    def read(self, pin: int) -> Literal[0, 1]: ...
    def write(self, pin: int, state: Literal[0, 1]) -> None: ...
    def set_pull(self, pin: int, pull: Literal['up', 'down', 'none']) -> None: ...
    def get_pull(self, pin: int) -> Literal['up', 'down', 'none']: ...
    def cleanup(self) -> None: ...
