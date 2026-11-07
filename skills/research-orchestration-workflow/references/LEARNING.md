# LEARNING.md · 跨会话连续性记忆（Anthropic Ralph Loop 模式）

> 本文件是 v2.1.0 Harness Engineering 的**跨会话记忆载体**。每个任务结束时，相关 agent **必须**追加一段 task 记录到本文件。
> 模型：Anthropic Ralph Loop（双相：Init agent 写 progress file → 后续 session 读取 → 接力）。
> 校验：`scripts/harness_eval.py` H9 检查本文件存在。

---

## 写入规则

每个 task 记录必含：
- **日期**：`YYYY-MM-DD`
- **agent_id**：哪个 agent 写入（domain-expert-biomed / -ai / -general / methodological-reviewer / synthesis-integrator / team-lead）
- **task_topic**：本次任务一句话主题
- **决策**：本次任务的关键决策（≤ 5 条 bullet）
- **证据**：关键证据（GRADE 等级 + 来源 DOI/PMID/URL）
- **下一步**：本任务的下一步建议（≤ 3 条 bullet）
- **observability**：4 个 metrics（成功率 / 平均 tool call / 重试次数 / next_actions 字段存在率）

---

## Task 记录（按时间倒序）

> 说明：以下 v2.2.0 补记的 5 条为**工程内证**——证据来源为本仓库真实 commit（short hash）、`CHANGELOG.md`、`README.md 版本历史` 与脚本 / 文件路径，不引用外部 DOI / PMID / URL；`observability` 因历史未逐任务采集，统一如实标注「未采集」，不自造数值。

### [2026-11-08] / team-lead / v2.3.0 残留风险工程化收口（R5 分级扩展 + R6 工具真实性）

- **决策**：
  - v2.2.0 发布时登记的 4 条残留风险中 3 条落为工程修复，1 条文档化收口，不「记录了事」
  - R5 分级解析扩展全 8 成员：atomic（registry 有 tools 行）沿用四类解析 + 双向相等；非 atomic（零工具授权）用 ①②③ 三类解析、任何工具 token 即 FAIL，跳过对中文叙述误报率高的 ④ `+` 槽位分支——不选「净化 MD 描述」路线，避免损失内容
  - 新增 R6 工具真实性：对照真实 MCP 清单（env `ROUTING_EVAL_MCP_JSON` → `~/.workbuddy/mcp.json`）硬校验 registry 全部 `mcp__` 名；清单不可得的 CI / git-clone 态显式 SKIP（⏭️ 标记，不计 FAIL 不影响 rc），安装态必须 PASS
  - 条目 4（validate_expert 硬编码安装路径）在 README 文档化为已知限制，不改官方脚本
  - 门禁总量 33 → 39 项（R5 3→8、R6 +1）
- **证据**：
  - `git fd23177` feat(v2.3.0)（R5/R6/文档收口/升版，7 files +304/-65）
  - `git 85e343c` fix(CI): N12 fixture 自包含化（见下方 lesson）
  - 实测：routing 39/39（R5 8/8 + R6 1/1）、selftest 12/12、R6 SKIP 分支空 HOME 下 rc=0、破坏验证非 atomic 注入 rc=1 / registry 注 GHOST_SERVER + 清单 rc=1、CI run 42420262814 success
  - Release：tag v2.3.0 → 85e343c，三源（canonical / GitHub / OneDrive 镜像）一致
- **下一步**：
  - CI tag 步骤曾把 tag 打在 CI-failure 的 fd23177 上，后重打到 85e343c——发布纪律补强：**tag 必须落在 CI 绿的 commit**，先看 run 结果再打 tag（已执行，记录防复发）
  - R6 的 SKIP 语义与 V4 同类：环境性 SKIP ≠ 门禁失败，但「39/39 全绿」在 CI 态实际是 38 项判定 + 1 项 SKIP，对外报告须注明
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：1（fd23177 CI 红后 85e343c 修复重推）
  - next_actions 存在率：2/2（两条均有下一步）

