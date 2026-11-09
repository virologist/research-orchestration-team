# Harness 迭代进化 · 状态文件（断点续跑单一事实源）
<!-- c8-exempt: audit-history -->
> 适用对象：科研价值驱动研究编排团（research-orchestration-team，Team 型 8 成员）
> 指令来源：《科研编排团·Harness迭代进化指令》（10 节，§0–§10）
> 用途：每轮会话执行一个「诊断 → 构建 → 测试&debug → 再诊断」闭环；下轮从本文件断点续跑。

## 1. 元信息

| 项 | 值 |
|---|---|
| 状态文件版本 | 1 |
| 当前轮次 | **R1（首轮）** |
| 创建时间 | 2026-11-08（GMT+8） |
| 指令标识 | sha256 前 16 位 `789e7c720094cbe0`（正文 4896 字符 / 10634 字节 / 70 行，含 §0–§10 全文；抽取件 `/tmp/rot-r1-instruction.md`） |
| 执行者 | `agent-harness-architect`（Agent Harness 专家团 P1 架构师角色） |
| 执行者裁决依据 | 指令 §0 指定「Agent Harness 架构设计师\|墨衡」，经全环境检索确认该专家不存在而冻结；管家节点 2026-11-08 裁决 **A**：改由 agent-harness-expert 的架构师角色执行，不虚拟身份 |
| 迭代对象基线 | **v2.3.0** |
| canonical HEAD | `b521563`（docs(learning): v2.3.0 task 记录 + CI 环境性假红 lesson） |
| tag | `v2.3.0` → `85e343c`（CI 绿 commit） |
| 工作树 | **R1 全闭环（GATE3 已过）**：12 文件已改 + 5 文件新建（均在授权范围内）；未 commit、未 push、未同步三源、未升版、未打 tag |
| canonical 路径 | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/research-orchestration-team/` |
| 加载可见性 | `my-experts/plugins/` 下 **7 个专家包 + 1 个共享件**（`shared-core/` 为联邦共享真源，非独立专家包）：agent-harness-expert / research-orchestration-team / smart-textbook-team / smart-textbook-v2 / triz-invention-team / vet-med-ppt-team / viral-evo-lab；本包双 manifest + settings.json 均在位 |

## 2. §0 启动自检复检（R1）

| 自检项 | 结果 | 证据 |
|---|---|---|
| 身份核验 | ✅ 已按裁决指定 | 管家节点回「A」；不冒用不存在的「墨衡」 |
| 读文件 | [实] | 本轮实际读取 CHANGELOG / REDTEAM-REPORT / 双 manifest / settings.json 等 |
| 写文件 | [实] | 本文件即落盘产物 |
| Bash | [实] | git / python3 / wc / find 均已实跑 |
| 子代理调度 | [实] | R1 Phase A 四路并行只读调研 |
| GitHub API / git push | [待核实] | 本轮冻结期不触碰；核验办法 = Phase C 后 `gh api` 只读探测 |
| 联网检索 | [待核实 → 本轮实测] | 核验办法 = 实际调用一次 WebSearch，结果仅用于能力核验，不进诊断结论 |
| 仓库定位 | ✅ | canonical 路径存在，HEAD b521563，工作树干净 |
| 状态续跑 | ✅ 首轮 | 本文件原不存在 → 判定 R1 并建立 |
| 意图漂移 | 0%（< 15%，静默通过） | 首轮无历史状态可比；本文件 §3 建立漂移基线 |

## 3. 意图漂移基线（后续轮次对比基准）

| 维度 | R1 基线表述 |
|---|---|
| 使命 | 对专家团执行可持续「诊断→构建→测试&debug→再诊断」闭环，每轮一循环、结果落盘、下轮断点续跑 |
| 终态 | 可复用于任意科研选题 / 深度调研 / 高价值决策 / 方法学复评场景的高质量专家团 |
| 硬边界 | 永不产出科研正文；只产出团队自身的 agent 定义 / 协议 / skill / 脚本 / manifest / 文档 / 测试 |
| 事实源 | §3 诊断基准清单所列仓库资产；已修复问题不重复上报；每条结论引用具体文件路径与章节 |
| 门控 | Phase A → [GATE1] → Phase B → [GATE2] → Phase C（分批）→ Phase D → [GATE3]，每个 GATE 等管家节点「继续/执行」 |
| 验收 | §8 九套门禁全绿；任一红 → 根因定位 → 修复 → 全量回归；失败保留现场快照 |
| 收敛终止 | 连续 2 轮再诊断无 P0/P1 新问题且 §8 全绿 → 输出收口建议等管家节点裁决 |

> 漂移判定口径（后续轮）：比较新一轮指令与本表六维表述；>30% 暂停等裁决，15–30% 标 `[目标偏移:轻度]`，<15% 静默通过。

## 4. 四阶段进度台账

| 阶段 | 状态 | 起止 | 产出 | GATE |
|---|---|---|---|---|
| Phase A 只读诊断 | ✅ 已完成 | 2026-11-08 | 现状诊断报告 / 关键问题清单 P0-P2 / 升级设计（Mermaid 双图）→ 对话输出 | **GATE1 已通过**（管家节点放行「执行，直接进 Phase C」「仅本地改文件」） |
| Phase B 规划 | ✅ 已完成 | 2026-11-08 | 执行计划（分批：批次1 退出码真门禁 → 批次2 阶段名归一化 → 批次3 C8 声明式豁免 → 批次4 协议/文档/运行时三层 → 批次5 文档口径 + 成员 ID 一致性门禁） | **GATE2 已通过**（与 GATE1 合并放行） |
| Phase C 构建＋测试&debug | ✅ 已完成 | 2026-11-08 ~ 2026-11-09 | 8 批次全部落盘；脚本改动 8 文件 +1517 行、新建 5 文件；主理人对每批次做独立注入实锤验收 | 每批后报告（已出） |
| Phase D 再诊断＋状态落盘 | ✅ 已完成 | 2026-11-09 | 本文件更新（§4 台账 / §5 基线 / §8 失败模式库 / §10 下轮入口）+ GATE3 验收报告 | **GATE3 已通过**（§8 最终全量回归 12/12 全绿 + 3 组独立负向实锤 + 还原后 md5 逐字节一致） |

### 4.1 Phase C 批次明细（断点续跑用）

| 批次 | 范围 | 落点 | 状态 |
|---|---|---|---|
| 批次 1 | 退出码真门禁（`main()` 无返回值 → 恒 rc=0） | `protocol_check.py` | ✅ 主理人独立验收 |
| 批次 2 | `--phase` 阶段名归一化（8 阶段名 × 2 写法 + 大小写 + 整数 + 非法值） | `assemble_spawn_prompt.py` + 新建 `scripts/test_phase_normalization.py` | ✅ 主理人独立验收（26/26 + vendor-only 隔离复验） |
| 批次 3 | C8 声明式豁免（白名单 + 文件头标记双路径） | `manifest_check.py` + `manifest_check_selftest.py` | ✅ 主理人独立验收（23/23，真实注入双向验证） |
| 批次 4A | 协议层证据链 + 两层 pointer 校验 + 集成段去自证化 | `protocol_check.py` + 新建 `protocol_check_selftest.py` | ✅ 主理人独立注入实锤两次 + 7 探针 |
| 批次 4B | 协议文档角色矩阵 + 文档-实现一致性表 + 两个模板登记 | `agent-protocol.md` + `team-lead.md` | ✅ 主理人逐项核实（D3/D4/模板登记已落地） |
| 批次 4C | 状态机代码化（按序推进 / 熔断 / 预算 / metrics / `fail` 子命令） | `state_io.py` + `agent-registry.md` | ✅ 主理人独立实测（跳级 rc=1、熔断 rc=1、metrics 记 null） |
| 批次 5A | C13 成员 ID 五处一致性门禁 + N24/N25/N26 注入负例 | `manifest_check.py` + `manifest_check_selftest.py` | ✅ 主理人独立验收（73 项 + 26/26；4 处破坏 + 空集合 fail-closed 全部实锤） |
| 批次 5B | 全仓数字口径对齐 + README 结构树补齐 + 门禁体系现状小节 | `README.md` + `CONTRIBUTING.md` + `SKILL.md` + `agent-registry.md` + `validate.yml` | ✅ 主理人独立验收（12 套门禁全绿；另修 tarball 404 死链与「三套并存」标题错） |

## 5. §8 验收基线（Phase C 执行前登记，来源 v2.3.0 CHANGELOG「Regression evidence」）

| # | 门禁 | 基线值 | R1 实测 |
|---|---|---|---|
| 1 | `manifest_check.py` + selftest | 64/64 + 21/21 | ✅ **73/73 + 26/26**（批次 5 新增 C13 成员 ID 五处一致性，C13 自身贡献 9 项；selftest 新增 N24/N25/N26） |
| 2 | `harness_eval.py` + selftest | 12/12 + 14/14 | ✅ 12/12 + 14/14 |
| 3 | `routing_eval.py` + selftest | 39/39（R1-R6）+ 12/12 | ✅ 39/39 + 12/12 |
| 4 | `tests/test_vendor_core.py` | V1-V6 6/6（隔离态 V4 SKIP） | ✅ 6/6（安装态全跑，无 SKIP） |
| 5 | `protocol_check.py` | envelope 16/16(v2.4) + conflict 5/5 + integration 8/8 | ✅ **37/37(v2.4) + 12/12(legacy) + 5/5 + 阶段流水线 9/9 + HANDOFF 回引链检出**（批次 4A 去硬编码自证并把主套件从 16 扩到 37） |
| 6 | `topic_scoring.py` 冒烟 | 越界 rc=1 / 缺维 rc=2 / 正常 rc=0 | ✅ 越界 rc=1 / 缺维 rc=2 / 正常 rc=0 |
| 7 | `state_io.py` 全生命周期 | 全链路 rc=0 / 并发 20 路 | ✅ init rc=0；跳级 advance rc=1；按序 8 阶段全 rc=0 + 8 检查点；resume / budget / finish rc=0；`budget` 落盘 `turns_max=30 / tokens_max=200000 / max_time_sec=1800 / max_failures=5`；`metrics` 4 键未上报记 `null`；熔断路径：`--force` 缺 reason rc=1、`fail` 空 reason rc=1、失败计数达上限 → `status=aborted` + `abort_reason=circuit_breaker`、熔断后 advance rc=1、熔断后 finish rc=0 且**保留** `aborted` 不改写 |
| 8 | 官方 `validate_expert.py` | 安装态原位 0 error（tempfile 副本环境性误报不计） | ⚠️ **本机不存在该脚本**（已全盘检索 `~/.workbuddy` / `~/.claude` / WorkBuddy.app 资源目录 / 根目录 6 层）→ 以包内 `manifest_check.py` + `tests/test_vendor_core.py` V5/V6 安装态冒烟替代 |
| 9 | 双 manifest 一致性人工 review | version 2.3.0 / 2.3.0 | ✅ 两份均 2.3.0；C2 共享字段仅 7 个（不含 description），故双 manifest 描述文本差异不违规 |
| 10 | 阶段名归一化（批次 2 新增） | — | ✅ `test_phase_normalization.py` 26/26；shim 实测 `--phase CLARIFY` / `--phase=CLARIFY` / `--phase clarify` / `--phase 4` 全 rc=3（任务包缺失=参数已通过 argparse），`--phase BOGUS` rc=2（argparse 原报错） |
| 11 | 协议注入式负例（批次 4A 新增） | — | ✅ `protocol_check_selftest.py` 13/13；主理人独立注入实锤两次（破坏阶段序列 → integration rc=1；破坏 evidence ref 校验分支 → envelope rc=1）+ 7 探针全通过 |
| 12 | 模板一致性（批次 4B 新增） | — | ✅ `result-envelope-v2.4.json` 6 必填字段与 `REQUIRED_FIELDS_V24` 逐字一致（缺失 0）；协议登记的两个模板路径均可解析；`cross-domain-combo.md` 覆盖 biomed/general/ai 三组合 + 86 个占位符 |

| 13 | GATE3 最终全量回归（R1 收口实测） | — | ✅ **12/12 套全绿**（逐条独立执行取 rc，不串成一条命令——见 FM-R1-07）；详见 §5.1 |

> 注：Phase A 为只读诊断，不运行改动型门禁；上表为登记基线，避免另造平行基线（§7-3）。
> **第 8 项口径修正**：该基线项在 R1 环境下不可执行（宿主未随包分发官方校验器），已按「环境性已知限制」处理，改由包内门禁覆盖同一风险面（结构完整性 + 安装态冒烟）。

### 5.1 GATE3 最终验收证据（R1 收口实测，2026-11-09）

**逐条独立执行，每条单独取退出码**（禁止把多套门禁串成一条命令后只看整体 rc——FM-R1-07）：

| # | 门禁 | rc | 实测计数 |
|---|---|---|---|
| 1 | `scripts/manifest_check.py` | 0 | 73/73 |
| 2 | `scripts/manifest_check_selftest.py` | 0 | 26/26 |
| 3 | `scripts/harness_eval.py` | 0 | 12/12 |
| 4 | `scripts/harness_eval_selftest.py` | 0 | 14/14 |
| 5 | `scripts/routing_eval.py` | 0 | 39/39 |
| 6 | `scripts/routing_eval_selftest.py` | 0 | 12/12 |
| 7 | `tests/test_vendor_core.py` | 0 | V1–V6 6/6（安装态 0 SKIP） |
| 8 | `scripts/test_phase_normalization.py` | 0 | 26/26 |
| 9 | `protocol_check.py envelope` | 0 | 37/37(v2.4) + 12/12(legacy) |
| 10 | `protocol_check.py conflict` | 0 | 5/5 |
| 11 | `protocol_check.py integration` | 0 | 阶段流水线 9/9 + HANDOFF 回引链覆盖 8/8 检查点 |
| 12 | `protocol_check_selftest.py` | 0 | 13/13 |

**主理人独立负向实锤**（不采信执行者自报；每次破坏后还原，md5 与基线逐字节一致）：

| # | 破坏手法 | 期望 | 实测 |
|---|---|---|---|
| 负例 1 | 协议 §1 角色矩阵改一名成员 ID（`synthesis-integrator` → `synthesis-integratorX`） | rc=1 且逐项列差异 | ✅ rc=1；`多出: ['synthesis-integratorX']` / `缺少: ['synthesis-integrator']`；还原后 rc=0、md5 一致 |
| 负例 2 | 清空 `agents/` 下全部 `*.md`（真值源为空） | rc=1（fail-closed，空集合不静默通过） | ✅ rc=1；「C13 真值源为空: agents/ 下没有任何 *.md 文件……空集合一律判红」；还原后 rc=0、成员数 8 |
| 负例 3 | 破坏 `state_io.py` 的 `PHASES`（删 `NEXT`） | 集成段 rc=1 且列出两侧序列差异 | ✅ rc=1；「阶段流水线校验：8/9 通过」+ 声明序列 vs `state_io.PHASES` 逐项对比；还原后 rc=0、md5 一致 |
| 负例 4 | 4C 状态机 9 条路径（init / 按序 / 跳级 / 重复同阶段 / `--force` 缺 reason / `--force` 带 reason / advance 传 `--max-*` / `fail` 空 reason / fail 后继续） | 各自 rc 与设计语义一致 | ✅ init 0、按序 0、跳级 1、重复同阶段 1、`--force` 缺 reason 1、带 reason 0、`--max-*` 被忽略并告警、`fail` 空 reason 1、fail 后 advance 0 |

> **负例 3 的锚点教训**：`PHASES` 定义的换行位置与记忆不符（真实断点在 `CLARIFY", "ALIGN",` 之后），首次构造的跨行锚点命中 0 次 → 破坏无效但 rc 仍为 0。这与 FM-R1-05 同源：**「锚点唯一命中」是必要不充分条件，注入后必须确认 rc 真的翻转**。

