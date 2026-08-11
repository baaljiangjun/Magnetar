# Magnetar CV610 workflow

```text
INIT → ACQUIRE → EXPORT → TOOLCHAIN → COMPILE → SIMULATE
→ SDK-GEN → RUNONBOARD（可选）→ PACKAGE → PUBLISH（需确认）
```

- 编译产物：`compile/model.om`
- 精度验证：MindCmd float/funcsim/instsim/npu Dump 与 cmp
- 板端 Runtime：SVP_ACL
- 板端连接：只使用显式 BOARD，不扫描网络
- 失败门禁：动态 Shape、工具链缺失、ATC 失败、精度不达标、需要修改模型或凭据
