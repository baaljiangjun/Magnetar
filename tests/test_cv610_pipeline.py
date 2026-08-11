import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from magnetar.stages.compile import _shape_spec, build_atc_command, summarize_compile_log
from magnetar.stages.package import assemble
from magnetar.stages.sdk_gen import run_generic_cpp, run_generic_python
from magnetar.stages.simulate import cosine


class Cv610PipelineTest(unittest.TestCase):
    def _task(self, root: Path) -> Path:
        task = root / "task"
        for d in ("origin", "export", "compile", "sdk/python", "sdk/cpp"):
            (task / d).mkdir(parents=True, exist_ok=True)
        meta = {
            "model_name": "demo",
            "inputs": [{"name": "images", "shape": [1, 3, 224, 224], "dtype": "float32"}],
            "outputs": [{"name": "logits", "shape": [1, 1000], "dtype": "float32"}],
        }
        (task / "export" / "model_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (task / "export" / "model.onnx").write_bytes(b"onnx")
        (task / "config.json").write_text(json.dumps({"TARGET_HARDWARE": "Hi3516CV610"}), encoding="utf-8")
        return task

    def test_static_shape_spec(self):
        self.assertEqual(_shape_spec({"inputs": [{"name": "x", "shape": [1, 3, 8, 8]}]}), "x:1,3,8,8")
        with self.assertRaises(ValueError):
            _shape_spec({"inputs": [{"name": "x", "shape": [1, -1]}]})

    def test_atc_command_targets_cv610_and_om(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task(Path(tmp))
            cmd = build_atc_command(task, atc_bin="/opt/atc")
            joined = " ".join(cmd)
            self.assertIn("--framework=5", joined)
            self.assertIn("--soc_version=Hi3516CV610", joined)
            self.assertIn("--input_shape=images:1,3,224,224", joined)
            self.assertIn("compile", joined)

    def test_sdk_is_onnx_reference_plus_svp_acl_cpp(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task(Path(tmp))
            run_generic_python(task)
            run_generic_cpp(task)
            py = (task / "sdk/python/demo_sdk/inference.py").read_text(encoding="utf-8")
            cpp = (task / "sdk/cpp/src/cv610_model.cpp").read_text(encoding="utf-8")
            cmake = (task / "sdk/cpp/CMakeLists.txt").read_text(encoding="utf-8")
            self.assertIn("onnxruntime", py)
            self.assertNotIn("pyaxengine", py)
            self.assertIn("svp_acl_init", cpp)
            self.assertIn("svp_acl_rt_reset_device", cpp)
            self.assertIn("kExtraInputCount = 2", cpp)
            self.assertIn("task buffer + work buffer", cpp)
            self.assertIn("svp_acl_mdl_execute", cpp)
            self.assertNotIn("TODO: bind", cpp)
            self.assertIn("svp_acl", cmake)
            self.assertIn("ss_mpi_sysmem", cmake)

    def test_cosine(self):
        self.assertAlmostEqual(cosine(np.array([1, 2]), np.array([1, 2])), 1.0, places=6)

    def test_package_keeps_onnx_reference_separate_from_om(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task(Path(tmp))
            (task / "compile" / "model.om").write_bytes(b"om")
            (task / "compile" / "atc_command.txt").write_text("atc --soc_version=Hi3516CV610", encoding="utf-8")
            run_generic_python(task)
            run_generic_cpp(task)
            pkg = assemble(task, {}, "ATC", model_name="demo")
            demo = (pkg / "python" / "demo.py").read_text(encoding="utf-8")
            self.assertIn("model_convert/model.onnx", demo)
            self.assertNotIn('ModelSDK("models/model.om")', demo)
            self.assertTrue((pkg / "models" / "model.om").is_file())


if __name__ == "__main__":
    unittest.main()
