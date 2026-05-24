import time
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class MockDeviceClient:
    """Simulates a Linux-based edge device for CI environments."""

    MOCK_RESPONSES = {
        "uname -r": ("5.15.0-embedded", "", 0),
        "uname -m": ("aarch64", "", 0),
        "cat /proc/uptime": ("127.43 119.02", "", 0),
        "cat /proc/version": (
            "Linux version 5.15.0-embedded (gcc version 11.3.0)",
            "", 0,
        ),
        "systemd-analyze | head -1": (
            "Startup finished in 2.341s (kernel) + 6.872s (userspace) = 9.213s.",
            "", 0,
        ),
        "cat /etc/os-release | grep PRETTY_NAME": (
            'PRETTY_NAME="Embedded Linux 3.2.1"', "", 0,
        ),
        "cat /sys/class/thermal/thermal_zone0/temp": ("42000", "", 0),
        "cat /sys/class/thermal/thermal_zone1/temp": ("38000", "", 0),
        "cat /sys/class/thermal/thermal_zone2/temp": ("45000", "", 0),
        "ls /sys/class/thermal/": (
            "thermal_zone0  thermal_zone1  thermal_zone2", "", 0,
        ),
        "cat /sys/class/thermal/thermal_zone0/type": ("cpu-thermal", "", 0),
        "cat /sys/class/thermal/thermal_zone1/type": ("gpu-thermal", "", 0),
        "cat /sys/class/thermal/thermal_zone2/type": ("board-thermal", "", 0),
        "ls /dev/watchdog*": ("/dev/watchdog\n/dev/watchdog0", "", 0),
        "cat /proc/sys/kernel/watchdog_thresh": ("60", "", 0),
        "cat /sys/class/watchdog/watchdog0/timeout": ("30", "", 0),
        "cat /sys/class/watchdog/watchdog0/timeleft": ("28", "", 0),
        "cat /sys/class/watchdog/watchdog0/identity": (
            "Hardware Watchdog Timer", "", 0,
        ),
        "ls /sys/class/gpio/": ("export  unexport  gpiochip0  gpiochip1", "", 0),
        "cat /sys/class/gpio/gpiochip0/ngpio": ("32", "", 0),
        "cat /sys/class/gpio/gpiochip0/base": ("0", "", 0),
        "ls /dev/iio*": ("/dev/iio:device0\n/dev/iio:device1", "", 0),
        "cat /sys/bus/iio/devices/iio:device0/name": ("adc128s052", "", 0),
        "cat /sys/bus/iio/devices/iio:device0/in_voltage_scale": ("0.805664", "", 0),
        "df -h /": ("Filesystem  Size  Used Avail Use% Mounted on\n/dev/mmcblk0p2  7.2G  2.1G  4.8G  31% /", "", 0),
        "free -m": ("              total  used  free\nMem:           512   187   325\nSwap:            0     0     0", "", 0),
        "date +%s": (str(int(time.time())), "", 0),
        "timedatectl status | grep 'System clock'": (
            "System clock synchronized: yes", "", 0,
        ),
        "cat /proc/net/if_inet6": ("", "", 0),
        "ip addr show eth0": (
            "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
            "    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0",
            "", 0,
        ),
    }

    SERVICES = {
        "sensor-daemon": "active",
        "data-collector": "active",
        "watchdog": "active",
        "edge-agent": "active",
        "ssh": "active",
        "syslog": "active",
        "networking": "active",
        "chrony": "active",
    }

    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def execute_command(self, cmd: str) -> CommandResult:
        start = time.monotonic()

        if cmd in self.MOCK_RESPONSES:
            stdout, stderr, exit_code = self.MOCK_RESPONSES[cmd]
        elif cmd.startswith("systemctl is-active "):
            svc = cmd.split("systemctl is-active ", 1)[1].strip()
            status = self.SERVICES.get(svc, "inactive")
            stdout, stderr, exit_code = status, "", (0 if status == "active" else 1)
        elif cmd.startswith("systemctl is-enabled "):
            svc = cmd.split("systemctl is-enabled ", 1)[1].strip()
            stdout, stderr, exit_code = "enabled", "", 0
        elif cmd.startswith("systemctl show "):
            stdout, stderr, exit_code = "WatchdogUSec=30000000\nWatchdogTimestamp=n/a", "", 0
        elif cmd.startswith("cat /sys/class/gpio/gpio"):
            if "direction" in cmd:
                stdout, stderr, exit_code = "out", "", 0
            elif "value" in cmd:
                stdout, stderr, exit_code = "0", "", 0
            elif "edge" in cmd:
                stdout, stderr, exit_code = "none", "", 0
            else:
                stdout, stderr, exit_code = "", "No such file", 1
        elif cmd.startswith("echo ") and "/sys/class/gpio/" in cmd:
            stdout, stderr, exit_code = "", "", 0
        elif cmd.startswith("gpioget"):
            stdout, stderr, exit_code = "0", "", 0
        elif cmd.startswith("gpioset"):
            stdout, stderr, exit_code = "", "", 0
        elif cmd.startswith("cat /sys/bus/iio/devices/iio:device0/in_voltage"):
            channel = 0
            import re
            m = re.search(r"in_voltage(\d+)_raw", cmd)
            if m:
                channel = int(m.group(1))
            stdout, stderr, exit_code = str(2048 + channel * 10), "", 0
        elif "dmesg" in cmd:
            stdout, stderr, exit_code = (
                "[    0.000000] Booting Linux on physical CPU 0x0\n"
                "[    0.000001] Linux version 5.15.0-embedded\n"
                "[    0.512000] sensor-daemon: initialized\n"
                "[    0.623000] data-collector: started",
                "", 0,
            )
        elif cmd.startswith("python3 -c") and "pipeline" in cmd:
            stdout, stderr, exit_code = "OK", "", 0
        else:
            stdout, stderr, exit_code = "", f"mock: unhandled command: {cmd}", 0

        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(stdout=stdout, stderr=stderr, exit_code=exit_code, duration_ms=duration_ms)

    def read_file(self, path: str) -> str:
        result = self.execute_command(f"cat {path}")
        if result.exit_code != 0:
            raise FileNotFoundError(f"Remote file not found: {path}")
        return result.stdout

    def write_file(self, path: str, content: str) -> None:
        pass

    def reboot(self) -> None:
        pass

    def wait_for_boot(self, timeout: int = 60) -> None:
        time.sleep(0.05)


