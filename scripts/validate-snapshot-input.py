#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identity_resolver import ResolutionError, validate_identity_ledger

MODULES = {
    "即时协同": [
        "active_rate_7workday",
        "activate_rate",
        "active_duration_pavg_7workday",
        "im_dau",
        "im_dau_penetration_rate",
    ],
    "会议协同": [
        "vc_dau",
        "vc_dau_penetration_rate",
        "vc_meeting_cnt",
        "join_meeting_ucnt",
        "vc_meeting_active_duration_pavg_val",
        "minutes_dau",
        "minutes_dau_penetration_rate",
        "vc_ai_dau",
        "vc_ai_minutes_dau_penetration_rate",
    ],
    "内容沉淀": [
        "doc_independent_create_fcnt",
        "doc_view_dau_penetration_rate",
        "tenant_used_wiki_space_cnt",
        "wiki_dau",
        "wiki_dau_penetration_rate",
    ],
    "多维表格": [
        "bitable_independent_create_fcnt",
        "base_rownum_over15000_fcnt",
        "bitable_automation_run",
        "base_dashboard_cnt",
        "base_dau_rate_avg_7workday",
    ],
    "知识管理": [
        "cansearch_pv_per_user",
        "knowledge_ai_pavg_use_cnt",
        "search_dau_penetration_rate",
        "teampedia_dau_penetration_rate",
        "self_build_teampedia_entity_cnt",
    ],
    "AI 赋能": [
        "ai_dau",
        "aily_dau",
        "aily_buddy_dau",
        "base_ai_dau",
        "miaoda_app_dau",
        "miaoda_claw_dau",
    ],
    "服务台": [
        "helpdesk_cnt",
        "tenant_used_normal_helpdesks_all_cnt",
        "helpdesk_dau",
        "helpdesk_wau",
        "ticket_cnt",
        "bot_finish_rate",
    ],
}


def read_input() -> str:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).read_text()
    return sys.stdin.read()


text = read_input()
coverage = {}
for module, fields in MODULES.items():
    found = [
        field
        for field in fields
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}[\"']?\s*[:=]", text)
    ]
    minimum = len(fields) if module == "会议协同" else 3
    coverage[module] = {
        "found": found,
        "missing": [field for field in fields if field not in found],
        "valid_count": len(found),
        "minimum_required": minimum,
        "ready": len(found) >= minimum,
    }

identity_error = None
try:
    parsed = json.loads(text)
    validate_identity_ledger(parsed)
    identity_ready = True
except (json.JSONDecodeError, ResolutionError) as exc:
    identity_ready = False
    identity_error = str(exc)
ready = identity_ready and all(item["ready"] for item in coverage.values())

print(
    json.dumps(
        {
            "ok": ready,
            "identity_ready": identity_ready,
            "identity_error": identity_error,
            "coverage": coverage,
            "next_action": "generate" if ready else "supplement_or_query",
        },
        ensure_ascii=False,
        indent=2,
    )
)
sys.exit(0 if ready else 1)
