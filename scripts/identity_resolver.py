#!/usr/bin/env python3
"""Deterministically resolve a C360 account and its main tenant."""

import argparse
import json
import math
import sys
from decimal import Decimal
from pathlib import Path


ACCOUNT_MATCH_RULE = "account_search.entity_id_exact"
TENANT_SCOPE_RULE = "tenant_list_scope.account_id_exact_complete_no_keyword"
TENANT_RANK_RULE = (
    "is_primary_tenant_desc_then_x7wd_avg_dau_suite_desc_"
    "then_display_id_tenant_id_display_name_asc"
)


class ResolutionError(ValueError):
    pass


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ResolutionError(f"{field} 必须是非空字符串")
    return value.strip()


def _cell_value(value):
    if not isinstance(value, dict) or "value" not in value:
        return value
    raw = value.get("value")
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _cell_text(value, field):
    parsed = _cell_value(value)
    if parsed is None and isinstance(value, dict):
        parsed = value.get("display_value")
    return _text(parsed, field)


def _account_id(value, field):
    value = _cell_value(value)
    if isinstance(value, dict):
        value = value.get("account_id", value.get("id"))
    return _text(value, field)


def _company_reference_account_id(value, field):
    reference = _account_id(value, field)
    if reference.startswith("02NN"):
        reference = reference[4:]
    if not reference:
        raise ResolutionError(f"{field} 未包含 account_id")
    return reference


