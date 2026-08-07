# Feishu Customer BR

一个用于生成“飞书整体使用情况回顾”的 TRAE Skill。它会识别客户主租户，读取近 180 天使用数据，形成结构化洞见，并生成飞书文档与数据画板。

> 当前版本：`2.5.1`

![脱敏后的生成效果](assets/board-preview.png)

预览图中的公司、租户编号和数据均为虚构示例，不对应任何真实客户。

## 适用场景

当你需要完成以下工作时，可以调用本 Skill：

- 准备客户 Business Review；
- 复盘客户近 180 天飞书使用情况；
- 分析主租户的协同、内容、知识、AI 与服务台使用；
- 生成可直接放入飞书文档的数据洞察画板。

安装后，用户提到“回访”“BR”“Business Review”“客户复盘”“使用回顾”等相近意图时，TRAE 会自动匹配并调用本 Skill，无需显式输入 Skill 名称。

## 能力范围

Skill 会完成：

1. 识别客户及其主租户；
2. 从 C360 获取租户与最新使用指标；
3. 从指定 Aeolus 看板读取近 180 天累计或日均指标；
4. 按七个模块整理数据并生成洞见；
5. 创建飞书整体使用情况回顾文档；
6. 创建并回读检查飞书画板。

七个模块包括：

- 即时协同
- 会议协同
- 内容沉淀
- 多维表格
- 知识管理
- AI 赋能
- 服务台

本 Skill 不负责案例推荐、服务计划、场景共创、交互卡片或会后自动更新。

## 前置依赖

运行前需要具备：

- TRAE 的自定义 Skill 能力；
- 可用的 `lark-c360` CLI；
- C360 查询权限；
- Aeolus 看板访问权限及已登录的 ByteDance SSO 会话；
- 飞书文档与画板的创建、读取和更新权限；
- 可操作 Aeolus 页面的浏览器能力。

这些依赖包含内部数据源和权限。本仓库不会提供账号、凭据或真实客户数据。

## 安装

### 从 Release 安装

1. 打开仓库的 [Releases](https://github.com/yvwaiii/Feishu_Customer_BR/releases)；
2. 下载 `customer-business-review-skill.zip`；
3. 解压到工作区的 `.trae/skills/` 目录。

安装后的目录结构：

```text
.trae/skills/customer-business-review/
├── SKILL.md
├── README.md
└── references/
```

### 从源码安装

将仓库中的 `SKILL.md`、`README.md` 和 `references/` 复制到：

```text
.trae/skills/customer-business-review/
```

## 使用方法

安装后，用自然语言向 TRAE 提出客户使用回顾需求。例如：

```text
请为客户示例科技生成飞书整体使用情况回顾。
```

也可以直接提供主租户 F 码：

```text
请基于主租户 FXXXXXXXXXXX 生成近 180 天飞书使用回顾。
```

如果客户或主租户无法唯一确定，Skill 会先要求补充或确认，不会使用默认租户继续分析。

## 输入

至少提供以下任一信息：

- 客户正式名称；
- 客户简称；
- 主租户 F 码。

可选信息：

- 回顾背景；
- 计划回顾月份。

## 输出

一次完整运行会生成：

- 一份飞书整体使用情况回顾文档；
- 一张嵌入文档的飞书数据洞察画板。

文档包含：

- 数据口径与合规说明；
- 核心结论；
- 核心指标总览；
- 七模块完整数据与洞见。

画板采用单列七模块布局，每个模块展示 3～5 个关键指标。数据区使用固定五等分栅格，指标名称和数值居中对齐。

## 数据口径

- Aeolus 使用滚动近 180 天数据；
- C360 指标可能是最新快照；
- 不同口径会分别标注，不会混合比较；
- `180 天`不会改写成“半年”或“6 个月”；
- 派生指标只基于口径兼容的数据计算。

## 洞见原则

- 洞见基于多个指标之间的关系，而不是单项数据复述；
- 可分析规模、覆盖、结构、粘性、供给与消费关系；
- 上方已经展示的数据不会在洞见句中重复；
- 不根据相关性推断未经证实的原因；
- 不使用没有数据支撑的宣传口号。

## 数据安全

- 仓库不包含真实客户数据、租户编号、账号或访问凭据；
- README 中的效果图只使用虚构公司和示例数据；
- 运行过程中只读查询 C360，不写回客户数据；
- 生成的文档和画板仅展示统计指标，不应包含用户级敏感信息；
- 对外分享前，请再次确认访问权限和数据范围。

## 项目结构

```text
.
├── SKILL.md
├── README.md
├── assets/
│   └── board-preview.png
└── references/
    ├── aeolus-browser-runbook.md
    ├── bootstrap-and-recovery.md
    ├── data-and-insights.md
    ├── deliverables-and-lifecycle.md
    ├── reference-br-and-completeness.md
    ├── runtime-capability-and-notification.md
    ├── tool-routing.md
    └── workflow.md
```

详细执行规则请查看 `SKILL.md` 和 `references/`。
