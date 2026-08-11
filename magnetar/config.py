"""读取 .magnetarrc 配置和环境变量。"""
import json, os, re
from pathlib import Path

def load_config(project_root: Path | None = None) -> dict:
    if project_root is None:
        for parent in [Path.cwd(), *Path.cwd().parents]:
            if (parent / ".magnetarrc").exists() or (parent / ".git").exists():
                project_root = parent; break
        else:
            project_root = Path.cwd()
    cfg: dict[str, str] = {}
    rc = project_root / ".magnetarrc"
    if rc.exists():
        for line in rc.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            m = re.match(r"^(\w+)\s*=\s*(.*)", line)
            if m: cfg[m.group(1)] = m.group(2).strip()
    for key in cfg:
        if os.environ.get(key): cfg[key] = os.environ[key]
    cfg.setdefault("TARGET_HARDWARE", "Hi3516CV610")
    cfg.setdefault("SDK_LANG", "both")
    cfg.setdefault("BOARD_USER", "root")
    cfg.setdefault("BOARD_PORT", "22")
    cfg.setdefault("BOARD_PASSWORD", os.environ.get("MAGNETAR_BOARD_PASSWORD", ""))
    cfg.setdefault("BOARD_TRANSPORT", "ssh")
    cfg.setdefault("BOARD_SERIAL_PORT", "")
    cfg.setdefault("BOARD_SERIAL_BAUD", "115200")
    cfg.setdefault("ATC_BIN", "atc")
    cfg.setdefault("MINDCMD_BIN", "mindcmd")
    cfg.setdefault("LIBC", "musl")
    return cfg


def load_task_config(task_dir: Path | str, project_root: Path | None = None) -> dict:
    """加载单任务配置：TASK_DIR/config.json（INIT 快照）优先，缺失键回退 .magnetarrc 公共默认，环境变量最后覆盖。

    并发任务隔离约定：每个任务 INIT 时把任务参数（SOURCE/TARGET_HARDWARE/MODEL_NAME/BOARD/TASK_DIR）
    固化到自己的 config.json；之后各阶段一律读本函数，不再回改全局 .magnetarrc。
    """
    cfg = dict(load_config(project_root))
    snap = Path(task_dir) / "config.json"
    if snap.is_file():
        try:
            snap_cfg = json.loads(snap.read_text(encoding="utf-8"))
        except Exception:
            snap_cfg = {}
        cfg.update({k: v for k, v in snap_cfg.items() if v not in (None, "")})
    for key in list(cfg):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    cfg.setdefault("TASK_DIR", str(task_dir))
    cfg.setdefault("TARGET_HARDWARE", "Hi3516CV610")
    cfg.setdefault("BOARD_USER", "root")
    cfg.setdefault("BOARD_PORT", "22")
    cfg.setdefault("BOARD_PASSWORD", os.environ.get("MAGNETAR_BOARD_PASSWORD", ""))
    cfg.setdefault("BOARD_TRANSPORT", "ssh")
    cfg.setdefault("BOARD_SERIAL_PORT", "")
    cfg.setdefault("BOARD_SERIAL_BAUD", "115200")
    cfg.setdefault("ATC_BIN", "atc")
    cfg.setdefault("MINDCMD_BIN", "mindcmd")
    cfg.setdefault("LIBC", "musl")
    return cfg


def require_serial_config(cfg: dict) -> tuple[str, int]:
    """读取用户选择的串口配置；绝不猜测或默认使用某个 COM 口。"""
    port = str(cfg.get("BOARD_SERIAL_PORT", "")).strip()
    if not port:
        raise ValueError(
            "未配置 BOARD_SERIAL_PORT。请先询问用户板子当前连接的串口号"
            "（例如 Windows 的 COM5 或 Linux 的 /dev/ttyUSB0），禁止默认使用 COM3。"
        )
    try:
        baud = int(cfg.get("BOARD_SERIAL_BAUD", 115200))
    except (TypeError, ValueError) as exc:
        raise ValueError("BOARD_SERIAL_BAUD 必须是整数，例如 115200") from exc
    if baud <= 0:
        raise ValueError("BOARD_SERIAL_BAUD 必须大于 0")
    return port, baud
