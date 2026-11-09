# Agent Registry · 团队能力单一事实源

> 本文件是 v2.1.0 路由机制的核心：主理人（沈知枢）通过本文件做**动态路由 + 权限分级 + 触发条件匹配**，取代 v2.0 静态决策树。
> 单一事实源（SSOT）：任何 agent 的能力、工具、权限变更必须同步更新本文件。
> 校验：CI 跑 `scripts/harness_eval.py` 检查本文件存在 + 含 `trigger` / `tools` / 权限档位（safe/moderate/dangerous）三个字段。

---

## 团队成员一览

| agent_id | displayName | 角色 | 领域标签 | 状态 |
|----------|-------------|------|---------|------|
| `research-orchestration-team-team-lead` | 沈知枢 | 编排者 / Orchestrator | 主理人 | always-on |
| `socratic-questioner` | 问清源 | 分析者 / Analyzer | 苏格拉底追问 | always-on（FREEZE 阶段常驻） |
| `meta-architect` | 梁构局 | 分析者 / Analyzer | 问题结构 / 跨域节点 | always-on |
| `domain-expert-biomed` | 博域闻·生医 | 执行者 / Executor (atomic) | 生物医药（PubMed/GISAID/兽医/分子生物学/流行病学） | 按需 |
| `domain-expert-ai` | 博域闻·AI | 执行者 / Executor (atomic) | AI/大模型/RAG/Agent/生信/蛋白设计 | 按需 |
| `domain-expert-general` | 博域闻·通识 | 执行者 / Executor (atomic) | 通用研究方法/教育/管理/政策/统计 | 按需 |
| `methodological-reviewer` | 严复回 | 审查者 / Reviewer | 证据等级 / 复评闭环 | always-on（REVIEW 阶段常驻） |
| `synthesis-integrator` | 顾合璧 | 整合者 / Integrator | 多源融合 / 冲突仲裁 / 共识矩阵 | always-on（NEXT 阶段常驻） |

> **变化说明**：v2.1.0 起，原 `domain-expert` 拆为 3 个 atomic subagent（biomed / ai / general），符合 Vercel / LangChain 实测的"工具最小化、atomic 优于集成"原则。每个 atomic 能力边界更窄，工具调用更明确。

---

## 触发条件（trigger · 用于 semantic routing）

主理人通过以下关键词 + 任务领域标签做动态路由（取代 v2.0 静态决策）：

### research-orchestration-team-team-lead（沈知枢）
- **trigger**: 科研规划 / 选题 / 立题 / 投资方向 / 编排 / 仲裁 / 融合 / 复评
- **routing**: 自身路由到合适的 subagent 组合（Orchestrator Pattern）

### socratic-questioner（问清源）
- **trigger**: 澄清 / 信息完整度 / 假设密度 / 风险评估
- **stage**: FREEZE → CLARIFY（信息完整度 < 90% 时触发）
- **routing**: 与 free-form 任务强相关，几乎 always-on

### meta-architect（梁构局）
- **trigger**: 结构分解 / 跨域节点 / 骨架设计 / 中观跨域研究
- **stage**: IDENTIFY → COLLAPSE（任务复杂时触发）
- **routing**: 复杂任务（多步骤 / 多领域）才调

### domain-expert-biomed（博域闻·生医）
- **trigger**: 生物医药 / PubMed / GISAID / 流感 / 禽流感 / 兽医 / 分子生物学 / 流行病学 / 病原 / 序列 / 基因 / 蛋白 / 疫苗 / 抗原 / 宿主范围 / H5 / H10 / NHRAI / GAR
- **stage**: EXECUTE（领域深挖时触发）
- **tools**: `WebFetch` / `WebSearch` / `mcp__biomcp` / `mcp__pubmed` / `mcp__semantic-scholar` / `mcp__biorxiv-mcp-server`
- **routing**: 任务领域标签 = `biomed` 时由 meta-router 调度

