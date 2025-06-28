"""Tests for hardware mock framework"""

import pytest
import time
from src.mocks import (
    GPIOMock, I2CMock, SPIMock, UARTMock,
    TimingEngine, VirtualClock
)
from src.mocks.i2c import I2CDeviceMock
from src.mocks.spi import SPIDeviceMock


class TestTimingEngine:
    """Test timing engine functionality"""
    
    def test_virtual_clock(self):
        """Test virtual clock advancement"""
        clock = VirtualClock(real_time_factor=0)  # Instant
        
        assert clock.get_time_us() == 0
        
        clock.advance_us(1000)
        assert clock.get_time_us() == 1000
        
        clock.reset()
        assert clock.get_time_us() == 0
        
    def test_event_scheduling(self):
        """Test event scheduling and execution"""
        engine = TimingEngine()
        events_fired = []
        
        # Schedule events
        engine.schedule_event(100, lambda: events_fired.append(1))
        engine.schedule_event(50, lambda: events_fired.append(2))
        engine.schedule_event(150, lambda: events_fired.append(3))
        
        # Run until 120us
        engine.run_until(120)
        
        # Events at 50us and 100us should have fired
        assert events_fired == [2, 1]
        
        # Run to 200us
        engine.run_until(200)
        
        # Event at 150us should now fire
        assert events_fired == [2, 1, 3]
        
    def test_event_cancellation(self):
        """Test event cancellation"""
        engine = TimingEngine()
        fired = False
        
        # Schedule and cancel
        event_id = engine.schedule_event(100, lambda: setattr(self, 'fired', True))
        assert engine.cancel_event(event_id)
        
        # Run past event time
        engine.run_until(200)
        
        # Event should not have fired
        assert not fired


class TestGPIOMock:
    """Test GPIO mock functionality"""
    
    def test_pin_setup(self):
        """Test basic pin configuration"""
        gpio = GPIOMock()
        gpio.initialize()
        
        # Setup output pin
        gpio.setup(17, 'output')
        state = gpio.get_pin_state(17)
        assert state.mode.value == 'output'
        
        # Setup input with pull-up
        gpio.setup(27, 'input', 'up')
        state = gpio.get_pin_state(27)
        assert state.mode.value == 'input'
        assert state.pull.value == 'up'
        assert state.value == 1  # Pull-up sets high
        
    def test_output_operation(self):
        """Test output pin operation"""
        gpio = GPIOMock()
        gpio.initialize()
        
        gpio.setup(17, 'output')
        
        # Write high
        gpio.output(17, 1)
        assert gpio.get_pin_state(17).value == 1
        
        # Write low
        gpio.output(17, 0)
        assert gpio.get_pin_state(17).value == 0
        
    def test_input_operation(self):
        """Test input pin operation"""
        gpio = GPIOMock()
        gpio.initialize()
        
        gpio.setup(22, 'input')
        
        # Simulate external signal
        gpio.simulate_edge(22, 1)
        assert gpio.input(22) == 1
        
        gpio.simulate_edge(22, 0)
        assert gpio.input(22) == 0
        
    def test_edge_detection(self):
        """Test edge detection and callbacks"""
        gpio = GPIOMock()
        gpio.initialize()
        
        edges_detected = []
        
        gpio.setup(22, 'input')
        gpio.add_event_detect(22, 'rising', 
                             callback=lambda pin: edges_detected.append(pin))
        
        # Simulate rising edge
        gpio.simulate_edge(22, 1)
        
        # Give interrupt thread time to process
        time.sleep(0.01)
        
        assert 22 in edges_detected
        
    def test_debouncing(self):
        """Test debounce functionality"""
        gpio = GPIOMock()
        gpio.initialize()
        
        edges_detected = []
        
        gpio.setup(22, 'input')
        gpio.add_event_detect(22, 'both',
                             callback=lambda pin: edges_detected.append(pin),
                             bouncetime=10)  # 10ms debounce
        
        # Simulate bouncing signal
        gpio.simulate_edge(22, 1)
        gpio.simulate_edge(22, 0, delay_us=1000)  # 1ms later
        gpio.simulate_edge(22, 1, delay_us=2000)  # 2ms later
        
        # Process events
        gpio.timing_engine.run_for(20000)  # Run for 20ms
        time.sleep(0.01)
        
        # Only first edge should be detected due to debounce
        assert len(edges_detected) == 1


