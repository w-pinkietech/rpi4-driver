#!/usr/bin/env python3
"""
Contract-Based Mock Generator
Generates perfect mock implementations from interface contracts
"""

import yaml
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import re


class MockGenerationError(Exception):
    """Raised when mock generation fails"""
    pass


@dataclass
class MockState:
    """Maintains state for contract-compliant mock"""
    interface: str
    initialized: bool = False
    pins: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    bus_state: str = "IDLE"
    devices: Set[int] = field(default_factory=set)
    timing_mode: str = "typical"  # 'typical', 'worst_case', 'best_case'
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Return state as dictionary for contract verification"""
        return {
            'initialized': self.initialized,
            'pins': self.pins,
            'bus_state': self.bus_state,
            'devices': list(self.devices)
        }


class ContractMockGenerator:
    """Generates mock implementations from contracts"""
    
    def __init__(self, contract_path: str):
        self.contract_path = Path(contract_path)
        with open(contract_path) as f:
            self.contract = yaml.safe_load(f)
        
        self.interface = self.contract['interface']
        self.operations = self.contract.get('operations', {})
        self.invariants = self.contract.get('invariants', {})
        self.state_machine = self.contract.get('state_machine', {})
    
    def generate_mock(self) -> Any:
        """Generate mock implementation that perfectly satisfies contract"""
        if self.interface == "GPIO":
            return self._generate_gpio_mock()
        elif self.interface == "I2C":
            return self._generate_i2c_mock()
        elif self.interface == "SPI":
            return self._generate_spi_mock()
        elif self.interface == "UART":
            return self._generate_uart_mock()
        else:
            raise MockGenerationError(f"Unknown interface: {self.interface}")
    
    def _generate_gpio_mock(self):
        """Generate GPIO mock from contract"""
        
        class GPIOMock:
            def __init__(self):
                self.state = MockState(interface="GPIO")
                self.contract = self.contract
                # Initialize pins based on contract
                self._init_pins()
            
            def _init_pins(self):
                """Initialize pins to satisfy invariants"""
                # Extract valid pins from contract
                valid_pins = list(range(2, 28))  # RPi4 pins from contract
                for pin in valid_pins:
                    self.state.pins[pin] = {
                        'direction': 'INPUT',
                        'value': 'LOW',
                        'pull': 'NONE'
                    }
            
            def get_state(self) -> Dict[str, Any]:
                """Get current state for contract verification"""
                return {
                    'gpio': {'initialized': self.state.initialized},
                    'pins': {pin: data.copy() for pin, data in self.state.pins.items()},
                    'pin': None  # Will be set per operation
                }
            
            def execute_operation(self, operation: str, **kwargs) -> Any:
                """Execute operation according to contract"""
                if operation == "initialize":
                    return self._initialize(**kwargs)
                elif operation == "set_direction":
                    return self._set_direction(**kwargs)
                elif operation == "read":
                    return self._read(**kwargs)
                elif operation == "write":
                    return self._write(**kwargs)
                elif operation == "set_pull":
                    return self._set_pull(**kwargs)
                elif operation == "cleanup":
                    return self._cleanup(**kwargs)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
            
            def _initialize(self) -> None:
                """Initialize GPIO subsystem"""
                if self.state.initialized:
                    raise RuntimeError("ALREADY_INITIALIZED")
                
                self.state.initialized = True
                # Reset all pins to INPUT with no pull (per contract)
                for pin in self.state.pins:
                    self.state.pins[pin]['direction'] = 'INPUT'
                    self.state.pins[pin]['pull'] = 'NONE'
            
            def _set_direction(self, pin_id: int, direction: str) -> None:
                """Set pin direction"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if pin_id not in self.state.pins:
                    raise ValueError(f"Invalid pin: {pin_id}")
                
                self.state.pins[pin_id]['direction'] = direction
                
                # Contract: output pins start LOW
                if direction == 'OUTPUT':
                    self.state.pins[pin_id]['value'] = 'LOW'
                    self.state.pins[pin_id]['pull'] = 'NONE'
                
                self._simulate_timing('set_direction')
            
            def _read(self, pin_id: int) -> str:
                """Read pin value"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if pin_id not in self.state.pins:
                    raise ValueError(f"Invalid pin: {pin_id}")
                
                self._simulate_timing('read')
                return self.state.pins[pin_id]['value']
            
            def _write(self, pin_id: int, value: str) -> None:
                """Write to output pin"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if pin_id not in self.state.pins:
                    raise ValueError(f"Invalid pin: {pin_id}")
                
                if self.state.pins[pin_id]['direction'] != 'OUTPUT':
                    raise RuntimeError("INVALID_DIRECTION")
                
                self.state.pins[pin_id]['value'] = value
                self._simulate_timing('write')
            
            def _set_pull(self, pin_id: int, pull: str) -> None:
                """Set pull resistor"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if pin_id not in self.state.pins:
                    raise ValueError(f"Invalid pin: {pin_id}")
                
                if self.state.pins[pin_id]['direction'] != 'INPUT':
                    raise RuntimeError("INVALID_DIRECTION")
                
                self.state.pins[pin_id]['pull'] = pull
                self._simulate_timing('set_pull')
            
            def _cleanup(self) -> None:
                """Release GPIO resources"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                self.state.initialized = False
                # Reset all pins per contract
                for pin in self.state.pins:
                    self.state.pins[pin]['direction'] = 'INPUT'
                    self.state.pins[pin]['value'] = 'LOW'
            
            def _simulate_timing(self, operation: str):
                """Simulate realistic timing based on contract"""
                op_spec = self.contract['operations'].get(operation, {})
                timing = op_spec.get('timing', {})
                
                if self.state.timing_mode == 'typical':
                    delay_us = timing.get('typical_latency_us', 1)
                elif self.state.timing_mode == 'worst_case':
                    delay_us = timing.get('max_latency_us', 10)
                else:  # best_case
                    delay_us = 0.1
                
                time.sleep(delay_us / 1_000_000)  # Convert to seconds
        
        return GPIOMock()
    
    def _generate_i2c_mock(self):
        """Generate I2C mock from contract"""
        
        class I2CMock:
            def __init__(self):
                self.state = MockState(interface="I2C")
                self.contract = self.contract
                self.bus_speed = 100000  # Default standard speed
                self.state.devices = {0x48, 0x68, 0x76}  # Mock devices
            
            def get_state(self) -> Dict[str, Any]:
                """Get current state for contract verification"""
                return {
                    'bus': {
                        'state': self.state.bus_state,
                        'initialized': self.state.initialized,
                        'speed': self.bus_speed
                    },
                    'devices': list(self.state.devices)
                }
            
            def execute_operation(self, operation: str, **kwargs) -> Any:
                """Execute operation according to contract"""
                if operation == "initialize":
                    return self._initialize(**kwargs)
                elif operation == "scan":
                    return self._scan(**kwargs)
                elif operation == "read":
                    return self._read(**kwargs)
                elif operation == "write":
                    return self._write(**kwargs)
                elif operation == "read_write":
                    return self._read_write(**kwargs)
                elif operation == "reset":
                    return self._reset(**kwargs)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
            
            def _initialize(self, bus_id: int, speed: int) -> None:
                """Initialize I2C bus"""
                if self.state.initialized:
                    raise RuntimeError("ALREADY_INITIALIZED")
                
                if speed not in [100000, 400000, 1000000, 3400000]:
                    raise ValueError(f"Invalid speed: {speed}")
                
                self.state.initialized = True
                self.state.bus_state = "IDLE"
                self.bus_speed = speed
            
            def _scan(self, start_addr: int = 0x08, end_addr: int = 0x77) -> List[int]:
                """Scan for devices"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if self.state.bus_state != "IDLE":
                    raise RuntimeError("Bus not idle")
                
                # Simulate scanning
                self.state.bus_state = "BUSY"
                found_devices = []
                
                for addr in range(start_addr, end_addr + 1):
                    if addr in self.state.devices:
                        found_devices.append(addr)
                    # Simulate scan timing
                    time.sleep(0.0001)  # 0.1ms per address
                
                self.state.bus_state = "IDLE"
                return found_devices
            
            def _read(self, address: int, length: int, register: Optional[int] = None) -> bytes:
                """Read from device"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if self.state.bus_state != "IDLE":
                    raise RuntimeError("Bus not idle")
                
                if address not in self.state.devices:
                    raise RuntimeError("NACK")
                
                # Simulate read
                self.state.bus_state = "BUSY"
                
                # Generate mock data
                if register is not None:
                    # Reading from specific register
                    data = bytes([(register + i) % 256 for i in range(length)])
                else:
                    # Direct read
                    data = bytes([i % 256 for i in range(length)])
                
                # Simulate timing
                time.sleep(length * 0.0001)  # 0.1ms per byte
                
                self.state.bus_state = "IDLE"
                return data
            
            def _write(self, address: int, data: bytes, register: Optional[int] = None) -> int:
                """Write to device"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                if self.state.bus_state != "IDLE":
                    raise RuntimeError("Bus not idle")
                
                if address not in self.state.devices:
                    raise RuntimeError("NACK")
                
                # Simulate write
                self.state.bus_state = "BUSY"
                
                # Simulate timing
                time.sleep(len(data) * 0.0001)  # 0.1ms per byte
                
                self.state.bus_state = "IDLE"
                return len(data)
            
            def _read_write(self, address: int, write_data: bytes, read_length: int) -> bytes:
                """Combined write-then-read"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                # Write without stop
                self._write(address, write_data)
                # Read with repeated start
                return self._read(address, read_length)
            
            def _reset(self) -> None:
                """Reset bus to idle state"""
                if not self.state.initialized:
                    raise RuntimeError("Not initialized")
                
                self.state.bus_state = "IDLE"
                time.sleep(0.01)  # 10ms reset time
        
        return I2CMock()
    
    def _generate_spi_mock(self):
        """Generate SPI mock from contract"""
        # Similar pattern to GPIO and I2C
        raise NotImplementedError("SPI mock generation not yet implemented")
    
    def _generate_uart_mock(self):
        """Generate UART mock from contract"""
        # Similar pattern to GPIO and I2C
        raise NotImplementedError("UART mock generation not yet implemented")


