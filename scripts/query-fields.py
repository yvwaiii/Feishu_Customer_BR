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


payload = {
    "required_fields": list(FIELD_SPECS),
    "optional_fields": list(OPTIONAL_FIELD_SPECS),
    "all_fields": list(FIELD_SPECS) + list(OPTIONAL_FIELD_SPECS),
    "field_count": len(FIELD_SPECS) + len(OPTIONAL_FIELD_SPECS),
    "instruction": "先读取实体 meta，只查询 meta 中真实存在的 all_fields；返回值需保留原始 JSON 数字精度。",
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