## 6. R1 诊断基准资产清单（§3，实际存在性已核验）

| 族 | 实际文件 |
|---|---|
| agents/（8） | domain-expert-ai / domain-expert-biomed / domain-expert-general / meta-architect / methodological-reviewer / research-orchestration-team-team-lead / socratic-questioner / synthesis-integrator |
| skills/…/（1 skill） | SKILL.md；references/{agent-protocol, agent-registry, LEARNING}.md；scripts/{memory_log, state_io, topic_scoring, protocol_check}.py；templates/topic-scoring-card.md |
| scripts/（7） | assemble_spawn_prompt.py；manifest_check{,_selftest}.py；harness_eval{,_selftest}.py；routing_eval{,_selftest}.py |
| tests/ | test_vendor_core.py |
| docs/ | REDTEAM-REPORT.md；arbitration-L4L5-live-test.md；harness-eval-report-v2.0.2.md；**本文件（R1 新增）** |
| 根 | CHANGELOG.md / README.md / CONTRIBUTING.md / settings.json / test-prompts.json / .gitignore |
| 双 manifest | `.claude-plugin/plugin.json`、`.codebuddy-plugin/plugin.json`（+ 各自 marketplace.json） |
| vendor + CI | `vendor/shared-core/{VENDOR.json, assemble_spawn_prompt.py}`；`.github/workflows/validate.yml` |

