# LEARNING.md · 跨会话连续性记忆（Anthropic Ralph Loop 模式）

> 本文件是 v2.1.0 Harness Engineering 的**跨会话记忆载体**。每个任务结束时，相关 agent **必须**追加一段 task 记录到本文件。
> 模型：Anthropic Ralph Loop（双相：Init agent 写 progress file → 后续 session 读取 → 接力）。
> 校验：`scripts/harness_eval.py` H9 检查本文件存在。

---

## 写入规则

每个 task 记录必含：
- **日期**：`YYYY-MM-DD`
- **agent_id**：哪个 agent 写入（domain-expert-biomed / -ai / -general / methodological-reviewer / synthesis-integrator / team-lead）
- **task_topic**：本次任务一句话主题
- **决策**：本次任务的关键决策（≤ 5 条 bullet）
- **证据**：关键证据（GRADE 等级 + 来源 DOI/PMID/URL）
- **下一步**：本任务的下一步建议（≤ 3 条 bullet）
- **observability**：4 个 metrics（成功率 / 平均 tool call / 重试次数 / next_actions 字段存在率）

---

## Task 记录（按时间倒序）

> 说明：以下 v2.2.0 补记的 5 条为**工程内证**——证据来源为本仓库真实 commit（short hash）、`CHANGELOG.md`、`README.md 版本历史` 与脚本 / 文件路径，不引用外部 DOI / PMID / URL；`observability` 因历史未逐任务采集，统一如实标注「未采集」，不自造数值。

### [2026-11-10] / team-lead / R3 输入护栏收口（半成品回归实锤 + 注入式护栏）

- **决策**：
  - 接手时发现另一工作线已落盘两处输入护栏修复但未提交、无测试、无文档；按「不擅自扩展诊断范围」原则，只收口已落盘修复与其引入的回归
  - 实测实锤回归：`--checkpoint` 为可选参数，半成品把「未传」与「非法」都返回 `None` → 不带检查点的正常推进 rc=1（期望 0）；改为空值返回空串、非法值才返回 None
  - 按 FM-R2-06 纪律补 10 条护栏用例：逐条独立临时目录 + rc，负例断言失败原因归属被测分支且无裸堆栈；包根向上逐层探测标志目录，不用 `parents[N]` 硬索引
  - 代码行为变更但**未升版、未打 tag、未发 release**，升版与发布交由管家节点裁决
- **证据**：
  - `tests/test_state_io_guards.py` 10/10 全绿；3 组注入破坏实验证明会红（A 空值仍返回 None → G1/G9 红；B 去掉前缀剥离 → G2 红；C 短路 task_id 消毒 → G6/G7/G10 红）
  - 实测：不带 checkpoint 的 advance 修复前 rc=1、修复后 rc=0；`state://cp-001` 归一化为 `checkpoints/cp-001.md` 且无 `state:` 目录；非法 task_id 统一入口 rc=2
  - CI step 口径核到 step 名级：v2.4.x 12 门禁/18 总、v2.5.0 14 门禁/20 总、R3 15 门禁/21 总（差额 6 恒为平台 step）
  - 本条为**工程内证**：证据来源为本仓库真实脚本路径、实跑退出码与 `gh run view` 输出，不引用外部 DOI / PMID / URL
- **下一步**：
  - R3 全轮 Phase A 再诊断 / GATE 裁决 / 台账完整落盘，待管家节点裁决
  - 是否发 v2.5.1（代码行为已变更）待裁决；已发布 tag `v2.5.0` 不重写
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集

### [2026-11-09] / team-lead / v2.5.0 R2 覆盖矩阵盲区修复（语义锁定 + 幽灵成员门禁 + 负例补全）

- **决策**：
  - R2 主题定为**覆盖矩阵盲区审计**——「每一条门禁分支都要有一只『会红的测试』盯着」。用 16 组真实破坏实验逐条验证三层门禁，把 R1 的产出当作待验证对象而非既成事实
  - 实锤并修复 **2 个 P0**（编排层上限语义失真 / 流水线幽灵成员无门禁）、**4 个 P1**（protocol selftest N6/N10 纯重复 / C8 七条规则无负例 / fail-熔断零 CI 覆盖 / C13 三分支无负例）、**1 个 P2**（跨市场 description 漂移）；同时排除 **4 个假阳性**（C8 豁免窗口边界 / C13 目录删除 / C11 三路径 / references 依赖）
  - 发布链路同步根治：README「安装方式 3」改为指向 `releases/latest` 页面（去掉版本锚点），并补 4 条打包前强制检查，根治「每次发版都要改 README」的复发点
- **证据**：
  - 全量回归 **13/13 套全绿**（逐条独立取退出码）：manifest 74/74、manifest_selftest 30/30、harness 12/12、harness_selftest 14/14、routing 39/39、routing_selftest 12/12、phase_norm 26/26、vendor V1–V6 6/6、state_ceilings 4/4、protocol envelope 37/37(v2.4)+12/12(legacy)+conflict 5/5+阶段流水线 10/10+HANDOFF 8/8、protocol_selftest 14/14
  - 6 组独立负向实锤（不采信 CHANGELOG 自报，每次破坏后还原、md5 与基线逐字节一致）：幽灵成员 `GHOST-MEMBER` → integration rc=1 并精确列出幽灵 ID；C2 description 漂移 → rc=1 并逐字段对照；熔断全链路 → `aborted` + advance rc=1 拒绝 + finish rc=0 但状态不改写；C13 三分支（`members[].role` 声明位互换 / 表格单元格重复 ID / `agents/*.md` 全删）→ 三分支各自 rc=1；C8 废弃表述注入 → 两条规则精确命中带行号
  - CI run `42623476669` success（14 门禁 step / 20 总 step 全执行）；发布产物 `rot-v2.5.0.tar.gz` 14689986 B，tag `v2.5.0` 落在 CI 绿 commit `4d6e7e0`
  - 三源一致性：canonical / origin / OneDrive 镜像 / GitHub API 四处 HEAD 全等 `4d6e7e0`，两处工作树 `git status --porcelain` 均 0 项
  - 本条为**工程内证**：证据来源为本仓库真实 commit / 脚本路径 / 实跑退出码，不引用外部 DOI / PMID / URL
- **下一步**：
  - R2 状态文件（`docs/harness-iteration-loop.md`）Phase D 已落盘：§1 元信息 / §1.1 R1 快照 / §3.1 漂移复检 / §4.2 R2 台账 / §4.3 R2 批次明细 / §5.2 R2 验收证据 / §8 FM-R2-01~06 / §10 改 R3 入口 / §10.3.2 负例验收纪律补录 / §10.5 R3 建议审计方向
  - FM-R2-03 ~ FM-R2-06 四条失败模式已回流本文件，并入速查索引
  - R3 的增量空间更可能在**断言交互**与**运行时序**（并发 / 重入 / 中断恢复），而非单条分支——建议方向见 §10.5
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：3（`manifest_check_selftest` 与 `routing_eval_selftest` 在前台被沙箱 SIGTERM 截断，改为后台独立运行 + 显式超时后通过）
  - next_actions 字段存在率：未采集

### [2026-11-09] / team-lead / v2.4.1 发布介质自洽性补丁（tarball 与 tag 内容脱钩的根因修复）

