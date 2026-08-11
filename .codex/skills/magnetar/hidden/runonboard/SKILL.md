---
name: runonboard
description: Deploy an OM and executable to an explicitly configured Hi3516CV610 board.
---

# RUNONBOARD

调用 `magnetar.stages.runonboard.run(task_dir, sample)`。

- BOARD 必须显式配置；未配置时标注跳过。
- 使用 NFS + 串口时，必须先询问用户实际串口号并配置
  `BOARD_SERIAL_PORT`；禁止默认 COM3、禁止自动选择扫描到的端口。
- 配置板端 IP 后先验证与 PC 同网段及双向连通，再挂载 NFS。
- 优先 SSH key，密码只从环境变量读取，不写入报告或仓库。
- 使用 SCP/NFS 传输已构建的 OM、可执行文件和样本。
- 禁止扫描局域网、探测任意端口或自动安装后台 daemon。
- 验证输出、耗时、内存和板端日志，写入 `runonboard_report.md`。

连接失败、SDK/动态库不匹配或输出异常时停止并保留日志。
