# Magnetar CV610

将浮点 CV 模型转换为 Hi3516CV610 可部署的 OM 交付包。

```text
模型 → 静态 ONNX → AMCT（可选）→ ATC → OM
     → MindCmd 功能/指令/上板对分 → SVP_ACL C++ SDK → 交付包
```

## 支持范围

- 目标：`Hi3516CV610`
- 输入模型：当前以静态 ONNX 为主
- 编译：SDK 匹配版本的 CANN/ATC
- 量化：AMCT 产出的 deploy ONNX 与量化参数（可选）
- 验证：MindCmd `funcsim`、`instsim`、NPU board run
- 板端：32 位 ARM musl/glibc、SVP_ACL

LLM/ax-llm、Pulsar2、AXMODEL、AXEngine 不属于此分支支持范围。

## 环境

Linux x86_64 开发机需要：

- Python 3.10+
- Git、CMake
- 与 CV610 SDK 匹配的 CANN/ATC 和 MindCmd
- `arm-v01c02-linux-musleabi-*`（musl）或 `arm-v01c02-linux-gnueabi-*`（glibc）
- Hi3516CV610 SDK
- 可选：SSH/SCP、sshpass（仅密码登录需要）

安装 CANN 后先执行配套环境脚本：

```bash
source "$HOME/Ascend/ascend-toolkit/<version>/x86_64-linux/script/setenv.sh"
```

## 快速开始

```bash
git clone https://github.com/baaljiangjun/Magnetar.git
cd Magnetar
cp .magnetarrc.example .magnetarrc
vim .magnetarrc
./bin/magnetar check
```

最小配置：

```ini
SOURCE=/path/to/model-or-repo
MODEL_NAME=demo
TARGET_HARDWARE=Hi3516CV610
CV610_SDK_ROOT=/path/to/Hi3516CV610_SDK
MINDCMD_IMAGE_LIST=/path/to/image_ref_list.txt
```

板端验证需要显式配置，不会扫描局域网：

```ini
BOARD=root@192.168.1.10
BOARD_PASSWORD=
BOARD_RUN_COMMAND=cd /tmp/magnetar_cv610 && ./cv610_infer model.om
```

建议使用 SSH Key，不在配置文件中保存密码。

## 阶段

| 阶段 | 功能 | 产物 |
|---|---|---|
| ACQUIRE | 获取模型与前后处理契约 | `origin/` |
| INIT | 创建隔离任务目录 | `TASK_DIR/config.json` |
| EXPORT | 导出静态 ONNX 并与原框架对分 | `export/model.onnx` |
| TOOLCHAIN | 检查 ATC、MindCmd、交叉编译器 | 工具链信息 |
| COMPILE | ATC 编译 | `compile/model.om` |
| SIMULATE | MindCmd 功能/指令仿真和精度对比 | `simulate_report.md` |
| SDK-GEN | 生成 PC 参考代码和 SVP_ACL C++ 骨架 | `sdk/` |
| RUNONBOARD | 显式 SSH 上板验证 | `runonboard_report.md` |
| PACKAGE | 组装可复现交付包 | `package/` |
| PUBLISH | 用户确认后发布 | 仓库地址 |

## ATC

`magnetar.stages.compile` 从 `model_meta.json` 生成 ATC 命令，基础参数包括：

```text
--mode=0
--framework=5
--model=<model.onnx>
--output=<compile/model>
--input_shape=<name:shape>
--soc_version=Hi3516CV610
--workbuf_optimize_enable=1
```

可通过以下配置扩展：

```ini
AIPP_CONFIG=/path/to/insert_op.cfg
QUANT_PARAM_FILE=/path/to/quant_param_record.txt
ATC_EXTRA_ARGS=--pb_share_config=30
```

生成的完整命令保存在 `compile/atc_command.txt`。

## MindCmd 对分

SIMULATE 生成阶段开关并调用：

```bash
mindcmd oneclick onnx -m model.onnx -i image_ref_list.txt
```

结果目录遵循 MindCmd 约定：

```text
simulate/work_space/output/project_*/
├─ cmp/
└─ dump/
   ├─ float/
   ├─ funcsim/
   ├─ instsim/
   └─ npu/
```

## C++ SDK 说明

生成器提供经过知识库校准的 ACL 生命周期骨架：

```text
svp_acl_init
→ svp_acl_rt_set_device
→ 检查 SVP_ACL_DEVICE
→ 模型加载/数据集/Buffer/执行
→ 卸载模型
→ svp_acl_rt_reset_device
→ svp_acl_finalize
```

模型加载和 Dataset/Buffer 帮助函数会因 SDK 补丁版本不同而变化，因此生成代码明确要求从目标 SDK 的以下样例集成：

```text
smp/a7_linux/source/mpp/sample/svp/common/sample_common_svp_npu.c
smp/a7_linux/source/mpp/sample/svp/svp_npu/
```

在没有目标 SDK 的情况下，Magnetar 不会伪造一个声称可运行的 ABI。

## 依据

- `zh/01.software/pc/SVP_NPU/ATC工具使用指南.pdf`
- `zh/01.software/pc/SVP_NPU/MindCmd 使用指南.pdf`
- `zh/01.software/pc/SVP_NPU/快速上手指南.pdf`
- `zh/01.software/pc/SVP_NPU/AMCT使用指南（PyTorch）.pdf`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/common/sample_common_svp_npu.c`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/bsp/readme_cn.txt`

## 当前边界

- 不自动下载私有 CANN、MindCmd 或 SDK。
- 不自动扫描局域网，也不自动向板端安装守护进程。
- Python SDK 是 PC ONNX 参考实现；CV610 板端以 C/C++ SVP_ACL 为准。
- 生成 OM 不代表业务精度通过，必须执行模型级和任务级测试。
