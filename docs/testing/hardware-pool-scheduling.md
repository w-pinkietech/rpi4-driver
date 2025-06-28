# Hardware Pool Scheduling Algorithms

## Overview

This document details the scheduling algorithms for efficient hardware pool management, ensuring fair access, minimal wait times, and optimal resource utilization.

## Core Scheduling Algorithm: Weighted Fair Queue with Priority Preemption

### Algorithm Design

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import heapq

@dataclass
class TestRequest:
    id: str
    team_id: str
    priority: int  # 0=CRITICAL, 1=HIGH, 2=NORMAL, 3=LOW
    required_capabilities: List[str]
    estimated_duration: timedelta
    submitted_at: datetime
    max_wait_time: Optional[timedelta]
    preemptible: bool = True
    
@dataclass
class HardwareNode:
    id: str
    capabilities: List[str]
    status: str  # 'available', 'busy', 'maintenance'
    current_job: Optional[str] = None
    available_at: Optional[datetime] = None

class WeightedFairScheduler:
    """
    Implements a weighted fair queue with priority preemption for hardware allocation.
    """
    
    def __init__(self):
        self.queue: List[TestRequest] = []
        self.hardware_pool: Dict[str, HardwareNode] = {}
        self.team_quotas: Dict[str, float] = {}
        self.team_usage: Dict[str, timedelta] = {}
        
    def calculate_weight(self, request: TestRequest) -> float:
        """
        Calculate scheduling weight based on multiple factors.
        Lower weight = higher priority.
        """
        # Base weight from priority
        base_weight = request.priority * 1000
        
        # Time waiting factor (increases urgency over time)
        wait_time = datetime.now() - request.submitted_at
        wait_factor = max(0, 1 - (wait_time.total_seconds() / 3600))  # Decreases over hour
        
        # Team quota factor
        team_usage_ratio = self.get_team_usage_ratio(request.team_id)
        quota_factor = team_usage_ratio * 2  # Penalize overuse
        
        # Duration factor (prefer shorter tests)
        duration_factor = request.estimated_duration.total_seconds() / 300  # Normalized to 5 min
        
        # Calculate final weight
        weight = base_weight * (1 + wait_factor + quota_factor + duration_factor)
        
        # Critical priority override
        if request.priority == 0:  # CRITICAL
            weight = weight * 0.1  # 10x boost
            
        return weight
    
    def find_suitable_hardware(self, request: TestRequest) -> Optional[HardwareNode]:
        """Find hardware that matches the test requirements."""
        for hw_id, hardware in self.hardware_pool.items():
            if hardware.status == 'available':
                if all(cap in hardware.capabilities for cap in request.required_capabilities):
                    return hardware
        return None
    
    def can_preempt(self, request: TestRequest, hardware: HardwareNode) -> bool:
        """Determine if the request can preempt current job."""
        if not request.preemptible or hardware.current_job is None:
            return False
            
        current_job = self.get_job(hardware.current_job)
        if not current_job or not current_job.preemptible:
            return False
            
        # Only higher priority can preempt
        return request.priority < current_job.priority
    
    def schedule_next(self) -> Optional[Tuple[TestRequest, HardwareNode]]:
        """Select the next test to run based on weighted fair queue."""
        if not self.queue:
            return None
            
        # Sort queue by weight
        self.queue.sort(key=lambda r: self.calculate_weight(r))
        
        for request in self.queue:
            # Check if request has exceeded max wait time
            if request.max_wait_time:
                wait_time = datetime.now() - request.submitted_at
                if wait_time > request.max_wait_time:
                    self.queue.remove(request)
                    self.handle_timeout(request)
                    continue
            
            # Try to find suitable hardware
            hardware = self.find_suitable_hardware(request)
            if hardware:
                self.queue.remove(request)
                return (request, hardware)
            
            # Check for preemption opportunity
            for hw_id, hw in self.hardware_pool.items():
                if self.can_preempt(request, hw):
                    self.preempt_job(hw)
                    self.queue.remove(request)
                    return (request, hw)
        
        return None
