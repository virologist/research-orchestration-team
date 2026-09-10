# Contributing to Research Orchestration Team

> 感谢你愿意参与贡献。本专家包是研究规划与决策支持的协作工具集，质量门槛 = 学术严谨。

## 行为准则

- **事实洁癖**：不伪造文献、不编造证据等级、不把推断包装成事实
- **尊重角色边界**：每个 agent 有严格的能力范围（见 `.claude-plugin/plugin.json` 与 `skills/research-orchestration-workflow/references/agent-protocol.md` §1）
- **诚实标注不确定性**：单一来源、证据冲突、未核实内容须 ⚠️ 标注

## 提交前必跑（强制 CI）

```bash
# 1. 协议合规单元测试
python3 skills/research-orchestration-workflow/scripts/protocol_check.py

# 2. 选题评分脚本边界测试
python3 skills/research-orchestration-workflow/scripts/topic_scoring.py \
  --topic test --originality 11 --feasibility 7 --value-density 9 \
  --data-availability 7 --competition 6 --cognition 8 --resource-fit 7 --sustainability 7
# 期望：退出码 1 + "评分超出有效范围"

# 3. 专家包完整性
python3 /path/to/validate_expert.py .
```

## 开发流程

1. Fork 仓库 → 创建 feature 分支（命名：`feat/xxx` / `fix/xxx` / `docs/xxx`）
2. 改动一个角色或协议 → 在 `agents/` 或 `references/agent-protocol.md` 修
3. 若涉及协议改动（消息信封/仲裁/错误分类），**必须**同步更新：
   - 5 个 agent MD 的「v2.0 协议合规契约」章节
   - `protocol_check.py` 对应单元测试
   - `CHANGELOG.md` 标注 BREAKING
4. 跑完整 CI（见上）→ 通过后提 PR
5. PR 描述须含：变更动机 + 影响范围 + 红队/回归证据

## 角色修改规范

每个 agent MD 顶部都有「v2.0 协议合规契约」5-7 条约束。**修改任何约束必须**：
- 在 PR 描述里逐条列出
- 同步 `agent-protocol.md` 的相关章节
- 跑 `protocol_check.py` 确保其他 agent 仍能产出合规信封

## 文档维护

- README 安装方式与当前实际命令保持同步（marketplace add 路径/插件目录名）
- CHANGELOG.md 每条目含：版本 / 日期 / 变更摘要 / 红队/回归证据
- 红队审查报告（`docs/REDTEAM-REPORT.md`）按需更新，不要删除历史记录

## 提问与求助

- 协议设计层：开 issue 标 `protocol`
- 角色 prompt 层：开 issue 标 `agents/<角色名>`
- 工具/脚本层：开 issue 标 `scripts`