> **§5-1 对象锚定校正**：指令 §3 措辞「scripts/ 校验六件套」「skills/…scripts/ 四件」与实际资产分布不完全一致——仓库 `scripts/` 下是 3 套校验器 + 3 套 selftest + 1 装配器；`protocol_check.py`/`topic_scoring.py`/`state_io.py`/`memory_log.py` 在 skill 的 `scripts/` 下；`validate_expert.py` 是宿主官方工具、不在本仓库内。本状态文件以实测清单为准，禁止引用仓库中不存在的组件。

## 7. 已修复问题黑名单（禁止当作新发现重复上报）

> **引用式登记（R1 修订）**：本表**不转录历史缺陷的原始措辞**。`scripts/manifest_check.py` 的 C8 对仓库全文做废弃表述正则扫描，其豁免名单 `SCAN_EXEMPT`（:108）是硬编码文件名白名单，本文件不在其中——R1 首次落盘时因抄录历史术语名触发 3 项假红（见 §8 `FM-R1-01`）。逐条原文以下列审计文档为准：
>
> | 来源 | 覆盖范围 |
> |---|---|
> | `docs/REDTEAM-REPORT.md` §二 / §四 | 15 项缺陷（A1–A4 / B1–B3 / C1–C2 / D1–D4 / E1–E2），全部已修复；回归结果 12/12 信封、5/5 仲裁、8/8 集成 |
> | `CHANGELOG.md` `[2.2.0]` Added / Fixed / 交叉验证后修复 | 状态持久化、路由一致性、CI 门禁、settings 恢复、工具名校准、并发互踩、协议门禁方向、全库阶段名统一等 |
> | `CHANGELOG.md` `[2.3.0]` Added / Changed | R6 工具真实性、R5 全 8 成员分级解析、selftest 12 例、CI 环境性假红根治、官方校验器限制文档化 |
> | `CHANGELOG.md` 各版 Regression evidence 表 | 门禁实测值与已知环境性限制 |
>
> **黑名单语义**：上述四处登记过的缺陷一律不得作为后续轮次的新发现重复上报；疑似回归须标「回归核验」并附门禁实测值。环境性已知限制（官方校验器安装路径、R6 在 CI 态显式 SKIP、V4 隔离态 SKIP、tag 只打 CI 绿 commit）同样按已知限制处理，不计缺陷。

