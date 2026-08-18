# 确定性交付流水线

正式 C360 快照版必须使用本流水线。禁止 Agent 自行拼接 SVG、单位、洞见或扩展字段。

## 1. 准备输入 JSON

把已确认字段写入 `snapshot-input.json`：

```json
{
  "customer_name": "客户实体名称",
  "tenant_name": "主租户显示名称",
  "fcode": "FXXXXXXXXXXX",
  "identity_ledger": {
    "company_reference": {"account_id": "account-id"},
    "resolved_account": {"account_id": "account-id", "customer_name": "客户实体名称"},
    "tenant_list_scope": {"account_id": "account-id", "account_scoped": true},
    "tenant_candidates": [],
    "main_tenant": {},
    "resolution": {}
  },
  "review_month": "YYYY-MM",
  "suite": "套件名称",
  "industry": "行业",
  "metrics": {
    "im_dau": 0
  }
}
```

`identity_ledger` 禁止手写，必须由 `scripts/identity_resolver.py` 基于本轮 account search、完整 account-scoped tenant/list 原始 JSON envelope 与 `tenant_list_scope` 生成。scope 必须满足 `account_id==account search entity_id`、`account_scoped=true` 且不含 keyword；resolver 不按 tenant `company` 字段筛选，而是对完整列表按 `is_primary_tenant`、DAU 降序和稳定键排序。renderer 和 auditor 会重新校验 scope、确定性排序及顶层客户/租户/F 码一致性。

`metrics` 必须包含 `scripts/render-snapshot.py` 的 `FIELD_SPECS` 中全部 41 个必需字段。值必须是 JSON 数字，不带单位、逗号或百分号。会议字段合同固定为九项：VC DAU、VC 渗透率、会议数、参会人次、平均参会时长、妙记 DAU/渗透率、智能纪要 DAU/渗透率。

41 个必需字段只是稳定基线，不是字段上限。C360 实体 meta 中真实存在、在 `OPTIONAL_FIELD_SPECS` 注册且有有效值的字段必须写入 `extra_metrics`：

```json
"extra_metrics": {
  "vc_ai_dau_avg_7workday": {"value": 12.5, "source": "c360"},
  "search_dau": {"value": 61, "source": "c360"},
  "ai_arpu": {"value": 9.8, "source": "c360"}
}
```

扩展字段必须带 `source=c360`。未注册字段先更新字段注册表，不得直接删除真实数据，也不得猜测值。

`bitable_automation_run` 表示自动化运行额度；实际用量使用 `tenant_current_month_bitable_workflow_instance_cnt`。内容扩展应采集 `create_fcnt`。C360 画板内容模块优先 `create_fcnt`，多维表格模块优先实际自动化用量，额度不作为核心指标。

采集前先运行 `python3 scripts/query-fields.py`，使用输出的 `all_fields` 与实体 meta 求交集后一次性查询。禁止只查询 41 个必需字段。

输入还必须包含：

```json
"percent_scale": "0_to_100",
"source_snapshot": {
  "queried_at": "ISO-8601 时间",
  "fcode": "主租户 F 码",
  "normalized_response_sha256": "规范化 C360 响应哈希"
}
```

原始数值保持 C360 精度，展示层统一按十进制 `ROUND_HALF_UP` 取整数（`.5` 远离 0）。百分比只允许 `0_to_100` 口径，不得无条件乘以 100。派生比值的分母必须大于 0；否则只说明无法计算，不生成结构或阶段判断。

可选 Aeolus 正式输入使用 `aeolus_snapshot`：

```json
"aeolus_snapshot": {
  "fcode": "FXXXXXXXXXXX",
  "current_period": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "comparison_period": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "source_sha256": "64 位规范化来源哈希",
  "metrics": {
    "doc_create_fcnt_180d": {"current": 1200, "comparison": 900},
    "bitable_create_total_180d": {"current": 321, "comparison": 210},
    "bitable_automation_run_total_180d": {"current": 4567, "comparison": 3456},
    "ticket_cnt": {"current": 88}
  }
}
```

`current_period` 与 `metrics` 必需；`comparison_period` 及每个指标的 `comparison` 可选。当前期须为连续 180 天；提供对比期时，两期各须连续 180 天且对比期紧邻当前期。Aeolus 使用独立语义键，不得复用 C360 当前月键。指标只允许 renderer 的 `AEOLUS_FIELD_SPECS`，其中还包括可选增强字段 `ticket_cnt`、`bot_finish_rate`、`im_dau`。提供当前期-only 数据也自动进入增强模式：画板和文档展示当前期，明确“未提供对比期”，且禁止出现“未接入 Aeolus”或生成导出邀请。

## 2. 确定性生成

```bash
SKILL_ROOT="<当前 Skill 根目录>"
python3 "$SKILL_ROOT/scripts/render-snapshot.py" \
  --input snapshot-input.json \
  --out-dir generated
```

生成：

