"""Generate PC ONNX references and deployable Hi3516CV610 SVP_ACL SDKs."""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path


def _sanitize(name: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_]", "_", name.lower())
    return value if not value[:1].isdigit() else f"model_{value}"


def _load_meta_and_flow(task_dir: Path, meta=None, flow=None):
    if meta is None:
        meta = json.loads((task_dir / "export" / "model_meta.json").read_text(encoding="utf-8"))
    flow_path = task_dir / "origin" / "model_flow.json"
    if flow is None:
        flow = json.loads(flow_path.read_text(encoding="utf-8")) if flow_path.is_file() else {}
    return meta, flow


def run_generic_python(task_dir: Path, meta=None, flow=None,
                       model_name: str | None = None, **_ignored) -> Path:
    """Generate the PC-side ONNX reference used for preprocessing/output checks."""
    task_dir = Path(task_dir)
    meta, _ = _load_meta_and_flow(task_dir, meta, flow)
    name = _sanitize(model_name or meta.get("model_name", "model"))
    root = task_dir / "sdk" / "python"
    pkg = root / f"{name}_sdk"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("from .inference import ModelSDK\n", encoding="utf-8")
    (pkg / "inference.py").write_text(textwrap.dedent('''\
        """PC reference only; CV610 deployment uses the generated C++ SDK."""
        from pathlib import Path
        import numpy as np
        import onnxruntime as ort

        class ModelSDK:
            def __init__(self, model_path):
                path = Path(model_path)
                if path.suffix != ".onnx":
                    raise ValueError("Python reference expects ONNX; OM uses SVP_ACL C++")
                self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

            def run(self, *arrays):
                names = [x.name for x in self.session.get_inputs()]
                return self.session.run(None, {n: np.asarray(v) for n, v in zip(names, arrays)})
        '''), encoding="utf-8")
    (pkg / "example.py").write_text(textwrap.dedent(f'''\
        import argparse, numpy as np
        from {name}_sdk import ModelSDK
        p = argparse.ArgumentParser()
        p.add_argument("--model", default="model.onnx")
        p.add_argument("--input", required=True)
        args = p.parse_args()
        outputs = ModelSDK(args.model).run(np.load(args.input))
        for i, value in enumerate(outputs): np.save(f"output_{{i}}.npy", value)
        '''), encoding="utf-8")
    (root / "requirements.txt").write_text("numpy\nonnxruntime\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# PC Reference SDK\n\n仅用于 ONNX 参考输出；CV610 板端使用 `cpp/`。\n", encoding="utf-8")
    return root


_HEADER = r'''#pragma once
#include <cstdint>
#include <string>
#include <vector>

class Cv610Model {
public:
    bool init(const std::string& acl_config = "", int device_id = 0);
    bool load(const std::string& om_path);
    bool run(const std::vector<uint8_t>& input, std::vector<std::vector<uint8_t>>& outputs);
    void unload();
    void deinit();
    ~Cv610Model();
private:
    int device_id_ = 0;
    bool acl_ready_ = false;
    bool model_ready_ = false;
    void* impl_ = nullptr;
};
'''


