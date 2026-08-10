# 数据源与工具路由

## 总则

- 启动只读 `SKILL.md`；确认需要 C360 后才按需读取本文件和 [环境检测、安装与恢复](bootstrap-and-recovery.md)，不得预读全部 reference。
- 执行任何 C360 命令前，先遵循 `c360-shared`。
- C360 仅使用 `lark-c360`，禁止猜测字段、命令或请求体。
- 飞书资源操作先遵循 `lark-shared`；遇到授权问题，走统一授权流程。
- Aeolus 只能在可访问 ByteDance 内网的浏览器中查询，不使用 WebFetch、curl 或自行拼接接口绕过访问限制。
- C360 七模块数据完整时可独立生成快照版；Aeolus 用于增强近 180 天累计、日均、趋势和对比。

## C360 路由

若用户消息已经提供经过校验的客户、主租户、F 码和下述七模块字段，视为本次 C360 查询结果，直接使用；不再执行 CLI，也不要求再次粘贴。附件仅用于可选交叉校验。

| 数据 | Skill | 执行要求 |
|---|---|---|
| 客户匹配、客户档案、客户下租户、ARR | `c360-account` | 先按客户名获取唯一 account；客户下租户列表必须走 account 规定的 tenant/list 页面同形请求 |
| 主租户使用数据、全部可用指标、健康状态 | `c360-tenant` | `tenant metrics` 的租户参数使用主租户 `display_id`，即 F 码 |

### 快速路径调用预算

正常成功路径最多调用：客户搜索一次、`tenant/list` 一次、`tenant metrics get` 一次。禁止为“确认能力”预读 schema/meta、API catalog 或重复探测；仅在命令明确返回字段/参数错误时读取一次对应 schema/meta，并最多重试一次失败命令。

把 `account search --json`、完整 account-scoped `tenant/list --json` 原始 envelope 和 `tenant_list_scope={"account_id":"<account>","account_scoped":true}` 直接交给 `scripts/identity_resolver.py`。resolver 要求 scope account_id 与 account search 唯一 `entity_id` 相等，再对完整列表排序。禁止 tenant keyword，也禁止按 tenant `company` 字段二次筛选。

### 七模块固定字段补充

`tenant metrics get` 除通用数据外，至少检查：

- 即时协同：`active_rate_7workday`、`activate_rate`、`active_duration_pavg_7workday`、`im_dau`、`im_dau_penetration_rate`；
- 会议协同：`vc_dau`、`vc_dau_penetration_rate`、`vc_meeting_cnt`、`join_meeting_ucnt`、`vc_meeting_active_duration_pavg_val`、`minutes_dau`、`minutes_dau_penetration_rate`、`vc_ai_dau`、`vc_ai_minutes_dau_penetration_rate`；
- 内容沉淀：`doc_independent_create_fcnt`、`create_fcnt`、`doc_view_dau_penetration_rate`、`tenant_used_wiki_space_cnt`、`wiki_dau`、`wiki_dau_penetration_rate`；
- 多维表格：`bitable_independent_create_fcnt`、`base_rownum_over15000_fcnt`、`bitable_automation_run`（额度）、`tenant_current_month_bitable_workflow_instance_cnt`（实际用量）、`base_dashboard_cnt`、`base_dau_rate_avg_7workday`；
- 知识管理：`cansearch_pv_per_user`、`knowledge_ai_pavg_use_cnt`、`search_dau_penetration_rate`、`teampedia_dau_penetration_rate`、`self_build_teampedia_entity_cnt`；
- AI 赋能：`aily_dau`、`aily_buddy_dau`、`base_ai_dau`、`ai_dau`、`miaoda_app_dau`、`miaoda_claw_dau`；
- 服务台：`helpdesk_cnt`、`tenant_used_normal_helpdesks_all_cnt`、`helpdesk_dau`、`helpdesk_wau`、`ticket_cnt`、`bot_finish_rate`。

字段仍以当前实体 meta 为准；字段不存在时记录缺失，不用相似字段猜测。

### 主租户规则

1. 用 account search 唯一结果的 `entity_id` 确定 account_id；不从模糊名称推断主体。
2. 请求该 account_id 的完整 account-scoped `tenant/list`；`tenant_list_scope.account_id` 必须等于 account_id，`account_scoped` 必须为 true，禁止 tenant keyword，`has_more` 必须为 false。
3. 不按 tenant `company` 字段筛选。对完整列表依次使用 `is_primary_tenant` 降序、`x7wd_avg_dau_suite` 降序；并列时按 `display_id`、`tenant_id`、`display_name` 升序，选择第一名作为唯一主租户。
4. 记录主租户 `display_name`、`display_id`、`tenant_id`。
5. `display_id` 是 F 码，用于 Aeolus 回填和 `tenant metrics`。
6. `tenant_id` 仅用于明确要求该字段的 C360 接口，不得与 F 码混用。