### domain-expert-ai（博域闻·AI）
- **trigger**: AI / 大模型 / LLM / GPT / Claude / 深度学习 / 神经网络 / RAG / Agent / 多智能体 / LoRA / QLoRA / 微调 / 推理 / 强化学习 / 蛋白设计 / AlphaFold / ESMFold / 生信管道 / Python / R
- **stage**: EXECUTE
- **tools**: `WebFetch` / `WebSearch` / `mcp__arxiv-mcp-server` / `mcp__semantic-scholar` / `mcp__context7` / `mcp__fetch`
- **routing**: 任务领域标签 = `ai` 时

### domain-expert-general（博域闻·通识）
- **trigger**: 统计 / 方法学 / 教育 / 教学 / 管理 / 社会科学 / 政策 / 研究设计 / 问卷 / 实验设计 / 样本量 / meta 分析 / 文献综述 / PRISMA / GRADE / CONSORT / STROBE
- **stage**: EXECUTE
- **tools**: `WebFetch` / `WebSearch` / `mcp__semantic-scholar` / `mcp__tooluniverse` / `mcp__web-scout`
- **routing**: 任务领域标签 = `general` 时

### methodological-reviewer（严复回）
- **trigger**: 证据等级 / 方法学合规 / 复评闭环 / 升档 / 降档 / 止损
- **stage**: REVIEW（必触发）
- **routing**: always-on 审查者

### synthesis-integrator（顾合璧）
- **trigger**: 整合 / 融合 / 汇总 / 冲突 / 仲裁 / 共识 / 综合报告 / 多源合并
- **stage**: REVIEW → NEXT（仲裁 + 汇总）
- **routing**: always-on 整合者

---

## 工具与权限（authz · 三档分级）

> 2026 主流做法：safe / moderate / dangerous 三档，禁止发"全能 token"。
> 本表所列工具名以本文件各成员条目的 `tools` 行为唯一事实源，不得出现 `tools` 行之外的工具名；`Read / Grep / Glob` 为宿主内置只读工具、仅适用于分析者/整合者，不受此限。

### safe（自动放行 + 审计日志）

| 工具 | 适用 agent |
|------|-----------|
| `WebFetch` / `WebSearch` | 所有执行者 |
| `mcp__biomcp` / `mcp__pubmed` / `mcp__semantic-scholar` / `mcp__biorxiv-mcp-server` | domain-expert-biomed |
| `mcp__arxiv-mcp-server` / `mcp__context7` / `mcp__fetch` | domain-expert-ai |
| `mcp__semantic-scholar` / `mcp__tooluniverse` / `mcp__web-scout` | domain-expert-general |
| `Read` / `Grep` / `Glob`（本地文件读取） | 所有分析者 / 整合者 |

### moderate（记录 + 二次确认）

| 工具 | 适用 agent | 二次确认规则 |
|------|-----------|--------------|
| `Write` / `Edit`（本地文件修改） | 所有"调我改 SKILL/registry"的 agent | 改动前说明意图 + 受影响文件列表 |
| `Bash`（git commit / push） | 主理人 | 仅限发布流程的预定义命令 |
| 各成员 tools 行中已声明的 MCP 检索源（高级批量检索） | 三个 atomic 执行者（仅限各自已声明的源） | 批量/高频调用须二次确认；不得越权调用他成员声明的源 |

### dangerous（强制人审 + 回滚 + 仅隔离环境）

| 工具 | 适用 agent | 强制人审条件 |
|------|-----------|--------------|
| 发邮件 / 部署 / 删数据 / 改训练数据 | **禁止** | — |
| `gh release create` / `gh repo` | 主理人（仅 B 方案清理） | 必须经用户确认 |
| `git push --force` / `rm -rf` | 主理人 | 必须经用户确认 |
| 模型微调 / 训练启动 | **禁止** | — |

---

## 工具降级链（v2.2.0 · 单点故障规避）