### [2026-11-07] / team-lead / v2.2.0 P0-1 恢复包根 settings.json + manifest C12 护栏

- **决策**：
  - 推翻 v2.1.2 后「宿主启动时必然删除 settings.json」的假设，恢复包根 `settings.json`
  - 官方 `validate_expert.py` 对 Team 型硬要求该文件（报错原文「Team type must have settings.json」），删除后官方校验出现 1 error
  - 反证：同格式的 agent-harness-expert 文件存活数周未被宿主删除，原假设不成立
  - `manifest_check.py` 63 → 64 项，新增 C12（Team 型 settings.json 存在 + 单键 agent 指向主理人），把「宿主误删」变成下次发行校验即报警
  - `manifest_check_selftest.py` 负例 17 → 21（N18 删除负例 / N19 篡改负例 / N20 旧团队规模表述 / N21 隐藏目录 marketplace.json 旧英文规模表述护栏，验证 C8 rglob 覆盖）
- **证据**：
  - `git 66d069b` fix(P0-1): 恢复包根 settings.json + manifest_check C12 护栏（2026-11-07）
  - `git 5fc2630` / `git 688dd92` 为当初删除该文件的两次 commit（2026-11-04），本版已 revert
  - `CHANGELOG.md §[2.2.0] Fixed`：官方 `validate_expert.py` 由 1 error → 0 error；C12、N18/N19/N20/N21 与 C8 的「旧团队规模表述（现为八agent / Eight-agent）」规则说明
  - `README.md 版本历史 v2.2.0`：「恢复包根 settings.json（官方校验 0 error）+ manifest C12 护栏」
- **下一步**：
  - 后续发行前跑 `python3 scripts/manifest_check.py -v` 确认 C12 仍绿
  - 若未来宿主真删除该文件，以 C12 报警为准，不等官方校验器事后报错
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-11-07] / team-lead / v2.2.0 P0-2 state_io.py 状态持久化与断点续跑

- **决策**：
  - 把 `agent-protocol.md §3` 的纸面 schema（八阶段状态机）变成确定性落盘：状态写入 `<workspace>/.harness-runs/<task_id>/_state.json`
  - 新增 `skills/research-orchestration-workflow/scripts/state_io.py`，五命令 init/advance/resume/finish/budget
  - 原子写（`.tmp` + `os.replace`）；退出码 0/1/2/3，JSON 损坏 fail fast 不静默重建
  - `state://cp-NNN` 伪 URI 绑定真实路径 `.harness-runs/<task_id>/checkpoints/cp-NNN.md`
  - team-lead.md 增「状态初始化与断点续跑」强制条款：开工 resume 盘点、阶段收尾 advance、撞限恢复不依赖对话记忆；写入者=仅主理人
- **证据**：
  - `git e73df63` feat(P0-2): 状态持久化落地 — state_io.py + 断点续跑条款（2026-11-07）
  - `CHANGELOG.md §[2.2.0] Added`：「八阶段状态的确定性落盘层」、原子写并发 20 路实测无损坏、rc 0/1/2/3 契约
  - `README.md 版本历史 v2.2.0`：「新增 state_io.py 状态持久化与断点续跑（治协议 §3 纸面 schema）」
  - `state_io.py` 文件头 docstring 明载五命令用法与退出码契约（仓库真实文件）
- **下一步**：
  - 新会话开工先跑 `state_io.py resume` 盘点「上次阶段 + 下一步」
  - 把本文件新增的 lesson 记录与 `state_io.py finish` 归档判断对齐
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-11-07] / team-lead / v2.2.0 P0-3 版本收口 2.2.0 + CHANGELOG 历史欠账补记

