#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identity_resolver import ResolutionError, validate_identity_ledger


BANNED_WORDS = [
    "同构", "抓手", "潜力", "提升空间", "一家独大", "最后一公里",
    "续约", "增购", "重度办公", "已替代", "原因是",
]

CONTENT_VERSION = "3.2.0"

MEETING_REQUIRED = [
    "vc_dau",
    "vc_dau_penetration_rate",
    "vc_meeting_cnt",
    "join_meeting_ucnt",
    "vc_meeting_active_duration_pavg_val",
    "minutes_dau",
    "minutes_dau_penetration_rate",
    "vc_ai_dau",
    "vc_ai_minutes_dau_penetration_rate",
]

AEOLUS_ALLOWLIST = {
    "doc_create_fcnt",
    "bitable_create_fcnt",
    "automation_run_cnt",
    "base_dashboard_cnt",
    "wiki_total_visit_cnt",
    "vc_meeting_cnt",
    "join_meeting_ucnt",
    "vc_meeting_active_duration_pavg_val",
    "ticket_cnt",
    "bot_finish_rate",
    "im_dau",
}


def fail(errors):
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    sys.exit(1)


def canonical_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def rounded_text(value):
    rounded = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(rounded):,}"


def normalize_visible(value):
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def collect_strings(value):
    result = []
    if isinstance(value, dict):
        for child in value.values():
            result.extend(collect_strings(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(collect_strings(child))
    elif isinstance(value, str):
        normalized = normalize_visible(value)
        if normalized:
            result.append(normalized)
    return result


def compare_values(expected, actual, target, errors):
    expected_counts = Counter(normalize_visible(value) for value in expected)
    actual_counts = Counter(actual)
    for value, count in expected_counts.items():
        if actual_counts[value] < count:
            errors.append(
                f"{target}逐值比对失败：{value}，期望 {count} 次，实际 {actual_counts[value]} 次"
            )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--svg", required=True)
    p.add_argument("--xml", required=True)
    p.add_argument("--remote-doc-json")
    p.add_argument("--remote-board-raw")
    p.add_argument("--receipt", required=True)
    p.add_argument("--aeolus-request")
    p.add_argument("--aeolus-source-json")
    p.add_argument("--source-json", "--source", dest="source_json", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text())
    svg = Path(args.svg).read_text()
    xml = Path(args.xml).read_text()
    errors = []
    extra_metrics = data.get("extra_metrics", {})
    aeolus = data.get("aeolus_snapshot")
    enhanced = isinstance(aeolus, dict)

    try:
        validate_identity_ledger(data)
    except ResolutionError as exc:
        errors.append(str(exc))
    if data.get("percent_scale") != "0_to_100":
        errors.append("percent_scale 必须明确为 0_to_100")
    source_snapshot = data.get("source_snapshot", {})
    for key in ["queried_at", "fcode", "normalized_response_sha256"]:
        if not source_snapshot.get(key):
            errors.append(f"source_snapshot 缺少 {key}")
    if source_snapshot.get("fcode") and source_snapshot["fcode"] != data.get("fcode"):
        errors.append("source_snapshot.fcode 与主租户 F 码不一致")
    source_sha = source_snapshot.get("normalized_response_sha256")
    if source_sha and not re.fullmatch(r"[0-9a-fA-F]{64}", str(source_sha)):
        errors.append("source_snapshot.normalized_response_sha256 不是有效 SHA256")
    if args.source_json:
        actual_source_sha = canonical_sha256(
            json.loads(Path(args.source_json).read_text())
        )
        if str(source_sha).lower() != actual_source_sha:
            errors.append("source_snapshot.normalized_response_sha256 与规范化 source JSON 不匹配")
    for key in MEETING_REQUIRED:
        if key not in data.get("metrics", {}) and key not in extra_metrics:
            errors.append(f"会议模块缺少 C360 核心字段：{key}")
    if enhanced:
        aeolus_metrics = aeolus.get("metrics", {})
        if not isinstance(aeolus_metrics, dict) or not aeolus_metrics:
            errors.append("aeolus_snapshot.metrics 不能为空")
            aeolus_metrics = {}
        unknown = set(aeolus_metrics) - AEOLUS_ALLOWLIST
        if unknown:
            errors.append(f"Aeolus 指标不在 allowlist：{sorted(unknown)}")
        if aeolus.get("fcode") != data.get("fcode"):
            errors.append("aeolus_snapshot.fcode 与主租户 F 码不一致")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(aeolus.get("source_sha256", ""))):
            errors.append("aeolus_snapshot.source_sha256 不是有效 SHA256")
        periods = {}
        for period_name in ("current_period",):
            try:
                period = aeolus[period_name]
                start = date.fromisoformat(period["start_date"])
                end = date.fromisoformat(period["end_date"])
                periods[period_name] = (start, end)
                if end - start != timedelta(days=179):
                    errors.append(f"{period_name} 不是连续 180 天")
            except (KeyError, TypeError, ValueError):
                errors.append(f"{period_name} 日期结构错误")
        comparison_period = aeolus.get("comparison_period")
        if comparison_period is not None:
            try:
                comparison_start = date.fromisoformat(comparison_period["start_date"])
                comparison_end = date.fromisoformat(comparison_period["end_date"])
                periods["comparison_period"] = (comparison_start, comparison_end)
                if comparison_end - comparison_start != timedelta(days=179):
                    errors.append("comparison_period 不是连续 180 天")
                if (
                    "current_period" in periods
                    and comparison_end + timedelta(days=1) != periods["current_period"][0]
                ):
                    errors.append("Aeolus 对比期未紧邻当前期之前")
            except (KeyError, TypeError, ValueError):
                errors.append("comparison_period 日期结构错误")
        if args.aeolus_source_json:
            actual_aeolus_sha = canonical_sha256(
                json.loads(Path(args.aeolus_source_json).read_text())
            )
            if str(aeolus.get("source_sha256", "")).lower() != actual_aeolus_sha:
                errors.append("aeolus_snapshot.source_sha256 与 Aeolus source JSON 不匹配")
        for key, item in aeolus_metrics.items():
            if not isinstance(item, dict) or "current" not in item:
                errors.append(f"Aeolus 指标结构错误：{key}")
                continue
            expected_values = []
            value_periods = ("current", "comparison") if comparison_period else ("current",)
            for period in value_periods:
                value = item.get(period)
                if value is None and period == "comparison":
                    expected_values.append("—")
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append(f"Aeolus 指标值错误：{key}.{period}")
                    continue
                if key == "bot_finish_rate" and not 0 <= value <= 100:
                    errors.append(
                        f"Aeolus 百分比字段未归一到 0-100：{key}.{period}={value}"
                    )
                rendered = rounded_text(value)
                expected_values.append(rendered)
            if comparison_period is None and item.get("comparison") is not None:
                errors.append(f"Aeolus 指标存在 comparison 但未提供 comparison_period：{key}")
            candidate_rows = re.findall(
                rf"<tr>(?:(?!</tr>).)*?<code>{re.escape(key)}</code>"
                rf"(?:(?!</tr>).)*?</tr>",
                xml,
                flags=re.S,
            )
            value_pairs = [
                re.findall(r"<td><b>(.*?)</b></td>", row, flags=re.S)
                for row in candidate_rows
            ]
            value_pairs = [values for values in value_pairs if len(values) == len(value_periods)]
            if not value_pairs:
                errors.append(f"Aeolus 指标未进入文档：{key}")
            elif len(expected_values) == len(value_periods):
                normalized_pairs = [
                    [
                        re.sub(r"[^\d,—-]", "", normalize_visible(value))
                        for value in values
                    ]
                    for values in value_pairs
                ]
                if not any(
                    all(
                        expected in actual
                        for expected, actual in zip(expected_values, actual_values)
                    )
                    for actual_values in normalized_pairs
                ):
                    errors.append(f"Aeolus 当前/对比值未逐项进入文档：{key}")
        if comparison_period is None and "未提供对比期" not in svg + xml:
            errors.append("Aeolus 当前期-only 产物未明确“未提供对比期”")
        for forbidden in ("未接入 Aeolus", "请将 CSV", "如果你希望升级"):
            if forbidden in svg or forbidden in xml:
                errors.append(f"增强模式产物包含未接入/邀请文案：{forbidden}")

    percent_values = {}
    for key, value in data.get("metrics", {}).items():
        if "%" in key or "rate" in key or "penetration" in key:
            percent_values[key] = value
    for key, item in extra_metrics.items():
        if "%" in key or "rate" in key or "penetration" in key:
            percent_values[key] = item.get("value")
    for key, value in percent_values.items():
        if not isinstance(value, (int, float)) or not 0 <= value <= 100:
            errors.append(f"百分比字段未归一到 0-100：{key}={value}")

    if "<whiteboard type=\"svg\"" not in xml:
        errors.append("文档未使用 SVG whiteboard 资源块")
    if "&lt;svg" in xml or "&lt;rect" in xml:
        errors.append("文档包含转义 SVG 源码")
    if len(re.findall(r"<g transform=.*?stroke=", svg)) < 7:
        errors.append("少于 7 组图标")
    board_text = " ".join(re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S))
    for marker in ["客观洞见", "相差", "高于", "低于", "达到", "起步阶段"]:
        if marker in board_text:
            errors.append(f"画板包含洞见文本：{marker}")
    if "<image" in svg:
        errors.append("SVG 包含图片节点")
    for word in BANNED_WORDS:
        if word in svg or word in xml:
            errors.append(f"包含禁用表述：{word}")
    for value in [" 人", " 个", " 张", " 次", " 分钟", " 单"]:
        if value not in svg:
            errors.append(f"画板缺少同行单位：{value.strip()}")
    rendered_values = re.findall(r'font-size="28"[^>]*>(.*?)</text>', svg)
    rendered_values += re.findall(r"<td[^>]*>.*?<b>(.*?)</b>.*?</td>", xml, flags=re.S)
    for value in rendered_values:
        if re.search(r"\d+\.\d+", value):
            errors.append(f"展示值不是整数：{value}")

    metrics = data.get("metrics", {})
    svg_visible = " ".join(re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S))
    xml_visible = re.sub(r"<[^>]+>", " ", xml)
    visible_text = svg_visible + " " + xml_visible
    number_tokens = set(re.findall(r"(?<![A-Za-z])\d[\d,.]*%?", visible_text))
    allowed_numbers = set()
    for value in metrics.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            allowed_numbers.add(f"{value}")
            allowed_numbers.add(rounded_text(value))
            allowed_numbers.add(f"{value:.2f}")
            allowed_numbers.add(f"{value:,.2f}")
            allowed_numbers.add(f"{value:.2f}%")
    def collect_scalars(value):
        if isinstance(value, dict):
            for child in value.values():
                collect_scalars(child)
        elif isinstance(value, list):
            for child in value:
                collect_scalars(child)
        else:
            allowed_numbers.update(re.findall(r"\d[\d,.]*", str(value)))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                allowed_numbers.add(rounded_text(value))
                allowed_numbers.add(rounded_text(value).replace(",", ""))
    collect_scalars(data)
    scalar_blob = json.dumps(data, ensure_ascii=False)
    allowed_numbers.update({"7", "180", "1.5", "01", "02", "03", "04", "05", "06", "07"})
    allowed_numbers.update(re.findall(r"\d+", str(data.get("review_month", ""))))
    for token in number_tokens:
        if token.rstrip("%").replace(",", "") in scalar_blob:
            continue
        normalized = token.rstrip("%").replace(",", "")
        if token in allowed_numbers or normalized in {x.rstrip("%").replace(",", "") for x in allowed_numbers}:
            continue
        if "." in normalized:
            if normalized == "1.5":
                continue
            errors.append(f"展示文本包含未取整小数：{token}")
            continue
        if len(normalized) <= 2:
            continue
        errors.append(f"发现可能无来源的数字：{token}")

    if args.remote_doc_json:
        remote = json.loads(Path(args.remote_doc_json).read_text())
        content = remote["data"]["document"]["content"]
        if "&lt;svg" in content or "&lt;rect" in content:
            errors.append("云文档回读包含转义 SVG")
        remote_plain = normalize_visible(content)
        doc_markers = [data["customer_name"], data["tenant_name"], data["fcode"]]
        doc_markers += [normalize_visible(value) for value in re.findall(r"<h2>(.*?)</h2>", xml)]
        doc_markers += [normalize_visible(value) for value in re.findall(r"<td>(.*?)</td>", xml)]
        for marker in doc_markers:
            if marker and marker not in remote_plain:
                errors.append(f"云文档缺少内容：{marker}")
        local_doc_values = re.findall(r"<td[^>]*>.*?<b>(.*?)</b>.*?</td>", xml, flags=re.S)
        remote_doc_values = re.findall(r"<td[^>]*>.*?<b>(.*?)</b>.*?</td>", html.unescape(content), flags=re.S)
        compare_values(
            local_doc_values,
            [normalize_visible(value) for value in remote_doc_values],
            "云文档",
            errors,
        )
    if args.remote_board_raw:
        raw = json.loads(Path(args.remote_board_raw).read_text())
        types = Counter(node.get("type") for node in raw.get("nodes", []))
        if types.get("image", 0):
            errors.append(f"云画板包含 {types['image']} 个图片节点")
        if types.get("group", 0) < 7:
            errors.append("云画板图标分组少于 7")
        if types.get("connector", 0) < 20:
            errors.append("云画板矢量线条节点不足")
        local_board_values = re.findall(
            r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S
        )
        compare_values(
            local_board_values,
            collect_strings(raw),
            "云画板",
            errors,
        )

    if errors:
        fail(errors)
    if args.receipt:
        receipt_path = Path(args.receipt)
        receipt = json.loads(receipt_path.read_text())
        expected = {
            "input_sha256": canonical_sha256(data),
            "content_version": CONTENT_VERSION,
            "identity_ledger_sha256": canonical_sha256(data.get("identity_ledger")),
            "source_sha256": str(source_sha).lower(),
            "board_sha256": hashlib.sha256(Path(args.svg).read_bytes()).hexdigest(),
            "document_sha256": hashlib.sha256(Path(args.xml).read_bytes()).hexdigest(),
        }
        if enhanced:
            expected["aeolus_source_sha256"] = str(aeolus.get("source_sha256")).lower()
        for key, value in expected.items():
            if receipt.get(key) != value:
                fail([f"执行回执哈希不匹配：{key}"])
        if enhanced:
            if args.aeolus_request:
                fail(["增强模式禁止提供 Aeolus 邀请文件"])
            if receipt.get("aeolus_handoff_required") is not False:
                fail(["增强模式回执不得要求 Aeolus 邀请"])
        else:
            if not args.aeolus_request:
                fail(["缺少 --aeolus-request，无法校验主动邀请"])
            request_path = Path(args.aeolus_request)
            request_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
            if receipt.get("aeolus_request_sha256") != request_sha:
                fail(["Aeolus 邀请文件哈希不匹配"])
            request_text = request_path.read_text()
            for marker in ["无法直接访问 Aeolus", "主租户 F 码", "连续 180 天", "CSV", "XLSX"]:
                if marker not in request_text:
                    fail([f"Aeolus 邀请缺少内容：{marker}"])
        receipt["local_audit"] = "passed"
        receipt["remote_audit"] = "passed" if args.remote_doc_json and args.remote_board_raw else "pending"
        if args.remote_doc_json:
            remote = json.loads(Path(args.remote_doc_json).read_text())
            document = remote["data"]["document"]
            receipt["remote_document_id"] = document.get("document_id")
            token_match = re.search(r'<whiteboard[^>]+token="([^"]+)"', document.get("content", ""))
            receipt["remote_whiteboard_token"] = token_match.group(1) if token_match else None
            if not receipt["remote_document_id"] or not receipt["remote_whiteboard_token"]:
                fail(["远端文档 ID 或画板 token 绑定失败"])
        if args.remote_board_raw:
            receipt["remote_node_types"] = dict(Counter(
                node.get("type") for node in json.loads(Path(args.remote_board_raw).read_text()).get("nodes", [])
            ))
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({"ok": True, "message": "快照产物审计通过"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
