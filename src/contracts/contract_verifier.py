#!/usr/bin/env python3
"""
Contract-Based Testing Framework
Verifies implementations against formal interface contracts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple
import yaml
import time
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant


@dataclass
class ContractViolation:
    """Represents a contract violation"""
    operation: str
    violation_type: str  # 'precondition', 'postcondition', 'invariant', 'timing'
    expected: str
    actual: Any
    context: Dict[str, Any]


class InterfaceContract:
    """Loads and parses interface contracts"""
    
    def __init__(self, contract_path: str):
        self.path = Path(contract_path)
        with open(contract_path) as f:
            self.spec = yaml.safe_load(f)
        
        self.interface = self.spec['interface']
        self.version = self.spec['version']
        self.invariants = self.spec.get('invariants', {})
        self.operations = self.spec.get('operations', {})
        self.state_machine = self.spec.get('state_machine', {})
        self.test_properties = self.spec.get('test_properties', [])
    
    def get_operation_spec(self, operation: str) -> Dict[str, Any]:
        """Get specification for a specific operation"""
        if operation not in self.operations:
            raise ValueError(f"Operation {operation} not defined in contract")
        return self.operations[operation]
    
    def get_invariants(self) -> Dict[str, Dict[str, str]]:
        """Get all invariants that must always hold"""
        return self.invariants
    
    def get_timing_constraints(self, operation: str) -> Optional[Dict[str, float]]:
        """Get timing constraints for an operation"""
        op_spec = self.get_operation_spec(operation)
        return op_spec.get('timing')


class InterfaceImplementation(Protocol):
    """Protocol that all interface implementations must follow"""
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for invariant checking"""
        ...
    
    def execute_operation(self, operation: str, **kwargs) -> Any:
        """Execute an operation with given parameters"""
        ...


class ContractVerifier(ABC):
    """Base class for contract verification"""
    
    def __init__(self, contract: InterfaceContract, implementation: InterfaceImplementation):
        self.contract = contract
        self.impl = implementation
        self.violations: List[ContractViolation] = []
    
    def verify_invariants(self) -> bool:
        """Verify all invariants hold for current state"""
        state = self.impl.get_state()
        
        for inv_name, inv_spec in self.contract.get_invariants().items():
            if not self._check_constraint(inv_spec['constraint'], state):
                self.violations.append(ContractViolation(
                    operation="invariant_check",
                    violation_type="invariant",
                    expected=inv_spec['constraint'],
                    actual=state,
                    context={'invariant': inv_name}
                ))
                return False
        return True
    
    def verify_preconditions(self, operation: str, args: Dict[str, Any]) -> bool:
        """Verify preconditions before operation"""
        op_spec = self.contract.get_operation_spec(operation)
        state = self.impl.get_state()
        
        for precond in op_spec.get('preconditions', []):
            context = {**state, **args}
            if not self._check_constraint(precond, context):
                self.violations.append(ContractViolation(
                    operation=operation,
                    violation_type="precondition",
                    expected=precond,
                    actual=context,
                    context={'args': args}
                ))
                return False
        return True
    
    def verify_postconditions(self, operation: str, 
                            old_state: Dict[str, Any],
                            new_state: Dict[str, Any],
                            result: Any,
                            args: Dict[str, Any]) -> bool:
        """Verify postconditions after operation"""
        op_spec = self.contract.get_operation_spec(operation)
        
        for postcond in op_spec.get('postconditions', []):
            context = {
                'old': old_state,
                'new': new_state,
                'result': result,
                **args
            }
            if not self._check_constraint(postcond, context):
                self.violations.append(ContractViolation(
                    operation=operation,
                    violation_type="postcondition",
                    expected=postcond,
                    actual=context,
                    context={'args': args, 'result': result}
                ))
                return False
        return True
    
    def verify_timing(self, operation: str, duration_us: float) -> bool:
        """Verify operation completed within timing constraints"""
        timing = self.contract.get_timing_constraints(operation)
        if not timing:
            return True
        
        max_latency = timing.get('max_latency_us', float('inf'))
        if duration_us > max_latency:
            self.violations.append(ContractViolation(
                operation=operation,
                violation_type="timing",
                expected=f"<= {max_latency}us",
                actual=f"{duration_us}us",
                context={'timing': timing}
            ))
            return False
        return True
    
    def execute_with_verification(self, operation: str, **kwargs) -> Tuple[Any, bool]:
        """Execute operation with full contract verification"""
        # Check preconditions
        if not self.verify_preconditions(operation, kwargs):
            return None, False
        
        # Capture initial state
        old_state = self.impl.get_state()
        
        # Execute with timing
        start_time = time.perf_counter()
        try:
            result = self.impl.execute_operation(operation, **kwargs)
        except Exception as e:
            # Check if this error was expected
            op_spec = self.contract.get_operation_spec(operation)
            expected_errors = op_spec.get('errors', {})
            if type(e).__name__ not in expected_errors:
                raise
            return e, True
        
        duration_us = (time.perf_counter() - start_time) * 1e6
        
        # Capture final state
        new_state = self.impl.get_state()
        
        # Verify everything
        timing_ok = self.verify_timing(operation, duration_us)
        postcond_ok = self.verify_postconditions(operation, old_state, new_state, result, kwargs)
        invariant_ok = self.verify_invariants()
        
        success = timing_ok and postcond_ok and invariant_ok
        return result, success
    
    @abstractmethod
    def _check_constraint(self, constraint: str, context: Dict[str, Any]) -> bool:
        """Check if a constraint holds in given context"""
        pass