## 8. 失败模式库（R1 建立，初始为空）

| ID | 轮次 | 失败节点 | 根因类别 | 根因摘要 | 已尝试路径 | 风险等级 | 预防建议 | 匹配关键词 |
|---|---|---|---|---|---|---|---|---|
| FM-R1-01 | R1 | Phase A 状态文件首次落盘 → `manifest_check.py` C8 | 逻辑错误（门禁设计） | C8 走全库 `rglob` 正则扫描，豁免仅靠 `SCAN_EXEMPT` 硬编码文件名白名单；任何**新增**审计类文档只要引用历史缺陷术语名即被判红（实测 63 通过 / 3 失败，基线应 64/64） | ① 只读复现并定位到 `manifest_check.py:108/418`；② 状态文件 §7 改引用式登记、不转录旧术语；③ 重跑全量回归 | 🟡 中（可恢复，但阻塞「状态文件记录失败模式库」这一迭代刚需） | Phase C 根治方案见 GATE1 报告 P0-1：豁免机制声明化 + 注入式负例证明未标记文件仍被拦截；下轮 Phase A 先比对本条 | C8 / SCAN_EXEMPT / 审计文档 / 假红 / 状态文件落盘 |
| FM-R1-02 | R1 | Phase C 主理人验收 → 检索命令返回空结果 | 工具误用（检索工具选型） | 在 Bash 里对含中文/正则元字符的 pattern 做 `grep`，本仓库 3 组检索（team-lead / state_io / topic_scoring）**全部返回空**，但文件确有命中——是 Bash `grep` 在该沙箱环境下的假阴性，不是「内容不存在」 | ① 改用专用检索工具复验，3 组全部命中；② 此前同类假阴性已累计 3 次，本次为第 4 次 | 🟢 低（易发现，但若轻信会造成「误判文件无此内容」的错误结论） | **检索一律用专用检索工具，不用 Bash grep**；Bash grep 返回空时必须用第二种工具交叉验证后才可下「不存在」结论 | grep 假阴性 / 检索为空 / 中文 pattern / 交叉验证 |
| FM-R1-03 | R1 | Phase C 批次 2 验收 → vendor-only 隔离测试被污染 | 环境污染（测试前置条件缺失） | shim 的 `_find_federal()` 从包根父目录起**逐级向上 4 层**查找 `shared-core/assemble_spawn_prompt.py`；隔离测试目录放在 `/tmp` 下时，被 `/tmp/shared-core/`（他包历史拷贝，sha256 与联邦真源一致）抢先命中，导致「vendor 兜底路径」实际未被测到 | ① 发现 `SHIM_DEBUG=1` 打印的 core 来源是 `federal` 而非 `vendor`，判定隔离失效；② 改用 `$HOME` 下无同名祖先目录的干净路径重测，来源确认为 vendor | 🟡 中（当前无害——同名副本 sha256 与联邦真源一致，内容不漂移；但若祖先目录存在**旧版**或被篡改的同名文件，会被静默加载并绕过 `VENDOR.json` 哈希门禁） | 隔离测试必须在**祖先链无同名目录**的路径下构造，并断言 `SHIM_DEBUG=1` 打印的来源确实是 `vendor`；shim 向上查找的脆弱性列入下轮待办（可加「命中即校验 sha256 与 VENDOR.json 一致，不一致则拒绝加载」硬校验） | shim / _find_federal / vendor 兜底 / 隔离测试污染 / SHIM_DEBUG / sha256 |
| FM-R1-04 | R1 | Phase C 验收 → 「去标记 → C8 应红」实测不红 | 验证方法错误（验收前提不成立） | 该验收项的前提是「状态文件本身含历史术语」，但批次 3 已把它改成**引用式登记**，实测该文件对 C8 全部 13 条规则的命中数为 **0**；去标记后自然不会变红。若据此判定「C8 漏扫新文件」即属误判 | ① 逐文件统计全仓 C8 命中，确认 4 个文件有命中且均在豁免名单内；② 改用**真实注入**做双向验收：同一文件注入旧术语 → 带标记 64/64、去标记 rc=1 | 🟡 中（若未察觉，会把「验收前提不成立」误判成「门禁失效」，进而在错误方向上改门禁） | **负例验收必须先确认被测物当前确实含违规内容**（命中数 > 0）再做「去掉防护应变红」的双向测试；否则改用真实注入构造违规态 | 验收前提 / 负例 / 命中数 / 双向验收 / 假绿 |
| FM-R1-05 | R1 | Phase C 批次 4A → selftest N9 首轮 rc=0（应为 1） | 负例设计错误（注入锚点未命中生效分支） | 注入 `_invalid_pointers` 的**第一个**分支，但被测反例指针（`state://phase2/xxx`）通用形态合法、实际由**第二个**分支（P2 cp-* 要求）抓出 → 短第一个分支完全不影响检出，rc 仍为 0，负例形同虚设 | ① 锚点改为覆盖整个两分支块；② 3 条对抗核验（整函数替换）确认外层 selftest 立即报警 | 🟡 中（假绿会让「校验器已被废掉」伪装成「校验器有效」） | **注入锚点必须指向真正生效的分支**——「锚点唯一命中」是必要条件，**不是充分条件**；注入后必须确认 rc 真的翻转（0→1），不能只看用例显示 PASS | 注入锚点 / 假绿 / 负例设计 / 分支命中 / rc 翻转 |
| FM-R1-06 | R1 | Phase C 批次 4A → 集成段负例两个维度互相干扰 | 负例设计错误（反例自带无关失败原因） | 集成段反例原用「仅 1 条形态非法条目」，此时 8 个 cp 全部未覆盖 → `missing` 必然非空 → **无论 pointer 形态校验是否生效都能判「检出」**，属假绿（两个失败原因混在一条反例里） | ① 改为「8 个 cp 全部正常覆盖 + 1 条额外形态非法条目」，两个维度正交；② 形态校验失效时返回 `[]` → 门禁失败 | 🟡 中（假绿会让失效的校验被当成有效） | **一条负例只承载一个失败维度**；反例必须让「被破坏的那条规则」成为**唯一**的失败原因，否则无法证明该规则被检出 | 负例设计 / 维度正交 / 唯一失败原因 / 假绿 |
| FM-R1-07 | R1 | Phase C 批次 5 验收 → 整批门禁命令被 SIGTERM 截断 | 工具误用（长任务未隔离执行） | 8 套门禁串在一条 Bash 命令里跑，其中 `test_phase_normalization.py` 耗时较长，整批命令被沙箱以 SIGTERM（exit 137）截断，**导致后序门禁根本没执行**——若只看该命令的整体退出码会误判为「全绿」 | ① 拆成单条独立调用逐个取 rc；② 超长门禁单独跑并显式设 timeout | 🟢 低（易发现，但整批截断会掩盖未执行的门禁） | **门禁必须逐条独立执行并逐条断言退出码**，禁止把多套门禁串成一条命令后只看整体 rc；长耗时门禁单独跑并显式设超时 | SIGTERM / exit 137 / 批量门禁 / 整批截断 / 退出码 |
| FM-R1-08 | R1 | Phase C 批次 5 验收 → `run()` 辅助函数把整个命令当成单个参数 | 工具误用（shell 辅助函数签名错误） | 写的辅助函数 `run() { "$@" >log 2>&1; rc=$?; }` 被调用成 `run "python3 scripts/x.py"`（单个带引号字符串），`"$@"` 展开成一个整体参数 → shell 试图执行名为「python3 scripts/x.py」的单个命令 → rc=127 全部失败。**表面现象是「所有门禁都 127」，真实原因是参数封装错误而非门禁坏了** | ① 改为 `run() { local tag="$1"; shift; "$@" ...; }`；② rc=127 立即按「命令未找到」排查而非怀疑门禁 | 🟢 低（易发现） | 批量执行门禁的辅助函数必须 `shift` 掉 tag 参数；**rc=127 一律先按「命令/路径不存在」排查**，不要直接归因为门禁失效 | rc=127 / 辅助函数 / shift / 命令未找到 / 参数封装 |

