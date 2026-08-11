"""COMPILE: convert a static ONNX model to Hi3516CV610 OM with ATC."""
from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path

from magnetar.config import load_task_config
from magnetar.cv610_util import resolve_tool, run_command


def _shape_spec(meta: dict) -> str:
    specs = []
    for item in meta.get("inputs", []):
        shape = item.get("shape", [])
        if not shape or any(not isinstance(v, int) or v <= 0 for v in shape):
            raise ValueError(f"CV610 ATC 要求静态输入 Shape，当前为 {item.get('name')}: {shape}")
        specs.append(f"{item['name']}:{','.join(map(str, shape))}")
    if not specs:
        raise ValueError("model_meta.json 中没有输入信息")
    return ";".join(specs)


def build_atc_command(task_dir: Path, *, atc_bin: str = "atc",
                      custom_args: list[str] | None = None) -> list[str]:
    meta = json.loads((task_dir / "export" / "model_meta.json").read_text(encoding="utf-8"))
    cfg = load_task_config(task_dir)
    cmd = [
        atc_bin,
        "--mode=0",
        "--framework=5",
        f"--model={task_dir / 'export' / 'model.onnx'}",
        f"--output={task_dir / 'compile' / 'model'}",
        f"--input_shape={_shape_spec(meta)}",
        "--soc_version=Hi3516CV610",
        "--workbuf_optimize_enable=1",
    ]
    aipp = cfg.get("AIPP_CONFIG")
    if aipp:
        cmd.append(f"--insert_op_conf={Path(aipp).expanduser().resolve()}")
    quant = cfg.get("QUANT_PARAM_FILE")
    if quant:
        cmd.append(f"--quant_param_file={Path(quant).expanduser().resolve()}")
    extra = custom_args
    if extra is None and cfg.get("ATC_EXTRA_ARGS"):
        extra = shlex.split(cfg["ATC_EXTRA_ARGS"])
    cmd.extend(extra or [])
    return cmd


def run(task_dir: Path, target_hw: str = "Hi3516CV610", toolchain=None,
        custom_args: list[str] | None = None, **_ignored) -> Path:
    if target_hw.lower() not in {"hi3516cv610", "cv610"}:
        raise ValueError(f"此分支仅支持 Hi3516CV610，收到 {target_hw}")
    task_dir = Path(task_dir)
    out = task_dir / "compile"
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_task_config(task_dir)
    configured = toolchain.get("atc") if isinstance(toolchain, dict) else cfg.get("ATC_BIN")
    atc = resolve_tool("atc", configured)
    cmd = build_atc_command(task_dir, atc_bin=atc, custom_args=custom_args)
    (out / "atc_command.txt").write_text(shlex.join(cmd) + "\n", encoding="utf-8")
    run_command(cmd, timeout=3600, log_file=out / "compile.log")
    om = out / "model.om"
    if not om.is_file():
        summary = summarize_compile_log(task_dir)
        raise RuntimeError(f"ATC 未生成 {om}；错误摘要: {summary['errors'][:3]}")
    report = {
        "target": "Hi3516CV610",
        "model": str(om),
        "size_bytes": om.stat().st_size,
        "atc_command": shlex.join(cmd),
    }
    (out / "compile_report.md").write_text(
        "# CV610 ATC Compile Report\n\n" +
        "\n".join(f"- {k}: `{v}`" for k, v in report.items()) + "\n",
        encoding="utf-8",
    )
    from magnetar.stages.state import mark_stage
    mark_stage(task_dir, "COMPILE", artifacts={"om": str(om)},
               metrics={"om_size_kb": om.stat().st_size / 1024},
               summary=f"COMPILE OK om={om.stat().st_size / 1024:.1f} KB")
    return om


def summarize_compile_log(task_dir: Path) -> dict:
    log = Path(task_dir) / "compile" / "compile.log"
    result = {"size_bytes": None, "errors": [], "tail": ""}
    om = Path(task_dir) / "compile" / "model.om"
    if om.is_file():
        result["size_bytes"] = om.stat().st_size
    if not log.is_file():
        result["errors"] = ["compile.log 不存在"]
        return result
    text = log.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if re.search(r"error|failed|exception|fatal", line, re.I):
            result["errors"].append(line.strip()[:240])
            if len(result["errors"]) >= 8:
                break
    result["tail"] = text[-1500:]
    return result
