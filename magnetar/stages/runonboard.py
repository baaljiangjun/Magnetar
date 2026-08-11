"""RUNONBOARD: deploy a CV610 package through SSH or explicit NFS+serial."""
from __future__ import annotations

import json
import ipaddress
import os
import shutil
from pathlib import Path

from magnetar.board_util import scp_to, select_board, serial_command, serial_ipv4, ssh
from magnetar.config import load_task_config, require_serial_config


def _write_report(out: Path, report: dict, log: str) -> None:
    (out / "board.log").write_text(log, encoding="utf-8")
    (out / "runonboard_report.md").write_text(
        "# CV610 Run On Board Report\n\n" +
        "\n".join(f"- {k}: `{v}`" for k, v in report.items()) + "\n", encoding="utf-8")


def _run_nfs_serial(task_dir: Path, cfg: dict, executable: Path | None, sample) -> tuple[dict, str]:
    port, baud = require_serial_config(cfg)
    if executable is None or sample is None:
        raise ValueError("NFS+串口上板需要显式提供 executable 和 sample")
    server = str(cfg.get("BOARD_NFS_SERVER", "")).strip()
    export = str(cfg.get("BOARD_NFS_EXPORT", "")).strip()
    local_root_value = str(cfg.get("BOARD_NFS_LOCAL_ROOT", "")).strip()
    local_root = Path(local_root_value) if local_root_value else None
    mount = str(cfg.get("BOARD_NFS_MOUNT", "/mnt/nfs")).strip()
    if not server or not export or local_root is None:
        raise ValueError("NFS+串口需要 BOARD_NFS_SERVER/EXPORT/LOCAL_ROOT")
    board_ip, prefix = serial_ipv4(port, baud)
    if ipaddress.ip_address(server) not in ipaddress.ip_network(f"{board_ip}/{prefix}", strict=False):
        raise RuntimeError(f"NFS服务器 {server} 与板端 {board_ip}/{prefix} 不在同一网段")
    share = local_root / f"magnetar_{task_dir.name}"
    share.mkdir(parents=True, exist_ok=True)
    shutil.copy2(task_dir / "compile" / "model.om", share / "model.om")
    shutil.copy2(Path(executable), share / "cv610_infer")
    shutil.copy2(Path(sample), share / "input.bin")
    remote = f"{mount}/{share.name}"
    command = (
        f"mkdir -p {mount}; mount | grep -q ' on {mount} ' || "
        f"mount -t nfs -o nolock,tcp {server}:{export} {mount}; "
        f"cp {remote}/cv610_infer /tmp/cv610_infer; chmod +x /tmp/cv610_infer; "
        f"cd {remote}; /tmp/cv610_infer model.om input.bin"
    )
    log = serial_command(port, baud, command, timeout=600)
    return ({"board": board_ip, "transport": "nfs_serial", "serial": port,
             "nfs": f"{server}:{export}", "command": command, "status": "ok"}, log)


def run(task_dir: Path, sample=None, target_hw: str = "Hi3516CV610",
        pwd: str = "", executable: Path | None = None, **_ignored) -> dict | None:
    task_dir = Path(task_dir)
    cfg = load_task_config(task_dir)
    out = task_dir / "runonboard"
    out.mkdir(parents=True, exist_ok=True)
    transport = str(cfg.get("BOARD_TRANSPORT", "ssh")).lower()
    if transport == "nfs_serial":
        report, log = _run_nfs_serial(task_dir, cfg, executable, sample)
        _write_report(out, report, log)
        from magnetar.stages.state import mark_stage
        mark_stage(task_dir, "RUNONBOARD", metrics=report,
                   summary=f"CV610 board {report['board']} OK via NFS+serial")
        return report
    if transport != "ssh":
        raise ValueError(f"不支持 BOARD_TRANSPORT={transport}")
    board = select_board(target_hw, pwd or cfg.get("BOARD_PASSWORD", ""), cfg.get("BOARD"))
    if board is None:
        from magnetar.stages.state import mark_stage
        mark_stage(task_dir, "RUNONBOARD", status="skipped", summary="未配置 CV610 BOARD，跳过上板")
        return None
    remote = cfg.get("BOARD_DEPLOY_DIR", f"/tmp/magnetar_cv610_{os.getpid()}")
    ssh(board, f"mkdir -p {remote}")
    scp_to(board, task_dir / "compile" / "model.om", f"{remote}/model.om")
    if executable:
        scp_to(board, executable, f"{remote}/cv610_infer")
        ssh(board, f"chmod +x {remote}/cv610_infer")
        command = cfg.get("BOARD_RUN_COMMAND", f"cd {remote} && ./cv610_infer model.om")
    else:
        command = cfg.get("BOARD_RUN_COMMAND")
        if not command:
            raise ValueError("需要 executable，或在配置中设置 BOARD_RUN_COMMAND")
    log = ssh(board, command, timeout=600, max_tail=300)
    report = {"board": board["host"], "chip_type": board.get("chip_type", "Hi3516CV610"),
              "command": command, "status": "ok"}
    _write_report(out, report, log)
    from magnetar.stages.state import mark_stage
    mark_stage(task_dir, "RUNONBOARD", metrics=report, summary=f"CV610 board {board['host']} OK")
    return report
