---
name: compile
description: Compile static ONNX into Hi3516CV610 OM with ATC.
---

# COMPILE

调用 `magnetar.stages.compile.run(task_dir)`。

- ONNX 输入必须是静态 Shape。
- ATC 必须使用 `--framework=5 --soc_version=Hi3516CV610 --mode=0`。
- 保存完整命令到 `compile/atc_command.txt`，日志和摘要写入编译目录。
- 验证 `compile/model.om` 存在且非空。

ATC 报不支持算子、Shape 或模型转换错误时停止，返回 EXPORT 修模；不得伪造 OM。