class DeviceClient:
    """SSH-based client for real hardware."""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._client = None

    def connect(self):
        import paramiko
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            self.host, port=self.port,
            username=self.username, password=self.password,
            timeout=10,
        )

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None

    def execute_command(self, cmd: str) -> CommandResult:
        if not self._client:
            raise RuntimeError("Not connected")
        start = time.monotonic()
        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=30)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(stdout=out, stderr=err, exit_code=exit_code, duration_ms=duration_ms)

    def read_file(self, path: str) -> str:
        return self.execute_command(f"cat {path}").stdout

    def write_file(self, path: str, content: str) -> None:
        import paramiko
        sftp = self._client.open_sftp()
        with sftp.file(path, "w") as f:
            f.write(content)
        sftp.close()

    def reboot(self) -> None:
        try:
            self.execute_command("reboot")
        except Exception:
            pass
        self.disconnect()

    def wait_for_boot(self, timeout: int = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.connect()
                result = self.execute_command("echo ready")
                if result.exit_code == 0:
                    return
            except Exception:
                time.sleep(2)
        raise TimeoutError(f"Device did not boot within {timeout}s")


def get_device_client():
    from framework.config import load_config
    cfg = load_config()
    if cfg.mock_device or os.getenv("MOCK_DEVICE", "false").lower() == "true":
        client = MockDeviceClient()
    else:
        client = DeviceClient(
            cfg.device.host, cfg.device.port,
            cfg.device.username, cfg.device.password,
        )
    client.connect()
    return client