> §9：下轮 Phase A 先与本库比对，匹配度 >70% 先输出历史摘要与预防建议。

## 9. 版本与发布契约（§5-13 登记）

- 改 agent 必同步两份 manifest（`version` + `agents` 清单）；CHANGELOG 与版本号同步。
- push 后 OneDrive 镜像 `git pull --ff-only` 并 `rev-parse` 核对两处 HEAD。
- `validate_expert.py` 仅安装态原位运行；tempfile 副本环境性误报不计失败。
- 高危动作（`git push --force`、`rm -rf`、gh release、覆写共享资源）先警告并等管家节点确认。

## 10. 下轮入口（R2 起始状态）

### 10.1 下一轮起始阶段

- **R2 从 Phase A 开始**（只读诊断）。R1 已完成 Phase A→B→C→D 全程，R2 需先做**再诊断**，把 R1 的产出当作待验证对象而非既成事实。
- R2 的**意图漂移基线** = 本文件 §3 六维表述（R1 基线）；若 R2 指令与该基线偏离 >30% 暂停等裁决。
- R2 的**事实源** = 本文件 §6 资产清单 + §5 验收基线表（R1 实测列）。R1 已修复的问题见 §7 黑名单，**不得作为新发现重复上报**。
- R2 的**失败模式前置比对**：先与 §8 失败模式库（FM-R1-01 ~ FM-R1-08）比对，匹配度 >70% 则先输出历史摘要与预防建议，再动手。

