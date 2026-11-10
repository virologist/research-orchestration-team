#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""state_io 运行时序 / 终态污染 / 观测数据一致性的注入式锁定（R6）

=====================================================================
R5（组合态审计）把「两条各自成立的断言组合起来是否仍成立」查完了，
R6 转向 §10.5 里 R5 **未覆盖**的方向：**运行时序**（终态后的写操作、
并发、重入、中断恢复）与**观测数据一致性**（budget 上报值是否会被
后续写操作静默冲掉）。

R6 Phase A 做了 13 组运行时序实验，实锤 2 个 P0 + 2 个 P1：

  P0-1 终态污染（E1 + E2）：
    `resume` / `budget` 的 max_time 检查守卫原先是 `status != aborted`，
    **漏了 done**；`cmd_budget` 更严重——它**没有任何终态守卫**。
    后果：任务 finish 成功后，只要事后超过 max_time，调一次 resume 或
    budget 就会把 status 从 done 改写成 aborted——**已完成的任务被翻成
    失败**，且 metrics 里 success_rate=1 与 status=aborted 自相矛盾。
  P0-2 熔断可被绕过（E8）：
    `fail` 子命令允许 `--max-failures` **抬高**已落盘阈值，于是
    「每次 fail 都自带一个更大的阈值」能让熔断彻底失效（实测 8 次失败
    后 status 仍是 running）。registry 只授权 init / budget 覆写上限。
  P1-1 观测数据静默丢失（E9）：
    `advance` 里 `budget.turns_used = state["turn"]` 是**覆盖**而非累加，
    主理人用 budget 上报的观测值（turns=25 / tokens=42000）会被下一次
    advance 静默冲回 turn 的小数值。

本文件把这些行为**锁死**：任何一处被改回去，本测试立即红。

八条用例：
  T1 done 终态 + 超时 → resume 不翻案（status 仍 done）        ← P0-1
  T2 done 终态 → budget 拒绝改写（rc=1，status 仍 done）      ← P0-1
  T3 done 终态 → budget 拒绝后状态完全未变（护栏完整性）      ← P0-1
  T4 fail 抬高 --max-failures → 忽略并告警，熔断照常触发        ← P0-2
  T5 fail 收紧 --max-failures → 允许（阈值只收紧不放宽）        ← P0-2
  T6 budget 上报 turns → advance 不冲掉观测值                 ← P1-1
  T7 未上报时 turns_used 仍随 turn 递增（修复未破坏原语义）    ← P1-1
  T8 aborted 终态 → budget 同样拒绝（终态守卫覆盖两类终态）    ← P0-1

纪律（见 docs/harness-iteration-loop.md §10.3.2 / FM-R2-06）：
  - 每条用例独立临时目录，逐条独立取 rc，不串成一条命令只看整体 rc；
  - 负例不仅断言 rc 翻转，还要断言**失败原因归属于被测分支**
    （输出含业务报错文案、且无 Traceback），避免被无关校验抢先拦截造成假检出；
  - 自包含：只依赖标准库与本包文件，包根向上逐层探测标志目录，
    不用 `parents[N]` 硬索引（Linux /tmp 浅层布局会 IndexError）。

运行：python3 tests/test_state_runtime_sequencing.py
退出码：0 = 全部通过；1 = 有用例失败；2 = 环境错误。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ── 包根定位：向上逐层找「同时存在 agents/ 与 .codebuddy-plugin/」的目录 ──
def _find_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "agents").is_dir() and (parent / ".codebuddy-plugin").is_dir():
            return parent
    raise RuntimeError("找不到包根：向上未探测到 agents/ + .codebuddy-plugin/ 标志目录")


ROOT = _find_root()
STATE_IO = ROOT / "skills" / "research-orchestration-workflow" / "scripts" / "state_io.py"
CASES = []


def case(cid, desc, fn):
    """登记一条用例。fn() -> (通过?, 明细)。"""
    CASES.append((cid, desc, fn))