```

### Advanced Scheduling Features

#### 1. Predictive Scheduling
```python
class PredictiveScheduler(WeightedFairScheduler):
    """Extends scheduler with ML-based prediction capabilities."""
    
    def __init__(self):
        super().__init__()
        self.duration_model = self.load_duration_model()
        self.failure_model = self.load_failure_model()
        
    def predict_duration(self, request: TestRequest) -> timedelta:
        """Use ML model to predict actual test duration."""
        features = self.extract_features(request)
        predicted_seconds = self.duration_model.predict(features)
        
        # Add safety margin based on confidence
        confidence = self.duration_model.confidence(features)
        margin = 1.2 if confidence < 0.8 else 1.1
        
        return timedelta(seconds=predicted_seconds * margin)
    
    def predict_failure_probability(self, request: TestRequest) -> float:
        """Predict likelihood of test failure."""
        features = self.extract_features(request)
        return self.failure_model.predict_proba(features)
    
    def optimize_schedule(self, queue: List[TestRequest]) -> List[TestRequest]:
        """Optimize queue order for maximum throughput."""
        # Group similar tests for batching
        grouped = self.group_similar_tests(queue)
        
        # Optimize within groups
        optimized = []
        for group in grouped:
            # Sort by predicted duration (shortest first)
            group.sort(key=lambda r: self.predict_duration(r))
            optimized.extend(group)
        
        return optimized
```

#### 2. Hardware Affinity Scheduling
```python
class AffinityScheduler(PredictiveScheduler):
    """Considers hardware affinity for better performance."""
    
    def __init__(self):
        super().__init__()
        self.affinity_map: Dict[str, Dict[str, float]] = {}
        
    def update_affinity(self, test_type: str, hardware_id: str, performance: float):
        """Update affinity scores based on historical performance."""
        if test_type not in self.affinity_map:
            self.affinity_map[test_type] = {}
        
        # Exponential moving average
        alpha = 0.3
        old_score = self.affinity_map[test_type].get(hardware_id, 0.5)
        self.affinity_map[test_type][hardware_id] = alpha * performance + (1 - alpha) * old_score
    
    def find_suitable_hardware(self, request: TestRequest) -> Optional[HardwareNode]:
        """Find hardware with consideration for affinity."""
        candidates = []
        
        for hw_id, hardware in self.hardware_pool.items():
            if hardware.status == 'available':
                if all(cap in hardware.capabilities for cap in request.required_capabilities):
                    # Calculate affinity score
                    test_type = self.get_test_type(request)
                    affinity = self.affinity_map.get(test_type, {}).get(hw_id, 0.5)
                    candidates.append((hardware, affinity))
        
        if candidates:
            # Return hardware with highest affinity
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
```

#### 3. Cost-Aware Scheduling
```python
class CostAwareScheduler(AffinityScheduler):
    """Considers operational costs in scheduling decisions."""
    
    def __init__(self):
        super().__init__()
        self.hardware_costs: Dict[str, float] = {}  # $/hour
        self.energy_costs: Dict[str, float] = {}   # kWh
        
    def calculate_job_cost(self, request: TestRequest, hardware: HardwareNode) -> float:
        """Calculate estimated cost of running test on specific hardware."""
        duration_hours = self.predict_duration(request).total_seconds() / 3600
        
        # Base hardware cost
        hw_cost = self.hardware_costs.get(hardware.id, 1.0) * duration_hours
        
        # Energy cost
        energy_cost = self.energy_costs.get(hardware.id, 0.1) * duration_hours * 0.15  # $/kWh
        
        # Opportunity cost (if preempting)
        opportunity_cost = 0
        if hardware.current_job:
            opportunity_cost = self.calculate_preemption_cost(hardware.current_job)
        
        return hw_cost + energy_cost + opportunity_cost
    
    def schedule_with_budget(self, request: TestRequest, budget: float) -> Optional[HardwareNode]:
        """Schedule within budget constraints."""
        candidates = []
        
        for hw_id, hardware in self.hardware_pool.items():
            if self.is_suitable(hardware, request):
                cost = self.calculate_job_cost(request, hardware)
                if cost <= budget:
                    candidates.append((hardware, cost))
        
        if candidates:
            # Choose lowest cost option
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        
        return None
