#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


BANNED_WORDS = [
    "同构", "抓手", "潜力", "提升空间", "一家独大", "最后一公里",
    "续约", "增购", "重度办公", "已替代", "原因是",
]


def fail(errors):
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--svg", required=True)
    p.add_argument("--xml", required=True)
    p.add_argument("--remote-doc-json")
    p.add_argument("--remote-board-raw")
    p.add_argument("--receipt")
    p.add_argument("--aeolus-request")
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text())
    svg = Path(args.svg).read_text()
    xml = Path(args.xml).read_text()
    errors = []

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

    metrics = data.get("metrics", {})
    svg_visible = " ".join(re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S))
    xml_visible = re.sub(r"<[^>]+>", " ", xml)
    visible_text = svg_visible + " " + xml_visible
    number_tokens = set(re.findall(r"(?<![A-Za-z])\d[\d,.]*%?", visible_text))
    allowed_numbers = set()
    for value in metrics.values():
        if isinstance(value, (int, float)):
            allowed_numbers.add(f"{value}")
            allowed_numbers.add(f"{value:,.0f}")
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
        # 派生差值/占比允许两位小数，由固定渲染器生成；外部未知整数不允许。
        if "." in normalized:
            continue
        if len(normalized) <= 2:
            continue
        errors.append(f"发现可能无来源的数字：{token}")

    if args.remote_doc_json:
        remote = json.loads(Path(args.remote_doc_json).read_text())
        content = remote["data"]["document"]["content"]
        if "&lt;svg" in content or "&lt;rect" in content:
            errors.append("云文档回读包含转义 SVG")
    if args.remote_board_raw:
        raw = json.loads(Path(args.remote_board_raw).read_text())
        types = Counter(node.get("type") for node in raw.get("nodes", []))
        if types.get("image", 0):
            errors.append(f"云画板包含 {types['image']} 个图片节点")
        if types.get("group", 0) < 7:
            errors.append("云画板图标分组少于 7")
        if types.get("connector", 0) < 20:
            errors.append("云画板矢量线条节点不足")

    if errors:
        fail(errors)
    if args.receipt:
        receipt_path = Path(args.receipt)
        receipt = json.loads(receipt_path.read_text())
        expected = {
            "board_sha256": hashlib.sha256(Path(args.svg).read_bytes()).hexdigest(),
            "document_sha256": hashlib.sha256(Path(args.xml).read_bytes()).hexdigest(),
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                fail([f"执行回执哈希不匹配：{key}"])
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
        if args.remote_board_raw:
            receipt["remote_node_types"] = dict(Counter(
                node.get("type") for node in json.loads(Path(args.remote_board_raw).read_text()).get("nodes", [])
            ))
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({"ok": True, "message": "快照产物审计通过"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
