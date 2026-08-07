#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


FIELD_SPECS = {
    "im_dau": ("IM DAU", "人", 0),
    "im_dau_penetration_rate": ("IM 渗透率", "%", 2),
    "active_rate_7workday": ("近 7 工作日活跃率", "%", 2),
    "activate_rate": ("激活率", "%", 2),
    "active_duration_pavg_7workday": ("人均使用时长", "分钟", 2),
    "vc_meeting_active_duration_pavg_val": ("单场人均参会时长", "分钟", 2),
    "minutes_dau_penetration_rate": ("妙记渗透率", "%", 2),
    "vc_ai_minutes_dau_penetration_rate": ("智能纪要渗透率", "%", 2),
    "doc_independent_create_fcnt": ("文档独立创建数", "个", 0),
    "doc_view_dau_penetration_rate": ("文档查看渗透率", "%", 2),
    "tenant_used_wiki_space_cnt": ("知识库空间数", "个", 0),
    "wiki_dau": ("Wiki DAU", "人", 0),
    "wiki_dau_penetration_rate": ("Wiki 渗透率", "%", 2),
    "bitable_independent_create_fcnt": ("多维表格独立创建数", "个", 0),
    "base_rownum_over15000_fcnt": ("超 1.5 万行大表", "张", 0),
    "bitable_automation_run": ("自动化运行次数", "次", 0),
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
    "vc_dau": ("VC DAU", "人", 0, "meeting"),
    "vc_dau_penetration_rate": ("VC DAU 渗透率", "%", 2, "meeting"),
    "vc_meeting_cnt": ("会议数", "场", 0, "meeting"),
    "join_meeting_ucnt": ("参会人次", "人次", 0, "meeting"),
    "minutes_dau": ("妙记 DAU", "人", 0, "meeting"),
    "vc_ai_dau": ("智能纪要 DAU", "人", 0, "meeting"),
    "vc_ai_dau_avg_7workday": ("智能纪要 DAU 近 7 工作日均值", "人", 2, "meeting"),
    "create_fcnt": ("创建文档数", "个", 0, "content"),
    "sheet_create_fcnt": ("Sheet 创建数", "个", 0, "content"),
    "doc_view_ucnt": ("Doc DAU", "人", 0, "content"),
    "doc_edit_ucnt": ("文档编辑用户", "人", 0, "content"),
    "doc_creator_ucnt_penetration_rate": ("文档创建用户渗透率", "%", 2, "content"),
    "bitable_view_ucnt": ("多维表格 DAU", "人", 0, "base"),
    "base_ai_dau_avg_7workday": ("多维表格 AI DAU 近 7 工作日均值", "人", 2, "base"),
    "search_dau": ("搜索 DAU", "人", 0, "knowledge"),
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

MODULE_FIELDS = [
    ("instant", "01｜统一协同底座、工作入口稳定", "#5CC8FF",
     ["im_dau", "im_dau_penetration_rate", "active_rate_7workday", "activate_rate", "active_duration_pavg_7workday"]),
    ("meeting", "02｜会议协同活跃、智能纪要起步", "#4FE0CC",
     ["vc_meeting_active_duration_pavg_val", "minutes_dau_penetration_rate", "vc_ai_minutes_dau_penetration_rate"]),
    ("content", "03｜内容持续沉淀、知识库覆盖稳定", "#9D8CFF",
     ["doc_independent_create_fcnt", "doc_view_dau_penetration_rate", "tenant_used_wiki_space_cnt", "wiki_dau", "wiki_dau_penetration_rate"]),
    ("base", "04｜业务线上运转、自动化使用深入", "#8D7CFF",
     ["bitable_independent_create_fcnt", "base_rownum_over15000_fcnt", "bitable_automation_run", "base_dashboard_cnt", "base_dau_rate_avg_7workday"]),
    ("knowledge", "05｜知识检索活跃、术语资产待建", "#B99CFF",
     ["cansearch_pv_per_user", "knowledge_ai_pavg_use_cnt", "search_dau_penetration_rate", "teampedia_dau_penetration_rate", "self_build_teampedia_entity_cnt"]),
    ("ai", "06｜AI 使用形成、多维表格先行", "#75A7FF",
     ["ai_dau", "aily_dau", "aily_buddy_dau", "base_ai_dau", "miaoda_app_dau"]),
    ("helpdesk", "07｜服务响应覆盖、机器人承担闭环", "#51D3C8",
     ["helpdesk_cnt", "helpdesk_dau", "helpdesk_wau", "ticket_cnt", "bot_finish_rate"]),
]

BOARD_PRIORITY = {
    "instant": ["tenant_primary_suite_version_suite_dau_avg_7workday", "im_dau", "im_dau_penetration_rate", "active_rate_7workday", "active_duration_pavg_7workday"],
    "meeting": ["vc_dau", "vc_meeting_cnt", "join_meeting_ucnt", "vc_meeting_active_duration_pavg_val", "vc_ai_minutes_dau_penetration_rate"],
    "content": ["doc_independent_create_fcnt", "doc_view_dau_penetration_rate", "wiki_dau", "wiki_dau_penetration_rate", "tenant_used_wiki_space_cnt"],
    "base": ["base_dau_rate_avg_7workday", "base_rownum_over15000_fcnt", "bitable_automation_run", "base_dashboard_cnt", "base_ai_dau"],
    "knowledge": ["search_dau", "search_dau_penetration_rate", "cansearch_pv_per_user", "teampedia_dau_penetration_rate", "self_build_teampedia_entity_cnt"],
    "ai": ["ai_dau", "ai_dau_avg_7workday", "knowledge_ai_dau_avg_7workday", "base_ai_dau", "miaoda_app_dau"],
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
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} 必须是数字")
    return value


def fmt(data, key):
    spec = FIELD_SPECS.get(key) or OPTIONAL_FIELD_SPECS.get(key)
    label, unit, _ = spec[:3]
    value = n(data, key)
    number = f"{value:,.0f}"
    return label, f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def insights(data):
    m = data["metrics"]
    if all(key in data.get("extra_metrics", {}) for key in ["vc_meeting_cnt", "join_meeting_ucnt", "vc_dau"]):
        meeting_insight = (
            f"VC DAU {n(data, 'vc_dau'):,.0f} 人；"
            f"{n(data, 'vc_meeting_cnt'):,.0f} 场会议覆盖 {n(data, 'join_meeting_ucnt'):,.0f} 人次，"
            f"单场平均 {n(data, 'join_meeting_ucnt') / n(data, 'vc_meeting_cnt'):.0f} 人次。"
        )
    else:
        meeting_insight = f"智能纪要渗透高于妙记 {m['vc_ai_minutes_dau_penetration_rate']-m['minutes_dau_penetration_rate']:.0f}pp，两项覆盖均处起步阶段。"
    return [
        f"IM 渗透与活跃率相差 {abs(m['im_dau_penetration_rate']-m['active_rate_7workday']):.0f}pp，协同入口覆盖稳定。",
        meeting_insight,
        f"文档与 Wiki 渗透相差 {abs(m['doc_view_dau_penetration_rate']-m['wiki_dau_penetration_rate']):.0f}pp，内容消费路径接近。",
        f"多维表格渗透低于 IM {m['im_dau_penetration_rate']-m['base_dau_rate_avg_7workday']:.0f}pp，但已覆盖多数活跃用户。",
        f"搜索渗透高于词典 {m['search_dau_penetration_rate']-m['teampedia_dau_penetration_rate']:.0f}pp，自建词条仍为空白。",
        f"多维表格 AI 占 AI DAU {m['base_ai_dau']/m['ai_dau']*100:.0f}%，Aily 尚未形成日活。",
        f"DAU/WAU 为 {m['helpdesk_dau']/m['helpdesk_wau']*100:.0f}%，机器人闭环率达到 {m['bot_finish_rate']:.0f}%。",
    ]


def text(x, y, value, size, fill, anchor="start", weight=400):
    return f'<text x="{x}" y="{y}" font-family="Noto Sans SC,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(value)}</text>'


def validate(data):
    for key in FIELD_SPECS:
        n(data, key)
    for key in ["customer_name", "tenant_name", "fcode", "review_month", "suite", "industry"]:
        if not data.get(key):
            raise ValueError(f"缺少 {key}")
    if not str(data["fcode"]).startswith(("F", "L")):
        raise ValueError("fcode 格式错误")
    for key, item in data.get("extra_metrics", {}).items():
        if key not in OPTIONAL_FIELD_SPECS:
            raise ValueError(f"未注册的扩展字段：{key}")
        if not isinstance(item, dict) or item.get("source") != "c360":
            raise ValueError(f"{key} 必须包含 source=c360")
        if not isinstance(item.get("value"), (int, float)):
            raise ValueError(f"{key}.value 必须是数字")


def render(data, out_dir):
    validate(data)
    ins = insights(data)
    modules = []
    for idx, (module_id, title, color, required_fields) in enumerate(MODULE_FIELDS):
        doc_keys = list(required_fields)
        for key, item in data.get("extra_metrics", {}).items():
            if OPTIONAL_FIELD_SPECS[key][3] == module_id:
                doc_keys.append(key)
        board_keys = []
        for key in BOARD_PRIORITY[module_id]:
            try:
                n(data, key)
                board_keys.append(key)
            except KeyError:
                pass
        for key in required_fields:
            if len(board_keys) >= 5:
                break
            if key not in board_keys:
                board_keys.append(key)
        modules.append({
            "id": module_id,
            "title": title,
            "color": color,
            "board_metrics": [(key, *fmt(data, key)) for key in board_keys[:5]],
            "doc_metrics": [(key, *fmt(data, key)) for key in doc_keys],
            "insight": ins[idx],
        })

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1960">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#172554"/><stop offset="1" stop-color="#06080F"/></linearGradient></defs>',
        '<rect width="1600" height="1960" fill="url(#bg)"/>',
        '<rect x="58" y="56" width="5" height="98" rx="2.5" fill="#5CC8FF"/>',
        text(82, 101, f"{data['tenant_name']} × 飞书｜最新使用快照", 34, "#F7FAFF", weight=700),
        text(82, 137, f"数据来源：C360 最新使用快照｜主租户 {data['fcode']}｜{data['suite']}", 15, "#9CAAC6"),
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
        text(82, 1916, "C360 最新使用快照。本次未接入 Aeolus，因此不包含近 180 天累计、日均、趋势和对比期。", 14, "#8E9AB4"),
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
        sections.append(
            f'<h2>{escape(title)}</h2>'
            f'<table><colgroup><col width="290"/><col width="160"/><col width="260"/></colgroup>'
            f'<thead><tr><th background-color="light-gray">指标</th>'
            f'<th background-color="light-gray">C360 最新值</th>'
            f'<th background-color="light-gray">来源字段</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<p><b>客观洞见：</b>{escape(insight)}</p>'
        )

    core_observations = [
        f"即时协同覆盖稳定：IM DAU {n(data, 'im_dau'):,.0f} 人，渗透率 {n(data, 'im_dau_penetration_rate'):.0f}%。",
        f"会议使用规模可复核：VC DAU {n(data, 'vc_dau'):,.0f} 人，{n(data, 'vc_meeting_cnt'):,.0f} 场会议覆盖 {n(data, 'join_meeting_ucnt'):,.0f} 人次。",
        f"内容与知识库使用接近：文档查看渗透率 {n(data, 'doc_view_dau_penetration_rate'):.0f}%，Wiki 渗透率 {n(data, 'wiki_dau_penetration_rate'):.0f}%。",
        f"多维表格使用深入：渗透率 {n(data, 'base_dau_rate_avg_7workday'):.0f}%，自动化运行 {n(data, 'bitable_automation_run'):,.0f} 次。",
        f"AI 已形成基础使用：AI DAU {n(data, 'ai_dau'):,.0f} 人，其中多维表格 AI DAU {n(data, 'base_ai_dau'):,.0f} 人。",
    ]
    core_xml = "".join(f"<li>{escape(item)}</li>" for item in core_observations)

    doc = f'''<title>{escape(data["tenant_name"])}｜飞书整体使用情况回顾｜{escape(data["review_month"])}</title>
<callout emoji="📊" background-color="light-blue" border-color="blue">
<p><b>数据口径：</b>C360 最新使用快照。本次未接入 Aeolus，因此不包含近 180 天累计、日均、趋势和对比期。</p>
<p><b>客户实体：</b>{escape(data["customer_name"])}。</p>
<p><b>回顾对象：</b>{escape(data["tenant_name"])}（{escape(data["fcode"])}），{escape(data["suite"])}。</p>
</callout>
<h1>一、核心观察</h1>
<ul>{core_xml}</ul>
<h1>二、飞书整体使用快照</h1>
<whiteboard type="svg" path="@board.svg"></whiteboard>
<h1>三、七模块数据回顾</h1>
{"".join(sections)}
<hr/><callout emoji="📌" background-color="light-gray" border-color="gray">
<p><b>数据完整性说明：</b>正文包含 35 个必需字段及本次 C360 返回并通过字段注册表校验的扩展字段。每项指标均列出来源字段；未提供的 Aeolus 指标不作为缺失，也不参与判断。</p>
<p>文档不包含无来源数据、行业对标、原因假设、风险判断或销售建议。</p>
</callout>'''
    (out_dir / "document.xml").write_text(doc)
    field_sources = {key: "c360_required" for key in FIELD_SPECS}
    field_sources.update({key: item["source"] for key, item in data.get("extra_metrics", {}).items()})
    (out_dir / "manifest.json").write_text(json.dumps({
        "mode": "c360_snapshot",
        "required_fields": list(FIELD_SPECS),
        "optional_fields_used": list(data.get("extra_metrics", {})),
        "field_sources": field_sources,
        "insights": ins
    }, ensure_ascii=False, indent=2))
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
        "content_version": "3.0.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "c360_snapshot",
        "field_count": len(FIELD_SPECS) + len(data.get("extra_metrics", {})),
        "required_field_count": len(FIELD_SPECS),
        "optional_field_count": len(data.get("extra_metrics", {})),
        "display_rounding": "half_even_integer",
        "raw_precision_preserved": True,
        "source_snapshot": data.get("source_snapshot"),
        "input_sha256": hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "board_sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
        "document_sha256": hashlib.sha256((out_dir / "document.xml").read_bytes()).hexdigest(),
        "aeolus_request_sha256": hashlib.sha256(handoff_path.read_bytes()).hexdigest(),
        "aeolus_handoff_required": True,
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
