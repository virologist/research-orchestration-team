# Harness 迭代进化 · 状态文件（断点续跑单一事实源）
<!-- c8-exempt: audit-history -->
> 适用对象：科研价值驱动研究编排团（research-orchestration-team，Team 型 8 成员）
> 指令来源：《科研编排团·Harness迭代进化指令》（10 节，§0–§10）
> 用途：每轮会话执行一个「诊断 → 构建 → 测试&debug → 再诊断」闭环；下轮从本文件断点续跑。

## 1. 元信息

| 项 | 值 |
|---|---|
| 状态文件版本 | 1 |
| 当前轮次 | **R2（第二轮）· 已收口**（R1 见 §1.1 历史快照） |
| 创建时间 | 2026-11-08（GMT+8） |
| 指令标识 | sha256 前 16 位 `789e7c720094cbe0`（正文 4896 字符 / 10634 字节 / 70 行，含 §0–§10 全文；抽取件 `/tmp/rot-r1-instruction.md`） |
| 执行者 | R1 = `agent-harness-architect`（Agent Harness 专家团 P1 架构师角色）；R2 = `team-lead`（主理人直做） |
| 执行者裁决依据 | 指令 §0 指定「Agent Harness 架构设计师\|墨衡」，经全环境检索确认该专家不存在而冻结；管家节点 2026-11-08 裁决 **A**：改由 agent-harness-expert 的架构师角色执行，不虚拟身份 |
| 迭代对象基线 | R1 = v2.3.0；**R2 = v2.4.1**（`5a5aaa4`） |
| canonical HEAD | **`f6ed42e`**（docs(state): R2 Phase D 收口 — 状态文件落盘 + FM-R2-06 回流 LEARNING）；前序 `4d6e7e0`（fix(release): 打包前拦截资产内文档滞后） |
| tag | **v2.5.0 → `4d6e7e0`**（CI 绿 commit；发布于 2026-11-09T14:12:58Z，资产 `rot-v2.5.0.tar.gz` 14689986 B）。已发布 tag **不重写**——R2 Phase D 为纯文档落盘，走 patch commit，不影响资产内容 |
| 工作树 | **R2 全闭环（GATE3 已过）**：工作树干净（`git status --porcelain` 0 项）；canonical / origin / OneDrive 镜像 / GitHub API 四处 HEAD 全等 `f6ed42e`；CI run `42637122693` success（16 门禁 step 全执行全绿） |
| 意图漂移 | **R2 相对 R1 基线 = 0%**（静默通过，见 §3.1 复检） |
| R2 主题 | 覆盖矩阵盲区审计——「每一条门禁分支都要有一只『会红的测试』盯着」 |
| canonical 路径 | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/research-orchestration-team/` |
| 加载可见性 | `my-experts/plugins/` 下 **7 个专家包 + 1 个共享件**（`shared-core/` 为联邦共享真源，非独立专家包）：agent-harness-expert / research-orchestration-team / smart-textbook-team / smart-textbook-v2 / triz-invention-team / vet-med-ppt-team / viral-evo-lab；本包双 manifest + settings.json 均在位 |

### 1.1 R1 历史快照（只读留存，勿改）

| 项 | R1 值 |
|---|---|
| 轮次 | R1（首轮），2026-11-08 ~ 2026-11-09 |
| 迭代对象基线 | v2.3.0（`b521563`） |
| tag | v2.4.0 → `90a1c36`；v2.4.1 → `5a5aaa4`（发布介质自洽性补丁） |
| 工作树产出 | 12 文件已改 + 5 文件新建；脚本改动 8 文件 +1517 行 |
| GATE 状态 | GATE1 / GATE2 / GATE3 全部通过；§8 最终全量回归 12/12 全绿 |
| 失败模式 | FM-R1-01 ~ FM-R1-08（8 条，已回流包内 `LEARNING.md`） |
| 详见 | 本文件 §5.1（R1 验收证据）、§8（R1 失败模式库）、§10.2 第 1–8 项（R1 遗留清单） |

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

### 3.1 R2 漂移复检（相对 R1 基线）

| 维度 | R2 表述 | 偏离 |
|---|---|---|
| 使命 | 同 R1（诊断→构建→测试&debug→再诊断闭环，每轮一循环、结果落盘、下轮断点续跑） | 0% |
| 终态 | 同 R1（可复用于任意科研选题/深度调研/高价值决策/方法学复评场景的高质量专家团） | 0% |
| 硬边界 | 同 R1（永不产出科研正文；只产出团队自身的 agent/协议/skill/脚本/manifest/文档/测试） | 0% |
| 事实源 | 同 R1（§6 资产清单 + §5 验收基线表；已修复问题见 §7 黑名单） | 0% |
| 门控 | 同 R1（Phase A→GATE1→Phase B→GATE2→Phase C→Phase D→GATE3） | 0% |
| 验收 | 同 R1（全量回归全绿 + 独立负向实锤；失败保留现场快照） | 0% |

> **结论：0% 偏离，静默通过。** R2 的主题变化（覆盖矩阵盲区审计）属**手段层**收敛——使命、终态、硬边界、门控、验收五项均未变，不构成目标偏移。R2 是对 R1 产出做**再诊断**（把 R1 的产出当作待验证对象而非既成事实），与 §10.1 的下轮入口约定一致。

## 4. 四阶段进度台账

| 阶段 | 状态 | 起止 | 产出 | GATE |
|---|---|---|---|---|
| Phase A 只读诊断 | ✅ 已完成 | 2026-11-08 | 现状诊断报告 / 关键问题清单 P0-P2 / 升级设计（Mermaid 双图）→ 对话输出 | **GATE1 已通过**（管家节点放行「执行，直接进 Phase C」「仅本地改文件」） |
| Phase B 规划 | ✅ 已完成 | 2026-11-08 | 执行计划（分批：批次1 退出码真门禁 → 批次2 阶段名归一化 → 批次3 C8 声明式豁免 → 批次4 协议/文档/运行时三层 → 批次5 文档口径 + 成员 ID 一致性门禁） | **GATE2 已通过**（与 GATE1 合并放行） |
| Phase C 构建＋测试&debug | ✅ 已完成 | 2026-11-08 ~ 2026-11-09 | 8 批次全部落盘；脚本改动 8 文件 +1517 行、新建 5 文件；主理人对每批次做独立注入实锤验收 | 每批后报告（已出） |
| Phase D 再诊断＋状态落盘 | ✅ 已完成 | 2026-11-09 | 本文件更新（§4 台账 / §5 基线 / §8 失败模式库 / §10 下轮入口）+ GATE3 验收报告 | **GATE3 已通过**（§8 最终全量回归 12/12 全绿 + 3 组独立负向实锤 + 还原后 md5 逐字节一致） |

> 上表为 **R1** 台账。R2 台账见 §4.2。

### 4.2 R2 四阶段台账（2026-11-09）

| 阶段 | 状态 | 起止 | 产出 | GATE |
|---|---|---|---|---|
| Phase A 再诊断（只读） | ✅ 已完成 | 2026-11-09 | **覆盖矩阵盲区审计**：16 组真实破坏实验逐条验证三层门禁。实锤 **2 个 P0**（编排层上限语义失真 / 流水线幽灵成员无门禁）+ **4 个 P1**（protocol selftest N6/N10 纯重复 / C8 七条规则无负例 / fail-熔断零 CI 覆盖 / C13 三分支无负例）+ **1 个 P2**（跨市场 description 漂移）；排除 **4 个假阳性**（C8 豁免窗口边界 / C13 目录删除 / C11 三路径 / references 依赖） | ✅ 通过（主线直做，无需等裁决） |
| Phase B 规划 | ✅ 已完成 | 2026-11-09 | 修复计划（P0-1 语义分层锁定 → P0-2 真值源断言 → P1-1~P1-4 负例补全与 CI 补齐 → P2-1 description 纳管） | ✅ 通过 |
| Phase C 构建＋测试&debug | ✅ 已完成 | 2026-11-09 | 新增 `tests/test_state_ceilings.py`（4 用例）；`protocol_check.py` 集成段 +1 项断言（流水线 9→10）；protocol selftest 13→14 条；manifest selftest 26→30 条；CI 14→16 step；C2 `SHARED_FIELDS` 纳管 description（73→74 项）；全仓文档计数同步 | 每批后报告（已出） |
| Phase D 再诊断＋状态落盘 | ✅ 已完成 | 2026-11-09 | 本文件 §1/§3.1/§4.2/§5.2/§8（R2 失败模式）/§10（R3 入口）更新 | ✅ 通过 |
| **发布** | ✅ 已完成 | 2026-11-09 | v2.5.0（`4d6e7e0`）tag + release + 资产 `rot-v2.5.0.tar.gz`；三源同步；CI 16 step 全绿 | ✅ 通过 |

### 4.3 R2 修复批次明细（断点续跑用）

| 批次 | 范围 | 落点 | 状态 |
|---|---|---|---|
| R2-P0-1 | 编排层上限语义失真（advance 超限仍放行；CHANGELOG「代码化」易误读为截断） | `tests/test_state_ceilings.py`（新建，4 用例）+ `CHANGELOG.md` / `README.md` 措辞修正 | ✅ 已闭环 |
| R2-P0-2 | 流水线 producers/requires 幽灵成员 ID 无门禁 | `protocol_check.py` 集成段真值源断言（+1 项）+ `protocol_check_selftest.py` N11 | ✅ 已闭环 |
| R2-P1-1 | protocol selftest N6/N10 锚点重复（13 条里 1 条纯重复） | `protocol_check_selftest.py` N10 重构为 context_ref list 形态分支（13→14 条） | ✅ 已闭环 |
| R2-P1-2 | C8 十三条规则中 7 条无负例 | `manifest_check_selftest.py` N27 批量覆盖（26→30 条） | ✅ 已闭环 |
| R2-P1-3 | fail/熔断路径零 CI 覆盖（v2.4.0 核心特性裸奔） | `.github/workflows/validate.yml` +2 step（熔断段 + ceiling 语义锁定）（14→16 step） | ✅ 已闭环 |
| R2-P1-4 | C13 三分支无负例（声明位互换 / 重复 ID / 目录删除） | `manifest_check_selftest.py` N28 / N29 / N30 | ✅ 已闭环 |
| R2-P2-1 | 跨市场 description 漂移不可察觉（C2 只对等 7 字段） | 双 manifest 统一措辞 + `SHARED_FIELDS` 纳管 description（73→74 项） | ✅ 已闭环 |
| R2-发布侧 | 打包前拦截资产内文档滞后（FM-R1-01 第 3 次复发根治） | `README.md` 方式 3 改指 `releases/latest` + 发布契约 4 条强制检查 + CHANGELOG 段序归位 | ✅ 已闭环（v2.5.0 内） |
| R2-收尾 | `protocol_check.py` 的 `load_agent_ids` 弃用 `parents[3]` 硬索引（Linux tempfile 布局越界崩 CI） | `protocol_check.py`（commit `dcd174e`） | ✅ 已闭环 |

### 4.1 R1 Phase C 批次明细（只读留存，勿改）

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

### 5.2 R2 GATE3 最终验收证据（2026-11-09，v2.5.0 发布后复跑）

**逐条独立执行，每条单独取退出码**（沿用 FM-R1-07 纪律；长耗时门禁转后台并显式设超时）：

| # | 门禁 | rc | 实测计数 |
|---|---|---|---|
| 1 | `scripts/manifest_check.py` | 0 | **74/74**（C2 纳管 description，73→74） |
| 2 | `scripts/manifest_check_selftest.py` | 0 | **30/30**（新增 N27–N30） |
| 3 | `scripts/harness_eval.py` | 0 | 12/12 |
| 4 | `scripts/harness_eval_selftest.py` | 0 | 14/14 |
| 5 | `scripts/routing_eval.py` | 0 | 39/39（R1-R6） |
| 6 | `scripts/routing_eval_selftest.py` | 0 | 12/12 |
| 7 | `tests/test_vendor_core.py` | 0 | V1–V6 **6/6**（安装态 0 SKIP） |
| 8 | `scripts/test_phase_normalization.py` | 0 | 26/26 |
| 9 | `tests/test_state_ceilings.py`（R2 新增） | 0 | **4/4**（语义分层锁定） |
| 10 | `protocol_check.py envelope` | 0 | 37/37(v2.4) + 12/12(legacy) |
| 11 | `protocol_check.py conflict` | 0 | 5/5 |
| 12 | `protocol_check.py integration` | 0 | 阶段流水线 **10/10**（含真值源断言）+ HANDOFF 回引 8/8 |
| 13 | `protocol_check_selftest.py` | 0 | **14/14**（N10 重构 + N11 新增） |

> **13/13 套全绿**（R1 为 12 套，R2 因新增 `test_state_ceilings.py` 增至 13 套）。

**主理人独立负向实锤（6 组，不采信 CHANGELOG 自报；每次破坏后还原，md5 与基线逐字节一致）**：

| # | 破坏手法 | 期望 | 实测 |
|---|---|---|---|
| 负例 1 | `protocol_check.py` 的 `PIPELINE_STAGES` 注入幽灵成员 `GHOST-MEMBER` | integration rc=1 且精确列出幽灵 ID | ✅ rc=1；「❌ 流水线成员引用 ⊆ agents/*.md 真值源　幽灵成员 ID（不在 agents/*.md）: ['GHOST-MEMBER']」；还原后 rc=0、md5 `831814130baaa66d…` 一致 |
| 负例 2 | `.codebuddy-plugin/plugin.json` 的 `description` 改写为漂移文案 | C2 rc=1 且逐字段对照 | ✅ rc=1（73/74）；「❌ 字段不一致: description」+ 两侧全文并列；还原后 rc=0、工作树干净 |
| 负例 3 | `state_io.py` 熔断全链路（init → fail×3 → advance → finish） | 熔断终态 + advance 拒绝 + finish 不改写 | ✅ init 0、fail 0×3 → `status=aborted`/`abort_reason=circuit_breaker`；熔断后 advance **rc=1**（「拒绝推进：任务已熔断」）；finish rc=0 但 `status` 仍为 `aborted`（**不改写**） |
| 负例 4 | C13 三分支：①`members[].role` 声明位互换 ②协议表格单元格内重复 ID ③`agents/*.md` 全删 | 三分支各自 rc=1 | ✅ ①rc=1（2 项失败，精确报「leadAgent=…，members[].role=lead 声明的是 ['synthesis-integrator']」）；②rc=1（「C13 成员 ID 重复出现: 协议 §1 角色矩阵 … ['socratic-questioner']」）；③rc=1（33 项失败，「C13 真值源为空: agents/ 下没有任何 *.md 文件，空集合一律判红」）；三次还原后 rc=0、md5 逐字节一致、工作树干净 |
| 负例 5 | C8 规则注入未豁免文件（`LEARNING.md` 追加「六阶段…五项核心任务」） | C8 rc=1 且逐条命中 | ✅ rc=1；两条规则精确命中并带行号定位（「六阶段 → 旧状态机表述（现为八阶段）」/「五项核心任务 → v1 遗留任务模型」）；还原后 md5 `ba329b71cdd4f2dc…` 一致、rc=0 |
| 负例 6 | 「C13 声明位互换」负例首版构造（仅改 `agents[]` 数组顺序） | 期望 rc=1 | ❌ **rc=0 —— 首版负例无效**；C13 是**集合**一致性门禁（不比顺序），且 C2 `agents` 字段对等先抢先拦截。**修正**：改 `members[].role` 声明位（真声明位所在）后 rc=1 通过 |

> **负例 6 是本轮新增的失败模式（FM-R2-06）**：负例构造时把「声明位」误解为「`agents[]` 数组中的位置」，实际语义在 `members[].role == "lead"`。若只改数组顺序，C13 判绿（集合相同）且 C2 先抢先报红——**表面 rc=1 实则与 C13 无关**，属典型的「负例被无关门禁抢先拦截」（FM-R1-06 的变体）。结论：**负例必须对准被测分支的真实数据载体，且验证「失败原因归属」而非仅看 rc**。

**发布侧三源一致性验收（R2 收口）**：

| 检查 | 结果 |
|---|---|
| canonical HEAD | `4d6e7e0` |
| origin/master | `4d6e7e0`（一致） |
| OneDrive 镜像（`~/Library/CloudStorage/OneDrive-Personal/GPT/Claude/research-orchestration-team/`） | `4d6e7e0`（一致），工作树 `git status --porcelain` 0 项 |
| GitHub API release | tag `v2.5.0` → `4d6e7e0`，资产 `rot-v2.5.0.tar.gz`（14689986 B），发布于 2026-11-09T14:12:58Z |
| CI | v2.5.0 发布 run `42623476669` success（16 step 全执行）；v2.5.0 首推 run `42610641275` failure → 已由 `dcd174e`/`4d6e7e0` 修复，后续 run 全绿 |
| **R2 Phase D 落盘后**（本轮续跑补记） | canonical / origin / OneDrive 镜像三处 HEAD 全等 **`f6ed42e`**，两处工作树 0 项；CI run `42637122693` success（核到 step 级：Package consistency / Checker self-test / Protocol compliance / Protocol checker self-test / Phase normalization / Harness H1-H12 / Harness eval self-test / Routing R1-R6 / Routing eval self-test / Vendor V1-V6 / State IO lifecycle / State IO circuit breaker + ceiling / State IO ceiling semantics lock / Topic scoring 共 **14 个门禁 step 全执行全绿**）；tag `v2.5.0` 仍指向 `4d6e7e0`（**已发布 tag 不重写**，纯文档落盘走 patch commit，不影响资产内容） |

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
| FM-R2-01 | R2 | v2.4.0 发布 → tarball 内 README 仍写旧版指引 | 流程纪律违反（打 tag 时机） | 修正「方式 3」链接的 commit `2f2b016` 发生在打 tag `v2.4.0` **之后**（tag → `90a1c36`）；资产用 `git archive` 从 tag 打包，忠实复制了 tag 时刻的旧文档 → 介质内容与介质自身文档矛盾。被明确否决的「重打 v2.4.0 资产」路径会造成「资产内容 ≠ tag 内容」，比文档过期更严重 | ① 定位 tag 与修正 commit 的先后；② 不改历史 tag、不重打历史资产，改发 v2.4.1 补丁版；③ README 发布契约新增 4 条强制检查 | 🟡 中（用户按包内文档操作会指向旧版） | 文档类修正必须在**打 tag 之前**完成并进 CI 绿 commit；已发布则走补丁版；打包一律 `git archive <tag>`，打完必须解包核对 README 版本行与关键链接 | tarball / 资产内文档 / tag 时机 / git archive / 补丁版 |
| FM-R2-02 | R2 | 修正类 commit 单独走一轮「commit→push→CI→同步镜像」 | 流程纪律违反（把资产当独立事件） | 把「修正文档」和「发布资产」当成两个独立事件，忽略「**资产是 tag 的派生物**」这一约束。tag 之前的修正会进资产，tag 之后的修正不会 | ① 固化执行顺序链；② §10.3.1 补录发布纪律 | 🟡 中 | 执行顺序固定为 **修文档 → 升版 → commit → push → 等 CI 绿 → 打 tag → `git archive <tag>` 打包 → 解包核对 → 建 release → 上传 → 同步镜像** | 发布顺序 / 资产派生 / tag 隔断 |
| FM-R2-03 | R2 | v2.4.0 CHANGELOG 写「上限代码化」→ 实测 advance 超限仍 rc=0 放行 | 文档与实现脱节 | CHANGELOG 措辞从 `state_io.py` docstring 的语义分层表（告警 vs 终态）压缩成一句话时丢失关键限定。「代码化」被读成「真截断」，实际 turns/tokens 是**告警**语义，max_time/failures 才是**终态熔断** | ① 破坏实验实测（超限一次看 rc 与 status）；② 新增 `tests/test_state_ceilings.py` 4 用例锁定分层；③ CHANGELOG/README 措辞按实现口径修正 | 🟡 中（读者会按「硬上限」字面理解行为） | 写行为类 CHANGELOG 必须区分「检测到违规」（告警/记录）与「阻止继续」（拒绝/终态）；描述任何上限前先做破坏实验，禁止凭 docstring 转写 | 上限语义 / 代码化 / 告警 vs 终态 / 文档脱节 |
| FM-R2-04 | R2 | 16 组破坏实验 → 三类覆盖缺口（幽灵成员无门禁 / N6-N10 纯重复 / C8 七规则无负例） | 门禁覆盖缺口 | 负例设计按「校验器大项」（C13/H1/R1）配对，未下沉到「分支级」；跨文件引用类断言（流水线成员 vs `agents/*.md`）在两处独立演进时无人对齐。**每条负例必须对应一个「会独立失效的分支」** | ① 覆盖矩阵审计（列出全部断言分支 × 全部负例做差集）；② N10 重构为 list 形态分支；③ 新增真值源断言 + N11；④ N27 批量覆盖七规则；⑤ N28/N29/N30 覆盖 C13 三分支 | 🟡 中（重复负例给人虚假安心，真盲区裸奔） | 新增断言时同步回答「哪条负例会在该断言被破坏时变红？」——**答不出就不许合入**；定期跑覆盖矩阵差集；覆盖矩阵差集 >0 且涉及 rc 判定分支时必须补负例后才能发布 | 覆盖矩阵 / 负例配对 / 分支级 / 差集审计 / 幽灵成员 |
| FM-R2-05 | R2 | 补 N11 时注入在「单文件副本态」静默失效 | 工具失败（跨副本语义） | 新断言读 `agents/*.md` 真值源，副本里没有 `agents/` 目录 → 断言按设计 SKIP 放行 → 注入了破坏但 rc 仍 0（负例假绿）。同轮 CI 的 YAML heredoc 首版把 Python 代码顶格写进 `run: |` 块，YAML 解析直接崩 | ① N11 改整包副本（copytree 整个包再注入）强制走非 SKIP 路径；② heredoc 保持块缩进 + 本地 `yaml.safe_load` 验证 | 🟡 中（容错路径在负例场景下变成盲区） | 给校验器加 SKIP 分支时必须同步问「负例如何强制走非 SKIP 路径？」；负例跑完 rc 未翻转且输出含 SKIP 字样 → 该负例无效，禁止计为通过 | SKIP / 副本态 / 假绿 / yaml heredoc / 整包副本 |
| FM-R2-06 | R2 | Phase D 独立负向实锤 → C13 声明位互换负例首版 rc=0（无效负例） | 负例设计错误（误解被测分支的数据载体 + 无关门禁抢先拦截） | 构造负例时把 C13 的「声明位」误解为「`agents[]` 数组中的位置」，实际语义在 `members[].role == "lead"`。只改数组顺序 → C13 判绿（集合相同），且 C2 `agents` 字段对等**先抢先报红**——表面 rc=1 实则与 C13 无关。**两次构造均未翻转 rc**，才暴露问题 | ① 读 C13 实现定位真实数据载体（`members[].role`）；② 改声明位而非数组顺序 → rc=1 且精确报错；③ 还原后 md5 一致 | 🟡 中（若只看 rc=1 会误以为 C13 已被证明） | 负例必须对准被测分支的**真实数据载体**，且验收要看「**失败原因归属**」而非仅看 rc；被无关门禁抢先拦截的负例一律视为无效负例 | 负例无效 / 数据载体 / 失败原因归属 / 抢先拦截 / 声明位 |

> §9：下轮 Phase A 先与本库比对，匹配度 >70% 先输出历史摘要与预防建议。

## 9. 版本与发布契约（§5-13 登记）

- 改 agent 必同步两份 manifest（`version` + `agents` 清单）；CHANGELOG 与版本号同步。
- push 后 OneDrive 镜像 `git pull --ff-only` 并 `rev-parse` 核对两处 HEAD。
- **release 资产一律用 `git archive <tag>` 打包**（强制「资产内容 == tag 内容」），打完必须解包核对 README 版本行与关键链接，再上传。
- **已发布 tag 不重写、已发布资产不重打包**；资产内文档过期走补丁版。
- `validate_expert.py` 仅安装态原位运行；tempfile 副本环境性误报不计失败。
- 高危动作（`git push --force`、`rm -rf`、gh release、覆写共享资源）先警告并等管家节点确认。

## 10. 下轮入口（R3 起始状态）

### 10.1 下一轮起始阶段

- **R3 从 Phase A 开始**（只读诊断）。R1、R2 均已完成 Phase A→B→C→D 全程，R3 需先做**再诊断**，把 R2 的产出当作待验证对象而非既成事实。
- R3 的**意图漂移基线** = 本文件 §3 六维表述（R1 基线）+ §3.1 的 R2 复检结论（0% 偏离）；若 R3 指令与该基线偏离 >30% 暂停等裁决。
- R3 的**事实源** = 本文件 §6 资产清单 + §5 验收基线表（R1 实测列）+ §5.2（R2 实测列）。R1/R2 已修复的问题见 §7 黑名单与 §10.2 清单，**不得作为新发现重复上报**。
- R3 的**失败模式前置比对**：先与 §8 失败模式库（FM-R1-01 ~ FM-R1-08 + FM-R2-01 ~ FM-R2-06）比对，匹配度 >70% 先输出历史摘要与预防建议，再动手。
- **R3 的建议主题**：R2 已把「分支级负例覆盖」推到极致（14 条 protocol + 30 条 manifest + 4 条 ceiling + N27 批量覆盖）。下一轮的增量空间更可能在**断言之间的交互**（两条都通过的断言组合起来是否仍成立）与**运行时序**（并发/重入/中断恢复），而非单条分支。可优先审计的方向见 §10.5。

### 10.2 R1 未闭环问题（截至 R2 收口的状态）

| # | 问题 | 状态 | 后续动作 |
|---|---|---|---|
| 1 | 官方 `validate_expert.py` 本机不存在 | **环境性已知限制**（非缺陷） | R3 若宿主更新该工具，补装后跑安装态原位校验，接管 §5-8 的替代口径 |
| 2 | `assemble_spawn_prompt.py` shim 向上查找 `shared-core/` 的脆弱性 | **已闭环**（FM-R1-03 根治） | shim 已加「命中即校验 sha256 与 `VENDOR.json` 一致，不一致则拒绝加载」硬校验（`_expected_sha256()` + fail-closed 分支）；祖先目录存在旧版/被篡改同名文件不再会被静默加载 |
| 3 | `token_budget` 无硬截断 | **已闭环（语义确认）** | R2 审计确认这是**设计语义**而非缺陷：turns/tokens 触顶 = 告警（主理人语义裁量），max_time/failures = 终态熔断。`tests/test_state_ceilings.py` 4 用例已把该分层锁定，误改即红。CHANGELOG/README 措辞已修正（「代码化」→「语义分层」） |
| 4 | `protocol_check.py` 集成段的 `cp-001~cp-008` 检查点清单仍为硬编码 | **未闭环**（低优先，R2 复核仍在） | 当前与 `state_io.py` 的阶段序列已交叉比对（真断言），但 cp 清单本身未动态化；成员增删 cp 编号变动时需同步 |
| 5 | selftest 约 350s IO 耗时 | **未闭环**（低优先，R2 复核仍在） | 可用硬链接替代复制提速；R2 实测：`manifest_check_selftest` ~90s、`routing_eval_selftest` ~64s、`protocol_check_selftest` ~8s |
| 6 | `avatars/domain-expert.png` 不被任何 manifest 引用 | **已闭环 · 保留（既定决策）** | R2 复核发现：v2.1.0 CHANGELOG 已明确定策「保留（防历史引用）」，并非「待清理的孤儿文件」。R1 §10.2 曾误登记为待删除项，与既定决策冲突，R2 已改正。不再作为遗留项跟踪 |
| 7 | GitHub Release tarball 资产名不统一 + v2.2.0/v2.3.0 无 tarball 资产 | **已闭环** | README 方式 3 原链 `v2.2.0/research-orchestration-team-2.2.0.tar.gz` 实测 HTTP 404；R1 改文档，v2.4.0 发布侧补齐 `rot-v2.4.0.tar.gz`（14685476 B），**v2.4.1 补齐 `rot-v2.4.1.tar.gz`（14673511 B）**。v2.2.0/v2.3.0 的资产缺口作为历史缺口如实登记，不追溯补发 |
| 8 | README「安装方式」标题写「三套并存」但实际列 4 种方式 | **已闭环** | v2.0 时期引入就存在的表述错误（从引入 commit 起就错），R1 改为「四种并存」 |
| 9 | release 资产内容可能与 tag 内容脱钩（资产内 README 与自身文档矛盾） | **已闭环**（v2.4.1） | v2.4.0 的 tag 指向 `90a1c36`，早于修正「方式 3」链接的 commit `2f2b016` → 资产内 README 仍写旧版本指引。按发布纪律（tag 不重写、已发布资产不重打包）发 v2.4.1 补丁版；打包一律用 `git archive <tag>` 强制「资产内容 == tag 内容」 |
| 10 | 编排层上限语义失真（advance 超限仍放行，CHANGELOG「代码化」易误读为截断） | **已闭环**（v2.5.0 P0-1） | 真实语义 = 分层：turns/tokens 触顶告警（budget ⚠️）、max_time/failures 终态熔断。`tests/test_state_ceilings.py` 4 用例锁定；CHANGELOG/README 措辞修正 |
| 11 | 流水线 producers/requires 幽灵成员 ID 无门禁 | **已闭环**（v2.5.0 P0-2） | 集成段新增「流水线成员引用 ⊆ agents/*.md 真值源」断言（流水线 9→10 项）；protocol selftest N11（整包副本态注入 GHOST-MEMBER → rc=1）锁定 |
| 12 | protocol selftest N6/N10 锚点重复（13 条里 1 条纯重复） | **已闭环**（v2.5.0 P1-1） | N10 重构为破坏 context_ref list 形态逐条校验分支（V29/V33 失效证明生效），与 N6 互不重叠；13→14 条 |
| 13 | C8 七条规则无负例（Six-role/L1-L3/msg_type/量纲/五项核心任务/5-task 等） | **已闭环**（v2.5.0 P1-2） | N27 一条用例批量覆盖七条缺口规则，规则正则被误改立即红 |
| 14 | fail/熔断路径零 CI 覆盖（v2.4.0 核心特性裸奔） | **已闭环**（v2.5.0 P1-3） | CI 新增 State IO circuit breaker step（fail x5 → aborted → advance 拒绝 → finish 不改写）+ ceiling semantics lock step；14→16 step |
| 15 | C13 三分支无负例（声明位互换 / 重复 ID / 目录删除） | **已闭环**（v2.5.0 P1-4） | N28/N29/N30 分别锁定，26→30 条 |
| 16 | 跨市场 description 漂移不可察觉（C2 只对等 7 字段） | **已闭环**（v2.5.0 P2-1） | 实锤两份 description 已漂移（ACP 措辞 vs Harness 措辞）→ 统一措辞 + SHARED_FIELDS 纳管 description（73→74 项）；keywords/author 有意不纳管（理由在校验器注释） |
| 17 | v2.5.0 首推 CI run 失败（`load_agent_ids` 用 `parents[3]` 硬索引，Linux tempfile 布局越界） | **已闭环**（commit `dcd174e`） | 已改为按目录特征定位（找同时含 `agents/` 与 `.codebuddy-plugin/` 的祖先），修掉跨平台越界；后续 run 全绿 |
| 18 | README「安装方式 3」写死版本锚点（每次发版都要改 README 的复发点） | **已闭环**（v2.5.0 发布侧） | 统一指向 `releases/latest` 页面并去掉版本锚点；README 发布契约补 4 条强制检查（CI 绿才打 tag / `git archive <tag>` / 打包前查版本字面量 / 解包核对版本行） |

### 10.5 R3 建议审计方向（供下轮参考，非承诺）

| 方向 | 依据 | 备注 |
|---|---|---|
| 断言**交互**覆盖 | R2 已把单条分支覆盖做满（§5.2 13 套 + 6 组实锤）；两条都单独通过的断言，其组合是否仍成立未被验证 | 例：C13 集合一致 + C2 字段对等同时成立时，是否存在两侧都「合法」但语义冲突的状态 |
| 运行时序 / 并发 | R1 曾测 20 路并发写状态，但 R2 未复测；`state_io` 的断点续跑语义（resume）在异常中断后的恢复正确性未见负例 | v2.4.0 的 `state_io` 状态持久化特性至今没有「崩溃中断→resume」路径的负例 |
| 熔断与预算的**交互** | R2 的 `test_state_ceilings.py` 4 条用例彼此独立；「超 turns + 熔断 + resume」叠加态未验证 | 语义分层锁定后，组合态是下一个盲区 |
| 遗留 #4 cp 清单动态化 | 硬编码 `cp-001~cp-008` 与阶段序列交叉比对已在，但清单本身未动态化 | 低优先，成员增删时是同步风险点 |

### 10.6 R2 验收遗留（已全部闭环）

- **R2 未做升版**：R2 改动在 v2.5.0 发布前停留在工作树。 → **已闭环**：v2.5.0（`4d6e7e0`）已发布，tag + release 资产 `rot-v2.5.0.tar.gz`（14689986 B）+ 三源同步 + CI 16 step 全绿。
- **R2 状态文件未落盘**：R2 的 Phase D 未完成，状态文件 §1/§4/§5/§8/§10 仍停在 R1。 → **已闭环**：本轮（R2 收口续跑）已补齐 §1 元信息、§1.1 R1 快照、§3.1 漂移复检、§4.2 R2 台账、§4.3 R2 批次明细、§5.2 R2 验收证据、§8 FM-R2-01~06、§10.3.2、§10.5、§10.4 判据更新。
- **FM-R2-06 未回流包内 `LEARNING.md`**：R2 收口时新增的失败模式（负例数据载体误解）尚需登记。 → **待办**：本条已在 §8 登记，**包内 `LEARNING.md` 同步待 R3 随下一次升版一并完成**（`LEARNING.md` 当前含 FM-R1-01~08 + FM-R2-01~05）。

### 10.3 R1 验收遗留

- **R1 未做升版**：包 `version` 仍为 `2.3.0`，本轮改动全部停留在工作树（未 commit / 未 push / 未三源同步 / 未打 tag）。升版与发布属高危动作，需管家节点单独裁决。 → **已闭环**：管家节点已授权，v2.4.0（commit `90a1c36`）与 v2.4.1（commit `5a5aaa4`）均已发布，三源同步 + tag + release 资产全部落地。
- **CI step 名已改**：`Routing consistency check (R1-R5)` → `(R1-R6)`（R6 已在 v2.3.0 落地，step 名未同步）。**该改名会触发一次 CI 重跑**，需与首次 push 一并完成。 → **已闭环**：CI 已扩为 14 step，v2.4.0 / v2.4.1 两次发布 run 均 14 step 全执行全绿；R2 再扩至 16 step。
- **CHANGELOG 未写 v2.4.0 条目**：R1 的全部改动尚未进入 CHANGELOG。升版时需补，含批次 1–5 的变更摘要与回归证据表。 → **已闭环**：CHANGELOG 已含 v2.4.0 段（Added/Changed/Fixed/Regression evidence/Known limitations）+ v2.4.1 段。
- **§7 黑名单的 4 处引用式登记仍有效**，但新增的 8 条失败模式（FM-R1-01 ~ FM-R1-08）需在升版时同步进包内 `LEARNING.md`。 → **已闭环**：8 条失败模式已写入 `LEARNING.md`（含速查索引），C8 扫描零命中。

### 10.3.1 发布纪律补录（v2.4.1 新增）

- **tag 只打 CI 绿的 commit**，且**资产必须从该 tag 打包**（`git archive <tag>`），禁止从工作树或分支 HEAD 打包——否则会出现「资产内容 ≠ tag 内容」。
- **已发布 tag 不重写、已发布资产不重打包**：发现资产内文档过期时，走补丁版（v2.4.0 → v2.4.1），不原地修补。
- **文档修正必须先于打 tag**：凡会被打进资产的文档（README/CHANGELOG），必须在打 tag 之前完成修正并进 CI 绿 commit。
- **三源一致性的验收口径**：canonical / origin / mirror / GitHub API 四处 `rev-parse` 全部相等，且两处工作树 `git status --porcelain` 均为 0 项。

### 10.3.2 负例验收纪律补录（R2 收口新增，见 FM-R2-06）

- **负例必须对准被测分支的真实数据载体**：先读实现，确认「被破坏的那条规则」实际读的是哪个字段/集合/位置，再构造破坏。禁止凭字段名直觉构造。
- **rc 翻转是必要条件，不是充分条件**：rc 必须从 0 翻到 1（或反之），且**失败原因必须归属于被测门禁**。若失败信息来自另一条门禁抢先拦截，该负例一律作废重做（FM-R1-06 的变体）。
- **验收记录必须写清「被测分支 ← 破坏手法 ← 失败原因归属」三段对应关系**，供下一轮复核者独立判断该负例是否真有效。

### 10.4 收口判据进度

| 判据（§3「收敛终止」） | 状态 |
|---|---|
| 连续 2 轮再诊断无 P0/P1 新问题 | **0/2**（R2 再诊断**实锤 2 个 P0 + 4 个 P1 + 1 个 P2**，全部已修复并闭环；判据未达成——R2 是「发现问题并修复」的轮次，不是「无新问题」的轮次） |
| §8 全量回归全绿 | **R2 达成**（GATE3 实测 **13/13** 全部 rc=0，见 §5.2；R1 为 12/12） |
| 输出收口建议等管家节点裁决 | ✅ **R2 已闭环**：v2.5.0 已发布（tag `4d6e7e0` + release 资产 + 三源同步 + CI 16 step 全绿）；状态文件 Phase D 已落盘。**R3 的起步方向见 §10.1 与 §10.5** |

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
| R2 | 2026-11-09 | **覆盖矩阵盲区审计**：16 组真实破坏实验逐条验证三层门禁。实锤 2 个 P0（编排层上限语义失真：advance 超限仍放行 / 流水线幽灵成员无门禁）+ 4 个 P1（protocol selftest N6/N10 纯重复 / C8 七条规则无负例 / fail-熔断零 CI 覆盖 / C13 三分支无负例）+ 1 个 P2（跨市场 description 漂移实锤）；排除 4 个假阳性（C8 豁免窗口边界 / C13 目录删除 / C11 三路径 / references 依赖） | team-lead（R2 主理人直做） |
| R2 | 2026-11-09 | **v2.5.0 修复落盘**：语义分层锁定（新增 `tests/test_state_ceilings.py` 4 用例）+ 集成段真值源断言（流水线 9→10 项）+ protocol selftest 13→14 条（N10 重构消除重复 / N11 新增）+ manifest selftest 26→30 条（N27–N30）+ CI 14→16 step（熔断段 + 语义锁定）+ C2 纳管 description（73→74 项）+ 全仓文档计数同步 | team-lead（R2 主理人直做） |
| R2 | 2026-11-09 | **v2.5.0 发布**：commit `4d6e7e0` + tag `v2.5.0` + release 资产 `rot-v2.5.0.tar.gz`（14689986 B）+ 三源同步（canonical / origin / OneDrive 镜像全等 `4d6e7e0`）+ CI 16 step 全绿（run `42623476669`） | team-lead |
| R2 | 2026-11-09 | **Phase D 收口（本次续跑）**：§1 元信息更新至 R2 + §1.1 R1 历史快照 + §3.1 R2 漂移复检（0%）+ §4.2 R2 四阶段台账 + §4.3 R2 修复批次明细（9 批次）+ §5.2 R2 GATE3 验收证据（13/13 全绿 + 6 组独立负向实锤）+ §8 补 FM-R2-01~06 + §10 改 R3 入口 + §10.2 遗留项更新至 18 条 + §10.3.2 负例验收纪律补录 + §10.5 R3 建议审计方向 + §10.4 判据更新 | agent-harness-architect |
