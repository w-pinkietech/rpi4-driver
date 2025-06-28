"""SPI Mock implementation with full-duplex simulation"""

import threading
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from .base import BaseMock, MockException, MockState
from .timing import TimingEngine


class SPIMode(Enum):
    """SPI modes (CPOL, CPHA)"""
    MODE_0 = (0, 0)  # CPOL=0, CPHA=0
    MODE_1 = (0, 1)  # CPOL=0, CPHA=1
    MODE_2 = (1, 0)  # CPOL=1, CPHA=0
    MODE_3 = (1, 1)  # CPOL=1, CPHA=1
    

@dataclass
class SPIConfig:
    """SPI configuration"""
    speed_hz: int = 1_000_000  # 1 MHz default
    mode: SPIMode = SPIMode.MODE_0
    bits_per_word: int = 8
    lsb_first: bool = False
    cs_active_high: bool = False
    

@dataclass
class SPITransaction:
    """Record of an SPI transaction"""
    chip_select: int
    tx_data: bytes
    rx_data: bytes
    timestamp: float
    duration_us: float


class SPIDeviceMock:
    """Base class for virtual SPI devices"""
    
    def __init__(self, chip_select: int):
        self.chip_select = chip_select
        self.selected = False
        
    def select(self) -> None:
        """Called when device is selected"""
        self.selected = True
        
    def deselect(self) -> None:
        """Called when device is deselected"""
        self.selected = False
        
    def transfer_byte(self, tx_byte: int) -> int:
        """
        Transfer single byte
        
        Args:
            tx_byte: Byte to transmit
            
        Returns:
            Received byte
        """
        return 0xFF  # Default: return all 1s
        
    def reset(self) -> None:
        """Reset device to initial state"""
        pass


