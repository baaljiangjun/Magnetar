"""SIMULATE: use MindCmd for float/OM functional, instruction and board comparison."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import numpy as np

from magnetar.config import load_task_config
from magnetar.cv610_util import resolve_tool, run_command


def cosine(a, b):
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    b = np.asarray(b, dtype=np.float32).reshape(-1)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def _write_switches(path: Path, *, board: bool, instruction: bool, dump: bool) -> None:
    path.write_text(
        "\n".join([
            f"IS_NPU_RUN={int(board)}",
            f"IS_FUNC_RUN={int(not board and not instruction)}",
            f"IS_INST_RUN={int(instruction)}",
            "IS_PERF_RUN=0",
            f"IS_DUMP_OPEN={int(dump)}",
            "IS_COMPARE_OPEN=1",
            f"IS_BOARD_PROFILING_OPEN={int(board)}",
            "IS_PROFILE_DISPLAY_OPEN=0",
            "IS_QUANT_ANALYSIS_OPEN=0",
            "IS_PRINT_PROCESS_DETAIL=0",
        ]) + "\n", encoding="utf-8")


def _find_reports(workspace: Path) -> tuple[list[Path], list[Path]]:
    cmp_files = sorted(workspace.glob("output/project_*/cmp/**/*"))
    cmp_files = [p for p in cmp_files if p.is_file()]
    dumps = sorted(workspace.glob("output/project_*/dump/**/*"))
    dumps = [p for p in dumps if p.is_file()]
    return cmp_files, dumps


def _parse_metrics(files: list[Path]) -> dict:
    metrics: dict[str, float | str] = {}
    pattern = re.compile(r"(cos(?:ine)?(?:_similarity)?|mae|max_abs(?:_diff)?)\s*[:=]\s*([-+0-9.eE]+)", re.I)
    for path in files:
        if path.suffix.lower() not in {".txt", ".csv", ".json", ".log"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for key, value in pattern.findall(text):
            try:
                metrics[key.lower()] = float(value)
            except ValueError:
                pass
    return metrics


def run(task_dir: Path, sample: np.ndarray | None = None, toolchain=None,
        *, image_list: str | Path | None = None, aipp: str | Path | None = None,
        board: dict | None = None, instruction: bool = False,
        dump: bool = True, **_ignored) -> dict:
    task_dir = Path(task_dir)
    cfg = load_task_config(task_dir)
    sim = task_dir / "simulate"
    sim.mkdir(parents=True, exist_ok=True)
    configured = toolchain.get("mindcmd") if isinstance(toolchain, dict) else cfg.get("MINDCMD_BIN")
    mindcmd = resolve_tool("mindcmd", configured)

    image_list = image_list or cfg.get("MINDCMD_IMAGE_LIST")
    if not image_list and sample is not None:
        raw = sim / "input.bin"
        np.asarray(sample).tofile(raw)
        generated = sim / "image_ref_list.txt"
        generated.write_text(str(raw.resolve()) + "\n", encoding="utf-8")
        image_list = generated
    if not image_list:
        raise ValueError("请传入 image_list 或配置 MINDCMD_IMAGE_LIST；它必须与模型前处理约定一致")

    ini = sim / "mindcmd.ini"
    _write_switches(ini, board=bool(board), instruction=instruction, dump=dump)
    workspace = sim / "work_space"
    workspace.mkdir(exist_ok=True)
    cmd = [mindcmd, "oneclick", "onnx", "-m", str((task_dir / "export" / "model.onnx").resolve()),
           "-i", str(Path(image_list).expanduser().resolve())]
    aipp = aipp or cfg.get("AIPP_CONFIG")
    if aipp:
        cmd += ["--aipp", str(Path(aipp).expanduser().resolve())]

    env_ini = os.environ.get("MINDCMD_CONFIG")
    if env_ini:
        shutil.copy2(ini, Path(env_ini).expanduser())
    run_command(cmd, cwd=sim, timeout=7200, log_file=sim / "mindcmd.log")
    cmp_files, dumps = _find_reports(workspace)
    metrics = _parse_metrics(cmp_files)
    metrics.update({
        "method": "mindcmd-board" if board else "mindcmd-instsim" if instruction else "mindcmd-funcsim",
        "compare_files": len(cmp_files),
        "dump_files": len(dumps),
    })
    (sim / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (sim / "simulate_report.md").write_text(
        "# CV610 MindCmd Simulation Report\n\n" +
        "\n".join(f"- {k}: `{v}`" for k, v in metrics.items()) +
        "\n\n完整精度报告位于 `work_space/output/project_*/cmp/`。\n",
        encoding="utf-8")
    from magnetar.stages.state import mark_stage
    mark_stage(task_dir, "SIMULATE", metrics=metrics,
               summary=f"SIMULATE {metrics['method']} cmp_files={len(cmp_files)}")
    return metrics
