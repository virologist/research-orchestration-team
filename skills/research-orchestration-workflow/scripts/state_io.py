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

## 用法

  # 1. 开工：初始化状态（已存在则原样返回，幂等）
  python3 state_io.py init --task-id trace-h9n2-001 \
    --workspace /path/to/project --perception '{"completeness":35,"assumption_density":8}'

  # 2. 每阶段收尾：推进阶段 + 写检查点指针
  python3 state_io.py advance --task-id trace-h9n2-001 --phase CLARIFY \
    --checkpoint cp-003 --workspace /path/to/project \
    --note "完整度达 92%，可进入 ALIGN"

  # 3. 中断恢复：读取状态，打印下一步
  python3 state_io.py resume --task-id trace-h9n2-001 --workspace /path/to/project

  # 4. 收尾：标记任务完成（供 LEARNING.md 汇总与目录归档判断）
  python3 state_io.py finish --task-id trace-h9n2-001 --workspace /path/to/project

  # 5. 预算更新（可选，主理人每轮清点）
  python3 state_io.py budget --task-id trace-h9n2-001 --turns 5 --tokens 42000 \
    --workspace /path/to/project

## 退出码

  0 = 成功
  1 = 用法/参数错误（含 --task-id 缺失）
  2 = 状态文件不存在（resume/advance/finish/budget 遇到未 init 的任务）
  3 = JSON 解析失败（状态文件被外部破坏，fail fast 不静默重建）

## 依赖

仅标准库，Python >= 3.9。原子写：PID 隔离 .tmp + os.replace；
写操作（init/advance/finish/budget）经 flock 互斥锁串行化
（把协议 §3「写入者=仅主理人」的纸面约定固化为工程约束，
非 POSIX 平台退化为无锁 + 约定兜底）。
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
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

STATE_VERSION = 1


def runs_dir(workspace: Path) -> Path:
    """状态根目录：<workspace>/.harness-runs/。"""
    return workspace / ".harness-runs"


def state_path(workspace: Path, task_id: str) -> Path:
    return runs_dir(workspace) / task_id / "_state.json"


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
    except Exception as exc:
        print(f"❌ 状态文件损坏（fail fast，不静默重建）: {p}\n   {exc}", file=sys.stderr)
        sys.exit(3)


