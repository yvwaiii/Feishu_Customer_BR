#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

renderer_path = Path(__file__).with_name("render-snapshot.py")
spec = importlib.util.spec_from_file_location("render_snapshot", renderer_path)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
FIELD_SPECS = renderer.FIELD_SPECS
OPTIONAL_FIELD_SPECS = renderer.OPTIONAL_FIELD_SPECS
FORMAL_C360_SPECS = renderer.FORMAL_C360_SPECS
AEOLUS_FIELD_SPECS = renderer.AEOLUS_FIELD_SPECS


payload = {
    "required_fields": list(FIELD_SPECS),
    "optional_fields": list(OPTIONAL_FIELD_SPECS),
    "all_fields": list(FIELD_SPECS) + list(OPTIONAL_FIELD_SPECS),
    "field_count": len(FIELD_SPECS) + len(OPTIONAL_FIELD_SPECS),
    "formal_br": {
        "c360_fields": [
            {"field": key, "display_name": spec[0]}
            for key, spec in FORMAL_C360_SPECS.items()
        ],
        "aeolus_fields": [
            {"field": key, "display_name": spec[0]}
            for key, spec in AEOLUS_FIELD_SPECS.items()
        ],
        "required_metric_count": 19,
        "all_required": True,
        "c360_only_status": "draft_only",
        "near_match_substitution_allowed": False,
    },
    "instruction": "先读取实体 meta，只查询 meta 中真实存在的 all_fields；正式 BR 还必须逐项获取 formal_br.c360_fields 与 formal_br.aeolus_fields，禁止相近字段替代；返回值需保留原始 JSON 数字精度。",
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