_SOURCE = r'''#include "cv610_model.h"
#include "svp_acl.h"
#include "svp_acl_mdl.h"
#include "svp_acl_rt.h"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iostream>

namespace {
constexpr size_t kExtraInputCount = 2;  // task buffer + work buffer
struct Impl {
    uint32_t model_id = 0;
    bool model_loaded = false;
    void* model_mem = nullptr;
    svp_acl_mdl_desc* desc = nullptr;
    svp_acl_mdl_dataset* input = nullptr;
    svp_acl_mdl_dataset* output = nullptr;
    std::vector<void*> input_mem, output_mem;
    std::vector<size_t> input_size, output_size;
};

void destroy_dataset(svp_acl_mdl_dataset*& dataset) {
    if (!dataset) return;
    const size_t count = svp_acl_mdl_get_dataset_num_buffers(dataset);
    for (size_t i = 0; i < count; ++i) {
        auto* buffer = svp_acl_mdl_get_dataset_buffer(dataset, i);
        if (buffer) svp_acl_destroy_data_buffer(buffer);
    }
    svp_acl_mdl_destroy_dataset(dataset);
    dataset = nullptr;
}
}

bool Cv610Model::init(const std::string& config, int device_id) {
    if (acl_ready_) return true;
    device_id_ = device_id;
    const char* cfg = config.empty() ? nullptr : config.c_str();
    svp_acl_error ret = svp_acl_init(cfg);
    if (ret != SVP_ACL_SUCCESS) { std::cerr << "svp_acl_init failed: " << ret << "\n"; return false; }
    ret = svp_acl_rt_set_device(device_id_);
    if (ret != SVP_ACL_SUCCESS) {
        std::cerr << "svp_acl_rt_set_device failed: " << ret << "\n";
        svp_acl_finalize(); return false;
    }
    svp_acl_rt_run_mode mode;
    ret = svp_acl_rt_get_run_mode(&mode);
    if (ret != SVP_ACL_SUCCESS || mode != SVP_ACL_DEVICE) {
        std::cerr << "unexpected run mode: ret=" << ret << " mode=" << mode << "\n";
        svp_acl_rt_reset_device(device_id_); svp_acl_finalize(); return false;
    }
    impl_ = new Impl;
    acl_ready_ = true;
    return true;
}

bool Cv610Model::load(const std::string& om_path) {
    if (!acl_ready_) return false;
    unload();
    auto* p = static_cast<Impl*>(impl_);
    FILE* fp = std::fopen(om_path.c_str(), "rb");
    if (!fp) { std::cerr << "open model failed: " << om_path << "\n"; return false; }
    std::fseek(fp, 0, SEEK_END); const long length = std::ftell(fp); std::fseek(fp, 0, SEEK_SET);
    svp_acl_error ret = length > 0
        ? svp_acl_rt_malloc(&p->model_mem, static_cast<size_t>(length), SVP_ACL_MEM_MALLOC_HUGE_FIRST)
        : static_cast<svp_acl_error>(-1);
    if (ret != SVP_ACL_SUCCESS ||
        std::fread(p->model_mem, 1, static_cast<size_t>(length), fp) != static_cast<size_t>(length)) {
        std::fclose(fp); std::cerr << "read/allocate model failed: " << ret << "\n";
        unload(); return false;
    }
    std::fclose(fp);
    ret = svp_acl_mdl_load_from_mem(static_cast<uint8_t*>(p->model_mem),
                                    static_cast<size_t>(length), &p->model_id);
    if (ret != SVP_ACL_SUCCESS) {
        std::cerr << "svp_acl_mdl_load_from_mem failed: " << ret << "\n"; unload(); return false;
    }
    p->model_loaded = true;
    p->desc = svp_acl_mdl_create_desc();
    if (!p->desc || svp_acl_mdl_get_desc(p->desc, p->model_id) != SVP_ACL_SUCCESS) {
        std::cerr << "get model desc failed\n"; unload(); return false;
    }
    const size_t total_inputs = svp_acl_mdl_get_num_inputs(p->desc);
    const size_t outputs = svp_acl_mdl_get_num_outputs(p->desc);
    if (total_inputs <= kExtraInputCount || total_inputs - kExtraInputCount != 1 || outputs == 0) {
        std::cerr << "unsupported IO count: total_inputs=" << total_inputs
                  << " business_inputs=" << (total_inputs > 2 ? total_inputs - 2 : 0)
                  << " outputs=" << outputs << "\n";
        unload(); return false;
    }
    p->input = svp_acl_mdl_create_dataset(); p->output = svp_acl_mdl_create_dataset();
    if (!p->input || !p->output) { unload(); return false; }
    for (size_t i = 0; i < total_inputs; ++i) {
        const size_t size = svp_acl_mdl_get_input_size_by_index(p->desc, i);
        const size_t stride = svp_acl_mdl_get_input_default_stride(p->desc, i);
        void* mem = nullptr;
        ret = svp_acl_rt_malloc(&mem, size, SVP_ACL_MEM_MALLOC_NORMAL_ONLY);
        auto* buffer = ret == SVP_ACL_SUCCESS ? svp_acl_create_data_buffer(mem, size, stride) : nullptr;
        if (!buffer || svp_acl_mdl_add_dataset_buffer(p->input, buffer) != SVP_ACL_SUCCESS) {
            if (buffer) svp_acl_destroy_data_buffer(buffer); if (mem) svp_acl_rt_free(mem);
            std::cerr << "create business/task/work buffer failed at " << i << "\n"; unload(); return false;
        }
        p->input_mem.push_back(mem); p->input_size.push_back(size);
    }
    for (size_t i = 0; i < outputs; ++i) {
        const size_t size = svp_acl_mdl_get_output_size_by_index(p->desc, i);
        const size_t stride = svp_acl_mdl_get_output_default_stride(p->desc, i);
        void* mem = nullptr;
        ret = svp_acl_rt_malloc(&mem, size, SVP_ACL_MEM_MALLOC_NORMAL_ONLY);
        auto* buffer = ret == SVP_ACL_SUCCESS ? svp_acl_create_data_buffer(mem, size, stride) : nullptr;
        if (!buffer || svp_acl_mdl_add_dataset_buffer(p->output, buffer) != SVP_ACL_SUCCESS) {
            if (buffer) svp_acl_destroy_data_buffer(buffer); if (mem) svp_acl_rt_free(mem);
            std::cerr << "create output buffer failed at " << i << "\n"; unload(); return false;
        }
        p->output_mem.push_back(mem); p->output_size.push_back(size);
    }
    return model_ready_ = true;
}

bool Cv610Model::run(const std::vector<uint8_t>& input,
                     std::vector<std::vector<uint8_t>>& outputs) {
    if (!model_ready_) return false;
    auto* p = static_cast<Impl*>(impl_);
    if (input.size() > p->input_size[0]) { std::cerr << "input too large\n"; return false; }
    std::memset(p->input_mem[0], 0, p->input_size[0]);
    std::memcpy(p->input_mem[0], input.data(), input.size());
    const auto begin = std::chrono::steady_clock::now();
    const svp_acl_error ret = svp_acl_mdl_execute(p->model_id, p->input, p->output);
    const auto end = std::chrono::steady_clock::now();
    std::cerr << "npu_execute_ms="
              << std::chrono::duration<double, std::milli>(end - begin).count()
              << " ret=" << ret << "\n";
    if (ret != SVP_ACL_SUCCESS) return false;
    outputs.resize(p->output_mem.size());
    for (size_t i = 0; i < outputs.size(); ++i) {
        const auto* data = static_cast<const uint8_t*>(p->output_mem[i]);
        outputs[i].assign(data, data + p->output_size[i]);
    }
    return true;
}

void Cv610Model::unload() {
    auto* p = static_cast<Impl*>(impl_); if (!p) return;
    destroy_dataset(p->output); destroy_dataset(p->input);
    for (void* mem : p->output_mem) if (mem) svp_acl_rt_free(mem);
    for (void* mem : p->input_mem) if (mem) svp_acl_rt_free(mem);
    p->output_mem.clear(); p->input_mem.clear(); p->output_size.clear(); p->input_size.clear();
    if (p->desc) { svp_acl_mdl_destroy_desc(p->desc); p->desc = nullptr; }
    if (p->model_loaded) { svp_acl_mdl_unload(p->model_id); p->model_loaded = false; }
    if (p->model_mem) { svp_acl_rt_free(p->model_mem); p->model_mem = nullptr; }
    model_ready_ = false;
}

void Cv610Model::deinit() {
    unload();
    if (acl_ready_) { svp_acl_rt_reset_device(device_id_); svp_acl_finalize(); acl_ready_ = false; }
    delete static_cast<Impl*>(impl_); impl_ = nullptr;
}
Cv610Model::~Cv610Model() { deinit(); }
'''


