#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "identity_resolver.py"
SPEC = importlib.util.spec_from_file_location("identity_resolver_regression", SCRIPT)
RESOLVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLVER)


def tenant(account_id, tenant_id, fcode, name, dau, is_primary=False):
    return {
        "account_id": account_id,
        "tenant_id": tenant_id,
        "display_id": fcode,
        "display_name": name,
        "is_primary_tenant": is_primary,
        "x7wd_avg_dau_suite": dau,
    }


def cell(value, display_value=None, field_type="text"):
    import json

    return {
        "field_type": field_type,
        "display_value": str(value) if display_value is None else display_value,
        "value": json.dumps(value, ensure_ascii=False),
    }


class IdentityResolverRegressionTest(unittest.TestCase):
    def test_real_lark_c360_envelopes_select_yuedong_company_tenant(self):
        account_id = "001TL000001HwqIYAS"
        payload = {
            "tenant_list_scope": {
                "account_id": account_id,
                "account_scoped": True,
            },
            "account_search": {
                "data": {
                    "list": [{
                        "title": {
                            "name": cell("广州悦动游戏科技有限公司"),
                        },
                        "abstract": {
                            "id": cell(account_id, field_type="id"),
                        },
                        "entity_id": account_id,
                    }],
                    "has_more": False,
                },
                "ok": True,
            },
            "tenant_list": {
                "data": {
                    "code": 0,
                    "data": {
                        "has_more": False,
                        "list": [
                            {
                                "company": cell(
                                    "02NN001TL00000sdvvRYAQ",
                                    "广州星火无限游戏科技有限公司",
                                    "reference",
                                ),
                                "display_id": cell("F3E565Y313M"),
                                "display_name": cell(
                                    "F3E565Y313M-广州星火无限游戏科技有限公司"
                                ),
                                "is_primary_tenant": cell(
                                    True, "true", "bool"
                                ),
                                "tenant_id": cell("7308658312639807490"),
                                "x7wd_avg_dau_suite": cell(
                                    657, "657", "integer"
                                ),
                            },
                            {
                                "company": cell(
                                    f"02NN{account_id}",
                                    "广州悦动游戏科技有限公司",
                                    "reference",
                                ),
                                "display_id": cell("FBJAZABY02E"),
                                "display_name": cell(
                                    "FBJAZABY02E-广州悦动游戏科技有限公司"
                                ),
                                "is_primary_tenant": cell(
                                    True, "true", "bool"
                                ),
                                "tenant_id": cell("7304119056562602012"),
                                "x7wd_avg_dau_suite": cell(
                                    0, "0", "integer"
                                ),
                            },
                        ],
                        "total": 2,
                    },
                    "message": "success",
                },
                "ok": True,
            },
        }

        ledger = RESOLVER.resolve(payload)

        self.assertEqual(ledger["resolved_account"]["account_id"], account_id)
        self.assertEqual(ledger["main_tenant"]["display_id"], "F3E565Y313M")
        self.assertEqual(ledger["main_tenant"]["x7wd_avg_dau_suite"], 657)
        self.assertEqual(len(ledger["tenant_candidates"]), 2)
        self.assertEqual(
            ledger["resolution"],
            {
                "account_match": "account_search.entity_id_exact",
                "tenant_scope": "tenant_list_scope.account_id_exact_complete_no_keyword",
                "tenant_rank": (
                    "is_primary_tenant_desc_then_x7wd_avg_dau_suite_desc_"
                    "then_display_id_tenant_id_display_name_asc"
                ),
            },
        )

    def test_same_entity_primary_precedes_higher_dau_then_stable_key(self):
        payload = {
            "company_reference": {"account_id": "acc-a"},
            "tenant_list_scope": {"account_id": "acc-a", "account_scoped": True},
            "accounts": [{"account_id": "acc-a", "customer_name": "客户 A"}],
            "tenants": [
                tenant("acc-a", "t-non-primary", "F000", "非主租户", 999, False),
                tenant("acc-a", "t-b", "F200", "主租户 B", 10, True),
                tenant("acc-a", "t-a", "F100", "主租户 A", 10, True),
            ],
        }
        first = RESOLVER.resolve(payload)
        second = RESOLVER.resolve({**payload, "tenants": list(reversed(payload["tenants"]))})
        self.assertEqual(first, second)
        self.assertEqual(
            [item["tenant_id"] for item in first["tenant_candidates"]],
            ["t-a", "t-b", "t-non-primary"],
        )

    def test_yuedong_exact_account_precedes_cross_entity_dau(self):
        payload = {
            "company_reference": {
                "account_id": "acc-yuedong-tech",
                "customer_name": "悦动科技",
            },
            "accounts": [
                {"account_id": "acc-yuedong-media", "customer_name": "悦动传媒"},
                {"account_id": "acc-yuedong-tech", "customer_name": "悦动科技有限公司"},
            ],
            "tenant_list_scope": {
                "account_id": "acc-yuedong-tech",
                "account_scoped": True,
            },
            "tenants": [
                tenant("acc-yuedong-tech", "t-sub", "FYD200", "悦动科技二部", 180),
                tenant("acc-yuedong-tech", "t-main", "FYD100", "悦动科技", 420),
            ],
        }
        ledger = RESOLVER.resolve(payload)
        self.assertEqual(ledger["resolved_account"]["account_id"], "acc-yuedong-tech")
        self.assertEqual(ledger["main_tenant"]["tenant_id"], "t-main")
        self.assertEqual(
            [item["tenant_id"] for item in ledger["tenant_candidates"]],
            ["t-main", "t-sub"],
        )

    def test_xinghuo_same_entity_tie_break_is_deterministic(self):
        payload = {
            "company_reference": {
                "account_id": "acc-xinghuo-edu",
                "customer_name": "星火教育",
            },
            "accounts": [
                {"account_id": "acc-xinghuo-ai", "customer_name": "星火智能"},
                {"account_id": "acc-xinghuo-edu", "customer_name": "星火教育集团"},
            ],
            "tenant_list_scope": {
                "account_id": "acc-xinghuo-edu",
                "account_scoped": True,
            },
            "tenants": [
                tenant("acc-xinghuo-edu", "t-b", "FXH200", "星火教育 B", 300),
                tenant("acc-xinghuo-edu", "t-a", "FXH100", "星火教育 A", 300),
            ],
        }
        first = RESOLVER.resolve(payload)
        second = RESOLVER.resolve({**payload, "tenants": list(reversed(payload["tenants"]))})
        self.assertEqual(first, second)
        self.assertEqual(first["main_tenant"]["tenant_id"], "t-a")

    def test_resolver_rejects_scope_mismatch_and_keyword(self):
        base = {
            "company_reference": {"account_id": "acc-a"},
            "accounts": [{"account_id": "acc-a", "customer_name": "客户 A"}],
            "tenants": [tenant("acc-a", "tenant-a", "FAAAAAA", "租户 A", 1)],
        }
        with self.assertRaisesRegex(RESOLVER.ResolutionError, "account 不一致"):
            RESOLVER.resolve({
                **base,
                "tenant_list_scope": {
                    "account_id": "acc-b",
                    "account_scoped": True,
                },
            })
        with self.assertRaisesRegex(RESOLVER.ResolutionError, "禁止 tenant keyword"):
            RESOLVER.resolve({
                **base,
                "tenant_list_scope": {
                    "account_id": "acc-a",
                    "account_scoped": True,
                    "keyword": "FAAAAAA",
                },
            })

    def test_ledger_rejects_tampered_scope(self):
        ledger = RESOLVER.resolve({
            "company_reference": {"account_id": "acc-a"},
            "tenant_list_scope": {"account_id": "acc-a", "account_scoped": True},
            "accounts": [{"account_id": "acc-a", "customer_name": "客户 A"}],
            "tenants": [tenant("acc-a", "tenant-a", "FAAAAAA", "租户 A", 1)],
        })
        ledger["tenant_list_scope"]["account_id"] = "acc-b"
        with self.assertRaisesRegex(RESOLVER.ResolutionError, "scope.account_id"):
            RESOLVER.validate_identity_ledger({
                "customer_name": "客户 A",
                "tenant_name": "租户 A",
                "fcode": "FAAAAAA",
                "identity_ledger": ledger,
            })


if __name__ == "__main__":
    unittest.main()
