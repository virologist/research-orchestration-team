# 多代理通信协议 v2.0（Agent Protocol）

> 科研价值驱动研究编排团的代理间通信规范。覆盖消息格式、状态同步、上下文传递、结果回传、
> 角色矩阵、任务分配策略与冲突仲裁。所有成员通信必须遵守本协议。

---

## 1. 角色矩阵（Role Matrix）

抽象为五类通用角色，现有 8 名成员归位如下（v2.1.0 起 domain-expert 拆为 biomed/ai/general 三个 atomic）。**能力边界是硬约束，越界即违规。**

| 抽象角色 | 成员 ID | 成员 | 核心能力 | 能力边界（禁止） | 接口契约 |
|---------|--------|------|---------|----------------|---------|
| **编排者** Orchestrator | `research-orchestration-team-team-lead` | 沈知枢（主理人） | 任务解析、状态机驱动、调度编排、仲裁升级 | ❌ 代写任何成员的专业产出<br>❌ 替用户做价值选择<br>❌ 成员间直连 | 入：`TASK`（来自用户）<br>出：`TASK`/`HANDOFF`（至成员/用户） |
| **分析者** Analyzer | `socratic-questioner`<br>`meta-architect` | 问清源（追问）<br>梁构局（架构） | 信息完整度评估、假设识别、MECE 结构分解、骨架设计 | ❌ 输出研究结论<br>❌ 替用户作答<br>❌ 做可行性判断（属执行者） | 入：`TASK`<br>出：`CLARIFY`/`RESULT` |
| **执行者** Executor | `domain-expert-biomed`<br>`domain-expert-ai`<br>`domain-expert-general` | 博域闻·生医<br>博域闻·AI<br>博域闻·通识 | 多源检索、证据评级、可行性核查、前沿扫描 | ❌ 做价值判断（值不值得做）<br>❌ 替用户下结论<br>❌ 隐藏负面证据 | 入：`TASK`<br>出：`RESULT`（必带 `evidence[]`） |
| **审查者** Reviewer | `methodological-reviewer` | 严复回（复评） | 证据等级审查、方法学合规、复评闭环决策 | ❌ 判断研究方向价值<br>❌ 输出「待定/观察」<br>❌ 因证据不足跳过评级 | 入：`RESULT`<br>出：`REVIEW`（必带 `decision`） |
| **整合者** Integrator | `synthesis-integrator` | 顾合璧（融合） | 多源 RESULT 聚合、冲突检测、五级仲裁执行、共识矩阵、综合汇编 | ❌ 产生新知识<br>❌ 裁决价值问题（L5 直接升级）<br>❌ 隐藏分歧 | 入：`inputs_ref[]`（多方 msg_id）<br>出：`RESULT`（synthesis + 共识矩阵 + 仲裁记录） |

**成员 ID 取值规则**：成员 ID = 对应 `../../../agents/<成员ID>.md` 的**文件名（去 `.md`）**，与该文件 frontmatter 的 `name` 字段一致——派单与回传一律用成员 ID，禁止用中文名或自创名称。

**三个 atomic 执行者的归属说明**：执行者是**一个抽象角色、三个 atomic 成员**（biomed / ai / general 按领域分工，v2.1.0 起由原 `domain-expert` 拆分为三个 atomic）。三者共享同一套能力边界与接口契约，但在证据链里是**三个独立 `agent_id`**，各自单独出具 `evidence[]` 与 `confidence`，不合并、不互相代签。跨领域任务命中两个及以上领域标签时并行 fan-out（模板见同目录 `agent-registry.md`「交叉领域组合路由模板（v2.2.0 · 补 F9）」）。

**角色-阶段绑定**：FREEZE/IDENTIFY/COLLAPSE→编排者；CLARIFY→分析者（问清源）；
骨架设计→分析者（梁构局）；领域核查→执行者；REVIEW→审查者；**多方产出汇聚→整合者（顾合璧）**。

