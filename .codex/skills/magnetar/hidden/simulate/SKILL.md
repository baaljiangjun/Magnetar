---
name: simulate
description: Validate CV610 OM accuracy with MindCmd float, simulator, and NPU stages.
---

# SIMULATE

调用 `magnetar.stages.simulate.run(task_dir, sample)`。

MindCmd 按 `float → funcsim → instsim → npu` 执行，并启用 `cmp`；需要定位误差时启用
`dump`。使用同一输入和前后处理，保存 `simulate/mindcmd.ini`、日志、结果与
`simulate_report.md`。

先定位 ONNX/float 差异，再定位 ATC/funcsim，随后 instsim，最后才看板端 npu。
精度不合格时停止，检查 AIPP、输入布局、量化配置和 AMCT/QAT，不把仿真失败自动降级成通过。
