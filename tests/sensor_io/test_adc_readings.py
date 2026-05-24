"""ADC (Analog-to-Digital Converter) validation tests."""
import pytest

pytestmark = pytest.mark.sensor

ADC_DEVICE = "iio:device0"
ADC_BITS = 12
ADC_MAX_RAW = (1 << ADC_BITS) - 1  # 4095
ADC_CHANNELS = 8
VOLTAGE_SCALE = 0.805664  # mV per count for adc128s052
VREF_MV = 3300.0


def _read_adc_raw(device, channel: int) -> int:
    result = device.execute_command(
        f"cat /sys/bus/iio/devices/{ADC_DEVICE}/in_voltage{channel}_raw"
    )
    assert result.exit_code == 0, f"Failed to read ADC channel {channel}"
    return int(result.stdout.strip())


def test_adc_device_present(device):
    result = device.execute_command("ls /dev/iio*")
    assert result.exit_code == 0
    assert "/dev/iio" in result.stdout


def test_adc_device_name(device):
    result = device.execute_command(
        f"cat /sys/bus/iio/devices/{ADC_DEVICE}/name"
    )
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0


def test_adc_voltage_scale_present(device):
    result = device.execute_command(
        f"cat /sys/bus/iio/devices/{ADC_DEVICE}/in_voltage_scale"
    )
    assert result.exit_code == 0
    scale = float(result.stdout.strip())
    assert scale > 0


def test_adc_voltage_scale_matches_expected(device):
    result = device.execute_command(
        f"cat /sys/bus/iio/devices/{ADC_DEVICE}/in_voltage_scale"
    )
    scale = float(result.stdout.strip())
    assert abs(scale - VOLTAGE_SCALE) < 0.01, (
        f"ADC scale {scale} != expected {VOLTAGE_SCALE}"
    )


def test_adc_channel0_raw_in_range(device):
    raw = _read_adc_raw(device, 0)
    assert 0 <= raw <= ADC_MAX_RAW, (
        f"ADC channel 0 raw value {raw} out of {ADC_BITS}-bit range [0, {ADC_MAX_RAW}]"
    )


def test_adc_all_channels_readable(device):
    for ch in range(ADC_CHANNELS):
        raw = _read_adc_raw(device, ch)
        assert 0 <= raw <= ADC_MAX_RAW, (
            f"Channel {ch} raw value {raw} out of range"
        )


def test_adc_channel_isolation(device):
    """Adjacent channels should not read identical values (cross-talk check)."""
    readings = [_read_adc_raw(device, ch) for ch in range(ADC_CHANNELS)]
    unique = set(readings)
    assert len(unique) > 1, (
        "All ADC channels returned identical values — possible multiplexer fault"
    )


def test_adc_voltage_calculation_in_range(device):
    raw = _read_adc_raw(device, 0)
    voltage_mv = raw * VOLTAGE_SCALE
    assert 0 <= voltage_mv <= VREF_MV, (
        f"Calculated voltage {voltage_mv:.1f}mV out of Vref range [0, {VREF_MV}]mV"
    )


def test_adc_raw_value_is_integer(device):
    result = device.execute_command(
        f"cat /sys/bus/iio/devices/{ADC_DEVICE}/in_voltage0_raw"
    )
    raw_str = result.stdout.strip()
    assert raw_str.isdigit(), f"ADC raw value '{raw_str}' is not an integer"


def test_adc_not_stuck_at_max(device):
    """A channel stuck at max (4095) would indicate a broken input."""
    raw = _read_adc_raw(device, 0)
    assert raw < ADC_MAX_RAW, (
        f"ADC channel 0 is stuck at maximum value {ADC_MAX_RAW}"
    )


def test_adc_not_stuck_at_zero(device):
    """All channels reading 0 indicates possible power or wiring fault."""
    readings = [_read_adc_raw(device, ch) for ch in range(4)]
    assert not all(r == 0 for r in readings), (
        "First 4 ADC channels all read 0 — possible power fault"
    )


def test_adc_resolution_12_bit(device):
    """Verify max raw value fits 12-bit range."""
    assert ADC_MAX_RAW == 4095
    raw = _read_adc_raw(device, 0)
    assert raw.bit_length() <= ADC_BITS, (
        f"Raw value {raw} exceeds {ADC_BITS}-bit resolution"
    )


def test_adc_channel4_raw_in_range(device):
    raw = _read_adc_raw(device, 4)
    assert 0 <= raw <= ADC_MAX_RAW


def test_adc_repeated_reads_stable(device):
    """Two consecutive reads of the same channel should be close."""
    r1 = _read_adc_raw(device, 0)
    r2 = _read_adc_raw(device, 0)
    assert abs(r1 - r2) <= 10, (
        f"ADC channel 0 unstable: {r1} vs {r2} (delta {abs(r1-r2)} > 10 LSB)"
    )


def test_adc_midscale_channels_not_clipping(device):
    for ch in range(ADC_CHANNELS):
        raw = _read_adc_raw(device, ch)
        assert raw < ADC_MAX_RAW, f"Channel {ch} is clipping at max value"
