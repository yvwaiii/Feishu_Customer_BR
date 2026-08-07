# 确定性交付流水线

正式 C360 快照版必须使用本流水线。禁止 Agent 自行拼接 SVG、单位、洞见或扩展字段。

## 1. 准备输入 JSON

把已确认字段写入 `snapshot-input.json`：

```json
{
  "customer_name": "客户实体名称",
  "tenant_name": "主租户显示名称",
  "fcode": "FXXXXXXXXXXX",
  "review_month": "YYYY-MM",
  "suite": "套件名称",
  "industry": "行业",
  "metrics": {
    "im_dau": 0
  }
}
```

`metrics` 必须包含 `scripts/render-snapshot.py` 的 `FIELD_SPECS` 中全部 35 个字段。值必须是 JSON 数字，不带单位、逗号或百分号。

不要写入会议数、参会人次、ARR、AI ARPU、AI 额度、FAQ、人工工单等白名单外字段。

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

禁止手工修改生成文件。需要调整时修改输入 JSON 后重新生成。

## 3. 本地审计

```bash
python3 "$SKILL_ROOT/scripts/audit-snapshot.py" \
  --input snapshot-input.json \
  --svg generated/board.svg \
  --xml generated/document.xml \
  --receipt generated/delivery-receipt.json

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
  --svg generated/board.svg \
  --xml generated/document.xml \
  --remote-doc-json remote-doc.json \
  --remote-board-raw remote-board-raw.json \
  --receipt generated/delivery-receipt.json
```

## 6. 最终门禁

必须同时满足：

- 35 个快照字段完整；
- 画板七模块存在；
- 数字与单位在同一文本节点；
- raw 节点 `image=0`；
- raw 节点 `group>=7`；
- 无转义 SVG 普通段落；
- 无白名单外整数；
- 无归因、销售建议或提升空间表述；
- 远端预览人工检查通过。
- `delivery-receipt.json.content_version=2.7.1`；
- `delivery-receipt.json.local_audit=passed`；
- `delivery-receipt.json.remote_audit=passed`；
- `delivery-receipt.json.remote_node_types.image` 不存在或为 0。

通过后才返回文档链接和 `文档URL#whiteboard_block_id`。

最终回复必须同时报告执行回执中的 `content_version`、`input_sha256` 前 12 位、`local_audit` 和 `remote_audit`。无法提供这些值表示确定性流水线没有执行，禁止声称“门禁已通过”。
