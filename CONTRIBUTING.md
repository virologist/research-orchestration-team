# Contributing to Research Orchestration Team

> 感谢你愿意参与贡献。本专家包是研究规划与决策支持的协作工具集，质量门槛 = 学术严谨。

## 行为准则

- **事实洁癖**：不伪造文献、不编造证据等级、不把推断包装成事实
- **尊重角色边界**：每个 agent 有严格的能力范围（见两份 manifest 与 `skills/research-orchestration-workflow/references/agent-protocol.md` §1）
- **诚实标注不确定性**：单一来源、证据冲突、未核实内容须 ⚠️ 标注

## 提交前必跑（强制 CI）

```bash
# 推荐：一条命令跑完 22 条门禁并落盘「检查对象/结果/证据」，再单独做文档差集与反馈检查。
python3 scripts/rot.py check
python3 scripts/rot.py verify
python3 scripts/rot.py feedback

# CI 共 23 个门禁 step（18 静态 + 4 结构 + 1 文档差集；另有 6 个平台 step 不计入），
# 以下按 workflow 顺序给出本地等价命令。
# 逐条独立取 rc；rc=0 通过 / rc=1 校验失败 / rc=2 文件不存在 / rc=3 参数缺失。
# rc≠0/1 一律先查命令、路径、参数，不直接归因为门禁失效（见 LEARNING.md 的 FM-R1-08）。

# 1. 包一致性（C1–C13，74 项：双 manifest 对等含 description / 市场清单 / agents 与头像 /
#    团队 settings 自洽 / README 版本一致 / 废弃表述 / 契约章节 / 成员 ID 五处一致性）
python3 scripts/manifest_check.py -v

# 2. 校验器自测（注入式负例 30 条，含 C8 全规则矩阵 N27 / C13 分支 N28–N30）：
#    证明上面的校验器真的会失败，而不是永远返回 0
python3 scripts/manifest_check_selftest.py

# 3. 协议合规（信封 37 + legacy 12 / 仲裁 5 / 集成 10 + HANDOFF 8）
python3 skills/research-orchestration-workflow/scripts/protocol_check.py envelope
python3 skills/research-orchestration-workflow/scripts/protocol_check.py conflict
python3 skills/research-orchestration-workflow/scripts/protocol_check.py integration

# 4. 协议合规注入式负例自测（14 条）：证明上面三个 suite 不是永远返回 0
python3 skills/research-orchestration-workflow/scripts/protocol_check_selftest.py

# 5. 阶段名归一化自测（26 条）：--phase 阶段名 / 数字 / 大小写 / 非法值的归一化行为
python3 scripts/test_phase_normalization.py

# 6–7. Harness 设计检查 H1–H12 + 注入式负例自测（14 条）
python3 scripts/harness_eval.py
python3 scripts/harness_eval_selftest.py

# 8–9. 路由结构一致性 R1–R6（39 项）+ 注入式负例自测（12 条）
python3 scripts/routing_eval.py
python3 scripts/routing_eval_selftest.py

# 10. 联邦防漂移 V1–V6
python3 tests/test_vendor_core.py

# 11–12. State IO lifecycle smoke / 熔断路径：这两段是 workflow 内嵌脚本（heredoc），
#        本地等价命令见 .github/workflows/validate.yml 同名 step，直接复制其命令块执行。

# 13. 编排层四项硬上限语义锁定（4 条）：turns/tokens 触顶=告警、max_time/failures=终态熔断
python3 tests/test_state_ceilings.py

# 14. state_io 输入护栏注入式验证（10 条）：checkpoint 归一化 / task_id 消毒 / 回归护栏
python3 tests/test_state_io_guards.py

# 15. 主理人双重事实源一致性（6 条，R5）：C12 的 agentName 必须跟随 C13 声明位
python3 tests/test_lead_source_of_truth.py

# 16. 运行时序 / 终态污染 / 观测数据一致性（8 条，R6）
python3 tests/test_state_runtime_sequencing.py

# 17. 状态文件健壮性 / cp 编号 / 孤儿 tmp（12 条，R7）
python3 tests/test_state_file_robustness.py

# 18. 选题评分脚本边界测试
python3 skills/research-orchestration-workflow/scripts/topic_scoring.py \
  --topic test --originality 11 --feasibility 7 --value-density 9 \
  --data-availability 7 --competition 6 --cognition 8 --resource-fit 7 --sustainability 7
# 期望：退出码 1 + "评分超出有效范围"

# 19. 工作地图一致性 W1–W12（任务/阶段/依赖/工具/验收/地图与样例不漂移）
python3 scripts/workmap_check.py -v

# 20. 工作地图校验器注入式负例自测（7 组破坏，每组精确命中一个检查项）
python3 scripts/workmap_check.py --self-test

# 21. 真实任务样例断言有效性自测（A1–A9 正例 PASS / 反例 FAIL）
python3 scripts/sample_check.py --self-test

# 22. 反馈记录完整性 / 规则膨胀 / 认可样例状态（F1–F8）
python3 scripts/rot.py feedback

# 23. 文档 ↔ 仓库实际 全量差集（V0–V10，发布契约第 5 条的程序化实现）
python3 scripts/rot.py selftest
python3 scripts/rot.py verify
```

