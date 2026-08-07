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

MODULE_FIELDS = [
    ("01｜统一协同底座、工作入口稳定", "#5CC8FF",
     ["im_dau", "im_dau_penetration_rate", "active_rate_7workday", "activate_rate", "active_duration_pavg_7workday"]),
    ("02｜会议内容沉淀、智能能力起步", "#4FE0CC",
     ["vc_meeting_active_duration_pavg_val", "minutes_dau_penetration_rate", "vc_ai_minutes_dau_penetration_rate"]),
    ("03｜内容持续沉淀、知识库覆盖稳定", "#9D8CFF",
     ["doc_independent_create_fcnt", "doc_view_dau_penetration_rate", "tenant_used_wiki_space_cnt", "wiki_dau", "wiki_dau_penetration_rate"]),
    ("04｜业务线上运转、自动化使用深入", "#8D7CFF",
     ["bitable_independent_create_fcnt", "base_rownum_over15000_fcnt", "bitable_automation_run", "base_dashboard_cnt", "base_dau_rate_avg_7workday"]),
    ("05｜知识检索活跃、术语资产待建", "#B99CFF",
     ["cansearch_pv_per_user", "knowledge_ai_pavg_use_cnt", "search_dau_penetration_rate", "teampedia_dau_penetration_rate", "self_build_teampedia_entity_cnt"]),
    ("06｜AI 使用形成、多维表格先行", "#75A7FF",
     ["ai_dau", "aily_dau", "aily_buddy_dau", "base_ai_dau", "miaoda_app_dau"]),
    ("07｜服务响应覆盖、机器人承担闭环", "#51D3C8",
     ["helpdesk_cnt", "helpdesk_dau", "helpdesk_wau", "ticket_cnt", "bot_finish_rate"]),
]

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
    value = data["metrics"][key]
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} 必须是数字")
    return value