def create_contract_compliant_mock(interface: str) -> Any:
    """
    Create a mock that perfectly complies with the interface contract.
    
    Args:
        interface: Interface name (GPIO, I2C, SPI, UART)
    
    Returns:
        Mock implementation that satisfies all contract requirements
    """
    contract_path = f"contracts/{interface.lower()}.contract.yaml"
    generator = ContractMockGenerator(contract_path)
    return generator.generate_mock()


# Example of advanced mock features
class SmartContractMock:
    """
    Advanced mock that can simulate various scenarios while
    maintaining contract compliance.
    """
    
    def __init__(self, contract_path: str):
        self.generator = ContractMockGenerator(contract_path)
        self.mock = self.generator.generate_mock()
        self.scenarios = {}
    
    def add_scenario(self, name: str, setup_fn):
        """Add a test scenario"""
        self.scenarios[name] = setup_fn
    
    def with_scenario(self, name: str):
        """Apply a scenario to the mock"""
        if name in self.scenarios:
            self.scenarios[name](self.mock)
        return self.mock
    
    def with_timing_mode(self, mode: str):
        """Set timing simulation mode"""
        if hasattr(self.mock, 'state'):
            self.mock.state.timing_mode = mode
        return self.mock
    
    def with_devices(self, devices: List[int]):
        """Configure I2C mock with specific devices"""
        if hasattr(self.mock, 'state') and self.mock.state.interface == "I2C":
            self.mock.state.devices = set(devices)
        return self.mock


# Contract compliance validator
def validate_mock_compliance(mock: Any, contract_path: str, num_operations: int = 1000) -> Dict[str, Any]:
    """
    Validate that a mock implementation fully complies with its contract.
    
    Performs random operations and verifies all contract requirements are met.
    """
    from .contract_verifier import verify_implementation_against_contract
    
    # Run verification
    result = verify_implementation_against_contract(
        contract_path,
        mock,
        num_examples=num_operations
    )
    
    return {
        'compliant': result['passed'],
        'violations': result['violations'],
        'operations_tested': num_operations,
        'interface': result['interface']
    }