> 背景：本文件的 `tools` 字段已按本机 `~/.workbuddy/mcp.json` 实测的 45 个 server 名与宿主内置工具校准。任何单一检索源超时 / 鉴权失败 / 无结果时，执行者**不得静默跳过检索**，必须按下列三级链降级，保证证据链不断裂、信封始终合规。

### ① 首选源不可用

触发条件：首选 MCP server 超时、鉴权失败、返回空结果或接口报错。此时**不得因单源失败静默跳过检索**，也不得直接以「未检索到」收尾，须立即进入 ②；切换动作记入 `issues` 与 `evidence[].used_for`。

### ② 同类换源

在同一领域内按「首选 → 次选 → 兜底」依次切换；每次切换记录失败原因与替代源。表内全部为宿主内置工具或本机实测存在的 server：

| 领域 | 首选 | 次选 | 兜底 |
|------|------|------|------|
| biomed | `mcp__pubmed` / `WebSearch` | `mcp__biomcp`（~30 源统一语法）/ `mcp__semantic-scholar` / `mcp__biorxiv-mcp-server`（预印本 / 新颖性核查） | `WebFetch`（PubMed / 期刊官网公开网页）/ `WebSearch` |
| ai | `mcp__arxiv-mcp-server` / `WebSearch` | `mcp__semantic-scholar` / `mcp__context7` / `mcp__fetch` | `WebFetch`（arXiv / 会议官网公开网页）/ `WebSearch` |
| general | `mcp__semantic-scholar` / `WebSearch` | `mcp__tooluniverse` / `mcp__web-scout` | `WebFetch`（公开政策网页 / 行业白皮书）/ `WebSearch` |

### ③ 三源全败则降置信输出

首选、次选、兜底全部失败时，仍须回传一个合规但降级的信封，不得空回、不得编造：

- **confidence 上限**：≤ 40，且显式标注为「未经在线核实」的估计值，禁止给高分。
- **evidence 标注**：每条 evidence 的 `grade` 或 `used_for` 中标注 `source_unavailable`，并写明三源失败的具体原因（超时 / 鉴权 / 空结果 / 接口报错）。
- **禁止编造数据**：不得虚构 DOI / PMID / arXiv ID / URL / 数值 / 结论；确无证据时如实写「未检索到」，并区分「关键词问题」与「真空白」。
- **6 必填字段齐全**：`agent_id` / `task_id` / `phase` / `status` / `confidence` / `deliverable_summary` 一个不少（对齐 `references/agent-protocol.md` §2）。
- **status 取值**：`partial`（仍有部分可用信息）或 `blocked`（完全无可用信息）；**禁止**填 `success`。
- **后续动作**：`issues` 与 `next_agent_hint` 必须给出补检建议（重试源 / 换关键词 / 请主理人介入或升级用户）。

---

## 路由策略（Orchestrator Pattern · 两步）

### 步骤 1：Route（一次 LLM 调用）

读任务 + Pre-flight Contract（若已有）→ 选 1-3 个 agent：

- **独立并行**：fan-out 给多个 atomic subagent（domain-expert-biomed / ai / general 三个 atomic 可独立调用）
- **依赖串行**：触发 `plan_execution` 元工具信号，严格依赖图执行（如先问清源 → 元架构师 → 执行者 → 严复回 → 顾合璧）

### 步骤 2：Execute（确定性执行）

- **Parallelism** = 多个 atomic subagent 并行 fan-out → 汇总
- **Sequential** = plan_execution 信号触发依赖图
- **Loop** = 质量阈值未达 → 重做（**硬上限 5 次**）

### 步骤 3：Synthesize

整合者顾合璧汇总 + per-step verification（每个步骤都走 verification，不只是 final-output）。

---

## 交叉领域组合路由模板（v2.2.0 · 补 F9）

> v2.1.0 的 atomic 拆分解决了单领域路由，但**跨领域任务**没有固定组合模板：主理人每次临时拼装 fan-out，容易漏掉一侧、或让单领域成员给跨域结论背书。本节把高频组合固化为可复用模板，供步骤 1 的 Route 直接命中。
> 判定：任务命中**两个及以上**领域标签（biomed / ai / general）时必须套用下表；未显式标注领域标签的，退回 `socratic-questioner` 在 FREEZE → CLARIFY 阶段先澄清，不得猜。

