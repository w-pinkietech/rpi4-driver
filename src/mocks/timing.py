"""Virtual timing engine for microsecond-precision simulation"""

import heapq
import threading
import time
from typing import Callable, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass(order=True)
class ScheduledEvent:
    """Event scheduled for future execution"""
    time_us: float
    callback: Callable = field(compare=False)
    event_id: int = field(compare=False)
    

class VirtualClock:
    """Virtual clock with controllable time progression"""
    
    def __init__(self, real_time_factor: float = 0.0):
        """
        Initialize virtual clock
        
        Args:
            real_time_factor: 0.0 = instant, 1.0 = real-time, 0.5 = half-speed
        """
        self.virtual_time_us = 0.0
        self.real_time_factor = real_time_factor
        self.start_real_time = time.time()
        self.start_virtual_time = 0.0
        self._lock = threading.Lock()
        
    def get_time_us(self) -> float:
        """Get current virtual time in microseconds"""
        with self._lock:
            return self.virtual_time_us
            
    def advance_us(self, microseconds: float) -> None:
        """Advance virtual time by specified microseconds"""
        with self._lock:
            self.virtual_time_us += microseconds
            
            # If real-time factor > 0, sleep to simulate real time
            if self.real_time_factor > 0:
                sleep_time = (microseconds * self.real_time_factor) / 1e6
                time.sleep(sleep_time)
                
    def set_time_us(self, time_us: float) -> None:
        """Set virtual time to specific value"""
        with self._lock:
            self.virtual_time_us = time_us
            
    def reset(self) -> None:
        """Reset virtual clock to zero"""
        with self._lock:
            self.virtual_time_us = 0.0
            self.start_real_time = time.time()
            self.start_virtual_time = 0.0


class TimingEngine:
    """Microsecond-precision timing simulation engine"""
    
    def __init__(self, clock: Optional[VirtualClock] = None):
        """
        Initialize timing engine
        
        Args:
            clock: Virtual clock instance (creates new if None)
        """
        self.clock = clock or VirtualClock()
        self.events: List[ScheduledEvent] = []
        self.next_event_id = 0
        self._lock = threading.Lock()
        self.active = True
        
        # Performance tracking
        self.events_processed = 0
        self.total_scheduling_time = 0.0
        self.total_execution_time = 0.0
        
    def schedule_event(self, delay_us: float, callback: Callable) -> int:
        """
        Schedule event for future execution
        
        Args:
            delay_us: Delay in microseconds from current time
            callback: Function to call when event fires
            
        Returns:
            Event ID for cancellation
        """
        start_time = time.time()
        
        with self._lock:
            event_time = self.clock.get_time_us() + delay_us
            event_id = self.next_event_id
            self.next_event_id += 1
            
            event = ScheduledEvent(
                time_us=event_time,
                callback=callback,
                event_id=event_id
            )
            
            heapq.heappush(self.events, event)
            
        scheduling_time = time.time() - start_time
        self.total_scheduling_time += scheduling_time
        
        return event_id
        
    def cancel_event(self, event_id: int) -> bool:
        """
        Cancel scheduled event
        
        Args:
            event_id: ID returned by schedule_event
            
        Returns:
            True if event was cancelled, False if not found
        """
        with self._lock:
            for i, event in enumerate(self.events):
                if event.event_id == event_id:
                    self.events.pop(i)
                    heapq.heapify(self.events)
                    return True
        return False
        
    def run_until(self, target_time_us: float) -> int:
        """
        Advance time and execute all events up to target time
        
        Args:
            target_time_us: Target virtual time in microseconds
            
        Returns:
            Number of events executed
        """
        executed = 0
        
        while True:
            with self._lock:
                if not self.events or self.events[0].time_us > target_time_us:
                    # No more events or next event is beyond target time
                    self.clock.set_time_us(target_time_us)
                    break
                    
                # Get next event
                event = heapq.heappop(self.events)
                
            # Advance clock to event time
            self.clock.set_time_us(event.time_us)
            
            # Execute callback
            start_time = time.time()
            try:
                event.callback()
                executed += 1
                self.events_processed += 1
            except Exception as e:
                print(f"Error in scheduled event: {e}")
            finally:
                execution_time = time.time() - start_time
                self.total_execution_time += execution_time
                
        return executed
        
    def run_for(self, duration_us: float) -> int:
        """
        Run for specified duration from current time
        
        Args:
            duration_us: Duration in microseconds
            
        Returns:
            Number of events executed
        """
        target_time = self.clock.get_time_us() + duration_us
        return self.run_until(target_time)
        
    def delay_ns(self, nanoseconds: float) -> None:
        """Simulate nanosecond delay"""
        self.clock.advance_us(nanoseconds / 1000.0)
        
    def delay_us(self, microseconds: float) -> None:
        """Simulate microsecond delay"""
        self.clock.advance_us(microseconds)
        
    def delay_ms(self, milliseconds: float) -> None:
        """Simulate millisecond delay"""
        self.clock.advance_us(milliseconds * 1000.0)
        
    def get_pending_events(self) -> int:
        """Get number of pending events"""
        with self._lock:
            return len(self.events)
            
    def clear_events(self) -> None:
        """Clear all pending events"""
        with self._lock:
            self.events.clear()
            
    def get_next_event_time(self) -> Optional[float]:
        """Get time of next scheduled event"""
        with self._lock:
            if self.events:
                return self.events[0].time_us
        return None
        
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        avg_scheduling = 0
        avg_execution = 0
        
        if self.events_processed > 0:
            avg_scheduling = self.total_scheduling_time / self.events_processed
            avg_execution = self.total_execution_time / self.events_processed
            
        return {
            'events_processed': self.events_processed,
            'pending_events': self.get_pending_events(),
            'average_scheduling_time_ms': avg_scheduling * 1000,
            'average_execution_time_ms': avg_execution * 1000,
            'virtual_time_us': self.clock.get_time_us()
        }
        
    def reset(self) -> None:
        """Reset timing engine to initial state"""
        with self._lock:
            self.clock.reset()
            self.events.clear()
            self.next_event_id = 0
            self.events_processed = 0
            self.total_scheduling_time = 0.0
            self.total_execution_time = 0.0