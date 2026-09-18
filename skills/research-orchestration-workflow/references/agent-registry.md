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
- **trigger**: 任意科研规划 / 选题 / 立题 / 投资方向 / 编排 / 仲裁 / 融合 / 复评
- **routing**: 自身路由到合适的 subagent 组合（Orchestrator Pattern）

### socratic-questioner（问清源）
- **trigger**: 任何需要澄清的任务 / 信息完整度 / 假设密度 / 风险评估
- **stage**: FREEZE → CLARIFY（信息完整度 < 90% 时触发）
- **routing**: 与 free-form 任务强相关，几乎 always-on

### meta-architect（梁构局）
- **trigger**: 结构分解 / 跨域节点 / 骨架设计 / 中观跨域研究
- **stage**: IDENTIFY → COLLAPSE（任务复杂时触发）
- **routing**: 复杂任务（多步骤 / 多领域）才调

### domain-expert-biomed（博域闻·生医）
- **trigger**: 生物医药 / PubMed / GISAID / 流感 / 禽流感 / 兽医 / 分子生物学 / 流行病学 / 病原 / 序列 / 基因 / 蛋白 / 疫苗 / 抗原 / 宿主范围 / H5 / H10 / NHRAI / GAR
- **stage**: EXECUTE_ONE_STEP（领域深挖时触发）
- **tools**: `WebFetch` / `WebSearch` / `mcp__biomcp` / `mcp__crossref` / `mcp__biorxiv`
- **routing**: 任务领域标签 = `biomed` 时由 meta-router 调度

### domain-expert-ai（博域闻·AI）
- **trigger**: AI / 大模型 / LLM / GPT / Claude / 深度学习 / 神经网络 / RAG / Agent / 多智能体 / LoRA / QLoRA / 微调 / 推理 / 强化学习 / 蛋白设计 / AlphaFold / ESMFold / 生信管道 / Python / R
- **stage**: EXECUTE_ONE_STEP
- **tools**: `WebFetch` / `WebSearch` / `mcp__paper_search_server` / `mcp__consensus` / `mcp__arxiv-mcp-server`
- **routing**: 任务领域标签 = `ai` 时

### domain-expert-general（博域闻·通识）
- **trigger**: 统计 / 方法学 / 教育 / 教学 / 管理 / 社会科学 / 政策 / 研究设计 / 问卷 / 实验设计 / 样本量 / meta 分析 / 文献综述 / PRISMA / GRADE / CONSORT / STROBE
- **stage**: EXECUTE_ONE_STEP
- **tools**: `WebFetch` / `WebSearch` / `mcp__crossref` / 政策文件库
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

### safe（自动放行 + 审计日志）

| 工具 | 适用 agent |
|------|-----------|
| `WebFetch` / `WebSearch` | 所有执行者 |
| `mcp__biomcp` | domain-expert-biomed |
| `mcp__crossref` | domain-expert-biomed, domain-expert-general |
| `mcp__biorxiv` | domain-expert-biomed |
| `mcp__paper_search_server` / `mcp__consensus` | domain-expert-ai |
| `mcp__arxiv-mcp-server` | domain-expert-ai |
| `Read` / `Grep` / `Glob`（本地文件读取） | 所有分析者 / 整合者 |

### moderate（记录 + 二次确认）

| 工具 | 适用 agent | 二次确认规则 |
|------|-----------|--------------|
| `Write` / `Edit`（本地文件修改） | 所有"调我改 SKILL/registry"的 agent | 改动前说明意图 + 受影响文件列表 |
| `Bash`（git commit / push） | 主理人 | 仅限发布流程的预定义命令 |
| `mcp__biomcp`（高级查询） | domain-expert-biomed | 限定 30 源子集 |

### dangerous（强制人审 + 回滚 + 仅隔离环境）

| 工具 | 适用 agent | 强制人审条件 |
|------|-----------|--------------|
| 发邮件 / 部署 / 删数据 / 改训练数据 | **禁止** | — |
| `gh release create` / `gh repo` | 主理人（仅 B 方案清理） | 必须经用户确认 |
| `git push --force` / `rm -rf` | 主理人 | 必须经用户确认 |
| 模型微调 / 训练启动 | **禁止** | — |

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

## Loop 终止硬上限（circuit breaker）

| 上限 | 数值 | 说明 |
|------|------|------|
| max_turns | 30 | 单任务总轮次 |
| max_time | 1800s (30 分钟) | 单任务总时长 |
| max_token | 200,000 | 单任务总 token 消耗 |
| circuit_breaker | 失败 5 次 | 同一 task 失败 5 次 → 熔断 + 升级用户 |

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

| 指标 | 含义 |
|------|------|
| 成功率 | 每个任务类型的成功数 / 总数 |
| 平均 tool call 次数 / 任务 | 工具调用频次 |
| 重试次数 / 任务 | 错误回流统计 |
| 失败时 next_actions 字段存在率 | 错误路径设计质量 |

### 注入式负例

参考 `scripts/harness_eval.py` 与 `scripts/harness_eval_selftest.py`（待 v2.1.0 改造后新增 selftest）：
- H1-H12 正向校验（当前）
- 注入式负例（selftest 待补）

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