#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identity_resolver import validate_identity_ledger


CONTENT_VERSION = "3.3.0"

FIELD_SPECS = {
    "im_dau": ("IM DAU", "人", 0),
    "im_dau_penetration_rate": ("IM 渗透率", "%", 2),
    "active_rate_7workday": ("近 7 工作日活跃率", "%", 2),
    "activate_rate": ("激活率", "%", 2),
    "active_duration_pavg_7workday": ("人均使用时长", "分钟", 2),
    "vc_dau": ("VC DAU", "人", 0),
    "vc_dau_penetration_rate": ("VC DAU 渗透率", "%", 2),
    "vc_meeting_cnt": ("会议数", "场", 0),
    "join_meeting_ucnt": ("参会人次", "人次", 0),
    "vc_meeting_active_duration_pavg_val": ("单场人均参会时长", "分钟", 2),
    "minutes_dau": ("妙记 DAU", "人", 0),
    "minutes_dau_penetration_rate": ("妙记渗透率", "%", 2),
    "vc_ai_dau": ("智能纪要 DAU", "人", 0),
    "vc_ai_minutes_dau_penetration_rate": ("智能纪要渗透率", "%", 2),
    "doc_independent_create_fcnt": ("文档独立创建数", "个", 0),
    "doc_view_dau_penetration_rate": ("文档查看渗透率", "%", 2),
    "tenant_used_wiki_space_cnt": ("知识库空间数", "个", 0),
    "wiki_dau": ("Wiki DAU", "人", 0),
    "wiki_dau_penetration_rate": ("Wiki 渗透率", "%", 2),
    "bitable_independent_create_fcnt": ("多维表格独立创建数", "个", 0),
    "base_rownum_over15000_fcnt": ("超 1.5 万行大表", "张", 0),
    "bitable_automation_run": ("自动化运行额度", "次", 0),
    "base_dashboard_cnt": ("仪表盘数", "个", 0),
    "base_dau_rate_avg_7workday": ("多维表格渗透率", "%", 2),
    "cansearch_pv_per_user": ("人均可搜文档数", "篇", 2),
    "knowledge_ai_pavg_use_cnt": ("知识问答人均使用", "次", 2),
    "search_dau_penetration_rate": ("搜索渗透率", "%", 2),
    "teampedia_dau_penetration_rate": ("词典渗透率", "%", 2),
    "self_build_teampedia_entity_cnt": ("企业自建词条", "个", 0),
    "ai_dau": ("AI DAU", "人", 0),
    "aily_dau": ("Aily 应用 DAU", "人", 0),
    "aily_buddy_dau": ("智能伙伴 DAU", "人", 0),
    "base_ai_dau": ("多维表格 AI DAU", "人", 0),
    "miaoda_app_dau": ("妙搭 DAU", "人", 0),
    "miaoda_claw_dau": ("妙搭 OpenClaw DAU", "人", 0),
    "helpdesk_cnt": ("服务台新建数量", "个", 0),
    "tenant_used_normal_helpdesks_all_cnt": ("使用中服务台总数", "个", 0),
    "helpdesk_dau": ("服务台 DAU", "人", 0),
    "helpdesk_wau": ("服务台 WAU", "人", 0),
    "ticket_cnt": ("工单数", "单", 0),
    "bot_finish_rate": ("机器人闭环率", "%", 2),
}

OPTIONAL_FIELD_SPECS = {
    "tenant_primary_suite_version_suite_dau_avg_7workday": ("主版本近 7 日均 DAU", "人", 0, "instant"),
    "active_ucnt": ("激活用户", "人", 0, "instant"),
    "send_msg_ucnt": ("发消息用户", "人", 0, "instant"),
    "msg_sender_ucnt_penetration_rate": ("发消息渗透率", "%", 2, "instant"),
    "op_app_dau": ("开放平台 DAU", "人", 0, "instant"),
    "op_app_dau_self": ("自建应用 DAU", "人", 0, "instant"),
    "vc_ai_dau_avg_7workday": ("智能纪要 DAU 近 7 工作日均值", "人", 2, "meeting"),
    "create_fcnt": ("创建文档数", "个", 0, "content"),
    "sheet_create_fcnt": ("Sheet 创建数", "个", 0, "content"),
    "doc_view_ucnt": ("Doc DAU", "人", 0, "content"),
    "doc_edit_ucnt": ("文档编辑用户", "人", 0, "content"),
    "doc_creator_ucnt_penetration_rate": ("文档创建用户渗透率", "%", 2, "content"),
    "bitable_view_ucnt": ("多维表格 DAU", "人", 0, "base"),
    "tenant_current_month_bitable_workflow_instance_cnt": ("当月自动化实际运行数", "次", 0, "base"),
    "base_ai_dau_avg_7workday": ("多维表格 AI DAU 近 7 工作日均值", "人", 2, "base"),
    "search_dau": ("搜索 DAU", "人", 0, "knowledge"),
    "knowledge_ai_dau": ("知识问答 DAU", "人", 0, "knowledge"),
    "knowledge_ai_dau_avg_7workday": ("知识问答 DAU 近 7 工作日均值", "人", 2, "knowledge"),
    "knowledge_ai_use_cnt": ("知识问答使用次数", "次", 0, "knowledge"),
    "teampedia_dau": ("词典 DAU", "人", 0, "knowledge"),
    "ai_dau_avg_7workday": ("AI DAU 近 7 工作日均值", "人", 2, "ai"),
    "ai_credits_asset_usage": ("AI 通用额度当日消耗", "点", 0, "ai"),
    "ai_credits_asset_usage_knowledge": ("知识问答额度消耗", "点", 0, "ai"),
    "ai_arpu": ("AI ARPU", "元/人", 2, "ai"),
    "aily_buddy_sum_messages": ("智能伙伴消息数", "条", 0, "ai"),
    "artificial_ticket_cnt": ("人工工单数", "单", 0, "helpdesk"),
    "helpdesk_faq_cnt": ("服务台 FAQ", "条", 0, "helpdesk"),
}

