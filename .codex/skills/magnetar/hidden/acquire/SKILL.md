---
name: acquire
description: Acquire a local or remote CV model without modifying its source.
---

# ACQUIRE

调用 `magnetar.stages.acquire.run(task_dir, source)`，并用
`magnetar.stages.acquire.write_model_flow(task_dir, flow)` 记录已验证的样本、前处理、
后处理和 SDK 调用接口。

验证 `origin/`、`cache/acquire/manifest.json` 和 `origin/model_flow.json`。SOURCE 无效或
需要私有凭据时停止，不猜测凭据。
