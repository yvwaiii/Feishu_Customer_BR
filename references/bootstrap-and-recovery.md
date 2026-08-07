# 环境检测、安装与恢复

## C360 CLI 自举

运行 Skill 后先检测：

```bash
command -v lark-c360
lark-c360 --version
```

### 未安装

如 `command -v` 找不到 `lark-c360`：

1. 确认 `node` 和 `npm` 可用。
2. 自动安装：

```bash
npm install -g @customer360/lark-c360
```

3. 再次执行 `lark-c360 --version`。
4. 安装成功后继续，不要求用户另开会话。

如 npm 全局目录无写权限，使用当前 Agent 环境允许的 npm global prefix 安装；不要使用 `sudo`，不要修改系统 Node。

### 已安装但有诊断日志告警

`lark-c360 --version` 或业务命令可能出现：

```text
append diagnostic failed: ... operation not permitted
```

只要命令退出码为 0 且正常返回版本或业务 JSON，该信息是非阻塞诊断日志告警，不得误判为 CLI 不可用。记录到内部运行日志，继续执行。

## 环境与登录

```bash
lark-c360 env status --json
lark-c360 auth status --json
```

- 未登录、登录过期或无效时，按 `c360-shared` 的分步登录流程处理。
- 环境不是 online 时，切换到 online 后重新检查登录状态。
- 每个 JSON 输出都检查 `_notice.update`，按 `c360-shared` 规则提示，但不得自动升级。

## 输入快速路径

Skill 支持以下任一输入：

- 客户名称；
- 主租户 F 码；
- 客户名称 + 主租户 F 码。

### 客户名称路径

1. `account search` 获取唯一客户。
2. 查询该客户下全部关联租户。
3. 按 DAU 选主租户并取得 F 码。

### F 码路径

1. 用 `tenant list --keyword <F码>` 查询，并显式请求 `display_id`、`display_name`、`tenant_id`、`account`、`x7wd_avg_dau_suite`。
2. 只接受 `display_id` 与输入 F 码完全一致的唯一租户。
3. 从租户记录读取所属 account，再查询客户详情和该客户下全部关联租户。
4. 仍需按全部关联租户 DAU 验证该 F 码是否为主租户。
5. 若输入 F 码不是 DAU 最高租户，使用 DAU 最高租户继续，并向 CSM 说明自动切换结果。

租户显示名与所属客户名可能不同。两者必须分字段保存和展示，不得因为名称不同而否定关联，也不得把租户名覆盖客户正式名称。

## C360 查询恢复

- 字段不确定：先查 schema/meta，修正后最多重试一次。
- `code=100001` 或安全策略拦截：立即停止，不尝试绕过。
- 设备证书错误：严格按 `c360-shared` 处理，不移除证书要求。
- 客户、主租户、F 码无法确认：停止 BR 生成，让 CSM 补充。

## Aeolus 环境恢复

1. 打开固定看板后遇到 SSO：请用户完成一次登录，再自动继续。
2. 登录后浏览器会话可复用，后续不重复要求登录。
3. 找不到“企业编码（F/L码）”或日期筛选器：刷新一次并重新获取页面快照。
4. F 码无精确候选：停止，不使用近似匹配。
5. 查询完成但数据区为空：
   - 先验证筛选器标题中 F 码和日期是否正确；
   - 再等待看板查询完成并刷新一次；
   - 仍为空则记录为“该条件无有效数据”，不编造指标。
