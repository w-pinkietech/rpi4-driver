"""Hardware Mock Framework for RPi4 Driver Testing

This package provides sophisticated hardware mocks that enable testing without physical hardware.
All mocks are designed to be drop-in replacements for real hardware interfaces.
"""

from .base import BaseMock, MockException
from .timing import TimingEngine, VirtualClock
from .gpio import GPIOMock
from .i2c import I2CMock
from .spi import SPIMock
from .uart import UARTMock

__all__ = [
    'BaseMock',
    'MockException',
    'TimingEngine', 
    'VirtualClock',
    'GPIOMock',
    'I2CMock',
    'SPIMock',
    'UARTMock'
]

__version__ = '0.1.0'