_MAIN = r'''#include "cv610_model.h"
#include <cstdio>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 3) { std::cerr << "usage: cv610_infer model.om input.bin [acl.json]\n"; return 2; }
    Cv610Model model;
    if (!model.init(argc > 3 ? argv[3] : "")) return 3;
    if (!model.load(argv[1])) return 4;
    FILE* fp = std::fopen(argv[2], "rb"); if (!fp) return 5;
    std::vector<uint8_t> input; uint8_t chunk[4096]; size_t got = 0;
    while ((got = std::fread(chunk, 1, sizeof(chunk), fp)) != 0)
        input.insert(input.end(), chunk, chunk + got);
    std::fclose(fp);
    std::vector<std::vector<uint8_t>> outputs;
    if (!model.run(input, outputs)) return 6;
    for (size_t i = 0; i < outputs.size(); ++i) {
        const std::string path = "output_" + std::to_string(i) + ".bin";
        FILE* out = std::fopen(path.c_str(), "wb"); if (!out) return 7;
        std::fwrite(outputs[i].data(), 1, outputs[i].size(), out); std::fclose(out);
    }
    return 0;
}
'''


def run_generic_cpp(task_dir: Path, meta=None, flow=None,
                    model_name: str | None = None, target_hw="Hi3516CV610", **_ignored) -> Path:
    """Generate a buildable single-business-input CV610 SVP_ACL runner."""
    task_dir = Path(task_dir)
    meta, _ = _load_meta_and_flow(task_dir, meta, flow)
    root = task_dir / "sdk" / "cpp"
    (root / "include").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "model_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (root / "include" / "cv610_model.h").write_text(_HEADER, encoding="utf-8")
    (root / "src" / "cv610_model.cpp").write_text(_SOURCE, encoding="utf-8")
    (root / "src" / "main.cpp").write_text(_MAIN, encoding="utf-8")
    (root / "CMakeLists.txt").write_text(textwrap.dedent('''\
        cmake_minimum_required(VERSION 3.15)
        project(cv610_model CXX)
        set(CMAKE_CXX_STANDARD 14)
        if(NOT DEFINED ENV{CV610_SDK_ROOT})
          message(FATAL_ERROR "set CV610_SDK_ROOT to the matching Hi3516CV610 SDK")
        endif()
        set(SDK $ENV{CV610_SDK_ROOT})
        include_directories(include ${SDK}/smp/a7_linux/source/out/include)
        link_directories(${SDK}/smp/a7_linux/source/out/lib)
        add_executable(cv610_infer src/main.cpp src/cv610_model.cpp)
        target_link_libraries(cv610_infer -Wl,--start-group svp_acl ss_mpi ss_mpi_sysmem
          ss_mpi_sysbind protobuf-c securec ot_osal -Wl,--end-group pthread dl m)
        '''), encoding="utf-8")
    (root / "README.md").write_text(
        "# CV610 C++ SDK\n\n可编译的 SVP_ACL 单业务输入执行器。模型描述最后两个输入是 task/work "
        "buffer，代码会按官方 sample 顺序创建。运行：`./cv610_infer model.om input.bin`。\n",
        encoding="utf-8")
    return root


def run_mobilenet_python(task_dir: Path, imagenet_labels=None):
    return run_generic_python(task_dir, model_name="mobilenet_v2")


def run_mobilenet_cpp(task_dir: Path, target_hw="Hi3516CV610"):
    return run_generic_cpp(task_dir, model_name="mobilenet_v2", target_hw=target_hw)


def make_npu_only_sdk_dir(_py_dir: Path) -> bool:
    """Compatibility shim: CV610 board delivery is C++ only."""
    return False
