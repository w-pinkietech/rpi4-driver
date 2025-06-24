# Custom Protocol Support Strategy

## Philosophy: Progressive Enhancement with Guaranteed Passthrough

The system follows a **"70% automatic, 30% learning"** approach where unknown protocols are always passed through transparently while the system progressively learns to handle them better.

## Protocol Support Levels

### Level 1: Transparent Passthrough (100% coverage)
**Guarantee**: All data is forwarded regardless of understanding
```python
# Always works - raw data forwarding
{
  "device": "/dev/ttyUSB0",
  "timestamp": 1736931234.567890,
  "raw_data": "base64_encoded_bytes",
  "protocol": "unknown"
}
```

### Level 2: Pattern Recognition (70% target)
**Capability**: Automatic protocol detection for common patterns
```python
# Known patterns
PROTOCOL_PATTERNS = {
    'nmea_gps': r'^\$GP[A-Z]{3},.*\*[0-9A-F]{2}$',
    'json_sensor': r'^\{.*"value".*\}$',
    'modbus_rtu': r'^[\x01-\xF7][\x03\x04\x06\x10].*',
    'ascii_delimited': r'^[A-Za-z0-9,.\-\s]+[\r\n]+$'
}
```

### Level 3: Custom Protocol Definition (User-extensible)
**Flexibility**: User-defined protocol parsers and configurations
```yaml
# config/custom_protocols.yaml
protocols:
  my_weather_station:
    name: "Custom Weather Station v2.1"
    vendor: "WeatherCorp"
    init_sequence: [0xAA, 0x55, 0x01]
    response_pattern: "^WS:[0-9\\.]+:[0-9\\.]+:[0-9\\.]+$"
    parser: "parsers/weather_station_v21.py"
    timeout: 2.0
    documentation: "protocols/weather_station_v21.md"
```

### Level 4: Machine Learning (Future enhancement)
**Intelligence**: Automatic pattern discovery and protocol evolution
```python
# Future: ML-based protocol discovery
class ProtocolLearner:
    def analyze_patterns(self, device_samples):
        # Cluster similar data patterns
        # Suggest protocol structures
        # Generate parsing hints
        pass
```

## Implementation Architecture

### Protocol Manager Service
```python
class ProtocolManager:
    """Manages protocol detection and custom protocol support"""
    
    def __init__(self):
        self.known_protocols = self.load_builtin_protocols()
        self.custom_protocols = self.load_custom_protocols()
        self.learning_engine = ProtocolLearner()
    
    async def process_device_data(self, device_path: str, raw_data: bytes) -> Dict:
        """Process data with progressive protocol enhancement"""
        
        # Level 1: Always guarantee passthrough
        result = {
            'device': device_path,
            'timestamp': time.time(),
            'raw_data': base64.b64encode(raw_data).decode(),
            'protocol': 'unknown',
            'confidence': 0.0
        }
        
        # Level 2: Try pattern recognition
        detected_protocol = await self.detect_protocol(raw_data)
        if detected_protocol:
            result.update({
                'protocol': detected_protocol['name'],
                'confidence': detected_protocol['confidence'],
                'parsed_data': detected_protocol.get('parsed_data')
            })
        
        # Level 3: Try custom protocols
        if result['confidence'] < 0.7:
            custom_result = await self.try_custom_protocols(device_path, raw_data)
            if custom_result:
                result.update(custom_result)
        
        # Level 4: Feed learning engine
        await self.learning_engine.process_sample(device_path, raw_data, result)
        
        return result
```

## Custom Protocol Definition Format

### Protocol Configuration File
```yaml
# config/protocols/my_device.yaml
protocol:
  name: "My Custom Device Protocol"
  version: "1.0"
  vendor: "MyCompany"
  device_types: ["sensor", "actuator"]
  
connection:
  baudrate: 9600
  data_bits: 8
  stop_bits: 1
  parity: "none"
  timeout: 1.0
  
initialization:
  required: true
  sequence:
    - send: [0xAA, 0x55]
    - wait: 0.1
    - expect: [0x55, 0xAA]
    - send: [0x01, 0x02, 0x03]
  
data_format:
  type: "structured"
  pattern: "^DATA:([0-9\\.]+):([0-9\\.]+):([0-9\\.]+)\\r\\n$"
  fields:
    - name: "temperature"
      type: "float"
      unit: "celsius"
      group: 1
    - name: "humidity" 
      type: "float"
      unit: "percent"
      group: 2
    - name: "pressure"
      type: "float"
      unit: "hPa"
      group: 3

error_handling:
  retry_count: 3
  timeout_action: "reset_connection"
  malformed_data: "log_and_continue"

metadata:
  documentation: "docs/protocols/my_device.md"
  parser: "parsers/my_device.py"
  examples: "examples/my_device/"
  created: "2024-01-15"
  author: "john.doe@mycompany.com"
```

