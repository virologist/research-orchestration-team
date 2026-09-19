# Changelog

所有重要变更按版本倒序记录。格式基于 [Keep a Changelog](https://keepachangelog.com/)。

## [2.1.1] - 2026-09-19

### Test（新增 selftest 工具）

> 协议与运行时行为**无变更**。仅新增 1 个 dev-only 验证脚本。已安装实例**无需重装**。

#### Added

- **`scripts/harness_eval_selftest.py`**：13 条注入式负例（N1-N12 + R1），对应 harness_eval.py 12 项 H1-H12 检查
  - **双断言**：每条断言 `rc=1`（反向用例 rc=0）+ 输出命中预期检查项文案
  - **覆盖**：删文件 / 替换关键字 / 替换近义词 / 子串加后缀
  - **首次跑暴露真实漏洞**：selftest v1 跑出 10/13 失败——因 mutate 字符串大小写敏感，漏过 `Per-step Verification`（首字母大写）。改用 `re.sub(..., flags=re.IGNORECASE)` 后 13/13 全过
  - **意义**：避免「harness_eval.py 自己假绿」（校验器永久返回 0）
  - **不接入 CI**：与 manifest_check_selftest.py 同策略（dev-only 工具）

#### Fixed

- **selftest 字符串稳定性假设**：mutate 关键字必须大小写无关（`re.IGNORECASE`）

### Regression evidence

| 套件 | v2.1.0 | v2.1.1 |
|------|--------|--------|
| `harness_eval.py` | 12/12 ✅ | 12/12 ✅ |
| `manifest_check.py` | 63/63 ✅ | 63/63 ✅ |
| `manifest_check_selftest.py` | 17/17 ✅ | 17/17 ✅ |
| **`harness_eval_selftest.py`** | ❌ 不存在 | **13/13 ✅**（新增）|
| `protocol_check.py` | 信封 12/12 + 仲裁 5/5 + 集成 8/8 ✅ | 同左 ✅ |
| `topic_scoring.py` 退出码契约 | rc=0/1/2 ✅ | 同左 ✅ |

---

## [2.1.0] - 2026-09-18

### Harness Engineering 升级（基于 2026-09 检索的 Anthropic / LangChain / Vercel 最佳实践）

> 协议与运行时行为**有变更**：主理人路由机制、Loop 硬停止、阶段边界 compact、跨会话连续性。已安装实例从 v2.0.x 升级需重启会话。

#### Added（新增）

- **`scripts/harness_eval.py`**：12 项 Harness Engineering 注入式正向校验（H1-H12）
- **`scripts/research-orchestration-workflow/references/agent-registry.md`**：单一事实源（SSOT），含 trigger / tools / safe/moderate/dangerous 三档权限分级
- **`scripts/research-orchestration-workflow/references/LEARNING.md`**：跨会话连续性（Anthropic Ralph Loop 模式），每次任务必追加 task 记录
- **`agents/domain-expert-biomed.md`**：生物医药 atomic（PubMed / GISAID / 兽医 / 分子生物学 / 流行病学 / 病原）
- **`agents/domain-expert-ai.md`**：AI atomic（大模型 / RAG / Agent / 生信 / 蛋白设计）
- **`agents/domain-expert-general.md`**：通用研究方法学 atomic（统计 / 教育 / 管理 / 政策）
- **`avatars/domain-expert-{biomed,ai,general}.png`**：3 个 atomic 头像（从原 domain-expert.png 派生）

#### Changed（变更）

- **`agents/research-orchestration-team-team-lead.md`**：v2.1.0 Harness Engineering 升级摘要
  - 新增 Loop 硬停止（三层上限：max_turns=30 / max_time=1800s / max_token=200000 / circuit_breaker=5 次失败熔断）
  - 新增 Token budget 跟踪 + 阶段边界 compact
  - 新增 plan_execution 元工具（Orchestrator Pattern 信号触发串行模式）
  - 新增 Per-step verification（每步走 verification，非仅 final-output）
  - 新增 Observability 4 metrics（成功率 / 平均 tool call / 重试次数 / next_actions 字段存在率）
  - 团队成员表更新：domain-expert 拆为 3 atomic
- **`skills/.../references/agent-protocol.md`**：§6 增补 Per-step verification 子节（root_cause_hint / safe_retry_instruction / explicit_stop_condition）
- **`skills/.../SKILL.md`**：模块 1 增补阶段边界 compact 表（8 个阶段边界 × 保留 / 抛弃字段）
- **`skills/.../SKILL.md`**：模块 2 + 边界条件提及 atomic subagent（替代原 domain-expert 单点引用）
- **`.codebuddy-plugin/plugin.json` + `.claude-plugin/plugin.json`**：版本 2.0.2 → 2.1.0；agents 字段 6 项 → 8 项（atomic 拆分）；description / keywords / members / displayDescription 全部同步更新
- **`README.md`**：版本号 2.0.2 → 2.1.0；团队人数 6 → 8

#### Removed（删除）

- **`agents/domain-expert.md`**：已被 3 个 atomic subagent（biomed / ai / general）取代
- **`avatars/domain-expert.png`**（不再被引用，但保留文件以防历史引用）
- **SKILL.md 模块 2 + 边界条件中的"domain-expert 单一引用"**：改为 atomic fan-out

### Fixed（修复）

- **Claude manifest skills 字段**：从数组 `["./skills/.../SKILL.md"]` 改为字符串 `"./skills"`（第一方约定，WorkBuddy 一致）
- **3 个 atomic MD 的 profession 字段与 manifest members[].profession 不一致**：统一为"Domain Expert · {X} (atomic)"格式
- **README 头部版本号 2.0.2 → 2.1.0 + 6 人 → 8 人**

### Regression evidence（回归证据）

| 套件 | v2.0.2 | v2.1.0 |
|------|--------|--------|
| `harness_eval.py` | 0/12 ❌ | **12/12 ✅** |
| `manifest_check.py` | 53/53 ✅ | **63/63 ✅**（新增 10 项因 3 atomic）|
| `manifest_check_selftest.py` | 17/17 ✅ | 17/17 ✅（未破坏）|
| `protocol_check.py` | 信封 12/12 + 仲裁 5/5 + 集成 8/8 ✅ | 同左 ✅ |
| `topic_scoring.py` 退出码契约 | rc=0/1/2 ✅ | 同左 ✅ |
| 双 manifest + 双 marketplace.json + GitHub Actions CI | ✅ | ✅ |

### Known issues（已知）

- harness_eval.py 暂无 selftest（v2.1.1 待补）
- 3 个 atomic subagent 共享原 domain-expert.png 头像（视觉上相同）；后续可用 icon 区分

---

## [Unreleased] - 2026-09-10

**docs patch**：仅文档变更，不发新 release。协议、运行时、CI 校验均无变化。

### Added

- README 新增「§5 · OneDrive 镜像同步」一节：明确三处真值源（canonical / GitHub 远端 / OneDrive 镜像）的角色分工、发布后同步契约、`git pull --ff-only` 步骤、健康检查 4 项必跑。

### Why

v2.0.1 → v2.0.2 期间 OneDrive 镜像未自动同步（落后一个版本），根因是发布流程没有明文契约。`docs/REDTEAM-REPORT.md` 把这列为「跨文件不一致」类风险的典型例子。此节固化该教训，避免下次重演。

## [2.0.2] - 2026-09-10

修复 v2.0.1 未覆盖的一个**用户可见功能缺陷**：README 把「Marketplace 一键添加」列为**推荐**安装方式，但该命令**实际会失败**。协议与运行时行为无变更。

### Fixed（修复）

| # | 级别 | 缺陷 | 根因 | 修复 |
|---|------|------|------|------|
| D19 | **P0** | README「方式 1 · Marketplace 一键添加（推荐）」**不工作**。仓库根既没有 `.claude-plugin/marketplace.json`，也没有 `.codebuddy-plugin/marketplace.json`；而 `/plugin marketplace add owner/repo` 要求前者必须存在于仓库根。三种安装方式里只有「git clone + 拷贝」与实际相符 | 打包时把仓库当作「单个插件仓库」处理，未意识到 marketplace 协议要求一份**市场清单**。平台侧之所以能正常安装，是因为本地市场 `my-experts` 自带 `.codebuddy-plugin/marketplace.json` 并以 `./plugins/research-orchestration-team` 指向本包 —— 这个本地清单掩盖了「GitHub 仓库本身缺文件」的事实 | 补入两份市场清单，用 **`"source": "./"` 让仓库自我托管**：仓库根同时作为市场根与插件根。**无需重构目录**，`git clone` 路径与 tarball 结构与 v2.0.1 完全一致，向后兼容 |
| D20 | P1 | 该缺陷此前**完全无自动化保护** | 既有校验项只覆盖 `plugin.json` 与资产完整性，没有覆盖「文档承诺的安装路径是否真的可用」 | `manifest_check.py` 新增 **C10**：两份市场清单存在且 JSON 合法、含 `name`/`owner`/`plugins`、收录本插件、`source` 可解析、两份市场名与插件列表一致 |

### Changed（变更）

- README 安装说明修正：市场名为 `tzuvet-experts`，安装命令为 `/plugin install research-orchestration-team@tzuvet-experts`；兼容性表补列 `marketplace.json` 并说明其必要性；结构树补入两份市场清单。
- 版本号 2.0.1 → 2.0.2，三方同步（两份 `plugin.json` + README 头部）。
- `manifest_check.py` 由 C1–C9（42 项）扩展为 **C1–C10（46 项）**。
- **新增 `scripts/manifest_check_selftest.py`（注入式负例套件，17 条）并接入 CI**：把此前只存在于一次会话中的负例固化为可复跑的资产。动机是「只测正向无法区分『校验器真的在检查』与『它永远返回 0』」——这正是本项目假绿的成因。用例同时断言**退出码**与**命中的检查项文案**，避免「碰巧因别的原因失败」也算通过。

### 回归证据

- `manifest_check.py` 正向：**46/46**（`rc=0`）
- `manifest_check_selftest.py` 负例（注入式，已入库）：**17/17** —— 在 v2.0.1 的 11 条之上新增 6 条市场清单负例（Claude 侧文件缺失 / WorkBuddy 侧文件缺失 / 未收录本插件 / source 无法解析 / 两份市场名不一致 / JSON 非法），并含 1 条**反向用例**（换用等价契约命名时应放行，`rc=0`）
- `protocol_check.py`：信封 12/12、冲突仲裁 5/5、集成仿真 8/8 检查点回引
- `topic_scoring.py` 退出码契约：正常 `rc=0` / 越界 `rc=1` / 缺维 `rc=2`

### 说明

v2.0.2 之后，本仓库既是「一个可被 `/plugin marketplace add` 添加的市场」，也是「该市场中唯一的插件」。这属于官方文档支持的写法（市场条目的 `source` 可用 `"./"` 指向市场根，使仓库自身成为插件源），因此**无需**把插件挪进 `plugins/<name>/` 子目录 —— 后者会让所有既有 `git clone` 用户与 tarball 使用者被迫改路径，收益不足以抵消破坏性。

## [2.0.1] - 2026-09-10

发布卫生补丁。**协议与运行时行为无变更**，全部为打包层 / 文档层修复，不影响已安装实例的编排逻辑，无需重装即可继续使用。

### Fixed（修复）

本轮分两阶段推进：**第一阶段**从零重扫三个分发位置（本地仓库 / GitHub 远端 / OneDrive 镜像）；**第二阶段**逐字段对照双 manifest，并拿 WorkBuddy **第一方内置插件的真实 manifest** 作为约定基准。共发现 18 项缺陷。

#### 第一阶段：分发位置重扫（D1–D8）

| # | 级别 | 缺陷 | 根因 | 修复 |
|---|------|------|------|------|
| D1 | **P0** | 7 个 `*.bak.*` 编辑备份被 git 跟踪**并已推送至远端 master**，随发布包外流 | `.gitignore` 的 `*.bak.*` 仅对「未跟踪文件」生效，对已入库文件无效——这些备份是在 ignore 规则生效之前提交的 | `git rm` 移出索引，文件移出工作树另存于 `my-experts/.backups/`（**未删除**）；`.gitignore` 补 `*.bak`、`*.bak-*`、`*.orig`、`*.rej` |
| D2 | P1 | `__pycache__/` 仅靠用户全局 `~/.config/git/ignore` 忽略 | 仓库级 `.gitignore` 缺该规则；换机器 clone 后 `*.pyc` 会显示为未跟踪文件，易被误提交 | 仓库 `.gitignore` 显式声明 `__pycache__/`、`*.py[cod]`、`.DS_Store`、编辑器目录、构建产物 |
| D3 | P1 | `avatars/` 被 `.gitignore` 排除，但 Release tarball 含头像、README 又将其标注为包内组件 → `git clone` 与 tarball **两条安装路径产出的包不一致** | 忽略规则、打包流程、文档三处各写各的，缺少一致性约束 | 决策为「头像随 git 分发」：从 `.gitignore` 移除 `avatars/` 与 `*.png`，8 个头像文件入库；README 增补一致性约定，禁止后续单侧改动 |
| D4 | P1 | README 引用 `docs/MCP-BRIDGE.md`，**该文件不存在** | 计划中的文档被当作已存在文档写成链接 | 移除悬空链接，改为「桥接方案尚未落地（计划 v2.1）」 |
| D5 | P2 | 仓库根的开发期产物（`.darwin-results.tsv`、`DARWIN-EVOLUTION-REPORT.html`、`EVOLUTION-V2.0-REPORT.md`）随包分发 | 演化过程产物直接落在仓库根，未归类 | 经确认无任何文档/代码引用后移出仓库，备份于 `my-experts/.backups/research-orchestration-team-dev-artifacts/` |
| D6 | P2 | 同一 tag 的 `v2.0.0` 指向含 `.bak` 的提交，Release 溯源不干净 | 同 D1 | 打 `v2.0.1` 补丁 tag 并重建 Release 与新 tarball；`v2.0.0` 保留为历史，**不重写标签** |
| D7 | P2 | README 目录结构树缺 `.claude-plugin/`、`.github/`、`docs/`、`LICENSE`/`CONTRIBUTING`/`CHANGELOG` | 结构树未随 v2.0.0 打包改动同步 | 重写结构树至与仓库实际一致 |
| D8 | P2 | `docs/arbitration-L4L5-live-test.md` 为孤儿文档，README 未索引 | 文档新增后未回填索引 | README 新增「文档索引（`docs/`）」表，纳入两份审计文档 |

#### 第二阶段：双 manifest 逐字段对照（D9–D18）

基准来自 WorkBuddy **第一方内置插件**的真实 manifest（`.codebuddy-plugin/plugin.json` 共 31 处为当前主流写法，`.workbuddy-plugin/` 8 处为早期写法），而非凭经验猜测字段语义。

| # | 级别 | 缺陷 | 根因 | 修复 |
|---|------|------|------|------|
| D9 | **P0** | `.codebuddy-plugin` 的 `displayDescription.zh` 仍写「与**三级**冲突仲裁」，与全局统一的「五级仲裁」**直接矛盾**，且该字段会展示给用户 | 上一轮红队修复只覆盖 `agents/*.md` 与协议文档，漏了 WorkBuddy manifest 的展示字段；同时 CI 术语清单写的是精确串「三级仲裁」，而实际文本是「三级**冲突**仲裁」，子串不匹配 → **假绿** | 改为「五级冲突仲裁」；术语规则改为宽松正则并迁入单一维护点 |
| D10 | P1 | WorkBuddy manifest 的 `author.email` 是占位符 `tzuvet@example.com`，与 Claude manifest 的 `yzuvet@outlook.com` 不一致 | 两份 manifest 分头编写时未对齐 | 统一为 `yzuvet@outlook.com`；新增占位邮箱 / URL 扫描规则 |
| D11 | P1 | WorkBuddy manifest 的 quickPrompt 写「**5-task** orchestration（identify / collapse / clarify / execute / **evolve**）」与「**五项核心任务**」，与 v2.0 的**八阶段状态机**及 SKILL.md 的**三大任务**均矛盾 | v1 遗留文案未随 v2.0 重构清除 | 改写为「选题评估（8 维评分 / S-A-B-C 分档 / 止损线）+ 深度调研编排」，并把旧表述加入扫描清单 |
| D12 | P1 | 两份 manifest 的 `skills` 写法互不一致，且**都偏离第一方约定**：本包写 `["./skills/…/SKILL.md"]`（文件）与 `["./skills/research-orchestration-workflow"]`（子目录），而第一方插件一律写字符串 `"./skills"` | 字段语义未对照第一方实现，属未验证的臆断 | 两份统一为 `"./skills"`；新增 C4 校验（必须为字符串且指向存在的目录） |
| D13 | P2 | WorkBuddy manifest 缺 `homepage` / `repository` / `license` / `keywords`（Claude manifest 有） | 分头编写 | 补齐，使共享字段完全对等，并由 C2 强制校验 |
| D14 | P2 | `.claude-plugin/plugin.json` 文件末尾缺换行符 | 手写 JSON | 补末尾换行 |
| D15 | P1 | **原 CI 存在两处有效性缺陷**：① 术语清单用精确串，漏检插入词（即 D9 得以漏网的原因）；② 「Validate expert package structure」步骤的 agents 存在性检查写死只遍历 `.codebuddy-plugin/plugin.json`，**Claude manifest 的引用从未被验证** | 测试只覆盖了「实现者当时想到的那一条路径」，与红队曾发现的 C1「负例期望从未断言」同类 | 删除重复的 bash 术语清单与重复的 JSON 校验步骤，统一由 `scripts/manifest_check.py` 承担；两份 manifest 的 agents 都被检查 |
| D16 | P2 | workflow 的 `paths` 触发器遗漏 `docs/**`、`README.md`、`avatars/**`、`CHANGELOG.md`（改这些文件不触发 CI），而 `scripts/**` 却指向当时并不存在的目录 | 触发器未随目录结构调整同步 | 补齐触发路径 —— `scripts/**` 此时才真正有意义 |
| D17 | P2 | `CONTRIBUTING.md` 的「提交前必跑」引用 `python3 /path/to/validate_expert.py .`，**该脚本不在仓库内**，贡献者照做必然失败 | 引用了 WorkBuddy 平台侧的内部工具，未替换为本仓库自带的自检脚本 | 替换为 `python3 scripts/manifest_check.py -v` |
| D18 | P2 | `CONTRIBUTING.md` 声称「每个 agent MD 顶部都有『v2.0 协议合规契约』5-7 条约束」——**与实际不符**：只有 4 个成员有该章节，整合者用「接口契约」、主理人用「Harness 运行时规范 v2.0」 | 文档描述未随 v2.0 新增整合者同步 | 如实改写为三分工对照表；并新增 **C9 校验**把「每个成员必须有契约章节」固化为不变式（此前这条链路由 `protocol_check.py` 完全未覆盖 —— 它只测协议逻辑，不读 agent MD） |

### Changed（变更）

- 版本号 2.0.0 → 2.0.1，三方同步：`.claude-plugin/plugin.json`、`.codebuddy-plugin/plugin.json`、README 头部。
- Release 资产命名统一为 `research-orchestration-team-2.0.1.tar.gz`（去除上一版的 `-clean` 后缀）；tarball 内容与 `git clone` 保持一致（含 `avatars/`，不含任何 `.bak` 与本地产物）。
- `.gitignore` 重写并补注释，明确「安装后运行所需文件必须提交」的原则与头像分发策略的切换方法。
- **新增 `scripts/manifest_check.py`**：C1 manifest 合法性 / C2 共享字段对等 / C3 agents 引用 / C4 skills 格式 / C5 头像资产 / C6 团队结构自洽 / C7 README 版本一致 / C8 废弃表述扫描 / C9 成员契约章节完整性，共九类校验（仅依赖标准库，正向 42 项检查）。
- **废弃术语清单收敛为单一事实来源**：只维护在 `manifest_check.py` 的 `FORBIDDEN_PATTERNS` 中，CI 不再另抄一份，避免再次出现「清单与实现漂移」。
- CI 从「结构校验 + 协议测试 + 评分边界 + bash 术语扫描」调整为「Package consistency check + 协议测试 + 评分边界」，术语扫描与结构校验合并进前者。

### 回归证据（v2.0.1 发布前实测）

- `protocol_check.py`：信封 **12/12** 通过、冲突仲裁 **5/5** 通过、集成仿真 **8/8** 检查点回引 —— 全绿
- `topic_scoring.py` 退出码契约：正常 `rc=0` / 越界 `rc=1` / 缺维 `rc=2` —— 符合
- 废弃术语一致性扫描：**0 命中**（**11 条正则**规则，含仲裁层级 / 状态机阶段数 / 团队规模 / 英文角色数 / 信封字段名 / FREEZE 量纲 / v1 任务模型 / 占位邮箱；审计文档按 `SCAN_EXEMPT` 豁免）
- 文档悬空链接扫描：**0 处缺失**
- `git check-ignore` 校验：忽略规则来源为本仓库 `.gitignore`（不再依赖全局配置），且未误伤 `settings.json`、`docs/`、双 manifest 等必需文件
- **`manifest_check.py` 正向**：**42 项全部通过**（`rc=0`）
- **`manifest_check.py` 负例（注入式）**：**11/11 通过** —— 校验器必须在被破坏时失败，逐项验证：版本漂移 / 术语回归 / 头像缺失 / README 版本漂移 / skills 路径失效 / leadAgent 错指 / agent 文件缺失 / 占位邮箱 / 契约章节被移除 / 契约章节被改名 / 另一标记可救回。每条负例均断言 `rc=1` **且** 命中预期检查项，而非仅看退出码（避免红队 C1「假绿」重演）
- **双 manifest 共享字段**（name / version / license / homepage / repository / agents / skills）：逐项一致
- **CI 编排**：YAML 语法校验通过；步骤为 Checkout → Setup Python → Package consistency check → Protocol compliance tests → Topic scoring edge cases

### 已知问题

- 无阻塞项。原「双 manifest 需人工同步」的风险已由 `manifest_check.py` 的 C2–C6 自动化拦截，不再依赖人工 review。

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