# 科研价值驱动研究编排团

> **团队名称**：科研价值驱动研究编排团 / Research Value-Driven Research Orchestration Team
> **专家类型**：Team 型（6 人协作团）
> **行业分类**：12-IndustryConsultant（跨学科咨询）
> **版本**：2.0.1
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
| 首席研究编排官（主理人）| 沈知枢（Shen Zhishu）| 全流程编排、状态机控制、最终汇编 |
| 苏格拉底追问者 | 问清源（Wen Qingyuan）| 5 轮×5 问澄清、信息完整度评估 |
| 元架构师 | 梁构局（Liang Gouju）| 问题分解、跨域节点、骨架设计 |
| 跨学科领域专家 | 博域闻（Bo Yuwen）| 跨学科知识调用、可行性核查、前沿扫描 |
| 方法学复评官 | 严复回（Yan Fuhui）| 证据等级审查、复评闭环决策 |
| 整合者 | 顾合璧（Gu Hebi）| 多源融合、冲突五级仲裁、综合汇编 |

## 核心工作流：八阶段状态机

```
FREEZE → IDENTIFY → COLLAPSE → CLARIFY → ALIGN → EXECUTE_ONE_STEP → REVIEW → NEXT
```

## 目录结构

```
research-orchestration-team/
├── .claude-plugin/
│   └── plugin.json          # Claude Code 标准 manifest
├── .codebuddy-plugin/
│   └── plugin.json          # WorkBuddy manifest（与上一份同步维护）
├── .github/
│   └── workflows/
│       └── validate.yml     # CI：双 manifest 校验 + 协议单测 + 一致性扫描
├── agents/
│   ├── research-orchestration-team-team-lead.md   # 主理人：沈知枢
│   ├── socratic-questioner.md                      # 团员1：问清源
│   ├── meta-architect.md                           # 团员2：梁构局
│   ├── domain-expert.md                            # 团员3：博域闻
│   ├── methodological-reviewer.md                  # 团员4：严复回
│   └── synthesis-integrator.md                     # 团员5：顾合璧（整合者）
├── skills/
│   └── research-orchestration-workflow/
│       ├── SKILL.md                                # 强制工作流模块
│       ├── references/
│       │   └── agent-protocol.md                   # 多代理通信协议 v2.0（9 节）
│       ├── scripts/
│       │   ├── topic_scoring.py                    # 选题评分卡生成器
│       │   ├── protocol_check.py                   # 协议合规单元测试
│       │   └── memory_log.py                       # 持久记忆自动写入
│       └── templates/
│           └── topic-scoring-card.md               # 选题评分卡模板
├── scripts/
│   └── manifest_check.py                            # 包一致性校验（双 manifest 对等 / 资产 / 版本 / 废弃表述）
├── avatars/                                         # 6 名成员头像 + 团队头像（随 git 分发）
├── docs/
│   ├── REDTEAM-REPORT.md                           # 红队审查报告（5 维度 · 缺陷 · 回归证据）
│   └── arbitration-L4L5-live-test.md               # 冲突仲裁 L4/L5 真实团队实测记录
├── settings.json                                    # 主理人 Agent ID 配置
├── .gitignore
├── README.md
├── CHANGELOG.md                                     # 版本变更历史
├── CONTRIBUTING.md                                  # 贡献流程与协议变更政策
└── LICENSE                                          # MIT
```

> **一致性约定**：`avatars/` 随 git 分发（不写入 `.gitignore`），以保证 `git clone` 与 Release tarball 两条安装路径产出的包完全一致。若将来改为仅随 Release 资产分发，必须同步修改本节结构树、下方三条安装说明与 `.gitignore`。

## 使用方式

1. 在 WorkBuddy 中加载本专家团
2. 主理人（沈知枢）会主动触发 FREEZE 协议评估信息完整度
3. 信息不足时调度问清源做 5 轮×5 问澄清
4. 信息充分时按 SOP 进入 ALIGN → EXECUTE → REVIEW
5. 严复回主导复评闭环，必给维持/升档/降档/止损四项决策之一

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

## 安装方式（三套并存）

### 方式 1 · Marketplace 一键添加（推荐）

适用于 **Claude Code** 与 **WorkBuddy**（两者共用同一 marketplace 协议）：

```bash
# Claude Code
/plugin marketplace add virologist/research-orchestration-team
/plugin install research-orchestration-team

# WorkBuddy（同一组命令）
/plugin marketplace add virologist/research-orchestration-team
/plugin install research-orchestration-team
```

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

下载 [v2.0.1 release](https://github.com/virologist/research-orchestration-team/releases/tag/v2.0.1) 的 `research-orchestration-team-2.0.1.tar.gz` → 解压 → 按方式 2 拷贝。

> tarball 内容与 `git clone` 一致（含 `avatars/`），已剔除编辑备份等本地产物。

### 方式 4 · 开发测试（`--plugin-dir`）

```bash
# Claude Code 本地开发模式
claude --plugin-dir ./research-orchestration-team
```

## 三种 agent 工具的兼容性

| 工具 | manifest | marketplace 命令 | 加载路径 |
|------|---------|-----------------|---------|
| **Claude Code** | `.claude-plugin/plugin.json` | `/plugin marketplace add` | `~/.claude/skills/` 或 `--plugin-dir` |
| **WorkBuddy** | `.codebuddy-plugin/plugin.json` | `/plugin marketplace add` | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/` |
| **Claude Desktop** | 通过 MCP bridge 包装 | 暂不支持 marketplace，需手动装 | 桥接方案尚未落地（计划 v2.1），当前请按方式 2 手动安装 |

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
