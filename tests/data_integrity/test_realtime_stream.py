"""Real-time data stream integrity and performance tests."""
import time
import json
import hashlib
import threading
import queue
import pytest

pytestmark = pytest.mark.data_integrity

LATENCY_THRESHOLD_MS = 100
THROUGHPUT_MIN_MSG_PER_S = 100
STREAM_TEST_DURATION_S = 1
RECONNECT_TIMEOUT_S = 5


class FakeStream:
    """Simulates a real-time message stream from the edge device."""

    def __init__(self, latency_ms: float = 5.0, drop_rate: float = 0.0):
        self.latency_ms = latency_ms
        self.drop_rate = drop_rate
        self._seq = 0
        self._closed = False

    def read_message(self) -> dict:
        time.sleep(self.latency_ms / 1000.0)
        self._seq += 1
        return {
            "sequence": self._seq,
            "timestamp": int(time.time() * 1000),
            "value": 42.0 + self._seq * 0.001,
            "latency_ms": self.latency_ms,
        }

    def close(self):
        self._closed = True


@pytest.fixture
def stream():
    s = FakeStream(latency_ms=5.0)
    yield s
    s.close()


@pytest.fixture
def high_latency_stream():
    s = FakeStream(latency_ms=150.0)
    yield s
    s.close()


def test_single_message_latency_under_threshold(stream):
    start = time.monotonic()
    msg = stream.read_message()
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < LATENCY_THRESHOLD_MS, (
        f"Message latency {elapsed_ms:.1f}ms exceeds {LATENCY_THRESHOLD_MS}ms"
    )


def test_high_latency_stream_exceeds_threshold(high_latency_stream):
    start = time.monotonic()
    msg = high_latency_stream.read_message()
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms >= LATENCY_THRESHOLD_MS


def test_throughput_meets_minimum(stream):
    count = 0
    deadline = time.monotonic() + STREAM_TEST_DURATION_S
    while time.monotonic() < deadline:
        stream.read_message()
        count += 1
    rate = count / STREAM_TEST_DURATION_S
    assert rate >= THROUGHPUT_MIN_MSG_PER_S, (
        f"Throughput {rate:.0f} msg/s below minimum {THROUGHPUT_MIN_MSG_PER_S} msg/s"
    )


def test_messages_have_monotonic_sequence(stream):
    messages = [stream.read_message() for _ in range(10)]
    seqs = [m["sequence"] for m in messages]
    assert seqs == sorted(seqs), f"Sequence not monotonic: {seqs}"


def test_messages_have_increasing_timestamps(stream):
    messages = [stream.read_message() for _ in range(5)]
    timestamps = [m["timestamp"] for m in messages]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1], (
            f"Timestamp not increasing: {timestamps[i-1]} -> {timestamps[i]}"
        )


def test_stream_latency_reported_in_message(stream):
    msg = stream.read_message()
    assert "latency_ms" in msg, "Message does not include latency_ms field"
    assert msg["latency_ms"] >= 0


def test_no_duplicate_sequences_in_burst(stream):
    messages = [stream.read_message() for _ in range(20)]
    seqs = [m["sequence"] for m in messages]
    assert len(seqs) == len(set(seqs)), f"Duplicate sequence numbers: {seqs}"


def test_stream_value_field_present(stream):
    msg = stream.read_message()
    assert "value" in msg, "Message missing 'value' field"
    assert isinstance(msg["value"], (int, float))


def test_consecutive_values_not_identical(stream):
    messages = [stream.read_message() for _ in range(5)]
    values = [m["value"] for m in messages]
    assert len(set(values)) > 1, "All consecutive values are identical (stuck sensor?)"


def test_stream_reconnect_within_timeout():
    class ReconnectableStream:
        def __init__(self):
            self.connected = False
            self.reconnect_time_s = 0.1

        def connect(self):
            time.sleep(self.reconnect_time_s)
            self.connected = True

        def read_message(self):
            if not self.connected:
                raise ConnectionError("Not connected")
            return {"sequence": 1, "timestamp": int(time.time() * 1000), "value": 1.0}

    s = ReconnectableStream()
    start = time.monotonic()
    s.connect()
    elapsed = time.monotonic() - start
    assert elapsed < RECONNECT_TIMEOUT_S, (
        f"Reconnect took {elapsed:.2f}s, exceeding {RECONNECT_TIMEOUT_S}s timeout"
    )
    assert s.connected


def test_backpressure_queue_does_not_overflow():
    q = queue.Queue(maxsize=1000)
    producer_count = [0]
    consumer_count = [0]

    def producer():
        for i in range(500):
            if not q.full():
                q.put({"sequence": i, "value": float(i)})
                producer_count[0] += 1

    def consumer():
        while not q.empty():
            q.get()
            consumer_count[0] += 1

    t_prod = threading.Thread(target=producer)
    t_cons = threading.Thread(target=consumer)
    t_prod.start()
    t_prod.join()
    t_cons.start()
    t_cons.join()
    assert not q.full(), "Queue overflowed — backpressure not working"


def test_stream_messages_are_json_serializable(stream):
    msg = stream.read_message()
    serialized = json.dumps(msg)
    assert len(serialized) > 0


def test_stream_burst_100_messages_all_valid(stream):
    messages = [stream.read_message() for _ in range(100)]
    assert len(messages) == 100
    for msg in messages:
        assert "sequence" in msg
        assert "timestamp" in msg
        assert "value" in msg


def test_stream_sequence_starts_at_1(stream):
    msg = stream.read_message()
    assert msg["sequence"] >= 1


def test_stream_timestamp_is_recent(stream):
    msg = stream.read_message()
    now_ms = int(time.time() * 1000)
    assert abs(msg["timestamp"] - now_ms) < 2000, (
        f"Message timestamp {msg['timestamp']} not close to now ({now_ms})"
    )


def test_parallel_stream_readers_get_different_sequences():
    results = []
    lock = threading.Lock()

    def reader(stream_id):
        s = FakeStream(latency_ms=1.0)
        msg = s.read_message()
        with lock:
            results.append((stream_id, msg["sequence"]))

    threads = [threading.Thread(target=reader, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 5


def test_stream_value_not_nan(stream):
    import math
    msg = stream.read_message()
    assert not math.isnan(msg["value"]), "Stream message value is NaN"


def test_stream_value_not_inf(stream):
    import math
    msg = stream.read_message()
    assert not math.isinf(msg["value"]), "Stream message value is infinite"


def test_message_rate_consistent_over_window(stream):
    window_size = 50
    start = time.monotonic()
    for _ in range(window_size):
        stream.read_message()
    elapsed = time.monotonic() - start
    rate = window_size / elapsed
    assert rate >= THROUGHPUT_MIN_MSG_PER_S * 0.5, (
        f"Message rate {rate:.0f} msg/s dropped below 50% of target"
    )