> **本表是「抽象角色 ↔ 成员 ID」归属的单一事实源（SSOT）**。成员增删或改名必须同步四处：本表、同目录 `agent-registry.md`「团队成员一览」、仓库根 `../../../.claude-plugin/plugin.json` 与 `../../../.codebuddy-plugin/plugin.json` 的 `agents` 列表（及其 `members[]` / `teamInfo`）、以及 `../../../scripts/routing_eval.py` 的成员集合校验基数。任一处漏改都会被 R1「成员集合一致」门禁判红。
>
> **「成员集合」维度的机器真值源**是 `../../../agents/*.md` 的**文件名集合**（最底层事实：文件在，成员就在）。上述五处均以它为准，由 `../../../scripts/manifest_check.py` 的 **C13「成员 ID 集合一致性」**逐处比对——任一处漏改即 rc=1 并逐处列出「多出 / 缺少」差异。本表负责的是「抽象角色 ↔ 成员 ID 的**归属**」（哪个 ID 属于哪个角色、承担什么职责），这一层不由 C13 覆盖。

---

## 2. 消息信封（Message Envelope · 统一协议 result_envelope v2.4）

所有跨代理通信使用统一结构化信封。**禁止纯自然语言传参**——自然语言只放在 `payload` 内。

> **跨团队统一（2026-09-30）**：6必填字段对齐 triz-invention-team / viral-evo-lab / vet-med-ppt-team。
> 原 ACP v2.0 的 `envelope:` YAML 格式**已废弃**；其高级能力（evidence GRADE分级 / trace_id 追踪链 / payload 角色定制）保留为扩展字段，能力不降级。

```json
{
  "agent_id": "<成员ID>",
  "task_id": "<任务ID·与trace_id对应>",
  "phase": "<阶段·如 CLARIFY/ALIGN/EXECUTE 或阶段号>",
  "status": "success|partial|failed|blocked",
  "confidence": 0-100,
  "deliverable_summary": "<一句话摘要>",
  "evidence": [
    {"type": "source|skill_ref|prior_artifact", "ref": "<PMID|DOI|URL|路径>",
     "used_for": "<该证据支撑的结论>", "grade": "<GRADE 1a-1b-2a-2b-3a-3b-4-5>", "recency": "<近6月|近12月|>12月>"}
  ],
  "issues": ["<自评发现的问题>"],
  "next_agent_hint": "<建议下游成员>",
  "metrics": {"duration_ms": 0, "retry_count": 0},
  "trace_id": "trace-<task>-<seq>",
  "msg_id": "msg-<seq>-<from>",
  "parent_msg_id": "msg-<seq>-<parent>",
  "type": "TASK|RESULT|CLARIFY|REVIEW|ERROR|STATUS|HANDOFF",
  "context_ref": {"mode": "full|summary|ref", "pointer": "state://phase2/..."},
  "payload": { "<按角色定制·见各成员MD>" }
}
```

**字段强制规则**：
- **6必填**（agent_id / task_id / phase / status / confidence / deliverable_summary）：跨团队统一强制，缺一即判 `partial`
- `evidence[]`：执行者、审查者**必填**；分析者、整合者可为空（分析者不产出事实性结论；整合者不产生新知识）。执行者指 §1 三个 atomic 执行者（`domain-expert-biomed` / `domain-expert-ai` / `domain-expert-general`），审查者指 `methodological-reviewer`
- `confidence`：**必填**，取值 0-100 的数值（非数值或越界即判非法），用于冲突仲裁（§7）
- `context_ref`：**一般情形为「推荐」**（禁止在消息内全量拷贝上游产出，对抗 context rot）；**但 `HANDOFF` 类型信封为必填**——HANDOFF 的 `context_ref.pointer` 必须覆盖**全部** `state://cp-*` 检查点，缺任一即违规重生成。校验分两层，各层职责与失败语义不同，**分开走不合流**：
  - **信封层**（`../scripts/protocol_check.py` 的 `check_envelope_full` → `check_envelope`）：判 `context_ref` 存在且非空（dict 须非空；list 须非空且每项是 dict），缺失或为空时失败文案为 `context_ref 必填`；同时校验 `mode` 取值与 `pointer` 形态——`pointer` 允许 4 种形态（`state://cp-NNN` / `state://<路径段>` / `http(s)://...` / `<路径>:<行号>`），按 `mode` 定是否必填（`full`/`summary` 的 pointer **可空**，`ref` 的 pointer **必填**，缺失报 `<label>.pointer 缺失`，非空但形态非法报 `<label>.pointer 格式非法`）；`HANDOFF` 的 pointer **必须**是 `state://cp-NNN` 检查点指针
  - **覆盖层**（`../scripts/protocol_check.py` 的 `check_handoff_coverage`）：判是否覆盖全部 `state://cp-*`，返回缺失清单；同时校验 pointer 形态（覆盖层的 pointer 必须是 cp-*，非 cp-* 指针是死引用——既不计入覆盖也不报错）
  - **不合流的理由**：覆盖层需要「本次任务实际产生了哪些 cp-*」这份运行时清单，信封层拿不到也不该猜；若合流会让信封层硬编码 cp 清单。且两层失败语义不同（漏字段 vs 漏回引）
  - 口径见 `../../../agents/research-orchestration-team-team-lead.md`「HANDOFF 回引硬约束」
