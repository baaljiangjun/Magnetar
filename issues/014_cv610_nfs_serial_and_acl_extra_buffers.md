# CV610：NFS+串口部署与 SVP_ACL 附加 Buffer

## 现象

在没有 SSH 的 Hi3516CV610 板上，通过 NFS+串口运行 ATC 生成的 OM 时，初版 SDK
在加载或执行阶段失败：

```text
model desc failed: inputs=3 outputs=1
input->num(1) should be 3
```

## 根因

`svp_acl_mdl_get_num_inputs()` 返回模型输入 Dataset 的总 Buffer 数。CV610 常规模型
最后两个输入是运行时内部的 task buffer 与 work buffer，不能将总数直接当成业务
输入数，也不能只创建业务输入 Buffer。

官方实现依据：

```text
code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/common/
sample_common_svp_npu_model.c
```

创建顺序为：业务输入 → `sample_common_svp_npu_create_task_buf` →
`sample_common_svp_npu_create_work_buf`。

## 修复

- 业务输入数按 `total_inputs - 2` 计算；通用生成器当前明确支持单业务输入。
- 输入 Dataset 按模型描述的 size/stride 创建全部 Buffer。
- 所有 SVP_ACL 失败点输出返回码，并记录 `svp_acl_mdl_execute()` 核心耗时。
- NFS+串口要求用户显式指定串口；不默认 COM3，不扫描局域网。
- 从串口读取板端 IP，并验证 NFS 服务器与板端处于同一网段后才挂载。

## 实测

- OM：3,544,152 bytes；输入：320×320 NV21
- task buffer：400 bytes；work buffer：541,440 bytes
- 连续三次返回码均为 0，输出完全一致
- NPU 核心耗时：12.300、12.305、12.303 ms

检测后处理还应将归一化坐标裁剪到 `[0,1]`，避免浮点回归产生轻微越界。