- **决策**：
  - 双 manifest version 由 2.1.2 收口到 2.2.0，README 头部同步
  - 补记 tag v2.1.2（`bb05e18`）之后 6 个「无版本号 commit」的 CHANGELOG 欠账（shim v3.4.2 跟升、vendor 联邦两级查找、settings.json 移除决策的推翻等）
  - 恢复「改必升版」纪律，避免长期不升版导致版本历史失真
  - README 三处过期同步：团队表 6 人→8 人（八人团队）、目录树补 vendor / tests / state_io 等、版本历史补 2.1.0 / 2.1.1 / 2.1.2 / 2.2.0
  - LEARNING.md 补 tag 后 5 条历史记录 + 新增「失败回流规则」落盘节
- **证据**：
  - `git 8fc83ca` chore(P0-3): 版本收口 2.2.0 + CHANGELOG 补账（tag v2.1.2 后 6 commit 欠账）（2026-11-07）
  - `CHANGELOG.md §[2.2.0]` 开头「从零独立诊断（15 项短板亲验）后的补全完善版」与 Regression evidence 表
  - `README.md 版本历史` 现有 v2.1.0 / v2.1.1 / v2.1.2 / v2.2.0 四条
  - `git bb05e18`（tag v2.1.2，2026-09-30）与 `git 0945fba`（其后无版本号基线，2026-11-04）
- **下一步**：
  - 保持「改必升版」：任何后续改动先升版再改 CHANGELOG
  - 本文件每条新 task 记录须带真实 commit hash 作证据，禁止口头补账
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-30] / team-lead / v2.1.2 协议 / 门禁加固：两套上限消歧义 + CI 纳入 H1-H12 + 注入式负例

- **决策**：
  - 修复 v2.1.0 atomic 拆分后 4 处 `domain-expert` 死引用，改为按领域标签 fan-out 到三个 atomic
  - **两套上限消歧义**：frontmatter `maxTurns: 180` = 平台层会话兜底；registry `max_turns: 30` = 编排层任务自控预算，两者不冲突
  - CI 新增 2 个 step：`Harness design checks (H1-H12)` 与 `Harness eval self-test`，把此前仅本地手动跑的 12+13 项检查纳入门禁
  - `manifest_check_selftest.py` N2 假绿根因：文案改为「五级仲裁」后 replace 精确串 mutation 空转；改为 append 式注入废弃表述，无论现文案如何都稳定触发校验器
  - 双 manifest version 2.1.0 → 2.1.2
- **证据**：
  - `git bb05e18`（tag v2.1.2）fix(v2.1.2): 补全 v2.1.0 atomic 拆分残留 + CI 纳入 harness 校验（2026-09-30）
  - `git 0945fba` 为 v2.1.2 之后的基线刷新（2026-11-04）
  - `CHANGELOG.md §[2.1.2]`：四处死引用、maxTurns 消歧义、N2 修复、`.github/workflows/validate.yml` 两个新 step
  - `README.md 版本历史 v2.1.2`：「回归 12/12 + 63/63 + 17/17 + 13/13」
- **下一步**：
  - 每次改校验器文案后跑 selftest，防 mutation 空转假绿复发
  - CI 门禁结果纳入本文件下一条记录的证据链
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-19] / team-lead / v2.1.1 新增 harness_eval_selftest.py（dev-only 注入式负例）

- **决策**：
  - 仅新增 1 个 dev-only 验证脚本，协议与运行时行为无变更，已安装实例无需重装
  - `scripts/harness_eval_selftest.py`：13 条注入式负例（当时口径；v2.2.0 新增 N13 后为 14 条）（N1-N12 + R1），对应 `harness_eval.py` 的 H1-H12 检查
  - 每条双断言：`rc=1`（反向用例 `rc=0`）+ 输出命中预期检查项文案，避免「校验器永久返回 0」的假绿
  - 首次跑暴露真实漏洞：selftest v1 跑出 10/13 失败，因 mutate 大小写敏感漏过 `Per-step Verification`；改用 `re.sub(..., flags=re.IGNORECASE)` 后 13/13 全过
  - 不接入 CI（与 `manifest_check_selftest.py` 同策略）
