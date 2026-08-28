# Research Orchestration Workflow Skill

> 科研价值驱动研究编排团的强制工作流模块。覆盖三大高频任务：科研选题 / 深度调研 / 复评闭环。

## 触发条件

当主理人/团员触发以下任务时，**必须**加载本 Skill：

| 任务类型 | 触发关键词 | 加载模块 |
|----------|-----------|----------|
| **科研选题** | "选题"、"立题"、"分档"、"方向评估" | 《科研选题工作流模块》|
| **深度调研** | "综述"、"调研"、"文献策略"、"情报图谱" | 《多视角深度研究模块》|
| **复评闭环** | "复评"、"升档"、"降档"、"止损" | 《输出模板与分档规则》|

## 模块 1：科研选题工作流模块

### 工作流（5 步）

1. **价值锚点识别**：用 VALUE-A 卡片识别研究的真问题（Who / What / Why / How / Success Criteria）
2. **候选结构分解**：用 STRUCTURE-D 矩阵拆解为 3-5 个子模块
3. **多视角评分**：用 TOPIC-SCORING 卡做 8 维评分（原创性/可行性/价值密度/数据可得性/竞争烈度/认知层级/资源匹配/可持续性）
4. **分档决策**：用 GRADE-BUCKET 规则分档（S/A/B/C 四档）
5. **止损线设定**：用 STOP-LOSS 矩阵设定 3 条止损线

### 关键产出

- 《选题评分卡》（模板见 `templates/topic-scoring-card.md`）
- 《分档建议表》（自动生成，由 `scripts/topic_scoring.py` 辅助）
- 《止损线矩阵》

## 模块 2：多视角深度研究模块

### 工作流（4 步）

1. **骨架设计**：meta-architect 主导，输出"研究路线图骨架图"
2. **多领域对照**：domain-expert 主导，并行 3-5 个领域的最优方法对照
3. **证据等级评级**：methodological-reviewer 主导，标注每条结论的 GRADE 等级
4. **盲点识别**：识别综述中可能遗漏的关键变量、替代解释

### 关键产出

- 《深度调研路线图》
- 《关键文献清单》（含证据等级 + 时效性）
- 《盲点清单》

## 模块 3：输出模板与分档规则

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

## 使用方式

> ⚠️ **注意**：skill 目录名含连字符（`research-orchestration-workflow`），**不能**直接
> `from skills.research_orchestration_workflow.scripts... import`。必须按文件路径加载（见方式 1）。

### 方式 1：主理人 / 团员直接调用（Python API）

```python
import importlib.util
from pathlib import Path

# 按文件路径加载：目录名含连字符，无法作为 Python 包导入
SCRIPT = Path("/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/"
              "research-orchestration-team/skills/research-orchestration-workflow/"
              "scripts/topic_scoring.py")

def _load_scoring():
    spec = importlib.util.spec_from_file_location("topic_scoring", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

scoring = _load_scoring()

result = scoring.score_topic(
    topic_name="禽流感HA糖基化与宿主适应",
    scores={          # 8 维评分，每维必须是 1-10 的整数（越界会抛 ValueError）
        "originality": 9, "feasibility": 7, "value_density": 9,
        "data_availability": 8, "competition": 6, "cognition": 8,
        "resource_fit": 7, "sustainability": 8,
    },
)
print(scoring.format_report(result))   # 分档 + 止损线 + 决策建议

# 复评闭环（对比前后两轮评分，必给维持/升档/降档/止损之一）
decision, reason, action = scoring.review_decision(scores_old, scores_new, risks=["中"])
```

### 方式 2：以模板形式输出

参考 `templates/topic-scoring-card.md`，由主理人在每个选题任务结束时填充。

### 方式 3：以 CLI 工具调用（推荐，最简单可靠）

```bash
python3 scripts/topic_scoring.py \
  --topic "禽流感HA糖基化与宿主适应" \
  --originality 8 --feasibility 7 --value-density 9 \
  --data-availability 7 --competition 6 --cognition 8 \
  --resource-fit 7 --sustainability 7
```

**CLI 错误处理**：评分越界（如 `--originality 11`）或缺失维度时，脚本会在 stderr 打印
`❌ 评分失败：...` 并以退出码 1 结束，不会静默产生错误分档。

## 注意事项

- **强制分档**：所有选题必须落到 S/A/B/C 四档之一，禁止"暂未定档"
- **必给止损线**：每条选题必须附 3 条止损线（数据 / 时间 / 资源）
- **证据等级必标注**：每条结论附 GRADE 等级，禁止纯定性判断
- **复评决策必给**：四项决策之一必选，禁止"待定/观察"
