#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务状态持久化工具（协议 §3 State Sync 的确定性落盘层）

## 为什么需要这个脚本

agent-protocol.md §3 定义了 SSOT 状态 JSON（phase/turn/checkpoints/perception/
budget），v2.1.2 之前它只是**纸面 schema**——没有任何脚本负责写盘，任务状态只活在
主理人的对话上下文里。会话中断（撞限/用户取消/平台超时）后，断点续跑无从谈起。

本脚本把协议 §3 变成确定性工程：状态落盘为
`<workspace>/.harness-runs/<task_id>/_state.json`，主理人每阶段收尾调用 `advance`，
重启后调用 `resume` 即可拿到「上次完成阶段 + 下一步」。

## `state://cp-*` 伪 URI 约定

协议 §3 检查点使用 `state://cp-001` 形式的指针。本脚本为其绑定真实路径：
`state://cp-NNN` ≡ `.harness-runs/<task_id>/checkpoints/cp-NNN.md`（阶段产物落盘文件）。
主理人写检查点时把阶段产物存入 checkpoints/ 子目录，指针即可解析。

## 四个硬上限的代码化（v2.3.0）

registry「Loop 终止硬上限」表的四项此前只有 max_turns / max_token 落到了代码里，
max_time 与 circuit_breaker 是纯纸面。本版本把四项**全部**代码化，文档表与代码常量
一一对应（registry §Loop 终止硬上限 的「代码落点」列）：

| registry 键 | 本模块常量 | 状态字段 | 覆写参数 | 执行点 |
|-------------|-----------|---------|---------|--------|
| max_turns | `DEFAULT_MAX_TURNS` | `budget.turns_max` | `--max-turns` | `budget` 子命令触顶告警 |
| max_token | `DEFAULT_MAX_TOKENS` | `budget.tokens_max` | `--max-tokens` | `budget` 子命令触顶告警 |
| max_time | `DEFAULT_MAX_TIME` | `budget.max_time_sec` | `--max-time` | `advance` / `resume` / `budget` 超时拒绝 |
| circuit_breaker | `DEFAULT_MAX_FAILURES` | `budget.max_failures` | `--max-failures` | `fail` 子命令累计失败并熔断 |

- `max_time` 起算点：`budget.started_at`（init 时与 `created_at` 同值落盘；
  旧状态文件缺该字段时回退到 `created_at`）。
- 超时判定：`elapsed = now - started_at`，`elapsed >= budget.max_time_sec` 即触顶。
- 熔断判定：`budget.failures >= budget.max_failures` 即熔断。
- 上限覆写只在意图明确的子命令生效：`init`（四项全量）、`budget`（四项全量）、
  `fail`（仅 `--max-failures`）；`advance` / `resume` / `finish` 只接受这些参数但不
  改写已落盘的上限，避免「跑一次 advance 顺手把天花板抬了」。

## 按序推进门禁（sequential advance gate）

`advance` 的目标阶段必须等于**当前阶段的下一个阶段**（阶段序列读 `PHASES`，禁止硬编码）：

- 跳级 → 退出码 **1**，stderr 打印当前阶段 / 目标阶段 / 期望阶段三要素。
- 逃生阀 `--force`：允许跳级，但**必须**同时给非空 `--force-reason`；
  缺理由 → 退出码 1。用了 force 一定在 `notes` 里留痕，并打印
  `⚠️ 越级推进（force）`。
- `--force-reason` 单独出现（未写 `--force`）时**隐含开启** force：既然主理人已经
  给出了越级理由，就不必再敲一次开关；此时理由非空校验照常生效。

### 边界：`init` 之后的第一次推进为什么可以指向 FREEZE 本身

`init` 已把 `phase` 置为 `PHASES[0]`（FREEZE）且 `turn=0`、`checkpoints=[]`——
此刻 FREEZE 阶段**尚未产出任何检查点**，状态里的 `phase` 表达的是「当前所处的阶段」，
而不是「已完成到哪一步」。因此第一条检查点必须记在 FREEZE 上，否则 FREEZE 阶段的
产物（冻结后的任务定义）无处落盘，`turn` 与 `checkpoints` 也会从 IDENTIFY 起步，
与协议 §3 的检查点示例（cp-001 = FREEZE）不一致。

判定规则（`_expected_next_phase`）：当 `turn == 0` 且 `checkpoints` 为空且
`phase == PHASES[0]` 时，期望目标 = `PHASES[0]`（FREEZE，记为第 1 个检查点）；
此后一律严格 next——目标必须等于当前阶段的后继阶段。末阶段（NEXT）之后无后继，
任何推进都属越界（可用 force 显式声明）。

## 熔断（circuit breaker）后的状态语义

熔断是**终态**，不是提示：

- `fail` 累计失败次数达到 `budget.max_failures` → 立刻置 `status = "aborted"`、
  `abort_reason = "circuit_breaker"`，并打印
  `🛑 熔断：同一 task 失败 N 次 → 自动熔断 + 升级用户`。
- 超时同样是终态：`abort_reason = "max_time"`。
- `status == "aborted"` 后，`advance` 与 `fail` **一律拒绝**（退出码 1），
  不再接受任何新的阶段推进或失败计数，避免熔断后继续空转。
