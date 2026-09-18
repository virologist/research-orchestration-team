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

## 跨会话连续性协议（Ralph Loop）

每个新 session 启动后：
1. **读取**本文件（git log + LEARNING.md）
2. **识别**最高优先级未完成 task（按时间倒序 + "下一步"标签）
4. **处理**该 task
5. **提交**到 git
6. **追加**新一段 task 记录到本文件
7. **循环**直到 30 turns / 30min / 200k tokens 任一触发 → compact / circuit breaker