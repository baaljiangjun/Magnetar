# Hi3516CV610 工具链知识索引

## PC 工具侧

- `zh/01.software/pc/SVP_NPU/快速上手指南.pdf`
- `zh/01.software/pc/SVP_NPU/驱动和开发环境安装指南.pdf`
- `zh/01.software/pc/SVP_NPU/ATC工具使用指南.pdf`
- `zh/01.software/pc/SVP_NPU/AMCT使用指南（PyTorch）.pdf`
- `zh/01.software/pc/SVP_NPU/MindCmd 使用指南.pdf`

## 板端与样例

- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/common/sample_common_svp_npu.c`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/svp_npu/readme.txt`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/svp/svp_npu/sample_svp_npu/`
- `code/Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/bsp/readme_cn.txt`

## 核心约束

- ONNX 输入 Shape 必须固定。
- ATC 目标为 `Hi3516CV610`，输出 OM。
- ATC/AMCT/MindCmd/板端库必须使用相互匹配的版本。
- MindCmd 可产生 float、funcsim、instsim、npu Dump 和 cmp 报告。
- musl 工具链为 `arm-v01c02-linux-musleabi-`，glibc 为 `arm-v01c02-linux-gnueabi-`。
- 板端 ACL 退出顺序包含 reset device 和 finalize。
