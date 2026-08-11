---
name: sdk-gen
description: Generate a PC ONNX reference and a CV610 SVP_ACL C++ integration skeleton.
---

# SDK-GEN

调用：

- `magnetar.stages.sdk_gen.run_generic_python(task_dir)`：PC 端 ONNX Runtime 参考；
- `magnetar.stages.sdk_gen.run_generic_cpp(task_dir)`：板端 SVP_ACL C++ 骨架。

模型接口以 `export/model_meta.json` 为准，前后处理以
`origin/model_flow.json` 为准。板端不使用 Python 推理封装。

C++ 必须遵循 `svp_acl_init → set_device → load/run → reset_device → finalize` 生命周期。
模型加载、Dataset 和 Buffer 代码必须从目标 SDK 同版本的
`sample_common_svp_npu.c` 集成；SDK ABI 未确认时保留明确 TODO，不编造函数签名。
