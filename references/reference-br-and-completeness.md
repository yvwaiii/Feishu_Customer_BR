# 参考 BR 与数据完整性门禁

## 参考文档

生成飞书整体使用情况回顾时，结构、数据密度和表达质量参考以下文档：

- `https://bytedance.larkoffice.com/docx/NnDHdjaKbodlCXxlEqoc9yrVnBg`
- `https://bytedance.larkoffice.com/docx/UJ2gd3dvioV2fhxoPhQcpWitn5d`
- `https://bytedance.larkoffice.com/docx/UGYLdPGZDo5JiDxjEbPcpFGQnMe`

运行时不需要每次全文读取，但 Skill 开发、评审或模板调整时必须重新对照。

## 结构基线

回顾文档至少包含：

1. 数据口径与合规说明；
2. 3～5 条核心结论；
3. 单一飞书总画板；
4. 飞书整体使用情况回顾；
5. 核心指标总览；
6. 各协同场景完整数据和判断；
7. AI 使用场景完整数据和判断；

到七模块整体使用情况回顾结束，不继续输出其他章节。

## 画板与正文边界

- 画板每模块展示 3～5 个关键指标，是视觉摘要规则。
- 正文必须展示该模块所有核心可解释指标，不受 3～5 个限制。
- 画板和顶部结论帮助客户快速理解；正文用于完整回顾和讨论。
- 禁止把“画板精简”误解成“整份 BR 精简数据”。

## 画板七模块结构

默认按参考画板的一级模块组织，不得自行合并：

1. **即时协同**：活跃率、激活率、人均使用时长、IM DAU/渗透率；
2. **会议协同**：人均参会时长、妙记渗透率、智能会议纪要渗透率、会议规模；
3. **内容沉淀**：文档创建数、文档 DAU 渗透率、知识库空间数、知识库访问/DAU；
4. **多维表格**：创建数、大表数、自动化运行数、仪表盘数、DAU 渗透率；
5. **知识管理**：人均可搜文档数、知识问答人均使用次数、搜索渗透率、词典渗透率、企业自建词条数；
6. **AI 赋能**：Aily 专业版、Aily 智能伙伴、多维表格 AI、妙搭/OpenClaw 等使用指标；
7. **服务台**：服务台数量、DAU/WAU、工单数、机器人拦截率。

模块有有效数据时必须独立展示。特别规则：

- **知识管理不得并入 AI 赋能**。知识管理描述知识资产、检索、问答入口、词典和术语治理；AI 赋能描述 AI 产品使用。
- **内容沉淀不得替代知识管理**。内容沉淀回答“沉淀了多少”，知识管理回答“能否被检索、理解和复用”。
- **服务台不得因画板未展示或查询不完整而写成未开通**。必须先查 `helpdesk_cnt`、`tenant_used_normal_helpdesks_all_cnt`、`helpdesk_dau`、`helpdesk_wau`、`ticket_cnt`、`bot_finish_rate`。
- 某模块无数据时只隐藏该模块，并在内部版记录缺失原因；不得用另一个模块填补。

## 画板视觉规范

画板采用深色客户汇报风，不做白底后台仪表盘：