def save_state(workspace: Path, task_id: str, state: dict) -> None:
    _atomic_write(state_path(workspace, task_id),
                  json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


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
            except Exception:
                print("❌ --perception 不是合法 JSON", file=sys.stderr)
                return 1
        state = {
            "version": STATE_VERSION,
            "task_id": args.task_id,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "status": "running",          # running | done | aborted
            "phase": "FREEZE",
            "turn": 0,
            "checkpoints": [],            # [{turn, phase, ts, snapshot_ref}]
            "perception": perception,
            "budget": {"turns_used": 0, "turns_max": args.max_turns,
                       "tokens_used": 0, "tokens_max": args.max_tokens},
            "notes": [],
        }
        save_state(ws, args.task_id, state)
    print(f"✅ 状态已初始化: {state_path(ws, args.task_id)}")
    print(f"   阶段序列: {' → '.join(PHASES)}")
    return 0


def cmd_advance(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}（先跑 init）", file=sys.stderr)
            return 2
        if args.phase not in PHASES:
            print(f"❌ 非法阶段 {args.phase!r}，合法值: {'/'.join(PHASES)}", file=sys.stderr)
            return 1
        state["phase"] = args.phase
        state["turn"] += 1
        state["updated_at"] = now_iso()
        state["budget"]["turns_used"] = state["turn"]
        cp = {"turn": state["turn"], "phase": args.phase,
              "ts": now_iso(), "snapshot_ref": None}
        if args.checkpoint:
            # state://cp-NNN ≡ .harness-runs/<task_id>/checkpoints/cp-NNN.md
            cp["snapshot_ref"] = f"state://{args.checkpoint}"
            cp_dir = runs_dir(ws) / args.task_id / "checkpoints"
            cp_dir.mkdir(parents=True, exist_ok=True)
            marker = cp_dir / f"{args.checkpoint}.md"
            if not marker.exists():
                marker.write_text(
                    f"# {args.checkpoint}\n\n- phase: {args.phase}\n- ts: {cp['ts']}\n"
                    f"- note: {args.note or ''}\n\n"
                    f"（本文件为检查点指针：阶段产物应落盘于此目录，指针可被 resume 解析）\n",
                    encoding="utf-8")
        state["checkpoints"].append(cp)
        if args.note:
            state["notes"].append({"ts": now_iso(), "phase": args.phase, "note": args.note})
        save_state(ws, args.task_id, state)
    print(f"✅ 已推进到 {args.phase}（turn {state['turn']}/{state['budget']['turns_max']}）")
    if args.checkpoint:
        print(f"   检查点: {cp['snapshot_ref']} → checkpoints/{args.checkpoint}.md")
    return 0


def cmd_resume(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    state = load_state(ws, args.task_id)
    if state is None:
        print(f"❌ 无状态文件: {state_path(ws, args.task_id)}（该任务未在本工作区跑过）",
              file=sys.stderr)
        return 2
    print(f"📋 任务 {state['task_id']} 恢复点")
    print(f"   status     : {state['status']}")
    print(f"   当前阶段   : {state['phase']}（turn {state['turn']}）")
    print(f"   最后更新   : {state['updated_at']}")
    if state["checkpoints"]:
        last = state["checkpoints"][-1]
        print(f"   最后检查点 : {last['snapshot_ref']}（{last['phase']}，{last['ts']}）")
    if state["notes"]:
        print(f"   最近备注   : {state['notes'][-1]['note']}")
    b = state["budget"]
    print(f"   预算       : turns {b['turns_used']}/{b['turns_max']} · "
          f"tokens {b['tokens_used']}/{b['tokens_max']}")
    if state["status"] == "done":
        print("   → 任务已完成，无需续跑")
    else:
        idx = PHASES.index(state["phase"]) if state["phase"] in PHASES else -1
        nxt = PHASES[idx + 1] if 0 <= idx < len(PHASES) - 1 else "（当前即末阶段）"
        print(f"   → 断点续跑：从 {nxt} 阶段继续（不重跑已完成阶段）")
    return 0


def cmd_finish(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}", file=sys.stderr)
            return 2
        state["status"] = "done"
        state["updated_at"] = now_iso()
        save_state(ws, args.task_id, state)
    print(f"✅ 任务标记完成: {state['task_id']}")
    return 0


def cmd_budget(args) -> int:
    ws = Path(args.workspace).expanduser().resolve()
    with _state_lock(ws, args.task_id):
        state = load_state(ws, args.task_id)
        if state is None:
            print(f"❌ 任务未初始化: {args.task_id}", file=sys.stderr)
            return 2
        if args.turns is not None:
            state["budget"]["turns_used"] = args.turns
        if args.tokens is not None:
            state["budget"]["tokens_used"] = args.tokens
        state["updated_at"] = now_iso()
        save_state(ws, args.task_id, state)
        b = state["budget"]
    warn = ""
    if b["turns_used"] >= b["turns_max"] or b["tokens_used"] >= b["tokens_max"]:
        warn = "  ⚠️ 预算触顶 → 按协议熔断：升级用户，不空转"
    print(f"✅ 预算已更新: turns {b['turns_used']}/{b['turns_max']} · "
          f"tokens {b['tokens_used']}/{b['tokens_max']}{warn}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="协议 §3 状态持久化（init/advance/resume/finish/budget）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--task-id", required=True, help="任务 ID（=trace_id）")
        p.add_argument("--workspace", required=True, help="工作区根目录")
        p.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
        p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    p = sub.add_parser("init", help="初始化任务状态（幂等）")
    add_common(p)
    p.add_argument("--perception", default=None, help="四维感知 JSON（可选）")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("advance", help="推进阶段 + 写检查点")
    add_common(p)
    p.add_argument("--phase", required=True, help=f"目标阶段（{'/'.join(PHASES)}）")
    p.add_argument("--checkpoint", default=None, help="检查点名（如 cp-003）")
    p.add_argument("--note", default=None, help="阶段收尾备注")
    p.set_defaults(fn=cmd_advance)

    p = sub.add_parser("resume", help="中断恢复：打印续跑点")
    add_common(p)
    p.set_defaults(fn=cmd_resume)

    p = sub.add_parser("finish", help="标记任务完成")
    add_common(p)
    p.set_defaults(fn=cmd_finish)

    p = sub.add_parser("budget", help="更新预算计数")
    add_common(p)
    p.add_argument("--turns", type=int, default=None)
    p.add_argument("--tokens", type=int, default=None)
    p.set_defaults(fn=cmd_budget)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
