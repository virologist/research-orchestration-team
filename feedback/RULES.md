# 反馈规则 · 单次要求 / 长期规则 / 认可样例

> 目的：让错误变成**工具、检查和好样例**，而不是继续堆提示词。
> 机器真值源：[`RECORDS.jsonl`](./RECORDS.jsonl)；叙事性的跨会话记忆仍在 `skills/research-orchestration-workflow/references/LEARNING.md`。
> 本文件由 `python3 scripts/rot.py feedback` 自动校验，2026-11-10 建立。

## 一、错误转化的优先级（从高到低）

| 优先级 | 转化形式 | 判据 | 本轮实例 |
|--------|---------|------|---------|
| 1 | **工具修复** | 错误来自工具行为，修完同类输入不可能再错 | `parents[N]` 硬索引 → `find_root()` 逐层探测；评分越界静默钳制 → `topic_scoring.py` rc=1 |
| 2 | **程序检查** | 要求可客观判定，补一条会红的检查 | 工作地图漂移 → `workmap_check.py` W1–W12；样例只有文字 expected → `sample_check.py` A1–A9 |
| 3 | **认可样例** | 需要展示「什么算好」，且样本来自真实运行 | [`accepted/`](./accepted/) 三个候选样例 |
| 4 | **文字规则** | 前三档都承接不了时才写，且必须计入上限 | 仅在本文件与 `workmap.json` 的 human 项登记 |

**硬约束**：新增文字规则前，必须先在 `RECORDS.jsonl` 说明「为什么前三档不适用」。否则 `rot.py feedback` 判红。

## 二、单次要求 vs 长期规则

| | 单次要求 | 长期规则 |
|---|---|---|
| 作用范围 | 仅本次任务 | 跨会话、跨任务 |
| 写入位置 | `LEARNING.md` 的 task 记录 | `RECORDS.jsonl` + 一条可执行检查 |
| 晋升条件 | — | ① 同类错误**真实复发 ≥ 2 次**（有 commit / 报告证据）；② 已被程序检查或工具修复承接；③ 写明失效时哪条检查会红 |
| 典型例子 | 「这次报告用中文表格」 | 「每条门禁分支必须有一只会红的负例盯着」 |

**上限 24 条**。达到上限时，新规则必须先归档一条旧规则并给出「该规则已被哪条程序检查完全覆盖」的证据；`workmap.json` 的 `feedback.rule_cap` 是机器真值源，`rot.py feedback` 会核对。

**降级机制**：一条长期规则若连续 3 轮迭代从未触发、且其承接检查一直绿，可标记 `archived`，但不删除——保留证据链。

## 三、认可样例（accepted examples）

- 只收**真实运行结果**：commit hash、CI run、实测输出、脚本 rc 必须可指回。
- 状态标注：候选样例一律标 **「AI 评估通过 / 待人工确认」**；只有用户明确确认后才改成 **「人工确认通过」**。
- **禁止**把「门禁全绿」直接等同于「产出质量好」：静态门禁证明的是包自洽，不是任务产出好。两者在样例里分开写。
- 每个样例必须含四段：来源与证据 / 为什么算好 / 可复跑命令 / 当前状态。

## 四、四种结果状态（与 WORKMAP.md 一致）

`自动验证通过` · `AI 评估通过` · `人工确认通过` · `尚未验证`。

- 程序只能标前两种；**人工确认通过只能由用户标**。
- 语义质量、文献真实性、价值取舍（A10/A11、CK1/CK2/CK3、L5）永远不进自动断言，程序只负责登记「这里需要人工确认」。

## 五、一轮反馈怎么进入下一轮

1. 出错 → 在 `RECORDS.jsonl` 追加一条，填 `type` / `evidence` / `conversion` / `status`；
2. 优先做工具修复或补检查 → 跑 `python3 scripts/rot.py check` 取得新证据；
3. 如果是「什么算好」的问题 → 往 `accepted/` 加候选样例，状态写待人工确认；
4. 只有复发 ≥ 2 次且已承接，才晋升长期规则；
5. 收口时跑 `python3 scripts/rot.py verify` 做全量文档差集，防止再次出现「资产内文档口径滞后」。

## 六、记录格式（`RECORDS.jsonl`，每行一个 JSON 对象）

| 字段 | 说明 |
|------|------|
| `id` | `FB-YYYYMMDD-NN` |
| `type` | `tool_fix` / `program_check` / `accepted_example` / `long_term_rule` / `single_request` |
| `source` | 错误或要求的来源（文件 / 报告 / 用户反馈 / 实测 rc） |
| `evidence` | 可复跑的实证：commit、run id、命令、路径 |
| `conversion` | 转化成了哪个工具 / 哪条检查 / 哪个样例 |
| `check` | 承接检查的脚本路径（工具修复与程序检查必填，且必须真实存在） |
| `status` | 四种状态之一；`archived` 仅用于降级归档 |
| `created` | `YYYY-MM-DD` |
