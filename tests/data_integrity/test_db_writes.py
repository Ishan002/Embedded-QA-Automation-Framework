"""Database write integrity tests using an in-memory SQLite stand-in."""
import sqlite3
import threading
import time
import pytest

pytestmark = pytest.mark.data_integrity

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value REAL NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    UNIQUE(device_id, sequence)
)
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(CREATE_TABLE)
    conn.commit()
    yield conn
    conn.close()


def _insert(conn, device_id, sensor_type, value, ts_ms, sequence):
    conn.execute(
        "INSERT INTO sensor_readings (device_id, sensor_type, value, timestamp_ms, sequence) "
        "VALUES (?, ?, ?, ?, ?)",
        (device_id, sensor_type, value, ts_ms, sequence),
    )
    conn.commit()


def test_write_and_read_roundtrip(db):
    _insert(db, "edge-001", "temperature", 42.0, 1700000000000, 1)
    row = db.execute(
        "SELECT device_id, value FROM sensor_readings WHERE sequence = 1"
    ).fetchone()
    assert row is not None
    assert row[0] == "edge-001"
    assert row[1] == 42.0


def test_row_count_after_bulk_insert(db):
    for i in range(50):
        _insert(db, "edge-001", "temperature", float(i), int(time.time() * 1000) + i, i + 1)
    count = db.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    assert count == 50


def test_unique_constraint_prevents_duplicate_sequence(db):
    _insert(db, "edge-001", "temperature", 42.0, 1700000000000, 1)
    with pytest.raises(sqlite3.IntegrityError):
        _insert(db, "edge-001", "temperature", 43.0, 1700000000001, 1)


def test_not_null_constraint_device_id(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO sensor_readings (device_id, sensor_type, value, timestamp_ms, sequence) "
            "VALUES (NULL, 'temperature', 1.0, 1000, 99)"
        )
        db.commit()


def test_not_null_constraint_value(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO sensor_readings (device_id, sensor_type, value, timestamp_ms, sequence) "
            "VALUES ('edge-001', 'temperature', NULL, 1000, 100)"
        )
        db.commit()


def test_transaction_rollback_on_error(db):
    try:
        with db:
            db.execute(
                "INSERT INTO sensor_readings (device_id, sensor_type, value, timestamp_ms, sequence) "
                "VALUES (?, ?, ?, ?, ?)",
                ("edge-001", "temperature", 1.0, 1000, 200),
            )
            raise ValueError("Simulated error mid-transaction")
    except ValueError:
        pass
    count = db.execute(
        "SELECT COUNT(*) FROM sensor_readings WHERE sequence = 200"
    ).fetchone()[0]
    assert count == 0, "Row persisted despite transaction rollback"


def test_timestamp_precision_milliseconds(db):
    ts_ms = 1700000000123
    _insert(db, "edge-001", "temperature", 42.0, ts_ms, 1)
    row = db.execute(
        "SELECT timestamp_ms FROM sensor_readings WHERE sequence = 1"
    ).fetchone()
    assert row[0] == ts_ms, f"Timestamp precision lost: expected {ts_ms}, got {row[0]}"


def test_negative_value_stored_correctly(db):
    _insert(db, "edge-001", "temperature", -15.5, 1700000000000, 1)
    row = db.execute(
        "SELECT value FROM sensor_readings WHERE sequence = 1"
    ).fetchone()
    assert row[0] == -15.5


def test_zero_value_stored_correctly(db):
    _insert(db, "edge-001", "gpio", 0.0, 1700000000000, 1)
    row = db.execute(
        "SELECT value FROM sensor_readings WHERE sequence = 1"
    ).fetchone()
    assert row[0] == 0.0


def test_autoincrement_id_increases(db):
    _insert(db, "edge-001", "temperature", 1.0, 1000, 1)
    _insert(db, "edge-001", "temperature", 2.0, 2000, 2)
    rows = db.execute("SELECT id FROM sensor_readings ORDER BY id").fetchall()
    ids = [r[0] for r in rows]
    assert ids == sorted(ids)
    assert ids[1] > ids[0]


def test_concurrent_writes_no_data_loss(db):
    """Simulate concurrent writers using a mutex-protected connection (mirrors production pattern)."""
    errors = []
    lock = threading.Lock()
    written = []

    def writer(start_seq):
        try:
            for i in range(10):
                seq = start_seq + i
                with lock:
                    db.execute(
                        "INSERT INTO sensor_readings (device_id, sensor_type, value, timestamp_ms, sequence) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (f"edge-{start_seq:03d}", "temperature", float(i), int(time.time() * 1000), seq),
                    )
                    db.commit()
                    written.append(seq)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors during concurrent writes: {errors}"
    count = db.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    assert count == 50, f"Expected 50 rows after concurrent writes, found {count}"


def test_ordered_retrieval_by_sequence(db):
    sequences = [5, 1, 3, 2, 4]
    for seq in sequences:
        _insert(db, "edge-001", "temperature", float(seq), seq * 1000, seq)
    rows = db.execute(
        "SELECT sequence FROM sensor_readings ORDER BY sequence ASC"
    ).fetchall()
    retrieved = [r[0] for r in rows]
    assert retrieved == sorted(retrieved)


def test_delete_old_records(db):
    for i in range(10):
        _insert(db, "edge-001", "temperature", float(i), i * 1000, i + 1)
    db.execute("DELETE FROM sensor_readings WHERE timestamp_ms < 5000")
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    assert count < 10, "Old records were not deleted"


def test_query_by_device_id(db):
    _insert(db, "edge-001", "temperature", 1.0, 1000, 1)
    _insert(db, "edge-002", "temperature", 2.0, 2000, 1)
    rows = db.execute(
        "SELECT * FROM sensor_readings WHERE device_id = 'edge-001'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "edge-001"


def test_float_precision_preserved(db):
    value = 3.14159265358979
    _insert(db, "edge-001", "voltage", value, 1000, 1)
    row = db.execute("SELECT value FROM sensor_readings").fetchone()
    assert abs(row[0] - value) < 1e-6
