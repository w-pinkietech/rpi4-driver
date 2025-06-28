"""UART Mock implementation with flow control and timing accuracy"""

import queue
import threading
import time
from typing import Optional, List, Callable
from enum import Enum
from dataclasses import dataclass

from .base import BaseMock, MockException, MockState
from .timing import TimingEngine


class FlowControl(Enum):
    """UART flow control modes"""
    NONE = "none"
    HARDWARE = "hardware"  # RTS/CTS
    SOFTWARE = "software"  # XON/XOFF
    

class Parity(Enum):
    """UART parity modes"""
    NONE = "none"
    EVEN = "even"
    ODD = "odd"
    MARK = "mark"
    SPACE = "space"
    

@dataclass
class UARTConfig:
    """UART configuration"""
    baudrate: int = 9600
    bytesize: int = 8
    parity: Parity = Parity.NONE
    stopbits: float = 1.0
    flow_control: FlowControl = FlowControl.NONE
    timeout: Optional[float] = None
    

@dataclass
class UARTFrame:
    """Single UART frame with metadata"""
    data: int
    timestamp: float
    parity_error: bool = False
    framing_error: bool = False
    break_detected: bool = False


class UARTMock(BaseMock):
    """UART interface mock with realistic timing and flow control"""
    
    # Flow control characters
    XON = 0x11   # DC1
    XOFF = 0x13  # DC3
    
    def __init__(self, port: str = "/dev/ttyS0", timing_engine: Optional[TimingEngine] = None):
        super().__init__(f"UART-{port}")
        self.port = port
        self.timing_engine = timing_engine or TimingEngine()
        self.config = UARTConfig()
        
        # Buffers
        self.tx_buffer = queue.Queue()
        self.rx_buffer = queue.Queue()
        
        # Flow control state
        self.rts = True  # Ready to Send
        self.cts = True  # Clear to Send
        self.xoff_received = False
        self.break_condition = False
        
        # Statistics
        self.bytes_transmitted = 0
        self.bytes_received = 0
        self.parity_errors = 0
        self.framing_errors = 0
        
        # Virtual peer connection
        self.peer: Optional['UARTMock'] = None
        self.loopback = False
        
    def initialize(self, config: Optional[UARTConfig] = None, **kwargs) -> None:
        """Initialize UART interface"""
        if config:
            self.config = config
        else:
            # Apply kwargs to config
            if 'baudrate' in kwargs:
                self.config.baudrate = kwargs['baudrate']
            if 'bytesize' in kwargs:
                self.config.bytesize = kwargs['bytesize']
            if 'parity' in kwargs:
                self.config.parity = Parity(kwargs['parity'])
            if 'stopbits' in kwargs:
                self.config.stopbits = kwargs['stopbits']
            if 'flow_control' in kwargs:
                self.config.flow_control = FlowControl(kwargs['flow_control'])
            if 'timeout' in kwargs:
                self.config.timeout = kwargs['timeout']
                
        self.set_state(MockState.INITIALIZED)
        self.set_state(MockState.ACTIVE)
        
    def shutdown(self) -> None:
        """Shutdown UART interface"""
        self.set_state(MockState.SHUTDOWN)
        
        # Clear buffers
        while not self.tx_buffer.empty():
            self.tx_buffer.get()
        while not self.rx_buffer.empty():
            self.rx_buffer.get()
            
    def write(self, data: bytes) -> int:
        """
        Write data to UART
        
        Args:
            data: Bytes to transmit
            
        Returns:
            Number of bytes written
        """
        start_time = time.time()
        bytes_written = 0
        
        try:
            for byte in data:
                # Check flow control
                if not self._can_transmit():
                    break
                    
                # Calculate transmission time
                self._simulate_byte_transmission(byte)
                
                # Add to TX buffer
                frame = UARTFrame(
                    data=byte,
                    timestamp=self.timing_engine.clock.get_time_us()
                )
                self.tx_buffer.put(frame)
                
                # If loopback or peer connected, handle reception
                if self.loopback:
                    self.rx_buffer.put(frame)
                elif self.peer:
                    self.peer.rx_buffer.put(frame)
                    
                bytes_written += 1
                self.bytes_transmitted += 1
                
            self._emit_event('data_transmitted', {
                'bytes': bytes_written,
                'data': data[:bytes_written]
            })
            
            return bytes_written
            
        finally:
            duration = time.time() - start_time
            self._record_operation(duration)
            
    def read(self, size: int = 1) -> bytes:
        """
        Read data from UART
        
        Args:
            size: Maximum number of bytes to read
            
        Returns:
            Received bytes
        """
        start_time = time.time()
        data = bytearray()
        timeout = self.config.timeout or 0
        deadline = start_time + timeout if timeout > 0 else None
        
        try:
            for _ in range(size):
                # Check timeout
                if deadline and time.time() > deadline:
                    break
                    
                try:
                    # Try to get frame from buffer
                    remaining = deadline - time.time() if deadline else None
                    frame = self.rx_buffer.get(timeout=remaining)
                    
                    # Check for errors
                    if frame.break_detected:
                        if data:
                            break  # Return data received so far
                        raise MockException("Break condition detected")
                        
                    if frame.parity_error:
                        self.parity_errors += 1
                    if frame.framing_error:
                        self.framing_errors += 1
                        
                    data.append(frame.data)
                    self.bytes_received += 1
                    
                    # Handle software flow control
                    if self.config.flow_control == FlowControl.SOFTWARE:
                        if frame.data == self.XOFF:
                            self.xoff_received = True
                        elif frame.data == self.XON:
                            self.xoff_received = False
                            
                except queue.Empty:
                    if deadline is None:
                        # No timeout, return what we have
                        break
                        
            if data:
                self._emit_event('data_received', {
                    'bytes': len(data),
                    'data': bytes(data)
                })
                
            return bytes(data)
            
        finally:
            duration = time.time() - start_time
            self._record_operation(duration)
            
    def flush(self) -> None:
        """Flush transmit buffer"""
        while not self.tx_buffer.empty():
            self.tx_buffer.get()
            
    def flush_input(self) -> None:
        """Flush receive buffer"""
        while not self.rx_buffer.empty():
            self.rx_buffer.get()
            
    def send_break(self, duration: float = 0.25) -> None:
        """
        Send break condition
        
        Args:
            duration: Break duration in seconds
        """
        self.break_condition = True
        
        # Create break frame
        frame = UARTFrame(
            data=0,
            timestamp=self.timing_engine.clock.get_time_us(),
            break_detected=True
        )
        
        if self.loopback:
            self.rx_buffer.put(frame)
        elif self.peer:
            self.peer.rx_buffer.put(frame)
            
        # Simulate break duration
        self.timing_engine.delay_ms(duration * 1000)
        self.break_condition = False
        
    def set_rts(self, state: bool) -> None:
        """Set RTS line state"""
        if self.config.flow_control == FlowControl.HARDWARE:
            self.rts = state
            if self.peer:
                self.peer.cts = state
                
    def get_cts(self) -> bool:
        """Get CTS line state"""
        return self.cts
        
    def inject_rx_data(self, data: bytes, 
                      inter_char_delay_ms: float = 0,
                      errors: Optional[List[str]] = None) -> None:
        """
        Inject data into receive buffer
        
        Args:
            data: Data to inject
            inter_char_delay_ms: Delay between characters
            errors: List of errors to inject ('parity', 'framing')
        """
        for i, byte in enumerate(data):
            frame = UARTFrame(
                data=byte,
                timestamp=self.timing_engine.clock.get_time_us(),
                parity_error='parity' in (errors or []) and i == 0,
                framing_error='framing' in (errors or []) and i == 0
            )
            
            self.rx_buffer.put(frame)
            
            if inter_char_delay_ms > 0:
                self.timing_engine.delay_ms(inter_char_delay_ms)
                
    def connect_peer(self, peer: 'UARTMock') -> None:
        """Connect to another UART mock for communication"""
        self.peer = peer
        peer.peer = self
        
    def disconnect_peer(self) -> None:
        """Disconnect from peer"""
        if self.peer:
            self.peer.peer = None
            self.peer = None
            
    def enable_loopback(self, enabled: bool = True) -> None:
        """Enable/disable loopback mode"""
        self.loopback = enabled
        
    def _can_transmit(self) -> bool:
        """Check if transmission is allowed by flow control"""
        if self.config.flow_control == FlowControl.HARDWARE:
            return self.cts
        elif self.config.flow_control == FlowControl.SOFTWARE:
            return not self.xoff_received
        return True
        
    def _simulate_byte_transmission(self, byte: int) -> None:
        """Simulate time to transmit one byte"""
        # Calculate frame size
        bits_per_frame = 1  # Start bit
        bits_per_frame += self.config.bytesize  # Data bits
        
        # Parity bit
        if self.config.parity != Parity.NONE:
            bits_per_frame += 1
            
        # Stop bits
        bits_per_frame += int(self.config.stopbits * 2) / 2
        
        # Calculate transmission time
        bit_time_us = 1_000_000 / self.config.baudrate
        frame_time_us = bits_per_frame * bit_time_us
        
        self.timing_engine.delay_us(frame_time_us)
        
    def _calculate_parity(self, byte: int) -> int:
        """Calculate parity bit for byte"""
        ones = bin(byte).count('1')
        
        if self.config.parity == Parity.EVEN:
            return 1 if ones % 2 else 0
        elif self.config.parity == Parity.ODD:
            return 0 if ones % 2 else 1
        elif self.config.parity == Parity.MARK:
            return 1
        elif self.config.parity == Parity.SPACE:
            return 0
        else:
            return 0
            
    def _handle_injected_error(self, error_type: str, **kwargs) -> None:
        """Handle injected errors"""
        if error_type == "break_condition":
            duration = kwargs.get('duration', 0.25)
            self.send_break(duration)
            
        elif error_type == "parity_error":
            # Next received byte will have parity error
            if not self.rx_buffer.empty():
                frame = self.rx_buffer.get()
                frame.parity_error = True
                self.rx_buffer.put(frame)
                
        elif error_type == "framing_error":
            # Next received byte will have framing error
            if not self.rx_buffer.empty():
                frame = self.rx_buffer.get()
                frame.framing_error = True
                self.rx_buffer.put(frame)
                
        elif error_type == "overrun":
            # Fill RX buffer to simulate overrun
            for _ in range(1000):
                self.inject_rx_data(b'\xFF')
                
        else:
            raise MockException(f"Unknown error type: {error_type}")
            
    def get_statistics(self) -> dict:
        """Get UART statistics"""
        return {
            'bytes_transmitted': self.bytes_transmitted,
            'bytes_received': self.bytes_received,
            'parity_errors': self.parity_errors,
            'framing_errors': self.framing_errors,
            'rx_buffer_size': self.rx_buffer.qsize(),
            'tx_buffer_size': self.tx_buffer.qsize()
        }
        
    def reset_statistics(self) -> None:
        """Reset statistics counters"""
        self.bytes_transmitted = 0
        self.bytes_received = 0
        self.parity_errors = 0
        self.framing_errors = 0