---
name: magnetar
description: Convert remote or local CV models into Hi3516CV610 OM delivery packages with MindCmd validation and SVP_ACL C++ integration.
---

# Magnetar CV610

始终使用中文。完整约束见仓库根目录 `AGENTS.md`。

## 工作流

```text
INIT → ACQUIRE → EXPORT → TOOLCHAIN → COMPILE → SIMULATE
→ SDK-GEN → RUNONBOARD（可选）→ PACKAGE → PUBLISH（需确认）
```

优先调用 `magnetar/stages/*.py` 的确定性函数。状态读取 `TASK_DIR/.magnetar-state.json`，详细日志只落盘并读取尾部摘要。

## 阶段要求

| 阶段 | 执行函数 | 验证 |
|---|---|---|
| INIT | `stages.init.run` | 任务目录与配置快照 |
| ACQUIRE | `stages.acquire.run` | 原模型与 `model_flow.json` |
| EXPORT | `run_generic`/`run_custom` | 静态 ONNX、原框架对分 |
| TOOLCHAIN | `stages.toolchain.run` | ATC、MindCmd、交叉编译器 |
| COMPILE | `stages.compile.run` | 生成非空 `model.om` |
| SIMULATE | `stages.simulate.run` | MindCmd cmp/dump 报告 |
| SDK-GEN | `run_generic_python/cpp` | PC 参考代码与 SVP_ACL C++ 代码 |
| RUNONBOARD | `stages.runonboard.run` | 显式 BOARD 上板；无板跳过并标注 |
| PACKAGE | `stages.package.assemble` | OM、复现命令、代码和报告齐全 |
| PUBLISH | `stages.publish.publish` | 必须获得用户确认和凭据 |

## STOP 点

- SOURCE 缺失或需要私有凭据。
- ONNX 对分失败或动态 Shape 无法静态化。
- ATC、MindCmd、SDK 或交叉编译器不可用。
- ATC 失败、需要修改模型或增加自定义算子。
- MindCmd 精度不达标，需要调整 AIPP、AMCT、量化或进入 QAT。
- 任何发布操作。

## CV610 约束

- 只支持 Hi3516CV610，不使用 AXERA 工具链。
- CANN/ATC/MindCmd 与板端 SDK 必须版本匹配。
- musl 使用 `arm-v01c02-linux-musleabi-`，glibc 使用 `arm-v01c02-linux-gnueabi-`。
- MindCmd 对分顺序：float → funcsim → instsim → npu。
- 板端使用 SVP_ACL，退出必须 reset device 后 finalize。
- BOARD 只能显式配置；禁止扫网和自动安装 daemon。
- Python 仅作为 PC ONNX 参考；板端交付以 C/C++ 为准。

## 恢复

中断后读取 `.magnetar-state.json`，从最后阶段继续；不要重放已经成功的编译、仿真或上板操作。