- 整体使用深蓝黑渐变背景，建议从 `#172554` 过渡到 `#06080F`；
- 顶部使用大号白色标题、灰蓝副标题和小号口径说明，不放复杂品牌装饰；
- 主体使用单列通栏大卡片，七个序号模块各占一整行，不使用两列并排；
- 每张卡片顺序固定为：图标 → 编号与价值型标题 → 分隔线 → 3～5 个指标；
- 卡片使用接近黑色底 `#0A0E1A`、细灰边框 `#343A4B` 和 24～28px 圆角；
- 指标标签用灰蓝色，指标值用大号白色，单位使用小号弱化文字；
- 画板不展示洞见、判断、价值总结或建议；洞见只在文档对应模块正文中展示；
- 图标不使用白色圆角方块或单字缩写；优先使用无底框的蓝、青、紫线性 SVG 矢量图标，也可不放图标；
- 模块标题统一采用 `01｜统一协同底座、工作入口稳定` 格式，序号后必须是全角 `｜`；
- 七个模块全部采用相同宽度的通栏卡片，服务台作为第七行，底部再放独立数据口径卡；
- 每张通栏卡的数据区严格切分为 5 个等宽列；所有模块使用相同的列中心坐标；
- 每列的指标名称和指标值使用 `text-anchor="middle"`，共享同一中心轴；
- 指标名称只写名称，不带括号单位；单位必须跟随数字写入同一个值文本节点，例如 `648 人`、`47 分钟`、`542,600 次`；
- 百分比的 `%` 属于数值本身，不拆成独立文本；禁止出现“上方纯数字、单位另放标签”的布局；
- 七个模块必须各有一个可见的无底框线性 SVG 图标，使用 `<path>`、`<circle>`、`<rect>` 等矢量节点；写入后在 raw 节点和预览图中确认图标存在；
- 避免浅色大面积模块底、彩虹配色、仪表盘式迷你卡墙、大阴影和多余英文标签；
- 标题应描述业务价值，例如“统一协同底座，工作入口稳定”，不能只写模块名；
- 画板写入后必须回读预览，确认颜色、文字、节点和整体比例与本地预览一致；
- 飞书端预览与本地预览需逐项检查：图标、标题、指标、数字单位、洞见、口径卡；
- 文档回读不得出现 `&lt;svg`、`&lt;rect` 或完整 SVG 源码普通段落；SVG 只能存在于 whiteboard 资源块；
- 如原画板已被失败写入污染，新建画板，不在损坏画板上继续叠加。

## C360 快照模式清单

快照模式只要求当前输入或 C360 返回的七模块字段。以下字段足以生成完整七模块回顾：

- 即时协同：`active_rate_7workday`、`activate_rate`、`active_duration_pavg_7workday`、`im_dau`、`im_dau_penetration_rate`；
- 会议协同：`vc_dau`、`vc_dau_penetration_rate`、`vc_meeting_cnt`、`join_meeting_ucnt`、`vc_meeting_active_duration_pavg_val`、`minutes_dau`、`minutes_dau_penetration_rate`、`vc_ai_dau`、`vc_ai_minutes_dau_penetration_rate`；
- 内容沉淀：`doc_independent_create_fcnt`、`create_fcnt`、`doc_view_dau_penetration_rate`、`tenant_used_wiki_space_cnt`、`wiki_dau`、`wiki_dau_penetration_rate`；
- 多维表格：`bitable_independent_create_fcnt`、`base_rownum_over15000_fcnt`、`bitable_automation_run`（额度）、`tenant_current_month_bitable_workflow_instance_cnt`（实际用量）、`base_dashboard_cnt`、`base_dau_rate_avg_7workday`；
- 知识管理：`cansearch_pv_per_user`、`knowledge_ai_pavg_use_cnt`、`search_dau_penetration_rate`、`teampedia_dau_penetration_rate`、`self_build_teampedia_entity_cnt`；
- AI 赋能：`ai_dau`、`aily_dau`、`aily_buddy_dau`、`base_ai_dau`、`miaoda_app_dau`、`miaoda_claw_dau`；
- 服务台：`helpdesk_cnt`、`tenant_used_normal_helpdesks_all_cnt`、`helpdesk_dau`、`helpdesk_wau`、`ticket_cnt`、`bot_finish_rate`。

会议模块必须满足上述九项字段合同；其余模块至少有 3 个有效可解释字段即可通过初步覆盖门禁，正式生成前仍须补齐 41 个必需字段。不得要求快照输入补充以下增强字段：

- 会议总时长、趋势或同比；
- 统计期文档或多维表格累计创建数；
- AI ARPU、AI 用量、AI ARR；
- 时间趋势、前期对比或同比。