- **证据**：
  - `git 45dd4a9`（tag v2.1.1）test(harness): 新增 harness_eval_selftest.py — 13 条注入式负例（当时口径；v2.2.0 新增 N13 后为 14 条）（2026-09-19）
  - `git 7b1c75a` docs(changelog): v2.1.1 CHANGELOG 条目（2026-09-19）
  - `CHANGELOG.md §[2.1.1]` Added / Fixed 两节与 Regression evidence 表（`harness_eval_selftest.py` 从「❌ 不存在」→ 13/13 ✅）
  - `README.md 版本历史 v2.1.1`：「新增 harness_eval_selftest.py（dev-only 负例工具），运行时行为无变更」
- **下一步**：
  - 后续改 `harness_eval.py` 任一检查项，须同步补对应负例
  - 保持 dev-only 定位，不擅自接入 CI（变更需走版本升版）
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-18] / team-lead / v2.1.0 Harness Engineering 升级

- **决策**：
  - 拆 `domain-expert` 为 3 个 atomic subagent（biomed / ai / general），符合 Vercel / LangChain 实测的"工具最小化"
  - 引入 `agent-registry.md` 单一事实源（含 trigger / tools / safe/moderate/dangerous 权限档）
  - 引入 Loop 硬停止（max_turns=30 / max_time=1800s / max_token=200000 / circuit_breaker=5 次失败熔断）
  - 引入 plan_execution 元工具（Orchestrator Pattern 信号触发串行）
  - 引入 per-step verification（每步走 verification，不只 final-output）
  - 引入 4 个 observability metrics（成功率 / tool call / 重试 / next_actions 字段存在率）
  - 引入 LEARNING.md（Anthropic Ralph Loop 跨会话连续性）
- **证据**：

> ⚠️ 以下 4 条为设计时引用的**外部量化声称，本仓库未留存来源、未核实**，仅作设计动机记录，不得作为事实依据或对外引用。

  - LangChain: Terminal Bench 52.8% → 66.5%（仅改 Harness）
  - Vercel: 砍 80% 工具反而更准
  - Anthropic Harness Engineering: 任务成功率 ×2-3（不换模型）
  - METR 研究："先建 eval 再动 Harness"是 2026 分水岭
- **下一步**：
  - 跑 `scripts/harness_eval.py` 验证 12/12 通过
  - 写 `scripts/harness_eval_selftest.py` 注入式负例
  - 更新双 manifest / CHANGELOG / README
  - commit + force-with-lease push + tag v2.1.0 + Release + 同步 OneDrive
- **observability**：
  - 成功率：本任务 = 100%（plan → 5 phase 全部完成）
  - 平均 tool call：~30 次（web search ×5 + bash ×25）
  - 重试次数：0
  - next_actions 字段存在率：100%（每个 phase 结尾都有具体下一步）

---

## 模板（Copy-Paste 写入新记录）

```markdown
### [YYYY-MM-DD] / <agent_id> / <task_topic>

- **决策**：
  - ...
- **证据**：
  - ...（必带 GRADE + DOI/PMID/URL）
- **下一步**：
  - ...
- **observability**：
  - 成功率：...%
  - 平均 tool call：...次
  - 重试次数：...次
  - next_actions 字段存在率：...%
```

---

### [2026-11-07] / team-lead / 部署前两轮独立交叉验证发现门禁假绿与协议方向性错误

- **决策**：
  - 两轮独立交叉验证确认：发布门禁曾因「全文子串兜底词」出现假绿，协议信封校验方向一度指错版本，均须以仓库内真实规则为准收口
  - 权限档一律改为按 `###` 章节标题判定，不再用全文子串匹配，杜绝引言 / Changelog 兜底词放行被删章节
  - selftest 引入未归一化原始副本的 raw_probe 护栏，拒绝用「自愈夹具」把真实仓库的路由不一致归一化掉
  - 协议合规统一以 result_envelope v2.4 为当前判定，ACP v2.0 信封仅保留为历史 fixture 回归，不参与当前合规判定
  - 文档口径按脚本真实用例数收口；外部量化声称一律标注未核实，不得作为事实依据
