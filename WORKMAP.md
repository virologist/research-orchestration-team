# 工作地图 · 科研价值驱动研究编排团

> 一页看懂「做什么 → 走哪几步 → 依赖什么 → 凭什么算做完」。
> 机器真值源：[`workmap.json`](./workmap.json)；本文档是人读视图，两者由 `scripts/workmap_check.py` 双向校验。
> 版本 `2.5.8` · 2026-11-12。本图只描述**任务如何被完成与验收**，不替代 `agents/` 的角色定义与 `references/agent-protocol.md` 的通信协议。

## 一、四种结果状态（禁止混标）

| 状态 | 含义 | 谁能标 |
|------|------|--------|
| **自动验证通过** | 脚本实跑、rc 可复现、证据已落盘 | 程序 |
| **AI 评估通过** | AI 语义产出，结构化断言命中但未经人判断 | 程序 + 如实标注 |
| **人工确认通过** | 价值取舍、语义质量、审美判断 | **只能由用户标** |
| **尚未验证** | 没有运行证据，或证据不可复跑 | 默认态 |

规则：**没有证据不宣称验证通过**。语义与价值判断不得标成「自动验证通过」。

## 二、任务地图（3 类）

| 任务 | 输入 | 输出 | 走哪些阶段 | 验收条件 | 人工确认点 |
|------|------|------|-----------|----------|-----------|
| **T1 科研选题**（Workflow A） | 方向描述 + 8 维评分（1–10 整数） | 选题评分卡 / S·A·B·C 分档 / 3 条止损线 | P1→P2→P3→P5→P6→P7 | A1 A2 A3 A4 A6 | CK1 CK2 CK3 |
| **T2 深度调研·澄清**（Workflow B） | 信息不足的请求 | Round 1 五个宏观追问 / 完整度评估 / 假设清单 | P1→P2→P4→P8 | A1 A7 A8 | — |
| **T3 复评闭环**（Workflow C） | 研究卡点 / 止损判断 | 四项决策之一 / GRADE 等级 / 推翻条件 | P1→P2→P6→P7→P8 | A1 A4 A5 A9 A10 | CK2 |

## 三、阶段与依赖

```
P1 FREEZE ──┬──> P2 IDENTIFY ──> P3 COLLAPSE ──┐
            │                                  ├──> P5 ALIGN ──> P6 EXECUTE ──> P7 REVIEW ──> P8 NEXT
            └──> P4 CLARIFY ────────────────────┘
```

| 阶段 | 依赖 | 主工具 | 门禁 |
|------|------|--------|------|
| P1 FREEZE 冻结评估 | — | `state_io.py` | — |
| P2 IDENTIFY 内部分诊 | P1 | `state_io.py` | — |
| P3 COLLAPSE 坍缩组合 | P2 | `assemble_spawn_prompt.py` | ALIGN_ACK |
| P4 CLARIFY 澄清追问 | P1 | `assemble_spawn_prompt.py` | — |
| P5 ALIGN 对齐确认 | P3 + P4 | 人工 | ALIGN_ACK |
| P6 EXECUTE 单步执行 | P5 | `topic_scoring.py` | CK1 |
| P7 REVIEW 复评闭环 | P6 | `topic_scoring.py` | CK2 |
| P8 NEXT 下阶段收敛 | P7 | 人工 | CK3 |

关键分支：完整度 < 90% 或任一风险维 ≥ 7 → 走 P4；信息充分 → 跳过 P4 直接 P5；判定 C 档 / 止损 → 强制 CK2；升档 → 强制 CK3；结论冲突 → 五级仲裁，价值层 L5 上呈用户。

## 四、验收条件（能自动查的写检查，不能的显式交人）

| ID | 条件 | 检查实现 | 判定方 |
|----|------|---------|--------|
| A1 | 产出非空、语言与用户输入一致 | `sample_check:nonempty_language` | 程序 |
| A2 | 必含分档结论、禁「暂未定档」 | `sample_check:grade_bucket` | 程序 |
| A3 | 必含 3 条可辨识止损线 | `sample_check:stop_loss` | 程序 |
| A4 | 强结论必带 GRADE 等级 | `sample_check:grade_label` | 程序 |
| A5 | 复评必给四项决策之一、禁待定/观察 | `sample_check:review_decision` | 程序 |
| A6 | 评分越界必须 rc=1 拒绝 | `sample_check:scoring_edge` | 程序 |
| A7 | 信息不足必含 Round 1 五问 | `sample_check:clarify_round` | 程序 |
| A8 | 信息不足不得提前给方案 | `sample_check:no_premature_plan` | 程序 |
| A9 | 复评必含推翻条件 / 下一步 | `sample_check:next_action` | 程序 |
| A10 | 是否换方向 / 是否止损结案 | — | **用户** |
| A11 | 语义质量 / 文献真实性 / 表达 | — | **用户** |

> CK1 / CK2 / CK3 / ALIGN_ACK / L5 属**人工确认点**：程序只负责登记并提醒，不代替确认，也绝不标「自动验证通过」。

## 五、一条命令跑完检查

```bash
python3 scripts/rot.py check      # 18 条静态门禁 + 3 条结构检查，逐条独立 rc，证据落盘
python3 scripts/rot.py verify     # 文档 ↔ 仓库实际 全量差集（把发布契约第 5 条脚本化）
python3 scripts/rot.py sample --run-dir <产出目录>   # 对真实任务产出跑 A1–A9 断言
python3 scripts/rot.py feedback  # 反馈记录完整性 / 规则膨胀 / 认可样例状态
python3 scripts/rot.py roadmap   # 打印本图摘要
```

每次 `check` 生成结构化报告（检查对象 / 结果 / rc / 耗时 / 证据尾行）到 `.harness-runs/verify/`，内容变化后重跑即可比对。

## 六、反馈如何进入下一轮

错误按此优先级转化，而不是继续加提示词：**工具修复 → 程序检查 → 认可样例 → 文字规则**。
「单次要求」只写进本次 task 记录；只有同类错误真实复发 ≥ 2 次且已被程序检查承接，才晋升「长期规则」。
长期规则上限 24 条，满额时新规则须先归档一条旧规则并给证据。详见 [`feedback/RULES.md`](./feedback/RULES.md)。