def run(*args) -> tuple:
    """执行一次 state_io 子命令，返回 (rc, stdout+stderr)。"""
    p = subprocess.run([sys.executable, str(STATE_IO), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read_state(ws: Path, task: str) -> dict:
    """读落盘状态文件（判定唯一真值源）。"""
    return json.loads(
        (ws / ".harness-runs" / task / "_state.json").read_text(encoding="utf-8")
    )


def no_traceback(out: str) -> bool:
    """输出里不得出现裸 Traceback——业务报错必须有可读文案。"""
    return "Traceback (most recent call last)" not in out


def run_and_capture(ws: Path, *args) -> tuple:
    """跑一次子命令并同时返回 (rc, 输出)。"""
    return run(*args)


def case_t1_resume_does_not_rewrite_done() -> None:
    """T1：done 终态 + 事后超时 → resume 不得把 done 改写为 aborted。

    复现路径（R6 Phase A E1）：init --max-time 2 → advance → finish →
    等超过 max_time → resume。修复前 status 变 aborted（success_rate 仍 1，
    状态与 metrics 自相矛盾）。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t1-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t1", "--workspace", str(ws), "--max-time", "2")
        run("advance", "--task-id", "t1", "--workspace", str(ws),
            "--phase", "FREEZE", "--checkpoint", "cp-001")
        run("finish", "--task-id", "t1", "--workspace", str(ws), "--tool-calls", "12")
        before = read_state(ws, "t1")
        # 睡过 max_time，制造「已完成后超时」的时序
        import time
        time.sleep(3)
        rc, out = run("resume", "--task-id", "t1", "--workspace", str(ws))
        st = read_state(ws, "t1")
        ok = (before.get("status") == "done"
              and st.get("status") == "done"
              and st.get("abort_reason") is None
              and rc == 0
              and no_traceback(out))
        _check("T1 done 终态经超时 resume 不被翻案", ok,
               f"finish后={before.get('status')} resume后={st.get('status')} "
               f"abort_reason={st.get('abort_reason')} rc={rc}")


def case_t2_budget_rejects_done() -> None:
    """T2：done 终态 → budget 必须拒绝（rc=1）且不改写状态。

    复现路径（R6 Phase A E2）：finish 后调 `budget --max-time 0`。
    修复前 budget 没有任何终态守卫，直接把 done 改写成 aborted。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t2-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t2", "--workspace", str(ws))
        run("advance", "--task-id", "t2", "--workspace", str(ws),
            "--phase", "FREEZE", "--checkpoint", "cp-001")
        run("finish", "--task-id", "t2", "--workspace", str(ws), "--tool-calls", "5")
        before = read_state(ws, "t2")
        rc, out = run("budget", "--task-id", "t2", "--workspace", str(ws), "--max-time", "0")
        st = read_state(ws, "t2")
        # 失败原因必须归属于「终态守卫」这一分支：含业务报错文案且无 Traceback
        attribution = ("终态" in out) and no_traceback(out)
        ok = (before.get("status") == "done"
              and rc == 1
              and st.get("status") == "done"
              and st.get("abort_reason") is None
              and attribution)
        _check("T2 done 终态调 budget 被拒且不改写", ok,
               f"rc={rc} status前={before.get('status')} status后={st.get('status')} "
               f"归属断言={'通过' if attribution else '失败'}")


def case_t3_budget_reject_leaves_state_untouched() -> None:
    """T3：budget 被拒后，状态文件的关键字段必须**完全未变**。

    防止「虽然 rc=1 但落盘已被部分改写」——那会让拒绝形同虚设。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t3-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t3", "--workspace", str(ws))
        run("advance", "--task-id", "t3", "--workspace", str(ws),
            "--phase", "FREEZE", "--checkpoint", "cp-001")
        run("finish", "--task-id", "t3", "--workspace", str(ws), "--tool-calls", "7")
        before = read_state(ws, "t3")
        run("budget", "--task-id", "t3", "--workspace", str(ws),
            "--max-time", "0", "--turns", "999", "--tokens", "123456")
        after = read_state(ws, "t3")
        same = (before.get("status") == after.get("status")
                and before.get("budget") == after.get("budget")
                and before.get("metrics") == after.get("metrics"))
        ok = same
        _check("T3 budget 被拒后状态文件完全未变", ok,
               f"status {before.get('status')}→{after.get('status')} "
               f"budget同={before.get('budget') == after.get('budget')} "
               f"metrics同={before.get('metrics') == after.get('metrics')}")


def case_t4_fail_cannot_raise_threshold() -> None:
    """T4：fail 携带更大的 --max-failures → 忽略并告警，熔断照常触发。

    复现路径（R6 Phase A E8）：每次 fail 都自带更大的阈值。
    修复前 8 次失败后 status 仍 running（熔断被彻底绕过）。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t4-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t4", "--workspace", str(ws), "--max-failures", "3")
        warn_seen = False
        tripped = False
        for i in range(1, 7):
            rc, out = run("fail", "--task-id", "t4", "--workspace", str(ws),
                          "--reason", f"失败{i}", "--max-failures", str(10 + i))
            if "只允许收紧" in out:
                warn_seen = True
            st = read_state(ws, "t4")
            if st.get("status") == "aborted":
                tripped = True
                trip_at = i
                break
        st = read_state(ws, "t4")
        ok = (tripped and warn_seen
              and st.get("abort_reason") == "circuit_breaker"
              and st.get("budget", {}).get("max_failures") == 3)
        _check("T4 fail 抬高阈值被忽略且熔断照常触发", ok,
               f"熔断于第{trip_at if tripped else '?'}次 "
               f"status={st.get('status')} reason={st.get('abort_reason')} "
               f"max_failures={st.get('budget', {}).get('max_failures')} "
               f"告警={'有' if warn_seen else '无'}")


def case_t5_fail_can_tighten_threshold() -> None:
    """T5：fail 携带更小的 --max-failures → 允许收紧（不能把修复做成「一律忽略」）。

    收紧是安全方向：让熔断更早触发。修复若把覆写整体禁掉，这条会红。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t5-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t5", "--workspace", str(ws), "--max-failures", "9")
        rc, out = run("fail", "--task-id", "t5", "--workspace", str(ws),
                      "--reason", "收紧测试", "--max-failures", "2")
        st = read_state(ws, "t5")
        ok = (rc == 0
              and st.get("budget", {}).get("max_failures") == 2
              and st.get("status") == "running")
        _check("T5 fail 收紧阈值被接受", ok,
               f"rc={rc} max_failures={st.get('budget', {}).get('max_failures')} "
               f"status={st.get('status')}")


def case_t6_advance_keeps_reported_turns() -> None:
    """T6：budget 上报 turns=25 后，advance 不得把 turns_used 冲回小值。

    复现路径（R6 Phase A E9）：budget 上报观测值 → advance 覆盖。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t6-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t6", "--workspace", str(ws))
        run("advance", "--task-id", "t6", "--workspace", str(ws),
            "--phase", "FREEZE", "--checkpoint", "cp-001")
        run("budget", "--task-id", "t6", "--workspace", str(ws),
            "--turns", "25", "--tokens", "42000")
        run("advance", "--task-id", "t6", "--workspace", str(ws),
            "--phase", "IDENTIFY", "--checkpoint", "cp-002")
        st = read_state(ws, "t6")
        b = st.get("budget", {})
        ok = (b.get("turns_used") == 25 and b.get("tokens_used") == 42000)
        _check("T6 advance 不冲掉主理人上报的观测值", ok,
               f"turns_used={b.get('turns_used')} tokens_used={b.get('tokens_used')} "
               f"（期望 25 / 42000）")


def case_t7_turns_still_follows_turn() -> None:
    """T7：未上报时 turns_used 仍随 turn 递增（修复不得破坏原语义）。

    这是 T6 的对照组：防止把「取 max」写成「恒为上报值」或「恒不更新」。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t7-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t7", "--workspace", str(ws))
        phases = ["FREEZE", "IDENTIFY", "COLLAPSE"]
        for i, p in enumerate(phases, start=1):
            run("advance", "--task-id", "t7", "--workspace", str(ws),
                "--phase", p, "--checkpoint", f"cp-{i:03d}")
        st = read_state(ws, "t7")
        ok = (st.get("turn") == 3
              and st.get("budget", {}).get("turns_used") == 3)
        _check("T7 未上报时 turns_used 随 turn 递增", ok,
               f"turn={st.get('turn')} turns_used={st.get('budget', {}).get('turns_used')} "
               f"（期望 3 / 3）")


def case_t8_budget_rejects_aborted() -> None:
    """T8：aborted 终态 → budget 同样拒绝（终态守卫必须覆盖两类终态）。

    防止修复只挡住 done、漏掉 aborted（这正是 R6 修复前的原始 bug 形态）。
    """
    with tempfile.TemporaryDirectory(prefix="r6-t8-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t8", "--workspace", str(ws), "--max-failures", "2")
        for i in (1, 2):
            run("fail", "--task-id", "t8", "--workspace", str(ws), "--reason", f"f{i}")
        before = read_state(ws, "t8")
        rc, out = run("budget", "--task-id", "t8", "--workspace", str(ws), "--turns", "1")
        st = read_state(ws, "t8")
        attribution = ("终态" in out) and no_traceback(out)
        ok = (before.get("status") == "aborted"
              and rc == 1
              and st.get("status") == "aborted"
              and st.get("abort_reason") == "circuit_breaker"
              and attribution)
        _check("T8 aborted 终态调 budget 被拒", ok,
               f"rc={rc} status={st.get('status')} reason={st.get('abort_reason')} "
               f"归属断言={'通过' if attribution else '失败'}")


RESULTS = []


def _check(name: str, ok: bool, detail: str) -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name} | {detail}")
    RESULTS.append((name, ok, detail))


def main() -> int:
    if not STATE_IO.is_file():
        print(f"❌ 找不到 state_io.py: {STATE_IO}")
        return 2
    print("=" * 70)
    print("运行时序 / 终态污染 / 观测数据一致性锁定（R6）")
    print("=" * 70)
    case_t1_resume_does_not_rewrite_done()
    case_t2_budget_rejects_done()
    case_t3_budget_reject_leaves_state_untouched()
    case_t4_fail_cannot_raise_threshold()
    case_t5_fail_can_tighten_threshold()
    case_t6_advance_keeps_reported_turns()
    case_t7_turns_still_follows_turn()
    case_t8_budget_rejects_aborted()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("-" * 70)
    if failed:
        print(f"❌ {len(failed)}/{len(RESULTS)} 条用例失败: {failed}")
        return 1
    print(f"✅ {len(RESULTS)}/{len(RESULTS)} 条运行时序锁定全部符合设计")
    return 0


if __name__ == "__main__":
    sys.exit(main())