### Custom Parser Implementation
```python
# parsers/my_device.py
"""Custom parser for My Device Protocol"""

import re
from typing import Dict, Optional, Any

class MyDeviceParser:
    """Parser for My Custom Device Protocol v1.0"""
    
    PATTERN = re.compile(r'^DATA:([0-9\.]+):([0-9\.]+):([0-9\.]+)\r\n$')
    
    def __init__(self, config: Dict):
        self.config = config
        self.initialized = False
    
    async def initialize(self, connection) -> bool:
        """Initialize device connection"""
        try:
            # Send initialization sequence
            await connection.write(bytes([0xAA, 0x55]))
            await asyncio.sleep(0.1)
            
            response = await connection.read(2)
            if response == bytes([0x55, 0xAA]):
                await connection.write(bytes([0x01, 0x02, 0x03]))
                self.initialized = True
                return True
        except Exception as e:
            print(f"Initialization failed: {e}")
        
        return False
    
    def parse(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """Parse raw data according to protocol specification"""
        try:
            text = raw_data.decode('utf-8')
            match = self.PATTERN.match(text)
            
            if match:
                return {
                    'temperature': float(match.group(1)),
                    'humidity': float(match.group(2)),
                    'pressure': float(match.group(3)),
                    'unit': {
                        'temperature': 'celsius',
                        'humidity': 'percent', 
                        'pressure': 'hPa'
                    },
                    'parsed': True,
                    'confidence': 1.0
                }
        except Exception as e:
            print(f"Parse error: {e}")
        
        return None
    
    def validate(self, parsed_data: Dict) -> bool:
        """Validate parsed data makes sense"""
        temp = parsed_data.get('temperature', 0)
        humidity = parsed_data.get('humidity', 0)
        pressure = parsed_data.get('pressure', 0)
        
        # Basic range validation
        return (-50 <= temp <= 100 and 
                0 <= humidity <= 100 and 
                300 <= pressure <= 1200)
```

## Protocol Learning System

### Automatic Pattern Discovery
```python
class ProtocolLearner:
    """Automatically discover patterns in unknown protocols"""
    
    def __init__(self):
        self.device_samples = defaultdict(list)
        self.min_samples = 50
        self.confidence_threshold = 0.8
    
    async def process_sample(self, device_path: str, data: bytes, result: Dict):
        """Process a data sample for learning"""
        
        # Store sample if protocol confidence is low
        if result.get('confidence', 0) < 0.7:
            self.device_samples[device_path].append({
                'timestamp': time.time(),
                'data': data,
                'length': len(data),
                'printable_ratio': self.calculate_printable_ratio(data)
            })
            
            # Analyze when we have enough samples
            if len(self.device_samples[device_path]) >= self.min_samples:
                await self.analyze_device_patterns(device_path)
    
    async def analyze_device_patterns(self, device_path: str):
        """Analyze collected samples to discover patterns"""
        samples = self.device_samples[device_path]
        
        patterns = {
            'fixed_length': self.detect_fixed_length_pattern(samples),
            'delimited': self.detect_delimiter_pattern(samples),
            'structured': self.detect_structured_pattern(samples),
            'binary': self.detect_binary_pattern(samples)
        }
        
        # Find the most confident pattern
        best_pattern = max(patterns.items(), key=lambda x: x[1]['confidence'])
        
        if best_pattern[1]['confidence'] > self.confidence_threshold:
            await self.suggest_protocol_config(device_path, best_pattern)
    
    def detect_fixed_length_pattern(self, samples: List[Dict]) -> Dict:
        """Detect if data has consistent fixed length"""
        lengths = [s['length'] for s in samples]
        most_common_length = Counter(lengths).most_common(1)[0]
        
        confidence = most_common_length[1] / len(samples)
        
        return {
            'type': 'fixed_length',
            'length': most_common_length[0],
            'confidence': confidence,
            'description': f"Fixed length messages of {most_common_length[0]} bytes"
        }
    
    def detect_delimiter_pattern(self, samples: List[Dict]) -> Dict:
        """Detect common delimiters in data"""
        common_delimiters = [b'\r\n', b'\n', b'\r', b'\x00', b',', b';']
        delimiter_counts = defaultdict(int)
        
        for sample in samples:
            for delim in common_delimiters:
                if delim in sample['data']:
                    delimiter_counts[delim] += 1
        
        if delimiter_counts:
            best_delim = max(delimiter_counts.items(), key=lambda x: x[1])
            confidence = best_delim[1] / len(samples)
            
            return {
                'type': 'delimited',
                'delimiter': best_delim[0],
                'confidence': confidence,
                'description': f"Delimiter-based with {best_delim[0]!r}"
            }
        
        return {'type': 'delimited', 'confidence': 0.0}
    
    async def suggest_protocol_config(self, device_path: str, pattern: Tuple):
        """Generate a suggested protocol configuration"""
        pattern_type, pattern_info = pattern
        
        suggestion = {
            'device': device_path,
            'suggested_protocol': {
                'name': f"Auto-detected {pattern_type}",
                'type': pattern_type,
                'confidence': pattern_info['confidence'],
                'config': pattern_info,
                'auto_generated': True,
                'timestamp': time.time()
            }
        }
        
        # Publish suggestion for user review
        await self.publish_protocol_suggestion(suggestion)
```