| 组合 | 典型任务 | 触发词交集（两侧各至少 1 个） | 并行 fan-out | 串行依赖与仲裁 |
|------|---------|------------------------------|--------------|----------------|
| **biomed × ai** | 用蛋白语言模型预测 H5 HA 糖基化位点的免疫逃逸 | biomed：禽流感 / 抗原 / 序列 / 宿主范围；ai：大模型 / 蛋白设计 / AlphaFold / 生信管道 | `domain-expert-biomed` + `domain-expert-ai` 同时发 | 先由 `meta-architect` 拆「生物学假设 / 计算可行性」两侧 → 两执行者各自出具 evidence → `methodological-reviewer` 分别按 GRADE 与模型基准复评 → `synthesis-integrator` 融合。**生物学结论不得由计算侧单方定论**；evidence 须分别带 PMID/DOI 与模型版本/基准名 |
| **biomed × general** | 禽流感疫苗株推荐的成本-效果与流行病学证据综合 | biomed：流感 / 流行病学 / 疫苗；general：meta 分析 / GRADE / 样本量 / 政策 | `domain-expert-biomed` + `domain-expert-general` | 严复回先统一证据等级口径（GRADE 优先于样本量口径）→ 顾合璧生成共识矩阵，冲突按 L1 证据等级命中即止 |
| **ai × general** | 兽医大模型评测基准与教学评估量规设计 | ai：LLM / 微调 / 推理 / Agent；general：研究设计 / 问卷 / Rubric / 统计 | `domain-expert-ai` + `domain-expert-general` | general 侧定义样本量与量规、ai 侧定义基准与指标，两侧产出经 `methodological-reviewer` 复评后融合；禁止用模型自评替代独立量规 |

**跨组合三条硬规则（任何模板都适用）**：

1. **不猜标签**：领域标签集合必须由任务文本或用户确认得出；缺标签 → 走 CLARIFY，不进 EXECUTE。
2. **不引用未落盘结论**：并行的两个 atomic 成员不得互相引用对方尚未落盘的中间结论；一律用 `context_ref.mode = ref` + `state://cp-NNN` 指向检查点（协议 §4、§3）。
3. **跨域结论不得单方定论**：最终综合报告必须由 `synthesis-integrator` 按 L1 证据等级 → L2 置信度 → L3 角色权威 → L4 主理人 → L5 用户裁决的五级链仲裁；任一领域成员不得单独给跨域结论盖章。

---

## Loop 终止硬上限（circuit breaker）

| 上限 | 数值 | 说明 | 代码落点（`skills/research-orchestration-workflow/scripts/state_io.py`） |
|------|------|------|-----------------------------------|
| max_turns | 30 | 单任务总轮次 | 常量 `DEFAULT_MAX_TURNS` → 落盘 `budget.turns_max`；`budget` 子命令触顶告警；覆写 `--max-turns` |
| max_time | 1800s (30 分钟) | 单任务总时长 | 常量 `DEFAULT_MAX_TIME` → 落盘 `budget.max_time_sec`（起算点 `budget.started_at`，与 `created_at` 同值）；`advance` / `resume` / `budget` 超时即拒绝推进并置 `status=aborted`；覆写 `--max-time` |
| max_token | 200,000 | 单任务总 token 消耗 | 常量 `DEFAULT_MAX_TOKENS` → 落盘 `budget.tokens_max`；`budget` 子命令触顶告警；覆写 `--max-tokens` |
| circuit_breaker | 失败 5 次 | 同一 task 失败 5 次 → 熔断 + 升级用户 | 常量 `DEFAULT_MAX_FAILURES` → 落盘 `budget.max_failures`；`fail` 子命令累计 `budget.failures`，达上限即熔断；覆写 `--max-failures` |

