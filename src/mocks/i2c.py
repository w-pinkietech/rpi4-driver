"""I2C Mock implementation with protocol-accurate timing"""

import threading
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from .base import BaseMock, MockException, MockState
from .timing import TimingEngine


class I2CSpeed(Enum):
    """I2C bus speeds"""
    STANDARD = 100_000  # 100 kHz
    FAST = 400_000      # 400 kHz
    FAST_PLUS = 1_000_000  # 1 MHz
    

class BusState(Enum):
    """I2C bus states"""
    IDLE = "idle"
    START = "start"
    ADDRESS = "address"
    DATA = "data"
    ACK = "ack"
    NACK = "nack"
    STOP = "stop"
    

@dataclass
class I2CTransaction:
    """Record of an I2C transaction"""
    address: int
    write_data: bytes
    read_data: bytes
    success: bool
    timestamp: float
    duration_us: float


class I2CDeviceMock:
    """Base class for virtual I2C devices"""
    
    def __init__(self, address: int):
        self.address = address
        self.registers: Dict[int, int] = {}
        
    def write(self, data: bytes) -> bool:
        """
        Handle write operation
        
        Returns:
            True for ACK, False for NACK
        """
        return True
        
    def read(self, length: int) -> bytes:
        """
        Handle read operation
        
        Returns:
            Data bytes to send
        """
        return bytes([0] * length)
        
    def reset(self) -> None:
        """Reset device to initial state"""
        self.registers.clear()


