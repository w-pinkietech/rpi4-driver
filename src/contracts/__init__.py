"""Contract-based interface specifications for RPi4 drivers.

This package contains formal contracts that define the behavior of hardware interfaces.
All implementations (mock or real) must satisfy these contracts.
"""

from .gpio_contract import GPIOContract
from .i2c_contract import I2CContract
from .spi_contract import SPIContract
from .uart_contract import UARTContract

__all__ = ['GPIOContract', 'I2CContract', 'SPIContract', 'UARTContract']