> **`--max-*` 的生效范围**：仅 `init` 与 `budget` 子命令接受覆写；`advance` / `resume` / `finish` 传入会被忽略并告警（避免中途改预算导致前后不可比）。

### 按序推进门禁

`state_io.py advance` 强制**按 `PHASES` 顺序推进**，跳级即拒绝（rc=1）：

| 情形 | 判定 | 退出码 |
|------|------|--------|
| init 后第一次 advance 到 `FREEZE` | 合法（`turn == 0` 且 checkpoints 为空且 `phase == PHASES[0]`） | 0 |
| 跳级（如 FREEZE 直接到 EXECUTE） | 拒绝 | 1 |
| 重复推进同一阶段 | 拒绝 | 1 |
| 顺序推进到下一阶段 | 通过 | 0 |

**逃生阀**：`--force` 可跳过顺序门禁，但**必须**同时给 `--force-reason`（非空）。`--force` 缺 reason → rc=1；`--force-reason` 非空即隐含 force（无需再写 `--force`）。逃生阀的每次使用都必须记入 `issues` 与 `LEARNING.md`，否则视为绕过门禁。

### 熔断后的状态语义（`status: aborted`）

| 字段 | 取值 | 含义 |
|------|------|------|
| `status` | `running` / `done` / `aborted` | `aborted` = 熔断归档，**不可再推进** |
| `abort_reason` | `null` / `max_time` / `circuit_breaker` | 熔断原因 |

熔断后的行为约定：
- `advance` / `fail` 一律 rc=1（不再接受任何推进与失败计数）。
- `finish` **仍可执行**（用于归档 metrics 与写收尾备注），但**不得改写** `status=aborted`——收尾不等于翻案。



---

## Plan-execution 元工具（信号触发串行）

`plan_execution` 是一个**信号而非函数**。当 LLM 调用它时，主理人切换到串行执行模式：

```yaml
plan_execution:
  description: "Use this ONLY when the query requires sequential steps
                where a later step DEPENDS on the result of an earlier step."
  parameters:
    reason: { type: string, required: true }
```

---

## 评估与观测（observability）

### 必须收集的 4 个 metrics

| 指标 | 含义 | 落盘键 | 推导 vs 上报 |
|------|------|--------|-----------|
| 成功率 | 每个任务类型的成功数 / 总数 | `metrics.success_rate` | **可推导**——由状态文件的成功/失败计数算出 |
| 平均 tool call 次数 / 任务 | 工具调用频次 | `metrics.avg_tool_calls_per_task` | **仅上报**——脚本无从推断（调用记录分散在成员信封里），须主理人显式上报 |
| 重试次数 / 任务 | 错误回流统计 | `metrics.retries_per_task` | **可推导**——由 `budget.failures` 算出 |
| 失败时 next_actions 字段存在率 | 错误路径设计质量 | `metrics.next_actions_presence_rate` | **仅上报**——同上，脚本拿不到 `next_actions` 字段 |

**未上报记 `null`，禁止编造**：4 个键中凡主理人未上报的，落盘一律为 `null`（不是 0、不是空串）。编造数值比缺失更危险——缺失会被发现，编造会被当真的用。

**上报方式**：`state_io.py finish --task-id <id> --workspace <ws> --tool-calls <n> [--next-actions-present | --next-actions-missing]`（可重复调用；后一次不带上报参数会**保留**上次已上报的真实值，不会擦成 `null`）。

### 门禁体系现状

本包的发布门禁分三层：**正向校验器**（干净仓库应全绿）、**注入式负例自测**（证明校验器不是永远返回 0）、**联邦防漂移门禁**（防 vendor 副本被静默改写）。各层条数以脚本实测为准：

