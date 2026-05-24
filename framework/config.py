import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeviceConfig:
    host: str = "192.168.1.100"
    port: int = 22
    username: str = "root"
    password: str = "embedded"
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200


@dataclass
class FrameworkConfig:
    device: DeviceConfig = field(default_factory=DeviceConfig)
    portal_url: str = ""
    portal_token: str = ""
    test_timeout: int = 30
    retry_count: int = 3
    mock_device: bool = False


def load_config() -> FrameworkConfig:
    device = DeviceConfig(
        host=os.getenv("DEVICE_HOST", "192.168.1.100"),
        port=int(os.getenv("DEVICE_PORT", "22")),
        username=os.getenv("DEVICE_USER", "root"),
        password=os.getenv("DEVICE_PASS", "embedded"),
        serial_port=os.getenv("DEVICE_SERIAL", "/dev/ttyUSB0"),
        baud_rate=int(os.getenv("DEVICE_BAUD", "115200")),
    )
    return FrameworkConfig(
        device=device,
        portal_url=os.getenv("PORTAL_URL", ""),
        portal_token=os.getenv("PORTAL_TOKEN", ""),
        test_timeout=int(os.getenv("TEST_TIMEOUT", "30")),
        retry_count=int(os.getenv("RETRY_COUNT", "3")),
        mock_device=os.getenv("MOCK_DEVICE", "false").lower() == "true",
    )
