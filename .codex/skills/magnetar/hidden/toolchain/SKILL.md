---
name: toolchain
description: Validate the CV610 ATC, MindCmd, SDK, and 32-bit cross toolchain.
---

# TOOLCHAIN

调用 `magnetar.stages.toolchain.run()`，验证：

- 与目标 SDK 配套的 ATC/CANN；
- MindCmd 及其运行环境；
- Hi3516CV610 SDK；
- musl 的 `arm-v01c02-linux-musleabi-` 或 glibc 的
  `arm-v01c02-linux-gnueabi-` 交叉编译器。

记录工具路径和版本。任何关键工具缺失时停止，并报告缺失项，不自动下载未知版本镜像。