> `scripts/manifest_check.py` 的校验项为 C1–C13，全部为**硬失败**（`rc=1`）。
> 其中 C8 的废弃术语清单是本仓库的**单一事实来源**，请勿在 workflow 或别处另抄一份
> —— 历史上正是因为另抄了一份「精确串」清单，某个在关键词中间插了字的旧表述逃过匹配，
> 造成了 CI 假绿。

## 开发流程

1. Fork 仓库 → 创建 feature 分支（命名：`feat/xxx` / `fix/xxx` / `docs/xxx`）
2. 改动一个角色或协议 → 在 `agents/` 或 `references/agent-protocol.md` 修
3. **改任何元数据必须同步两份 manifest**：`.claude-plugin/plugin.json`（Claude Code）与
   `.codebuddy-plugin/plugin.json`（WorkBuddy）。二者的共享字段
   （`name` / `version` / `license` / `homepage` / `repository` / `description` / `agents` / `skills`）
   必须逐项一致，由 `manifest_check.py` 的 C2 强制校验。
   注意 `skills` 的取值是**字符串** `"./skills"`（WorkBuddy 第一方约定），不是文件路径数组。
4. **市场清单同样要同步两份**：`.claude-plugin/marketplace.json` 与 `.codebuddy-plugin/marketplace.json`。
   本仓库是「自我托管市场」——仓库根既是市场根也是插件根，市场条目用 `"source": "./"` 指回自身。
   **删掉或改坏它们会让 README 首推的 `/plugin marketplace add` 失效**（v2.0.1 之前就是这个状态），
   由 `manifest_check.py` 的 C10 守护。
5. 若涉及协议改动（消息信封/仲裁/错误分类），**必须**同步更新：
   - 6 个执行/分析/审查型 agent MD 的「v2.0 协议合规契约」章节
     （整合者用「接口契约」、主理人用「Harness 运行时规范 v2.0」，命名不同但语义等价，
     由 `manifest_check.py` 的 C9 统一校验「每个成员都必须有契约章节」）
   - `protocol_check.py` 对应单元测试
   - `CHANGELOG.md` 标注 BREAKING
6. 版本号三处同步：两份 `plugin.json` 的 `version` + README 头部的「版本」（由 C7 校验）
7. 跑完整 CI（见上）→ 通过后提 PR
8. PR 描述须含：变更动机 + 影响范围 + 红队/回归证据

## 角色修改规范

本包共 8 个 agent（1 主理人 + 7 成员）。契约章节的命名分工如下：

| 角色类型 | agent | 契约章节 |
|---------|-------|---------|
| 主理人 | `research-orchestration-team-team-lead` | `## Harness 运行时规范 v2.0` |
| 分析/执行/审查型成员 | `socratic-questioner` / `meta-architect` / `domain-expert-biomed`（atomic 三元之一）/ `methodological-reviewer` | `## v2.0 协议合规契约` |
| 整合型成员 | `synthesis-integrator` | `## 接口契约` |

> 注：本表及上文第 5 条中的「v2.0 协议合规契约」「Harness 运行时规范 v2.0」此处为契约章节名，非版本号，勿随协议版本改名；`scripts/manifest_check.py` 的 `CONTRACT_SECTION_MARKERS` 以这些字面量做校验，改名会直接破坏门禁。

**修改任何契约约束必须**：
- 在 PR 描述里逐条列出
- 同步 `agent-protocol.md` 的相关章节
- 跑 `protocol_check.py` 确保其他 agent 仍能产出合规信封
- 跑 `manifest_check.py` 的 C9 确认没有成员丢掉契约章节

> `protocol_check.py` 只测试协议逻辑本身，**不读取 agent MD 文件**。
> 因此「成员是否带契约章节」这条链路由 C9 单独守护。

## 文档维护

- README 安装方式与当前实际命令保持同步（marketplace add 路径/插件目录名）
- README 的结构树必须与仓库实际目录一致；`avatars/` 的分发策略若变更，需同时改
  `.gitignore`、结构树、三条安装说明三处
- CHANGELOG.md 每条目含：版本 / 日期 / 变更摘要 / 红队/回归证据
- 红队审查报告（`docs/REDTEAM-REPORT.md`）按需更新，不要删除历史记录
- 仓库根不放置开发期产物（演化报告、中间结果等），如需留档请归档到 `docs/` 下列目录
- 不使用 `*.bak` / `*.orig` 之类的手工备份：`.gitignore` 已忽略，且已入库的备份
  不会因 ignore 规则而消失（需 `git rm` 才能真正移除）

## 提问与求助

- 协议设计层：开 issue 标 `protocol`
- 角色 prompt 层：开 issue 标 `agents/<角色名>`
- 工具/脚本层：开 issue 标 `scripts`