如主租户标记、DAU 或候选身份字段不完整，停止后续动作并要求 CSM 补充；并列必须使用上述稳定次级键，不得要求人工任意选择。

resolver 输出的 `identity_ledger` 是 renderer/auditor 强制输入，禁止手工改写。

### 刷新隔离

一旦用户要求刷新或本轮发出第一条 C360 刷新命令，旧消息、任务评论、resource、artifact 和缓存一律不得补值。本次 metrics 缺字段时直接失败；不得沿用旧快照中的同名字段。缓存只可在未刷新且身份账本与 source hash 均匹配时复用。

## Aeolus 路由

指定看板：

`https://data.bytedance.net/aeolus/pages/dashboard/1014743?appId=1161&sheetId=1247624`

增强模式调用浏览器能力，并按 [Aeolus 浏览器自动化手册](aeolus-browser-runbook.md) 完成：

1. 打开指定看板。
2. 将 C360 返回的主租户 `display_id`（F 码）填入企业编码查询条件。
3. 以看板最近可用数据日为结束日设置明确的滚动 180 天，不使用“近 6 个月”快捷选项。
4. 启动查询并等待看板完成刷新。
5. 读取所有可见模块和指标；需要翻页、展开或切换板块时完成相应交互。
6. 对比期可选；提供时使用紧邻当前期之前的连续 180 天。如看板不支持一次显示两期，分别使用两组明确日期查询。
7. Aeolus 输出使用独立语义键（如 `doc_create_fcnt`、`bitable_create_fcnt`、`automation_run_cnt`、`wiki_total_visit_cnt`），不得复用 C360 当前月字段键；可选增强 `ticket_cnt`、`bot_finish_rate`、`im_dau`。
8. 保存字段名、当前值、可选对比值、单位、模块、日期范围及查询条件。

禁止：

- 使用客户名、租户名、tenant_id 或 account_id 替代 F 码；
- 在 F 码回填前读取默认看板数据；
- 根据页面位置猜测字段含义；
- 将未刷新完成或筛选条件未生效的数据写入分析。

## 飞书交付路由

| 任务 | Skill | 规则 |
|---|---|---|
| 创建使用情况回顾文档、创建画板资源块 | `lark-doc` | 使用用户身份，保存到当前 CSM 个人云盘个人空间 |
| 更新、导出和检查总画板 | `lark-whiteboard` | 只更新文档中已创建的画板；写入后导出预览 |

当前 CLI 没有 `lark-cli whiteboard +create`。禁止调用不存在的命令。

可靠流程：

1. 生成完整 SVG 文件；
2. 若文档使用 XML 创建，在正文插入 `<whiteboard type="svg" path="@board.svg"></whiteboard>`；
3. 若用户明确要求 `docs +create --doc-format markdown`，先创建 Markdown 文档，再用 `docs +update` 以 XML 追加 SVG whiteboard 资源块；
4. 从 `docs +create` 或 `docs +update` 返回的 `new_blocks` 读取 `block_token`（whiteboard token）和 `block_id`；
5. 如需重写内容，调用 `lark-cli whiteboard +update --whiteboard-token <token> --input_format svg --source @board.svg --overwrite --as user`；
6. 调用 `whiteboard +query --output_as image` 回读预览；
7. 文档链接使用返回的 `url`；画板链接使用 `<文档URL>#<whiteboard block_id>`。

不得把 whiteboard token 猜成独立 URL。

写后强制检查：

- `docs +fetch --detail full`：不存在转义 SVG 源码段落，不存在乱码或异体字；
- `whiteboard +query --output_as image`：人工检查七组图标、数字单位同行、洞见和口径卡；
- `whiteboard +query --output_as raw`：确认每个模块包含矢量图标节点；
- 用本次输入字段来源账本扫描文档与 raw 画板，任何未在必需字段、已注册 C360 扩展字段或可复核派生结果中的数值都视为错误；
- 发现错误必须修正并重新回读，不得直接交付链接。

## 并行边界

以下步骤必须串行：

`account search 唯一 entity_id → 完整 account-scoped tenant/list（无 keyword）→ scope account_id 校验 → is_primary_tenant/DAU/稳定键排序 → 取得 F 码 → 单次 metrics get`

上述依赖完成后，下列任务可并行：

- C360 七模块固定字段查询；
- 运行环境允许时读取 Aeolus 当前期数据，并尽可能读取可选对比期数据；当前期-only 仍进入增强模式。

快照模式只等待 C360；增强模式等待 C360 与 Aeolus。