| 层 | 门禁 | 检查项 | 覆盖什么 |
|----|------|--------|---------|
| 正向 | `scripts/manifest_check.py` | **C1–C13（73 项）** | 双 manifest 对等 / 资产完整性 / 版本一致 / 废弃表述 / 契约章节 / frontmatter 结构 / **成员 ID 五处一致性** / Team settings.json |
| 正向 | `scripts/harness_eval.py` | **H1–H12（12 项）** | Harness Engineering 设计模式退化（路由单一事实源、Loop 硬停止、per-step verification 等） |
| 正向 | `scripts/routing_eval.py` | **R1–R6（39 项）** | 成员集合 / 触发词 / 条目结构 / 工具名形态 / 工具集合双向相等 / 真实 MCP 清单对照（R6 清单不可得时显式 SKIP，不计 FAIL） |
| 正向 | `skills/research-orchestration-workflow/scripts/protocol_check.py` | **信封 37 / 冲突仲裁 5 / 集成仿真 9** | 协议合规三层判定（信封字段 + 证据链 + HANDOFF 回引覆盖） |
| 负例 | `scripts/manifest_check_selftest.py` | **26 条** | 见下方「注入式负例」 |
| 负例 | `scripts/harness_eval_selftest.py` | **14 条** | H1–H12 每项被破坏时都能检出 |
| 负例 | `scripts/routing_eval_selftest.py` | **12 条** | R1–R6 各类路由破坏（含 raw_probe 未归一化护栏，不计入用例数） |
| 负例 | `skills/research-orchestration-workflow/scripts/protocol_check_selftest.py` | **13 条** | 三个 suite 的退出码链路与判定分支真实有效 |
| 负例 | `scripts/test_phase_normalization.py` | **26 条** | `--phase` 阶段名归一化 shim 的映射与透传 |
| 防漂移 | `tests/test_vendor_core.py` | **V1–V6（6 项）** | `vendor/shared-core/` 与联邦真源 sha256 比对（真源不可达时显式 SKIP，不计 FAIL） |

**「注入式 selftest」的含义**：把仓库复制到临时目录 → 注入一处破坏 → 断言校验器 **rc=1** 且输出命中**预期的检查项文案**。第二个断言不可省略：只断言退出码会让「任何错误都算通过」，检查项本身失效也会被误判为通过——这正是本项目历史上假绿的成因。

### 注入式负例

`scripts/harness_eval.py` 提供 H1-H12 正向校验，`scripts/harness_eval_selftest.py` 提供 14 条注入式（mutation-based）负例；两者均已纳入 CI（见 `.github/workflows/validate.yml` 中名为 `Harness design checks (H1-H12)` 与 `Harness eval self-test (mutation-based)` 的两个 step；按 step 名定位，不依赖行号）：
- **H1-H12 正向校验**：`python3 scripts/harness_eval.py`（干净仓库期望 rc=0）
- **14 条注入式负例（N1-N13 + R1）**：`python3 scripts/harness_eval_selftest.py`（逐条把仓库复制到临时目录、注入一处破坏，断言校验器 rc=1 且命中预期检查项文案；R1 为语义不变的反向放行用例）
  - N13 删除整个 `### moderate` 权限档章节（标题+正文），验证 H6 已改为按 `^### (safe|moderate|dangerous)` 章节标题判定，不再被 Changelog 里的兜底词放行
