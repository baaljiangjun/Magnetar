"""TOOLCHAIN: validate the Hi3516CV610 host and cross toolchains."""
from __future__ import annotations

import shutil

from magnetar.config import load_config
from magnetar.cv610_util import cross_prefix, resolve_tool, tool_version


def run() -> dict:
    cfg = load_config()
    atc = resolve_tool("atc", cfg.get("ATC_BIN"))
    mindcmd = resolve_tool("mindcmd", cfg.get("MINDCMD_BIN"))
    prefix = cfg.get("CROSS_COMPILE") or cross_prefix(cfg.get("LIBC", "musl"))
    gcc = shutil.which(f"{prefix}gcc")
    gxx = shutil.which(f"{prefix}g++")
    if not gcc or not gxx:
        raise RuntimeError(
            f"找不到 CV610 交叉编译器 {prefix}gcc/g++。"
            "请安装 SDK 配套 arm-v01c02-linux-musleabi 或 gnueabi 工具链。"
        )
    result = {
        "atc": atc,
        "atc_version": tool_version(atc),
        "mindcmd": mindcmd,
        "mindcmd_version": tool_version(mindcmd),
        "cross_compile": prefix,
        "cc": gcc,
        "cxx": gxx,
        "libc": cfg.get("LIBC", "musl"),
        "sdk_root": cfg.get("CV610_SDK_ROOT", ""),
    }
    print("[TOOLCHAIN] Hi3516CV610 toolchain ready")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return result
