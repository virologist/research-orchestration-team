# Harness Engineering 评估报告 · v2.0.2（基线）

> 基线快照：v2.0.2 在引入 harness_eval.py 前**完全不具备** Harness Engineering 12 项设计模式。
> 本报告记录 v2.1.0 改造前的真实状态，作为改进下限。

## 评估方法

- **工具**：`scripts/harness_eval.py`（v2.1.0 新增，12 项注入式正向校验）
- **校验对象**：v2.0.2 commit `b3c2e0c`（Latest 之前的稳定版）+ a783f4e docs+tools patch
- **退出码**：1（存在失败项）

## 评估结果

| 项 | 设计模式 | v2.0.2 状态 | 证据 |
|----|---------|------------|------|
| H1  | 路由机制升级（agent-registry.md 单一事实源） | ❌ 文件不存在 |
| H2  | Loop 硬停止（max_turns / max_time / max_token）| ❌ 3 项全缺 |
| H3  | Per-step verification | ❌ protocol 未提及 |
| H4  | 阶段边界 compact | ❌ SKILL.md 未提及 |
| H5  | Atomic subagent 拆分（biomed/ai/general）| ❌ 仅 1 个 domain-expert.md |
| H6  | 权限分层（safe/moderate/dangerous）| ❌ 无 registry |
| H7  | Eval & Observability（metrics）| ❌ team-lead 无 metrics 字段 |
| H8  | Token budget 跟踪 | ❌ team-lead 无 token budget |
| H9  | LEARNING.md 跨会话连续性 | ❌ 文件不存在 |
| H10 | Circuit breaker（失败熔断）| ❌ 无熔断机制 |
| H11 | plan_execution 元工具（Orchestrator Pattern）| ❌ team-lead 无此元工具 |
| H12 | agent-registry.md 单一事实源 | ❌ 文件不存在 |

**总分：0/12**

## 含义

v2.0.2 在 Harness Engineering 维度**0 项符合**——这是一个 harness 健壮性盲区。
即使 manifest_check.py（发行卫生）全绿，harness_eval.py 仍能识别 12 项设计模式缺失。
这印证了 METR 研究的结论：「只测正向无法区分『校验器真的在检查』与『它永远返回 0』」。
v2.0.2 缺一个**客观、可复现的 harness 健康度量**。

## 对照（v2.0.2 vs v2.1.0）

v2.1.0 改造后：**12/12 通过**。
- H5 从 ❌→✅（拆分 atomic subagent）
- H1/H6/H12 从 ❌→✅（agent-registry.md 单一事实源 + safe/moderate/dangerous）
- H2/H7/H8/H10/H11 从 ❌→✅（team-lead prompt 注入 v2.1.0 升级摘要）
- H3 从 ❌→✅（agent-protocol.md §6 增补 per-step verification）
- H4 从 ❌→✅（SKILL.md 模块 1 增补阶段边界 compact 表）
- H9 从 ❌→✅（LEARNING.md + Ralph Loop 跨会话连续性）

详细改造记录见 CHANGELOG.md v2.1.0 条目。