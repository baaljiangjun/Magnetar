# Magnetar CV610 Agent Guide

所有回复使用中文。本分支只面向 Hi3516CV610。

## 目标

```text
模型 → 静态 ONNX → AMCT（可选）→ ATC → OM
→ MindCmd 仿真/上板对分 → SVP_ACL C++ SDK → 交付包
```

禁止重新引入 Pulsar2、AXMODEL、AXEngine、pyaxengine、ax-remote-infer 或 ax-llm。

## 阶段接口

| 阶段 | 模块 | 产物 |
|---|---|---|
| INIT | `magnetar.stages.init` | 隔离任务目录与配置快照 |
| ACQUIRE | `magnetar.stages.acquire` | 原始模型与 `model_flow.json` |
| EXPORT | `magnetar.stages.export` | 静态 ONNX 与 `model_meta.json` |
| TOOLCHAIN | `magnetar.stages.toolchain` | ATC、MindCmd、交叉编译器信息 |
| COMPILE | `magnetar.stages.compile` | `model.om`、ATC 命令和日志 |
| SIMULATE | `magnetar.stages.simulate` | MindCmd cmp/dump 与报告 |
| SDK-GEN | `magnetar.stages.sdk_gen` | PC ONNX 参考代码、SVP_ACL C++ 骨架 |
| RUNONBOARD | `magnetar.stages.runonboard` | 显式 SSH 板端验证报告 |
| PACKAGE | `magnetar.stages.package` | CV610 交付包 |
| PUBLISH | `magnetar.stages.publish` | 用户确认后的发布地址 |

## 强制门禁

- SOURCE 未提供。
- 原模型与 ONNX 对分不达标。
- ONNX 输入包含未静态化维度。
- ATC、MindCmd 或交叉编译器不可用。
- ATC 未生成 OM。
- MindCmd 功能仿真精度不达标。
- 需要修改原模型或进入 AMCT/QAT。
- 需要凭据或执行 PUBLISH。

未配置 BOARD 时可以跳过 RUNONBOARD，但交付报告必须标注“未完成真实板端验证”。

## 安全规则

- BOARD 必须显式配置；禁止扫描局域网。
- 禁止自动安装板端 daemon。
- 优先 SSH Key；不得把密码和 Token 写入交付包。
- CANN、MindCmd、SDK 必须由用户提供匹配版本，不得从未知地址下载。
- 所有失败分支必须保留完整日志路径，只向 Agent 返回尾部摘要。

## CV610 技术约束

- 目标 SoC 固定为 `Hi3516CV610`。
- 交叉工具链为 32 位 ARM：musl 使用 `arm-v01c02-linux-musleabi-`，glibc 使用 `arm-v01c02-linux-gnueabi-`。
- OM 在板端通过 SVP_ACL 执行。
- ACL 生命周期至少包含 init、set device、run mode check、reset device、finalize。
- ATC、AMCT、MindCmd 配置和运行时必须与目标 SDK 版本匹配。
- 输入格式、AIPP、归一化、量化校准和板端前处理必须保持一致。

## 知识依据

- `zh/01.software/pc/SVP_NPU/ATC工具使用指南.pdf`
- `zh/01.software/pc/SVP_NPU/MindCmd 使用指南.pdf`
- `zh/01.software/pc/SVP_NPU/快速上手指南.pdf`
- `zh/01.software/pc/SVP_NPU/AMCT使用指南（PyTorch）.pdf`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/common/sample_common_svp_npu.c`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/bsp/readme_cn.txt`