## Community Protocol Sharing

### Protocol Repository Structure
```
protocols/
├── builtin/           # Built-in protocol definitions
│   ├── nmea_gps.yaml
│   ├── modbus_rtu.yaml
│   └── json_generic.yaml
├── community/         # Community-contributed protocols
│   ├── arduino_firmata.yaml
│   ├── weatherstation_ws2000.yaml
│   └── industrial_plc_siemens.yaml
├── user/             # User-specific protocols
│   ├── my_sensor.yaml
│   └── prototype_device.yaml
└── learned/          # Auto-generated from learning
    ├── unknown_device_001.yaml
    └── pattern_12345.yaml
```

### Protocol Sharing API
```python
class ProtocolRepository:
    """Manage protocol definitions and sharing"""
    
    async def submit_protocol(self, protocol_config: Dict, 
                            examples: List[bytes]) -> str:
        """Submit a protocol definition to community repository"""
        
        # Validate protocol definition
        if not self.validate_protocol_config(protocol_config):
            raise ValueError("Invalid protocol configuration")
        
        # Generate protocol ID
        protocol_id = self.generate_protocol_id(protocol_config)
        
        # Create submission package
        submission = {
            'id': protocol_id,
            'config': protocol_config,
            'examples': [base64.b64encode(ex).decode() for ex in examples],
            'submitted_by': 'anonymous',
            'submitted_at': time.time(),
            'verification_status': 'pending'
        }
        
        # Submit to community repository
        await self.upload_to_repository(submission)
        
        return protocol_id
    
    async def search_protocols(self, device_info: Dict) -> List[Dict]:
        """Search for matching protocol definitions"""
        
        # Search by VID/PID if available
        if device_info.get('vendor_id') and device_info.get('product_id'):
            vid_pid_matches = await self.search_by_vid_pid(
                device_info['vendor_id'], 
                device_info['product_id']
            )
            if vid_pid_matches:
                return vid_pid_matches
        
        # Search by device characteristics
        return await self.search_by_characteristics(device_info)
```

## Usage Examples

### 1. Basic Unknown Device
```bash
# Device connected: /dev/ttyUSB0 (unknown)
# System automatically:
# 1. Forwards all data transparently
# 2. Attempts pattern recognition
# 3. Learns patterns over time

# MQTT output:
Topic: rpi4/uart/ttyUSB0/data
Payload: {
  "device": "/dev/ttyUSB0",
  "timestamp": 1736931234.567890,
  "raw_data": "VGVtcDoyMy41LEh1bWlkaXR5OjY1LjINCg==",
  "protocol": "unknown",
  "confidence": 0.0
}
```

### 2. Custom Protocol Definition
```bash
# 1. Add protocol definition
echo "protocol: ..." > config/protocols/my_sensor.yaml

# 2. Add custom parser
cp my_sensor_parser.py parsers/

# 3. Restart system
docker-compose restart device-manager

# 4. Device now automatically recognized
Topic: rpi4/uart/ttyUSB0/data  
Payload: {
  "device": "/dev/ttyUSB0",
  "protocol": "my_sensor_v1",
  "confidence": 1.0,
  "parsed_data": {
    "temperature": 23.5,
    "humidity": 65.2,
    "units": {"temperature": "celsius", "humidity": "percent"}
  }
}
```

### 3. Protocol Learning in Action
```bash
# After 50+ samples of unknown device:
Topic: rpi4/system/protocol_suggestions
Payload: {
  "device": "/dev/ttyUSB0",
  "suggestion": {
    "name": "Auto-detected delimited",
    "type": "delimited", 
    "delimiter": "\r\n",
    "confidence": 0.85,
    "sample_count": 50
  },
  "next_steps": [
    "Review suggestion",
    "Create protocol definition", 
    "Add to custom protocols"
  ]
}
```

## Benefits of This Approach

### For Users
- **Zero fear factor**: Unknown devices always work (raw passthrough)
- **Progressive improvement**: System gets smarter over time
- **Community benefit**: Share and benefit from others' protocol work

### For Developers  
- **Extensible design**: Easy to add new protocol support
- **No breaking changes**: New protocols don't affect existing functionality
- **Test-driven**: Can test protocols with known data samples

### For Operations
- **Guaranteed compatibility**: No device is ever "unsupported"
- **Graceful degradation**: System works even with 100% unknown protocols
- **Incremental value**: Value increases as protocol library grows

This strategy ensures the system provides immediate value while continuously improving through use and community contribution.