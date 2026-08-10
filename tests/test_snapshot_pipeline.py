#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import re
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
IDENTITY_RESOLVER = load_script("identity_resolver.py")


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
    identity_ledger = IDENTITY_RESOLVER.resolve({
        "company_reference": {
            "account_id": "account-test",
            "customer_name": "虚构客户",
        },
        "accounts": [
            {"account_id": "account-test", "customer_name": "虚构客户"},
        ],
        "tenant_list_scope": {
            "account_id": "account-test",
            "account_scoped": True,
        },
        "tenants": [
            {
                "account_id": "account-test",
                "tenant_id": "tenant-test",
                "display_id": "FTEST123456",
                "display_name": "虚构租户",
                "is_primary_tenant": True,
                "x7wd_avg_dau_suite": 10,
            },
        ],
    })
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
        "identity_ledger": identity_ledger,
        "source_snapshot": {
            "queried_at": "2026-08-07T00:00:00Z",
            "fcode": "FTEST123456",
            "normalized_response_sha256": canonical_sha256(source),
        },
    }


def with_aeolus(data, source):
    data["aeolus_snapshot"] = {
        "fcode": data["fcode"],
        "current_period": {
            "start_date": "2026-02-09",
            "end_date": "2026-08-07",
        },
        "comparison_period": {
            "start_date": "2025-08-13",
            "end_date": "2026-02-08",
        },
        "source_sha256": canonical_sha256(source),
        "metrics": {
            "doc_create_fcnt": {"current": 1200.5, "comparison": 900.4},
            "bitable_create_fcnt": {"current": 321, "comparison": 210},
            "automation_run_cnt": {
                "current": 4567,
                "comparison": 3456,
            },
            "base_dashboard_cnt": {"current": 98, "comparison": 76},
            "wiki_total_visit_cnt": {"current": 76543, "comparison": 65432},
            "vc_meeting_cnt": {"current": 2345, "comparison": 2000},
            "join_meeting_ucnt": {"current": 9876, "comparison": 8765},
            "vc_meeting_active_duration_pavg_val": {
                "current": 42.5,
                "comparison": 40.4,
            },
        },
    }
    return data


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
            self.assertEqual(receipt["content_version"], "3.2.0")
            self.assertEqual(receipt["display_rounding"], "ROUND_HALF_UP_integer")
            self.assertEqual(receipt["input_sha256"], canonical_sha256(data))
            self.assertEqual(
                receipt["identity_ledger_sha256"],
                canonical_sha256(data["identity_ledger"]),
            )
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

    def test_renderer_rejects_tampered_identity_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = {"rows": []}
            data = sample_input(source)
            data["identity_ledger"]["main_tenant"]["display_id"] = "FWRONG123"
            input_path = temp / "input.json"
            input_path.write_text(json.dumps(data, ensure_ascii=False))
            result = self.run_command(
                ROOT / "scripts/render-snapshot.py",
                "--input",
                input_path,
                "--out-dir",
                temp / "generated",
                expect_ok=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("main_tenant", result.stderr)

    def test_enhanced_schema_values_enter_outputs_without_handoff_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            c360_source = {"rows": []}
            aeolus_source = {"export": "formal-schema"}
            data = with_aeolus(sample_input(c360_source), aeolus_source)
            data["aeolus_snapshot"]["metrics"]["base_dashboard_cnt"].pop("comparison")
            input_path = temp / "input.json"
            c360_path = temp / "c360.json"
            aeolus_path = temp / "aeolus.json"
            output = temp / "generated"
            input_path.write_text(json.dumps(data, ensure_ascii=False))
            c360_path.write_text(json.dumps(c360_source, ensure_ascii=False))
            aeolus_path.write_text(json.dumps(aeolus_source, ensure_ascii=False))
            self.run_command(
                ROOT / "scripts/render-snapshot.py",
                "--input", input_path,
                "--out-dir", output,
            )
            self.assertFalse((output / "aeolus-request.txt").exists())
            svg = (output / "board.svg").read_text()
            xml = (output / "document.xml").read_text()
            self.assertIn("C360 + Aeolus 近 180 天增强版", svg)
            self.assertIn("1,201 个", svg)
            self.assertIn("当前期</th><th>对比期", xml)
            self.assertIn("4,567 次", xml)
            self.assertRegex(
                xml,
                r"<td><b>98 个</b></td><td><b>—</b></td><td><code>base_dashboard_cnt</code>",
            )
            self.assertNotIn("未接入 Aeolus", svg + xml)
            self.assertNotIn("请将 CSV", svg + xml)
            self.run_command(
                ROOT / "scripts/audit-snapshot.py",
                "--input", input_path,
                "--source-json", c360_path,
                "--aeolus-source-json", aeolus_path,
                "--svg", output / "board.svg",
                "--xml", output / "document.xml",
                "--receipt", output / "delivery-receipt.json",
            )

    def test_enhanced_current_period_only_accepts_integer_values(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            c360_source = {"rows": []}
            aeolus_source = {"export": "current-only-integers"}
            data = with_aeolus(sample_input(c360_source), aeolus_source)
            del data["aeolus_snapshot"]["comparison_period"]
            for item in data["aeolus_snapshot"]["metrics"].values():
                item["current"] = RENDERER.rounded_integer(item["current"])
                item.pop("comparison", None)
            data["aeolus_snapshot"]["metrics"].update({
                "im_dau": {"current": 88},
                "ticket_cnt": {"current": 77},
                "bot_finish_rate": {"current": 66},
            })
            input_path = temp / "input.json"
            c360_path = temp / "c360.json"
            aeolus_path = temp / "aeolus.json"
            output = temp / "generated"
            input_path.write_text(json.dumps(data, ensure_ascii=False))
            c360_path.write_text(json.dumps(c360_source, ensure_ascii=False))
            aeolus_path.write_text(json.dumps(aeolus_source, ensure_ascii=False))
            self.run_command(
                ROOT / "scripts/render-snapshot.py",
                "--input", input_path,
                "--out-dir", output,
            )
            self.assertFalse((output / "aeolus-request.txt").exists())
            svg = (output / "board.svg").read_text()
            xml = (output / "document.xml").read_text()
            self.assertIn("C360 + Aeolus 近 180 天增强版", svg)
            self.assertIn("未提供对比期", svg + xml)
            self.assertNotIn("<th>对比期</th>", xml)
            self.assertIn("<code>automation_run_cnt</code>", xml)
            self.assertIn("<code>ticket_cnt</code>", xml)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertFalse(manifest["aeolus_comparison_available"])
            displayed = re.findall(r'font-size="28"[^>]*>(.*?)</text>', svg)
            displayed += re.findall(r"<td><b>(.*?)</b></td>", xml)
            self.assertTrue(all(not re.search(r"\d+\.\d+", value) for value in displayed))
            self.run_command(
                ROOT / "scripts/audit-snapshot.py",
                "--input", input_path,
                "--source-json", c360_path,
                "--aeolus-source-json", aeolus_path,
                "--svg", output / "board.svg",
                "--xml", output / "document.xml",
                "--receipt", output / "delivery-receipt.json",
            )

    def test_enhanced_rejects_unknown_metric_and_bad_period(self):
        data = with_aeolus(sample_input({"rows": []}), {"export": "x"})
        data["aeolus_snapshot"]["metrics"]["unknown_metric"] = {"current": 1}
        with self.assertRaisesRegex(ValueError, "allowlist"):
            RENDERER.validate(data)
        del data["aeolus_snapshot"]["metrics"]["unknown_metric"]
        data["aeolus_snapshot"]["current_period"]["start_date"] = "2026-02-10"
        with self.assertRaisesRegex(ValueError, "连续 180 天"):
            RENDERER.validate(data)
        data = with_aeolus(sample_input({"rows": []}), {"export": "x"})
        del data["aeolus_snapshot"]["comparison_period"]
        with self.assertRaisesRegex(ValueError, "需要 comparison_period"):
            RENDERER.validate(data)

    def test_field_semantics_and_call_budget_contract(self):
        self.assertEqual(
            RENDERER.FIELD_SPECS["bitable_automation_run"][0],
            "自动化运行额度",
        )
        self.assertIn(
            "tenant_current_month_bitable_workflow_instance_cnt",
            RENDERER.OPTIONAL_FIELD_SPECS,
        )
        self.assertEqual(RENDERER.BOARD_PRIORITY["content"][0], "create_fcnt")
        self.assertEqual(
            RENDERER.BOARD_PRIORITY["base"][0],
            "tenant_current_month_bitable_workflow_instance_cnt",
        )
        self.assertNotIn("bitable_automation_run", RENDERER.BOARD_PRIORITY["base"])
        self.assertTrue(
            {"ticket_cnt", "bot_finish_rate", "im_dau"}
            <= set(RENDERER.AEOLUS_FIELD_SPECS)
        )
        routing = (ROOT / "references/tool-routing.md").read_text()
        self.assertIn("客户搜索一次", routing)
        self.assertIn("tenant/list` 一次", routing)
        self.assertIn("tenant metrics get` 一次", routing)
        self.assertNotIn("tenant list --keyword", (ROOT / "references/bootstrap-and-recovery.md").read_text())

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