def fmt(data, key):
    label, unit, digits = FIELD_SPECS[key]
    value = n(data, key)
    if digits == 0:
        number = f"{value:,.0f}"
    else:
        number = f"{value:,.{digits}f}"
    return label, f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def insights(data):
    m = data["metrics"]
    return [
        f"IM 渗透与活跃率相差 {abs(m['im_dau_penetration_rate']-m['active_rate_7workday']):.2f}pp，协同入口覆盖稳定。",
        f"智能纪要渗透高于妙记 {m['vc_ai_minutes_dau_penetration_rate']-m['minutes_dau_penetration_rate']:.2f}pp，两项覆盖均处起步阶段。",
        f"文档与 Wiki 渗透相差 {abs(m['doc_view_dau_penetration_rate']-m['wiki_dau_penetration_rate']):.2f}pp，内容消费路径接近。",
        f"多维表格渗透低于 IM {m['im_dau_penetration_rate']-m['base_dau_rate_avg_7workday']:.2f}pp，但已覆盖多数活跃用户。",
        f"搜索渗透高于词典 {m['search_dau_penetration_rate']-m['teampedia_dau_penetration_rate']:.2f}pp，自建词条仍为空白。",
        f"多维表格 AI 占 AI DAU {m['base_ai_dau']/m['ai_dau']*100:.2f}%，Aily 尚未形成日活。",
        f"DAU/WAU 为 {m['helpdesk_dau']/m['helpdesk_wau']*100:.2f}%，机器人闭环率达到 {m['bot_finish_rate']:.2f}%。",
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


def render(data, out_dir):
    validate(data)
    ins = insights(data)
    modules = []
    for idx, (title, color, fields) in enumerate(MODULE_FIELDS):
        modules.append((title, color, [(key, *fmt(data, key)) for key in fields], ins[idx]))

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 2460">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#172554"/><stop offset="1" stop-color="#06080F"/></linearGradient></defs>',
        '<rect width="1600" height="2460" fill="url(#bg)"/>',
        '<rect x="58" y="56" width="5" height="98" rx="2.5" fill="#5CC8FF"/>',
        text(82, 101, f"{data['tenant_name']} × 飞书｜最新使用快照", 34, "#F7FAFF", weight=700),
        text(82, 137, f"数据来源：C360 最新使用快照｜主租户 {data['fcode']}｜{data['suite']}", 15, "#9CAAC6"),
    ]
    centers = [205, 495, 785, 1075, 1365]
    for idx, (title, color, metrics, insight) in enumerate(modules):
        y = 190 + idx * 300
        svg += [
            f'<rect x="58" y="{y}" width="1484" height="280" rx="26" fill="#0A0E1A" stroke="#343A4B" stroke-width="2"/>',
            f'<rect x="58" y="{y}" width="5" height="280" rx="2.5" fill="{color}"/>',
            f'<g transform="translate(82 {y+28})" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{ICONS[idx]}</g>',
            text(132, y + 58, title, 24, "#F2F6FF", weight=700),
            f'<line x1="82" y1="{y+78}" x2="1518" y2="{y+78}" stroke="#20283A"/>',
        ]
        used = [350, 800, 1250] if len(metrics) == 3 else centers
        for cx, (_, label, value) in zip(used, metrics):
            svg += [text(cx, y + 123, label, 15, "#8E9AB4", "middle"), text(cx, y + 174, value, 28, "#F7FAFF", "middle", 700)]
        svg.append(text(88, y + 240, insight, 17, "#C7D9FF", weight=500))
    svg += [
        '<rect x="58" y="2290" width="1484" height="108" rx="20" fill="#10172A" stroke="#343A4B" stroke-width="2"/>',
        text(82, 2328, "数据口径", 17, "#C9D5EF", weight=700),
        text(82, 2362, "C360 最新使用快照。本次未接入 Aeolus，因此不包含近 180 天累计、日均、趋势和对比期。", 15, "#8E9AB4"),
        "</svg>",
    ]
    svg_path = out_dir / "board.svg"
    svg_path.write_text("".join(svg))

    sections = []
    for title, _, metrics, insight in modules:
        rows = "".join(f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>" for _, label, value in metrics)
        if title.startswith("06"):
            key = "miaoda_claw_dau"
            label, value = fmt(data, key)
            rows += f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        if title.startswith("07"):
            key = "tenant_used_normal_helpdesks_all_cnt"
            label, value = fmt(data, key)
            rows += f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        sections.append(f'<h2>{escape(title)}</h2><table><colgroup><col width="360"/><col width="200"/></colgroup><thead><tr><th background-color="light-gray">指标</th><th background-color="light-gray">C360 最新值</th></tr></thead><tbody>{rows}</tbody></table><p><b>客观洞见：</b>{escape(insight)}</p>')

    doc = f'''<title>{escape(data["tenant_name"])}｜飞书整体使用情况回顾｜{escape(data["review_month"])}</title>
<callout emoji="📊" background-color="light-blue" border-color="blue">
<p><b>数据口径：</b>C360 最新使用快照。本次未接入 Aeolus，因此不包含近 180 天累计、日均、趋势和对比期。</p>
<p><b>客户实体：</b>{escape(data["customer_name"])}。</p>
<p><b>回顾对象：</b>{escape(data["tenant_name"])}（{escape(data["fcode"])}），{escape(data["suite"])}。</p>
</callout>
<h1>一、飞书整体使用快照</h1>
<whiteboard type="svg" path="@board.svg"></whiteboard>
<h1>二、七模块数据回顾</h1>
{"".join(sections)}
<hr/><p><b>说明：</b>仅使用已确认的主租户 C360 快照字段。文档不包含无来源数据、对标、因果推断或销售建议。</p>'''
    (out_dir / "document.xml").write_text(doc)
    (out_dir / "manifest.json").write_text(json.dumps({"mode": "c360_snapshot", "fields": list(FIELD_SPECS), "insights": ins}, ensure_ascii=False, indent=2))
    receipt = {
        "generator": "customer-business-review/render-snapshot.py",
        "content_version": "2.7.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "c360_snapshot",
        "field_count": len(FIELD_SPECS),
        "input_sha256": hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "board_sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
        "document_sha256": hashlib.sha256((out_dir / "document.xml").read_bytes()).hexdigest(),
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