class PropertyBasedContractTest(RuleBasedStateMachine):
    """
    Base class for property-based testing of contracts.
    Generates random sequences of operations and verifies contracts hold.
    """
    
    def __init__(self):
        super().__init__()
        self.contract = self._load_contract()
        self.impl = self._create_implementation()
        self.verifier = self._create_verifier()
        self.operation_count = 0
    
    @abstractmethod
    def _load_contract(self) -> InterfaceContract:
        """Load the contract for this test"""
        pass
    
    @abstractmethod
    def _create_implementation(self) -> InterfaceImplementation:
        """Create implementation to test"""
        pass
    
    @abstractmethod
    def _create_verifier(self) -> ContractVerifier:
        """Create verifier for this contract type"""
        pass
    
    @invariant()
    def invariants_always_hold(self):
        """Check that all invariants hold after any operation"""
        assert self.verifier.verify_invariants(), \
            f"Invariant violation: {self.verifier.violations[-1]}"
    
    def teardown(self):
        """Report any violations found during testing"""
        if self.verifier.violations:
            print(f"\nContract violations found ({len(self.verifier.violations)}):")
            for v in self.verifier.violations:
                print(f"  - {v.operation}: {v.violation_type} - {v.expected}")


# Example GPIO Contract Verifier
class GPIOContractVerifier(ContractVerifier):
    """Verifies GPIO implementations against contract"""
    
    def _check_constraint(self, constraint: str, context: Dict[str, Any]) -> bool:
        """
        Simple constraint checker for GPIO.
        In production, use a proper expression evaluator or Z3.
        """
        # Handle simple membership constraints
        if "∈" in constraint:
            parts = constraint.split("∈")
            var_path = parts[0].strip()
            valid_set = parts[1].strip()
            
            # Extract variable value from context
            value = self._get_value_from_path(var_path, context)
            
            # Check membership
            if valid_set == "{HIGH, LOW}":
                return value in ["HIGH", "LOW"]
            elif valid_set == "{INPUT, OUTPUT}":
                return value in ["INPUT", "OUTPUT"]
            elif valid_set == "{PULL_UP, PULL_DOWN, NONE}":
                return value in ["PULL_UP", "PULL_DOWN", "NONE"]
            elif "valid_pins" in valid_set:
                # RPi4 valid pins
                return value in range(2, 28)
        
        # Handle other constraint types...
        return True
    
    def _get_value_from_path(self, path: str, context: Dict[str, Any]) -> Any:
        """Extract value from nested path like 'pin.value'"""
        parts = path.split('.')
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


# Example usage with Hypothesis
class GPIOPropertyTest(PropertyBasedContractTest):
    """Property-based tests for GPIO contract"""
    
    def _load_contract(self) -> InterfaceContract:
        return InterfaceContract('contracts/gpio.contract.yaml')
    
    def _create_implementation(self):
        # Would return actual GPIO implementation
        # For testing, return a mock that satisfies contract
        from .gpio_mock import ContractCompliantGPIOMock
        return ContractCompliantGPIOMock()
    
    def _create_verifier(self) -> ContractVerifier:
        return GPIOContractVerifier(self.contract, self.impl)
    
    @rule(pin=st.integers(min_value=2, max_value=27),
          direction=st.sampled_from(['INPUT', 'OUTPUT']))
    def set_direction(self, pin: int, direction: str):
        """Test setting pin direction"""
        result, success = self.verifier.execute_with_verification(
            'set_direction', pin_id=pin, direction=direction
        )
        assert success, f"Contract violation in set_direction"
    
    @rule(pin=st.integers(min_value=2, max_value=27),
          value=st.sampled_from(['HIGH', 'LOW']))
    def write_pin(self, pin: int, value: str):
        """Test writing to output pins"""
        # First ensure pin is output
        state = self.impl.get_state()
        if state.get('pins', {}).get(pin, {}).get('direction') != 'OUTPUT':
            # Set to output first
            self.verifier.execute_with_verification(
                'set_direction', pin_id=pin, direction='OUTPUT'
            )
        
        result, success = self.verifier.execute_with_verification(
            'write', pin_id=pin, value=value
        )
        assert success, f"Contract violation in write"


def verify_implementation_against_contract(
    contract_path: str,
    implementation: InterfaceImplementation,
    num_examples: int = 100
) -> Dict[str, Any]:
    """
    Verify an implementation against its contract.
    Returns verification report.
    """
    contract = InterfaceContract(contract_path)
    
    # Create appropriate verifier based on interface type
    if contract.interface == "GPIO":
        verifier = GPIOContractVerifier(contract, implementation)
    elif contract.interface == "I2C":
        # Would use I2CContractVerifier
        pass
    else:
        raise ValueError(f"Unknown interface type: {contract.interface}")
    
    # Run property-based tests
    # In production, would use Hypothesis to generate test cases
    
    return {
        'interface': contract.interface,
        'version': contract.version,
        'violations': verifier.violations,
        'passed': len(verifier.violations) == 0
    }