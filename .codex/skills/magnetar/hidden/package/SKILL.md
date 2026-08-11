---
name: package
description: Assemble a reproducible Hi3516CV610 OM delivery package.
---

# PACKAGE

调用 `magnetar.stages.package.assemble(task_dir, metrics, toolchain, model_name, labels)`。

交付包必须包含：

- `models/model.om` 与元信息；
- `model_convert/model.onnx`、ATC 完整命令和 MindCmd 配置模板；
- PC ONNX 参考代码；
- CV610 SVP_ACL C++ 代码；
- 导出、编译、仿真和可选板端报告；
- 清楚标注 SDK 版本、交叉工具链和尚未完成的板端适配项。

验证包内引用不把 OM 交给 ONNX Runtime，且不包含凭据、缓存和构建产物。