class TestI2CMock:
    """Test I2C mock functionality"""
    
    def test_device_detection(self):
        """Test I2C device scanning"""
        i2c = I2CMock()
        i2c.initialize()
        
        # Add virtual devices
        device1 = I2CDeviceMock(0x48)
        device2 = I2CDeviceMock(0x68)
        
        i2c.add_device(device1)
        i2c.add_device(device2)
        
        # Scan bus
        devices = i2c.scan()
        
        assert 0x48 in devices
        assert 0x68 in devices
        assert len(devices) == 2
        
    def test_write_read_transaction(self):
        """Test I2C write-read transaction"""
        i2c = I2CMock()
        i2c.initialize()
        
        # Create virtual device with registers
        class TestDevice(I2CDeviceMock):
            def __init__(self):
                super().__init__(0x48)
                self.registers = {0x00: 0x12, 0x01: 0x34}
                self.pointer = 0
                
            def write(self, data):
                if data:
                    self.pointer = data[0]
                return True
                
            def read(self, length):
                result = []
                for i in range(length):
                    addr = (self.pointer + i) & 0xFF
                    result.append(self.registers.get(addr, 0xFF))
                return bytes(result)
                
        device = TestDevice()
        i2c.add_device(device)
        
        # Write register address and read data
        data = i2c.write_read(0x48, b'\x00', 2)
        
        assert data == b'\x12\x34'
        
    def test_timing_accuracy(self):
        """Test I2C timing accuracy"""
        i2c = I2CMock()
        i2c.initialize(speed=i2c.I2CSpeed.STANDARD)  # 100kHz
        
        device = I2CDeviceMock(0x50)
        i2c.add_device(device)
        
        # Perform transaction
        start_time = i2c.timing_engine.clock.get_time_us()
        i2c.write_read(0x50, b'\x00\x01\x02', 0)
        end_time = i2c.timing_engine.clock.get_time_us()
        
        # Calculate expected time
        # START (4.7us) + 4 bytes * 9 bits/byte * 10us/bit + STOP (4us)
        expected_min = 4.7 + 4 * 9 * 10 + 4
        
        actual = end_time - start_time
        assert actual >= expected_min


class TestSPIMock:
    """Test SPI mock functionality"""
    
    def test_basic_transfer(self):
        """Test basic SPI transfer"""
        spi = SPIMock()
        spi.initialize()
        
        # Create echo device
        class EchoDevice(SPIDeviceMock):
            def transfer_byte(self, tx_byte):
                return tx_byte  # Echo back
                
        device = EchoDevice(chip_select=0)
        spi.add_device(device)
        
        # Transfer data
        tx_data = b'\x01\x02\x03\x04'
        rx_data = spi.transfer(tx_data, chip_select=0)
        
        assert rx_data == tx_data
        
    def test_spi_modes(self):
        """Test different SPI modes"""
        from src.mocks.spi import SPIMode, SPIConfig
        
        spi = SPIMock()
        
        # Test all 4 modes
        for mode in [SPIMode.MODE_0, SPIMode.MODE_1, 
                    SPIMode.MODE_2, SPIMode.MODE_3]:
            config = SPIConfig(mode=mode)
            spi.configure(config)
            spi.initialize()
            
            # Clock should start at correct polarity
            cpol, _ = mode.value
            bus_state = spi.get_bus_state()
            assert bus_state['sclk'] == cpol
            
    def test_chip_select(self):
        """Test chip select handling"""
        spi = SPIMock()
        spi.initialize()
        
        selected_devices = []
        
        class TrackingDevice(SPIDeviceMock):
            def __init__(self, cs):
                super().__init__(cs)
                self.parent_list = selected_devices
                
            def select(self):
                super().select()
                self.parent_list.append(self.chip_select)
                
        # Add multiple devices
        for cs in range(3):
            spi.add_device(TrackingDevice(cs))
            
        # Transfer to different devices
        spi.transfer(b'\x00', chip_select=1)
        spi.transfer(b'\x00', chip_select=2)
        
        assert selected_devices == [1, 2]


