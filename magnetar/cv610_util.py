"""Hi3516CV610 host toolchain helpers.

The CANN/ATC/MindCmd packages are proprietary and are therefore discovered
from PATH or explicit configuration instead of being downloaded by Magnetar.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path


def resolve_tool(name: str, configured: str | None = None) -> str:
    candidate = configured or os.environ.get(f"MAGNETAR_{name.upper()}_BIN") or name
    found = shutil.which(candidate)
    if found:
        return found
    path = Path(candidate).expanduser()
    if path.is_file():
        return str(path.resolve())
    raise RuntimeError(
        f"找不到 {name}: {candidate}。请先安装与 Hi3516CV610 SDK 匹配的 CANN/工具包，"
        f"source setenv.sh，或配置 {name.upper()}_BIN。"
    )


def run_command(args: list[str], *, cwd: str | Path | None = None,
                timeout: int = 1800, log_file: str | Path | None = None) -> str:
    proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode:
        tail = "\n".join(proc.stdout.splitlines()[-200:])
        raise RuntimeError(f"命令失败({proc.returncode}): {shlex.join(args)}\n{tail}")
    return proc.stdout


def tool_version(binary: str) -> str:
    for flag in (["--version"], ["-v"], ["version"]):
        try:
            return run_command([binary, *flag], timeout=30).strip()
        except Exception:
            continue
    return "available (version output unavailable)"


def cross_prefix(libc: str = "musl") -> str:
    return (
        "arm-v01c02-linux-gnueabi-" if libc == "glibc"
        else "arm-v01c02-linux-musleabi-"
    )