AEOLUS_FIELD_SPECS = {
    "meeting_duration_per_capita": ("人均会议时长", "分钟", "meeting"),
    "doc_create_fcnt_180d": ("文档创建数", "个", "content"),
    "bitable_create_total_180d": ("创建多维表格总数", "个", "base"),
    "bitable_automation_run_total_180d": ("多维表格自动化运行数", "次", "base"),
    "bitable_dashboard_create_total_180d": ("多维表格仪表盘创建数", "个", "base"),
    "helpdesk_total_180d": ("服务台数量", "个", "helpdesk"),
    "ticket_cumulative_total_180d": ("累计工单数", "单", "helpdesk"),
    "bot_interception_rate_avg_180d": ("平均机器人拦截率", "%", "helpdesk"),
    "wiki_space_total_180d": ("知识库总空间数", "个", "knowledge"),
    "wiki_visit_total_180d": ("总访问次数", "次", "knowledge"),
}

AEOLUS_BOARD_PRIORITY = {
    "meeting": ["meeting_duration_per_capita"],
    "content": ["doc_create_fcnt_180d"],
    "base": [
        "bitable_create_total_180d",
        "bitable_automation_run_total_180d",
        "bitable_dashboard_create_total_180d",
    ],
    "knowledge": ["wiki_space_total_180d", "wiki_visit_total_180d"],
    "helpdesk": [
        "helpdesk_total_180d",
        "ticket_cumulative_total_180d",
        "bot_interception_rate_avg_180d",
    ],
}

# 正式 BR 的 19 项指标合同。每个展示名只绑定一个独立源字段，禁止相近替代。
FORMAL_C360_SPECS = {
    "active_rate_7workday": ("活跃率", "%", "instant"),
    "active_duration_pavg_7workday": ("人均使用时长", "分钟", "instant"),
    "knowledge_ai_dau": ("知识问答 DAU", "人", "knowledge"),
    "cansearch_pv_per_user": ("知识问答人均可搜文档数", "篇", "knowledge"),
    "vc_ai_minutes_dau_penetration_rate": ("智能纪要渗透率", "%", "meeting"),
    "aily_buddy_dau": ("飞书 aily 智能伙伴 DAU", "人", "ai"),
    "base_ai_dau": ("多维表格 AI DAU", "人", "ai"),
    "base_dau_rate_avg_7workday": ("多维表格 DAU 渗透率", "%", "base"),
    "base_rownum_over15000_fcnt": ("单表超过 15,000 行的表格总数", "张", "base"),
}

FORMAL_BOARD_PRIORITY = {
    "instant": [("c360", "active_rate_7workday"), ("c360", "active_duration_pavg_7workday")],
    "meeting": [("aeolus", "meeting_duration_per_capita"), ("c360", "vc_ai_minutes_dau_penetration_rate")],
    "content": [("aeolus", "doc_create_fcnt_180d")],
    "base": [
        ("aeolus", "bitable_create_total_180d"),
        ("aeolus", "bitable_automation_run_total_180d"),
        ("aeolus", "bitable_dashboard_create_total_180d"),
        ("c360", "base_dau_rate_avg_7workday"),
        ("c360", "base_rownum_over15000_fcnt"),
    ],
    "knowledge": [
        ("aeolus", "wiki_space_total_180d"),
        ("aeolus", "wiki_visit_total_180d"),
        ("c360", "knowledge_ai_dau"),
        ("c360", "cansearch_pv_per_user"),
    ],
    "ai": [("c360", "aily_buddy_dau"), ("c360", "base_ai_dau")],
    "helpdesk": [
        ("aeolus", "helpdesk_total_180d"),
        ("aeolus", "ticket_cumulative_total_180d"),
        ("aeolus", "bot_interception_rate_avg_180d"),
    ],
}