- `status` 取值：`success` / `partial` / `failed` / `blocked`（**原 ACP `SUCCESS`/`FAILED`/`BLOCKED` UPPERCASE 已弃用**）
- `trace_id` / `msg_id` / `parent_msg_id` / `type` / `context_ref`：**扩展字段**（保留 ACP 追踪与审计能力）

### 文档-实现一致性说明（§2 字段规则 vs `protocol_check.py`）

本节只**登记差异与各自口径**，不改写上述强制规则。校验器实现见 `../scripts/protocol_check.py`；当前协议合规判定的**唯一入口**是 `check_envelope_full`（信封层 + 证据链层 + HANDOFF 回引层三层一次跑完），底层 `check_envelope` / `check_evidence_chain` / `check_handoff_coverage` 为其组成部分。

| 字段 | 本协议口径 | 校验器实际实现 | 差异说明 |
|------|-----------|---------------|---------|
| 6 必填 | 缺一即判 `partial` | 缺任一必填字段即列入失败原因 | 一致（校验器更严：直接报错而非降级判 `partial`，由调用方决定重生成） |
| `status` | 小写四值 | `VALID_STATUS_V24 = {success, partial, failed, blocked}` | 一致；大写 `SUCCESS` 等命中失败 |
| `confidence` | 必填，0-100 | 非数值或不在 0-100 区间即失败 | 一致 |
| `type` | 枚举 7 值 | 存在时须在枚举内；**缺省不报错**（视为可选扩展字段） | 一致（`type` 属扩展字段，允许省略） |
| `evidence[]` | 须为数组；执行者/审查者必带 | 须为数组；按 `agent_id` 判定执行者/审查者（`EVIDENCE_PRODUCERS_V24`），空数组即失败 | 一致；判定依据是 `agent_id` 而非角色名 |
| `evidence[].ref` | PMID/DOI/URL/路径 四类形态 | 证据链校验（`REF_PATTERNS`）：URL / `PMID:`+数字 / 裸数字 / `PMC`+数字 / `DOI:`+裸 DOI / `arXiv:` / `path:/` / `state://` / 绝对路径 / `<文件名>:<行号>`；缺失即「ref 缺失」 | 一致（允许形态比 §2 四类更细，属**超集细化**，不放宽） |
| `evidence[].grade` | GRADE 1a-1b-2a-2b-3a-3b-4-5 | 复用 `check_evidence_grade` 校验 grade 枚举；结论字段以 `claim`（历史）或 `used_for`（v2.4）任一非空即算已写明 | 一致（v2.4 用 `used_for` 承载结论，校验时与 `claim` 归一） |
| `evidence[].type` / `recency` | `source`/`skill_ref`/`prior_artifact`；`近6月`/`近12月`/`>12月` | **无机器校验** | **差异**：目前属约定性约束，不构成门禁 |
| 降级标注 | 工具降级链要求降级场景逐条标 `source_unavailable`，且**非降级场景不得出现**该标记 | 证据链第三分支双向校验：降级场景缺标记即失败；非降级场景出现标记即失败 | 一致（`used_for`/`grade`/`note`/`status`/`source` 任一字段承载标记即算已标注） |
| `context_ref.mode` | `full` / `summary` / `ref` | 三个值；**支持 dict 与 list 两种形态** | 一致（list 形态供多检查点回引使用） |
| `context_ref` 必填性 | 一般推荐；**HANDOFF 必填且须覆盖全部 cp-*** | **信封层**：`check_envelope_full` 对 `type == "HANDOFF"` 自动开启 `require_context_ref`，缺失或为空即失败（文案 `context_ref 必填`）。**覆盖层**：`check_handoff_coverage` 独立校验是否覆盖全部 `state://cp-*`，返回缺失清单；两者**不合并** | 一致（覆盖层需「本次任务实际产生了哪些 cp-*」运行时清单，合流会让信封层硬编码 cp 清单；且两层失败语义不同：漏字段 vs 漏回引） |
| `context_ref.pointer` 形态 | 指针指向 `state://cp-*` | **信封层与覆盖层双重校验形态**。信封层：允许 4 种形态（`state://cp-NNN` / `state://<路径段>` / `http(s)://...` / `<路径>:<行号>`），并按 `mode` 定是否必填（`full`/`summary` 的 pointer **可空**；`ref` 的 pointer **必填**，缺失报 `<label>.pointer 缺失`，非空但形态非法报 `<label>.pointer 格式非法`）；HANDOFF 的 pointer **必须**是 `state://cp-NNN` 检查点指针。覆盖层（`check_handoff_coverage`）同样校验形态 | 一致（形态门禁已落地：非 cp-* 指针在 HANDOFF 上既不计入覆盖也不报错 → 死引用，故显式拦截） |
| `metrics` | `{duration_ms, retry_count}` | **无机器校验** | 约定性约束，由主理人在 §8 收尾时人工清点 |
| `../templates/result-envelope-v2.4.json` | result_envelope v2.4 的**空白信封模板**；新建信封时以此为骨架，避免漏必填字段 | **模板，非门禁**——校验器不读取该文件 | 一致（模板 6 必填字段名与 `REQUIRED_FIELDS_V24` 逐字对齐） |
| `../templates/cross-domain-combo.md` | 跨域组合（biomed×ai / biomed×general / ai×general）的**编排模板**，承接 registry 的三组合与三条硬规则 | **模板，非门禁**——校验器不读取该文件 | 一致（模板为 registry 组合路由的可填执行单；与 registry 冲突时以 registry 为准） |

