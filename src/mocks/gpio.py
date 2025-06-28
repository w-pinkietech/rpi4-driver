"""GPIO Mock implementation with interrupt simulation"""

import threading
import queue
import time
from typing import Dict, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass

from .base import BaseMock, MockException, MockState
from .timing import TimingEngine


class PinMode(Enum):
    """GPIO pin modes"""
    INPUT = "input"
    OUTPUT = "output"
    

class PinPull(Enum):
    """GPIO pull resistor configuration"""
    OFF = "off"
    DOWN = "down"
    UP = "up"
    

class EdgeType(Enum):
    """GPIO edge detection types"""
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"
    

@dataclass
class PinState:
    """Complete state of a GPIO pin"""
    mode: PinMode = PinMode.INPUT
    value: int = 0
    pull: PinPull = PinPull.OFF
    edge_detection: Optional[EdgeType] = None
    

@dataclass
class EdgeEvent:
    """GPIO edge event"""
    pin: int
    edge_type: EdgeType
    timestamp: float
    value: int


class GPIOMock(BaseMock):
    """GPIO mock with realistic interrupt and timing simulation"""
    
    # RPi4 has 28 GPIO pins (0-27)
    VALID_PINS = list(range(28))
    
    def __init__(self, timing_engine: Optional[TimingEngine] = None):
        super().__init__("GPIO")
        self.timing_engine = timing_engine or TimingEngine()
        self.pin_states: Dict[int, PinState] = {}
        self.edge_callbacks: Dict[int, List[Callable]] = {}
        self.interrupt_queue = queue.Queue()
        self.interrupt_thread: Optional[threading.Thread] = None
        self.debounce_us: Dict[int, float] = {}
        self.last_edge_time: Dict[int, float] = {}
        
    def initialize(self, **kwargs) -> None:
        """Initialize GPIO mock"""
        self.set_state(MockState.INITIALIZED)
        
        # Start interrupt processing thread
        self.interrupt_thread = threading.Thread(
            target=self._interrupt_processor,
            daemon=True
        )
        self.interrupt_thread.start()
        
        self.set_state(MockState.ACTIVE)
        
    def shutdown(self) -> None:
        """Shutdown GPIO mock"""
        self.set_state(MockState.SHUTDOWN)
        
        # Stop interrupt thread
        if self.interrupt_thread:
            self.interrupt_queue.put(None)  # Sentinel
            self.interrupt_thread.join(timeout=1.0)
            
        # Clear all states
        self.pin_states.clear()
        self.edge_callbacks.clear()
        
    def setup(self, pin: int, mode: str, pull_up_down: Optional[str] = None) -> None:
        """
        Configure GPIO pin
        
        Args:
            pin: Pin number (0-27)
            mode: 'input' or 'output'
            pull_up_down: 'up', 'down', or None
        """
        start_time = time.time()
        
        try:
            # Validate pin
            if pin not in self.VALID_PINS:
                raise MockException(f"Invalid pin number: {pin}")
                
            # Validate mode
            try:
                pin_mode = PinMode(mode.lower())
            except ValueError:
                raise MockException(f"Invalid mode: {mode}")
                
            # Validate pull
            pull = PinPull.OFF
            if pull_up_down:
                try:
                    pull = PinPull(pull_up_down.lower())
                except ValueError:
                    raise MockException(f"Invalid pull setting: {pull_up_down}")
                    
            # Simulate setup time (50ns)
            self.timing_engine.delay_ns(50)
            
            # Update pin state
            if pin not in self.pin_states:
                self.pin_states[pin] = PinState()
                
            self.pin_states[pin].mode = pin_mode
            self.pin_states[pin].pull = pull
            
            # If input with pull resistor, set initial value
            if pin_mode == PinMode.INPUT:
                if pull == PinPull.UP:
                    self.pin_states[pin].value = 1
                elif pull == PinPull.DOWN:
                    self.pin_states[pin].value = 0
                    
            self._emit_event('pin_setup', {
                'pin': pin,
                'mode': mode,
                'pull': pull_up_down
            })
            
        finally:
            duration = time.time() - start_time
            self._record_operation(duration)
            
    def output(self, pin: int, value: int) -> None:
        """
        Set output pin value
        
        Args:
            pin: Pin number
            value: 0 or 1
        """
        start_time = time.time()
        
        try:
            # Validate
            if pin not in self.pin_states:
                raise MockException(f"Pin {pin} not configured")
                
            if self.pin_states[pin].mode != PinMode.OUTPUT:
                raise MockException(f"Pin {pin} not in output mode")
                
            if value not in (0, 1):
                raise MockException(f"Invalid value: {value}")
                
            # Simulate propagation delay (10ns)
            self.timing_engine.delay_ns(10)
            
            # Update value
            old_value = self.pin_states[pin].value
            self.pin_states[pin].value = value
            
            if old_value != value:
                self._emit_event('pin_change', {
                    'pin': pin,
                    'old_value': old_value,
                    'new_value': value
                })
                
        finally:
            duration = time.time() - start_time
            self._record_operation(duration)
            
    def input(self, pin: int) -> int:
        """
        Read input pin value
        
        Args:
            pin: Pin number
            
        Returns:
            Pin value (0 or 1)
        """
        start_time = time.time()
        
        try:
            # Validate
            if pin not in self.pin_states:
                raise MockException(f"Pin {pin} not configured")
                
            # Simulate read time (5ns)
            self.timing_engine.delay_ns(5)
            
            return self.pin_states[pin].value
            
        finally:
            duration = time.time() - start_time
            self._record_operation(duration)
            
    def add_event_detect(self, pin: int, edge: str, 
                        callback: Optional[Callable] = None,
                        bouncetime: Optional[int] = None) -> None:
        """
        Add edge detection to pin
        
        Args:
            pin: Pin number
            edge: 'rising', 'falling', or 'both'
            callback: Function to call on edge
            bouncetime: Debounce time in milliseconds
        """
        # Validate
        if pin not in self.pin_states:
            raise MockException(f"Pin {pin} not configured")
            
        if self.pin_states[pin].mode != PinMode.INPUT:
            raise MockException(f"Pin {pin} not in input mode")
            
        try:
            edge_type = EdgeType(edge.lower())
        except ValueError:
            raise MockException(f"Invalid edge type: {edge}")
            
        # Configure edge detection
        self.pin_states[pin].edge_detection = edge_type
        
        # Set debounce time
        if bouncetime:
            self.debounce_us[pin] = bouncetime * 1000.0
        else:
            self.debounce_us[pin] = 0
            
        # Add callback
        if callback:
            if pin not in self.edge_callbacks:
                self.edge_callbacks[pin] = []
            self.edge_callbacks[pin].append(callback)
            
        self._emit_event('edge_detect_added', {
            'pin': pin,
            'edge': edge,
            'has_callback': callback is not None
        })
        
    def remove_event_detect(self, pin: int) -> None:
        """Remove edge detection from pin"""
        if pin in self.pin_states:
            self.pin_states[pin].edge_detection = None
            
        if pin in self.edge_callbacks:
            del self.edge_callbacks[pin]
            
        if pin in self.debounce_us:
            del self.debounce_us[pin]
            
    def simulate_edge(self, pin: int, new_value: int, delay_us: float = 0) -> None:
        """
        Simulate edge event on input pin
        
        Args:
            pin: Pin number
            new_value: New pin value (0 or 1)
            delay_us: Delay before edge occurs
        """
        if pin not in self.pin_states:
            raise MockException(f"Pin {pin} not configured")
            
        if self.pin_states[pin].mode != PinMode.OUTPUT:
            # Schedule the edge event
            def apply_edge():
                current_time = self.timing_engine.clock.get_time_us()
                
                # Check debounce
                if pin in self.last_edge_time:
                    time_since_last = current_time - self.last_edge_time[pin]
                    if time_since_last < self.debounce_us.get(pin, 0):
                        return  # Ignore due to debounce
                        
                old_value = self.pin_states[pin].value
                self.pin_states[pin].value = new_value
                
                # Determine edge type
                if old_value == 0 and new_value == 1:
                    edge_type = EdgeType.RISING
                elif old_value == 1 and new_value == 0:
                    edge_type = EdgeType.FALLING
                else:
                    return  # No edge
                    
                # Check if we should detect this edge
                detection = self.pin_states[pin].edge_detection
                if detection:
                    if detection == EdgeType.BOTH or detection == edge_type:
                        # Create edge event
                        event = EdgeEvent(
                            pin=pin,
                            edge_type=edge_type,
                            timestamp=current_time,
                            value=new_value
                        )
                        self.interrupt_queue.put(event)
                        
                self.last_edge_time[pin] = current_time
                
            if delay_us > 0:
                self.timing_engine.schedule_event(delay_us, apply_edge)
            else:
                apply_edge()
                
    def _interrupt_processor(self) -> None:
        """Background thread to process interrupts"""
        while self.get_state() != MockState.SHUTDOWN:
            try:
                # Wait for edge event
                event = self.interrupt_queue.get(timeout=0.1)
                
                if event is None:  # Sentinel
                    break
                    
                # Process callbacks
                if event.pin in self.edge_callbacks:
                    for callback in self.edge_callbacks[event.pin]:
                        try:
                            callback(event.pin)
                        except Exception as e:
                            print(f"Error in GPIO callback: {e}")
                            
            except queue.Empty:
                continue
                
    def _handle_injected_error(self, error_type: str, **kwargs) -> None:
        """Handle injected errors"""
        if error_type == "stuck_pin":
            pin = kwargs.get('pin')
            value = kwargs.get('value', 0)
            if pin in self.pin_states:
                self.pin_states[pin].value = value
                # Prevent further changes
                self.pin_states[pin].mode = PinMode.INPUT
                
        elif error_type == "floating_pin":
            pin = kwargs.get('pin')
            if pin in self.pin_states:
                # Simulate floating by random value changes
                import random
                def float_pin():
                    if pin in self.pin_states:
                        self.pin_states[pin].value = random.randint(0, 1)
                        self.timing_engine.schedule_event(
                            random.uniform(1000, 10000),  # 1-10ms
                            float_pin
                        )
                float_pin()
                
        else:
            raise MockException(f"Unknown error type: {error_type}")
            
    def get_pin_state(self, pin: int) -> Optional[PinState]:
        """Get complete state of a pin"""
        return self.pin_states.get(pin)
        
    def get_all_pin_states(self) -> Dict[int, PinState]:
        """Get states of all configured pins"""
        return self.pin_states.copy()