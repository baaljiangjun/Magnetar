---
name: publish
description: Publish a validated CV610 package only after explicit user confirmation.
---

# PUBLISH

发布前必须确认平台、仓库名和凭据来源。建议仓库名默认
`{model_name}-hi3516cv610-om`。

调用 `magnetar.stages.publish.publish(...)` 后验证远端 URL。发布内容使用
`om`、`hi3516cv610`、`svp-acl` 标签，不包含密码、令牌、缓存或临时日志。

未获得明确确认、凭据缺失或上板/仿真验收未通过时不得发布。