- `finish` 在熔断后**仍然允许**（退出码 0）：它用于归档收尾与 metrics 落盘，
  但**不改写** `status = "aborted"`（熔断信号不得被「标记完成」抹掉），只追加 metrics
  与一条「熔断收尾」备注，并打印告警说明。
- `resume` 在熔断后打印熔断原因与「升级用户」指引，不再给出「继续下一阶段」的建议。

## 状态 JSON 结构（v2.3.0）

```jsonc
{
  "version": 1,
  "task_id": "trace-xxx-001",
  "created_at": "2026-11-09T10:00:00",   // 计时起点（与 budget.started_at 同值）
  "updated_at": "2026-11-09T10:07:30",
  "status": "running",                    // running | done | aborted
  "abort_reason": null,                   // null | max_time | circuit_breaker
  "phase": "FREEZE",                      // 当前所处阶段（读 PHASES）
  "turn": 0,                              // 已完成的检查点数
  "checkpoints": [{"turn": 1, "phase": "FREEZE", "ts": "...", "snapshot_ref": "state://cp-001"}],
  "perception": {},                       // 四维感知（init 时由主理人传入）
  "budget": {
    "turns_used": 0, "turns_max": 30,
    "tokens_used": 0, "tokens_max": 200000,
    "max_time_sec": 1800,                 // max_time 上限（秒）
    "started_at": "2026-11-09T10:00:00",  // max_time 起算点
    "failures": 0,                        // 累计失败次数（fail 子命令 +1）
    "max_failures": 5                     // circuit_breaker 阈值
  },
  "notes": [{"ts": "...", "phase": "FREEZE", "note": "..."}],
  "metrics": null                         // finish 时落盘 4 个 metrics；未 finish 时为 null
}
```

`metrics` 的 4 个键与取值口径（未上报一律 null，**禁止用 0 冒充未上报**）：

| 键 | 含义 | 来源 |
|----|------|------|
| `success_rate` | 成功率（单任务态：正常收尾 1，熔断中止 0） | 由状态推导 |
| `avg_tool_calls_per_task` | 平均 tool call 次数 / 任务 | 主理人上报：`finish --tool-calls N`；未上报 = `null` |
| `retries_per_task` | 重试次数 / 任务 | 由状态推导：等于 `budget.failures` |
| `next_actions_presence_rate` | 失败时 next_actions 字段存在率 | 主理人上报：`finish --next-actions-present`（1）/ `--next-actions-missing`（0）；未上报 = `null` |

## 用法

  # 1. 开工：初始化状态（已存在则原样返回，幂等）
  python3 state_io.py init --task-id trace-h9n2-001 \
    --workspace /path/to/project --perception '{"completeness":35,"assumption_density":8}'

  # 2. 每阶段收尾：推进阶段 + 写检查点指针（按序，越级需 --force + --force-reason）
  python3 state_io.py advance --task-id trace-h9n2-001 --phase CLARIFY \
    --checkpoint cp-003 --workspace /path/to/project \
    --note "完整度达 92%，可进入 ALIGN"

  # 3. 中断恢复：读取状态，打印下一步
  python3 state_io.py resume --task-id trace-h9n2-001 --workspace /path/to/project

  # 4. 收尾：标记任务完成（可同时上报 4 个 metrics）
  python3 state_io.py finish --task-id trace-h9n2-001 --workspace /path/to/project \
    --tool-calls 12 --next-actions-present

  # 5. 预算更新（可选，主理人每轮清点）
  python3 state_io.py budget --task-id trace-h9n2-001 --turns 5 --tokens 42000 \
    --workspace /path/to/project

  # 6. 失败登记（累计到阈值自动熔断）
  python3 state_io.py fail --task-id trace-h9n2-001 --workspace /path/to/project \
    --reason "检索源三源全败，无可用证据"

## 退出码

  0 = 成功
  1 = 用法/参数错误（含 --task-id 缺失、跳级未 force、熔断后拒绝推进）
  2 = 状态文件不存在（resume/advance/finish/budget/fail 遇到未 init 的任务）
  3 = JSON 解析失败（状态文件被外部破坏，fail fast 不静默重建）

## 依赖

仅标准库，Python >= 3.9。原子写：PID 隔离 .tmp + os.replace；
写操作（init/advance/finish/budget/fail/resume 的熔断置位）经 flock 互斥锁串行化
（把协议 §3「写入者=仅主理人」的纸面约定固化为工程约束，
非 POSIX 平台退化为无锁 + 约定兜底）。
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import re
import sys
from pathlib import Path

try:
    import fcntl  # POSIX 互斥锁；非 POSIX 平台退化为无锁（见 _state_lock）
except ImportError:  # pragma: no cover
    fcntl = None

# 八阶段状态机的合法阶段序列（顺序即推进方向）
PHASES = ["FREEZE", "IDENTIFY", "COLLAPSE", "CLARIFY", "ALIGN",
          "EXECUTE", "REVIEW", "NEXT"]