- **决策**：
  - 发现 `v2.4.0` 的 release 资产 `rot-v2.4.0.tar.gz` 内的 README 仍写「方式 3 只能安装到 v2.1.2」——**介质与自身文档矛盾**
  - **否决**重打 v2.4.0 资产：会造成「资产内容 ≠ tag 内容」，比文档过期更严重
  - **否决**重写 `v2.4.0` tag：已发布 tag 不可重写
  - 采用**补丁版 v2.4.1**：版本号三处同步，方式 3 改指 `rot-v2.4.1.tar.gz`，CHANGELOG 与 README 版本历史如实登记缺口成因
  - 确立发布纪律：**文档修正必须先于打 tag**；资产一律用 `git archive <tag>` 打包以强制「资产内容 == tag 内容」；打完必须解包核对再上传
- **证据**：
  - 根因定位：修正「方式 3」链接的 commit `2f2b016` 发生在打 tag `v2.4.0`（指向 `90a1c36`）**之后**
  - v2.4.1 全量回归 12/12 套全绿（逐条独立取退出码）：manifest 73/73、manifest_selftest 26/26、harness 12/12、harness_selftest 14/14、routing 39/39、routing_selftest 12/12、phase_norm 26/26、vendor V1–V6 6/6、protocol envelope 37/37(v2.4)+12/12(legacy)+conflict 5/5+阶段流水线 9/9+HANDOFF 8/8、protocol_selftest 13/13、shim rc=0
  - CI run `42561278912` **12 门禁 step / 18 总 step 全部实际执行全绿**（核到 step 级，非仅看摘要）
  - 资产自洽性实锤：`git archive v2.4.1` 打包 → 解包后 README 版本行为 `2.4.1`、方式 3 指向 v2.4.1 自身资产、双 manifest 均为 `2.4.1`；解包副本 manifest 73/73、protocol rc=0、shim rc=0
  - 发布产物：`rot-v2.4.1.tar.gz` 14673511 B（API 确认落地），tag `v2.4.1` 落在 CI 绿 commit `5a5aaa4`
  - 三源一致性：canonical / origin / mirror / GitHub API / tag **五方 HEAD 全等 `5a5aaa4`**，两处工作树 0 项未提交；镜像侧独立复跑 manifest 73/73 与 protocol 全套通过
  - 本条为**工程内证**：证据来源为本仓库真实 commit / 脚本路径 / 实跑退出码，不引用外部 DOI / PMID / URL
- **下一步**：
  - 发布链路纪律已写入 `docs/harness-iteration-loop.md` §9 + §10.3.1，下轮发版按此顺序执行
  - FM-R2-01 / FM-R2-02 两条失败模式已回流本文件，并入速查索引
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：1（`gh release upload` 曾遇 SIGTERM，改用 `timeout 400 ... --clobber` 后 rc=0；随后 API 确认资产落地）
  - next_actions 字段存在率：未采集

### [2026-11-09] / team-lead / v2.4.0 R1 Harness 迭代进化闭环（四阶段 + 13 批次）

- **决策**：
  - 建立 `docs/harness-iteration-loop.md` 作为断点续跑单一事实源（意图漂移基线 / 四阶段台账 / 验收基线 / 资产清单 / 已修复问题黑名单 / 失败模式库 / 发布契约 / 下轮入口），使每轮迭代可中断可续跑
  - 门禁必须具备 `main() → return 0/1 → sys.exit(main())` 完整链路；只打印通过/失败标记不算门禁——根治协议校验恒绿
  - 注入式负例的两条硬纪律落为正式规范：①锚点唯一命中 + 替换后落盘校验 ②一条负例只承载一个失败维度
  - 成员集合维度的机器真值源定为 `agents/*.md` 文件名集合（最底层事实），由 C13 逐处比对 8 个目标；协议 §1 只负责「角色↔成员 ID 的归属」这一层
  - 编排层硬上限（30 轮 / 1800s / 200000 token / 熔断 5 次）在 `state_io.py` 代码化，与平台层 `maxTurns: 180` 分层表述、两层都保留
- **证据**：
  - 门禁全量回归 12/12 套全绿（逐条独立取退出码，不串成一条命令）：manifest 73/73、manifest_selftest 26/26、harness 12/12、harness_selftest 14/14、routing 39/39、routing_selftest 12/12、vendor V1–V6 6/6（安装态 0 SKIP）、phase_norm 26/26、protocol envelope 37/37(v2.4)+12/12(legacy)、conflict 5/5、integration 阶段流水线 9/9 + HANDOFF 回引覆盖 8/8 检查点、protocol_selftest 13/13
  - 4 组独立负向实锤（不采信执行者自报；每次破坏后还原，md5 与基线逐字节一致）：改协议 §1 成员 ID → rc=1 且逐项列「多出/缺少」；清空 `agents/*.md` → rc=1（真值源为空一律判红）；破坏 `state_io.py` 的 `PHASES` → 集成段 rc=1 且列两侧序列差异；状态机 9 条路径退出码各自符合设计语义
  - Phase C 13 个批次落盘：12 文件已改 + 5 文件新建（新增 `docs/harness-iteration-loop.md`、`scripts/test_phase_normalization.py`、`skills/research-orchestration-workflow/scripts/protocol_check_selftest.py`、`skills/research-orchestration-workflow/templates/cross-domain-combo.md`、`skills/research-orchestration-workflow/templates/result-envelope-v2.4.json`）
  - CI 改造：12 → 14 个 step（纳入 protocol_selftest 与 phase_norm 两套注入式负例），timeout 15 → 25 分钟
  - 本条为**工程内证**：证据来源为本仓库真实脚本路径与实跑退出码，不引用外部 DOI / PMID / URL
- **下一步**：
  - 官方 `validate_expert.py` 本机不存在（宿主未随包分发）→ 环境性已知限制，改由包内 manifest_check + test_vendor_core 的 V5/V6 安装态冒烟替代
  - `protocol_check.py` 集成段的 `cp-001~cp-008` 检查点清单仍硬编码：当前已与 `state_io.py` 阶段序列交叉比对（真断言），但 cp 清单本身未动态化，成员增删 cp 编号变动时需同步
  - selftest 约 350s IO 耗时（每条负例在临时目录复制整个包体）：可用硬链接替代复制提速
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：3（批次 5 的三个执行者在**回报阶段**同时触发平台 Token Plan 上限；产出已先行落盘并经主理人独立负向实锤验收，上限未影响交付完整性）
  - next_actions 字段存在率：未采集

### [2026-11-08] / team-lead / v2.3.0 残留风险工程化收口（R5 分级扩展 + R6 工具真实性）