## 增强模式补充清单

字段存在且有有效值时，回顾正文必须展示；无数据时在 coverage matrix 记录原因。

### 整体健康度

- 激活率；
- 活跃率；
- 套件 DAU / WAU；
- IM DAU / 渗透率；
- 开放平台应用 DAU / 渗透率；
- 主要 ARR 与 AI ARR。

### 内容协同

- Doc 查看、创建、编辑人数和渗透率；
- 统计期文档创建数；
- Sheet 查看、创建指标；
- Wiki DAU / 渗透率、知识库空间数和访问指标。

### 知识管理

- 知识问答人均可搜文档数 `cansearch_pv_per_user`；
- 知识问答人均使用次数 `knowledge_ai_pavg_use_cnt`；
- 搜索 DAU 渗透率 `search_dau_penetration_rate`；
- 词典 DAU 渗透率 `teampedia_dau_penetration_rate`；
- 企业内自建词条数 `self_build_teampedia_entity_cnt`；
- 其他知识检索、可搜文档和术语治理指标。

### 业务线上化

- Base DAU / 渗透率；
- Base 查看、编辑、创建人数；
- 多维表格创建数；
- 自动化运行数；
- 仪表盘数；
- 审批 DAU / WAU 或实例指标；
- 项目、任务等有数据模块。

### 会议

- VC DAU / 渗透率；
- 会议数；
- 参会人次；
- 会议总时长；
- 人均或单次会议时长；
- 日程会议指标；
- 智能纪要和妙记指标。

### AI

- AI DAU / ARPU；
- AI ARR；
- 多维表格 AI DAU、用量、ARPU；
- 智能纪要 DAU、用量、渗透率；
- Aily 智能伙伴 DAU、消息量、额度；
- 妙搭 / OpenClaw；
- 其他有有效值的 AI 产品。

知识问答产品的 DAU 和 AI 消耗可在 AI 赋能中补充，但知识资产、搜索、词典和人均可搜文档必须保留在独立知识管理模块。

### 服务台

- `helpdesk_cnt` / `tenant_used_normal_helpdesks_all_cnt`；
- `helpdesk_dau` / `helpdesk_wau`；
- `ticket_cnt` / `artificial_ticket_cnt`；
- `bot_finish_rate`；
- 服务台知识库和消息阅读指标。

## 口径分层

Aeolus 与 C360 可能返回不同时间和聚合口径：

- Aeolus：明确标注滚动 180 天的累计、日均或趋势；
- C360：明确标注最新使用快照、近 7 工作日或字段自身口径；
- 同名指标口径不同不得相互覆盖；
- 不得把 C360 最新快照写成 180 天平均；
- 不得把 Aeolus 累计值写成当前 DAU；
- 同一表格内混用时增加“口径”列或在标题说明。

快照模式只使用 C360 时：

- coverage matrix 只要求 C360 当前可用的七模块核心字段；
- Aeolus 字段标记为“当前运行模式未接入”，不算数据缺失；
- 增强模式清单中的字段未提供时不算缺失，不得向用户追问；
- 文档和画板不得出现近 180 天累计、日均、趋势或同比表述；
- 不得因为 Aeolus 未接入而把正式快照版降级为预分析。

## 完整性检查

生成文档前构造 `coverage_matrix`：

| 模块 | 已查询字段 | 有效字段 | 回顾正文已展示 | 缺失原因 |
|---|---|---|---|---|

交付回顾文档前必须满足：

- 所有有效核心字段都能在正文中定位；
- 画板指标是正文数据的子集；
- 每个协同模块至少有数据、判断和自然表达；
- 每个 AI 模块至少有数据、阶段判断和适配建议；
- 所有数值保留来源和口径；
- 不存在无来源数值；
- 不存在将空值隐藏后仍作结论的情况。

任一有效核心字段未展示，禁止标记“飞书整体使用情况回顾完成”。
