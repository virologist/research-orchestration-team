# Changelog

所有重要变更按版本倒序记录。格式基于 [Keep a Changelog](https://keepachangelog.com/)。

## [2.5.5] - 2026-11-10

> R7 状态文件健壮性审计版。主题：**状态文件半损坏时会怎样？检查点编号与阶段序号绑不绑得住？崩溃后会不会留垃圾？**
> 11 组状态文件实验，实锤 2 个 P0（半损坏状态文件 → 裸 Traceback / 缺 status 时假绿）
> + 3 个 P1（触顶文案宣称「熔断」实为告警 / 检查点编号与阶段序号解耦 / SIGKILL 孤儿 tmp），
> 排除 3 组假阳性（vendor `except` 为联邦真源有意回退、`cp-008` 硬编码为脆性非缺陷、
> turns/tokens 不熔断为 registry 既定告警层）。R6 已把「运行时序」查完，R7 转向
> **状态文件本身的健壮性**与**跨层一致性**。

### Fixed

- **半损坏状态文件 → 裸 Traceback（R7 P0-1，E7）**：`load_state` 原先只做 JSON 解析层
  校验。文件是**合法 JSON 但缺关键字段**时（被外部改写 / 旧版本状态文件 / 部分写盘后
  编辑），下游子命令直接 `state["phase"]` / `state["status"]` → 裸 `KeyError` Traceback，
  实测 **13 组子命令 × 损坏形态组合**全部命中，违反「业务报错必须有可读文案、无裸
  Traceback」的既有契约。修复：`load_state` 增加**结构层校验**（`_validate_state_shape`）——
  必需字段缺失 / 类型不对 / 取值非法（`status` ∉ {running, done, aborted}、
  `phase` ∉ PHASES）一律 fail fast 退出码 **3**，且失败信息**逐条指名具体字段**。
  处置口径与 JSON 损坏同级：**不静默重建**（重建等于凭空替主理人编造任务状态）。
- **缺 status 时 budget / fail 假绿（R7 P0-2，E8）**：状态文件缺 `status` 时，
  `budget` / `fail` **rc=0 放行**，把「未知状态」静默当成 `running` 处理并继续写盘——
  等于凭空替主理人断言了任务状态。修复：随 P0-1 的结构校验一并拦截（rc=3）。
- **budget 触顶文案宣称「熔断」实为告警（R7 P1-1，E9）**：registry §Loop 终止硬上限
  明确把 `turns` / `tokens` 定为**告警层**（主理人语义裁量），只有 `max_time` /
  `failures` 才是**终态熔断层**。原文案写「按协议熔断」会让调用方误以为 `status` 已变
  `aborted`、后续推进会被拒，实际 `status` 仍是 `running`、`advance` 照常放行——文案与
  行为脱节（FM-R2-03 同族复发：语义分层在压缩成一句话时丢失关键限定）。修复：文案改为
  「⚠️ 预算触顶（告警层，不自动熔断）→ 请主理人裁量是否收尾或调预算」。
- **检查点编号与阶段序号解耦（R7 P1-2，E3，三处）**：协议 §3 约定「检查点编号 =
  阶段序号」（cp-001=FREEZE、cp-002=IDENTIFY…），而 `protocol_check` 的 HANDOFF 覆盖
  校验正按该约定动态生成 cp 清单。原实现只校验**形态**（`cp-[0-9]{3,}`），不校验编号
  一致性，于是：① 编号可乱写（第 1 个阶段记成 cp-007）；② 同一编号可被复用
  （`checkpoints` 里出现两条 `state://cp-007`）；③ marker 文件因 `if not marker.exists()`
  永不重写，第 2 次推进的 phase/ts 永不落盘，指针内容与状态文件脱节。三者都会破坏跨层
  校验。修复：`advance` 强制编号 = 本次推进后的 `turn` 对应编号，不符 rc=1 拒绝；同编号
  复用 rc=1 拒绝；marker 改为每次推进都重写，保证指针元信息与状态文件同步。
- **SIGKILL 崩溃留下孤儿 tmp（R7 P1-3，E1 / E5）**：`_atomic_write` 的 tmp 名带 PID 以
  隔离并发写者；进程在 `write_text` 与 `os.replace` 之间被杀，就留下
  `_state.json.tmp.<pid>`——实测崩溃后**永远不会被清理**，反复崩溃即无界堆积的磁盘泄漏
  （已确认无下游代码 glob 该目录，属空间泄漏而非正确性缺陷）。修复：写盘前清理**已确认
  孤儿**的 tmp（`os.kill(pid, 0)` 探测持有进程已死才删），当前进程自己的 tmp 与存活进程
  持有的 tmp 一律跳过；写盘异常时主动回收自己的 tmp。

### Added

- `tests/test_state_file_robustness.py`（**12** 条）：R1 缺 status → budget 拒绝 rc=3 /
  R2 缺 phase → resume 拒绝 / R3 缺 task_id → finish 拒绝 / R4 缺 turn → advance 拒绝 /
  R5 空对象 → init 拒绝 / R6 status 取值非法 / R7 phase 取值非法 / R8 turn 为 bool
  （bool 不算 int）/ R9 结构损坏被拒后状态文件逐字节未变（不静默重建）/ R10 budget 触顶
  文案表达「告警层」/ R11 检查点编号必须等于阶段序号（乱写与复用均拒 + marker 与状态
  一致）/ R12 孤儿 tmp 被清理。每条独立临时目录，判定同时断言 rc、失败文案归属与
  无裸 Traceback（FM-R2-06 纪律）。
- CI 新增 `State IO file robustness + checkpoint consistency (R7)` step；门禁 step
  **17 → 18**。

### Regression evidence（v2.5.5 部署前实测，16 套门禁逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` / `_selftest.py` | 74/74 ✅ / 30/30 ✅ |
| `harness_eval.py` / `_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 6/6 ✅ |
| `test_phase_normalization.py` | 26/26 ✅ |
| `tests/test_state_ceilings.py` | 4/4 ✅ |
| `tests/test_state_io_guards.py` | 10/10 ✅ |
| `tests/test_lead_source_of_truth.py` | 6/6 ✅ |
| `tests/test_state_runtime_sequencing.py` | 8/8 ✅ |
| `tests/test_state_file_robustness.py`（新增） | **12/12** ✅ |
| `protocol_check.py` envelope / conflict / integration | 37/37(v2.4)+12/12(legacy) ✅ / 5/5 ✅ / 10/10+8/8 ✅ |
| `protocol_check_selftest.py` | 14/14 ✅ |

注入破坏实锤（4 组，证明锁定真的会红）：N1 短路 `_validate_state_shape` 调用 → R1–R9
精确变红（9 条，R10–R12 不受影响，维度隔离正确）；N2 短路 cp 编号一致性校验 → 仅 R11
变红；N3 短路孤儿 tmp 清理 → 仅 R12 变红；N4 把触顶文案改回「熔断」→ 仅 R10 变红。
每组注入后还原校验 rc=0。

### Known limitations（设计语义 · 登记备查，非缺陷）

- **`init` / `budget` 仍可主动放宽熔断阈值**（台账 §10.2 #22）：registry 明确授权这两个
  子命令覆写上限，`budget --max-failures 99` 是合法路径。R6 已封堵 `fail` 的逐次抬高
  绕过路径，但要杜绝「主动放宽」属 registry 语义变更，需另开轮次裁决，**不在 R7 范围内**。
- **协议层与落盘状态无跨层校验入口**（台账 §10.5 第 3 项）：`state_io.py` 管落盘、
  协议 §2 管信封，`turn` / `phase` / `status` 三者在两层各自表述，漂移无门禁。R7 Phase A
  实测确认：信封 `phase=EXECUTE` / `task_id` 与落盘状态完全不符时，协议校验返回**空失败
  列表**（rc=0）。补这道跨层断言需要定义「信封与状态的绑定契约」（哪个信封应匹配哪个
  task_id、phase 如何对齐），属设计裁决，**不在 R7 范围内**，留待 R8。
- **`turns` / `tokens` 触顶不熔断**：registry 既定告警层语义（FM-R2-03 / §10.2 #3 /
  #10 已登记），非缺陷。本轮只修正文案表述使其与语义一致。

## [2.5.4] - 2026-11-10

> R6 运行时序审计版。主题：**终态之后写操作还会发生什么？观测数据会不会被静默冲掉？**
> 13 组运行时序实验，实锤 2 个 P0（终态污染 / 熔断可绕过）+ 2 个 P1（观测数据静默丢失），
> 其余 7 组验证为设计正确。R5 已把「断言组合态」查完，R6 转向 §10.5 里 R5 未覆盖的
> **运行时序**（终态后的写操作、并发、重入、中断恢复）与**观测数据一致性**。

### Fixed

- **终态污染（R6 P0-1，E1 + E2）**：`resume` / `budget` 的 `max_time` 改写守卫原先是
  `status != aborted`，**漏了 `done`**；`cmd_budget` 更严重——它**没有任何终态守卫**
  （`advance` / `fail` 都有）。后果：任务 `finish` 成功后，只要事后超过 `max_time`，
  调一次 `resume` 或 `budget` 就会把 `status` 从 `done` 改写成 `aborted`——**已完成的
  任务被翻成失败**，且 `metrics.success_rate=1` 与 `status=aborted` 自相矛盾。
  修复：新增 `_is_terminal(state)` 统一判定 `status ∈ {done, aborted}`；`resume` /
  `budget` 的超时改写一律要求「非终态」；`budget` 入口补齐终态守卫（对终态任务
  rc=1 拒绝，状态文件完全不变）。
- **熔断可被绕过（R6 P0-2，E8）**：`fail` 子命令的 `--max-failures` 原先能**抬高**
  已落盘阈值，于是「每次 fail 都自带一个更大的阈值」能让熔断彻底失效——实测 8 次
  失败后 `status` 仍是 `running`。registry 只授权 `init` / `budget` 覆写上限，`fail`
  的逐次抬高等于给熔断开了后门。修复：改为**只允许收紧**（阈值调低让熔断更早触发），
  放宽一律忽略并告警。
- **观测数据静默丢失（R6 P1-1，E9）**：`advance` 里 `budget.turns_used = state["turn"]`
  是**覆盖**而非累加——主理人用 `budget` 上报的观测值（如 `turns=25` / `tokens=42000`）
  会被下一次 `advance` 静默冲回 `turn` 的小数值。修复：改为 `max(已落盘值, turn)`——
  `turn` 是结构化事实（已推进阶段数），主理人上报值可能更大（编排轮次 ≠ 阶段数），
  两者不冲突，取 max 既保住观测值又不破坏未上报时的递增语义。

### Added

- `tests/test_state_runtime_sequencing.py`（**8** 条）：T1 done 终态经超时 resume 不被
  翻案 / T2 done 终态调 budget 被拒且不改写 / T3 budget 被拒后状态文件完全未变 /
  T4 fail 抬高阈值被忽略且熔断照常触发 / T5 fail 收紧阈值被接受（防止修复做成「一律
  忽略」）/ T6 advance 不冲掉上报的观测值 / T7 未上报时 turns_used 随 turn 递增
  （对照组）/ T8 aborted 终态调 budget 被拒。每条独立临时目录，判定同时断言 rc 与
  失败文案归属（FM-R2-06 纪律）。
- CI 新增 `State IO runtime sequencing + terminal state (R6)` step；门禁 step **16 → 17**。

### Regression evidence（v2.5.4 部署前实测，16 套门禁逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` / `_selftest.py` | 74/74 ✅ / 30/30 ✅ |
| `harness_eval.py` / `_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 6/6 ✅ |
| `test_phase_normalization.py` | 26/26 ✅ |
| `tests/test_state_ceilings.py` | 4/4 ✅ |
| `tests/test_state_io_guards.py` | 10/10 ✅ |
| `tests/test_lead_source_of_truth.py` | 6/6 ✅ |
| `tests/test_state_runtime_sequencing.py`（新增） | **8/8** ✅ |
| `protocol_check.py` envelope / conflict / integration | 37/37(v2.4)+12/12(legacy) ✅ / 5/5 ✅ / 10/10+8/8 ✅ |
| `protocol_check_selftest.py` | 14/14 ✅ |

运行时序实验台账（13 组，其余 7 组为设计正确性验证）：done×超时resume（**实锤并
修复**）/ done×budget（**实锤并修复**）/ fail×抬高阈值（**实锤并修复**）/
advance×budget上报（**实锤并修复**）/ 8 路并发 advance 无丢更新 ✅ /
checkpoint turn 序列无重复 ✅ / resume 续跑点正确 ✅ / init 幂等不覆盖已有状态 ✅ /
JSON 损坏五子命令全 fail-fast ✅ / 旧版本状态文件 budget 键补齐 ✅ /
fail 不带覆写的熔断对照组正常触发 ✅ / 熔断后 budget 拒绝（T8）✅。
台账详情见 `docs/harness-iteration-loop.md` §5.5。

### Known limitations

- 熔断阈值仍可由 `init` / `budget` **显式放宽**（如 `budget --max-failures 99`）——
  这是 registry 明确授权的上限写入口，R6 只封堵了 `fail` 的逐次抬高绕过路径。
  若需杜绝「主动放宽」，属 registry 语义变更，需另开轮次裁决。

## [2.5.3] - 2026-11-10

> R5 组合态盲区修复版。主题：**两条各自成立的断言，组合起来是否仍成立？**
> 11 组组合态实验，实锤 1 个 P1（C12×C13 主理人双重事实源——「主理人换人」
> 可静默通过全部 74 项门禁），其余 10 组验证为设计正确。

### Fixed

- **主理人双重事实源（R5-E4，P1）**：manifest 内 `agentName`（C12 读取）与
  `teamInfo.leadAgent` + `members[].role == "lead"` 声明位（C13 读取）此前是
  两个独立事实源。三处同步漂移到同一普通成员时：C2 对等绿（双侧同步）、
  C13 内部自洽绿（leadAgent == 声明位）、C12 绿（读 agentName，若 settings
  也同步即绿）——「主理人换人」静默通过，合法换主理人与劫持无从区分。
  修复：**C12 以 C13 的声明位为唯一事实源**（`members[].role == "lead"` →
  谁，settings 与校验就以谁为准）；`agentName` 降级为兼容字段——存在但
  ≠ 声明位即红（不再允许第二个事实源）。无声明位的旧版 manifest 回退旧
  口径（leadAgent/agentName）保持兼容。

### Added

- `tests/test_lead_source_of_truth.py`（**6** 条）：M1 基线 rc=0 / M2 事实源
  整体迁移（agentName+leadAgent+role+settings 全同步）= 合法换主理人放行 /
  M3 agentName 单独漂移红（归属 C12 新断言）/ M4 leadAgent 漂移红（归属
  C13 声明位断言）/ M5 role 声明位漂移红 / M6 settings 跟随声明位放行。
  每条独立整包副本注入，判定同时断言 rc 与失败文案归属（FM-R2-06 纪律）。
- CI 新增 `Lead source-of-truth consistency (R5 E4)` step；门禁 step **15 → 16**。

### Regression evidence（v2.5.3 部署前实测，15 套门禁逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` / `_selftest.py` | 74/74 ✅ / 30/30 ✅ |
| `harness_eval.py` / `_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 6/6 ✅ |
| `test_phase_normalization.py` | 26/26 ✅ |
| `tests/test_state_ceilings.py` | 4/4 ✅ |
| `tests/test_state_io_guards.py` | 10/10 ✅ |
| `tests/test_lead_source_of_truth.py`（新增） | **6/6** ✅ |
| `protocol_check.py` envelope / conflict / integration | 37/37(v2.4)+12/12(legacy) ✅ / 5/5 ✅ / 10/10+8/8 ✅ |
| `protocol_check_selftest.py` | 14/14 ✅ |

组合态实验台账（11 组，其余 10 组为设计正确性验证）：熔断×force（终态压过
特许）✅ / 熔断×fail 再登记（拒绝）✅ / 熔断×init 幂等重入（保留 aborted）✅ /
done×resume（正确提示无需续跑）✅ / turns 告警×finish（done 正常）✅ /
C2×agents 顺序（顺序敏感对等，双侧一致即绿）✅ / C13×memberAgents 倒序
（集合语义顺序无关）✅ / requires 幽灵成员（依赖断言红）✅ / requires 真实
成员未上游参与（依赖断言红）✅ / 重复回引探针（缺失正确检出）✅ / **E4 双重
事实源（实锤并修复）**。台账详情见 `docs/harness-iteration-loop.md` §5.4。

## [2.5.2] - 2026-11-10

> R4 遗留双闭环版：cp 检查点清单动态化（遗留 #4）+ selftest IO 提速（遗留 #5）。
> 校验器与协议行为无变更——前者消除同步风险点，后者是纯测试基建优化。

### Changed

- **cp 检查点清单动态化（遗留 #4，v2.1.0 起存在）**：`protocol_check.py` 集成段的
  `cp-001~cp-008` 逐条字面量清单，改为从 `state_io.PHASES` 长度生成（检查点编号
  = 阶段序号，协议 §3「每阶段结束时主理人写一次检查点」）。成员增删阶段时两侧
  自动同步，单侧漂移由「阶段序列与 state_io.PHASES 一致」断言先行拦截；
  PHASES 加载失败按 fail-closed 判红，不静默回退到硬编码清单（那会让本处校验
  在环境异常时假绿）。双向破坏实锤：PHASES 侧加第 9 阶段 → 序列断言红且 cp 清单
  自动变 9/9；声明侧插 PHANTOM 阶段 → 序列断言红且失败原因精确归属。
- **selftest IO 提速（遗留 #5）**：`manifest_check_selftest` 与
  `routing_eval_selftest` 的 `make_copy` 首选 macOS APFS `cp -cR`
  （clonefile 写时复制，0.39s/次 vs `shutil.copytree` 3.0s/次；全树 15.2MB
  中 avatars/ 的 9 张 PNG 占 95%）。CoW 写时断链使 mutate 原地写天然不回流
  pristine（实测：clone 后改 dst 的 manifest，src 不变）。跨平台回退链：
  `cp -cR` → Python 硬链接树（`st_nlink>1` 判定 + `_detach_hardlinks` 防
  mutate 回流）→ `copytree`（异卷 EXDEV）。
  实测：**manifest selftest 330s → 48s（6.9×）、routing selftest 64s → 10s（6.4×）**。

### Fixed

- **硬链接路径的 pristine 污染风险（开发期实测抓出并修复）**：Python 硬链接
  回退路径下，mutate 的 `write_text` 原地覆写会连带改写 pristine（共享 inode），
  污染后续全部用例——开发期 N11 首跑即踩中（契约改名回流 pristine，
  `agents/socratic-questioner.md` 被写脏，git checkout 还原）。防线两层：
  ① `_detach_hardlinks` 在 mutate 前把共享 inode 文件替换为独立副本；
  ② APFS CoW 路径下克隆文件 `st_nlink == 1`，该函数零操作（快路径）。

### Regression evidence（v2.5.2 部署前实测，14 套门禁逐条独立取 rc）

与 v2.5.1 同一套门禁、同一结果：manifest **74/74** ✅ / manifest_selftest **30/30** ✅
（48s，原 330s）/ harness **12/12** ✅ / harness_selftest **14/14** ✅ / routing **39/39** ✅ /
routing_selftest **12/12** ✅（10s，原 64s）/ phase_norm **26/26** ✅ / vendor V1–V6 **6/6** ✅ /
state_ceilings **4/4** ✅ / state_io_guards **10/10** ✅ / protocol envelope **37/37**(v2.4) +
**12/12**(legacy) ✅ / conflict **5/5** ✅ / integration 阶段流水线 **10/10** + HANDOFF **8/8** ✅ /
protocol_selftest **14/14** ✅。cp 动态化双向破坏实锤 2 组（PHASES 侧 / 声明侧）。

## [2.5.1] - 2026-11-10

> R3 输入护栏收口。Phase A 再诊断（断言交互 + 运行时序）实锤 1 个 P0
> （checkpoint 形态契约断裂：协议标准形态触发裸 Traceback）+ 1 个 P1
> （task_id / checkpoint 路径注入未消毒）；排除 4 个假候选（并发锁 /
> 门禁语义 / 损坏检测 / 熔断叠加态均验证为设计正确）。本版还修复了
> 修复过程中引入的一处回归（不带检查点的推进被误拒），并以 10 条
> 注入式护栏锁定全部修复语义。

### Fixed

- **checkpoint 形态归一化（R3-P0-1）**：`cmd_advance` 旧实现只接受裸 `cp-NNN`；按协议文档传 `state://cp-001` 时会拼出 `checkpoints/state:/cp-001.md` → 父目录不存在导致裸 Traceback。新增 `_normalize_checkpoint_name`，两种形态归一到裸名，并拒绝路径元字符。
- **task_id 消毒（R3-P1-2）**：`task_id` 直接拼进 runs 目录名，含路径分隔符可建子目录、`..` 可越界落盘。`main()` 统一入口用 `_validate_task_id` 拦截（rc=2 + 业务报错文案，无堆栈）。
- **R3 修复引入的回归（本轮实测实锤）**：`--checkpoint` 为可选参数（`default=None`），半成品把「未传」与「非法形态」都返回 `None`，而 `cmd_advance` 用 `is None` 判错 → 不带检查点的正常推进被误拒（实测 rc=1，期望 0）。改为空值返回 `""`、非法值才返回 `None`，docstring 明确三态语义。
- **状态文件元信息自指悖论**：§1 写「canonical HEAD = f6ed42e」，但写入该值的 commit 自身（`6bc2bbe`）让它在落盘瞬间失效。改为不记录 HEAD，以 tag 基线 + `git rev-parse HEAD` 为真值源；§5.2 同步去固化值。
- **陈旧状态与数字口径**：§10.6「FM-R2-06 待回流 LEARNING」改已闭环（该文件第 40/431/477 行已有）；README 结构树两处 R2 遗漏计数（protocol selftest 13→14、manifest selftest 26→30）补齐。

### Added

- `tests/test_state_io_guards.py`（**10** 条）：不带检查点推进 / 前缀归一化 / 裸名兼容 / 两类非法 checkpoint / 两类非法 task_id / 合法边界 / 空串 / 超长。每条独立临时目录与 rc，负例同时断言「失败原因归属被测分支」且无裸堆栈（FM-R2-06 纪律）。**3 组注入破坏实验**证明护栏会红：A 空值仍返回 None → G1/G9 红；B 去掉前缀剥离 → G2 红；C 短路 task_id 消毒 → G6/G7/G10 红（主理人独立抽验破坏 C 复现：7/10 红、失败原因精确归属，还原后 md5 逐字节一致）。
- CI 新增 `State IO input guards (R3 P0-1/P1-2)` step；门禁 step **14 → 15**（run 总 step 20 → 21）。全仓「14/16 step」旧计数统一，新增 `docs/harness-iteration-loop.md` §10.3.3 作为唯一真值源（实测 v2.4.x = 12 门禁/18 总、v2.5.0 = 14 门禁/20 总、R3 = 15 门禁/21 总；差额 6 恒为平台 step）。
- `docs/harness-iteration-loop.md` §5.3：R3 验收证据（Phase A 6 组实验台账 + 14 套门禁全绿 + 独立负向实锤）。

### Regression evidence（v2.5.1 部署前实测，14 套门禁逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` / `_selftest.py` | 74/74 ✅ / 30/30 ✅ |
| `harness_eval.py` / `_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 6/6 ✅ |
| `test_phase_normalization.py` | 26/26 ✅ |
| `tests/test_state_ceilings.py` | 4/4 ✅ |
| `tests/test_state_io_guards.py`（新增） | **10/10** ✅ |
| `protocol_check.py` envelope / conflict / integration | 37/37(v2.4)+12/12(legacy) ✅ / 5/5 ✅ / 10/10+8/8 ✅ |
| `protocol_check_selftest.py` | 14/14 ✅ |

### Known limitations

- 官方 `validate_expert.py` 本机不存在（环境性已知限制，同 v2.4.0 起）。
- R3 全轮的 GATE 裁决与完整台账以 §5.3 + 本段为准；并发两工作线汇合的事实已在 §10.1 如实登记。

## [2.5.0] - 2026-11-09

> R2 覆盖矩阵盲区修复版。主题：**每一条门禁分支都要有一只「会红的测试」盯着**。
> 16 组真实破坏实验逐条验证覆盖矩阵，修复 2 个 P0（语义失真 + 幽灵成员无门禁）、
> 4 个 P1（重复负例 / 规则覆盖缺口 / CI 缺口 / C13 分支无负例）、1 个 P2（跨市场
> 描述漂移实锤并修复）。

### Fixed

- **发布介质自洽性（打包前拦截，FM-R1-01 第 3 次复发的根治）**：本版打包前
  发现 README「安装方式 3」仍写死 `rot-v2.4.1.tar.gz`——与 v2.4.0 那次
  「资产内文档指向旧版」同源。已改为统一指向 `releases/latest` 页面并去掉
  版本锚点，**根治**每次发版都要同步改 README 的复发点；README 发布契约段
  补 4 条强制检查（CI 绿才打 tag / `git archive <tag>` 保证资产 == tag /
  打包前查版本字面量 / 解包核对版本行）。另修正本文件版本段倒序错误
  （v2.5.0 段原误排在 v2.4.1 之后）。协议、运行时、门禁行为均无变更。

- **编排层上限语义失真（P0-1）**：v2.4.0 CHANGELOG 笼统写「硬上限代码化」，实测
  `advance` 超过 `--max-turns` 上限后仍 rc=0 放行（turn 2/1）。真实语义是**分层**
  的：`turns`/`tokens` 触顶 = 告警（`budget` 子命令 ⚠️，主理人语义裁量），`max_time`
  超时与 `failures` 熔断 = 终态（`status: aborted`，advance/fail 拒绝）。CHANGELOG
  与 README 措辞已按 state_io.py docstring 的设计口径修正。
  - 新增 `tests/test_state_ceilings.py`（4 用例）锁定该语义分层——告警被误改成
    截断（或反向）时立即红。
- **跨市场 description 漂移（P2-1 实锤）**：两份 manifest 的 `description` 已实际
  漂移（cb 侧写 ACP+五角色矩阵，cl 侧写 v2.1.0 Harness 措辞）而 C2 无校验不可
  察觉——用户在两个市场看到的插件介绍不同。已统一措辞，并把 `description` 纳入
  `SHARED_FIELDS` 对等校验（74 项）。`keywords`/`author` 有意不纳管（允许平台
  差异化），理由写在校验器源码注释。

### Added

- **流水线成员真值源断言（P0-2）**：`protocol_check.py` 集成段新增「流水线成员
  引用 ⊆ agents/*.md 真值源」断言。审计实锤：producers 注入幽灵成员 ID
  （GHOST-MEMBER）时 integration 仍 rc=0——旧断言只查「引用是否在上游参与过」，
  不查「引用是否是真实成员」。agents/ 目录不可读（单文件副本态）时 SKIP 不误报；
  目录为空时 fail-closed 判红。阶段流水线 9 → **10** 项。
- **protocol selftest 13 → 14 条**：
  - N10 重构：原 N10 与 N6 锚点逐字相同、注入同一位置（纯重复），改为破坏
    `context_ref` **list 形态**逐条校验分支（V29/V33 两条用例失效证明注入生效），
    与 N6（dict 形态必填）互不重叠。
  - N11 新增：幽灵成员注入负例（整包副本态），锁定 P0-2 新断言。
- **manifest selftest 26 → 30 条**：
  - N27：C8 规则覆盖矩阵批量回归——13 条 FORBIDDEN_PATTERNS 中 7 条从无负例
    （Six-role / six-role research / L1-L3 conflict / msg_type / 任意一维<90 /
    五项核心任务 / 5-task），一条用例一次性覆盖，规则正则被误改时立即红。
  - N28：C13 主理人声明位互换攻击（lead 的 role 改 member + 普通成员改 lead），
    锁定「leadAgent 与声明位不一致」分支。
  - N29：C13 单元格内成员 ID 重复（duplicates 分支）。
  - N30：C13 agents/ 目录整体删除（fail-closed 路径）。

### Changed

- CI 新增 2 个门禁 step（12 → 14）：State IO circuit breaker 熔断段
  （fail x5 → aborted → advance 拒绝 → finish 不改写）与 ceiling semantics lock
  （test_state_ceilings.py）。v2.4.0 的熔断特性此前只在本地手测过，CI 只走 happy path。
- timeout 25 分钟维持不变（新增 step 为秒级）。

### Regression evidence（v2.5.0 部署前实测，逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` | **74/74** ✅（C2 +1 项）|
| `manifest_check_selftest.py` | **30/30** ✅（新增 N27–N30）|
| `harness_eval.py` / `harness_eval_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `routing_eval_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 **6/6** ✅ |
| `tests/test_state_ceilings.py`（新增） | **4/4** ✅ |
| `test_phase_normalization.py` | **26/26** ✅ |
| `protocol_check.py` | envelope **37/37**(v2.4) + **12/12**(legacy) ✅ / conflict **5/5** ✅ / integration 阶段流水线 **10/10**（+真值源断言）+ HANDOFF 回引 **8/8** ✅ |
| `protocol_check_selftest.py` | **14/14** ✅（N10 重构 + N11 新增）|
| 独立破坏实锤 | GHOST-MEMBER 注入 → integration rc=1 且列幽灵 ID ✅；turn 2/1 放行 + 告警（语义锁定）✅；fail x5 → aborted → advance rc=1 → finish rc=0 且 status 仍 aborted ✅ |

## [2.4.1] - 2026-11-09

> 发布介质自洽性补丁。主题：**资产内容必须与 tag 内容一致**。
> 协议、运行时、门禁**行为无变更**；仅修正发布链路的一处介质-文档矛盾。

### Fixed

- **release 资产内的 README 与自身文档矛盾**：v2.4.0 的 tarball 资产 `rot-v2.4.0.tar.gz` 已补齐，但 tag `v2.4.0` 指向 `90a1c36`——**早于**修正「安装方式 3」链接的 commit `2f2b016`。结果：tarball 内的 README 仍写「方式 3 只能安装到 v2.1.2」，用户下载后按文档操作会指向旧版本。
  - **不改 v2.4.0**：已发布 tag 不重写；已发布资产不重打包（重打会造成「资产内容 ≠ tag 内容」，比文档过期更严重）。
  - **改为发补丁版 v2.4.1**：版本号三处同步（`.claude-plugin` / `.codebuddy-plugin` / README 头部），方式 3 改指 `rot-v2.4.1.tar.gz`，README 版本历史补 v2.4.1 条目并如实登记该缺口成因。

### Changed

- 双 manifest version 2.4.0 → **2.4.1**；README 头部版本行同步。

### Regression evidence（v2.4.1 部署前实测，12 套门禁逐条独立取 rc）

与 v2.4.0 同一套门禁、同一结果：manifest **73/73** ✅ / manifest_selftest **26/26** ✅ / harness **12/12** ✅ / harness_selftest **14/14** ✅ / routing **39/39** ✅ / routing_selftest **12/12** ✅ / phase_norm **26/26** ✅ / vendor V1–V6 **6/6** ✅ / protocol envelope **37/37**(v2.4) + **12/12**(legacy) + conflict **5/5** + 阶段流水线 **9/9** + HANDOFF 回引覆盖 **8/8** ✅ / protocol_selftest **13/13** ✅ / shim `assemble_spawn_prompt.py --member synthesis-integrator` rc=0 ✅。
CI run（12 门禁 step / 18 总 step 全执行全绿）+ OneDrive 镜像独立复跑 manifest 73/73 与 protocol 全套通过。

### Known limitations

- v2.4.0 的 tarball 资产内 README 保留旧链接（历史资产，不追溯修改）；需最新安装路径的用户请用 v2.4.1 资产或方式 1 / 方式 2。

## [2.4.0] - 2026-11-09

> Harness 迭代进化 R1 首轮全闭环版。主题：**机制 → 门禁 → 文档 → 状态落盘**。
> 四阶段硬门控闭环（诊断 → 构建 → 测试&debug → 再诊断）走完一轮；13 个批次全部落盘，
> 12 套门禁 12/12 全绿；新增「断点续跑单一事实源」让迭代可中断可续跑。

### Added

- **C13 成员 ID 集合一致性门禁**：`manifest_check.py` 新增第 13 项校验——以 `agents/*.md` 的文件名集合（最底层事实）为机器真值源，逐处比对 8 个目标：协议 §1 角色矩阵「成员 ID」列 / registry「团队成员一览」`agent_id` 列 / team-lead 成员表 / `.claude-plugin` 的 `agents[]` / `.codebuddy-plugin` 的 `agents[]` / `.codebuddy-plugin` 的 `members[].id` / `teamInfo.leadAgent` / `teamInfo.memberAgents`。任一不匹配即 rc=1，并**逐处列出「多出 / 缺少」差异**。8 类解析失败路径（含真值源为空）全部 fail-closed——空集合一律判红。成员增删从此只需改 `agents/` 一处。
- **协议注入式负例自测**（新建 `skills/research-orchestration-workflow/scripts/protocol_check_selftest.py`，**13** 条）：证明 `protocol_check.py` 的三个 suite 真会拦截破坏，而非永远返回 0。
- **阶段名归一化自测**（新建 `scripts/test_phase_normalization.py`，**26** 条）：覆盖 8 个阶段名 × 2 种写法 + 大小写不敏感 + 整数直传 + 非法值透传。
- **编排层状态机代码化**（`state_io.py` 327 → 805 行）：`init` / `advance` / `resume` / `budget` / `fail` / `finish` 六命令；按序推进门禁（跳级 rc=1，逃生阀 `--force` 必须配非空 `--force-reason`）；失败熔断达阈值 → `status: aborted` + `abort_reason`；4 个 metrics 落盘且未上报记 `null` 禁编造；编排层四项硬上限全部代码化、**语义分层**（与平台层 `maxTurns: 180` 分层表述、两层都保留）：`max_time` 超时与 `failures` 熔断为**终态**（`status: aborted`，`advance`/`fail` 拒绝），`turns`/`tokens` 触顶为**告警**（`budget` 子命令打印 ⚠️ 不截断——轮次/token 计数由主理人语义裁量，状态机不越权代管）。
- **两层 pointer 校验**：信封层判「字段在不在」（4 种合法形态 + `full`/`summary` 可空 / `ref` 必填），覆盖层判「覆盖全不全」（HANDOFF 回引必须是 `state://cp-NNN`）。两层职责分离不合流——数据依赖与失败语义都不同。
- **迭代状态文件**（新建 `docs/harness-iteration-loop.md`）：断点续跑单一事实源，含意图漂移基线 / 四阶段台账 / 验收基线 / 资产清单 / 已修复问题黑名单 / 失败模式库 / 发布契约 / 下轮入口。
- **两个协议登记模板**（新建 `skills/research-orchestration-workflow/templates/`）：`cross-domain-combo.md`（三组合 fan-out 与仲裁链，86 个占位符）/ `result-envelope-v2.4.json`（16 键，与 `REQUIRED_FIELDS_V24` 逐字一致）。
- **shim core 哈希校验**：`assemble_spawn_prompt.py` 命中 core 后立即比对 `vendor/shared-core/VENDOR.json` 登记的 sha256，不一致即拒绝加载并退出（exit 4），阻断「祖先目录里的旧版/被篡改同名文件被静默加载并绕过哈希门禁」。

### Changed

- **门禁体系从「一层」升为「三层」**：第一层正向校验器（manifest C1–C13 / harness H1–H12 / routing R1–R6 / protocol 三 suite）、第二层注入式负例自测（5 套，共 91 条）、第三层联邦防漂移（V1–V6）。README 新增「门禁体系现状」节逐层说明，并固化**负例设计两条硬纪律**：①锚点唯一命中 + 替换后落盘校验 ②一条负例只承载一个失败维度。
- **C8 废弃表述扫描豁免机制声明化**：由硬编码文件名白名单扩为「白名单 + 文件头声明式标记」双路径，标记窗口限定在前 3 行 ∩ 前 512 字节。新增审计类文档不再需要改校验器源码。
- `protocol_check.py` 主套件 16 → **37**（v2.4 六必填 + legacy 12）；集成段去除硬编码自证，改为真读 `state_io.py` 的 `PHASES` 并交叉比对。
- 双 manifest version 2.3.0 → **2.4.0**；README 头部版本行与结构树同步。
- CI（`.github/workflows/validate.yml`）新增 2 个 step 纳入两套新注入式负例；timeout 15 → 25 分钟（5 套 selftest 在本地实测合计约 350s IO）。

### Fixed

- README 安装方式 3 的 tarball 链接指向已下线的资产（实测 HTTP 404）：改指实际存在的资产名，并补「资产名不统一」的限制说明。本轮 release 补齐 `rot-v2.4.0.tar.gz` 资产后，方式 3 已由 v2.1.2 改指 v2.4.0；v2.2.0 / v2.3.0 无资产的缺口如实登记为历史缺口。
- README「安装方式」标题写「三套并存」但实际列 4 种方式（自 v2.0 引入即错）：改为「四种并存」。
- CI step 名 `Routing consistency check (R1-R5)` 与实际的 R1–R6 不符：改为 `(R1-R6)`。
- 协议 §1 与 team-lead 对「成员集合真值源」的表述互为循环：两端统一拆成两层——归属 SSOT = 协议 §1；**集合维度的机器真值源 = `agents/*.md` 文件名集合**，由 C13 强制。

### Regression evidence（v2.4.0 部署前实测，12 套门禁逐条独立取 rc）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` | **73/73** ✅（新增 C13 贡献 9 项）|
| `manifest_check_selftest.py` | **26/26** ✅（新增 N24/N25/N26）|
| `harness_eval.py` / `harness_eval_selftest.py` | 12/12 ✅ / 14/14 ✅ |
| `routing_eval.py` / `routing_eval_selftest.py` | 39/39 ✅ / 12/12 ✅ |
| `tests/test_vendor_core.py` | V1–V6 **6/6** ✅（安装态 0 SKIP）|
| `test_phase_normalization.py` | **26/26** ✅ |
| `protocol_check.py` | envelope **37/37**(v2.4) + **12/12**(legacy) ✅ / conflict **5/5** ✅ / integration 阶段流水线 **9/9** + HANDOFF 回引覆盖 **8/8** 检查点 ✅ |
| `protocol_check_selftest.py` | **13/13** ✅ |
| 独立负向实锤（4 组，每次还原后 md5 与基线逐字节一致） | 改协议 §1 成员 ID → rc=1 且逐项列差异 ✅；清空 `agents/*.md` → rc=1（真值源为空一律判红）✅；破坏 `state_io.py` 的 `PHASES` → integration rc=1 且列两侧序列差异 ✅；状态机 9 条路径 rc 各自符合设计语义 ✅ |
| shim 哈希校验 | 联邦命中 rc=0 ✅ / vendor 兜底 rc=0 ✅ / 任一路径篡改 → rc=4 拒绝加载 ✅ / VENDOR.json 缺失 → 告警放行 rc=0 ✅ |

### Known limitations

- 官方 `validate_expert.py` 本机不存在（宿主未随包分发）→ 以包内 `manifest_check.py` + `tests/test_vendor_core.py` V5/V6 安装态冒烟替代。
- `protocol_check.py` 集成段的 `cp-001~cp-008` 检查点清单仍为硬编码：当前已与 `state_io.py` 的阶段序列交叉比对（真断言），但 cp 清单本身未动态化，成员增删 cp 编号变动时需同步。
- selftest 约 350s IO 耗时（每条负例在临时目录复制整个包体）：可用硬链接替代复制提速。

## [2.3.0] - 2026-11-08

> 发布后残留风险的工程化收口版。主题：**登记的残留 → 门禁化的消除**。
> 四条残留中的三条（R5 覆盖盲区 / SSOT 内容无保护 / 裸词拦截依赖槽位写法）落为工程修复，第四条（validate_expert 安装路径限制）文档化收口。

### Added

- **R6 工具真实性校验**：`routing_eval.py` 对照真实 MCP 清单（探测顺序：env `ROUTING_EVAL_MCP_JSON` → `~/.workbuddy/mcp.json`）硬校验 registry 全部成员 tools 行的 9 个 `mcp__` 名；伪造 server 名（形态合法但清单中不存在）现在会被拦截。清单不可得的 CI / git-clone 态**显式 SKIP**（组标题带 ⏭️ 标记 + V4 式语义说明），SKIP 不计入 FAIL、不影响 rc；安装态必须 PASS 才算完整覆盖。
- **R5 分级解析扩展全 8 成员**：原 R5 只覆盖 3 个 atomic。现按 registry 动态分级——atomic（有 tools 行）沿用四类解析 + 双向相等；非 atomic（无 tools 行 = 零工具授权）用 ①mcp__ 前缀 ②反引号 ③内置裸词 三类解析，任何工具 token 即 FAIL，**跳过 ④ `+` 槽位分支**（对中文叙述描述误报率高，是原残留的根因）。R5 由 3 项变 8 项。
- **selftest 12 例**：N10 非 atomic MD 注入反引号伪造名（走①类）断言 rc=1；N12 registry 注入 `mcp__GHOST_SERVER`（R4 形态放行、只有 R6 能拦）+ 真实清单 fixture + 环境快照恢复防用例间污染；N11 并入 P1 正例（与独立正例完全重复，不重复造例）。N10/N12 均实测 rc=1 命中。

### Regression evidence（v2.3.0 部署前实测）

| 套件 | 结果 |
|------|------|
| `routing_eval.py` | **39/39** ✅（R1 4 + R2 8 + R3 15 + R4 3 + **R5 8** + **R6 1**）|
| `routing_eval_selftest.py` | **12/12** ✅（P1 + N1~N10 + N12）|
| R6 SKIP 分支 | 空 HOME + 无 env 下显式 SKIP 标记、rc 仍 0、39/39 ✅ |
| 破坏验证 | 非 atomic 注 `` `mcp__GHOST_TOOL` `` rc=1（extra=）；registry 注 `mcp__GHOST_SERVER` + 真实清单 rc=1（不存在）✅ |
| `manifest_check.py` | 64/64 ✅ |
| `harness_eval.py` | 12/12 ✅ |

### Changed

- 双 manifest version 2.2.0 → **2.3.0**；README 头部、版本历史、健康检查命令注释同步。
- README 新增「validate_expert.py 的已知限制」节：该校验器硬编码安装路径检查，tempfile 副本必误报「专家不在专家目录下」、CI 无法覆盖，只能安装态原位运行（v2.2.0 部署时 xval 双验证者实测定性的环境性误报，现文档化）。
- agent-registry.md「注入式负例」节计数同步（routing selftest 10 → 12 条，R5/R6 语义一句话）。

## [2.2.0] - 2026-11-07

> 从零独立诊断（15 项短板亲验）后的补全完善版。主题：**纸面机制 → 确定性工程**。
> 本条目同时补记 tag v2.1.2（bb05e18）之后 6 个无版本号 commit 的欠账。

### Added（补记 v2.1.2 → 0945fba 欠账，tag 后曾长期未升版——本版起恢复「改必升版」纪律）

- **959dc1e / f746291 / 1eda103**：spawn 装配器 shim v3.4.2 跟升——60 行 R9 → 102 行联邦两级查找（联邦真源优先 + vendor 兜底 + SHIM_DEBUG），配套 `vendor/shared-core/` 副本 + `VENDOR.json` + `tests/test_vendor_core.py` 防漂移门禁——门禁全绿（详见下方 Regression evidence 表；`test_vendor_core.py` 在 git/CI 隔离态 V4 按设计 SKIP）；适配自 smart-textbook-team 先例
- **5fc2630 / 688dd92**：移除包根 settings.json（依「宿主启动时必然删除」假设）——**本版已推翻该决策**，见下方 Fixed/Reverted

### Added（本版新能力）

- **状态持久化（P0-2，治协议 §3 纸面 schema）**：新增 `skills/.../scripts/state_io.py`——八阶段状态的确定性落盘层。五命令 init/advance/resume/finish/budget；原子写（.tmp + os.replace，并发 20 路实测无损坏）；`state://cp-NNN` 伪 URI 绑定真实路径 `.harness-runs/<task_id>/checkpoints/cp-NNN.md`；退出码 0/1/2/3（JSON 损坏 fail fast）。team-lead.md 新增「状态初始化与断点续跑」强制条款：开工 resume 盘点、阶段收尾 advance、撞限恢复不依赖对话记忆。协议 §3 增补「状态落盘（确定性工程层）」节，写入者=仅主理人
- **routing 一致性评估（P2，已落地）**：新增 `scripts/routing_eval.py` + `scripts/routing_eval_selftest.py`。R1 三方成员集合 / R2 关键触发词覆盖 / R3 条目结构完整 / R4 工具名形态 / R5 工具集合一致性（比对 3 个 atomic MD description 与 registry tools 行，防伪造与漂移；交叉验证后补），共 33 项；按 `__file__` 上溯定位、支持 `--root`，rc 0/1/2。selftest 10 例注入式负例（P1 正向 + N1~N9，raw_probe 未归一化护栏不计入用例数），与仓库真实状态解耦。补齐 README/CHANGELOG 曾提前引用该文件造成的悬空引用
- **CI 门禁补齐（P2）**：`.github/workflows/validate.yml` 新增 3 个 step——Routing consistency check (R1-R5) / Routing eval self-test (mutation-based) / Vendor core anti-drift (V1-V6)，把原仅本地手跑的两套校验纳入每次 push；另新增 State IO lifecycle smoke test（v2.2.0，八阶段 + 8 检查点全链路冒烟）

### Fixed

- **恢复包根 settings.json + C12 护栏（P0-1，Reverted 5fc2630 的决策）**：官方 validate_expert 对 Team 型硬要求该文件（报错原文「Team type must have settings.json」），v2.1.2 后删除导致官方校验 1 error。反证：agent-harness-expert 同格式文件存活 3 周未被宿主删除。「宿主必然删除」假设不成立；若未来宿主真的删除，C12 会在下一次发行校验立即报警，而不是等官方校验器
- **manifest_check.py 63→64 项**：新增 C12（Team 型 settings.json 存在 + 单键 agent 指向主理人）；selftest 17→21 条（N18 删除负例 / N19 篡改负例 / N20 旧团队规模表述 / N21 marketplace.json Six-agent 护栏）
- **C8 废弃表述护栏补强**：`5 人协作` 规则的过期描述「现为六人」→「现为八人」；新增 `六人编排团|6 人协作` 规则，刻意避开 README 版本史里合法的「v2.0.0 六人团队」历史描述，并配 N20 注入式负例证明规则有效
- **harness_eval.py 根定位修复（P1）**：`Path.cwd()` → `__file__` 上溯（与 manifest_check 一致），任意外部目录调用不再 exit 2；harness_eval_selftest 同步覆盖
- **README 三处过期同步（P1）**：团队表 6 人→8 人；目录树补 vendor/、tests/、harness_eval.py、state_io.py、routing_eval.py；版本历史补 2.1.0/2.1.1/2.1.2/2.2.0；健康检查命令扩为全量清单
- **registry 工具名失真修复 + 三级降级链（P1，已落地）**：对照本机 `~/.workbuddy/mcp.json` 的 45 个真实 server 亲验，确认裸名 `mcp__crossref` / `mcp__paper_search_server` / `mcp__consensus` / `mcp__biorxiv` / 「政策文件库」全部无法对应真实 server，已按领域替换为真实名（注意 `biorxiv-mcp-server` 确为真实 server，保留其全名 `mcp__biorxiv-mcp-server` 作为预印本 / 新颖性核查源）——biomed：`mcp__pubmed` / `mcp__biomcp` / `mcp__semantic-scholar` / `mcp__biorxiv-mcp-server`；ai：`mcp__arxiv-mcp-server` / `mcp__semantic-scholar` / `mcp__context7` / `mcp__fetch`；general：`mcp__semantic-scholar` / `mcp__tooluniverse` / `mcp__web-scout`（registry tools 行、权限表与 3 个 atomic 成员 MD description 同步）。新增「工具降级链」节：① 首选源不可用不得静默跳过 → ② 同类换源（三领域首选/次选/兜底映射表）→ ③ 三源全败降置信输出（confidence ≤ 40、`source_unavailable` 标注、禁编造 DOI/PMID/URL、6 必填字段齐全、status 取 partial/blocked、issues 给补检建议）
- **成员 MD 信封单源化（P2）**：删除 8 处重复的 `result_envelope` JSON schema 与 status 取值复制，统一改为引用 `references/agent-protocol.md` §2；补 `payload 定制` 纯文本行保留各角色特有字段，并把 socratic-questioner 第二处 schema 的 `questions/assumption_density/emotion_risk/ready_for_align` 合并回主节，根治两套 payload 字段互相漂移。team-lead 作为编排者不产出成员式 RESULT 信封，属结构性例外；契约章节标题全部保留
- **memory_log.py docstring 纠错（P2）**：原写「对应 agent-protocol.md §4 三级记忆」，实际 §4 是上下文传递（Context Passing）；改指 team-lead「Harness 运行时规范 · Memory 三级」并说明与 §4 互补。Usage 中违反「禁代产出」铁律的示例换成合规的根定位修复案例。可执行代码零改动
- **displayDescription.zh 53→48 字**（官方建议 40-50）

### Changed

- 双 manifest version 2.1.2 → **2.2.0**；README 头部同步
- team-lead.md frontmatter：version 2.0.0 → 2.2.0、description 升 8 人 / v2.2 语义；Observability 节把 LEARNING.md 写入从注脚升级为三步强制收尾清单（finish → task 记录 → lesson 回流），写明三步未做完不得报完成
- LEARNING.md：补 tag v2.1.2 后 5 条真实历史 task 记录（证据均为仓库内 commit/CHANGELOG/README，未采集的 observability 如实标注、不自造数值）+ 新增「失败回流规则落盘」节（五类触发 / 三件套 / 护栏落地判据「未闭环不得写已修复」/ 复跑验证）+ Ralph Loop 协议编号 1,2,4,5,6,7 修正为 1–7 并补入「跑校验脚本确认基线」
- meta-architect.md：description 术语统一为正文 8 处使用的「跨域节点」，与 registry trigger 的「跨域节点」对齐，消除 SSOT 与成员正文的术语漂移
- `.gitignore` 增 `.harness-runs/`（state_io.py 运行期状态不入库）

### 交叉验证后修复（部署前）

- **B1 · 协议门禁方向性错误**：`protocol_check.py` 此前按已废弃的 ACP v2.0 信封判定合规，方向反了。重写后 envelope 模式以 **result_envelope v2.4 主套件 16/16** 作为当前合规判定，ACP v2.0 的 12/12 仅保留为历史 fixture 回归（legacy 不参与当前合规判定）。
- **R3 / H6 · 权限档章节漏检**：改为按 `^### (safe|moderate|dangerous)` 标题识别 + 正文非空判定，堵住「删掉整个权限档章节仍能过门禁」的假绿。
- **R5 · 工具集合覆盖盲区（新发现阻断项）**：原 R4 只校验 registry 自身 tools 行形态，从不比对 `agents/*.md`，MD 工具名漂移甚至伪造（实测注入 `mcp__GHOST_TOOL` 仍 30/30 全绿）。根治：3 个 atomic MD description 工具枚举单源化（只引用 registry 为 SSOT）+ 新增 R5「MD 出现 token 即须与 registry 集合双向相等（missing/extra/illegal 全 FAIL），零 token 视为已单源化 PASS」+ N8/N9 负例（伪造 `mcp__` 名与非工具名裸词）。
- **state_io 并发互踩（冻结前亲测实锤）**：20 路并发 advance 原本 19/20 崩溃（read-modify-write 共享 `.tmp` 互踩）；修复为 flock 互斥锁（把协议 §3「写入者=仅主理人」纸面约定固化为工程约束）+ PID 隔离 tmp 兜底，复测 20 路全 rc=0、turn 无丢更新。
- **routing_eval_selftest 自愈夹具**：新增 raw_probe 未归一化护栏，拒绝自愈夹具把真实缺陷悄悄修回后再判绿（掩盖真实缺陷）。
- **CI paths 补齐**：`.github/workflows/validate.yml` 触发器补 `tests/**` 与 `vendor/**`，避免改动这两处时不触发 CI。
- **两份 marketplace.json**：六agent / Six-agent → 八agent / Eight-agent，并去掉过期的 ACP 措辞。
- **C8 护栏 + N21**：补 `六agent|Six-agent` 规则，并新增 N21 负例——向 `.claude-plugin/marketplace.json` 注入 Six-agent 旧表述，验证 C8 的 `rglob` 覆盖隐藏目录。
- **全库阶段名统一**：`EXECUTE_ONE_STEP` → `EXECUTE`（与 `state_io.py` 的 `PHASES` 常量及协议 SSOT 一致）；CHANGELOG 历史条目保留原文并加注，以存审计。

### Regression evidence（v2.2.0 部署前逐功能实测）

| 套件 | 结果 |
|------|------|
| `manifest_check.py` | 64/64 ✅ |
| `manifest_check_selftest.py` | 21/21 ✅（N18/N19/N20/N21）|
| `harness_eval.py` | 12/12 ✅ |
| `harness_eval_selftest.py` | 14/14 ✅（N13 权限档章节负例）|
| `routing_eval.py` | 33/33 ✅（R1 4 + R2 8 + R3 15 + R4 3 + R5 3）|
| `routing_eval_selftest.py` | 10/10 ✅（P1 + N1~N9）|
| `protocol_check.py` | envelope 16/16(v2.4) + 12/12(legacy) + conflict 5/5 + integration 8/8 ✅ |
| `test_vendor_core.py` | V1-V6 6/6 ✅；安装态 6/6 PASS，git clone / CI 隔离态 V4 按设计 SKIP（联邦真源不可达），非门禁失败 |
| `state_io.py` 全链路 | init→advance×8→resume→budget→finish 全 rc=0；8 个 `cp-NNN.md` 真实落盘；异常 rc=1（非法阶段）/2（无状态）/3（JSON 损坏）逐项核对；并发 20 路 advance rc={0}、turn=20 无丢更新（flock 修复后）；幂等 init ✅ |
| `topic_scoring.py` 边界 | 越界 rc=1 / 缺维 rc=2 / 正常 rc=0 ✅ |
| 外部目录调用 | `manifest_check` / `harness_eval` / `routing_eval` 从 `/tmp` 调用均不依赖 cwd ✅ |
| CI workflow | YAML 可解析，`validate` job 共 12 steps（含新增 State IO lifecycle smoke test）✅ |
| 官方 `validate_expert.py` | 0 error / 0 warning ✅（原 1 error + 1 warning）|

## [2.1.2] - 2026-09-30

> v2.1.0 的一次**补全重构**：修复 atomic 拆分后调用点未同步的全部残留，并把 Harness 校验纳入 CI。
> 根因：v2.1.0 拆了 agent MD 但 team-lead 路由表/协议文档/CI 均未跟随更新（Step 3 诊断 5 P0）。

### Fixed

- **`agents/research-orchestration-team-team-lead.md`**：
  - L186 单 Agent 直调路由表 / L197 Workflow A Phase3 / L203 Workflow B Phase1 / L211 Workflow C Phase2 的 4 处 `domain-expert` 死引用 → 改为 `domain-expert-biomed / -ai / -general` 按领域标签 fan-out
  - 删除重复标题行「## 核心工作法：八阶段状态机」（原 L104/L106）
  - **maxTurns 消歧义**：新增「两套上限分工」说明——frontmatter `maxTurns: 180` = 平台层会话兜底；registry `max_turns: 30` = 编排层任务自控预算。两者不冲突
- **`skills/.../references/agent-protocol.md` §1**：「现有 6 名成员」→「现有 8 名成员（v2.1.0 起 domain-expert 拆为 biomed/ai/general 三个 atomic）」
- **`test-prompts.json` #1**：target_agents 中死引用 `domain-expert` → 3 个 atomic
- **`CONTRIBUTING.md`**：契约章节示例 `domain-expert` → `domain-expert-biomed`（atomic 三元之一）
- **`scripts/manifest_check_selftest.py` N2**：replace 精确串匹配第三次踩坑（displayDescription 文案从「五级冲突仲裁」改为「五级仲裁」后 mutation 空转 → 假绿）。改为 **append 式注入**废弃表述，无论现文案如何都保证触发校验器

### Added

- **`.github/workflows/validate.yml`**：新增 2 个 step——`Harness design checks (H1-H12)` 与 `Harness eval self-test`。此前 harness_eval 系列 12+13 项检查仅在本地手动跑，改一行文档即可无声破坏（Step 4 对标「可评估性」执行层缺口）

### Changed

- 双 manifest `version` 2.1.0 → 2.1.2（含 2026-09-30 晨 darwin-skill 提交的通信协议 v2.4 统一 + spawn 装配器，两项此前未发布）

### Regression evidence

| 套件 | v2.1.2 |
|------|--------|
| `harness_eval.py` | 12/12 ✅ |
| `manifest_check.py` | 63/63 ✅ |
| `manifest_check_selftest.py` | 17/17 ✅（N2 修复后）|
| `harness_eval_selftest.py` | 13/13 ✅ |
| `protocol_check.py` | envelope 12 + conflict 4 + integration ✅ |

### Skipped（有意不做）

- `avatars/domain-expert.png` 孤儿清理：按 v2.1.0 CHANGELOG 既定决策保留（防历史引用）
- Claude Code 式 hooks 拦截：专家包为跨平台分发物，hooks 属 Claude Code 专有；dangerous 拦截由 `assemble_spawn_prompt.py` 白名单 + registry 三档权限承载（P0-4 降级 P2）

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
- **`scripts/research-orchestration-workflow/references/agent-registry.md`**：单一事实源（SSOT），含 trigger / tools / safe/moderate/dangerous 三档权限分级（早期条目误写为 `scripts/`，实际路径为 `skills/`，此处保留原文以存审计）
- **`scripts/research-orchestration-workflow/references/LEARNING.md`**：跨会话连续性（Anthropic Ralph Loop 模式），每次任务必追加 task 记录（早期条目误写为 `scripts/`，实际路径为 `skills/`，此处保留原文以存审计）
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
- **八阶段状态机**：FREEZE → IDENTIFY → COLLAPSE → CLARIFY → ALIGN → EXECUTE_ONE_STEP → REVIEW → NEXT。（历史原文；v2.2.0 起阶段名统一为 `EXECUTE`，与 `state_io.py` 的 `PHASES` 常量及协议 SSOT 一致）
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
- **评分脚本**（`scripts/topic_scoring.py`）：8 维选题评分 + S/A/B/C 分档 + 3 条止损线 + 复评决策（维持/升档/降档/止损）。（早期条目误写为 `scripts/`，实际路径为 `skills/research-orchestration-workflow/scripts/`）
- **协议校验脚本**（`scripts/protocol_check.py`）：12 信封（当时口径；v2.2.0 现为 result_envelope v2.4 主套件 16 + ACP v2.0 legacy 回归 12）+ 5 冲突仲裁 + 集成仿真单元测试。（早期条目误写为 `scripts/`，实际路径为 `skills/research-orchestration-workflow/scripts/`）
- **Memory 持久层脚本**（`scripts/memory_log.py`）：4 类（decision/preference/convention/lesson）+ daily/longterm 双目标 + 去重。（早期条目误写为 `scripts/`，实际路径为 `skills/research-orchestration-workflow/scripts/`）
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