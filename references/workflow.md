# 执行流程

## 1. 前置门槛

1. 先解析当前消息正文。若已包含已校验客户、唯一主租户、F 码和七模块字段，直接复用，不安装或查询 C360。
2. 正文不足时再检查当前 resource、Drive 文件和 [环境检测、安装与恢复](bootstrap-and-recovery.md) 中的持久化存档。
3. 上述输入仍不足时才检测并补齐 `lark-c360`，再查询 C360。
4. 同时按 [运行能力检测与用户提醒](runtime-capability-and-notification.md) 检查飞书权限和运行环境。
5. 需要查询时，使用 `customer_name` 在 C360 只读匹配客户；若输入 `tenant_fcode`，先精确反查租户及所属客户。
6. 无唯一客户结果时停止，让 CSM 补充或选择。
7. 获取该客户下全部关联租户及 DAU，选 DAU 最高者为唯一主租户。
8. 获取该主租户 F 码。主租户或 F 码缺失时停止。

可将当前消息或 resource 内容保存为临时 Markdown 后运行：

```bash
python3 <当前Skill根目录>/scripts/validate-snapshot-input.py <input.md>
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
6. 只有用户明确要求增强数据时，才提醒用户导出两期数据。
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
3. 快照模式只按 [数据源与工具路由](tool-routing.md) 中的 C360 七模块字段检查；不要求会议数、参会人次、总时长、AI ARPU 等增强字段。
4. 快照模式按 [确定性交付流水线](deterministic-delivery.md) 把 35 个必需字段及全部已注册 C360 扩展字段写入 JSON，运行 `render-snapshot.py`；不得自行删减会议等模块数据，不得编写 SVG。
5. 运行 `audit-snapshot.py` 和 whiteboard-cli `--check`，失败时停止。
6. 按 [数据源与工具路由](tool-routing.md) 通过生成的 XML 创建文档和画板；不得调用不存在的 `whiteboard +create`。
7. 创建“飞书整体使用情况回顾”文档，并取得文档 URL、whiteboard block ID 和 token。
8. 回读画板图片、raw 节点和文档 XML，再次运行审计；raw 中 `image>0` 时必须重做。
9. 返回文档 URL 和 `<文档URL>#<whiteboard block_id>` 画板定位链接。
10. 校验通过后结束，不继续生成任何后续章节或自动化。
