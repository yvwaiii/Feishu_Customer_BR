# 执行流程

## 1. 前置门槛

1. 先解析当前消息正文。若已包含通过 `identity_resolver.py` 生成的身份账本、唯一主租户、F 码和七模块字段，直接复用，不安装或查询 C360。
2. 正文不足时再检查当前 resource、Drive 文件和 [环境检测、安装与恢复](bootstrap-and-recovery.md) 中的持久化存档。
3. 上述输入仍不足时才检测并补齐 `lark-c360`，再查询 C360。
4. 同时按 [运行能力检测与用户提醒](runtime-capability-and-notification.md) 检查飞书权限和运行环境。
5. 需要查询时，快速路径最多执行一次客户搜索、一次完整 account-scoped `tenant/list` 和一次 `tenant metrics get`。保留 account search 与 tenant/list 的完整 `--json` envelope；禁止 tenant keyword。
6. 把两份原始 envelope 和 `tenant_list_scope={"account_id":"<account>","account_scoped":true}` 交给 `scripts/identity_resolver.py`；resolver 要求 scope account_id 与唯一 account search `entity_id` 相等。无唯一 account 或 scope 不一致时停止，让 CSM 补充或修正查询。
7. resolver 不按 tenant `company` 字段筛选，而对完整 account-scoped 列表按 `is_primary_tenant` 降序、DAU 降序与稳定次级键排序，选第一名为唯一主租户，并输出 `identity_ledger`。
8. 获取该主租户 F 码。主租户或 F 码缺失时停止。

正常快速路径禁止预先读取 schema/meta、API catalog、帮助文档或枚举能力。仅当业务命令返回字段/参数错误时，才读取一次对应 schema/meta，修正后最多重试一次。

用户明确要求刷新或本轮已发起 C360 刷新后，进入“纯刷新”边界：旧消息、任务评论、resource、`artifacts/` 与持久化缓存不得补齐本次缺失身份或指标；本次 company reference、tenant/list、metrics 响应必须独立形成完整身份账本和 source snapshot。

将包含身份账本和指标的结构化输入保存为 JSON 后运行：

```bash
python3 <当前Skill根目录>/scripts/validate-snapshot-input.py snapshot-input.json
```

输出 `next_action=generate` 时禁止继续索取字段，直接进入分析与产出。

## 2. 选择模式

### C360 快照模式

用于 Aily、云端沙箱、无 ByteDance 内网或无法访问 Aeolus 的环境。先获取 C360 七模块最新快照，正常进入分析与产出。不得展示 180 天累计、日均、趋势或同比。

### C360 + Aeolus 增强模式

环境可访问 Aeolus，或用户提供 Aeolus 导出时使用：

- 当前周期：以 Aeolus 日期筛选器显示的最近可用数据日为结束日，向前滚动 180 天；
- 对比周期：紧邻当前周期之前的 180 天，不重叠、不留空档。

## 3. Aeolus 增强数据

指定看板：

`https://data.bytedance.net/aeolus/pages/dashboard/1014743?appId=1161&sheetId=1247624`

1. 把 C360 返回的主租户 F 码回填为看板查询条件。
2. 按 [Aeolus 浏览器自动化手册](aeolus-browser-runbook.md) 设置滚动 180 天，并将该日期范围同步给 C360。
3. 启动查询并确认成功。
4. 桌面环境优先使用 Agent 内置浏览器；没有时使用可操作用户 Chrome 的外部浏览器能力。
5. Aily 或云端沙箱访问内网失败时，立即跳过 Aeolus，使用 C360 快照模式继续。
6. 交付 C360 快照版时必须主动提醒一次用户可补充 Aeolus 当前期或两期数据；用户未提供时不阻塞，也不重复提醒。收到当前期-only 数据时直接升级增强版并明确“未提供对比期”，不得再次生成邀请。
7. 禁止用客户名称、租户名称或其他标识替代 F 码。

## 4. 数据收集

在 C360 主租户/F 码确认后执行：

- 当前消息正文已给出的字段直接进入 coverage matrix；
- resource 可读时用于交叉校验和补充，不可读时不影响已提供的正文数据；
- C360 客户、主租户及七模块固定使用指标；
- 增强模式下补充 Aeolus 飞书业务使用指标及板块数据；
- coverage matrix 所需字段。

不搜索群聊、会议、功能、案例或行业资料。

## 5. 分析与产出

1. 按业务板块关联全部指标。
2. 生成 coverage matrix，检查有效核心字段是否完整。
3. 快照模式按 [数据源与工具路由](tool-routing.md) 中的 C360 七模块字段检查；会议字段合同必须包含固定九项，但不要求会议总时长、AI ARPU、趋势或同比等增强字段。
4. 快照模式按 [确定性交付流水线](deterministic-delivery.md) 把身份账本、41 个必需字段及全部已注册 C360 扩展字段写入 JSON，运行 `render-snapshot.py`；不得自行删减会议等模块数据，不得编写 SVG。
5. 运行 `audit-snapshot.py` 和 whiteboard-cli `--check`，失败时停止。
6. 按 [数据源与工具路由](tool-routing.md) 通过生成的 XML 创建文档和画板；不得调用不存在的 `whiteboard +create`。
7. 创建“飞书整体使用情况回顾”文档，并取得文档 URL、whiteboard block ID 和 token。
8. 回读画板图片、raw 节点和文档 XML，再次运行审计；逐值比较远端文档/画板与本地生成物，任一值不一致或 raw 中 `image>0` 时必须重做。
9. 返回文档 URL 和 `<文档URL>#<whiteboard block_id>` 画板定位链接。
10. 校验通过后结束，不继续生成任何后续章节或自动化。
