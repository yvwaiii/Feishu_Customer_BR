# 环境检测、安装与恢复

## C360 CLI 自举

运行 Skill 后先检测：

```bash
command -v lark-c360
lark-c360 --version
```

### 未安装

如 `command -v` 找不到 `lark-c360`：

1. 不要执行 `npm install -g @customer360/lark-c360`。该包不发布到公共 npm，公共 registry 返回 404 是预期行为。
2. 执行 Skill 内置的官方 TOS 自举脚本：

```bash
C360_BIN="$(bash <当前Skill根目录>/scripts/bootstrap-lark-c360.sh)"
"${C360_BIN}" --version
```

3. 脚本读取官方 manifest，下载 `npm_package.latest_archive`，校验 SHA256 后安装。
4. Aily 环境安装到 `${AILY_WORKSPACE}` 或 `~/.aily/workspace`；其他环境安装到可写的用户目录。
5. 后续命令使用脚本返回的绝对路径 `${C360_BIN}`，不要依赖当前 shell 的 PATH 已刷新。
6. 安装成功后继续，不要求用户另开会话。

官方 manifest：

```text
https://lf-ldic360.feishucdn.com/obj/ldi-c360/cli/lark-c360/manifest.json
```

不要使用 `sudo`，不要修改系统 Node，不要从第三方镜像下载。

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

Aily 未登录时：

```bash
"${C360_BIN}" env use online
"${C360_BIN}" auth login --no-wait --json
```

把返回的 `authorize_url` 交给用户。用户完成授权后的下一轮执行：

```bash
"${C360_BIN}" auth login --resume
```

登录状态保存在 `~/.aily/workspace/.lark-c360/config`，不要写到任务级 workdir。

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

### 断点续跑

启动时检查当前工作目录的 `artifacts/`，并检查持久化目录。若存在本次客户的 C360 数据存档：

1. 读取存档中的客户名称、主租户名称、F 码、查询时间和七模块字段；
2. 与当前输入交叉校验；
3. 客户和 F 码一致、七模块数据完整时直接复用，不重复查询 C360；
4. 从运行模式选择、coverage matrix、画板和文档生成继续；
5. 存档身份不一致、字段不完整或无法判断来源时才重新查询。

路径规则：

- 用户给出的绝对路径仅作为线索，必须先检查文件是否在当前沙箱可读；
- `/home/gem/.aily/workdir/<task>/...` 属于任务级临时目录，不得假设下一次 Aily 运行仍可访问；
- Aily 持久化副本写入 `~/.aily/workspace/artifacts/customer-business-review/<F码>/c360-data.md`；
- 当前任务同时写入 `./artifacts/BR_<客户简称>_C360数据.md`，方便本次后续步骤读取；
- 声明的存档路径不可读时，不要停止；先查持久化副本，再使用已安装的 C360 CLI 重新查询。

使用内置脚本解析或保存：

```bash
# 解析：旧绝对路径可读则返回旧路径，否则查 Aily workspace 持久化副本
C360_ARTIFACT="$(bash <当前Skill根目录>/scripts/cache-c360-artifact.sh resolve <F码> "<任务方声明的路径>" || true)"

# 重新查询并写入当前任务 artifacts 后，保存持久化副本
bash <当前Skill根目录>/scripts/cache-c360-artifact.sh save <F码> "./artifacts/BR_<客户简称>_C360数据.md"
```

`resolve` 没有返回路径时，表示没有可复用数据，应继续安装/登录 C360 并重新查询，不得以“旧路径不可访问”为由终止。

Aily 默认 Skill 根目录为：

```text
~/.aily/workspace/skills/customer-business-review
```

不要假设当前工作目录就是 Skill 根目录。

- 字段不确定：先查 schema/meta，修正后最多重试一次。
- `code=100001` 或安全策略拦截：立即停止，不尝试绕过。
- 设备证书错误：严格按 `c360-shared` 处理，不移除证书要求。
- 客户、主租户、F 码无法确认：停止 BR 生成，让 CSM 补充。

## Aeolus 环境恢复

0. 先判断运行环境。Aily、云端沙箱或无法访问 ByteDance 内网时，不执行后续浏览器恢复步骤，直接切换到 C360 快照模式。
1. 打开固定看板后遇到 SSO：请用户完成一次登录，再自动继续。
2. 登录后浏览器会话可复用，后续不重复要求登录。
3. 找不到“企业编码（F/L码）”或日期筛选器：刷新一次并重新获取页面快照。
4. F 码无精确候选：停止，不使用近似匹配。
5. 查询完成但数据区为空：
   - 先验证筛选器标题中 F 码和日期是否正确；
   - 再等待看板查询完成并刷新一次；
   - 仍为空则记录为“该条件无有效数据”，不编造指标。

出现 `SSL_PROTOCOL_ERROR`、内网 DNS 失败或网络不可达时：

- 视为环境能力限制，不视为客户数据查询失败；
- 不使用 WebFetch、curl、代理或其他方式绕过内网限制；
- 不重复尝试沙箱浏览器和本地浏览器；
- C360 七模块完整时，继续生成 C360 快照版。