class I2CMock(BaseMock):
    """I2C bus mock with protocol-accurate behavior"""
    
    def __init__(self, bus_number: int = 1, timing_engine: Optional[TimingEngine] = None):
        super().__init__(f"I2C-{bus_number}")
        self.bus_number = bus_number
        self.timing_engine = timing_engine or TimingEngine()
        self.devices: Dict[int, I2CDeviceMock] = {}
        self.bus_speed = I2CSpeed.STANDARD
        self.bus_state = BusState.IDLE
        self.clock_stretching_enabled = True
        self.transaction_history: List[I2CTransaction] = []
        self._lock = threading.Lock()
        
    def initialize(self, speed: I2CSpeed = I2CSpeed.STANDARD, **kwargs) -> None:
        """Initialize I2C bus"""
        self.bus_speed = speed
        self.set_state(MockState.INITIALIZED)
        self.set_state(MockState.ACTIVE)
        
    def shutdown(self) -> None:
        """Shutdown I2C bus"""
        self.set_state(MockState.SHUTDOWN)
        self.devices.clear()
        self.transaction_history.clear()
        
    def add_device(self, device: I2CDeviceMock) -> None:
        """Add virtual device to bus"""
        if device.address in self.devices:
            raise MockException(f"Device already exists at address 0x{device.address:02X}")
        self.devices[device.address] = device
        self._emit_event('device_added', {'address': device.address})
        
    def remove_device(self, address: int) -> None:
        """Remove device from bus"""
        if address in self.devices:
            del self.devices[address]
            self._emit_event('device_removed', {'address': address})
            
    def scan(self) -> List[int]:
        """
        Scan for devices on bus
        
        Returns:
            List of device addresses
        """
        found_devices = []
        
        # Scan standard I2C address range (0x08-0x77)
        for address in range(0x08, 0x78):
            if self._probe_address(address):
                found_devices.append(address)
                
        return found_devices
        
    def write_read(self, address: int, write_data: bytes, read_length: int) -> bytes:
        """
        Perform write-read transaction (write-restart-read)
        
        Args:
            address: Device address
            write_data: Data to write
            read_length: Number of bytes to read
            
        Returns:
            Read data
        """
        start_time = self.timing_engine.clock.get_time_us()
        
        with self._lock:
            try:
                # START condition
                self._simulate_start_condition()
                
                # Send address + write bit
                if not self._send_address(address, read=False):
                    raise MockException(f"Device at 0x{address:02X} did not ACK")
                    
                # Write data
                for byte in write_data:
                    if not self._send_byte(byte):
                        raise MockException("Device NACKed during write")
                        
                # Repeated START for read
                if read_length > 0:
                    self._simulate_repeated_start()
                    
                    # Send address + read bit
                    if not self._send_address(address, read=True):
                        raise MockException(f"Device at 0x{address:02X} did not ACK read")
                        
                    # Read data
                    read_data = self._receive_bytes(address, read_length)
                else:
                    read_data = b''
                    
                # STOP condition
                self._simulate_stop_condition()
                
                # Record transaction
                duration = self.timing_engine.clock.get_time_us() - start_time
                transaction = I2CTransaction(
                    address=address,
                    write_data=write_data,
                    read_data=read_data,
                    success=True,
                    timestamp=start_time,
                    duration_us=duration
                )
                self.transaction_history.append(transaction)
                self._record_operation(duration / 1e6)
                
                return read_data
                
            except Exception as e:
                # Record failed transaction
                duration = self.timing_engine.clock.get_time_us() - start_time
                transaction = I2CTransaction(
                    address=address,
                    write_data=write_data,
                    read_data=b'',
                    success=False,
                    timestamp=start_time,
                    duration_us=duration
                )
                self.transaction_history.append(transaction)
                self._record_operation(duration / 1e6, error=True)
                raise
                
    def _probe_address(self, address: int) -> bool:
        """Check if device exists at address"""
        try:
            self._simulate_start_condition()
            ack = self._send_address(address, read=False)
            self._simulate_stop_condition()
            return ack
        except:
            return False
            
    def _simulate_start_condition(self) -> None:
        """Simulate START condition timing"""
        # START: SDA falls while SCL high (4.7μs min)
        self.timing_engine.delay_us(4.7)
        self.bus_state = BusState.START
        
    def _simulate_repeated_start(self) -> None:
        """Simulate repeated START condition"""
        # Same as START but without STOP first
        self.timing_engine.delay_us(4.7)
        self.bus_state = BusState.START
        
    def _simulate_stop_condition(self) -> None:
        """Simulate STOP condition timing"""
        # STOP: SDA rises while SCL high (4.0μs min)
        self.timing_engine.delay_us(4.0)
        self.bus_state = BusState.IDLE
        
    def _send_address(self, address: int, read: bool) -> bool:
        """
        Send address byte with R/W bit
        
        Returns:
            True if ACK, False if NACK
        """
        address_byte = (address << 1) | (1 if read else 0)
        return self._send_byte(address_byte, is_address=True)
        
    def _send_byte(self, byte: int, is_address: bool = False) -> bool:
        """
        Send single byte and wait for ACK/NACK
        
        Returns:
            True if ACK, False if NACK
        """
        # Calculate bit time based on speed
        bit_time_us = 1_000_000 / self.bus_speed.value
        
        # Send 8 bits
        for _ in range(8):
            self.timing_engine.delay_us(bit_time_us)
            
        # 9th clock for ACK/NACK
        self.timing_engine.delay_us(bit_time_us)
        
        # Check if device exists and will ACK
        if is_address:
            address = byte >> 1
            return address in self.devices
        else:
            return True  # Assume ACK for data bytes
            
    def _receive_bytes(self, address: int, length: int) -> bytes:
        """Receive bytes from device"""
        if address not in self.devices:
            return bytes([0xFF] * length)  # No device, bus pulled high
            
        device = self.devices[address]
        data = device.read(length)
        
        # Simulate byte transfer timing
        bit_time_us = 1_000_000 / self.bus_speed.value
        for _ in range(length):
            for _ in range(9):  # 8 data + 1 ACK
                self.timing_engine.delay_us(bit_time_us)
                
        return data
        
    def _handle_injected_error(self, error_type: str, **kwargs) -> None:
        """Handle injected errors"""
        if error_type == "sda_stuck_low":
            # Simulate SDA line stuck low
            self.bus_state = BusState.START
            raise MockException("SDA line stuck low - bus error")
            
        elif error_type == "arbitration_lost":
            # Simulate multi-master arbitration loss
            raise MockException("Arbitration lost")
            
        elif error_type == "clock_stretch_timeout":
            # Simulate clock stretching timeout
            self.timing_engine.delay_us(50000)  # 50ms timeout
            raise MockException("Clock stretching timeout")
            
        else:
            raise MockException(f"Unknown error type: {error_type}")
            
    def enable_clock_stretching(self, enabled: bool) -> None:
        """Enable/disable clock stretching simulation"""
        self.clock_stretching_enabled = enabled
        
    def get_transaction_history(self, limit: Optional[int] = None) -> List[I2CTransaction]:
        """Get transaction history"""
        if limit:
            return self.transaction_history[-limit:]
        return self.transaction_history.copy()
        
    def clear_transaction_history(self) -> None:
        """Clear transaction history"""
        self.transaction_history.clear()