# registry §Loop 终止硬上限（编排层默认值，主理人可用 --max-* 覆写）
DEFAULT_MAX_TURNS = 30
DEFAULT_MAX_TOKENS = 200000
DEFAULT_MAX_TIME = 1800        # max_time：单任务总时长上限（秒）
DEFAULT_MAX_FAILURES = 5       # circuit_breaker：同一 task 失败次数阈值

STATE_VERSION = 1

# ── status 取值（协议 §3 生命周期）────────────────────────────────────────
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_ABORTED = "aborted"

# ── 熔断原因标识（落盘到 state["abort_reason"]）────────────────────────────
ABORT_REASON_MAX_TIME = "max_time"
ABORT_REASON_CIRCUIT_BREAKER = "circuit_breaker"

# ── metrics 的 4 个键（registry §评估与观测 定义的 4 个 metrics）───────────
METRIC_KEYS = (
    "success_rate",
    "avg_tool_calls_per_task",
    "retries_per_task",
    "next_actions_presence_rate",
)


# ── 基础工具 ────────────────────────────────────────────────────────────

def runs_dir(workspace: Path) -> Path:
    """状态根目录：<workspace>/.harness-runs/。"""
    return workspace / ".harness-runs"


def state_path(workspace: Path, task_id: str) -> Path:
    return runs_dir(workspace) / task_id / "_state.json"


# checkpoint / task_id 的合法名字（R3-P0-1 + R3-P1-2）
#   checkpoint：裸 cp-NNN（3 位以上数字）。协议标准形态 state://cp-NNN 在
#   cmd_advance 入口先剥前缀再校验——两个组件对同一 pointer 的形态约定
#   必须一致（R3 再诊断实锤：直接拼路径会产出 checkpoints/state:/x.md）。
#   task_id：用于目录名，禁止路径分隔符与 ..（防 runs 根外的任意落盘）。
_CP_NAME_RE = re.compile(r"^cp-\d{3,}$")
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _normalize_checkpoint_name(raw) -> str | None:
    """归一化 checkpoint 名：接受 `state://cp-NNN` 与裸 `cp-NNN`。

    返回值有三种语义，**调用方必须区分**：
      - `""`   = 本次推进不带检查点（raw 为 None / 空串 / 全空白）——合法；
      - 裸名   = 合法检查点（如 `cp-001`），调用方据此落盘；
      - `None` = 非法形态（路径元字符、前缀剥除后不匹配等）——调用方判错。

    把「未传」也返回 None 会让 `cmd_advance` 误拒不带检查点的正常推进
    （R3 续跑实测 rc=1、期望 0），因此空值与非法值必须分开。
    """
    if raw is None or not str(raw).strip():
        return ""
    name = str(raw).strip()
    if name.startswith("state://"):
        name = name[len("state://"):]
    return name if _CP_NAME_RE.match(name) else None


def _validate_task_id(task_id: str) -> str | None:
    """消毒 task_id：仅字母数字/点/下划线/连字符，1~64 字符，不以符号开头后接。

    返回原值（合法）或 None（非法）。非法时调用方优雅报错 rc=2。
    """
    if task_id and _TASK_ID_RE.match(task_id):
        return task_id
    return None