- `scripts/routing_eval_selftest.py` 为 12 条（P1 + N1~N10 + N12；N11 并入 P1 正例），其中 `raw_probe` 是准备阶段护栏、不计入用例数，作用是对未归一化的原始副本直跑 `routing_eval.py`，防止 `sanitize_pristine` 自愈夹具掩盖真实仓库的 R2/R4 缺陷。R5 已扩展到全部 8 个成员（非 atomic 走 ①②③ 类解析、零工具授权，跳过误报率高的 ④ 槽位分支）；R6 对照真实 MCP 清单校验 registry 全部 `mcp__` 名，清单不可得的 CI/git-clone 态显式 SKIP 且不计 FAIL。
- `scripts/manifest_check_selftest.py` 为 26 条，含 N21 验证 C8 的 rglob 扫描覆盖隐藏目录下的 `.claude-plugin/marketplace.json`、N22/N23 验证 C8 声明式豁免（负例拦截 / 正例护栏）、N24/N25/N26 验证 C13 成员 ID 五处一致性（协议 §1 角色矩阵 / registry 团队成员一览 / team-lead 成员表 / 双 manifest 的 agents[]、members[].id、teamInfo 与 `agents/*.md` 文件名真值源对齐）。
- `skills/research-orchestration-workflow/scripts/protocol_check_selftest.py` 为 13 条注入式负例（P1/N1/N2/P2 + N3–N7 + P3 + N8/N9/N10），逐条把脚本复制到临时目录、注入一处破坏、断言 rc 翻转（0→1）且命中预期检查项文案；P3 另以干净副本跑全量 suite 断言 rc=0，防「负例全红」掩盖校验器整体失效。
- `scripts/test_phase_normalization.py` 为 26 条，验证 `assemble_spawn_prompt.py` 的 `--phase` 参数归一化：8 个阶段名 × 两种写法（`--phase X` / `--phase=X`）、大小写不敏感、整数透传、非法值透传给 argparse 报错（rc=2）、缺值不崩溃。

### 相关模板

| 模板 | 用途 |
|------|------|
| `../templates/cross-domain-combo.md` | 上节「交叉领域组合路由模板」的可填执行单（biomed×ai / biomed×general / ai×general 三组合的 fan-out、依赖链、仲裁链、硬上限登记与自检清单） |
| `../templates/result-envelope-v2.4.json` | result_envelope v2.4 的空白信封模板（6 必填字段名与 `../scripts/protocol_check.py` 的 `REQUIRED_FIELDS_V24` 逐字一致） |

---

## 跨会话连续性（LEARNING.md · Ralph Loop）

每次任务结束，agent 必须追加一条到 `references/LEARNING.md`：

```
## [YYYY-MM-DD] / [agent_id] / [task_topic]
- 决策：...
- 证据：...
- 下一步：...
```

文件不存在时由主理人创建并写入模板。

---

## Changelog

- **v2.1.0 (2026-09-18)**：新增本文件。取代 v2.0 静态决策树。
  - 引入 atomic subagent 拆分（biomed / ai / general）
  - 引入 safe/moderate/dangerous 三档权限分级
  - 引入 plan_execution 元工具（信号触发串行）
  - 引入 max_turns / max_time / max_token / circuit_breaker 硬上限
  - 引入 4 个 observability metrics
- **v2.2.0 (2026-11-07)**：工具名实测校准 + 单点故障规避。
  - 依据本机 `~/.workbuddy/mcp.json` 实测的 45 个 server 名，校准三个 atomic 执行者的 `tools` 字段与 safe / moderate 权限表：移除本机未登记的 MCP 名与非工具名占位表述，全部替换为真实名（`mcp__pubmed` / `mcp__biomcp` / `mcp__arxiv-mcp-server` / `mcp__semantic-scholar` / `mcp__context7` / `mcp__tooluniverse` / `mcp__web-scout` / `mcp__fetch` / `mcp__firecrawl`）与宿主内置工具；`trigger` / `tools` / `stage` / `routing` 字段与 safe / moderate / dangerous 三档结构保持不变。
  - 新增「工具降级链（v2.2.0 · 单点故障规避）」节：① 首选源不可用 → ② 同类换源（biomed / ai / general 三领域「首选 / 次选 / 兜底」表）→ ③ 三源全败降置信输出（confidence 上限、`source_unavailable` 标注、禁止编造数据、6 必填字段齐全、status 取 `partial` 或 `blocked`）；明确不得因单源失败静默跳过检索。
  - 更新「注入式负例」节：`harness_eval_selftest.py` 已存在并纳入 CI，13 条注入式负例（当时口径；v2.2.0 新增 N13 后为 14 条）与 H1-H12 正向校验同步运行，移除「selftest 待补」过期表述。
  - 同步 3 个 domain-expert MD 的 frontmatter 工具名与「回传信封」节（信封单源化，SSOT 指向 `references/agent-protocol.md` §2）。