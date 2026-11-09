# 科研价值驱动研究编排团

> **团队名称**：科研价值驱动研究编排团 / Research Value-Driven Research Orchestration Team
> **专家类型**：Team 型（8 人协作团 · v2.3.0 工具真实性门禁 R1-R6）
> **行业分类**：12-IndustryConsultant（跨学科咨询）
> **版本**：2.4.0
> **许可证**：MIT
> **仓库**：[github.com/virologist/research-orchestration-team](https://github.com/virologist/research-orchestration-team)

## 团队定位

跨学科研究规划与决策支持团队，融合**苏格拉底追问、元架构分解、跨学科知识、方法学复评**，专攻科研选题、深度调研、高价值决策支持与研究复评闭环。

**核心承诺**：
- 不伪造事实，不编造文献，不把推断包装成事实
- 不跳过必要调研，不在高风险任务上跳过澄清
- 不替用户做价值选择

## 团队成员

| 角色 | 名字 | 职责 |
|------|------|------|
| 首席研究编排官（主理人）| 沈知枢（Shen Zhishu）| 全流程编排、八阶段状态机、Orchestrator Pattern 路由、最终汇编 |
| 苏格拉底追问者 | 问清源（Wen Qingyuan）| 5 轮×5 问澄清、信息完整度四维评估、假设密度识别 |
| 元架构师 | 梁构局（Liang Gouju）| MECE 结构分解、跨域节点识别、路线图骨架设计 |
| 领域专家 · 生医（atomic）| 博域闻·生医 | PubMed/GISAID/兽医/分子生物学/流行病学检索与可行性核查 |
| 领域专家 · AI（atomic）| 博域闻·AI | 大模型/RAG/Agent/生信/蛋白设计检索与算力可行性核查 |
| 领域专家 · 通识（atomic）| 博域闻·通识 | 统计/教育/管理/政策/研究设计检索与方法学核查 |
| 方法学复评官 | 严复回（Yan Fuhui）| GRADE 证据等级审查、方法学合规、复评四项决策 |
| 整合者 | 顾合璧（Gu Hebi）| 多源融合、L1-L5 冲突仲裁、共识矩阵、综合汇编 |

> v2.1.0 起原单一 `domain-expert` 拆为 3 个 atomic subagent（biomed / ai / general），由主理人按领域标签 fan-out 调度。路由单一事实源见 `skills/research-orchestration-workflow/references/agent-registry.md`。

## 核心工作流：八阶段状态机

```
FREEZE → IDENTIFY → COLLAPSE → CLARIFY → ALIGN → EXECUTE → REVIEW → NEXT
```

## 目录结构

```
research-orchestration-team/
├── .claude-plugin/
│   ├── plugin.json          # Claude Code 插件清单
│   └── marketplace.json     # Claude Code 市场清单（本仓库自我托管）
├── .codebuddy-plugin/
│   ├── plugin.json          # WorkBuddy 插件清单（与上一份同步维护）
│   └── marketplace.json     # WorkBuddy 市场清单（与上一份同步维护）
├── .github/
│   └── workflows/
│       └── validate.yml     # CI：双 manifest 校验 + 协议单测 + 一致性扫描
├── agents/                                          # 8 名成员（主理人 1 + 团员 7）
│   ├── research-orchestration-team-team-lead.md   # 主理人：沈知枢
│   ├── socratic-questioner.md                      # 问清源（分析者）
│   ├── meta-architect.md                           # 梁构局（分析者）
│   ├── domain-expert-biomed.md                     # 博域闻·生医（atomic 执行者）
│   ├── domain-expert-ai.md                         # 博域闻·AI（atomic 执行者）
│   ├── domain-expert-general.md                    # 博域闻·通识（atomic 执行者）
│   ├── methodological-reviewer.md                  # 严复回（审查者）
│   └── synthesis-integrator.md                     # 顾合璧（整合者）
├── skills/
│   └── research-orchestration-workflow/
│       ├── SKILL.md                                # 强制工作流模块（选题/深度调研/复评闭环）
│       ├── references/
│       │   ├── agent-protocol.md                   # 多代理通信协议（9 节 + v2.2.0 状态落盘）
│       │   ├── agent-registry.md                   # 路由单一事实源（trigger/tools/权限三档）
│       │   └── LEARNING.md                         # Ralph Loop 跨会话记忆载体
│       ├── scripts/
│       │   ├── topic_scoring.py                    # 选题评分卡生成器
│       │   ├── protocol_check.py                   # 协议合规校验（三套 suite：信封 / 冲突仲裁 / 集成仿真）
│       │   ├── protocol_check_selftest.py          # 协议合规注入式负例自测 · 13 条
│       │   ├── memory_log.py                       # 持久记忆自动写入
│       │   └── state_io.py                         # 状态机持久化 · 六命令 init/advance/resume/budget/fail/finish（含预算与熔断语义）
│       └── templates/
│           ├── topic-scoring-card.md               # 选题评分卡模板
│           ├── cross-domain-combo.md               # 跨域组合编排模板 · biomed×ai / biomed×general / ai×general
│           └── result-envelope-v2.4.json           # result_envelope v2.4 空白信封模板
├── scripts/
│   ├── assemble_spawn_prompt.py                    # 成员人设注入装配器（联邦两级查找 shim）
│   ├── manifest_check.py                           # 包一致性校验 C1–C13（含成员 ID 一致性与 Team settings.json）
│   ├── manifest_check_selftest.py                  # 注入式负例自测（26 条）
│   ├── harness_eval.py                             # Harness Engineering H1–H12 设计检查
│   ├── harness_eval_selftest.py                    # harness 注入式负例自测（14 条）
│   ├── routing_eval.py                             # v2.2.0 路由结构一致性评估 R1–R6
│   ├── routing_eval_selftest.py                    # v2.2.0 路由注入式负例自测（12 条 · 含 raw_probe 未归一化护栏）
│   └── test_phase_normalization.py                 # 阶段名归一化自测 · 26 条
├── vendor/shared-core/                              # 联邦共享件兜底副本 + VENDOR.json 清单
├── tests/
│   └── test_vendor_core.py                         # 防漂移门禁 V1–V6
├── avatars/                                         # 8 名成员头像 + 团队头像（随 git 分发）
├── docs/
│   ├── REDTEAM-REPORT.md                           # 红队审查报告（5 维度 · 缺陷 · 回归证据）
│   ├── arbitration-L4L5-live-test.md               # 冲突仲裁 L4/L5 真实团队实测记录
│   ├── harness-eval-report-v2.0.2.md               # Harness 改造前基线（0/12）
│   └── harness-iteration-loop.md                   # Harness 迭代闭环状态文件 · 断点续跑 SSOT
├── .gitignore
├── README.md
├── CHANGELOG.md                                     # 版本变更历史
├── CONTRIBUTING.md                                  # 贡献流程与协议变更政策
├── settings.json                                    # Team 型包根必需（agent 指向主理人）
├── test-prompts.json
└── LICENSE                                          # MIT
```

> **一致性约定**：`avatars/` 随 git 分发（不写入 `.gitignore`），以保证 `git clone` 与 Release tarball 两条安装路径产出的包完全一致。若将来改为仅随 Release 资产分发，必须同步修改本节结构树、下方三条安装说明与 `.gitignore`。

## 使用方式

1. 在 WorkBuddy 中加载本专家团
2. 主理人（沈知枢）会主动触发 FREEZE 协议评估信息完整度
3. 信息不足时调度问清源做 5 轮×5 问澄清
4. 信息充分时按 SOP 进入 ALIGN → EXECUTE → REVIEW
5. 严复回主导复评闭环，必给维持/升档/降档/止损四项决策之一

## 门禁体系现状

本包的门禁分三层：**正向校验器**（干净仓库应全绿）、**注入式负例自测**（证明校验器不是永远返回 0）、**联邦防漂移门禁**（防 vendor 副本被静默改写）。

### 第一层 · 正向校验器（4 套）

| 校验器 | 检查项 | 防什么 |
|--------|--------|--------|
| `scripts/manifest_check.py` | **C1–C13** | 双 manifest 对等 / 资产完整性 / 版本一致 / 废弃表述扫描 / 契约章节 / frontmatter 结构 / 成员 ID 五处一致性 / Team settings.json |
| `scripts/harness_eval.py` | **H1–H12** | Harness Engineering 12 项设计模式（路由单一事实源、Loop 硬停止、per-step verification、失败熔断等）退化 |
| `scripts/routing_eval.py` | **R1–R6** | 路由结构一致性：成员集合 / 触发词 / 条目结构 / 工具名形态 / 工具集合双向相等 / 真实 MCP 清单对照（R6 需真实 MCP 清单，CI/git-clone 态显式 SKIP 且不计 FAIL） |
| `skills/research-orchestration-workflow/scripts/protocol_check.py` | **三个 suite** | 协议合规：信封 **37** / 冲突仲裁 **5** / 集成仿真 **9** |

### 第二层 · 注入式负例自测（4 套）+ 阶段名归一化自测（1 套）

| 自测脚本 | 用例数 | 证明什么 |
|----------|--------|----------|
| `scripts/manifest_check_selftest.py` | **26** 条 | manifest / 资产 / 版本 / 术语 / 市场清单 / settings.json / 成员 ID 各类破坏都能被检出 |
| `scripts/harness_eval_selftest.py` | **14** 条 | H1–H12 每项设计检查被破坏时都能被检出 |
| `scripts/routing_eval_selftest.py` | **12** 条 | R1–R6 各类路由破坏都能被检出（含 raw_probe 未归一化护栏，该护栏为准备阶段防自愈夹具掩盖真实缺陷，不计入用例数） |
| `skills/research-orchestration-workflow/scripts/protocol_check_selftest.py` | **13** 条 | 协议三个 suite 的退出码链路与判定分支都真实有效 |
| `scripts/test_phase_normalization.py` | **26** 条 | 阶段名归一化 shim 的映射与透传行为正确 |

### 第三层 · 联邦防漂移门禁（1 套）

| 门禁 | 检查项 | 防什么 |
|------|--------|--------|
| `tests/test_vendor_core.py` | **V1–V6** | 比对 `vendor/shared-core/` 与联邦真源的 sha256 清单，防 vendor 副本被静默漂移；联邦真源缺失时显式 SKIP 且不计 FAIL |

### 为什么必须有注入式负例

只测正向（干净仓库 rc=0）无法区分「真的在检查」与「永远返回 0」——**这正是本项目历史上假绿的成因**：CI 的术语清单曾写成精确串，真实存在的违规因插入词而漏检，校验器照样返回 0。

每条负例的做法是：把仓库复制到临时目录 → 注入一处破坏 → 断言校验器 **rc=1** 且输出命中**预期的检查项文案**。第二个断言不可省略：只断言退出码会让「任何错误都算通过」，检查项本身失效也会被误判为通过。

### 负例设计的两条硬纪律

这两条是本项目反复踩坑换来的，任何新增负例都必须遵守：

1. **锚点唯一命中 + 替换后落盘校验**：注入前断言目标锚点在文件中只出现一次，注入后断言旧串消失、新串出现。否则锚点没命中会静默空转，测试仍然绿——假绿。
2. **一条负例只承载一个失败维度**：反例若自带无关的失败原因，那么无论被破坏的规则是否生效都会判「检出」——假绿。例如覆盖类校验必须让「覆盖完整」与「形态非法」两个维度正交。

## 适用场景

- 🎯 **科研选题规划**：硕博选题、跨学科方向探索、基金前期认知搭建
- 📚 **深度调研编排**：综述前情报图谱、文献策略、跨域融合方案
- ⚖️ **高价值决策**：投稿选刊、基金分档、风险/收益权衡
- 🔄 **方法学复评**：研究卡点诊断、证据等级审查、复评闭环

## 注意事项

- 团队创建必须且只能由主理人执行
- 所有成员调度必须经过"建立团队 → 调度成员 → 成员回传"流程
- 成员结论为准，主理人只做编排与汇编
- 必给分档 + 必给止损线 + 必给复评决策，禁止"待定/观察"

## 版本历史

- **v1.0.0** (2026-08-28)：初始版本，5 人团队 + 选题评分卡 Skill
- **v2.0.0** (2026-09-10)：六人团队（新增整合者顾合璧）+ 八阶段状态机 + ACP 通信协议（9 节）+ 冲突五级仲裁 + harness 12 组件运行时
- **v2.0.1** (2026-09-10)：发布卫生修复（清理误提交的编辑备份、加固 `.gitignore`、头像纳入 git 分发以统一 clone/tarball 产物、修复文档悬空链接与结构树）。协议与运行时**行为无变更**，属纯打包层补丁。
- **v2.0.2** (2026-09-10)：修复**一键安装失效**——补入缺失的市场清单 `marketplace.json`（两份），使 `/plugin marketplace add` 真正可用；`scripts/manifest_check.py` 增至 C1–C10（46 项）。协议与运行时**行为无变更**。
- **v2.1.0** (2026-09-18)：Harness Engineering 升级——`domain-expert` 拆为 3 个 atomic subagent；新增 `agent-registry.md` 路由单一事实源、safe/moderate/dangerous 权限三档、Loop 硬停止、per-step verification、阶段边界 compact、4 项 observability metrics、LEARNING.md 跨会话记忆、harness_eval H1–H12。
- **v2.1.1** (2026-09-19)：新增 `harness_eval_selftest.py`（dev-only 负例工具），运行时行为无变更。
- **v2.1.2** (2026-09-30)：atomic 拆分残留补全（4 处死引用、六/八阶段表述、maxTurns 消歧义）；协议统一为 result_envelope v2.4；CI 纳入 harness 校验。回归 12/12 + 63/63 + 17/17 + 13/13。
- **v2.2.0** (2026-11-07)：从零独立诊断后的补全完善版。恢复包根 `settings.json`（官方校验 0 error）+ manifest C12 护栏；新增 `state_io.py` 状态持久化与断点续跑（治协议 §3 纸面 schema）；harness_eval 根定位修复；routing_eval 结构一致性评估；README/CHANGELOG/LEARNING 历史欠账补齐。两轮独立交叉验证后修复 3 个门禁假绿（R3/H6 权限档章节漏检、routing selftest 自愈夹具掩盖真实缺陷）与 1 个方向性错误（protocol_check 校验废弃 ACP v2.0），并补齐文档计数与两份 marketplace.json 的八agent 描述。详见 [CHANGELOG.md](./CHANGELOG.md)。
- **v2.3.0** (2026-11-08)：残留风险工程化收口。routing_eval 升至 **R1-R6 共 39 项**——R5 工具集合一致性扩展到全部 8 个成员（分级解析：atomic 四类 + 双向相等；非 atomic 零工具授权，①②③ 类 token 即 FAIL，跳过对中文叙述误报率高的 ④ `+` 槽位分支）；新增 **R6 工具真实性校验**（对照真实 MCP 清单硬校验 registry 全部 `mcp__` 名，清单不可得的 CI/git-clone 态显式 SKIP 且不计 FAIL）；selftest 增至 12 例（N10 非 atomic 注入 / N12 伪造 server 名 + 真实清单 fixture）。官方 `validate_expert.py` 的安装路径限制已在本文档化。详见 [CHANGELOG.md](./CHANGELOG.md)。
- **v2.4.0** (2026-11-09)：Harness 迭代进化 R1 首轮全闭环。四阶段硬门控走完一轮，门禁体系从一层升为**三层**（正向校验器 / 注入式负例自测 5 套 91 条 / 联邦防漂移）：manifest 升至 **C1–C13**（新增 C13 成员 ID 集合一致性，以 `agents/*.md` 文件名为机器真值源逐处比对 8 个目标）、protocol 主套件 16 → **37**、新增 `protocol_check_selftest.py`（13 条）与 `test_phase_normalization.py`（26 条）；`state_io.py` 状态机代码化（按序推进 / 熔断 / 预算 / metrics / `fail` 子命令）；C8 豁免机制声明化；shim 命中 core 加 sha256 硬校验。新建 `docs/harness-iteration-loop.md` 作为迭代断点续跑的单一事实源。回归 **12 套门禁全绿** + 4 组独立负向实锤。详见 [CHANGELOG.md](./CHANGELOG.md)。

## 安装方式（四种并存）

### 方式 1 · Marketplace 一键添加（推荐）

本仓库**自我托管为一个市场**：仓库根同时是市场根（`.claude-plugin/marketplace.json` / `.codebuddy-plugin/marketplace.json`）
与插件根（`plugin.json`），市场条目用 `"source": "./"` 指回仓库自身。

适用于 **Claude Code** 与 **WorkBuddy**（两者共用同一套 marketplace 协议）：

```bash
# Claude Code 与 WorkBuddy 命令相同
/plugin marketplace add virologist/research-orchestration-team
/plugin install research-orchestration-team@tzuvet-experts
```

> 市场名为 `tzuvet-experts`（定义在市场清单的 `name` 字段），因此安装命令须写成
> `<插件名>@<市场名>`。若省略 `@tzuvet-experts`，在只注册了一个市场的环境下通常也能解析。

### 方式 2 · 手动 git clone + 拷贝

```bash
# 克隆仓库
git clone https://github.com/virologist/research-orchestration-team.git

# WorkBuddy 用户级加载路径
cp -r research-orchestration-team ~/.workbuddy/plugins/marketplaces/my-experts/plugins/

# Claude Code 用户级 skills 路径
mkdir -p ~/.claude/skills
cp -r research-orchestration-team ~/.claude/skills/research-orchestration-team
```

### 方式 3 · GitHub Release tarball

下载 [v2.4.0 release](https://github.com/virologist/research-orchestration-team/releases/tag/v2.4.0) 的 `rot-v2.4.0.tar.gz` → 解压 → 按方式 2 拷贝。

> tarball 内容与 `git clone` 一致（含 `avatars/` 与包根 `settings.json`），已剔除编辑备份等本地产物。
> **注意资产名不统一**：各 release 的资产命名不完全遵循 `research-orchestration-team-<版本>.tar.gz` 约定（v2.1.2 与 v2.4.0 均为 `rot-<版本>.tar.gz`），下载前请先在 release 页面确认实际资产名。
> **历史缺口**：v2.2.0 与 v2.3.0 两个 release 未附带 tarball 资产；**自 v2.4.0 起已补齐 `rot-v2.4.0.tar.gz`**，方式 3 现在可直接安装到最新版。

### 方式 4 · 开发测试（`--plugin-dir`）

```bash
# Claude Code 本地开发模式
claude --plugin-dir ./research-orchestration-team
```

## 三种 agent 工具的兼容性

| 工具 | 清单文件 | marketplace 命令 | 加载路径 |
|------|---------|-----------------|---------|
| **Claude Code** | `.claude-plugin/plugin.json` + `marketplace.json` | `/plugin marketplace add` | `~/.claude/skills/` 或 `--plugin-dir` |
| **WorkBuddy** | `.codebuddy-plugin/plugin.json` + `marketplace.json` | `/plugin marketplace add` | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/` |
| **Claude Desktop** | 通过 MCP bridge 包装 | 暂不支持 marketplace，需手动装 | 桥接方案尚未落地（计划 v2.1），当前请按方式 2 手动安装 |

> **为什么需要 `marketplace.json`**：`/plugin marketplace add owner/repo` 要求仓库根存在
> `.claude-plugin/marketplace.json`。仅有 `plugin.json` 的裸插件仓库无法通过该命令添加
> —— v2.0.1 及更早版本的 README 曾把「一键添加」写成推荐方式，但实际会失败，v2.0.2 已修复。

> 本仓库双 manifest 共存：`.claude-plugin/` 与 `.codebuddy-plugin/` 指向同一组组件。两份元数据保持同步（每次改 agent 必须 review 两份 manifest）。

## 引用本包

```bibtex
@misc{research_orchestration_team_2026,
  author = {TZUVet},
  title = {Research Value-Driven Research Orchestration Team},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/virologist/research-orchestration-team}
}
```

## 反馈与贡献

- Issues: https://github.com/virologist/research-orchestration-team/issues
- 详细贡献流程见 [CONTRIBUTING.md](./CONTRIBUTING.md)
- 版本变更历史见 [CHANGELOG.md](./CHANGELOG.md)

### 文档索引（`docs/`）

| 文档 | 内容 |
|------|------|
| [docs/REDTEAM-REPORT.md](./docs/REDTEAM-REPORT.md) | 红队审查报告：5 维度诊断、缺陷清单与根因、修复方案、回归证据 |
| [docs/arbitration-L4L5-live-test.md](./docs/arbitration-L4L5-live-test.md) | 冲突仲裁协议 §7 第 4/5 层（升级主理人 / 用户裁决）的真实团队实测记录 |
| [docs/harness-eval-report-v2.0.2.md](./docs/harness-eval-report-v2.0.2.md) | Harness 改造前基线快照：v2.0.2 在 12 项设计模式上 0/12 符合 |
| [docs/harness-iteration-loop.md](./docs/harness-iteration-loop.md) | Harness 迭代进化状态文件：每轮「诊断 → 构建 → 测试&debug → 再诊断」闭环的断点续跑单一事实源 |

## §5 · OneDrive 镜像同步（云备份契约）

仓库存在三处真值源：

| 位置 | 角色 | 路径 |
|------|------|------|
| **canonical** | 编辑、CI 校验、WorkBuddy 实际加载 | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/research-orchestration-team/` |
| **GitHub 远端** | 公开/私有仓库 | `virologist/research-orchestration-team`（PRIVATE） |
| **OneDrive 镜像** | 只读云备份，跨设备可用 | `~/Library/CloudStorage/OneDrive-Personal/GPT/Claude/research-orchestration-team/` |

**发布契约**：每次 push 到 GitHub 之后，必须把 OneDrive 镜像 fast-forward 到同一 commit。**v2.0.1 → v2.0.2 期间发生过漏同步**，原因是没有明文契约——本节即是修补。

```bash
# 1. 在 canonical 仓库推送
cd ~/.workbuddy/plugins/marketplaces/my-experts/plugins/research-orchestration-team
git push origin master
gh release create vX.Y.Z --repo virologist/research-orchestration-team \
  --title "..." --notes-file /tmp/release-notes.md /tmp/release-X.Y.Z.tar.gz

# 2. 同步 OneDrive（**必做**，否则云镜像会落后）
cd ~/Library/CloudStorage/OneDrive-Personal/GPT/Claude/research-orchestration-team
git pull --ff-only
git rev-parse HEAD    # 确认与 remote master 一致

# 3. 健康检查（本地跑全部校验脚本 + 官方校验器）
cd ~/.workbuddy/plugins/marketplaces/my-experts/plugins/research-orchestration-team
python3 scripts/manifest_check.py                 # C1–C13，含成员 ID 一致性与 Team settings.json
python3 scripts/manifest_check_selftest.py        # 注入式负例
python3 scripts/harness_eval.py                   # H1–H12（根定位已改为 __file__，任意目录可调）
python3 scripts/harness_eval_selftest.py          # harness 注入式负例
python3 scripts/routing_eval.py                   # 路由结构一致性 R1-R6（R6 需真实 MCP 清单，CI 态显式 SKIP）
python3 scripts/routing_eval_selftest.py          # 路由注入式负例自测
python3 tests/test_vendor_core.py                 # 联邦防漂移 V1–V6
python3 skills/research-orchestration-workflow/scripts/protocol_check.py envelope    # v2.4 主套件 37 + legacy 12
python3 skills/research-orchestration-workflow/scripts/protocol_check.py conflict    # 冲突仲裁 5/5
python3 skills/research-orchestration-workflow/scripts/protocol_check.py integration # 集成仿真 9/9
python3 skills/research-orchestration-workflow/scripts/protocol_check_selftest.py    # 协议注入式负例自测 13 条
python3 scripts/test_phase_normalization.py                                          # 阶段名归一化自测 26 条
python3 skills/research-orchestration-workflow/scripts/state_io.py resume --help     # 状态持久化工具存在性自检
python3 skills/research-orchestration-workflow/scripts/topic_scoring.py --topic probe \
  --originality 8 --feasibility 7 --value-density 9 --data-availability 7 \
  --competition 6 --cognition 8 --resource-fit 7 --sustainability 7
python3 /Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts/validate_expert.py .   # 官方校验：0 error
```

> **validate_expert.py 的已知限制**：该校验器内部硬编码要求包位于 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/` 之下——对 tempfile 副本运行必报「专家不在专家目录下」（环境性误报），且 CI checkout 目录天然不满足安装路径，故这一项**只能安装态原位运行、无法纳入 CI**。上例 `cd` 到安装路径后原位执行即为正确用法。

> **为何不自动化**：OneDrive 是只读云备份，不是 critical path。手写契约比 launchd cron / WebDAV 推送简单可靠，且无凭据泄漏面。若未来团队规模扩大、需要 ≤1 天同步窗口，再考虑 GitHub Action + WebDAV（成本：OAuth + secret 配置）。

> **冲突处理**：OneDrive 路径永远只 `git pull --ff-only`，**禁止**在 OneDrive 路径做 commit 或 push。如果发现分歧（本地有未推送 commit 或 OneDrive 有本地没有的 commit），立即停下来排查，不要盲覆盖。