def _atomic_write(path: Path, text: str) -> None:
    """原子写：先写 .tmp 再 os.replace，中断不会留下半截 JSON。

    tmp 文件名按 PID 隔离：即使无锁环境（非 POSIX 退化路径）下多进程
    并发，也不会出现「A 的 os.replace 把 B 正在写的 tmp 搬走」互踩崩溃。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)  # POSIX 上原子


@contextlib.contextmanager
def _state_lock(workspace: Path, task_id: str):
    """同一任务写操作的互斥锁（flock，跨进程）。

    背景（v2.2.0 冻结前实测）：cmd_advance 是 read-modify-write，
    20 路并发 advance 时 19/20 因共享 tmp 互踩 / 丢更新而失败。
    协议 §3 约定「写入者=仅主理人（串行）」，本锁把该纸面约定固化
    为工程约束：即便被误用并发，也退化为排队执行而非数据损坏或崩溃。
    """
    lock = runs_dir(workspace) / task_id / "_state.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:  # 非 POSIX：依赖单写入者约定 + PID 隔离 tmp 兜底
        yield
        return
    with open(lock, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def load_state(workspace: Path, task_id: str) -> dict:
    p = state_path(workspace, task_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"❌ 状态文件损坏（fail fast，不静默重建）: {p}\n   {exc}", file=sys.stderr)
        sys.exit(3)


def save_state(workspace: Path, task_id: str, state: dict) -> None:
    _atomic_write(state_path(workspace, task_id),
                  json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── 状态字段读取与补齐（向后兼容旧状态文件）──────────────────────────────

def _budget(state: dict) -> dict:
    """取 budget 子结构并补齐缺失字段（v2.3.0 之前落盘的状态文件也能读）。

    补齐项：max_time_sec / started_at / failures / max_failures 及其余计数字段。
    started_at 缺失时回退到 created_at（旧状态文件的计时起点就是创建时刻）。
    """
    b = state.setdefault("budget", {})
    b.setdefault("turns_used", 0)
    b.setdefault("turns_max", DEFAULT_MAX_TURNS)
    b.setdefault("tokens_used", 0)
    b.setdefault("tokens_max", DEFAULT_MAX_TOKENS)
    b.setdefault("max_time_sec", DEFAULT_MAX_TIME)
    b.setdefault("failures", 0)
    b.setdefault("max_failures", DEFAULT_MAX_FAILURES)
    if not b.get("started_at"):
        b["started_at"] = state.get("created_at")
    return b


def _parse_iso(ts) -> datetime.datetime | None:
    """解析 ISO 时间串；不可解析返回 None（不猜、不编造）。"""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts)
    except ValueError:
        return None


def _elapsed_seconds(state: dict) -> int | None:
    """已用秒数 = now - budget.started_at；起点缺失或不可解析时返回 None。"""
    b = _budget(state)
    start = _parse_iso(b.get("started_at")) or _parse_iso(state.get("created_at"))
    if start is None:
        return None
    return int((datetime.datetime.now() - start).total_seconds())


def _time_exceeded(state: dict) -> tuple[bool, int | None]:
    """是否已触 max_time 上限。返回 (是否触顶, 已用秒数)。

    判定口径：`elapsed >= budget.max_time_sec`（与 turns/tokens 的「触顶」口径一致）。
    起点缺失时无法判定，返回 (False, None)——不因缺数据而误杀。
    """
    limit = int(_budget(state).get("max_time_sec", DEFAULT_MAX_TIME))
    elapsed = _elapsed_seconds(state)
    if elapsed is None:
        return False, None
    return elapsed >= limit, elapsed


def _note(state: dict, phase: str, note: str) -> None:
    """往 notes 里追加一条带时间戳的备注。"""
    state.setdefault("notes", []).append(
        {"ts": now_iso(), "phase": phase, "note": note})


def _mark_aborted(state: dict, reason: str, note: str) -> None:
    """置熔断终态：status=aborted + abort_reason=reason + 留痕。"""
    state["status"] = STATUS_ABORTED
    state["abort_reason"] = reason
    _note(state, state.get("phase"), note)


def _apply_ceiling_overrides(state: dict, args) -> None:
    """把显式传入的上限覆写写回 budget（未传的项不动已落盘值）。"""
    b = _budget(state)
    if getattr(args, "max_turns", None) is not None:
        b["turns_max"] = int(args.max_turns)
    if getattr(args, "max_tokens", None) is not None:
        b["tokens_max"] = int(args.max_tokens)
    if getattr(args, "max_time", None) is not None:
        b["max_time_sec"] = int(args.max_time)
    if getattr(args, "max_failures", None) is not None:
        b["max_failures"] = int(args.max_failures)


def _expected_next_phase(state: dict) -> str | None:
    """按序推进门禁：期望的下一个阶段（None = 末阶段之后，已无后继）。

    边界约定见模块 docstring「按序推进门禁」节：
    `init` 之后（turn==0 且 checkpoints 为空且 phase=FREEZE）第一次推进的目标
    就是 FREEZE 本身（记为第 1 个检查点）；此后严格取当前阶段的后继阶段。
    """
    phase = state.get("phase")
    if (int(state.get("turn", 0)) == 0
            and not state.get("checkpoints")
            and phase == PHASES[0]):
        return PHASES[0]
    if phase not in PHASES:
        return None
    idx = PHASES.index(phase)
    if idx + 1 >= len(PHASES):
        return None
    return PHASES[idx + 1]


def _force_enabled(args) -> bool:
    """是否开启越级逃生阀：`--force` 或给了非空 `--force-reason` 均可。"""
    reason = (getattr(args, "force_reason", None) or "").strip()
    return bool(getattr(args, "force", False)) or bool(reason)


def _warn_ignored_ceilings(args) -> None:
    """advance / resume / finish 不改写已落盘的上限——显式传入时必须说明被忽略。

    上限的写入口只有两个：`init`（开局一次性设定）与 `budget`（跑起来后调整）。
    若在 advance / resume / finish 上传 `--max-turns` 等参数而静默丢弃，
    调用方会以为天花板被抬了——这是典型的「静默假绿」，必须显式告知。
    """
    ignored = [name for name in ("max_turns", "max_tokens", "max_time", "max_failures")
               if getattr(args, name, None) is not None]
    if ignored:
        print(f"⚠️ 本子命令不改写上限，已忽略参数: {', '.join('--' + n.replace('_', '-') for n in ignored)}"
              f"（上限写入口只有 init 与 budget）", file=sys.stderr)


def _format_elapsed(state: dict) -> str:
    elapsed = _elapsed_seconds(state)
    return "未知" if elapsed is None else f"{elapsed}s"


# ── 子命令实现 ──────────────────────────────────────────────────────────

def cmd_init(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    with _state_lock(ws, args.task_id):
        existing = load_state(ws, args.task_id)
        if existing is not None:
            print(f"↩️ 任务已存在，幂等返回: {state_path(ws, args.task_id)}")
            print(f"   当前阶段: {existing['phase']}（turn {existing['turn']}）")
            return 0
        perception = {}
        if args.perception:
            try:
                perception = json.loads(args.perception)
            except ValueError:
                print(f"❌ --perception 不是合法 JSON: {args.perception!r}", file=sys.stderr)
                return 1
        created = now_iso()
        state = {
            "version": STATE_VERSION,
            "task_id": args.task_id,
            "created_at": created,
            "updated_at": created,
            "status": STATUS_RUNNING,        # running | done | aborted
            "abort_reason": None,            # null | max_time | circuit_breaker
            "phase": PHASES[0],
            "turn": 0,
            "checkpoints": [],               # [{turn, phase, ts, snapshot_ref}]
            "perception": perception,
            "budget": {
                "turns_used": 0,
                "turns_max": (args.max_turns if args.max_turns is not None
                              else DEFAULT_MAX_TURNS),
                "tokens_used": 0,
                "tokens_max": (args.max_tokens if args.max_tokens is not None
                               else DEFAULT_MAX_TOKENS),
                # max_time：起算点与 created_at 同值，旧状态文件回退到 created_at
                "max_time_sec": (args.max_time if args.max_time is not None
                                 else DEFAULT_MAX_TIME),
                "started_at": created,
                # circuit_breaker：失败计数与阈值
                "failures": 0,
                "max_failures": (args.max_failures if args.max_failures is not None
                                 else DEFAULT_MAX_FAILURES),
            },
            "notes": [],
            "metrics": None,                 # finish 时落盘 4 个 metrics
        }
        save_state(ws, args.task_id, state)
    print(f"✅ 状态已初始化: {state_path(ws, args.task_id)}")
    print(f"   阶段序列: {' → '.join(PHASES)}")
    print(f"   硬上限: turns {state['budget']['turns_max']} · "
          f"tokens {state['budget']['tokens_max']} · "
          f"max_time {state['budget']['max_time_sec']}s · "
          f"max_failures {state['budget']['max_failures']}")
    return 0


def cmd_advance(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    _warn_ignored_ceilings(args)
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}（先跑 init）", file=sys.stderr)
            return 2
        if args.phase not in PHASES:
            print(f"❌ 非法阶段 {args.phase!r}，合法值: {'/'.join(PHASES)}", file=sys.stderr)
            return 1
        # 熔断终态：拒绝任何推进，避免熔断后继续空转
        if state.get("status") == STATUS_ABORTED:
            print(f"❌ 拒绝推进：任务已熔断（status={STATUS_ABORTED}，原因: "
                  f"{state.get('abort_reason') or '未知'}）→ 按协议升级用户，不空转",
                  file=sys.stderr)
            return 1
        if state.get("status") == STATUS_DONE:
            print(f"❌ 拒绝推进：任务已完成（status={STATUS_DONE}）→ "
                  f"如需返工请新建 task_id", file=sys.stderr)
            return 1
        # max_time 触顶：拒绝推进并置熔断终态
        exceeded, elapsed = _time_exceeded(state)
        if exceeded:
            limit = _budget(state)["max_time_sec"]
            msg = (f"⚠️ 时长触顶（max_time）: 已用 {elapsed}s ≥ 上限 {limit}s "
                   f"→ 按协议熔断：升级用户，不空转")
            print(msg, file=sys.stderr)
            _mark_aborted(state, ABORT_REASON_MAX_TIME, msg)
            state["updated_at"] = now_iso()
            save_state(ws, args.task_id, state)
            print("❌ 拒绝推进：任务已因超时熔断（status=aborted）", file=sys.stderr)
            return 1
        # 按序推进门禁
        expected = _expected_next_phase(state)
        cur = state.get("phase")
        force = _force_enabled(args)
        reason = (getattr(args, "force_reason", None) or "").strip()
        if getattr(args, "force", False) and not reason:
            print("❌ --force 需要同时给非空 --force-reason（否则禁止越级推进）",
                  file=sys.stderr)
            return 1
        # ── checkpoint 形态归一化与消毒（R3-P0-1）──
        # 协议标准形态是 `state://cp-NNN`（protocol_check.py 的
        # CHECKPOINT_POINTER_PATTERN 即此形态），本函数此前的实现却按
        # 「裸 cp-NNN」设计：直接把参数拼进文件路径。主理人按协议文档
        # 传 `state://cp-002` 时，拼出 `checkpoints/state:/cp-002.md`——
        # 父目录不存在 → 裸 Traceback（rc=1 但输出是堆栈，无业务报错）。
        # 本块把两种形态归一到裸 cp-NNN，并拒绝任何路径元字符（防穿越）。
        cp_name = _normalize_checkpoint_name(args.checkpoint)
        if cp_name is None:
            print(f"❌ 非法 checkpoint 名 {args.checkpoint!r}（归一化后须匹配 "
                  f"cp-\\d{{3,}}；接受 `state://cp-NNN` 或裸 `cp-NNN`；"
                  f"禁止路径分隔符与 ..）", file=sys.stderr)
            return 1
        skipped = args.phase != expected
        if skipped and not force:
            print(f"❌ 越级推进被拒：当前阶段 {cur}，目标阶段 {args.phase}，"
                  f"期望阶段 {expected if expected else '（末阶段，已无后继）'}"
                  f"（按序推进门禁）", file=sys.stderr)
            print("   如确需越级，请加 --force 并同时给非空 --force-reason",
                  file=sys.stderr)
            return 1
        state["phase"] = args.phase
        state["turn"] += 1
        state["updated_at"] = now_iso()
        state["budget"]["turns_used"] = state["turn"]
        cp = {"turn": state["turn"], "phase": args.phase,
              "ts": now_iso(), "snapshot_ref": None}
        if cp_name:
            # state://cp-NNN ≡ .harness-runs/<task_id>/checkpoints/cp-NNN.md
            cp["snapshot_ref"] = f"state://{cp_name}"
            cp_dir = runs_dir(ws) / args.task_id / "checkpoints"
            cp_dir.mkdir(parents=True, exist_ok=True)
            marker = cp_dir / f"{cp_name}.md"
            if not marker.exists():
                marker.write_text(
                    f"# {cp_name}\n\n- phase: {args.phase}\n- ts: {cp['ts']}\n"
                    f"- note: {args.note or ''}\n\n"
                    f"（本文件为检查点指针：阶段产物应落盘于此目录，指针可被 resume 解析）\n",
                    encoding="utf-8")
        state["checkpoints"].append(cp)
        if args.note:
            _note(state, args.phase, args.note)
        if force:
            # 用了 force 一定留痕（目标恰为期望阶段时同样留痕，说明是显式声明）
            _note(state, args.phase,
                  f"⚠️ 越级推进（force）: {cur} → {args.phase}"
                  f"（期望 {expected if expected else '（末阶段，已无后继）'}）｜理由: {reason}")
        save_state(ws, args.task_id, state)
    print(f"✅ 已推进到 {args.phase}（turn {state['turn']}/{state['budget']['turns_max']}）")
    if cp_name:
        print(f"   检查点: {cp['snapshot_ref']} → checkpoints/{cp_name}.md")
    if force:
        if skipped:
            print(f"⚠️ 越级推进（force）: {cur} → {args.phase}"
                  f"（期望 {expected if expected else '（末阶段，已无后继）'}），理由: {reason}")
        else:
            print(f"⚠️ 越级推进（force）已声明但本次目标即为期望下一阶段: "
                  f"{cur} → {args.phase}，理由: {reason}")
    return 0


def cmd_resume(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    _warn_ignored_ceilings(args)
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 无状态文件: {state_path(ws, args.task_id)}（该任务未在本工作区跑过）",
                  file=sys.stderr)
            return 2
        # max_time 触顶 → 置熔断终态（写操作，必须走锁 + save_state）
        exceeded, elapsed = _time_exceeded(state)
        if exceeded and state.get("status") != STATUS_ABORTED:
            limit = _budget(state)["max_time_sec"]
            msg = (f"⚠️ 时长触顶（max_time）: 已用 {elapsed}s ≥ 上限 {limit}s "
                   f"→ 按协议熔断：升级用户，不空转")
            print(msg, file=sys.stderr)
            _mark_aborted(state, ABORT_REASON_MAX_TIME, msg)
            state["updated_at"] = now_iso()
            save_state(ws, args.task_id, state)
    b = _budget(state)
    print(f"📋 任务 {state['task_id']} 恢复点")
    print(f"   status     : {state['status']}"
          + (f"（原因: {state.get('abort_reason')}）" if state.get("abort_reason") else ""))
    print(f"   当前阶段   : {state['phase']}（turn {state['turn']}）")
    print(f"   最后更新   : {state['updated_at']}")
    if state.get("checkpoints"):
        last = state["checkpoints"][-1]
        print(f"   最后检查点 : {last['snapshot_ref']}（{last['phase']}，{last['ts']}）")
    if state.get("notes"):
        print(f"   最近备注   : {state['notes'][-1]['note']}")
    print(f"   预算       : turns {b['turns_used']}/{b['turns_max']} · "
          f"tokens {b['tokens_used']}/{b['tokens_max']} · "
          f"已用时长 {_format_elapsed(state)}/{b['max_time_sec']}s · "
          f"失败 {b['failures']}/{b['max_failures']}")
    if state["status"] == STATUS_DONE:
        print("   → 任务已完成，无需续跑")
    elif state["status"] == STATUS_ABORTED:
        print("   → 🛑 任务已熔断（按协议升级用户，不空转）；"
              "advance / fail 均已拒绝")
    else:
        nxt = _expected_next_phase(state)
        print(f"   → 断点续跑：从 {nxt if nxt else '（当前即末阶段）'} 阶段继续"
              f"（不重跑已完成阶段）")
    return 0


def cmd_finish(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    _warn_ignored_ceilings(args)
    if args.next_actions_present and args.next_actions_missing:
        print("❌ --next-actions-present 与 --next-actions-missing 互斥，只能选其一",
              file=sys.stderr)
        return 1
    if args.tool_calls is not None and args.tool_calls < 0:
        print(f"❌ --tool-calls 不能为负: {args.tool_calls}", file=sys.stderr)
        return 1
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}", file=sys.stderr)
            return 2
        b = _budget(state)
        aborted = state.get("status") == STATUS_ABORTED
        # 已上报过的指标在重复 finish 时保留——防止「后一次不带参数」把前一次
        # 上报的真实值擦成 null（那会凭空制造「未采集」的假象）。
        prev = state.get("metrics") or {}
        prev_calls = prev.get("avg_tool_calls_per_task")
        prev_next = prev.get("next_actions_presence_rate")
        # 4 个 metrics：可推导的从状态推导，不可推导的由主理人上报，未上报 = null
        metrics = {
            # 成功率：单任务态下，正常收尾记 1，熔断中止记 0
            "success_rate": 0 if aborted else 1,
            # 平均 tool call 次数 / 任务：主理人上报，未上报为 null（不填 0 冒充）
            "avg_tool_calls_per_task": (args.tool_calls if args.tool_calls is not None
                                        else prev_calls),
            # 重试次数 / 任务：由失败计数推导
            "retries_per_task": int(b.get("failures", 0)),
            # 失败时 next_actions 字段存在率：主理人上报，未上报为 null
            "next_actions_presence_rate": (1.0 if args.next_actions_present
                                            else (0.0 if args.next_actions_missing
                                                  else prev_next)),
        }
        state["metrics"] = metrics
        if aborted:
            # 熔断终态不被「标记完成」抹掉：只归档 metrics + 留痕
            _note(state, state.get("phase"),
                  "熔断后收尾：已落盘 metrics，status 保持 aborted（不改为 done）")
            state["updated_at"] = now_iso()
            save_state(ws, args.task_id, state)
        else:
            state["status"] = STATUS_DONE
            state["updated_at"] = now_iso()
            save_state(ws, args.task_id, state)
    print(f"✅ 任务标记完成: {state['task_id']}")
    if aborted:
        print("⚠️ 任务此前已熔断（status=aborted）: 本次 finish 仅归档 metrics，"
              "不覆盖熔断状态")
    print("📊 4 个 metrics（未上报项记 null，不以 0 冒充）")
    print(f"   成功率（success_rate）              : {metrics['success_rate']}")
    print(f"   平均 tool call 次数/任务            : {metrics['avg_tool_calls_per_task']}")
    print(f"   重试次数/任务（retries_per_task）    : {metrics['retries_per_task']}")
    print(f"   失败时 next_actions 存在率          : {metrics['next_actions_presence_rate']}")
    return 0


def cmd_budget(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}", file=sys.stderr)
            return 2
        _apply_ceiling_overrides(state, args)
        if args.turns is not None:
            state["budget"]["turns_used"] = args.turns
        if args.tokens is not None:
            state["budget"]["tokens_used"] = args.tokens
        # max_time 触顶 → 置熔断终态
        exceeded, elapsed = _time_exceeded(state)
        if exceeded and state.get("status") != STATUS_ABORTED:
            limit = state["budget"]["max_time_sec"]
            msg = (f"⚠️ 时长触顶（max_time）: 已用 {elapsed}s ≥ 上限 {limit}s "
                   f"→ 按协议熔断：升级用户，不空转")
            _mark_aborted(state, ABORT_REASON_MAX_TIME, msg)
        state["updated_at"] = now_iso()
        save_state(ws, args.task_id, state)
        b = state["budget"]
    warn = ""
    if b["turns_used"] >= b["turns_max"] or b["tokens_used"] >= b["tokens_max"]:
        warn = "  ⚠️ 预算触顶 → 按协议熔断：升级用户，不空转"
    print(f"✅ 预算已更新: turns {b['turns_used']}/{b['turns_max']} · "
          f"tokens {b['tokens_used']}/{b['tokens_max']} · "
          f"已用时长 {_format_elapsed(state)}/{b['max_time_sec']}s{warn}")
    if exceeded:
        print(f"⚠️ 时长触顶（max_time）→ 按协议熔断：升级用户，不空转"
              f"（status 已置 {state.get('status')}）")
    return 0


def cmd_fail(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    reason = (args.reason or "").strip()
    if not reason:
        print("❌ --reason 不能为空（失败必须带具体原因，不接受空泛登记）",
              file=sys.stderr)
        return 1
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}", file=sys.stderr)
            return 2
        if state.get("status") == STATUS_ABORTED:
            print(f"❌ 拒绝登记失败：任务已熔断（status={STATUS_ABORTED}，原因: "
                  f"{state.get('abort_reason') or '未知'}）→ 按协议升级用户，不空转",
                  file=sys.stderr)
            return 1
        if state.get("status") == STATUS_DONE:
            print(f"❌ 拒绝登记失败：任务已完成（status={STATUS_DONE}）", file=sys.stderr)
            return 1
        # max_time 触顶：失败登记同样不再受理，置熔断终态
        exceeded, elapsed = _time_exceeded(state)
        if exceeded:
            limit = _budget(state)["max_time_sec"]
            msg = (f"⚠️ 时长触顶（max_time）: 已用 {elapsed}s ≥ 上限 {limit}s "
                   f"→ 按协议熔断：升级用户，不空转")
            print(msg, file=sys.stderr)
            _mark_aborted(state, ABORT_REASON_MAX_TIME, msg)
            state["updated_at"] = now_iso()
            save_state(ws, args.task_id, state)
            print("❌ 拒绝登记失败：任务已因超时熔断（status=aborted）", file=sys.stderr)
            return 1
        b = _budget(state)
        if getattr(args, "max_failures", None) is not None:
            b["max_failures"] = int(args.max_failures)
        b["failures"] = int(b.get("failures", 0)) + 1
        failures = b["failures"]
        limit = int(b.get("max_failures", DEFAULT_MAX_FAILURES))
        _note(state, state.get("phase"), f"❌ 失败登记 #{failures}: {reason}")
        tripped = failures >= limit
        if tripped:
            _mark_aborted(state, ABORT_REASON_CIRCUIT_BREAKER,
                          f"🛑 熔断：同一 task 失败 {limit} 次 → 自动熔断 + 升级用户")
        state["updated_at"] = now_iso()
        save_state(ws, args.task_id, state)
    print(f"✅ 已记录失败 #{failures}/{limit}: {reason}")
    if tripped:
        print(f"🛑 熔断：同一 task 失败 {limit} 次 → 自动熔断 + 升级用户"
              f"（status=aborted，此后 advance / fail 一律拒绝）")
    return 0


class _Parser(argparse.ArgumentParser):
    """参数错误以退出码 1 结束（与模块 docstring 的退出码契约一致）。"""

    def error(self, message):  # noqa: D102 - 覆写 argparse 默认行为
        self.print_usage(sys.stderr)
        print(f"❌ 参数错误: {message}", file=sys.stderr)
        raise SystemExit(1)


def main(argv=None) -> int:
    parser = _Parser(
        description="协议 §3 状态持久化（init/advance/resume/finish/budget/fail）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--task-id", required=True, help="任务 ID（=trace_id）")
        p.add_argument("--workspace", required=True, help="工作区根目录")
        # 上限覆写：default=None 表示「未指定」，由各子命令按语义解析
        # （init/budget 落盘生效，fail 仅 --max-failures 生效）
        p.add_argument("--max-turns", type=int, default=None,
                       help=f"编排层单任务轮次上限（默认 {DEFAULT_MAX_TURNS}）")
        p.add_argument("--max-tokens", type=int, default=None,
                       help=f"编排层单任务 token 上限（默认 {DEFAULT_MAX_TOKENS}）")
        p.add_argument("--max-time", type=int, default=None,
                       help=f"编排层单任务时长上限（秒，默认 {DEFAULT_MAX_TIME}）")
        p.add_argument("--max-failures", type=int, default=None,
                       help=f"circuit_breaker 失败次数阈值（默认 {DEFAULT_MAX_FAILURES}）")

    p = sub.add_parser("init", help="初始化任务状态（幂等）")
    add_common(p)
    p.add_argument("--perception", default=None, help="四维感知 JSON（可选）")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("advance", help="推进阶段 + 写检查点（按序，越级需 force）")
    add_common(p)
    p.add_argument("--phase", required=True, help=f"目标阶段（{'/'.join(PHASES)}）")
    p.add_argument("--checkpoint", default=None, help="检查点名（如 cp-003）")
    p.add_argument("--note", default=None, help="阶段收尾备注")
    p.add_argument("--force", action="store_true",
                   help="允许越级推进（必须同时给非空 --force-reason）")
    p.add_argument("--force-reason", default=None,
                   help="越级推进理由（非空；不给理由则 --force 视为用法错误）")
    p.set_defaults(fn=cmd_advance)

    p = sub.add_parser("resume", help="中断恢复：打印续跑点")
    add_common(p)
    p.set_defaults(fn=cmd_resume)

    p = sub.add_parser("finish", help="标记任务完成（可上报 4 个 metrics）")
    add_common(p)
    p.add_argument("--tool-calls", type=int, default=None,
                   help="本任务的 tool call 总次数（未上报则 metrics 记 null）")
    p.add_argument("--next-actions-present", action="store_true",
                   help="上报：失败路径的 next_actions 字段存在（存在率记 1）")
    p.add_argument("--next-actions-missing", action="store_true",
                   help="上报：失败路径的 next_actions 字段缺失（存在率记 0）")
    p.set_defaults(fn=cmd_finish)

    p = sub.add_parser("budget", help="更新预算计数")
    add_common(p)
    p.add_argument("--turns", type=int, default=None)
    p.add_argument("--tokens", type=int, default=None)
    p.set_defaults(fn=cmd_budget)

    p = sub.add_parser("fail", help="登记一次失败（累计到阈值自动熔断）")
    add_common(p)
    p.add_argument("--reason", required=True, help="失败原因（具体、不可为空）")
    p.set_defaults(fn=cmd_fail)

    args = parser.parse_args(argv)
    # ── task_id 统一消毒（R3-P1-2）──
    # task_id 直接拼进 runs/<task_id>/ 目录名。实锤：`--task-id "a/b"` 会
    # 在 runs 根下建子目录、`..` 可穿越到 runs 外。所有子命令入口在此
    # 统一拦截，非法值优雅报错 rc=2（与「任务未初始化」同语义层）。
    if not hasattr(args, "task_id"):
        return parser.error("内部错误：子命令缺少 task_id")
    if _validate_task_id(args.task_id) is None:
        print(f"❌ 非法 task_id {args.task_id!r}（仅允许字母/数字/点/下划线/连字符，"
              f"1~64 字符，禁止路径分隔符与 ..）", file=sys.stderr)
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
