"""Boot sequence validation tests for the embedded edge device."""
import re
import pytest

pytestmark = pytest.mark.boot

EXPECTED_KERNEL = "5.15.0-embedded"
EXPECTED_ARCH = "aarch64"
REQUIRED_SERVICES = ["sensor-daemon", "data-collector", "watchdog", "edge-agent"]
BOOT_TIME_THRESHOLD_S = 30.0
MIN_FREE_MEMORY_MB = 64
FILESYSTEM_USAGE_LIMIT_PCT = 80


def test_kernel_version_matches_expected(device):
    result = device.execute_command("uname -r")
    assert result.exit_code == 0
    assert EXPECTED_KERNEL in result.stdout, (
        f"Expected kernel {EXPECTED_KERNEL}, got {result.stdout.strip()}"
    )


def test_cpu_architecture_is_aarch64(device):
    result = device.execute_command("uname -m")
    assert result.exit_code == 0
    assert result.stdout.strip() == EXPECTED_ARCH


def test_os_release_present(device):
    result = device.execute_command("cat /etc/os-release | grep PRETTY_NAME")
    assert result.exit_code == 0
    assert "Embedded Linux" in result.stdout


def test_required_services_running(device):
    for svc in REQUIRED_SERVICES:
        result = device.execute_command(f"systemctl is-active {svc}")
        assert result.stdout.strip() == "active", f"Service '{svc}' is not active"


def test_required_services_enabled_at_boot(device):
    for svc in REQUIRED_SERVICES:
        result = device.execute_command(f"systemctl is-enabled {svc}")
        assert result.stdout.strip() in ("enabled", "static"), (
            f"Service '{svc}' is not enabled: {result.stdout.strip()}"
        )


def test_boot_time_under_threshold(device):
    result = device.execute_command("systemd-analyze | head -1")
    assert result.exit_code == 0
    # "Startup finished in 2.341s (kernel) + 6.872s (userspace) = 9.213s."
    m = re.search(r"=\s+([\d.]+)s\.", result.stdout)
    assert m, f"Could not parse boot time from: {result.stdout}"
    total_s = float(m.group(1))
    assert total_s < BOOT_TIME_THRESHOLD_S, (
        f"Boot time {total_s:.1f}s exceeds threshold {BOOT_TIME_THRESHOLD_S}s"
    )


def test_system_uptime_is_positive(device):
    result = device.execute_command("cat /proc/uptime")
    assert result.exit_code == 0
    uptime_s = float(result.stdout.split()[0])
    assert uptime_s > 0, "System uptime should be positive"


def test_sufficient_free_memory(device):
    result = device.execute_command("free -m")
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    mem_line = next(l for l in lines if l.startswith("Mem:"))
    parts = mem_line.split()
    free_mb = int(parts[3])
    assert free_mb >= MIN_FREE_MEMORY_MB, (
        f"Free memory {free_mb}MB below minimum {MIN_FREE_MEMORY_MB}MB"
    )


def test_root_filesystem_not_full(device):
    result = device.execute_command("df -h /")
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    data_line = lines[-1]
    m = re.search(r"(\d+)%", data_line)
    assert m, f"Could not parse disk usage from: {data_line}"
    usage_pct = int(m.group(1))
    assert usage_pct < FILESYSTEM_USAGE_LIMIT_PCT, (
        f"Root filesystem {usage_pct}% full (limit {FILESYSTEM_USAGE_LIMIT_PCT}%)"
    )


def test_system_clock_synchronized(device):
    result = device.execute_command("timedatectl status | grep 'System clock'")
    assert result.exit_code == 0
    assert "yes" in result.stdout, "System clock is not synchronized with NTP"


def test_network_interface_up(device):
    result = device.execute_command("ip addr show eth0")
    assert result.exit_code == 0
    assert "inet " in result.stdout, "eth0 has no IPv4 address"


def test_kernel_has_no_oops_in_dmesg(device):
    result = device.execute_command("dmesg")
    assert result.exit_code == 0
    oops_keywords = ["Oops:", "BUG:", "kernel panic", "WARN_ON"]
    for keyword in oops_keywords:
        assert keyword not in result.stdout, (
            f"Kernel issue found in dmesg: '{keyword}'"
        )


def test_sensor_daemon_starts_in_dmesg(device):
    result = device.execute_command("dmesg")
    assert result.exit_code == 0
    assert "sensor-daemon" in result.stdout


def test_data_collector_starts_in_dmesg(device):
    result = device.execute_command("dmesg")
    assert result.exit_code == 0
    assert "data-collector" in result.stdout


def test_proc_version_matches_kernel(device):
    result = device.execute_command("cat /proc/version")
    assert result.exit_code == 0
    assert EXPECTED_KERNEL in result.stdout


def test_boot_sequence_services_in_order(device):
    """sensor-daemon must start before data-collector."""
    result = device.execute_command("dmesg")
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    sensor_idx = next(
        (i for i, l in enumerate(lines) if "sensor-daemon" in l), None
    )
    collector_idx = next(
        (i for i, l in enumerate(lines) if "data-collector" in l), None
    )
    assert sensor_idx is not None, "sensor-daemon not found in dmesg"
    assert collector_idx is not None, "data-collector not found in dmesg"
    assert sensor_idx < collector_idx, (
        "data-collector started before sensor-daemon"
    )


def test_no_swap_usage(device):
    result = device.execute_command("free -m")
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    swap_line = next((l for l in lines if l.startswith("Swap:")), None)
    if swap_line:
        parts = swap_line.split()
        swap_used = int(parts[2])
        assert swap_used == 0, f"Swap is in use: {swap_used}MB"


def test_all_services_have_no_failures(device):
    for svc in REQUIRED_SERVICES:
        result = device.execute_command(f"systemctl show {svc}")
        assert result.exit_code == 0
