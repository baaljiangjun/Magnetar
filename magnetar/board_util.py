"""Hi3516CV610 board access over SSH/SCP.

The module deliberately does not install a daemon or scan the LAN. A board must
be explicitly configured as BOARD/MAGNETAR_BOARD (for example root@192.168.1.10).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path


def _ssh_base(board: dict) -> list[str]:
    base: list[str] = []
    password = board.get("password", "")
    if password:
        if not shutil.which("sshpass"):
            raise RuntimeError("使用密码登录需要 sshpass；建议改用 SSH key")
        base += ["sshpass", "-p", password]
    return base + ["ssh", "-o", "StrictHostKeyChecking=accept-new",
                   "-o", "ConnectTimeout=10", "-p", str(board.get("port", 22)),
                   f"{board.get('user', 'root')}@{board['host']}"]


def _scp_base(board: dict) -> list[str]:
    base: list[str] = []
    password = board.get("password", "")
    if password:
        if not shutil.which("sshpass"):
            raise RuntimeError("使用密码登录需要 sshpass；建议改用 SSH key")
        base += ["sshpass", "-p", password]
    return base + ["scp", "-o", "StrictHostKeyChecking=accept-new",
                   "-P", str(board.get("port", 22))]


def ssh(board: dict, cmd: str, timeout: int = 120, max_tail: int | None = None) -> str:
    proc = subprocess.run(_ssh_base(board) + [cmd], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout)
    output = proc.stdout
    if proc.returncode:
        raise RuntimeError(f"CV610 remote command failed ({proc.returncode}):\n{output[-4000:]}")
    return "\n".join(output.splitlines()[-max_tail:]) if max_tail else output


def scp_to(board: dict, src: str | Path, dst: str) -> None:
    args = _scp_base(board)
    if Path(src).is_dir():
        args.append("-r")
    args += [str(src), f"{board.get('user', 'root')}@{board['host']}:{dst}"]
    subprocess.run(args, check=True, timeout=600)


def scp_from(board: dict, src: str, dst: str | Path) -> None:
    args = _scp_base(board) + ["-r", f"{board.get('user', 'root')}@{board['host']}:{src}", str(dst)]
    subprocess.run(args, check=True, timeout=600)


def select_board(target_hw: str = "Hi3516CV610", pwd: str = "",
                 spec: str | None = None) -> dict | None:
    spec = spec or os.environ.get("MAGNETAR_BOARD") or os.environ.get("BOARD")
    if not spec:
        return None
    parsed = urllib.parse.urlparse(spec if "://" in spec else f"ssh://{spec}")
    if not parsed.hostname:
        raise ValueError(f"无效 BOARD: {spec}")
    board = {"user": parsed.username or os.environ.get("BOARD_USER", "root"),
             "host": parsed.hostname, "port": parsed.port or int(os.environ.get("BOARD_PORT", "22")),
             "password": pwd}
    probe = ssh(board,
                "cat /proc/device-tree/compatible 2>/dev/null || "
                "cat /proc/cpuinfo 2>/dev/null || uname -a", timeout=20).strip("\x00\n ")
    normalized = probe.lower().replace("hi", "")
    if "3516cv610" not in normalized and "cv610" not in normalized:
        raise RuntimeError(f"目标板未识别为 Hi3516CV610: {probe[:300]}")
    board["chip_type"] = "Hi3516CV610"
    return board


def serial_command(port: str, baud: int, command: str, timeout: float = 15.0) -> str:
    """Run one shell command through an explicitly selected serial port."""
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("NFS+串口模式需要安装 pyserial") from exc
    begin, end = "__MAGNETAR_BEGIN__", "__MAGNETAR_END__"
    wrapped = f"echo {begin}; {command}; rc=$?; echo {end}:$rc\r\n"
    chunks: list[bytes] = []
    deadline = time.monotonic() + timeout
    with serial.Serial(port, baudrate=baud, timeout=0.25, write_timeout=2) as device:
        device.write(b"\r\n")
        time.sleep(0.2)
        device.write(wrapped.encode("utf-8"))
        while time.monotonic() < deadline:
            data = device.read(device.in_waiting or 1)
            if data:
                chunks.append(data)
                if end.encode() in b"".join(chunks):
                    break
    output = b"".join(chunks).decode("utf-8", errors="replace")
    match = re.search(rf"{end}:(\d+)", output)
    if not match:
        raise RuntimeError(f"串口命令超时或输出不完整:\n{output[-2000:]}")
    if int(match.group(1)) != 0:
        raise RuntimeError(f"板端命令失败 ({match.group(1)}):\n{output[-4000:]}")
    return output


def serial_ipv4(port: str, baud: int) -> tuple[str, int]:
    output = serial_command(port, baud, "ip -4 addr show eth0 2>/dev/null || ifconfig eth0")
    match = re.search(r"inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?", output)
    if not match:
        raise RuntimeError("未能从显式串口读取 eth0 IPv4 地址")
    return match.group(1), int(match.group(2) or 24)


def port_open(host: str, port: int = 22, timeout: float = 2.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