**两个模板的引用关系与用途**（**模板 ≠ 门禁**：校验器不读取这两个文件，故不写进上文「唯一入口是 `check_envelope_full`」的导语）：

| 模板文件 | 用途 | 与谁对齐 |
|----------|------|----------|
| `../templates/result-envelope-v2.4.json` | **result_envelope v2.4 的空白信封模板**。新建信封时直接以此为骨架填空，避免漏必填字段或写错 `status` / `mode` 取值 | 6 必填字段名与 `../scripts/protocol_check.py` 的 `REQUIRED_FIELDS_V24` **逐字一致**；`status` 四值、`context_ref.mode` 三值与校验器枚举一致 |
| `../templates/cross-domain-combo.md` | **跨域组合的编排模板**。任务命中两个及以上领域标签（biomed / ai / general）时，主理人在 Route 步骤套用它填空，产出并行 fan-out + 串行依赖链 + 仲裁方案 | 承接 `agent-registry.md`「交叉领域组合路由模板（v2.2.0 · 补 F9）」的三组合与三条硬规则；**与 registry 冲突时以 registry 为准** |

## 3. 状态同步（State Sync）

采用**单一事实源（SSOT）+ 检查点**模式，对应 harness 的 State + Checkpoints 组件。

```json
{
  "trace_id": "trace-xxx-001",
  "phase": "CLARIFY",
  "turn": 3,
  "checkpoints": [
    {"turn": 1, "phase": "FREEZE",  "ts": "...", "snapshot_ref": "state://cp-001"},
    {"turn": 2, "phase": "IDENTIFY","ts": "...", "snapshot_ref": "state://cp-002"}
  ],
  "perception": {"completeness": 35, "assumption_density": 8,
                 "emotion_risk": 4, "execution_risk": 9},
  "members": {
    "socratic-questioner":    {"status": "SUCCESS", "msg_id": "msg-004", "confidence": 80},
    "methodological-reviewer":{"status": "PENDING", "msg_id": null,  "confidence": null}
  },
  "conflicts": [],
  "budget": {"turns_used": 3, "turns_max": 30, "tokens_used": 12400, "tokens_max": 200000}
}
```