class TestUARTMock:
    """Test UART mock functionality"""
    
    def test_basic_communication(self):
        """Test basic UART communication"""
        uart = UARTMock()
        uart.initialize(baudrate=9600)
        
        # Enable loopback
        uart.enable_loopback()
        
        # Transmit data
        tx_data = b'Hello UART!'
        written = uart.write(tx_data)
        assert written == len(tx_data)
        
        # Receive data
        rx_data = uart.read(len(tx_data))
        assert rx_data == tx_data
        
    def test_peer_communication(self):
        """Test UART peer-to-peer communication"""
        uart1 = UARTMock("/dev/ttyS0")
        uart2 = UARTMock("/dev/ttyS1")
        
        uart1.initialize(baudrate=115200)
        uart2.initialize(baudrate=115200)
        
        # Connect peers
        uart1.connect_peer(uart2)
        
        # Send from uart1 to uart2
        uart1.write(b'From UART1')
        data = uart2.read(10)
        assert data == b'From UART1'
        
        # Send from uart2 to uart1
        uart2.write(b'From UART2')
        data = uart1.read(10)
        assert data == b'From UART2'
        
    def test_flow_control(self):
        """Test hardware flow control"""
        from src.mocks.uart import FlowControl, UARTConfig
        
        config = UARTConfig(flow_control=FlowControl.HARDWARE)
        uart = UARTMock()
        uart.initialize(config=config)
        
        # Clear CTS (not clear to send)
        uart.cts = False
        
        # Try to transmit
        written = uart.write(b'Test')
        assert written == 0  # Should not transmit
        
        # Set CTS
        uart.cts = True
        written = uart.write(b'Test')
        assert written == 4  # Should transmit
        
    def test_break_condition(self):
        """Test break condition"""
        uart = UARTMock()
        uart.initialize()
        uart.enable_loopback()
        
        # Send break
        uart.send_break(duration=0.1)
        
        # Try to read
        with pytest.raises(Exception) as exc_info:
            uart.read(1)
        assert "Break condition" in str(exc_info.value)
        
    def test_timing_accuracy(self):
        """Test UART timing accuracy"""
        uart = UARTMock()
        uart.initialize(baudrate=9600, bytesize=8, stopbits=1)
        
        # Measure transmission time
        start_time = uart.timing_engine.clock.get_time_us()
        uart.write(b'X')  # Single byte
        end_time = uart.timing_engine.clock.get_time_us()
        
        # Calculate expected time
        # 1 start + 8 data + 1 stop = 10 bits
        # At 9600 baud: 10 bits * (1/9600) seconds = 1041.67 us
        expected_us = 10 * 1_000_000 / 9600
        
        actual_us = end_time - start_time
        
        # Allow small tolerance
        assert abs(actual_us - expected_us) < 1


class TestErrorInjection:
    """Test error injection capabilities"""
    
    def test_gpio_stuck_pin(self):
        """Test GPIO stuck pin error"""
        gpio = GPIOMock()
        gpio.initialize()
        
        gpio.setup(17, 'output')
        gpio.enable_error_injection()
        
        # Inject stuck pin
        gpio.inject_error('stuck_pin', pin=17, value=1)
        
        # Try to change value (should remain stuck)
        gpio.output(17, 0)
        assert gpio.get_pin_state(17).value == 1  # Still stuck high
        
    def test_i2c_bus_error(self):
        """Test I2C bus error injection"""
        i2c = I2CMock()
        i2c.initialize()
        i2c.enable_error_injection()
        
        # Inject SDA stuck low
        with pytest.raises(Exception) as exc_info:
            i2c.inject_error('sda_stuck_low')
        assert "stuck low" in str(exc_info.value)
        
    def test_uart_overrun(self):
        """Test UART buffer overrun"""
        uart = UARTMock()
        uart.initialize()
        uart.enable_error_injection()
        
        # Inject overrun
        uart.inject_error('overrun')
        
        # Check buffer is full
        stats = uart.get_statistics()
        assert stats['rx_buffer_size'] == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])