---
name: research-orchestration-workflow
description: "科研编排团 v2.0 强制工作流：科研选题（8维评分+S/A/B/C分档+止损线）、深度调研（骨架+多领域对照+GRADE评级）、复评闭环（维持/升档/降档/止损）。触发词：选题、立题、分档、方向评估、下注、综述、调研、文献策略、情报图谱、复评、升档、降档、止损、评分卡、证据等级、协议检查、envelope、信封校验。含 topic_scoring.py + protocol_check.py。"
---

# Research Orchestration Workflow Skill

> 科研编排团强制工作流模块，覆盖三大高频任务：选题 / 深度调研 / 复评闭环。

## 触发条件

当主理人/团员触发以下任务时，**必须**加载本 Skill：

| 任务类型 | 触发关键词 | 加载模块 |
|----------|-----------|----------|
| **科研选题** | "选题"、"立题"、"分档"、"方向评估" | 《科研选题工作流模块》|
| **深度调研** | "综述"、"调研"、"文献策略"、"情报图谱" | 《多视角深度研究模块》|
| **复评闭环** | "复评"、"升档"、"降档"、"止损" | 《输出模板与分档规则》|

## 模块 1：科研选题（5 步）

价值锚点识别（VALUE-A：Who/What/Why/How/Success Criteria）→ 结构分解（STRUCTURE-D 拆 3-5 子模块）→ 8 维评分 → S/A/B/C 分档（GRADE-BUCKET）→ 设 3 条止损线（STOP-LOSS）。

**产出**：《选题评分卡》（`templates/topic-scoring-card.md`，由 `scripts/topic_scoring.py` 生成）、《止损线矩阵》。

## 模块 2：深度调研（4 步）

骨架设计（meta-architect）→ 多领域对照（domain-expert，3-5 领域最优方法）→ GRADE 评级（methodological-reviewer）→ 盲点识别（遗漏变量/替代解释）。

**产出**：《深度调研路线图》、《关键文献清单》（含证据等级+时效）、《盲点清单》。

## 模块 3：输出模板与分档规则

### v2.0 协议层（新增）

**通信协议**：`references/agent-protocol.md` 包含消息信封/状态同步/上下文传递/任务分配/冲突仲裁/错误四分类/生命周期 9 节。所有 v2.0 团队成员按此协议通信。

**协议校验脚本**：`scripts/protocol_check.py` 12 个信封 + 4 个冲突仲裁单元测试。集成前运行：
```bash
python3 scripts/protocol_check.py envelope    # 12 用例
python3 scripts/protocol_check.py conflict   # 4 用例
python3 scripts/protocol_check.py integration # 集成仿真
```

### 分档规则

| 分档 | 入选标准 | 资源建议 |
|------|---------|----------|
| **S 档** | 8 维评分均 ≥ 7 分；至少 1 维 ≥ 9 分 | 重投入，多团队并行 |
| **A 档** | 8 维评分均 ≥ 6 分；至少 2 维 ≥ 8 分 | 标准投入 |
| **B 档** | 8 维评分均 ≥ 5 分；至少 1 维 ≥ 8 分 | 保守投入，留退出通道 |
| **C 档** | 任一维 < 5 分；或证据等级 < 3 | 不投入 / 止损 |

### 复评闭环决策规则

| 决策 | 触发条件 |
|------|---------|
| **维持** | 当前路径证据等级 ≥ 2b，且无新增关键风险 |
| **升档** | 前 3 项评分进步 ≥ 1 分；或新数据显著提升关键指标 |
| **降档** | 关键评分退步 ≥ 1 分；或新风险等级 ≥ 中 |
| **止损** | 至少 1 维评分 ≤ 3 分；或 ≥ 2 项关键风险不可控 |

## 用户确认检查点

本 Skill 涉及资源投入与方向止损，属高风险动作，以下 3 处**必须暂停等待用户确认**：

| 检查点 | 时机 | 确认内容 |
|--------|------|---------|
| **CK1 · 评分前** | 打分之前 | 向用户展示 8 维的**初步判断依据**（不是分值），确认无重大误解后再落分 |
| **CK2 · 止损后** | 判定为 C 档或决策为「止损」时 | **必须**询问用户：接受止损 / 转向相邻选题 / 补充信息后重评。禁止直接结案 |
| **CK3 · 重投前** | 决策为「升档」（追加资源）时 | 明确列出增量资源清单与预期回报，获 ACK 后方可写入路线图 |

> 例外：用户已在初始指令中明确授权「直接给结论」时，可跳过 CK1，但 CK2/CK3 不可跳过。

## 使用方式（目录名含连字符，不可直接 import，按文件路径加载）

**方式 1 · CLI（推荐）**：

```bash
python3 scripts/topic_scoring.py --topic "选题名" \
  --originality 8 --feasibility 7 --value-density 9 --data-availability 7 \
  --competition 6 --cognition 8 --resource-fit 7 --sustainability 7
```
越界/缺维时 stderr 打印 `❌ 评分失败：...`，退出码 1，不会静默错档。

**方式 2 · Python API**（复用 review_decision 时）：

```python
import importlib.util
from pathlib import Path
S = Path("~/.../scripts/topic_scoring.py").expanduser()  # 实际绝对路径
spec = importlib.util.spec_from_file_location("ts", S)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r = m.score_topic("选题名", {"originality": 9, "feasibility": 7, "value_density": 9,
    "data_availability": 8, "competition": 6, "cognition": 8, "resource_fit": 7, "sustainability": 8})
print(m.format_report(r))
m.review_decision(old, new, risks=["中"])  # → (维持/升档/降档/止损, 依据, 行动)
```

**方式 3 · 模板**：`templates/topic-scoring-card.md`，选题任务结束时由主理人填充。

## 铁律与异常处理（fallback）

**四条铁律**：强制分档（禁"暂未定档"）｜每选题必附 3 条止损线｜每结论必标 GRADE 等级｜复评必给四项决策之一（禁"待定/观察"）。

| 异常场景 | 处理动作 |
|------|---------|
| 评分越界 / 缺维 | 脚本报错（退出码 1）；主理人回传错误原文要求重打，**禁自行钳制/补默认值** |
| 脚本不可用 | 降级手工分档，报告标注「⚠️ 脚本不可用，手工分档」 |
| 分档落边界 | 报告写明「边界案例，±1 分即升降档」 |
| C 档但 min≥5 | 文案须写「未达 B 档门槛：最高分仅 X 分」，禁套用「任一维<5分」 |
| 证据不足无法评级 | 标「证据等级 5」+ 计入风险触发复评，禁跳过评级 |
| 跨界选题维度失配 | domain-expert 复核该维，报告标注「⚠️ 经专家复核」 |

**三处用户确认检查点**（高风险动作必停）：CK1 打分前展示 8 维判断依据｜CK2 判 C 档/止损后必问「接受/转向/重评」，禁直接结案｜CK3 升档前必列增量资源清单获 ACK。用户已授权「直接给结论」时 CK1 可跳，CK2/CK3 不可跳。

**原则**：任何异常与降级处理都在报告中显式留痕。