MODULE_FIELDS = [
    ("instant", "01｜即时协同覆盖与活跃", "#5CC8FF",
     ["im_dau", "im_dau_penetration_rate", "active_rate_7workday", "activate_rate", "active_duration_pavg_7workday"]),
    ("meeting", "02｜会议协同规模与纪要覆盖", "#4FE0CC",
     ["vc_dau", "vc_dau_penetration_rate", "vc_meeting_cnt", "join_meeting_ucnt",
      "vc_meeting_active_duration_pavg_val", "minutes_dau", "minutes_dau_penetration_rate",
      "vc_ai_dau", "vc_ai_minutes_dau_penetration_rate"]),
    ("content", "03｜内容创建与知识库使用", "#9D8CFF",
     ["doc_independent_create_fcnt", "doc_view_dau_penetration_rate", "tenant_used_wiki_space_cnt", "wiki_dau", "wiki_dau_penetration_rate"]),
    ("base", "04｜多维表格使用与自动化", "#8D7CFF",
     ["bitable_independent_create_fcnt", "base_rownum_over15000_fcnt", "bitable_automation_run", "base_dashboard_cnt", "base_dau_rate_avg_7workday"]),
    ("knowledge", "05｜知识检索与词典使用", "#B99CFF",
     ["cansearch_pv_per_user", "knowledge_ai_pavg_use_cnt", "search_dau_penetration_rate", "teampedia_dau_penetration_rate", "self_build_teampedia_entity_cnt"]),
    ("ai", "06｜AI 使用与产品分布", "#75A7FF",
     ["ai_dau", "aily_dau", "aily_buddy_dau", "base_ai_dau", "miaoda_app_dau"]),
    ("helpdesk", "07｜服务台使用与闭环", "#51D3C8",
     ["helpdesk_cnt", "helpdesk_dau", "helpdesk_wau", "ticket_cnt", "bot_finish_rate"]),
]

BOARD_PRIORITY = {
    "instant": ["tenant_primary_suite_version_suite_dau_avg_7workday", "im_dau", "im_dau_penetration_rate", "active_rate_7workday", "active_duration_pavg_7workday"],
    "meeting": ["vc_dau", "vc_meeting_cnt", "join_meeting_ucnt", "vc_meeting_active_duration_pavg_val", "vc_ai_minutes_dau_penetration_rate"],
    "content": ["create_fcnt", "doc_independent_create_fcnt", "doc_view_dau_penetration_rate", "wiki_dau", "wiki_dau_penetration_rate"],
    "base": ["tenant_current_month_bitable_workflow_instance_cnt", "base_dau_rate_avg_7workday", "base_rownum_over15000_fcnt", "base_dashboard_cnt", "base_ai_dau"],
    "knowledge": ["knowledge_ai_dau", "search_dau", "search_dau_penetration_rate", "cansearch_pv_per_user", "teampedia_dau_penetration_rate"],
    "ai": ["ai_dau", "ai_dau_avg_7workday", "base_ai_dau", "miaoda_app_dau"],
    "helpdesk": ["helpdesk_cnt", "helpdesk_wau", "helpdesk_dau", "ticket_cnt", "bot_finish_rate"],
}

ICONS = [
    '<circle cx="19" cy="10" r="5"/><circle cx="8" cy="20" r="4"/><circle cx="30" cy="20" r="4"/><line x1="10" y1="34" x2="14" y2="26"/><line x1="14" y1="26" x2="24" y2="26"/><line x1="24" y1="26" x2="28" y2="34"/><line x1="2" y1="34" x2="4" y2="27"/><line x1="36" y1="34" x2="34" y2="27"/>',
    '<rect x="3" y="8" width="30" height="24" rx="4"/><line x1="10" y1="3" x2="10" y2="13"/><line x1="26" y1="3" x2="26" y2="13"/><line x1="10" y1="20" x2="26" y2="20"/><line x1="10" y1="26" x2="20" y2="26"/>',
    '<rect x="8" y="3" width="23" height="32" rx="2"/><line x1="13" y1="13" x2="26" y2="13"/><line x1="13" y1="19" x2="26" y2="19"/><line x1="13" y1="25" x2="26" y2="25"/><line x1="13" y1="31" x2="22" y2="31"/>',
    '<rect x="3" y="3" width="32" height="32" rx="4"/><line x1="3" y1="14" x2="35" y2="14"/><line x1="3" y1="25" x2="35" y2="25"/><line x1="14" y1="3" x2="14" y2="35"/><line x1="25" y1="3" x2="25" y2="35"/>',
    '<rect x="3" y="5" width="15" height="30" rx="3"/><rect x="20" y="5" width="15" height="30" rx="3"/><line x1="19" y1="7" x2="19" y2="35"/><line x1="7" y1="12" x2="14" y2="12"/><line x1="24" y1="12" x2="31" y2="12"/>',
    '<circle cx="19" cy="15" r="4"/><line x1="19" y1="2" x2="19" y2="9"/><line x1="19" y1="21" x2="19" y2="28"/><line x1="6" y1="15" x2="13" y2="15"/><line x1="25" y1="15" x2="32" y2="15"/><circle cx="31" cy="32" r="3"/><line x1="31" y1="25" x2="31" y2="28"/><line x1="31" y1="36" x2="31" y2="39"/><line x1="24" y1="32" x2="27" y2="32"/><line x1="35" y1="32" x2="38" y2="32"/>',
    '<circle cx="19" cy="18" r="14"/><rect x="2" y="18" width="8" height="13" rx="3"/><rect x="28" y="18" width="8" height="13" rx="3"/><line x1="28" y1="32" x2="24" y2="36"/><line x1="24" y1="36" x2="15" y2="36"/>',
]