### 10.2 R1 未闭环问题（下轮必查）

| # | 问题 | 状态 | 下轮动作 |
|---|---|---|---|
| 1 | 官方 `validate_expert.py` 本机不存在 | **环境性已知限制**（非缺陷） | R2 若宿主更新该工具，补装后跑安装态原位校验，接管 §5-8 的替代口径 |
| 2 | `assemble_spawn_prompt.py` shim 向上查找 `shared-core/` 的脆弱性 | **未闭环**（FM-R1-03） | 给 shim 加「命中即校验 sha256 与 `VENDOR.json` 一致，不一致则拒绝加载」硬校验；当前若祖先目录存在旧版/被篡改的同名文件，会被静默加载并绕过哈希门禁 |
| 3 | `token_budget` 无硬截断 | 未闭环（低优先） | R2 视优先级决定是否补 |
| 4 | `protocol_check.py` 集成段的 `cp-001~cp-008` 检查点清单仍为硬编码 | 未闭环（低优先） | 当前与 `state_io.py` 的阶段序列已交叉比对（真断言），但 cp 清单本身未动态化；成员增删 cp 编号变动时需同步 |
| 5 | selftest 约 350s IO 耗时 | 未闭环（低优先） | 可用硬链接替代复制提速 |
| 6 | `avatars/domain-expert.png` 不被任何 manifest 引用 | **已闭环 · 保留（既定决策）** | R2 复核发现：v2.1.0 CHANGELOG 已明确定策「保留（防历史引用）」，并非「待清理的孤儿文件」。R1 §10.2 曾误登记为待删除项，与既定决策冲突，R2 已改正。不再作为遗留项跟踪 |
| 7 | GitHub Release tarball 资产名不统一 + v2.2.0/v2.3.0 无 tarball 资产 | **R1 已修文档**（资产补发未闭环） | README 方式 3 原链 `v2.2.0/research-orchestration-team-2.2.0.tar.gz` 实测 HTTP 404；已改为指向 v2.1.2 的 `rot-v2.1.2.tar.gz` 并加「资产名不统一 / 当前版本无 tarball」的说明。**发版侧补 tarball 资产**仍需在下次发布时一并处理 |
| 8 | README「安装方式」标题写「三套并存」但实际列 4 种方式 | **R1 已修** | v2.0 时期引入就存在的表述错误（从引入 commit 起就错），R1 改为「四种并存」 |