- **证据**：
  - `scripts/routing_eval.py` R3：权限三档 safe / moderate / dangerous 必须作为 `###` 章节存在且正文非空（按章节标题判定，替代全文子串匹配）
  - `scripts/harness_eval.py` H6：`check_h6_permission_layer` 以 `^###\s+(safe|moderate|dangerous)\b` 取章节标题并校验正文非空
  - `scripts/routing_eval_selftest.py` raw_probe：准备阶段对未归一化原始副本直接跑 `routing_eval.py`，rc 非 0 即拒绝继续，不计入 CASES 用例数
  - `scripts/protocol_check.py`：`run_envelope_v24_tests` 主套件 16 用例（6 必填字段 + 小写四值 status），`run_legacy_envelope_tests` 12 用例仅作历史 fixture 回归
  - `scripts/manifest_check.py` C8：`FORBIDDEN_PATTERNS` 中「旧团队规模表述（现为八agent / Eight-agent）」规则，由 `scripts/manifest_check_selftest.py` N21 向隐藏目录下的 marketplace.json 注入旧规模表述，验证 C8 的 rglob 扫描覆盖；本文件不在 SCAN_EXEMPT 内，故此处不逐字复述被禁串以免触发 C8 自检
- **下一步**：
  - 冻结工作树后重跑全部门禁 + 交叉验证复查
  - 保持「改校验器必同步补负例」纪律，防止 mutation 空转假绿复发
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集

---

## 失败回流规则落盘（v2.2.0 · 确定性闭环）

> v2.1.0 协议 §6 只留了一句「失败回流为 harness 新规则（Hashimoto 模式）」的口头约定，没有落盘为可执行规则；v2.1.1 / v2.1.2 / v2.2.0 的失败与偏差因此没有形成可检索的 lesson 记录，进化回路停摆。本节把该约定固化为**确定性闭环**：触发即写、写完必验、未落地不算修好。

### 触发条件（五类，命中任一即回流）

1. **工具失败**：任一 tool call 返回错误、超时或限流（对齐协议 §6「瞬时 / 模型可恢复」两分类）
2. **撞熔断**：同一 task 失败累计触发 `circuit_breaker`（5 次）→ 自动熔断 + 升级用户
3. **校验器 rc=1**：`manifest_check.py` / `harness_eval.py` / `protocol_check.py` 及各自 selftest 任一返回非零
4. **用户纠偏**：用户明确否定当前产出、要求改方向或补证据
5. **中断续跑发现偏差**：`state_io.py resume` 读回的「上次阶段 / 下一步」与对话记忆或实际产物不一致

### 回流三件套（每条 lesson 必含，对齐协议 §6 与 team-lead「错误路径三件套」）

| 字段 | 含义 | 对齐来源 |
|------|------|---------|
| `root_cause_hint` | 人话版「为什么错」（非 stack trace） | `agent-protocol.md §6` Per-step Verification |
| `safe_retry_instruction` | 什么前提下可重试、不要改什么 | 同上 |
| `explicit_stop_condition` | 什么情况下必须停，不自己硬撞 | 同上；`team-lead.md` 错误路径三件套 |

> 三件套与协议 §6 的 `ERROR` payload（`category` / `detail` / `recovery_action` / `retry_count`）互补：前者写给**下一次会话的人**看，后者写给**当前运行时**用。

### [2026-11-08] / team-lead / lesson：CI 环境性假红（失败回流 · 部署实测抓出）

