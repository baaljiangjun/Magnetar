---
name: sdk-gen
description: Generate a PC ONNX reference and a buildable CV610 SVP_ACL C++ runner.
---

# SDK-GEN

调用：

- `magnetar.stages.sdk_gen.run_generic_python(task_dir)`：PC 端 ONNX Runtime 参考；
- `magnetar.stages.sdk_gen.run_generic_cpp(task_dir)`：板端可编译 SVP_ACL C++ 执行器。

模型接口以 `export/model_meta.json` 为准，前后处理以
`origin/model_flow.json` 为准。板端不使用 Python 推理封装。

C++ 必须遵循 `svp_acl_init → set_device → load/run → reset_device → finalize` 生命周期。
CV610 模型描述最后两个输入为 task/work buffer，业务输入数按 `total_inputs - 2`
计算，并按业务输入 → task → work 顺序加入 Dataset。生成后必须用用户指定 SDK 的
32 位交叉工具链实际编译；不得交付 TODO 骨架。
