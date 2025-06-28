"""Base mock interface and common functionality"""

import abc
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class MockException(Exception):
    """Base exception for mock-related errors"""
    pass


class MockState(Enum):
    """Common mock states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class MockEvent:
    """Base class for mock events"""
    timestamp: float
    event_type: str
    data: Any
    

class BaseMock(abc.ABC):
    """Abstract base class for all hardware mocks"""
    
    def __init__(self, name: str):
        self.name = name
        self.state = MockState.UNINITIALIZED
        self.state_lock = threading.RLock()
        self.event_callbacks: Dict[str, List[Callable]] = {}
        self.event_history: List[MockEvent] = []
        self.error_injection_enabled = False
        self.performance_metrics = {
            'operations': 0,
            'total_time': 0.0,
            'errors': 0
        }
        
    @abc.abstractmethod
    def initialize(self, **kwargs) -> None:
        """Initialize the mock with configuration"""
        pass
        
    @abc.abstractmethod
    def shutdown(self) -> None:
        """Cleanup and shutdown the mock"""
        pass
        
    def get_state(self) -> MockState:
        """Thread-safe state getter"""
        with self.state_lock:
            return self.state
            
    def set_state(self, new_state: MockState) -> None:
        """Thread-safe state setter with transition validation"""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            self._emit_event('state_change', {
                'old': old_state.value,
                'new': new_state.value
            })
            
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for specific event type"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
        
    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """Unregister callback"""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].remove(callback)
            
    def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit event to registered callbacks"""
        event = MockEvent(
            timestamp=time.time(),
            event_type=event_type,
            data=data
        )
        
        # Store in history
        self.event_history.append(event)
        
        # Call registered callbacks
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in callback for {event_type}: {e}")
                    
    def enable_error_injection(self) -> None:
        """Enable error injection for testing"""
        self.error_injection_enabled = True
        
    def disable_error_injection(self) -> None:
        """Disable error injection"""
        self.error_injection_enabled = False
        
    def inject_error(self, error_type: str, **kwargs) -> None:
        """Inject a specific error condition"""
        if not self.error_injection_enabled:
            raise MockException("Error injection is not enabled")
        self._handle_injected_error(error_type, **kwargs)
        
    @abc.abstractmethod
    def _handle_injected_error(self, error_type: str, **kwargs) -> None:
        """Handle injected error (implementation specific)"""
        pass
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self.state_lock:
            if self.performance_metrics['operations'] > 0:
                avg_time = self.performance_metrics['total_time'] / self.performance_metrics['operations']
            else:
                avg_time = 0
            return {
                **self.performance_metrics,
                'average_operation_time': avg_time
            }
            
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        with self.state_lock:
            self.performance_metrics = {
                'operations': 0,
                'total_time': 0.0,
                'errors': 0
            }
            
    def _record_operation(self, duration: float, error: bool = False) -> None:
        """Record operation metrics"""
        with self.state_lock:
            self.performance_metrics['operations'] += 1
            self.performance_metrics['total_time'] += duration
            if error:
                self.performance_metrics['errors'] += 1
                
    def get_event_history(self, event_type: Optional[str] = None, 
                         limit: Optional[int] = None) -> List[MockEvent]:
        """Get event history, optionally filtered"""
        history = self.event_history
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
            
        if limit:
            history = history[-limit:]
            
        return history
        
    def clear_event_history(self) -> None:
        """Clear event history"""
        self.event_history.clear()
        
    def verify_state_sequence(self, expected_states: List[MockState]) -> bool:
        """Verify that state transitions followed expected sequence"""
        state_events = self.get_event_history('state_change')
        
        if len(state_events) < len(expected_states):
            return False
            
        actual_states = []
        for event in state_events[-len(expected_states):]:
            actual_states.append(MockState(event.data['new']))
            
        return actual_states == expected_states