import pytest
from framework.device_client import get_device_client


@pytest.fixture(scope="session")
def device():
    client = get_device_client()
    yield client
    client.disconnect()


@pytest.fixture
def fresh_device(device):
    """Fixture that ensures a clean device state before each test."""
    yield device


@pytest.fixture
def sensor_baseline(device):
    readings = {}
    for zone in range(3):
        result = device.execute_command(
            f"cat /sys/class/thermal/thermal_zone{zone}/temp"
        )
        if result.exit_code == 0:
            readings[f"thermal_zone{zone}"] = int(result.stdout.strip()) / 1000.0
    return readings


@pytest.fixture
def gpio_pin(device):
    pin = 17
    device.execute_command(f"echo {pin} > /sys/class/gpio/export")
    yield pin
    device.execute_command(f"echo {pin} > /sys/class/gpio/unexport")
