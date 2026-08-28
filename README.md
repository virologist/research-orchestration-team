# 科研价值驱动研究编排团

> **团队名称**：科研价值驱动研究编排团 / Research Value-Driven Research Orchestration Team
> **专家类型**：Team 型（5 人协作团）
> **行业分类**：12-IndustryConsultant（跨学科咨询）
> **版本**：1.0.0

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

## 核心工作流：六阶段状态机

```
FREEZE → IDENTIFY → COLLAPSE → CLARIFY → ALIGN → EXECUTE_ONE_STEP → REVIEW → NEXT
```

## 目录结构

```
research-orchestration-team/
├── .codebuddy-plugin/
│   └── plugin.json          # 团队元数据 + 成员清单
├── agents/
│   ├── research-orchestration-team-team-lead.md   # 主理人
│   ├── socratic-questioner.md                      # 团员1：问清源
│   ├── meta-architect.md                           # 团员2：梁构局
│   ├── domain-expert.md                            # 团员3：博域闻
│   └── methodological-reviewer.md                  # 团员4：严复回
├── skills/
│   └── research-orchestration-workflow/
│       ├── SKILL.md                                # 强制工作流模块
│       ├── scripts/
│       │   └── topic_scoring.py                    # 选题评分卡生成器
│       ├── references/
│       └── templates/
│           └── topic-scoring-card.md               # 选题评分卡模板
├── avatars/                                         # 头像（待生成）
├── settings.json                                    # 主理人 Agent ID 配置
└── README.md
```

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
