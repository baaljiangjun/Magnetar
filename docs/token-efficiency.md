# CV610 长流程日志约定

- `compile.log`、`mindcmd.log` 和 SSH 输出完整落盘，Agent 只读错误摘要和尾部。
- 禁止读取 `.onnx`、`.om`、`.bin`、`.npy` 等二进制内容。
- ATC 完成后调用 `summarize_compile_log()` 获取 OM 大小和错误行。
- MindCmd 只汇总 `cmp/` 报告指标，逐层 Dump 仅在定位首个异常层时按需读取。
- 恢复任务优先读取 `.magnetar-state.json`，不重复执行已完成阶段。
