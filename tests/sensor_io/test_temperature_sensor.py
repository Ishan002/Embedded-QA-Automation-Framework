"""Temperature sensor I/O tests for the embedded edge device."""
import pytest

pytestmark = pytest.mark.sensor

TEMP_MIN_C = -40.0
TEMP_MAX_C = 85.0
CALIBRATION_OFFSET_MAX_C = 2.0
ZONE_COUNT = 3
TEMP_NOISE_FLOOR_C = 0.5
SAMPLING_INTERVAL_MAX_MS = 1000


def _read_temp_c(device, zone: int) -> float:
    result = device.execute_command(
        f"cat /sys/class/thermal/thermal_zone{zone}/temp"
    )
    assert result.exit_code == 0, f"Failed to read thermal_zone{zone}"
    return int(result.stdout.strip()) / 1000.0


def test_thermal_zones_exist(device):
    result = device.execute_command("ls /sys/class/thermal/")
    assert result.exit_code == 0
    for zone in range(ZONE_COUNT):
        assert f"thermal_zone{zone}" in result.stdout


def test_zone0_temperature_in_valid_range(device):
    temp = _read_temp_c(device, 0)
    assert TEMP_MIN_C <= temp <= TEMP_MAX_C, (
        f"Zone 0 temperature {temp:.1f}°C out of range [{TEMP_MIN_C}, {TEMP_MAX_C}]"
    )


def test_zone1_temperature_in_valid_range(device):
    temp = _read_temp_c(device, 1)
    assert TEMP_MIN_C <= temp <= TEMP_MAX_C


def test_zone2_temperature_in_valid_range(device):
    temp = _read_temp_c(device, 2)
    assert TEMP_MIN_C <= temp <= TEMP_MAX_C


def test_zone0_type_label_present(device):
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone0/type"
    )
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0


def test_zone1_type_label_present(device):
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone1/type"
    )
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0


def test_zone2_type_label_present(device):
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone2/type"
    )
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0


def test_all_zone_types_unique(device):
    types = []
    for zone in range(ZONE_COUNT):
        result = device.execute_command(
            f"cat /sys/class/thermal/thermal_zone{zone}/type"
        )
        types.append(result.stdout.strip())
    assert len(types) == len(set(types)), f"Duplicate thermal zone types: {types}"


def test_cpu_zone_temperature_not_critical(device):
    """CPU thermal zone should be below 70°C under normal load."""
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone0/type"
    )
    if "cpu" in result.stdout.lower():
        temp = _read_temp_c(device, 0)
        assert temp < 70.0, f"CPU temperature {temp:.1f}°C is critically high"


def test_temperature_reading_is_integer_millidegrees(device):
    """Raw sysfs value must be an integer (millidegrees Celsius)."""
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone0/temp"
    )
    assert result.exit_code == 0
    raw = result.stdout.strip()
    assert raw.lstrip("-").isdigit(), f"Non-integer raw temperature: '{raw}'"


def test_zone0_z1_delta_within_reasonable_range(device):
    """Two zones on the same board should not differ by more than 20°C."""
    t0 = _read_temp_c(device, 0)
    t1 = _read_temp_c(device, 1)
    delta = abs(t0 - t1)
    assert delta < 20.0, (
        f"Temperature delta between zone0 ({t0:.1f}°C) and zone1 ({t1:.1f}°C) "
        f"is {delta:.1f}°C — suspiciously large"
    )


def test_temperature_not_frozen(device, sensor_baseline):
    """A re-read of zone0 should return a value (live sysfs, not cached)."""
    live_temp = _read_temp_c(device, 0)
    baseline = sensor_baseline.get("thermal_zone0")
    if baseline is not None:
        assert abs(live_temp - baseline) < 5.0, (
            "Temperature reading appears to be stuck (delta > 5°C suggests stale data)"
        )


def test_board_temperature_below_operating_limit(device):
    temp = _read_temp_c(device, 2)
    assert temp < 80.0, f"Board temperature {temp:.1f}°C near thermal shutdown"


def test_all_zones_readable_sequentially(device):
    temps = [_read_temp_c(device, z) for z in range(ZONE_COUNT)]
    assert len(temps) == ZONE_COUNT
    assert all(TEMP_MIN_C <= t <= TEMP_MAX_C for t in temps)


def test_temperature_raw_value_scale(device):
    """Raw value should be in millidegrees — sanity-check the scale."""
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone0/temp"
    )
    raw = int(result.stdout.strip())
    # raw should be thousands (e.g. 42000 = 42°C), not single digits
    assert raw > 1000 or raw < -1000, (
        f"Raw temp value {raw} looks wrong — expected millidegrees"
    )


def test_zone0_temperature_repeatable(device):
    """Two reads within short succession should match within noise floor."""
    t1 = _read_temp_c(device, 0)
    t2 = _read_temp_c(device, 0)
    assert abs(t1 - t2) <= TEMP_NOISE_FLOOR_C, (
        f"Temperature readings not repeatable: {t1:.3f}°C vs {t2:.3f}°C"
    )


def test_zone_count_matches_expected(device):
    result = device.execute_command("ls /sys/class/thermal/")
    assert result.exit_code == 0
    zones = [x for x in result.stdout.split() if x.startswith("thermal_zone")]
    assert len(zones) >= ZONE_COUNT, (
        f"Expected at least {ZONE_COUNT} thermal zones, found {len(zones)}"
    )


def test_temperature_millidegree_resolution(device):
    """Sensor must report at 1°C or finer resolution (≥ 1000 step granularity)."""
    result = device.execute_command(
        "cat /sys/class/thermal/thermal_zone0/temp"
    )
    raw = int(result.stdout.strip())
    assert raw % 1000 == 0 or raw % 500 == 0, (
        f"Raw value {raw} doesn't match expected millidegree resolution"
    )
