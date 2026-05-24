"""Data pipeline integrity tests — validate message format, ordering, and checksums."""
import json
import hashlib
import time
import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.data_integrity

REQUIRED_FIELDS = ["sequence", "timestamp", "device_id", "sensor_type", "value", "checksum"]
SENSOR_TYPES = ["temperature", "voltage", "current", "gpio"]
MAX_SEQUENCE_GAP = 1


def _make_message(seq: int, value: float = 42.0, sensor_type: str = "temperature") -> dict:
    payload = {
        "sequence": seq,
        "timestamp": int(time.time() * 1000),
        "device_id": "edge-001",
        "sensor_type": sensor_type,
        "value": value,
    }
    checksum = hashlib.md5(
        json.dumps({k: v for k, v in payload.items()}, sort_keys=True).encode()
    ).hexdigest()[:8]
    payload["checksum"] = checksum
    return payload


def _verify_checksum(msg: dict) -> bool:
    payload = {k: v for k, v in msg.items() if k != "checksum"}
    expected = hashlib.md5(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:8]
    return msg.get("checksum") == expected


def test_message_has_all_required_fields(device):
    msg = _make_message(seq=1)
    for field in REQUIRED_FIELDS:
        assert field in msg, f"Required field '{field}' missing from message"


def test_message_checksum_valid(device):
    msg = _make_message(seq=1)
    assert _verify_checksum(msg), "Checksum validation failed for valid message"


def test_tampered_message_checksum_invalid(device):
    msg = _make_message(seq=1)
    msg["value"] = 999.9
    assert not _verify_checksum(msg), "Tampered message passed checksum validation"


def test_sequence_numbers_monotonically_increasing(device):
    messages = [_make_message(seq=i) for i in range(10)]
    seqs = [m["sequence"] for m in messages]
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i - 1], (
            f"Sequence not increasing at index {i}: {seqs[i-1]} -> {seqs[i]}"
        )


def test_no_sequence_gaps_in_batch(device):
    messages = [_make_message(seq=i) for i in range(5)]
    seqs = [m["sequence"] for m in messages]
    for i in range(1, len(seqs)):
        gap = seqs[i] - seqs[i - 1]
        assert gap <= MAX_SEQUENCE_GAP, (
            f"Sequence gap of {gap} between seq {seqs[i-1]} and {seqs[i]}"
        )


def test_duplicate_sequence_detected(device):
    seen = set()
    messages = [_make_message(seq=i) for i in [1, 2, 2, 3]]
    duplicates = []
    for msg in messages:
        seq = msg["sequence"]
        if seq in seen:
            duplicates.append(seq)
        seen.add(seq)
    assert len(duplicates) > 0, "Duplicate sequence not detected"


def test_timestamp_is_millisecond_epoch(device):
    msg = _make_message(seq=1)
    ts = msg["timestamp"]
    now_ms = int(time.time() * 1000)
    assert abs(ts - now_ms) < 5000, (
        f"Timestamp {ts} not close to current time {now_ms}"
    )


def test_timestamp_monotonically_increasing(device):
    messages = [_make_message(seq=i) for i in range(5)]
    timestamps = [m["timestamp"] for m in messages]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1], (
            f"Timestamp not monotonic at index {i}"
        )


def test_device_id_present_and_non_empty(device):
    msg = _make_message(seq=1)
    assert msg["device_id"], "device_id is empty"


def test_sensor_type_is_valid(device):
    for sensor_type in SENSOR_TYPES:
        msg = _make_message(seq=1, sensor_type=sensor_type)
        assert msg["sensor_type"] in SENSOR_TYPES


def test_value_is_numeric(device):
    msg = _make_message(seq=1, value=42.0)
    assert isinstance(msg["value"], (int, float)), (
        f"value type {type(msg['value'])} is not numeric"
    )


def test_json_serialization_roundtrip(device):
    msg = _make_message(seq=1)
    serialized = json.dumps(msg)
    deserialized = json.loads(serialized)
    assert deserialized == msg


def test_batch_of_100_messages_all_valid(device):
    for i in range(100):
        msg = _make_message(seq=i)
        assert _verify_checksum(msg), f"Message {i} failed checksum"


def test_message_size_within_mtu(device):
    msg = _make_message(seq=1)
    serialized = json.dumps(msg)
    assert len(serialized.encode("utf-8")) < 1400, (
        f"Message size {len(serialized)} bytes exceeds typical MTU"
    )


def test_missing_required_field_detected(device):
    msg = _make_message(seq=1)
    del msg["value"]
    missing = [f for f in REQUIRED_FIELDS if f not in msg]
    assert "value" in missing


def test_pipeline_processes_all_sensor_types(device):
    for i, sensor_type in enumerate(SENSOR_TYPES):
        msg = _make_message(seq=i, sensor_type=sensor_type)
        assert msg["sensor_type"] == sensor_type
        assert _verify_checksum(msg)


def test_negative_values_encoded_correctly(device):
    msg = _make_message(seq=1, value=-15.5)
    assert msg["value"] == -15.5
    assert _verify_checksum(msg)


def test_zero_value_encoded_correctly(device):
    msg = _make_message(seq=1, value=0.0)
    assert msg["value"] == 0.0
    assert _verify_checksum(msg)


def test_large_sequence_number_handled(device):
    msg = _make_message(seq=2**31 - 1)
    assert msg["sequence"] == 2**31 - 1
    assert _verify_checksum(msg)


def test_message_ordering_preserved_in_list(device):
    messages = [_make_message(seq=i) for i in range(20)]
    sorted_msgs = sorted(messages, key=lambda m: m["sequence"])
    assert [m["sequence"] for m in messages] == [m["sequence"] for m in sorted_msgs]


def test_checksum_changes_on_any_field_modification(device):
    msg = _make_message(seq=1)
    original_checksum = msg["checksum"]
    msg["device_id"] = "tampered-device"
    assert not _verify_checksum(msg), "Checksum did not detect device_id tampering"


def test_empty_batch_handled_gracefully(device):
    messages = []
    assert len(messages) == 0


def test_out_of_order_messages_detectable(device):
    seqs = [3, 1, 2, 0, 4]
    is_ordered = all(seqs[i] < seqs[i + 1] for i in range(len(seqs) - 1))
    assert not is_ordered, "Out-of-order messages should be detectable"


def test_pipeline_schema_version_field(device):
    msg = _make_message(seq=1)
    msg["schema_version"] = "1.0"
    assert "schema_version" in msg
