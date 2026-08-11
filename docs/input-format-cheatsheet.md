# CV610 输入格式检查表

同一个样本在原框架、ONNX、AMCT、ATC/MindCmd 和板端必须保持以下契约一致：

- 输入名称与顺序
- 静态 Shape
- NCHW/NHWC
- RGB/BGR/YUV420SP/NV21
- FP32/FP16/U8 等数据类型
- Resize、Letterbox、Crop
- Mean、Scale、Std
- AIPP 是否启用，避免前处理重复
- 原始数据文件的字节序和排列

先比较实际网络输入，再比较第一层，最后比较尾层和任务后处理。