- **决策**：
  - v2.2.0 发布时登记的 4 条残留风险中 3 条落为工程修复，1 条文档化收口，不「记录了事」
  - R5 分级解析扩展全 8 成员：atomic（registry 有 tools 行）沿用四类解析 + 双向相等；非 atomic（零工具授权）用 ①②③ 三类解析、任何工具 token 即 FAIL，跳过对中文叙述误报率高的 ④ `+` 槽位分支——不选「净化 MD 描述」路线，避免损失内容
  - 新增 R6 工具真实性：对照真实 MCP 清单（env `ROUTING_EVAL_MCP_JSON` → `~/.workbuddy/mcp.json`）硬校验 registry 全部 `mcp__` 名；清单不可得的 CI / git-clone 态显式 SKIP（⏭️ 标记，不计 FAIL 不影响 rc），安装态必须 PASS
  - 条目 4（validate_expert 硬编码安装路径）在 README 文档化为已知限制，不改官方脚本
  - 门禁总量 33 → 39 项（R5 3→8、R6 +1）
- **证据**：
  - `git fd23177` feat(v2.3.0)（R5/R6/文档收口/升版，7 files +304/-65）
  - `git 85e343c` fix(CI): N12 fixture 自包含化（见下方 lesson）
  - 实测：routing 39/39（R5 8/8 + R6 1/1）、selftest 12/12、R6 SKIP 分支空 HOME 下 rc=0、破坏验证非 atomic 注入 rc=1 / registry 注 GHOST_SERVER + 清单 rc=1、CI run 42420262814 success
  - Release：tag v2.3.0 → 85e343c，三源（canonical / GitHub / OneDrive 镜像）一致
- **下一步**：
  - CI tag 步骤曾把 tag 打在 CI-failure 的 fd23177 上，后重打到 85e343c——发布纪律补强：**tag 必须落在 CI 绿的 commit**，先看 run 结果再打 tag（已执行，记录防复发）
  - R6 的 SKIP 语义与 V4 同类：环境性 SKIP ≠ 门禁失败，但「39/39 全绿」在 CI 态实际是 38 项判定 + 1 项 SKIP，对外报告须注明
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：1（fd23177 CI 红后 85e343c 修复重推）
  - next_actions 存在率：2/2（两条均有下一步）

### [2026-11-07] / team-lead / v2.2.0 P0-1 恢复包根 settings.json + manifest C12 护栏

- **决策**：
  - 推翻 v2.1.2 后「宿主启动时必然删除 settings.json」的假设，恢复包根 `settings.json`
  - 官方 `validate_expert.py` 对 Team 型硬要求该文件（报错原文「Team type must have settings.json」），删除后官方校验出现 1 error
  - 反证：同格式的 agent-harness-expert 文件存活数周未被宿主删除，原假设不成立
  - `manifest_check.py` 63 → 64 项，新增 C12（Team 型 settings.json 存在 + 单键 agent 指向主理人），把「宿主误删」变成下次发行校验即报警
  - `manifest_check_selftest.py` 负例 17 → 21（N18 删除负例 / N19 篡改负例 / N20 旧团队规模表述 / N21 隐藏目录 marketplace.json 旧英文规模表述护栏，验证 C8 rglob 覆盖）
- **证据**：
  - `git 66d069b` fix(P0-1): 恢复包根 settings.json + manifest_check C12 护栏（2026-11-07）
  - `git 5fc2630` / `git 688dd92` 为当初删除该文件的两次 commit（2026-11-04），本版已 revert
  - `CHANGELOG.md §[2.2.0] Fixed`：官方 `validate_expert.py` 由 1 error → 0 error；C12、N18/N19/N20/N21 与 C8 的「旧团队规模表述（现为八agent / Eight-agent）」规则说明
  - `README.md 版本历史 v2.2.0`：「恢复包根 settings.json（官方校验 0 error）+ manifest C12 护栏」
- **下一步**：
  - 后续发行前跑 `python3 scripts/manifest_check.py -v` 确认 C12 仍绿
  - 若未来宿主真删除该文件，以 C12 报警为准，不等官方校验器事后报错
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-11-07] / team-lead / v2.2.0 P0-2 state_io.py 状态持久化与断点续跑

- **决策**：
  - 把 `agent-protocol.md §3` 的纸面 schema（八阶段状态机）变成确定性落盘：状态写入 `<workspace>/.harness-runs/<task_id>/_state.json`
  - 新增 `skills/research-orchestration-workflow/scripts/state_io.py`，五命令 init/advance/resume/finish/budget
  - 原子写（`.tmp` + `os.replace`）；退出码 0/1/2/3，JSON 损坏 fail fast 不静默重建
  - `state://cp-NNN` 伪 URI 绑定真实路径 `.harness-runs/<task_id>/checkpoints/cp-NNN.md`
  - team-lead.md 增「状态初始化与断点续跑」强制条款：开工 resume 盘点、阶段收尾 advance、撞限恢复不依赖对话记忆；写入者=仅主理人
- **证据**：
  - `git e73df63` feat(P0-2): 状态持久化落地 — state_io.py + 断点续跑条款（2026-11-07）
  - `CHANGELOG.md §[2.2.0] Added`：「八阶段状态的确定性落盘层」、原子写并发 20 路实测无损坏、rc 0/1/2/3 契约
  - `README.md 版本历史 v2.2.0`：「新增 state_io.py 状态持久化与断点续跑（治协议 §3 纸面 schema）」
  - `state_io.py` 文件头 docstring 明载五命令用法与退出码契约（仓库真实文件）
- **下一步**：
  - 新会话开工先跑 `state_io.py resume` 盘点「上次阶段 + 下一步」
  - 把本文件新增的 lesson 记录与 `state_io.py finish` 归档判断对齐
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-11-07] / team-lead / v2.2.0 P0-3 版本收口 2.2.0 + CHANGELOG 历史欠账补记

- **决策**：
  - 双 manifest version 由 2.1.2 收口到 2.2.0，README 头部同步
  - 补记 tag v2.1.2（`bb05e18`）之后 6 个「无版本号 commit」的 CHANGELOG 欠账（shim v3.4.2 跟升、vendor 联邦两级查找、settings.json 移除决策的推翻等）
  - 恢复「改必升版」纪律，避免长期不升版导致版本历史失真
  - README 三处过期同步：团队表 6 人→8 人（八人团队）、目录树补 vendor / tests / state_io 等、版本历史补 2.1.0 / 2.1.1 / 2.1.2 / 2.2.0
  - LEARNING.md 补 tag 后 5 条历史记录 + 新增「失败回流规则」落盘节
- **证据**：
  - `git 8fc83ca` chore(P0-3): 版本收口 2.2.0 + CHANGELOG 补账（tag v2.1.2 后 6 commit 欠账）（2026-11-07）
  - `CHANGELOG.md §[2.2.0]` 开头「从零独立诊断（15 项短板亲验）后的补全完善版」与 Regression evidence 表
  - `README.md 版本历史` 现有 v2.1.0 / v2.1.1 / v2.1.2 / v2.2.0 四条
  - `git bb05e18`（tag v2.1.2，2026-09-30）与 `git 0945fba`（其后无版本号基线，2026-11-04）
- **下一步**：
  - 保持「改必升版」：任何后续改动先升版再改 CHANGELOG
  - 本文件每条新 task 记录须带真实 commit hash 作证据，禁止口头补账
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-30] / team-lead / v2.1.2 协议 / 门禁加固：两套上限消歧义 + CI 纳入 H1-H12 + 注入式负例