```

## Scheduling Policies

### 1. Team Quota Management
```yaml
quota_policies:
  default_quota:
    daily_hours: 8
    weekly_hours: 40
    burst_allowance: 2x  # Can burst to 2x quota for short periods
    
  team_quotas:
    infrastructure:
      daily_hours: 16  # Higher quota for infra team
      priority_boost: 0.9
    
    development:
      daily_hours: 8
      priority_boost: 1.0
    
    qa:
      daily_hours: 12
      priority_boost: 0.95
  
  enforcement:
    soft_limit:
      action: "deprioritize"
      factor: 1.5
    
    hard_limit:
      action: "queue_delay"
      delay: "exponential_backoff"
```

### 2. Fairness Guarantees
```python
class FairnessMonitor:
    """Ensures fair access to hardware resources."""
    
    def __init__(self):
        self.wait_times: Dict[str, List[timedelta]] = {}
        self.allocation_counts: Dict[str, int] = {}
        
    def calculate_jain_fairness_index(self) -> float:
        """Calculate Jain's fairness index (0-1, 1 being perfectly fair)."""
        allocations = list(self.allocation_counts.values())
        if not allocations:
            return 1.0
            
        n = len(allocations)
        sum_alloc = sum(allocations)
        sum_squares = sum(x**2 for x in allocations)
        
        return (sum_alloc ** 2) / (n * sum_squares)
    
    def get_fairness_report(self) -> Dict:
        """Generate fairness metrics report."""
        return {
            'jain_index': self.calculate_jain_fairness_index(),
            'avg_wait_by_team': {
                team: sum(times, timedelta()) / len(times)
                for team, times in self.wait_times.items()
            },
            'allocation_distribution': self.allocation_counts,
            'recommendations': self.generate_fairness_recommendations()
        }
```

### 3. SLA Enforcement
```python
@dataclass
class SLA:
    team_id: str
    max_wait_time: timedelta
    min_availability: float  # Percentage
    priority_override: Optional[int] = None

class SLAScheduler(CostAwareScheduler):
    """Enforces Service Level Agreements in scheduling."""
    
    def __init__(self):
        super().__init__()
        self.slas: Dict[str, SLA] = {}
        self.sla_metrics: Dict[str, Dict] = {}
        
    def check_sla_violation_risk(self, request: TestRequest) -> bool:
        """Check if request is at risk of violating SLA."""
        sla = self.slas.get(request.team_id)
        if not sla:
            return False
            
        wait_time = datetime.now() - request.submitted_at
        time_remaining = sla.max_wait_time - wait_time
        
        # Predict if we can meet SLA
        next_available = self.predict_next_availability(request)
        return next_available > time_remaining
    
    def emergency_escalation(self, request: TestRequest):
        """Escalate request to prevent SLA violation."""
        # Temporarily boost priority
        request.priority = 0  # CRITICAL
        
        # Try to allocate immediately
        hardware = self.find_any_suitable_hardware(request)
        if hardware:
            # Preempt if necessary
            if hardware.current_job:
                self.preempt_job(hardware)
            
            return hardware
        
        # Alert operations team
        self.send_sla_alert(request)
```

## Implementation Best Practices

### 1. Queue Optimization
- Maintain separate queues for different priority levels
- Use heap data structure for O(log n) insertion/removal
- Periodically rebalance queues based on fairness metrics

### 2. Hardware Utilization
- Implement "warm-up" periods to prepare hardware
- Batch similar tests to minimize reconfiguration
- Use predictive maintenance to schedule downtime

### 3. Monitoring and Alerting
- Real-time dashboard with queue depths and wait times
- Alert on SLA violations or fairness degradation
- Track hardware efficiency and reliability metrics

### 4. Scalability Considerations
- Distribute scheduler across multiple nodes for HA
- Use event-driven architecture for state changes
- Implement circuit breakers for failing hardware

## Metrics and KPIs

```yaml
scheduling_metrics:
  efficiency:
    - hardware_utilization_rate
    - average_queue_wait_time
    - test_throughput_per_hour
    
  fairness:
    - jain_fairness_index
    - p95_wait_time_by_team
    - quota_usage_distribution
    
  reliability:
    - sla_compliance_rate
    - preemption_frequency
    - hardware_failure_impact
    
  optimization:
    - prediction_accuracy
    - scheduling_overhead
    - cost_per_test_hour
```

This scheduling system ensures that hardware resources are utilized efficiently while maintaining fairness and meeting SLA requirements. The multi-factor weighting system adapts to changing conditions and team needs, while predictive capabilities help optimize overall throughput.