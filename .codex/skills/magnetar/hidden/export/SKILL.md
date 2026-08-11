---
name: export
description: Export a CV model to static ONNX and validate it against the source model.
---

# EXPORT

MobileNet 可调用 `magnetar.stages.export.run_mobilenet(task_dir)`；其他 CV 模型使用
`run_generic` 或实现模型专用导出器。

- 固定所有输入 Shape，并通过 `onnx.checker`。
- 原框架与 ONNX Runtime 使用同一前处理和真实样本，cosine 建议不低于 0.99。
- 生成 `export/model.onnx`、`model_meta.json`、`export_report.md` 和真实业务校准样本。
- 动态 Shape 无法固定、ONNX 对分失败或只有未经确认的随机校准集时停止。

本项目面向 CV610 CV 模型，不提供 LLM 专用编译分支。