class SPIMock(BaseMock):
    """SPI bus mock with full-duplex communication"""
    
    def __init__(self, bus_number: int = 0, timing_engine: Optional[TimingEngine] = None):
        super().__init__(f"SPI-{bus_number}")
        self.bus_number = bus_number
        self.timing_engine = timing_engine or TimingEngine()
        self.devices: Dict[int, SPIDeviceMock] = {}
        self.config = SPIConfig()
        self.transaction_history: List[SPITransaction] = []
        self.current_cs: Optional[int] = None
        self._lock = threading.Lock()
        
        # Bus state
        self.mosi_line = 0
        self.miso_line = 0
        self.sclk_line = 0
        self.cs_lines: Dict[int, int] = {}
        
    def initialize(self, **kwargs) -> None:
        """Initialize SPI bus"""
        # Apply configuration
        if 'speed_hz' in kwargs:
            self.config.speed_hz = kwargs['speed_hz']
        if 'mode' in kwargs:
            self.config.mode = kwargs['mode']
            
        self.set_state(MockState.INITIALIZED)
        self.set_state(MockState.ACTIVE)
        
    def shutdown(self) -> None:
        """Shutdown SPI bus"""
        self.set_state(MockState.SHUTDOWN)
        self.devices.clear()
        self.transaction_history.clear()
        
    def add_device(self, device: SPIDeviceMock) -> None:
        """Add virtual device to bus"""
        if device.chip_select in self.devices:
            raise MockException(f"Device already exists on CS{device.chip_select}")
        self.devices[device.chip_select] = device
        self.cs_lines[device.chip_select] = 1 if self.config.cs_active_high else 0
        self._emit_event('device_added', {'chip_select': device.chip_select})
        
    def remove_device(self, chip_select: int) -> None:
        """Remove device from bus"""
        if chip_select in self.devices:
            del self.devices[chip_select]
            del self.cs_lines[chip_select]
            self._emit_event('device_removed', {'chip_select': chip_select})
            
    def configure(self, config: SPIConfig) -> None:
        """Update SPI configuration"""
        self.config = config
        
        # Set initial clock state based on CPOL
        cpol, _ = self.config.mode.value
        self.sclk_line = cpol
        
    def transfer(self, tx_data: bytes, chip_select: int = 0) -> bytes:
        """
        Perform full-duplex SPI transfer
        
        Args:
            tx_data: Data to transmit
            chip_select: Chip select line to use
            
        Returns:
            Received data
        """
        start_time = self.timing_engine.clock.get_time_us()
        
        with self._lock:
            try:
                # Assert chip select
                self._assert_cs(chip_select)
                
                # Transfer data
                rx_data = bytearray()
                for tx_byte in tx_data:
                    rx_byte = self._transfer_byte(tx_byte, chip_select)
                    rx_data.append(rx_byte)
                    
                # Deassert chip select
                self._deassert_cs(chip_select)
                
                # Record transaction
                duration = self.timing_engine.clock.get_time_us() - start_time
                transaction = SPITransaction(
                    chip_select=chip_select,
                    tx_data=tx_data,
                    rx_data=bytes(rx_data),
                    timestamp=start_time,
                    duration_us=duration
                )
                self.transaction_history.append(transaction)
                self._record_operation(duration / 1e6)
                
                return bytes(rx_data)
                
            except Exception as e:
                self._record_operation(0, error=True)
                raise
                
    def _assert_cs(self, chip_select: int) -> None:
        """Assert chip select line"""
        if self.current_cs is not None:
            raise MockException("Another device is already selected")
            
        # CS setup time (typically 50ns)
        self.timing_engine.delay_ns(50)
        
        # Set CS line
        self.cs_lines[chip_select] = 0 if self.config.cs_active_high else 1
        self.current_cs = chip_select
        
        # Notify device
        if chip_select in self.devices:
            self.devices[chip_select].select()
            
    def _deassert_cs(self, chip_select: int) -> None:
        """Deassert chip select line"""
        # CS hold time (typically 50ns)
        self.timing_engine.delay_ns(50)
        
        # Clear CS line
        self.cs_lines[chip_select] = 1 if self.config.cs_active_high else 0
        self.current_cs = None
        
        # Notify device
        if chip_select in self.devices:
            self.devices[chip_select].deselect()
            
    def _transfer_byte(self, tx_byte: int, chip_select: int) -> int:
        """Transfer single byte with bit-level timing"""
        cpol, cpha = self.config.mode.value
        rx_byte = 0
        
        # Calculate bit time
        bit_time_us = 1_000_000 / self.config.speed_hz
        
        # Get device response (if exists)
        device = self.devices.get(chip_select)
        
        for bit_num in range(8):
            # Determine bit position
            if self.config.lsb_first:
                bit_pos = bit_num
            else:
                bit_pos = 7 - bit_num
                
            # Set MOSI
            self.mosi_line = (tx_byte >> bit_pos) & 1
            
            # Handle clock and sampling based on mode
            if cpha == 0:
                # CPHA=0: Sample on first edge, shift on second
                
                # First edge
                self.sclk_line = 1 - cpol
                self.timing_engine.delay_us(bit_time_us / 2)
                
                # Sample MISO
                if device:
                    device_response = device.transfer_byte(tx_byte)
                    miso_bit = (device_response >> bit_pos) & 1
                else:
                    miso_bit = 1  # No device, line pulled high
                    
                rx_byte |= (miso_bit << bit_pos)
                
                # Second edge
                self.sclk_line = cpol
                self.timing_engine.delay_us(bit_time_us / 2)
                
            else:
                # CPHA=1: Shift on first edge, sample on second
                
                # First edge
                self.sclk_line = 1 - cpol
                self.timing_engine.delay_us(bit_time_us / 2)
                
                # Second edge
                self.sclk_line = cpol
                
                # Sample MISO
                if device:
                    device_response = device.transfer_byte(tx_byte)
                    miso_bit = (device_response >> bit_pos) & 1
                else:
                    miso_bit = 1
                    
                rx_byte |= (miso_bit << bit_pos)
                
                self.timing_engine.delay_us(bit_time_us / 2)
                
        return rx_byte
        
    def _handle_injected_error(self, error_type: str, **kwargs) -> None:
        """Handle injected errors"""
        if error_type == "clock_glitch":
            # Simulate clock glitch
            self.sclk_line = 1 - self.sclk_line
            self.timing_engine.delay_ns(10)
            self.sclk_line = 1 - self.sclk_line
            
        elif error_type == "cs_glitch":
            # Simulate CS glitch during transfer
            if self.current_cs is not None:
                cs = self.current_cs
                self._deassert_cs(cs)
                self.timing_engine.delay_us(1)
                self._assert_cs(cs)
                
        elif error_type == "miso_stuck":
            # Simulate MISO stuck high or low
            value = kwargs.get('value', 1)
            # Would affect device responses
            
        else:
            raise MockException(f"Unknown error type: {error_type}")
            
    def get_transaction_history(self, limit: Optional[int] = None) -> List[SPITransaction]:
        """Get transaction history"""
        if limit:
            return self.transaction_history[-limit:]
        return self.transaction_history.copy()
        
    def clear_transaction_history(self) -> None:
        """Clear transaction history"""
        self.transaction_history.clear()
        
    def get_bus_state(self) -> dict:
        """Get current bus line states"""
        return {
            'mosi': self.mosi_line,
            'miso': self.miso_line,
            'sclk': self.sclk_line,
            'cs': self.cs_lines.copy()
        }