### 10.3 R1 验收遗留

- **R1 未做升版**：包 `version` 仍为 `2.3.0`，本轮改动全部停留在工作树（未 commit / 未 push / 未三源同步 / 未打 tag）。升版与发布属高危动作，需管家节点单独裁决。
- **CI step 名已改**：`Routing consistency check (R1-R5)` → `(R1-R6)`（R6 已在 v2.3.0 落地，step 名未同步）。**该改名会触发一次 CI 重跑**，需与首次 push 一并完成。
- **CHANGELOG 未写 v2.4.0 条目**：R1 的全部改动尚未进入 CHANGELOG。升版时需补，含批次 1–5 的变更摘要与回归证据表。
- **§7 黑名单的 4 处引用式登记仍有效**，但新增的 8 条失败模式（FM-R1-01 ~ FM-R1-08）需在升版时同步进包内 `LEARNING.md`。

### 10.4 收口判据进度

| 判据（§3「收敛终止」） | 状态 |
|---|---|
| 连续 2 轮再诊断无 P0/P1 新问题 | **0/2**（R1 为首轮，R2 再诊断后计） |
| §8 全量回归全绿 | **R1 达成**（GATE3 实测 12/12 全部 rc=0，见 §5.1） |
| 输出收口建议等管家节点裁决 | 🔄 **已输出收口建议**（见 GATE3 报告）；**升版 / commit / push / 三源同步 / 打 tag 需管家节点单独授权** |