- **决策**：
  - 修复 v2.1.0 atomic 拆分后 4 处 `domain-expert` 死引用，改为按领域标签 fan-out 到三个 atomic
  - **两套上限消歧义**：frontmatter `maxTurns: 180` = 平台层会话兜底；registry `max_turns: 30` = 编排层任务自控预算，两者不冲突
  - CI 新增 2 个 step：`Harness design checks (H1-H12)` 与 `Harness eval self-test`，把此前仅本地手动跑的 12+13 项检查纳入门禁
  - `manifest_check_selftest.py` N2 假绿根因：文案改为「五级仲裁」后 replace 精确串 mutation 空转；改为 append 式注入废弃表述，无论现文案如何都稳定触发校验器
  - 双 manifest version 2.1.0 → 2.1.2
- **证据**：
  - `git bb05e18`（tag v2.1.2）fix(v2.1.2): 补全 v2.1.0 atomic 拆分残留 + CI 纳入 harness 校验（2026-09-30）
  - `git 0945fba` 为 v2.1.2 之后的基线刷新（2026-11-04）
  - `CHANGELOG.md §[2.1.2]`：四处死引用、maxTurns 消歧义、N2 修复、`.github/workflows/validate.yml` 两个新 step
  - `README.md 版本历史 v2.1.2`：「回归 12/12 + 63/63 + 17/17 + 13/13」
- **下一步**：
  - 每次改校验器文案后跑 selftest，防 mutation 空转假绿复发
  - CI 门禁结果纳入本文件下一条记录的证据链
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-19] / team-lead / v2.1.1 新增 harness_eval_selftest.py（dev-only 注入式负例）

- **决策**：
  - 仅新增 1 个 dev-only 验证脚本，协议与运行时行为无变更，已安装实例无需重装
  - `scripts/harness_eval_selftest.py`：13 条注入式负例（当时口径；v2.2.0 新增 N13 后为 14 条）（N1-N12 + R1），对应 `harness_eval.py` 的 H1-H12 检查
  - 每条双断言：`rc=1`（反向用例 `rc=0`）+ 输出命中预期检查项文案，避免「校验器永久返回 0」的假绿
  - 首次跑暴露真实漏洞：selftest v1 跑出 10/13 失败，因 mutate 大小写敏感漏过 `Per-step Verification`；改用 `re.sub(..., flags=re.IGNORECASE)` 后 13/13 全过
  - 不接入 CI（与 `manifest_check_selftest.py` 同策略）
- **证据**：
  - `git 45dd4a9`（tag v2.1.1）test(harness): 新增 harness_eval_selftest.py — 13 条注入式负例（当时口径；v2.2.0 新增 N13 后为 14 条）（2026-09-19）
  - `git 7b1c75a` docs(changelog): v2.1.1 CHANGELOG 条目（2026-09-19）
  - `CHANGELOG.md §[2.1.1]` Added / Fixed 两节与 Regression evidence 表（`harness_eval_selftest.py` 从「❌ 不存在」→ 13/13 ✅）
  - `README.md 版本历史 v2.1.1`：「新增 harness_eval_selftest.py（dev-only 负例工具），运行时行为无变更」
- **下一步**：
  - 后续改 `harness_eval.py` 任一检查项，须同步补对应负例
  - 保持 dev-only 定位，不擅自接入 CI（变更需走版本升版）
- **observability**：
  - 成功率：未采集（v2.2.0 起由 state_io.py 落盘后可追溯；本条为历史补记）
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集（本文件「下一步」段落已补齐该字段语义）

### [2026-09-18] / team-lead / v2.1.0 Harness Engineering 升级

- **决策**：
  - 拆 `domain-expert` 为 3 个 atomic subagent（biomed / ai / general），符合 Vercel / LangChain 实测的"工具最小化"
  - 引入 `agent-registry.md` 单一事实源（含 trigger / tools / safe/moderate/dangerous 权限档）
  - 引入 Loop 硬停止（max_turns=30 / max_time=1800s / max_token=200000 / circuit_breaker=5 次失败熔断）
  - 引入 plan_execution 元工具（Orchestrator Pattern 信号触发串行）
  - 引入 per-step verification（每步走 verification，不只 final-output）
  - 引入 4 个 observability metrics（成功率 / tool call / 重试 / next_actions 字段存在率）
  - 引入 LEARNING.md（Anthropic Ralph Loop 跨会话连续性）
- **证据**：

> ⚠️ 以下 4 条为设计时引用的**外部量化声称，本仓库未留存来源、未核实**，仅作设计动机记录，不得作为事实依据或对外引用。

  - LangChain: Terminal Bench 52.8% → 66.5%（仅改 Harness）
  - Vercel: 砍 80% 工具反而更准
  - Anthropic Harness Engineering: 任务成功率 ×2-3（不换模型）
  - METR 研究："先建 eval 再动 Harness"是 2026 分水岭
- **下一步**：
  - 跑 `scripts/harness_eval.py` 验证 12/12 通过
  - 写 `scripts/harness_eval_selftest.py` 注入式负例
  - 更新双 manifest / CHANGELOG / README
  - commit + force-with-lease push + tag v2.1.0 + Release + 同步 OneDrive
- **observability**：
  - 成功率：本任务 = 100%（plan → 5 phase 全部完成）
  - 平均 tool call：~30 次（web search ×5 + bash ×25）
  - 重试次数：0
  - next_actions 字段存在率：100%（每个 phase 结尾都有具体下一步）

---

## 模板（Copy-Paste 写入新记录）

```markdown
### [YYYY-MM-DD] / <agent_id> / <task_topic>

- **决策**：
  - ...
- **证据**：
  - ...（必带 GRADE + DOI/PMID/URL）
- **下一步**：
  - ...
- **observability**：
  - 成功率：...%
  - 平均 tool call：...次
  - 重试次数：...次
  - next_actions 字段存在率：...%
```

---

### [2026-11-07] / team-lead / 部署前两轮独立交叉验证发现门禁假绿与协议方向性错误

- **决策**：
  - 两轮独立交叉验证确认：发布门禁曾因「全文子串兜底词」出现假绿，协议信封校验方向一度指错版本，均须以仓库内真实规则为准收口
  - 权限档一律改为按 `###` 章节标题判定，不再用全文子串匹配，杜绝引言 / Changelog 兜底词放行被删章节
  - selftest 引入未归一化原始副本的 raw_probe 护栏，拒绝用「自愈夹具」把真实仓库的路由不一致归一化掉
  - 协议合规统一以 result_envelope v2.4 为当前判定，ACP v2.0 信封仅保留为历史 fixture 回归，不参与当前合规判定
  - 文档口径按脚本真实用例数收口；外部量化声称一律标注未核实，不得作为事实依据
- **证据**：
  - `scripts/routing_eval.py` R3：权限三档 safe / moderate / dangerous 必须作为 `###` 章节存在且正文非空（按章节标题判定，替代全文子串匹配）
  - `scripts/harness_eval.py` H6：`check_h6_permission_layer` 以 `^###\s+(safe|moderate|dangerous)\b` 取章节标题并校验正文非空
  - `scripts/routing_eval_selftest.py` raw_probe：准备阶段对未归一化原始副本直接跑 `routing_eval.py`，rc 非 0 即拒绝继续，不计入 CASES 用例数
  - `scripts/protocol_check.py`：`run_envelope_v24_tests` 主套件 16 用例（6 必填字段 + 小写四值 status），`run_legacy_envelope_tests` 12 用例仅作历史 fixture 回归
  - `scripts/manifest_check.py` C8：`FORBIDDEN_PATTERNS` 中「旧团队规模表述（现为八agent / Eight-agent）」规则，由 `scripts/manifest_check_selftest.py` N21 向隐藏目录下的 marketplace.json 注入旧规模表述，验证 C8 的 rglob 扫描覆盖；本文件不在 SCAN_EXEMPT 内，故此处不逐字复述被禁串以免触发 C8 自检
