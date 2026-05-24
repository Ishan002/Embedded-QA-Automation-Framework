"""GPIO pin validation tests."""
import pytest

pytestmark = pytest.mark.sensor

GPIO_CHIP = "gpiochip0"
TEST_OUTPUT_PIN = 17
TEST_INPUT_PIN = 18
EXPECTED_NGPIO = 32


def test_gpio_chip_exists(device):
    result = device.execute_command("ls /sys/class/gpio/")
    assert result.exit_code == 0
    assert GPIO_CHIP in result.stdout


def test_gpio_chip_ngpio(device):
    result = device.execute_command(f"cat /sys/class/gpio/{GPIO_CHIP}/ngpio")
    assert result.exit_code == 0
    ngpio = int(result.stdout.strip())
    assert ngpio == EXPECTED_NGPIO, (
        f"Expected {EXPECTED_NGPIO} GPIO lines, found {ngpio}"
    )


def test_gpio_chip_base(device):
    result = device.execute_command(f"cat /sys/class/gpio/{GPIO_CHIP}/base")
    assert result.exit_code == 0
    base = int(result.stdout.strip())
    assert base >= 0


def test_gpio_export_pin(device):
    result = device.execute_command(
        f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export"
    )
    assert result.exit_code == 0


def test_gpio_set_output_direction(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    result = device.execute_command(
        f"echo out > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    assert result.exit_code == 0


def test_gpio_read_output_direction(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo out > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    result = device.execute_command(
        f"cat /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "out"


def test_gpio_write_high(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo out > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    result = device.execute_command(
        f"echo 1 > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/value"
    )
    assert result.exit_code == 0


def test_gpio_write_low(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo out > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    result = device.execute_command(
        f"echo 0 > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/value"
    )
    assert result.exit_code == 0


def test_gpio_read_value_after_write_high(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo out > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/direction"
    )
    device.execute_command(
        f"echo 1 > /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/value"
    )
    result = device.execute_command(
        f"cat /sys/class/gpio/gpio{TEST_OUTPUT_PIN}/value"
    )
    assert result.exit_code == 0
    assert result.stdout.strip() in ("0", "1")


def test_gpio_unexport_pin(device):
    device.execute_command(f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/export")
    result = device.execute_command(
        f"echo {TEST_OUTPUT_PIN} > /sys/class/gpio/unexport"
    )
    assert result.exit_code == 0


def test_gpio_set_input_direction(device):
    device.execute_command(f"echo {TEST_INPUT_PIN} > /sys/class/gpio/export")
    result = device.execute_command(
        f"echo in > /sys/class/gpio/gpio{TEST_INPUT_PIN}/direction"
    )
    assert result.exit_code == 0


def test_gpio_edge_configuration_none(device):
    device.execute_command(f"echo {TEST_INPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo in > /sys/class/gpio/gpio{TEST_INPUT_PIN}/direction"
    )
    result = device.execute_command(
        f"cat /sys/class/gpio/gpio{TEST_INPUT_PIN}/edge"
    )
    assert result.exit_code == 0
    assert result.stdout.strip() in ("none", "rising", "falling", "both")


def test_gpio_set_rising_edge(device):
    device.execute_command(f"echo {TEST_INPUT_PIN} > /sys/class/gpio/export")
    device.execute_command(
        f"echo in > /sys/class/gpio/gpio{TEST_INPUT_PIN}/direction"
    )
    result = device.execute_command(
        f"echo rising > /sys/class/gpio/gpio{TEST_INPUT_PIN}/edge"
    )
    assert result.exit_code == 0


def test_gpioget_tool_available(device):
    result = device.execute_command(f"gpioget {GPIO_CHIP} {TEST_INPUT_PIN}")
    assert result.exit_code == 0
    assert result.stdout.strip() in ("0", "1")


def test_gpioset_tool_available(device):
    result = device.execute_command(
        f"gpioset {GPIO_CHIP} {TEST_OUTPUT_PIN}=0"
    )
    assert result.exit_code == 0


def test_multiple_gpio_lines_readable(device):
    for pin in range(4):
        result = device.execute_command(f"gpioget {GPIO_CHIP} {pin}")
        assert result.exit_code == 0, f"Failed to read GPIO pin {pin}"
        assert result.stdout.strip() in ("0", "1")


def test_gpio_value_is_binary(device):
    result = device.execute_command(f"gpioget {GPIO_CHIP} {TEST_INPUT_PIN}")
    assert result.exit_code == 0
    val = result.stdout.strip()
    assert val in ("0", "1"), f"GPIO value '{val}' is not binary"


def test_iio_devices_present(device):
    result = device.execute_command("ls /dev/iio*")
    assert result.exit_code == 0
    assert "/dev/iio" in result.stdout
