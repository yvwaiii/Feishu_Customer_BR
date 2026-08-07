#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDERER = load_script("render-snapshot.py")
PACKAGER = load_script("package-release.py")


def canonical_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def sample_input(source):
    metrics = {key: 10 for key in RENDERER.FIELD_SPECS}
    for key in metrics:
        if "rate" in key or "penetration" in key:
            metrics[key] = 25.5
    metrics.update(
        {
            "vc_meeting_cnt": 0,
            "join_meeting_ucnt": 12,
            "ai_dau": 0,
            "base_ai_dau": 3,
            "helpdesk_wau": 0,
            "helpdesk_dau": 2,
            "self_build_teampedia_entity_cnt": 0,
        }
    )
    return {
        "customer_name": "虚构客户",
        "tenant_name": "虚构租户",
        "fcode": "FTEST123456",
        "review_month": "2026-08",
        "suite": "虚构套件",
        "industry": "测试行业",
        "percent_scale": "0_to_100",
        "metrics": metrics,
        "extra_metrics": {},
        "source_snapshot": {
            "queried_at": "2026-08-07T00:00:00Z",
            "fcode": "FTEST123456",
            "normalized_response_sha256": canonical_sha256(source),
        },
    }


class SnapshotPipelineTest(unittest.TestCase):
    def run_command(self, *args, expect_ok=True):
        result = subprocess.run(
            [sys.executable, *map(str, args)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if expect_ok and result.returncode != 0:
            self.fail(f"命令失败：{result.stdout}\n{result.stderr}")
        return result

    def generate(self, temp):
        source = {"fcode": "FTEST123456", "rows": [{"metric": "im_dau", "value": 10}]}
        data = sample_input(source)
        input_path = temp / "input.json"
        source_path = temp / "source.json"
        output = temp / "generated"
        input_path.write_text(json.dumps(data, ensure_ascii=False))
        source_path.write_text(json.dumps(source, ensure_ascii=False))
        self.run_command(
            ROOT / "scripts/render-snapshot.py",
            "--input",
            input_path,
            "--out-dir",
            output,
        )
        return data, input_path, source_path, output

    def test_round_half_up_and_safe_insights(self):
        self.assertEqual(RENDERER.rounded_integer(2.5), 3)
        self.assertEqual(RENDERER.rounded_integer(-2.5), -3)
        self.assertEqual(RENDERER.rounded_integer(2.49), 2)
        source = {"rows": []}
        insight = RENDERER.insights(sample_input(source))
        self.assertIn("会议数为 0", insight[1])
        self.assertIn("AI DAU 为 0", insight[5])
        self.assertIn("服务台 WAU 为 0", insight[6])

    def test_meeting_contract_has_nine_required_fields(self):
        meeting = {
            "vc_dau",
            "vc_dau_penetration_rate",
            "vc_meeting_cnt",
            "join_meeting_ucnt",
            "vc_meeting_active_duration_pavg_val",
            "minutes_dau",
            "minutes_dau_penetration_rate",
            "vc_ai_dau",
            "vc_ai_minutes_dau_penetration_rate",
        }
        self.assertEqual(len(meeting), 9)
        self.assertTrue(meeting <= set(RENDERER.FIELD_SPECS))
        self.assertTrue(meeting.isdisjoint(RENDERER.OPTIONAL_FIELD_SPECS))
        self.assertEqual(len(RENDERER.FIELD_SPECS), 41)

    def test_render_and_local_hash_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            data, input_path, source_path, output = self.generate(temp)
            receipt = json.loads((output / "delivery-receipt.json").read_text())
            self.assertEqual(receipt["content_version"], "3.1.0")
            self.assertEqual(receipt["display_rounding"], "ROUND_HALF_UP_integer")
            self.assertEqual(receipt["input_sha256"], canonical_sha256(data))
            self.run_command(
                ROOT / "scripts/audit-snapshot.py",
                "--input",
                input_path,
                "--source-json",
                source_path,
                "--svg",
                output / "board.svg",
                "--xml",
                output / "document.xml",
                "--receipt",
                output / "delivery-receipt.json",
                "--aeolus-request",
                output / "aeolus-request.txt",
            )
            audited = json.loads((output / "delivery-receipt.json").read_text())
            self.assertEqual(audited["local_audit"], "passed")
            self.assertEqual(audited["remote_audit"], "pending")

    def test_remote_values_are_compared(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            _, input_path, source_path, output = self.generate(temp)
            xml = (output / "document.xml").read_text()
            svg = (output / "board.svg").read_text()
            doc_json = temp / "remote-doc.json"
            board_json = temp / "remote-board.json"
            remote_content = xml + '<whiteboard token="mock-whiteboard-token"></whiteboard>'
            doc_json.write_text(
                json.dumps({"data": {"document": {"document_id": "mock-document-id", "content": remote_content}}}, ensure_ascii=False)
            )
            import re

            values = re.findall(r'<text\b[^>]*>(.*?)</text>', svg)
            nodes = [{"type": "group"} for _ in range(7)]
            nodes += [{"type": "connector"} for _ in range(20)]
            nodes += [{"type": "text", "text": value} for value in values]
            board_json.write_text(json.dumps({"nodes": nodes}, ensure_ascii=False))
            args = [
                ROOT / "scripts/audit-snapshot.py",
                "--input",
                input_path,
                "--source-json",
                source_path,
                "--svg",
                output / "board.svg",
                "--xml",
                output / "document.xml",
                "--remote-doc-json",
                doc_json,
                "--remote-board-raw",
                board_json,
                "--receipt",
                output / "delivery-receipt.json",
                "--aeolus-request",
                output / "aeolus-request.txt",
            ]
            self.run_command(*args)
            nodes[-1]["text"] = "999 人"
            board_json.write_text(json.dumps({"nodes": nodes}, ensure_ascii=False))
            result = self.run_command(*args, expect_ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("云画板逐值比对失败", result.stdout)

    def test_deterministic_package_and_allowlist(self):
        manifest = json.loads((ROOT / "release-manifest.json").read_text())
        self.assertEqual(manifest["package_files"], sorted(set(manifest["package_files"])))
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            PACKAGER.build_archive(ROOT, first)
            PACKAGER.build_archive(ROOT, second)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )
            with zipfile.ZipFile(first) as archive:
                expected = [
                    f"customer-business-review/{path}"
                    for path in manifest["package_files"]
                ]
                self.assertEqual(archive.namelist(), expected)
                self.assertTrue(all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist()))


if __name__ == "__main__":
    unittest.main()
