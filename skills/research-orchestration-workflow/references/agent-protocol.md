# 多代理通信协议 v2.0（Agent Protocol）

> 科研价值驱动研究编排团的代理间通信规范。覆盖消息格式、状态同步、上下文传递、结果回传、
> 角色矩阵、任务分配策略与冲突仲裁。所有成员通信必须遵守本协议。

---

## 1. 角色矩阵（Role Matrix）

抽象为四类通用角色，现有 5 名成员归位如下。**能力边界是硬约束，越界即违规。**

| 抽象角色 | 成员 | 核心能力 | 能力边界（禁止） | 接口契约 |
|---------|------|---------|----------------|---------|
| **整合者** Integrator | 沈知枢（主理人） | 任务解析、状态机驱动、调度编排、最终汇编 | ❌ 代写任何成员的专业产出<br>❌ 替用户做价值选择<br>❌ 成员间直连 | 入：`TASK`（来自用户）<br>出：`RESULT`/`HANDOFF`（至用户） |
| **分析者** Analyzer | 问清源（追问）<br>梁构局（架构） | 信息完整度评估、假设识别、MECE 结构分解、骨架设计 | ❌ 输出研究结论<br>❌ 替用户作答<br>❌ 做可行性判断（属执行者） | 入：`TASK`<br>出：`CLARIFY`/`RESULT` |
| **执行者** Executor | 博域闻（领域） | 多源检索、证据评级、可行性核查、前沿扫描 | ❌ 做价值判断（值不值得做）<br>❌ 替用户下结论<br>❌ 隐藏负面证据 | 入：`TASK`<br>出：`RESULT`（必带 `evidence[]`） |
| **审查者** Reviewer | 严复回（复评） | 证据等级审查、方法学合规、复评闭环决策 | ❌ 判断研究方向价值<br>❌ 输出「待定/观察」<br>❌ 因证据不足跳过评级 | 入：`RESULT`<br>出：`REVIEW`（必带 `decision`） |

**角色-阶段绑定**：FREEZE/IDENTIFY/COLLAPSE→整合者；CLARIFY→分析者（问清源）；
骨架设计→分析者（梁构局）；领域核查→执行者；REVIEW→审查者。

---

## 2. 消息信封（Message Envelope）

所有跨代理通信使用统一结构化信封。**禁止纯自然语言传参**——自然语言只放在 `payload.body`。

```yaml
envelope:
  v: "2.0"                      # 协议版本
  msg_id: "msg-{seq}-{from}"    # 消息唯一 ID
  ts: "2026-08-29T06:30:00+08:00"
  from: "socratic-questioner"   # 发送方 Agent ID
  to: "research-orchestration-team-team-lead"   # 接收方，"user" 表示用户
  type: TASK | RESULT | CLARIFY | REVIEW | ERROR | STATUS | HANDOFF
  trace_id: "trace-{task}-{seq}"    # 贯穿整个任务的追踪链
  parent_msg_id: "msg-003-lead"     # 形成调用树，便于回放
  status: PENDING | RUNNING | SUCCESS | FAILED | BLOCKED
  confidence: 0-100                 # 发送方自评置信度
  context_ref:                      # 上下文引用（非拷贝，见 §4）
    mode: full | summary | ref
    pointer: "state://phase2/structure-d"
  evidence:                         # 每条结论必带（执行者/审查者强制）
    - claim: "HA 糖基化改变受体结合偏好"
      grade: "2b"                   # GRADE: 1a/1b/2a/2b/3a/3b/4/5
      source: "PMID 39884273"
      consistent: true | false | partial
  payload:
    task: {...}      # type=TASK 时
    result: {...}    # type=RESULT 时
    error: {...}     # type=ERROR 时，见 §6
  token_budget: 2000               # 本次产出 token 上限（Context 治理）
```

**字段强制规则**：
- `evidence[]`：执行者、审查者**必填**；分析者可为空（不产出事实性结论）
- `confidence`：**必填**，用于冲突仲裁（§7）
- `context_ref`：**必填**，禁止在消息内全量拷贝上游产出

---

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
  "budget": {"turns_used": 3, "turns_max": 180, "tokens_used": 12400}
}
```

**同步规则**：
1. 每个阶段结束时，主理人写一次检查点（可恢复、可回放）
2. 成员状态由主理人统一维护，成员不得自行改写全局状态
3. 状态变更必须通过 `STATUS` 消息广播给主理人

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
| **串行** serial | 存在硬依赖（后者需要前者输出） | 前序 `SUCCESS` 才触发后续 | 骨架 → 领域核查 → 复评 |
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

---

## 7. 冲突检测与仲裁（Conflict Resolution）

### 检测点（主理人在汇聚阶段执行）
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
    - {agent: "domain-expert",           verdict: "充足", grade: "5", confidence: 40}
    - {agent: "methodological-reviewer", verdict: "不足", grade: "5", confidence: 85}
  rule_applied: "置信度优先"
  resolution: "采纳严复回判断：样本量不足以支撑"
  escalated_to_user: false
```

**禁止**：主理人不得用「投票折中」或「综合两者」掩盖冲突——必须明确选定一方并说明理由。

---

## 8. 结果回传（Result Return）

成员完成产出后，通过 `RESULT`/`REVIEW` 消息回传主理人：

1. **必带结构化字段**：`status`、`confidence`、`evidence[]`、`context_ref`
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
| 达到最大轮次 | `maxTurns = 180` |
| Token/轮次预算耗尽 | `budget.turns_used ≥ turns_max` |
| 护栏触发 | 违反硬底线（伪造事实/跳过澄清） |
| 用户中断 | 用户显式要求停止 |
| 复评判定止损 | 严复回给出 `decision = 止损` 且用户 ACK |

---

*协议版本 v2.0 · 随 harness 架构同步演进 · 违反协议的产出视为无效，须重新生成*
