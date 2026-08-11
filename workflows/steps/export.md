# EXPORT（yaml step id: export）

- kind: agent；skill: `.codex/skills/magnetar/hidden/export/SKILL.md`
- depends_on: `acquire_valid`
- inputs: origin_path / acquire_manifest / TASK_DIR / model_flow
- outputs: onnx_path / model_meta_json / calibration_dir / export_report
- timeout: 3600s；retry: 1 次（export_failed / validation_mismatch / compile_rollback）
- on_failure: ask_user（多次失败需用户介入）
- 要点：静态 ONNX；原框架与 ONNX Runtime 使用相同样本和前后处理；cosine 建议 ≥ 0.99；
  校准集优先使用真实业务数据，扰动数据只作已标注的兜底。
- 不支持 LLM 专用构建路径；本分支只处理可导出静态 ONNX 的 CV 模型。
- 后置：`stage_review_export` + `export_valid` gate