def _dau(value):
    value = _cell_value(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResolutionError("x7wd_avg_dau_suite 必须是有限 JSON 数字")
    if not math.isfinite(value):
        raise ResolutionError("x7wd_avg_dau_suite 必须是有限 JSON 数字")
    return value


def _primary(value):
    value = _cell_value(value)
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ResolutionError("is_primary_tenant 必须是 JSON 布尔值")


def _list_from_envelope(value, field):
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        raise ResolutionError(f"{field} 必须是数组或 lark-c360 JSON envelope")
    candidates = (
        value.get("list"),
        value.get("data", {}).get("list") if isinstance(value.get("data"), dict) else None,
        value.get("data", {}).get("data", {}).get("list")
        if isinstance(value.get("data"), dict)
        and isinstance(value.get("data", {}).get("data"), dict)
        else None,
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate
    raise ResolutionError(f"{field} envelope 中缺少 list")


def _nested_cell(item, container, key):
    nested = item.get(container)
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return None


def _normalized_account(item):
    if not isinstance(item, dict):
        raise ResolutionError("account search 结果必须是对象")
    account_id_value = item.get("account_id", item.get("id", item.get("entity_id")))
    if account_id_value is None:
        account_id_value = _nested_cell(item, "abstract", "id")
    name_value = item.get("customer_name", item.get("name"))
    if name_value is None:
        name_value = _nested_cell(item, "title", "name")
    return {
        "account_id": _account_id(account_id_value, "account.entity_id"),
        "customer_name": _cell_text(name_value, "account.customer_name"),
    }


def _normalized_tenant(item, expected_account_id):
    if not isinstance(item, dict):
        raise ResolutionError("tenant 必须是对象")
    return {
        "account_id": expected_account_id,
        "tenant_id": _cell_text(item.get("tenant_id"), "tenant.tenant_id"),
        "display_id": _cell_text(item.get("display_id"), "tenant.display_id"),
        "display_name": _cell_text(item.get("display_name"), "tenant.display_name"),
        "is_primary_tenant": _primary(item.get("is_primary_tenant")),
        "x7wd_avg_dau_suite": _dau(item.get("x7wd_avg_dau_suite")),
    }


def _tenant_list_metadata(value):
    if isinstance(value, list):
        return None
    if not isinstance(value, dict):
        return None
    containers = [
        value,
        value.get("data") if isinstance(value.get("data"), dict) else None,
    ]
    nested = value.get("data")
    if isinstance(nested, dict) and isinstance(nested.get("data"), dict):
        containers.append(nested["data"])
    for container in reversed(containers):
        if isinstance(container, dict) and "list" in container:
            return container
    return None


def _validate_tenant_list_scope(payload, account_id, tenant_source, tenant_count):
    scope = payload.get("tenant_list_scope")
    if not isinstance(scope, dict):
        raise ResolutionError("缺少 tenant_list_scope")
    scoped_account_id = _account_id(
        scope.get("account_id"), "tenant_list_scope.account_id"
    )
    if scoped_account_id != account_id:
        raise ResolutionError("tenant_list_scope.account_id 与 account 不一致")
    if "keyword" in scope:
        raise ResolutionError("tenant_list_scope 禁止 tenant keyword")
    if scope.get("account_scoped") is not True:
        raise ResolutionError("tenant_list_scope.account_scoped 必须为 true")

    metadata = _tenant_list_metadata(tenant_source)
    if metadata is not None:
        if metadata.get("has_more") is not False:
            raise ResolutionError("tenant_list 必须是完整 account-scoped 列表")
        total = metadata.get("total")
        if total is not None and total != tenant_count:
            raise ResolutionError("tenant_list total 与完整列表长度不一致")


def tenant_sort_key(item):
    return (
        -int(item["is_primary_tenant"]),
        -Decimal(str(item["x7wd_avg_dau_suite"])),
        item["display_id"],
        item["tenant_id"],
        item["display_name"],
    )


def resolve(payload):
    if not isinstance(payload, dict):
        raise ResolutionError("输入必须是 JSON 对象")
    reference = payload.get("company_reference")
    if reference is not None and not isinstance(reference, dict):
        raise ResolutionError("company_reference 必须是对象")

    account_source = payload.get("account_search", payload.get("accounts"))
    accounts = [
        _normalized_account(item)
        for item in _list_from_envelope(account_source, "account_search")
    ]
    if reference is not None:
        reference_account_id = _company_reference_account_id(
            reference.get("account_id", reference.get("value")),
            "company_reference.account_id",
        )
        exact_accounts = [
            item for item in accounts if item["account_id"] == reference_account_id
        ]
    else:
        exact_accounts = accounts
    if len(exact_accounts) != 1:
        raise ResolutionError(
            f"account search 精确结果必须唯一，实际 {len(exact_accounts)}"
        )
    account = exact_accounts[0]
    reference_account_id = account["account_id"]
    customer_name = account["customer_name"]

    tenant_source = payload.get("tenant_list", payload.get("tenants"))
    tenants = _list_from_envelope(tenant_source, "tenant_list")
    _validate_tenant_list_scope(
        payload, reference_account_id, tenant_source, len(tenants)
    )
    account_tenants = [
        _normalized_tenant(item, reference_account_id) for item in tenants
    ]
    if not account_tenants:
        raise ResolutionError("account-scoped 列表中没有可排序租户")
    account_tenants.sort(key=tenant_sort_key)

    main_tenant = dict(account_tenants[0])
    return {
        "company_reference": {
            "account_id": reference_account_id,
            "customer_name": customer_name,
        },
        "resolved_account": {
            "account_id": reference_account_id,
            "customer_name": customer_name,
        },
        "tenant_list_scope": {
            "account_id": reference_account_id,
            "account_scoped": True,
        },
        "tenant_candidates": account_tenants,
        "main_tenant": main_tenant,
        "resolution": {
            "account_match": ACCOUNT_MATCH_RULE,
            "tenant_scope": TENANT_SCOPE_RULE,
            "tenant_rank": TENANT_RANK_RULE,
        },
    }


def validate_identity_ledger(data):
    ledger = data.get("identity_ledger")
    if not isinstance(ledger, dict):
        raise ResolutionError("缺少 identity_ledger")
    reference = ledger.get("company_reference")
    resolved = ledger.get("resolved_account")
    main = ledger.get("main_tenant")
    candidates = ledger.get("tenant_candidates")
    rules = ledger.get("resolution")
    if not all(isinstance(item, dict) for item in (reference, resolved, main, rules)):
        raise ResolutionError("identity_ledger 身份对象不完整")
    account_id = _account_id(reference.get("account_id"), "identity_ledger.company_reference.account_id")
    if _account_id(resolved.get("account_id"), "identity_ledger.resolved_account.account_id") != account_id:
        raise ResolutionError("identity_ledger resolved account_id 不一致")
    if rules != {
        "account_match": ACCOUNT_MATCH_RULE,
        "tenant_scope": TENANT_SCOPE_RULE,
        "tenant_rank": TENANT_RANK_RULE,
    }:
        raise ResolutionError("identity_ledger resolution 规则不匹配")
    if not isinstance(candidates, list) or not candidates:
        raise ResolutionError("identity_ledger.tenant_candidates 不能为空")

    scope = ledger.get("tenant_list_scope")
    if not isinstance(scope, dict):
        raise ResolutionError("identity_ledger 缺少 tenant_list_scope")
    if _account_id(scope.get("account_id"), "identity_ledger.tenant_list_scope.account_id") != account_id:
        raise ResolutionError("identity_ledger tenant_list_scope.account_id 不一致")
    if scope.get("account_scoped") is not True or "keyword" in scope:
        raise ResolutionError("identity_ledger tenant_list_scope 非完整 account-scoped 查询")

    normalized = []
    for item in candidates:
        tenant = _normalized_tenant(item, account_id)
        normalized.append(tenant)
    expected = sorted(normalized, key=tenant_sort_key)
    if normalized != expected:
        raise ResolutionError("identity_ledger 租户未按确定性主租户规则排序")
    if main != expected[0]:
        raise ResolutionError("identity_ledger.main_tenant 不是同主体排序第一名")
    if data.get("customer_name") != resolved.get("customer_name"):
        raise ResolutionError("customer_name 与 identity_ledger.resolved_account 不一致")
    if data.get("tenant_name") != main.get("display_name"):
        raise ResolutionError("tenant_name 与 identity_ledger.main_tenant 不一致")
    if data.get("fcode") != main.get("display_id"):
        raise ResolutionError("fcode 与 identity_ledger.main_tenant 不一致")
    return ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text())
        print(json.dumps({"ok": True, "identity_ledger": resolve(payload)}, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ResolutionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