> `members[].status`（任务生命周期状态，非 §2 信封 status 字段；两者不同，勿混用）

> **两套上限的分工（v2.1.2 消歧义）**：本块 `budget.turns_max` 是**编排层**单任务自控预算（默认 30，落盘默认值见 `../scripts/state_io.py` 的 `DEFAULT_MAX_TURNS`）；主理人 frontmatter 的 `maxTurns: 180` 是**平台层**会话兜底天花板（防止会话失控的最终熔断，正常任务不应触达）。两者不冲突：编排 30 是主理人主动自控的目标线，触达即按熔断流程升级用户；平台 180 是会话级兜底。完整口径见 `../../../agents/research-orchestration-team-team-lead.md`「### Loop 硬停止（三层上限 · circuit breaker）」节内的「两套上限的分工（v2.1.2 消歧义）」说明块。

**同步规则**：
1. 每个阶段结束时，主理人写一次检查点（可恢复、可回放）
2. 成员状态由主理人统一维护，成员不得自行改写全局状态
3. 状态变更必须通过 `STATUS` 消息广播给主理人

### v2.2.0 增补 · 状态落盘（确定性工程层）

§3 的 SSOT 状态 JSON **不是纸面 schema**——由 `../scripts/state_io.py` 负责确定性落盘：

- **状态文件**：`<workspace>/.harness-runs/<task_id>/_state.json`（原子写：.tmp + os.replace）
- **检查点指针**：`state://cp-NNN` ≡ `.harness-runs/<task_id>/checkpoints/cp-NNN.md`
- **六命令**：`init`（开工，幂等）/ `advance`（阶段收尾）/ `resume`（中断恢复，打印续跑点）/ `finish`（收尾）/ `budget`（轮次与 token 计数）/ `fail`（登记一次失败，累计达 `budget.max_failures` 即熔断置 `status = aborted`）
- **写入者**：仅主理人（与同步规则 2 一致）；成员只读
- **退出码**：0 成功 / 1 参数错（**含跳级未 force**、熔断后拒绝推进）/ 2 无状态文件 / 3 JSON 损坏（fail fast，禁静默重建）
- **按序推进门禁（sequential advance gate）**：`advance` 只允许推进到**期望的下一个阶段**；越级即拒绝并返回退出码 1。边界约定：`init` 之后第一次推进的目标就是 `FREEZE` 本身（记为第 1 个检查点），此后严格取当前阶段的后继阶段。逃生阀：给非空 `--force-reason` 即生效（`--force` 与 `--force-reason` 同时给亦可；**只给 `--force` 而不给理由会被拒**，返回退出码 1）。越级放行时会打印 ⚠️ 提示实际跳过的阶段与理由。越级属**例外路径**，须在交付报告中标明，不得作为常规推进方式

主理人断点续跑流程与命令示例见 `../../../agents/research-orchestration-team-team-lead.md`「标准工作流程（SOP）前的强制动作：状态初始化与断点续跑」节（本节与该处互为引用，行为以 `../scripts/state_io.py` 实现为准）。

**§3 纸面 schema vs 落盘 schema 的差异登记**（本段只登记差异，不改写上方示例；落盘实现以 `../scripts/state_io.py` 为准）：

| 项 | §3 纸面示例 | `state_io.py` 落盘 `_state.json` | 说明 |
|----|------------|------------------------------|------|
| 顶层键 | `trace_id` / `phase` / `turn` / `checkpoints` / `perception` / `members` / `conflicts` / `budget` | `version` / `task_id` / `created_at` / `updated_at` / `status` / `abort_reason` / `phase` / `turn` / `checkpoints` / `perception` / `budget` / `notes` / `metrics` | **差异**：落盘用 `task_id` 承载 trace 标识（`task_id` 即 trace_id），并额外落盘 `version` / 时间戳 / `status` / `abort_reason` / `notes` / `metrics`；纸面示例的 `trace_id` 不单独落盘 |
| `members` / `conflicts` | 有（成员状态与冲突清单） | **不落盘** | **差异**：两者是**编排期视图**，由主理人在 §2 信封与 `STATUS` 消息流中维护，不进 `_state.json`；`state_io.py` 的 `fail` 子命令另以 `budget.failures` / `budget.max_failures` 承载熔断计数 |
| `budget` 子键 | `turns_used` / `turns_max` / `tokens_used` / `tokens_max` | 上述四项 + `max_time_sec` / `started_at` / `failures` / `max_failures` | 落盘多出 max_time 与熔断计数四键；**`turns_max` 默认 30 与 `tokens_max` 默认 200,000 同为编排层口径**（`DEFAULT_MAX_TURNS` / `DEFAULT_MAX_TOKENS`） |
| `status` 语义 | 无顶层 `status` | `running` / `done` / `aborted`（+ `abort_reason`：`max_time` / `circuit_breaker`） | 落盘的 `status` 是**任务生命周期状态**，与 §2 信封的 `status`（`success`/`partial`/`failed`/`blocked`）和 §3 `members[].status`（`SUCCESS`/`PENDING`）三者互不相同，勿混用 |