- **下一步**：
  - 冻结工作树后重跑全部门禁 + 交叉验证复查
  - 保持「改校验器必同步补负例」纪律，防止 mutation 空转假绿复发
- **observability**：
  - 成功率：未采集
  - 平均 tool call：未采集
  - 重试次数：未采集
  - next_actions 字段存在率：未采集

---

## 失败回流规则落盘（v2.2.0 · 确定性闭环）

> v2.1.0 协议 §6 只留了一句「失败回流为 harness 新规则（Hashimoto 模式）」的口头约定，没有落盘为可执行规则；v2.1.1 / v2.1.2 / v2.2.0 的失败与偏差因此没有形成可检索的 lesson 记录，进化回路停摆。本节把该约定固化为**确定性闭环**：触发即写、写完必验、未落地不算修好。

### 触发条件（五类，命中任一即回流）

1. **工具失败**：任一 tool call 返回错误、超时或限流（对齐协议 §6「瞬时 / 模型可恢复」两分类）
2. **撞熔断**：同一 task 失败累计触发 `circuit_breaker`（5 次）→ 自动熔断 + 升级用户
3. **校验器 rc=1**：`manifest_check.py` / `harness_eval.py` / `protocol_check.py` 及各自 selftest 任一返回非零
4. **用户纠偏**：用户明确否定当前产出、要求改方向或补证据
5. **中断续跑发现偏差**：`state_io.py resume` 读回的「上次阶段 / 下一步」与对话记忆或实际产物不一致

### 回流三件套（每条 lesson 必含，对齐协议 §6 与 team-lead「错误路径三件套」）

| 字段 | 含义 | 对齐来源 |
|------|------|---------|
| `root_cause_hint` | 人话版「为什么错」（非 stack trace） | `agent-protocol.md §6` Per-step Verification |
| `safe_retry_instruction` | 什么前提下可重试、不要改什么 | 同上 |
| `explicit_stop_condition` | 什么情况下必须停，不自己硬撞 | 同上；`team-lead.md` 错误路径三件套 |

> 三件套与协议 §6 的 `ERROR` payload（`category` / `detail` / `recovery_action` / `retry_count`）互补：前者写给**下一次会话的人**看，后者写给**当前运行时**用。

### [2026-11-08] / team-lead / lesson：CI 环境性假红（失败回流 · 部署实测抓出）

- **task_id / trace_id**：v2.3.0 部署 / CI run 42419531746（failure）→ 42420262814（success）
- **失败类别**：第 3 类「校验器 rc=1」（CI 实跑抓出；本质是 fixture 依赖外部环境）
- **现象**：本机 12/12 全绿，CI 仅 `Routing eval self-test` 一步红：N12 前置处理 `AssertionError: 本机无默认 MCP 清单，无法构造 R6 fixture: /home/runner/.workbuddy/mcp.json` → selftest 11/12
- **root_cause_hint**：N12 的 fixture 从 `~/.workbuddy/mcp.json` 复制——该路径只在开发机存在。**测试依赖了本机私有的外部环境 = 测试不自包含**，CI 天然必红。「本机全绿」与「CI 全绿」之间隔着环境差异，任何跨机断言必须在 CI 同构环境（空 HOME / 无 env）下预演过才算数。
- **safe_retry_instruction**：fixture 改为**自包含合成清单**（覆盖被测全集的真实 server 名 + 少量干扰项，使「真实名 PASS / 伪造名 FAIL」判据与真实清单等价）；修复后在「空 HOME + 无 env」模拟 CI 态复跑通过再推送。不要用「CI 上跳过 N12」的方式糊——那会让 R6 的负例保护在 CI 里永久失明。
- **explicit_stop_condition**：若修复重推后 CI 仍红且失败点不在本地可复现的用例上，停止自行重试，拉 `gh run view --log-failed` 逐行比对本地与 CI 输出差异，定位环境差异源后再动手。
- **已落地护栏**：`scripts/routing_eval_selftest.py` N12（自包含合成清单，SYNTHETIC_SERVERS 12 项含干扰项）；`git 85e343c`；「空 HOME 模拟 CI 态」纳入交付判据。**附带教训**：tag 曾打在 CI-failure 的 `fd23177` 上——发布纪律：**先看 CI run 结果、再打 tag**（本次已重打至 `85e343c`）。

### [2026-11-09] / team-lead / lesson 组：R1 迭代的 8 条失败模式（失败回流 · 主理人验收抓出）

> 本组是 R1 迭代（2026-11-08 ~ 2026-11-09）积累的 8 条失败模式。每条按「回流三件套」写全，并额外给出**已落地护栏**的文件路径（护栏落地判据要求：每条失败必须指向一个真实存在的校验规则或脚本）。
> 编号与 `docs/harness-iteration-loop.md` §8 失败模式库一一对应（FM-R1-01 ~ FM-R1-08），便于下轮开工时先比对命中，防止重复踩坑。

#### FM-R1-01 · 废弃表述扫描的豁免机制与审计文档结构性互斥

- **失败类别**：第 3 类「校验器 rc=1」
- **现象**：状态文件首次落盘后 manifest 报 63 项通过 / 3 项失败，基线应为 64/64。
- **root_cause_hint**：废弃表述扫描走全库递归扫描，豁免仅靠校验器源码里硬编码的文件名白名单。任何**新增**审计类文档只要抄录历史缺陷术语名即被判红——每加一份审计文档都得改校验器源码，白名单不可持续。
- **safe_retry_instruction**：豁免机制改**声明式**——白名单保留作兼容，另加「文件头声明式标记」双路径（标记窗口限定在前 3 行 ∩ 前 512 字节，避免正文任意位置冒出标记就整文件放行）；状态文件改引用式登记、不转录旧术语字面量。修完配注入式负例证明未标记文件仍被拦截。
- **explicit_stop_condition**：若声明式标记被用作「整文件放行」的滥用（标记出现在正文而非文件头），停止自行放宽窗口，回到「按文件头窗口 + 逐条负例」重新设计。
- **已落地护栏**：`scripts/manifest_check.py`（C8 声明式豁免双路径 + 头窗口常量）；`scripts/manifest_check_selftest.py`（N22/N23 注入式负例）。

#### FM-R1-02 · Bash grep 假阴性