- **task_id / trace_id**：v2.3.0 部署 / CI run 42419531746（failure）→ 42420262814（success）
- **失败类别**：第 3 类「校验器 rc=1」（CI 实跑抓出；本质是 fixture 依赖外部环境）
- **现象**：本机 12/12 全绿，CI 仅 `Routing eval self-test` 一步红：N12 前置处理 `AssertionError: 本机无默认 MCP 清单，无法构造 R6 fixture: /home/runner/.workbuddy/mcp.json` → selftest 11/12
- **root_cause_hint**：N12 的 fixture 从 `~/.workbuddy/mcp.json` 复制——该路径只在开发机存在。**测试依赖了本机私有的外部环境 = 测试不自包含**，CI 天然必红。「本机全绿」与「CI 全绿」之间隔着环境差异，任何跨机断言必须在 CI 同构环境（空 HOME / 无 env）下预演过才算数。
- **safe_retry_instruction**：fixture 改为**自包含合成清单**（覆盖被测全集的真实 server 名 + 少量干扰项，使「真实名 PASS / 伪造名 FAIL」判据与真实清单等价）；修复后在「空 HOME + 无 env」模拟 CI 态复跑通过再推送。不要用「CI 上跳过 N12」的方式糊——那会让 R6 的负例保护在 CI 里永久失明。
- **explicit_stop_condition**：若修复重推后 CI 仍红且失败点不在本地可复现的用例上，停止自行重试，拉 `gh run view --log-failed` 逐行比对本地与 CI 输出差异，定位环境差异源后再动手。
- **已落地护栏**：`scripts/routing_eval_selftest.py` N12（自包含合成清单，SYNTHETIC_SERVERS 12 项含干扰项）；`git 85e343c`；「空 HOME 模拟 CI 态」纳入交付判据。**附带教训**：tag 曾打在 CI-failure 的 `fd23177` 上——发布纪律：**先看 CI run 结果、再打 tag**（本次已重打至 `85e343c`）。

### 写入位置与责任人

- **位置**：在本文件「## Task 记录」区追加一条 `lesson` 类记录，沿用四段模板，且额外必含 5 个字段：`task_id` / `trace_id` / 失败类别（五类之一）/ 根因（即 `root_cause_hint`）/ **已落地护栏的文件路径**
- **同步**：必要时调用 `python3 skills/research-orchestration-workflow/scripts/memory_log.py --type lesson --trace-id <trace_id> --note "<根因 + 护栏路径>"`，写入跨会话持久记忆层
- **责任人**：**成员只读，仅主理人（team-lead）写入**。成员命中触发条件时，把三件套随结果回传主理人，由主理人统一落盘，避免多头写入把本文件写散

### 护栏落地判据（防「口头已修复」）

- 每条失败**必须指向一个已存在的校验规则或脚本**（如 `manifest_check.py` 的 C12、`harness_eval.py` 的 H9、`manifest_check_selftest.py` 的某条负例），并把该路径写进 lesson
- 若一时无对应规则，状态标为 **「未闭环」**，并在「下一步」里写明「补哪条规则 / 哪个脚本」；**不得写「已修复」**
- 判据一句话：`grep` 能在本文件找到该 lesson，且该路径在仓库真实存在、`rc` 可复跑，才算闭环

### 验证方式（下次会话开工必跑）

1. 跑 `python3 skills/research-orchestration-workflow/scripts/state_io.py resume --task-id <task_id> --workspace <path>` 读回断点
2. 跑全部校验脚本：`manifest_check.py` / `manifest_check_selftest.py` / `harness_eval.py` / `harness_eval_selftest.py` / `protocol_check.py`，确认基线未破
3. `grep -n "<trace_id>" skills/research-orchestration-workflow/references/LEARNING.md` 确认该条 `lesson` 记录已落盘，且含 task_id / trace_id / 失败类别 / 根因 / 护栏路径 5 字段
4. 若某条 lesson 仍标「未闭环」，优先补规则再继续新 task，不让欠账跨会话累积

---

## 跨会话连续性协议（Ralph Loop）

每个新 session 启动后：
1. **读取**本文件（git log + LEARNING.md）
2. **识别**最高优先级未完成 task（按时间倒序 + "下一步"标签）
3. **校验**跑全部校验脚本（manifest_check / harness_eval / protocol_check 及各自 selftest）确认基线未破
4. **处理**该 task
5. **提交**到 git
6. **追加**新一段 task 记录到本文件
7. **循环**直到 30 turns / 30min / 200k tokens 任一触发 → compact / circuit breaker