---

## 4. 上下文传递（Context Passing）

**核心原则：引用优于拷贝**（对抗 context rot——关键内容落在窗口中段时模型性能下降 30%+）。

| 模式 | 适用场景 | 传递内容 |
|------|---------|---------|
| `full` | 当前阶段直接依赖的上游产出（≤2 项） | 完整原文 |
| `summary` | 间接依赖、历史阶段产出（默认） | 结构化摘要（≤300 字 + 关键表格） |
| `ref` | 大对象（长文献清单、完整骨架） | 指针，按需加载（JIT retrieval） |

**压缩触发**：累计上下文 > 60% 窗口 或 阶段数 > 5 → 主理人执行 compaction
（历史阶段降为 `summary`，保留决策点与证据等级，丢弃过程性推理）。

---

## 5. 任务分配策略（Task Dispatch）

| 模式 | 触发条件 | 调度规则 | 示例 |
|------|---------|---------|------|
| **并行** parallel | 多个任务无数据依赖 | 同时下发，等待全部完成（fan-out/fan-in） | Workflow A Phase 1：追问 + 结构分解并行 |
| **串行** serial | 存在硬依赖（后者需要前者输出） | 前序 `success` 才触发后续 | 骨架 → 领域核查 → 复评 |
| **条件** conditional | 依赖前序结果满足某条件 | 前置结果满足条件才调度 | 仅当 `completeness ≥ 90` 才进 EXECUTE |
| **扇出汇聚** fan-out/fan-in | 多成员独立产出后需整合 | 并行下发 → 主理人汇聚 → 冲突检测 | Workflow C Phase 2：领域 + 复评并行 |
| **单步** single | 单一原子动作 | 直接路由（见主理人路由表） | 用户只需澄清 → 直调问清源 |

**调度硬规则**：只读任务可并行；写状态/改决策的任务必须串行。

---

## 6. 错误分类与恢复（Error Taxonomy）

对应 harness 的 Error Recovery 组件。四类错误，恢复策略不同。

| 类别 | 判定 | 恢复策略 | 重试上限 |
|------|------|---------|---------|
| **瞬时** transient | 超时、限流、网络抖动 | 指数退避重试 | 3 次 |
| **模型可恢复** model-recoverable | 参数错误、格式错误、工具误用 | 结构化错误回传模型自纠 | 2 次 |
| **需人工** human-required | 需用户裁决、需外部信息、触及价值选择 | 中断并请求用户输入 | 不限（等待） |
| **系统缺陷** system-defect | 脚本异常、契约违反、逻辑死锁 | fail fast + 留痕 + 上报用户 | 0（不重试） |

`ERROR` 消息 payload 必含：`category`（四选一）、`detail`、`recovery_action`、`retry_count`。

### v2.1.0 增补 · Per-step Verification（每个步骤都校验）

> v2.0 仅 final-output 校验（整合者顾合璧统一 verify）；v2.1.0 改为 **per-step verification**（每个 step 输出都过 verification gate，避免单点失败累积）。

- **每个 step 输出**：必过 verification gate（不是只 verify final-output）
- **错误路径三件套**：
  - `root_cause_hint`：人话版"为什么错"（非 stack trace）
  - `safe_retry_instruction`：什么前提下可重试、不要改什么
  - `explicit_stop_condition`：什么情况下必须停，不自己硬撞