- **失败类别**：第 1 类「工具失败」（工具误用）
- **现象**：对含中文或正则元字符的 pattern 做 Bash `grep`，多组检索全部返回空，但文件确有命中——若轻信会得出「文件无此内容」的错误结论。
- **root_cause_hint**：该沙箱环境下 Bash `grep` 对中文/元字符 pattern 存在假阴性，返回空**不等于**内容不存在。这是工具行为问题，不是数据问题。
- **safe_retry_instruction**：检索一律用专用检索工具，不用 Bash grep。Bash grep 返回空时必须用第二种工具交叉验证后才可下「不存在」结论。不要因为 grep 空就改写文档或删代码。
- **explicit_stop_condition**：若同一 pattern 在专用检索工具下也无命中，才可下「不存在」结论；两种工具都空才算证据充分。
- **已落地护栏**：本组 8 条失败模式与 R1 状态文件的核验方式（详见 `docs/harness-iteration-loop.md` §8）；本轮累计复发 10 次，已固化为纪律。

#### FM-R1-03 · 隔离测试被祖先目录同名副本污染

- **失败类别**：第 1 类「工具失败」（测试前置条件缺失）
- **现象**：vendor 兜底路径的隔离测试实际命中的是联邦来源，测试目标根本没被测到。
- **root_cause_hint**：兼容 shim 从包根父目录起逐级向上查找联邦真源；隔离测试目录放在 `/tmp` 下时，被 `/tmp/shared-core/`（他包历史拷贝）抢先命中。**路径选择本身就是测试前置条件**，不声明就会被环境污染。
- **safe_retry_instruction**：隔离测试必须在**祖先链无同名目录**的路径下构造，并断言调试输出打印的来源确实是兜底路径而非联邦；同时给 shim 加「命中即校验哈希」硬校验，不一致即拒绝加载。
- **explicit_stop_condition**：若测试目录的祖先链存在同名目录，停止执行该测试并换路径，不要用「反正结果一样」糊过去。
- **已落地护栏**：`scripts/assemble_spawn_prompt.py`（命中 core 即比对 `vendor/shared-core/VENDOR.json` 登记的 sha256，不一致 exit 4 拒绝加载）；`tests/test_vendor_core.py`（V5/V6 冒烟）。

#### FM-R1-04 · 负例验收前提不成立

- **失败类别**：第 3 类「校验器 rc=1」（验证方法错误）
- **现象**：去掉防护后门禁仍不红，一度被误判为「门禁失效」。
- **root_cause_hint**：该验收项的前提是「被测物当前确实含违规内容」，但前一个批次已把它改成引用式登记，实测对扫描规则的命中数为 0——去掉防护自然不会变红。**验收前提不成立时，结论无效**。
- **safe_retry_instruction**：负例验收必须先确认被测物当前确实含违规内容（命中数 > 0），再做「去掉防护应变红」的双向测试；前提不成立则改用真实注入构造违规态。
- **explicit_stop_condition**：若命中数为 0，停止「去掉防护」这类破坏性验收，改为先构造违规态再测。
- **已落地护栏**：`scripts/manifest_check_selftest.py`（注入式负例：先注入违规、再断言 rc 翻转 + 命中预期检查项文案）。

#### FM-R1-05 · 注入锚点未命中生效分支

- **失败类别**：第 3 类「校验器 rc=1」（负例设计错误）
- **现象**：负例注入后校验器仍返回成功，负例形同虚设——「一直绿」与「真在检查」无法区分。
- **root_cause_hint**：注入位置落在了**未生效的分支**上：被测反例本身由另一个分支抓出，破坏未生效的分支完全不影响检出结果。**「锚点唯一命中」是必要条件，不是充分条件**；锚点会随代码演进失效（断行位置一变就命中 0 次，破坏静默空转）。
- **safe_retry_instruction**：注入锚点必须指向真正生效的分支；注入后必须确认退出码**真的翻转**，不能只看用例显示 PASS。锚点构造前先读目标代码的真实文本形态（断行位置）。
- **explicit_stop_condition**：若注入后退出码未翻转，不得记为「负例通过」——先查锚点是否命中、生效分支是否被破坏，再重做。
- **已落地护栏**：`skills/research-orchestration-workflow/scripts/protocol_check_selftest.py`、`scripts/manifest_check_selftest.py`（注入后同时断言退出码翻转 + 命中预期检查项文案 + 旧串消失新串出现）。

#### FM-R1-06 · 负例自带无关失败原因

- **失败类别**：第 3 类「校验器 rc=1」（负例设计错误）
- **现象**：无论被破坏的规则是否生效都能判「检出」，属假绿。
- **root_cause_hint**：反例自带了另一个失败原因（例如覆盖不完整），使得「被破坏的那条规则」是否为唯一失败原因无从判断——两个失败原因混在一条反例里。
- **safe_retry_instruction**：**一条负例只承载一个失败维度**；反例必须让「被破坏的那条规则」成为**唯一**的失败原因。两个维度正交时才能证明该规则被检出。
- **explicit_stop_condition**：若反例存在多个可能的失败原因，停止使用该反例，先把无关维度消掉。
- **已落地护栏**：`scripts/manifest_check_selftest.py`、`skills/research-orchestration-workflow/scripts/protocol_check_selftest.py`（负例设计两条硬纪律已写入 README「门禁体系现状」节与 `docs/harness-iteration-loop.md`）。

#### FM-R1-07 · 整批门禁被超时截断

- **失败类别**：第 1 类「工具失败」（长任务未隔离执行）
- **现象**：多套门禁串在一条命令里跑，整批被沙箱以 SIGTERM 截断（退出码 137），**后序门禁根本没执行**——只看整体退出码会误判为「全绿」。
- **root_cause_hint**：单条命令串行执行 + 长耗时 selftest（每条负例在临时目录复制整个包体）+ 沙箱超时上限，三者叠加。
- **safe_retry_instruction**：**门禁必须逐条独立执行并逐条断言退出码**，禁止把多套门禁串成一条命令后只看整体退出码；长耗时门禁单独跑并显式设超时。
- **explicit_stop_condition**：遇到退出码 137 或 124，停止解读结果——先拆成单条重跑，确认哪些门禁**实际执行过**。
- **已落地护栏**：`docs/harness-iteration-loop.md` §5.1（12 套门禁逐条独立取 rc 的验收证据表）；`.github/workflows/validate.yml`（timeout 提到 25 分钟）。

#### FM-R1-08 · 批量执行门禁的辅助函数参数封装错误

- **失败类别**：第 1 类「工具失败」（工具误用）
- **现象**：所有门禁一次性全部返回 127，表面上像「整套门禁都坏了」。
- **root_cause_hint**：辅助函数把整条命令当成单个带引号的字符串参数传入，`"$@"` 展开成一个整体参数，shell 于是试图执行一个名为「python3 脚本路径」的单条命令。**真实原因是参数封装错误，不是门禁失效**。
- **safe_retry_instruction**：批量执行门禁的辅助函数必须先 `shift` 掉 tag 参数再展开命令。**退出码 127 一律先按「命令/路径不存在」排查**，不要直接归因为门禁坏。同理，**退出码 2 也不等于「校验失败」**（可能是解释器报「文件不存在」）——退出码不是 0/1 时一律先查命令与路径。
- **explicit_stop_condition**：若退出码为 127 / 2 / 126，停止怀疑门禁实现，先核对脚本真实文件名与调用方式（本轮曾把 `harness_eval.py` / `routing_eval.py` / `tests/test_vendor_core.py` 误记为 `*_check.py`）。
- **已落地护栏**：`docs/harness-iteration-loop.md` §5.1（负向实锤表）与 §8（失败模式库）。