- `generated/board.svg`
- `generated/document.xml`
- `generated/manifest.json`
- `generated/delivery-receipt.json`
- `generated/aeolus-request.txt`（仅 C360 快照模式生成；任意 Aeolus 增强模式均不生成）

禁止手工修改生成文件。需要调整时修改输入 JSON 后重新生成。

## 3. 本地审计

```bash
python3 "$SKILL_ROOT/scripts/audit-snapshot.py" \
  --input snapshot-input.json \
  --source-json normalized-c360-response.json \
  --svg generated/board.svg \
  --xml generated/document.xml \
  --receipt generated/delivery-receipt.json \
  --aeolus-request generated/aeolus-request.txt

npx -y @larksuite/whiteboard-cli@^0.2.13 \
  -i generated/board.svg -f svg --check
```

任一命令失败时禁止写入飞书。

## 4. 创建或覆盖文档

```bash
lark-cli docs +create \
  --content @generated/document.xml \
  --doc-format xml \
  --as user
```

覆盖已有测试文档时可使用 `docs +update --command overwrite`。

从返回的 `new_blocks` 读取：

- `block_token`：whiteboard token；
- `block_id`：画板定位链接锚点。

## 5. 云端回读

```bash
lark-cli docs +fetch --doc "<doc_url>" \
  --detail full --doc-format xml --as user \
  --format json > remote-doc.json

lark-cli whiteboard +query \
  --whiteboard-token "<block_token>" \
  --output_as image --output remote-board.png \
  --overwrite --as user

lark-cli whiteboard +query \
  --whiteboard-token "<block_token>" \
  --output_as raw --output remote-board-raw.json \
  --overwrite --as user

python3 "$SKILL_ROOT/scripts/audit-snapshot.py" \
  --input snapshot-input.json \
  --source-json normalized-c360-response.json \
  --svg generated/board.svg \
  --xml generated/document.xml \
  --remote-doc-json remote-doc.json \
  --remote-board-raw remote-board-raw.json \
  --receipt generated/delivery-receipt.json \
  --aeolus-request generated/aeolus-request.txt
```

## 6. 最终门禁

必须同时满足：

- 41 个必需字段完整，全部已提供的注册扩展字段也完整进入正文；
- 身份账本存在且 tenant_list_scope account_id、完整 account-scoped 候选排序、主租户及顶层身份字段全部一致；
- 会议模块至少包含 VC DAU、VC 渗透率、会议数、参会人次、平均参会时长、妙记 DAU/渗透率、智能纪要 DAU/渗透率；
- 所有展示值按 `ROUND_HALF_UP` 为整数，输入 JSON 保留原始精度；
- 回执包含 C360 查询时间、F 码和规范化响应哈希；审计逐项校验规范化 source JSON、规范化输入、内容版本及生成物哈希；
- 画板七模块存在；
- 画板不包含任何洞见、判断或建议；洞见只在文档正文；
- 数字与单位在同一文本节点；
- raw 节点 `image=0`；
- raw 节点 `group>=7`；
- 无转义 SVG 普通段落；
- 所有数字均来自输入 JSON、固定版式或可复核派生运算；
- 无归因、销售建议或提升空间表述；
- 远端文档指标值与本地 XML 逐值一致，远端画板指标值与本地 SVG 逐值一致；
- 远端预览人工检查通过。
- `delivery-receipt.json.content_version=3.3.0`；
- `delivery-receipt.json.local_audit=passed`；
- `delivery-receipt.json.remote_audit=passed`；
- `delivery-receipt.json.remote_node_types.image` 不存在或为 0。

通过后才返回文档链接和 `文档URL#whiteboard_block_id`。仅 C360 快照模式原样附上 `generated/aeolus-request.txt`；Aeolus 增强模式（包括当前期-only）不得生成或附加邀请。

最终回复必须同时报告执行回执中的 `content_version`、`input_sha256` 前 12 位、`local_audit` 和 `remote_audit`。无法提供这些值表示确定性流水线没有执行，禁止声称“门禁已通过”。


## v3.3.0 正式 BR 十九项硬门禁

- 正式 BR 必须同时获取并在同一画板与正文原名展示 Aeolus 10 项：人均会议时长、文档创建数、创建多维表格总数、多维表格自动化运行数、多维表格仪表盘创建数、服务台数量、累计工单数、平均机器人拦截率、知识库总空间数、总访问次数。
- 正式 BR 必须同时获取并在同一画板与正文原名展示 C360 9 项：活跃率、人均使用时长、知识问答 DAU、知识问答人均可搜文档数、智能纪要渗透率、飞书 aily 智能伙伴 DAU、多维表格 AI DAU、多维表格 DAU 渗透率、单表超过 15,000 行的表格总数。
- 19 项各自映射独立字段，禁止使用同名复用、派生估算或语义相近字段替代。
- 19 项展示值统一使用 `ROUND_HALF_UP` 整数化，原始值保留在输入与来源账本。
- Aeolus 任一项缺失时不得得到正式审计 `passed`；C360-only 只能生成明确标记的草稿。