def n(data, key):
    if key in data["metrics"]:
        value = data["metrics"][key]
    else:
        extra = data.get("extra_metrics", {}).get(key)
        if not extra:
            raise KeyError(key)
        if extra.get("source") != "c360":
            raise ValueError(f"{key} 的来源必须是 c360")
        value = extra.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} 必须是有限 JSON 数字")
    return value


def aeolus_value(data, key, period="current"):
    item = data["aeolus_snapshot"]["metrics"][key]
    value = item.get(period)
    if value is None and period == "comparison":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"aeolus_snapshot.metrics.{key}.{period} 必须是有限 JSON 数字")
    return value


def rounded_integer(value):
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def display_number(value):
    return f"{rounded_integer(value):,}"


def safe_percent(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator * 100


def relation(left_label, left, right_label, right):
    delta = left - right
    rounded = abs(rounded_integer(delta))
    if rounded == 0:
        return f"{left_label}与{right_label}展示值持平"
    direction = "高于" if delta > 0 else "低于"
    return f"{left_label}{direction}{right_label} {rounded}pp"


def canonical_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def fmt(data, key):
    spec = FIELD_SPECS.get(key) or OPTIONAL_FIELD_SPECS.get(key)
    label, unit, _ = spec[:3]
    value = n(data, key)
    number = display_number(value)
    return label, f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def fmt_aeolus(data, key, period="current"):
    label, unit, _ = AEOLUS_FIELD_SPECS[key]
    value = aeolus_value(data, key, period)
    if value is None:
        return label, "—"
    return label, f"{display_number(value)} {unit}"


def fmt_formal_c360(data, key):
    label, unit, _ = FORMAL_C360_SPECS[key]
    value = n(data, key)
    number = display_number(value)
    return label, f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def formal_contract_status(data):
    c360_missing = []
    for key in FORMAL_C360_SPECS:
        try:
            n(data, key)
        except (KeyError, TypeError, ValueError):
            c360_missing.append(key)
    aeolus_metrics = data.get("aeolus_snapshot", {}).get("metrics", {})
    aeolus_missing = [key for key in AEOLUS_FIELD_SPECS if key not in aeolus_metrics]
    return {
        "ready": not c360_missing and not aeolus_missing,
        "c360_missing": c360_missing,
        "aeolus_missing": aeolus_missing,
    }


def insights(data):
    m = data["metrics"]
    attendees_per_meeting = (
        n(data, "join_meeting_ucnt") / n(data, "vc_meeting_cnt")
        if n(data, "vc_meeting_cnt") > 0
        else None
    )
    if attendees_per_meeting is not None:
        meeting_insight = (
            f"会议参与规模与场次形成可复核关系，单场平均 "
            f"{display_number(attendees_per_meeting)} 人次；"
            f"{relation('智能纪要渗透', m['vc_ai_minutes_dau_penetration_rate'], '妙记渗透', m['minutes_dau_penetration_rate'])}。"
        )
    else:
        meeting_insight = (
            "会议数为 0，无法计算单场参会人次；"
            f"{relation('智能纪要渗透', m['vc_ai_minutes_dau_penetration_rate'], '妙记渗透', m['minutes_dau_penetration_rate'])}。"
        )
    ai_share = safe_percent(m["base_ai_dau"], m["ai_dau"])
    ai_insight = (
        f"多维表格 AI 占 AI DAU {display_number(ai_share)}%，AI 使用集中于多维表格。"
        if ai_share is not None
        else "AI DAU 为 0，无法计算多维表格 AI 占比，不作集中度判断。"
    )
    helpdesk_stickiness = safe_percent(m["helpdesk_dau"], m["helpdesk_wau"])
    helpdesk_insight = (
        f"服务台 DAU/WAU 为 {display_number(helpdesk_stickiness)}%，"
        f"机器人闭环率为 {display_number(m['bot_finish_rate'])}%，反映日常使用粘性与自动闭环结构。"
        if helpdesk_stickiness is not None
        else f"服务台 WAU 为 0，无法计算 DAU/WAU；机器人闭环率为 {display_number(m['bot_finish_rate'])}%。"
    )
    base_relation = relation(
        "多维表格渗透", m["base_dau_rate_avg_7workday"],
        "IM 渗透", m["im_dau_penetration_rate"]
    )
    teampedia_suffix = (
        "，自建词条尚未形成供给。"
        if m["self_build_teampedia_entity_cnt"] == 0
        else f"，已有 {display_number(m['self_build_teampedia_entity_cnt'])} 个自建词条形成供给。"
    )
    return [
        f"{relation('IM 渗透', m['im_dau_penetration_rate'], '近 7 工作日活跃率', m['active_rate_7workday'])}，呈现协同入口覆盖与持续活跃的差距。",
        meeting_insight,
        f"{relation('文档查看渗透', m['doc_view_dau_penetration_rate'], 'Wiki 渗透', m['wiki_dau_penetration_rate'])}，反映两类内容消费路径的覆盖差异。",
        f"{base_relation}，反映业务应用与基础协同入口的覆盖差距。",
        f"{relation('搜索渗透', m['search_dau_penetration_rate'], '词典渗透', m['teampedia_dau_penetration_rate'])}{teampedia_suffix}",
        ai_insight,
        helpdesk_insight,
    ]


def text(x, y, value, size, fill, anchor="start", weight=400):
    return f'<text x="{x}" y="{y}" font-family="Noto Sans SC,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(value)}</text>'


def validate(data):
    validate_identity_ledger(data)
    for key in FIELD_SPECS:
        n(data, key)
        if FIELD_SPECS[key][1] == "%" and not 0 <= n(data, key) <= 100:
            raise ValueError(f"{key} 必须使用 0_to_100 百分比口径")
    for key in ["customer_name", "tenant_name", "fcode", "review_month", "suite", "industry"]:
        if not data.get(key):
            raise ValueError(f"缺少 {key}")
    if not str(data["fcode"]).startswith(("F", "L")):
        raise ValueError("fcode 格式错误")
    if data.get("percent_scale") != "0_to_100":
        raise ValueError("percent_scale 必须明确为 0_to_100")
    source_snapshot = data.get("source_snapshot")
    if not isinstance(source_snapshot, dict):
        raise ValueError("缺少 source_snapshot")
    for key in ("queried_at", "fcode", "normalized_response_sha256"):
        if not source_snapshot.get(key):
            raise ValueError(f"source_snapshot 缺少 {key}")
    if source_snapshot["fcode"] != data["fcode"]:
        raise ValueError("source_snapshot.fcode 与主租户 F 码不一致")
    if not isinstance(source_snapshot["normalized_response_sha256"], str) or len(
        source_snapshot["normalized_response_sha256"]
    ) != 64 or any(c not in "0123456789abcdefABCDEF" for c in source_snapshot["normalized_response_sha256"]):
        raise ValueError("source_snapshot.normalized_response_sha256 必须是 64 位 SHA256")
    for key, item in data.get("extra_metrics", {}).items():
        if key not in OPTIONAL_FIELD_SPECS:
            raise ValueError(f"未注册的扩展字段：{key}")
        if not isinstance(item, dict) or item.get("source") != "c360":
            raise ValueError(f"{key} 必须包含 source=c360")
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key}.value 必须是有限 JSON 数字")
        if OPTIONAL_FIELD_SPECS[key][1] == "%" and not 0 <= value <= 100:
            raise ValueError(f"{key}.value 必须使用 0_to_100 百分比口径")
    aeolus = data.get("aeolus_snapshot")
    if aeolus is None:
        return
    if not isinstance(aeolus, dict):
        raise ValueError("aeolus_snapshot 必须是对象")
    if aeolus.get("fcode") != data["fcode"]:
        raise ValueError("aeolus_snapshot.fcode 与主租户 F 码不一致")
    source_sha = aeolus.get("source_sha256")
    if not isinstance(source_sha, str) or len(source_sha) != 64 or any(
        c not in "0123456789abcdefABCDEF" for c in source_sha
    ):
        raise ValueError("aeolus_snapshot.source_sha256 必须是 64 位 SHA256")

    periods = {}
    for period_name in ("current_period",):
        period = aeolus.get(period_name)
        if not isinstance(period, dict):
            raise ValueError(f"aeolus_snapshot 缺少 {period_name}")
        try:
            start = date.fromisoformat(period["start_date"])
            end = date.fromisoformat(period["end_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{period_name} 日期必须为 YYYY-MM-DD") from exc
        if end - start != timedelta(days=179):
            raise ValueError(f"{period_name} 必须是连续 180 天")
        periods[period_name] = (start, end)
    comparison_period = aeolus.get("comparison_period")
    if comparison_period is not None:
        if not isinstance(comparison_period, dict):
            raise ValueError("comparison_period 日期必须为 YYYY-MM-DD")
        try:
            comparison_start = date.fromisoformat(comparison_period["start_date"])
            comparison_end = date.fromisoformat(comparison_period["end_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("comparison_period 日期必须为 YYYY-MM-DD") from exc
        if comparison_end - comparison_start != timedelta(days=179):
            raise ValueError("comparison_period 必须是连续 180 天")
        if comparison_end + timedelta(days=1) != periods["current_period"][0]:
            raise ValueError("Aeolus 对比期必须紧邻当前期之前")

    metrics = aeolus.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("aeolus_snapshot.metrics 不能为空")
    unknown = set(metrics) - set(AEOLUS_FIELD_SPECS)
    if unknown:
        raise ValueError(f"Aeolus 指标不在 allowlist：{sorted(unknown)}")
    for key, item in metrics.items():
        if not isinstance(item, dict) or "current" not in item:
            raise ValueError(f"aeolus_snapshot.metrics.{key} 缺少 current")
        current_value = aeolus_value(data, key, "current")
        if AEOLUS_FIELD_SPECS[key][1] == "%" and not 0 <= current_value <= 100:
            raise ValueError(f"aeolus_snapshot.metrics.{key}.current 必须使用 0_to_100 百分比口径")
        if "comparison" in item and item["comparison"] is not None:
            if comparison_period is None:
                raise ValueError(f"aeolus_snapshot.metrics.{key}.comparison 需要 comparison_period")
            comparison_value = aeolus_value(data, key, "comparison")
            if AEOLUS_FIELD_SPECS[key][1] == "%" and not 0 <= comparison_value <= 100:
                raise ValueError(f"aeolus_snapshot.metrics.{key}.comparison 必须使用 0_to_100 百分比口径")


def render(data, out_dir):
    validate(data)
    enhanced = "aeolus_snapshot" in data
    formal_contract = formal_contract_status(data)
    formal = formal_contract["ready"]
    ins = insights(data)
    modules = []
    for idx, (module_id, title, color, required_fields) in enumerate(MODULE_FIELDS):
        doc_keys = list(required_fields)
        for key, item in data.get("extra_metrics", {}).items():
            if OPTIONAL_FIELD_SPECS[key][3] == module_id:
                doc_keys.append(key)
        board_metrics = []
        if formal:
            for source, key in FORMAL_BOARD_PRIORITY[module_id]:
                if source == "aeolus":
                    board_metrics.append((f"aeolus:{key}", *fmt_aeolus(data, key)))
                else:
                    board_metrics.append((f"c360:{key}", *fmt_formal_c360(data, key)))
        elif enhanced:
            for key in AEOLUS_BOARD_PRIORITY.get(module_id, []):
                if key in data["aeolus_snapshot"]["metrics"]:
                    label, value = fmt_aeolus(data, key)
                    board_metrics.append((f"aeolus:{key}", label, value))
        for key in BOARD_PRIORITY[module_id] if not formal else []:
            if len(board_metrics) >= 5:
                break
            try:
                n(data, key)
                if not any(item[0] == key for item in board_metrics):
                    board_metrics.append((key, *fmt(data, key)))
            except KeyError:
                pass
        for key in required_fields if not formal else []:
            if len(board_metrics) >= 5:
                break
            if not any(item[0] == key for item in board_metrics):
                board_metrics.append((key, *fmt(data, key)))
        modules.append({
            "id": module_id,
            "title": title,
            "color": color,
            "board_metrics": board_metrics[:5],
            "doc_metrics": [(key, *fmt(data, key)) for key in doc_keys],
            "insight": ins[idx],
        })

    if formal:
        mode_label = "C360 + Aeolus 近 180 天正式 BR"
    elif enhanced:
        mode_label = "C360 + Aeolus 数据不完整草稿"
    else:
        mode_label = "C360-only 草稿"
    if enhanced:
        current_period = data["aeolus_snapshot"]["current_period"]
        comparison_period = data["aeolus_snapshot"].get("comparison_period")
        if comparison_period:
            period_note = (
                f"Aeolus 当前期 {current_period['start_date']} 至 {current_period['end_date']}；"
                f"对比期 {comparison_period['start_date']} 至 {comparison_period['end_date']}。"
            )
        else:
            period_note = (
                f"Aeolus 当前期 {current_period['start_date']} 至 {current_period['end_date']}；"
                "未提供对比期。"
            )
    else:
        period_note = "C360 最新使用快照，不包含近 180 天累计、日均、趋势和对比期。"

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1960">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#172554"/><stop offset="1" stop-color="#06080F"/></linearGradient></defs>',
        '<rect width="1600" height="1960" fill="url(#bg)"/>',
        '<rect x="58" y="56" width="5" height="98" rx="2.5" fill="#5CC8FF"/>',
        text(82, 101, f"{data['tenant_name']} × 飞书｜{'正式 BR' if formal else 'BR 草稿'}", 34, "#F7FAFF", weight=700),
        text(82, 137, f"数据来源：{mode_label}｜主租户 {data['fcode']}｜{data['suite']}", 15, "#9CAAC6"),
    ]
    centers = [205, 495, 785, 1075, 1365]
    for idx, module in enumerate(modules):
        title, color, metrics = module["title"], module["color"], module["board_metrics"]
        y = 190 + idx * 238
        svg += [
            f'<rect x="58" y="{y}" width="1484" height="220" rx="26" fill="#0A0E1A" stroke="#343A4B" stroke-width="2"/>',
            f'<rect x="58" y="{y}" width="5" height="220" rx="2.5" fill="{color}"/>',
            f'<g transform="translate(82 {y+28})" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{ICONS[idx]}</g>',
            text(132, y + 58, title, 24, "#F2F6FF", weight=700),
            f'<line x1="82" y1="{y+78}" x2="1518" y2="{y+78}" stroke="#20283A"/>',
        ]
        used = [350, 800, 1250] if len(metrics) == 3 else centers
        for cx, (_, label, value) in zip(used, metrics):
            svg += [text(cx, y + 123, label, 15, "#8E9AB4", "middle"), text(cx, y + 174, value, 28, "#F7FAFF", "middle", 700)]
    svg += [
        '<rect x="58" y="1860" width="1484" height="74" rx="20" fill="#10172A" stroke="#343A4B" stroke-width="2"/>',
        text(82, 1889, "数据口径", 16, "#C9D5EF", weight=700),
        text(82, 1916, period_note, 14, "#8E9AB4"),
        "</svg>",
    ]
    svg_path = out_dir / "board.svg"
    svg_path.write_text("".join(svg))

    sections = []
    for module in modules:
        title, metrics, insight = module["title"], module["doc_metrics"], module["insight"]
        rows = "".join(
            f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td><td><code>{escape(key)}</code></td></tr>"
            for key, label, value in metrics
        )
        if title.startswith("06"):
            key = "miaoda_claw_dau"
            label, value = fmt(data, key)
            rows += f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td><td><code>{key}</code></td></tr>"
        if title.startswith("07"):
            key = "tenant_used_normal_helpdesks_all_cnt"
            label, value = fmt(data, key)
            rows += f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td><td><code>{key}</code></td></tr>"
        aeolus_rows = ""
        if enhanced:
            module_aeolus = [
                key for key, spec in AEOLUS_FIELD_SPECS.items()
                if spec[2] == module["id"] and key in data["aeolus_snapshot"]["metrics"]
            ]
            if module_aeolus:
                has_comparison = bool(data["aeolus_snapshot"].get("comparison_period"))
                if has_comparison:
                    enhanced_rows = "".join(
                        f"<tr><td>{escape(fmt_aeolus(data, key)[0])}</td>"
                        f"<td><b>{escape(fmt_aeolus(data, key, 'current')[1])}</b></td>"
                        f"<td><b>{escape(fmt_aeolus(data, key, 'comparison')[1])}</b></td>"
                        f"<td><code>{escape(key)}</code></td></tr>"
                        for key in module_aeolus
                    )
                    aeolus_rows = (
                        "<h3>Aeolus 近 180 天增强指标</h3>"
                        '<table><colgroup><col width="260"/><col width="150"/>'
                        '<col width="150"/><col width="260"/></colgroup>'
                        "<thead><tr><th>指标</th><th>当前期</th><th>对比期</th>"
                        f"<th>来源字段</th></tr></thead><tbody>{enhanced_rows}</tbody></table>"
                    )
                else:
                    enhanced_rows = "".join(
                        f"<tr><td>{escape(fmt_aeolus(data, key)[0])}</td>"
                        f"<td><b>{escape(fmt_aeolus(data, key, 'current')[1])}</b></td>"
                        f"<td><code>{escape(key)}</code></td></tr>"
                        for key in module_aeolus
                    )
                    aeolus_rows = (
                        "<h3>Aeolus 近 180 天增强指标</h3>"
                        "<p><b>对比说明：</b>未提供对比期。</p>"
                        '<table><colgroup><col width="300"/><col width="170"/>'
                        '<col width="300"/></colgroup>'
                        "<thead><tr><th>指标</th><th>当前期</th>"
                        f"<th>来源字段</th></tr></thead><tbody>{enhanced_rows}</tbody></table>"
                    )
        sections.append(
            f'<h2>{escape(title)}</h2>'
            f'<table><colgroup><col width="290"/><col width="160"/><col width="260"/></colgroup>'
            f'<thead><tr><th background-color="light-gray">指标</th>'
            f'<th background-color="light-gray">C360 最新值</th>'
            f'<th background-color="light-gray">来源字段</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'{aeolus_rows}'
            f'<p><b>客观洞见：</b>{escape(insight)}</p>'
        )

    core_observations = [
        f"即时协同：IM DAU {display_number(n(data, 'im_dau'))} 人，渗透率 {display_number(n(data, 'im_dau_penetration_rate'))}%。",
        f"会议协同：VC DAU {display_number(n(data, 'vc_dau'))} 人，{display_number(n(data, 'vc_meeting_cnt'))} 场会议对应 {display_number(n(data, 'join_meeting_ucnt'))} 人次。",
        f"内容沉淀：文档查看渗透率 {display_number(n(data, 'doc_view_dau_penetration_rate'))}%，Wiki 渗透率 {display_number(n(data, 'wiki_dau_penetration_rate'))}%。",
        (
            f"多维表格：当月自动化实际运行数 {display_number(n(data, 'tenant_current_month_bitable_workflow_instance_cnt'))} 次，"
            f"渗透率 {display_number(n(data, 'base_dau_rate_avg_7workday'))}%。"
            if "tenant_current_month_bitable_workflow_instance_cnt" in data.get("extra_metrics", {})
            else f"多维表格：渗透率 {display_number(n(data, 'base_dau_rate_avg_7workday'))}%。"
        ),
        f"AI 赋能：AI DAU {display_number(n(data, 'ai_dau'))} 人，其中多维表格 AI DAU {display_number(n(data, 'base_ai_dau'))} 人。",
    ]
    core_xml = "".join(f"<li>{escape(item)}</li>" for item in core_observations)
    formal_contract_xml = ""
    if formal:
        formal_rows = []
        for key, (label, _, _) in AEOLUS_FIELD_SPECS.items():
            _, value = fmt_aeolus(data, key)
            formal_rows.append(
                f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td>"
                f"<td>Aeolus</td><td><code>{escape(key)}</code></td></tr>"
            )
        for key, (label, _, _) in FORMAL_C360_SPECS.items():
            _, value = fmt_formal_c360(data, key)
            formal_rows.append(
                f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td>"
                f"<td>C360</td><td><code>{escape(key)}</code></td></tr>"
            )
        formal_contract_xml = (
            "<h1>三、正式 BR 19 项指标</h1>"
            "<table><colgroup><col width=\"310\"/><col width=\"160\"/>"
            "<col width=\"100\"/><col width=\"300\"/></colgroup>"
            "<thead><tr><th>指标</th><th>展示值</th><th>数据源</th><th>独立来源字段</th></tr></thead>"
            f"<tbody>{''.join(formal_rows)}</tbody></table>"
        )

    doc = f'''<title>{escape(data["tenant_name"])}｜飞书整体使用情况回顾｜{escape(data["review_month"])}</title>
<callout emoji="📊" background-color="light-blue" border-color="blue">
<p><b>数据口径：</b>{escape(mode_label)}。{escape(period_note)}</p>
<p><b>交付状态：</b>{"正式 BR" if formal else "草稿；Aeolus 十项未完整前不得作为正式 BR 交付"}。</p>
<p><b>客户实体：</b>{escape(data["customer_name"])}。</p>
<p><b>回顾对象：</b>{escape(data["tenant_name"])}（{escape(data["fcode"])}），{escape(data["suite"])}。</p>
</callout>
<h1>一、核心观察</h1>
<ul>{core_xml}</ul>
<h1>二、飞书整体使用快照</h1>
<whiteboard type="svg" path="@board.svg"></whiteboard>
{formal_contract_xml}
<h1>{"四" if formal else "三"}、七模块数据回顾</h1>
{"".join(sections)}
<hr/><callout emoji="📌" background-color="light-gray" border-color="gray">
<p><b>数据完整性说明：</b>正文包含 {len(FIELD_SPECS)} 个必需字段（会议九项完整）及本次通过字段注册表校验的扩展字段。每项指标均列出来源字段。</p>
<p>文档不包含无来源数据、行业对标、原因假设、风险判断或销售建议。</p>
</callout>'''
    (out_dir / "document.xml").write_text(doc)
    field_sources = {key: "c360_required" for key in FIELD_SPECS}
    field_sources.update({key: item["source"] for key, item in data.get("extra_metrics", {}).items()})
    (out_dir / "manifest.json").write_text(json.dumps({
        "mode": "formal_br" if formal else "draft",
        "formal_contract": formal_contract,
        "formal_metric_count": 19 if formal else 0,
        "formal_board_metric_count": sum(len(module["board_metrics"]) for module in modules) if formal else 0,
        "account_id": data["identity_ledger"]["resolved_account"]["account_id"],
        "tenant_id": data["identity_ledger"]["main_tenant"]["tenant_id"],
        "required_fields": list(FIELD_SPECS),
        "optional_fields_used": list(data.get("extra_metrics", {})),
        "field_sources": field_sources,
        "aeolus_fields_used": list(data.get("aeolus_snapshot", {}).get("metrics", {})),
        "aeolus_comparison_available": bool(data.get("aeolus_snapshot", {}).get("comparison_period")),
        "aeolus_source_sha256": data.get("aeolus_snapshot", {}).get("source_sha256", "").lower() or None,
        "insights": ins
    }, ensure_ascii=False, indent=2))
    handoff_path = None
    if not enhanced:
        aeolus_request = f"""当前 Aily 环境无法直接访问 Aeolus，我已先生成 C360 最新使用快照版。

如果你希望升级为近 180 天增强版，请在可访问 ByteDance 内网的浏览器打开：
https://data.bytedance.net/aeolus/pages/dashboard/1014743?appId=1161&sheetId=1247624

查询条件：主租户 F 码 {data['fcode']}
- 当前期：以看板最近可用数据日为结束日，向前连续 180 天
- 对比期：紧邻当前期之前的连续 180 天

请将 CSV、XLSX、完整截图或两期指标表发给我。收到后我会校验 F 码与日期口径，并升级现有文档和画板。若暂不提供，当前 C360 快照版仍可正常使用。"""
        handoff_path = out_dir / "aeolus-request.txt"
        handoff_path.write_text(aeolus_request)
    receipt = {
        "generator": "customer-business-review/render-snapshot.py",
        "content_version": CONTENT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "formal_br" if formal else "draft",
        "formal_status": "ready" if formal else "draft_only",
        "formal_contract": formal_contract,
        "field_count": len(set(data.get("metrics", {})) | set(data.get("extra_metrics", {}))),
        "required_field_count": len(FIELD_SPECS),
        "optional_field_count": len(set(data.get("extra_metrics", {})) - set(FIELD_SPECS)),
        "display_rounding": "ROUND_HALF_UP_integer",
        "raw_precision_preserved": True,
        "source_snapshot": data.get("source_snapshot"),
        "identity_ledger_sha256": canonical_sha256(data["identity_ledger"]),
        "input_sha256": canonical_sha256(data),
        "source_sha256": data["source_snapshot"]["normalized_response_sha256"].lower(),
        "board_sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
        "document_sha256": hashlib.sha256((out_dir / "document.xml").read_bytes()).hexdigest(),
        "aeolus_source_sha256": data.get("aeolus_snapshot", {}).get("source_sha256", "").lower() or None,
        "aeolus_request_sha256": hashlib.sha256(handoff_path.read_bytes()).hexdigest() if handoff_path else None,
        "aeolus_handoff_required": not enhanced,
        "local_audit": "pending",
        "remote_audit": "pending"
    }
    (out_dir / "delivery-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    render(data, out_dir)
    print(json.dumps({"ok": True, "out_dir": str(out_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