#### R1 失败模式速查索引（下轮开工先比对命中）

| 编号 | 失败节点 | 预防动作关键词 |
|---|---|---|
| FM-R1-01 | 审计文档落盘 → 废弃表述扫描假红 | 豁免声明化；引用式登记，不转录旧术语 |
| FM-R1-02 | 检索命令返回空 | 专用检索工具；两种工具都空才算证据 |
| FM-R1-03 | 隔离测试路径被污染 | 祖先链无同名目录；命中即校验哈希 |
| FM-R1-04 | 去标记后门禁仍不红 | 先确认命中数 > 0；否则改用真实注入 |
| FM-R1-05 | 注入后退出码未翻转 | 锚点指向生效分支；必须确认退出码翻转 |
| FM-R1-06 | 反例自带无关失败原因 | 一条负例只承载一个失败维度 |
| FM-R1-07 | 整批门禁被截断（137） | 逐条独立执行并逐条断言退出码 |
| FM-R1-08 | 全套门禁返回 127 / 2 | 退出码非 0/1 先查命令与路径 |
| FM-R2-01 | 资产内文档与自身版本矛盾 | 先修文档再打 tag；资产用 `git archive <tag>` 打包 |
| FM-R2-02 | 文档修正落在 tag 之后 | 打 tag 前核对「将被打包的文档」已在 CI 绿 commit 内 |
| FM-R2-03 | CHANGELOG「代码化」掩盖告警/终态语义分层 | 行为类描述必须区分「检测到」与「阻止」；破坏实验实测后再写 |
| FM-R2-04 | 负例按大项配对 → 重复负例与分支盲区并存 | 每条负例对应一个可独立失效的分支；定期跑覆盖矩阵差集 |
| FM-R2-05 | SKIP 容错让副本态负例假绿；YAML heredoc 顶格崩解析 | 负例强制非 SKIP 路径（整包副本）；heredoc 保持块缩进 + yaml.safe_load 验证 |
| FM-R2-06 | 负例改错数据载体 → rc 未翻转；无关门禁抢先拦截致假检出 | 先读实现定位真实载体；rc 翻转 + 失败原因归属被测门禁才算有效 |

### [2026-11-09] / team-lead / lesson 组：发布介质自洽性 2 条失败模式（v2.4.1 补丁的根因）

#### FM-R2-01 · 失败类别：第 4 类「流程纪律违反」

- **现象**：v2.4.0 的 release 资产 `rot-v2.4.0.tar.gz` 已补齐，但 tarball 内的 README 仍写「方式 3 只能安装到 v2.1.2」——**介质内容与介质自身的文档互相矛盾**。用户下载资产后按包内文档操作会指向旧版本。
- **root_cause_hint**：修正「安装方式 3」链接的 commit `2f2b016` 发生在打 tag `v2.4.0` **之后**（tag 指向 `90a1c36`）。资产用 `git archive` 从 tag 打包时，忠实复制了 tag 时刻的旧文档——**打包机制本身是正确的，错的是打 tag 的时机**。另有一条被明确否决的「修复」路径：重打 v2.4.0 资产。那会造成「资产内容 ≠ tag 内容」，比文档过期更严重。
- **safe_retry_instruction**：文档类修正必须在**打 tag 之前**完成并进 CI 绿 commit。若已发布，**不改历史 tag、不重打历史资产**，走补丁版（本次为 v2.4.1）。打包一律用 `git archive <tag>`（而非工作树或分支 HEAD），打完**必须解包核对** README 版本行与关键链接。
- **explicit_stop_condition**：若解包后 README 的版本行 ≠ 预期版本，或包内链接指向的 release ≠ 本次 release，**禁止上传资产**。
- **已落地护栏**：`docs/harness-iteration-loop.md` §9（发布契约新增 3 条）+ §10.3.1（发布纪律补录）+ §10.2 第 9 项；`CHANGELOG.md` v2.4.1 段；`README.md` v2.4.1 版本历史条目。

#### FM-R2-02 · 失败类别：第 4 类「流程纪律违反」

- **现象**：修正类 commit 单独走一轮「commit → push → CI → 同步镜像」，看起来一切正常，但**已打 tag 的资产不会被这次修正覆盖**——发布链路的两个阶段（打 tag 前 / 打 tag 后）被当成了同一条路径处理。
- **root_cause_hint**：把「修正文档」和「发布资产」当成两个独立事件，忽略了**资产是 tag 的派生物**这一约束。凡是会进入资产的文档（README / CHANGELOG），其修正与打包之间必须由 tag 隔断；tag 之前的修正会进资产，tag 之后的修正不会。
- **safe_retry_instruction**：执行顺序固定为 **修文档 → 升版 → commit → push → 等 CI 绿 → 打 tag → `git archive <tag>` 打包 → 解包核对 → 建 release → 上传 → 同步镜像**。任何「先打 tag 后改文档」的路径都必须改为补丁版重发。
- **explicit_stop_condition**：若本次发布包含资产（tarball / zip），而文档修正发生在打 tag 之后 → **本轮资产不可发布**，必须换补丁版。
- **已落地护栏**：`docs/harness-iteration-loop.md` §9 与 §10.3.1 的执行顺序条款；`LEARNING.md` 的 FM-R2 速查索引 2 行。

### [2026-11-09] / team-lead / lesson 组：R2 覆盖矩阵审计的 3 条失败模式（16 组破坏实验实锤）

#### FM-R2-03 · 失败类别：第 5 类「文档与实现脱节」

- **现象**：v2.4.0 CHANGELOG 写「编排层硬上限（30 轮/1800s/200000 token/熔断 5 次）代码化」，实测 `init --max-turns 1` 后连续 `advance` 两次均 rc=0 放行（turn 2/1）——「代码化」被读成「真截断」，实际 turns/tokens 是「告警」语义。
- **root_cause_hint**：CHANGELOG 措辞从 state_io.py docstring 的语义分层表（告警 vs 终态）压缩成一句话时丢失了关键限定。读者（包括主理人自己）会按「硬上限」字面理解行为。语义类功能写文档时，「有这个机制」和「机制触发时发生什么」必须分开写。
- **safe_retry_instruction**：写行为类 CHANGELOG 必须区分「检测到违规」（告警/记录）与「阻止继续」（拒绝/终态）两种语义；或直接引用实现文件的语义表而不是另写摘要。
- **explicit_stop_condition**：描述任何门禁/上限前，先用破坏实验实测触发行为（超限一次看 rc 与 status），禁止凭 docstring 转写。
- **已落地护栏**：`tests/test_state_ceilings.py`（4 用例锁定语义分层）；`CHANGELOG.md` v2.5.0 Fixed 段；`README.md` state_io.py 注释行；`docs/harness-iteration-loop.md` §10.2 第 10 项。

#### FM-R2-04 · 失败类别：第 2 类「门禁覆盖缺口」

