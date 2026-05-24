import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework.fixtures import device, fresh_device, sensor_baseline, gpio_pin


def pytest_configure(config):
    config.addinivalue_line("markers", "boot: Boot sequence and system startup tests")
    config.addinivalue_line("markers", "sensor: Sensor I/O and hardware interface tests")
    config.addinivalue_line("markers", "data_integrity: Data pipeline and integrity tests")
    config.addinivalue_line("markers", "slow: Tests with long execution time (>5s)")
    config.addinivalue_line("markers", "hardware: Requires real hardware (skipped in mock mode)")