---

## 变更记录

| 轮次 | 日期 | 变更 | 操作者 |
|---|---|---|---|
| R1 | 2026-11-08 | 首轮建立（§0 判定状态文件不存在）；登记基线、自检、漂移基线、资产清单、已修复黑名单、§8 基线、空失败模式库 | agent-harness-architect |
| R1 | 2026-11-08 | Phase A 诊断 + Phase B 规划完成，GATE1/GATE2 放行「仅本地改文件」 | agent-harness-architect |
| R1 | 2026-11-08 | Phase C 批次 1–4 落盘（退出码真门禁 / 阶段名归一化 / C8 声明式豁免 / 协议·文档·运行时三层） | agent-harness-architect + 4 执行者 |
| R1 | 2026-11-09 | 4B 中断现场核实：D3/D4/模板登记已落地且与 4A 实现逐条对齐；未重做 | agent-harness-architect |
| R1 | 2026-11-09 | Phase C 批次 5 落盘：C13 成员 ID 五处一致性门禁（+9 项）+ N24/N25/N26 注入负例 + 全仓数字口径对齐 + README 结构树补齐 + 「门禁体系现状」小节 | agent-harness-architect + 2 执行者 |
| R1 | 2026-11-09 | 批次 5 收口修复：README tarball 404 死链 → 改指 v2.1.2 实际资产名 + 加限制说明；「安装方式」标题「三套并存」→「四种并存」；SSOT 声明改为「集合维度真值源 = `agents/*.md` 文件名」 | agent-harness-architect |
| R1 | 2026-11-09 | Phase D 收口：§4 台账 + §4.1 批次明细、§5 基线表回填 R1 实测值、§8 失败模式库增至 8 条（新增 FM-R1-07/08）、§10 下轮入口 + 8 条未闭环清单；**§8 最终全量回归 12/12 全绿** | agent-harness-architect |
| R1 | 2026-11-09 | **GATE3 验收通过**：§5.1 落盘最终验收证据（12 套门禁逐条独立 rc + 4 组独立负向实锤，含 C13 空集合 fail-closed 与 `PHASES` 破坏实锤）；Phase D 收口完成，R1 全闭环 | agent-harness-architect |