- **现象**：16 组破坏实验实锤三类覆盖缺口——①流水线 producers 注入幽灵成员 ID 后 integration 仍 rc=0（断言只查「引用是否在上游参与」不查「是否真实成员」）；②protocol selftest N6/N10 锚点逐字相同（13 条里 1 条纯重复，「两条负例」的计数给人虚假安心）；③C8 的 13 条规则仅 5 条有负例，7 条规则的正则被误改无人知晓。
- **root_cause_hint**：负例设计时按「校验器大项」（C13/H1/R1）配负例，没有下沉到「分支级」；跨文件引用类断言（流水线成员 vs agents/*.md）在两处独立演进时无人对齐。**每条负例必须对应一个「会独立失效的分支」**，大项级配对会产生重复负例和真盲区并存。
- **safe_retry_instruction**：新增断言时同步回答「哪条负例会在该断言被破坏时变红？」——答不出就不许合入；定期跑覆盖矩阵审计（列出全部断言分支 × 全部负例做差集）；发现重复负例立即重构为互补维度（本次 N10 改为 list 形态分支）。
- **explicit_stop_condition**：若覆盖矩阵差集 >0 且涉及「rc 判定分支」（非纯文案），必须补负例后才能发布；禁止以「低优先」延后 rc 分支的盲区。
- **已落地护栏**：`protocol_check.py` 集成段真值源断言（10 项）+ selftest N11（整包副本态）；selftest N10 重构；`manifest_check_selftest.py` N27（七规则批量）+ N28/N29/N30（C13 分支）；`docs/harness-iteration-loop.md` §10.2 第 11–16 项。

#### FM-R2-05 · 失败类别：第 1 类「工具失败」（跨副本语义）

- **现象**：给 protocol selftest 补 N11 时，第一版注入在「单文件副本态」静默失效——新断言读 agents/*.md 真值源，副本里没有 agents/ 目录 → 断言按设计 SKIP 放行 → 注入了破坏但 rc 仍 0，负例假绿。同轮 CI 的 YAML heredoc 首版把 Python 代码顶格写进 `run: |` 块，YAML 解析直接崩。
- **root_cause_hint**：①「SKIP 不误报」的容错设计与「负例必须红」的测试目标在副本态互相冲突——容错路径在负例场景下变成了盲区；②YAML 块标量内 heredoc 的每一行都受块缩进约束，顶格行会被 YAML 解析器当成新键。
- **safe_retry_instruction**：给校验器加 SKIP 分支时必须同步问「负例如何强制走非 SKIP 路径？」——N11 的解法是整包副本（copytree 整个包再注入）；CI 内嵌 Python 一律用 `python3 - args <<'EOF'` 且 heredoc 内容保持块缩进，写入后必跑 `yaml.safe_load` 验证。
- **explicit_stop_condition**：负例跑完后 rc 未翻转且输出含 SKIP 字样 → 该负例无效，禁止计为通过；CI YAML 修改后未经 `yaml.safe_load` 验证禁止 commit。
- **已落地护栏**：`protocol_check_selftest.py` run_case 的 whole_pkg 分支 + N11；`.github/workflows/validate.yml` heredoc 缩进版（本地 `yaml.safe_load` + 熔断段全链路实测通过）。

#### FM-R2-06 · 失败类别：第 2 类「门禁覆盖缺口」（负例数据载体误解）

- **现象**：R2 收口的独立负向实锤中，「C13 声明位互换」负例**首版构造 rc=0**（应为 1）——连续两次构造都没让 rc 翻转，才暴露问题。第一版把「声明位」理解为 `agents[]` 数组中的位置，只交换了两项的先后顺序。
- **root_cause_hint**：C13 是**集合**一致性门禁（比的是成员 ID 集合，不比数组顺序），真实的主理人声明位在 `members[].role == "lead"`，与数组位置无关。改数组顺序 → C13 判绿；更隐蔽的是 C2「双 manifest 字段对等」会因 `agents` 字段顺序不同而**抢先报红**——表面看 rc=1，实际失败原因根本不是 C13。若只看 rc 不看失败原因归属，会误以为「C13 已被证明能检出」。
- **safe_retry_instruction**：构造负例前先读实现，确认被破坏的那条规则**实际读的是哪个字段/集合/位置**，再动手改那个载体。验收时同时看两件事：① rc 是否翻转；② 失败信息是否**归属于被测门禁**（如 C13 的报错前缀是「C13 …」）。被无关门禁抢先拦截的负例一律作废重做。
- **explicit_stop_condition**：负例跑完 rc 未翻转 → 负例无效；若 rc 翻转但失败原因归属其他门禁 → **同样无效**。两种情况都不许计为通过。
- **已落地护栏**：`docs/harness-iteration-loop.md` §5.2 负例 6（记录首版无效 + 修正后的正确构造）、§8 FM-R2-06、§10.3.2（负例验收纪律补录 3 条）。

### 写入位置与责任人

- **位置**：在本文件「## Task 记录」区追加一条 `lesson` 类记录，沿用四段模板，且额外必含 5 个字段：`task_id` / `trace_id` / 失败类别（五类之一）/ 根因（即 `root_cause_hint`）/ **已落地护栏的文件路径**
- **同步**：必要时调用 `python3 skills/research-orchestration-workflow/scripts/memory_log.py --type lesson --trace-id <trace_id> --note "<根因 + 护栏路径>"`，写入跨会话持久记忆层
- **责任人**：**成员只读，仅主理人（team-lead）写入**。成员命中触发条件时，把三件套随结果回传主理人，由主理人统一落盘，避免多头写入把本文件写散

### 护栏落地判据（防「口头已修复」）

- 每条失败**必须指向一个已存在的校验规则或脚本**（如 `manifest_check.py` 的 C12、`harness_eval.py` 的 H9、`manifest_check_selftest.py` 的某条负例），并把该路径写进 lesson
- 若一时无对应规则，状态标为 **「未闭环」**，并在「下一步」里写明「补哪条规则 / 哪个脚本」；**不得写「已修复」**
- 判据一句话：`grep` 能在本文件找到该 lesson，且该路径在仓库真实存在、`rc` 可复跑，才算闭环

### 验证方式（下次会话开工必跑）

1. 跑 `python3 skills/research-orchestration-workflow/scripts/state_io.py resume --task-id <task_id> --workspace <path>` 读回断点
2. 跑全部校验脚本：`manifest_check.py` / `manifest_check_selftest.py` / `harness_eval.py` / `harness_eval_selftest.py` / `protocol_check.py`，确认基线未破
3. `grep -n "<trace_id>" skills/research-orchestration-workflow/references/LEARNING.md` 确认该条 `lesson` 记录已落盘，且含 task_id / trace_id / 失败类别 / 根因 / 护栏路径 5 字段
4. 若某条 lesson 仍标「未闭环」，优先补规则再继续新 task，不让欠账跨会话累积

---

## 跨会话连续性协议（Ralph Loop）

每个新 session 启动后：
1. **读取**本文件（git log + LEARNING.md）
2. **识别**最高优先级未完成 task（按时间倒序 + "下一步"标签）
3. **校验**跑全部校验脚本（manifest_check / harness_eval / protocol_check 及各自 selftest）确认基线未破
4. **处理**该 task
5. **提交**到 git
6. **追加**新一段 task 记录到本文件
7. **循环**直到 30 turns / 30min / 200k tokens 任一触发 → compact / circuit breaker