- **失败回流为 harness 新规则**：每次失败回流都写成 registry / protocol 的新增规则（Hashimoto 模式）
- **circuit_breaker**：同一 task 失败 5 次 → 自动熔断 + 升级用户（详见同目录 `agent-registry.md` §Loop 终止硬上限（circuit breaker））

---

## 7. 冲突检测与仲裁（Conflict Resolution）

### 检测点（整合者顾合璧在融合阶段执行，主理人监督）
1. **证据冲突**：同一 claim 不同成员给出不同 `grade`
2. **结论冲突**：成员结论方向相反（如「可行」vs「止损」）
3. **置信度冲突**：成员 `confidence` 差异 > 30 且结论不一致

### 仲裁优先级（自上而下，命中即止）
1. **证据等级优先**：GRADE 高者胜（1a > 1b > 2a > 2b > 3a > 3b > 4 > 5）
2. **置信度优先**：证据等级相同时，`confidence` 高者胜
3. **角色权威**：涉及方法学 → 审查者；涉及领域事实 → 执行者；涉及结构 → 分析者
4. **主理人判断**：仍无法裁决，主理人给出编排判断并标注「⚠️ 主理人裁决」
5. **用户裁决**：涉及价值选择时，**必须**上呈用户

### 仲裁输出格式
```yaml
conflict:
  id: "cf-001"
  claim: "2543 条序列是否足以支撑深度学习"
  positions:
    - {agent: "domain-expert-biomed",    verdict: "充足", grade: "5", confidence: 40}
    - {agent: "methodological-reviewer", verdict: "不足", grade: "5", confidence: 85}
  rule_applied: "置信度优先"
  resolution: "采纳严复回判断：样本量不足以支撑"
  escalated_to_user: false
```

**禁止**：主理人不得用「投票折中」或「综合两者」掩盖冲突——必须明确选定一方并说明理由。

---

## 8. 结果回传（Result Return）

成员完成产出后，通过 `RESULT`/`REVIEW` 消息回传主理人：

1. **必带结构化字段**：`status`、`confidence`、`context_ref`（`evidence[]` 仅执行者/审查者必带，分析者/整合者可为空，见 §2）
2. **必声明 token 用量**：便于主理人做 budget 控制
3. **必标注不确定性**：单一来源、证据冲突、推断内容均须 ⚠️ 标注
4. **禁止越界**：成员不得直接向用户输出（必须经主理人汇编）

主理人汇聚后，以 `HANDOFF` 消息交付用户，格式见主理人 MD 的「默认输出结构」。

---

## 9. 生命周期终止条件（Lifecycle）

任务在以下任一条件命中时终止（防止无限循环）：

| 条件 | 阈值 |
|------|------|
| 无待办工具/成员调用 | 自然收敛 |
| 编排层轮次预算耗尽 | 编排层 `budget.turns_used ≥ budget.turns_max`（默认 `turns_max = 30`）→ 熔断 + 升级用户 + 输出当前已知最佳 |
| 平台层会话兜底触达 | 平台层 `maxTurns`（主理人 frontmatter，默认 180）→ 平台强制截断会话（兜底天花板，正常任务不应触达） |
| Token 预算耗尽 | 编排层 `budget.tokens_used ≥ budget.tokens_max`（默认 200,000）→ 阶段边界 compact + 升级用户 |
| 护栏触发 | 违反硬底线（伪造事实/跳过澄清） |
| 用户中断 | 用户显式要求停止 |
| 复评判定止损 | 严复回给出 `decision = 止损` 且用户 ACK |

> **两层上限必须都保留、分层表述**：编排层 30 是主理人**主动自控**的目标线，触达即熔断升级用户，绝不空转；平台层 180 是**会话兜底**天花板，由平台强制截断。协议 §3 状态 JSON 的 `budget.turns_max` 属编排层口径，与同目录 `agent-registry.md`「Loop 终止硬上限（circuit breaker）」表的 `max_turns = 30` 一致；`maxTurns: 180` 只出现在主理人 frontmatter 与本表「平台层会话兜底触达」一行。详见 `../../../agents/research-orchestration-team-team-lead.md`「### Loop 硬停止（三层上限 · circuit breaker）」节内的「两套上限的分工（v2.1.2 消歧义）」说明块。

---

*协议版本 v2.0 · 随 harness 架构同步演进 · 违反协议的产出视为无效，须重新生成*
