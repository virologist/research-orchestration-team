# Changelog

所有重要变更按版本倒序记录。格式基于 [Keep a Changelog](https://keepachangelog.com/)。

## [2.0.0] - 2026-09-10

### Added（新增）

- **整合者顾合璧**（synthesis-integrator）：多源融合、冲突五级仲裁、共识矩阵生成。触发词：整合、融合、汇总、冲突、仲裁、共识、综合报告、多源合并。
- **八阶段状态机**：FREEZE → IDENTIFY → COLLAPSE → CLARIFY → ALIGN → EXECUTE_ONE_STEP → REVIEW → NEXT。
- **ACP 通信协议 v2.0**（`skills/research-orchestration-workflow/references/agent-protocol.md`，9 节）：
  - §1 角色矩阵（编排者/分析者/执行者/审查者/整合者 + 能力边界 + 接口契约）
  - §2 消息信封（v2.0 / msg_id / type / trace_id / evidence / context_ref）
  - §3 状态同步（SSOT + 检查点）
  - §4 上下文传递（full / summary / ref）
  - §5 任务分配（并行 / 串行 / 条件 / 扇出汇聚 / 单步）
  - §6 错误四分类（瞬时 / 模型可恢复 / 需人工 / 系统缺陷）
  - §7 冲突检测与仲裁（证据等级 → 置信度 → 角色权威 → 主理人判断 → 用户裁决）
  - §8 结果回传（status / confidence / evidence / context_ref / token_budget）
  - §9 生命周期终止条件
- **Harness 12 组件运行时**：Loop / Tools / Memory / Context / Prompt / Output / State / Error / Guardrails / Verify / Subagent / Lifecycle 全部落地。
- **评分脚本**（`scripts/topic_scoring.py`）：8 维选题评分 + S/A/B/C 分档 + 3 条止损线 + 复评决策（维持/升档/降档/止损）。
- **协议校验脚本**（`scripts/protocol_check.py`）：12 信封 + 5 冲突仲裁 + 集成仿真单元测试。
- **Memory 持久层脚本**（`scripts/memory_log.py`）：4 类（decision/preference/convention/lesson）+ daily/longterm 双目标 + 去重。
- **红队全面审查报告**（`docs/REDTEAM-REPORT.md`）：15 项 bug 分类诊断、修复方案、回归证据。
- **GitHub Actions CI**（`.github/workflows/validate.yml`）：push 自动跑 validate_expert.py + protocol_check.py。
- **双 manifest**（`.claude-plugin/` + `.codebuddy-plugin/`）：同时被 Claude Code / WorkBuddy 原生识别。

### Fixed（修复）

**红队五维诊断发现的 15 项 bug：**

- **P0（逻辑矛盾/死循环）**：
  - 代产出 fallback 与「严禁代写」铁律直接矛盾 → 对齐 §6 错误分类（重试 → 需人工）
  - FREEZE「任意一维 <90%」对 0-10 风险维失效 → 明确量纲（完整度 0-100% + 风险维 0-10）
- **P1（跨文件不一致）**：
  - plugin.json「Six-role」/「L1-L3」vs 协议「五角色矩阵」/「L1-L5」→ 全文同步
  - 整合者接口契约 schema 错位（msg_type / quality.confidence / 中文角色名）→ 对齐 §2 信封
  - README 5 人 → 6 人 / 六阶段 → 八阶段 / 补顾合璧 / 更新目录
  - 问清源 STATUS 信封缺 §2 必填字段 → 补全
  - memory_log 默认写入 `~/.workbuddy/memory` → 三层回退（env > 工作区 > 用户级）+ 告警
  - SKILL.md 复评闭环规则与代码阈值不一致 → 严格对齐
  - `arbitrate()` 平局按到达顺序静默选边 → 升级主理人（不再静默）
- **P2（细节）**：
  - 测试负向用例 expected 从不断言（假绿）→ 真断言
  - `or True` 死代码 → 删除
  - 去重 key 前 15 字误判 → 完整归一化内容
  - `REQUIRED_FIELDS` 缺 `ts` → 补全（回放审计）

### Changed（变更）

- 主理人 prompt 升级为 harness 运行时（TAO 循环 / 三级记忆 / 上下文治理 / 提示装配 / 三处护栏 / 双层验证 / HANDOFF 回引硬约束）。
- 4 团员 prompt 同步注入「v2.0 协议合规契约」5-7 条。
- 描述补触发词：协议检查 / envelope / 信封校验。

### Verified（回归证据）

- T1 脚本延迟与稳定性：4 路径 × 10 次 = **40/40** 通过，avg 41-46ms，sd ≤3.2ms
- T2 真实 spawn 协议合规：**通过**（111s 跑完 FREEZE → HANDOFF 8 阶段）
- T3 协议单元测试：**12/12 信封 + 5/5 冲突仲裁**
- T4 跨成员上下文回引：**10/10**（full/summary/ref 三级全覆盖）
- T5 Memory 持久层：dry-run / 写入 / 去重 / 路径全部通过
- `validate_expert.py`：✅ 通过
- §7 层级 4/5 仲裁实测（详见 `docs/arbitration-L4L5-live-test.md`）

## [1.0.0] - 2026-08-28

### Added

- 5 人初始团队（沈知枢/问清源/梁构局/博域闻/严复回）
- 六阶段状态机（v1）
- 选题评分卡（8 维评分 + S/A/B/C 分档）
- 项目级 README + CONTRIBUTING + 红队报告框架