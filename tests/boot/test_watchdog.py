"""Watchdog timer validation tests."""
import pytest

pytestmark = pytest.mark.boot

WATCHDOG_TIMEOUT_S = 30
WATCHDOG_KICK_MAX_INTERVAL_S = 25


def test_watchdog_device_exists(device):
    result = device.execute_command("ls /dev/watchdog*")
    assert result.exit_code == 0
    assert "/dev/watchdog" in result.stdout


def test_watchdog_service_active(device):
    result = device.execute_command("systemctl is-active watchdog")
    assert result.stdout.strip() == "active"


def test_watchdog_service_enabled(device):
    result = device.execute_command("systemctl is-enabled watchdog")
    assert result.stdout.strip() in ("enabled", "static")


def test_watchdog_hardware_identity(device):
    result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/identity"
    )
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0, "Watchdog identity string is empty"


def test_watchdog_timeout_configured(device):
    result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeout"
    )
    assert result.exit_code == 0
    timeout = int(result.stdout.strip())
    assert timeout == WATCHDOG_TIMEOUT_S, (
        f"Watchdog timeout {timeout}s != expected {WATCHDOG_TIMEOUT_S}s"
    )


def test_watchdog_timeleft_positive(device):
    result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeleft"
    )
    assert result.exit_code == 0
    timeleft = int(result.stdout.strip())
    assert timeleft > 0, "Watchdog timer has already expired"


def test_watchdog_timeleft_less_than_timeout(device):
    result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeleft"
    )
    timeout_result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeout"
    )
    timeleft = int(result.stdout.strip())
    timeout = int(timeout_result.stdout.strip())
    assert timeleft <= timeout, (
        f"timeleft ({timeleft}s) exceeds timeout ({timeout}s)"
    )


def test_watchdog_kernel_threshold_set(device):
    result = device.execute_command("cat /proc/sys/kernel/watchdog_thresh")
    assert result.exit_code == 0
    thresh = int(result.stdout.strip())
    assert thresh > 0, "Kernel watchdog threshold not set"


def test_watchdog0_symlink_exists(device):
    result = device.execute_command("ls /dev/watchdog*")
    assert result.exit_code == 0
    assert "/dev/watchdog0" in result.stdout


def test_watchdog_is_being_kicked(device):
    """timeleft should remain high, indicating the daemon is kicking."""
    result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeleft"
    )
    timeout_result = device.execute_command(
        "cat /sys/class/watchdog/watchdog0/timeout"
    )
    timeleft = int(result.stdout.strip())
    timeout = int(timeout_result.stdout.strip())
    min_expected = timeout - WATCHDOG_KICK_MAX_INTERVAL_S
    assert timeleft >= min_expected, (
        f"Watchdog timeleft {timeleft}s suggests daemon is not kicking "
        f"(expected >= {min_expected}s for {WATCHDOG_KICK_MAX_INTERVAL_S}s kick interval)"
    )
