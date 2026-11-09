#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""state_io.py 编排层四项硬上限的语义锁定测试（R2 P0-1）
=====================================================================
v2.4.0 CHANGELOG 曾把四项上限笼统写成「代码化」，实测发现 turn 2/1 仍放行
rc=0 —— turns/tokens 的设计语义是「告警」（budget 子命令 ⚠️），只有
max_time 与 failures 是「终态熔断」（status: aborted）。本测试把这个
语义分层**锁死**：任何一层的语义被误改（告警变截断 / 终态变告警 / 熔断
判断被改坏），本测试立即红。

四条用例：
  C1 turns 触顶告警放行   —— advance 超过 turns_max 仍 rc=0（语义=告警）
  C2 tokens 触顶同上      —— budget 写 tokens_max=1 后仍可推进（语义=告警）
  C3 failures 熔断终态    —— fail x N 后 status=aborted，advance 拒绝 rc!=0
  C4 finish 熔断后不改写  —— aborted 后 finish rc=0 但 status 仍 aborted

判定全部读落盘 _state.json + 真实退出码，不采信 stdout 文案。

用法：python3 tests/test_state_ceilings.py
退出码：0 全部通过 | 1 有失败 | 2 环境错误

仅标准库；每个用例独立 tempfile 工作区，互不污染。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
STATE_IO = PKG / "skills" / "research-orchestration-workflow" / "scripts" / "state_io.py"

RESULTS: list[tuple[str, bool, str]] = []


def _run(ws: Path, task: str, *args: str) -> tuple[int, str]:
    """真调 state_io.py 子命令，返回 (退出码, 合并输出)。"""
    proc = subprocess.run(
        [sys.executable, str(STATE_IO), *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _read_state(ws: Path, task: str) -> dict:
    """读落盘状态文件（判定唯一真值源）。"""
    return json.loads(
        (ws / ".harness-runs" / task / "_state.json").read_text(encoding="utf-8")
    )


def _check(name: str, ok: bool, detail: str) -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name} | {detail}")
    RESULTS.append((name, ok, detail))


def case_c1_turns_warn() -> None:
    """C1：init --max-turns 1 → 连续 advance 两次 → 两次都 rc=0（告警不截断）。"""
    with tempfile.TemporaryDirectory(prefix="ceil-c1-") as tmp:
        ws = Path(tmp)
        rc0, _ = _run(ws, "c1", "init", "--task-id", "c1", "--workspace", str(ws),
                      "--max-turns", "1")
        rc1, out1 = _run(ws, "c1", "advance", "--task-id", "c1", "--workspace", str(ws),
                         "--phase", "FREEZE", "--checkpoint", "cp-001", "--note", "n1")
        rc2, out2 = _run(ws, "c1", "advance", "--task-id", "c1", "--workspace", str(ws),
                         "--phase", "IDENTIFY", "--checkpoint", "cp-002", "--note", "n2")
        st = _read_state(ws, "c1")
        ok = (rc0 == 0 and rc1 == 0 and rc2 == 0
              and st.get("status") == "running"
              and st.get("budget", {}).get("turns_used", 0) >= 1)
        detail = (f"init={rc0} adv#1={rc1} adv#2={rc2} status={st.get('status')} "
                  f"turns_used={st.get('budget', {}).get('turns_used')}")
        # 语义锚：第二次 advance 的输出必须出现「已推进」而非拒绝文案
        ok = ok and ("已推进" in out2) and ("拒绝" not in out2)
        _check("C1 turns 触顶告警放行（不截断）", ok, detail)


def case_c2_tokens_warn() -> None:
    """C2：budget --max-tokens 1 → 再 advance → rc=0（tokens 同为告警语义）。"""
    with tempfile.TemporaryDirectory(prefix="ceil-c2-") as tmp:
        ws = Path(tmp)
        _run(ws, "c2", "init", "--task-id", "c2", "--workspace", str(ws))
        _run(ws, "c2", "advance", "--task-id", "c2", "--workspace", str(ws),
             "--phase", "FREEZE", "--checkpoint", "cp-001", "--note", "n1")
        rcb, _ = _run(ws, "c2", "budget", "--task-id", "c2", "--workspace", str(ws),
                      "--tokens", "1")
        rc, _ = _run(ws, "c2", "advance", "--task-id", "c2", "--workspace", str(ws),
                     "--phase", "IDENTIFY", "--checkpoint", "cp-002", "--note", "n2")
        st = _read_state(ws, "c2")
        ok = (rcb == 0 and rc == 0 and st.get("status") == "running")
        _check("C2 tokens 触顶告警放行（不截断）", ok,
               f"budget={rcb} advance={rc} status={st.get('status')}")


def case_c3_failures_abort() -> None:
    """C3：fail x 默认阈值 → status=aborted + advance 拒绝 rc!=0（终态语义）。"""
    with tempfile.TemporaryDirectory(prefix="ceil-c3-") as tmp:
        ws = Path(tmp)
        _run(ws, "c3", "init", "--task-id", "c3", "--workspace", str(ws))
        # 默认熔断阈值 5：连 fail 5 次（须带非空 --reason）
        rcs = []
        for i in range(1, 6):
            rc, _ = _run(ws, "c3", "fail", "--task-id", "c3", "--workspace", str(ws),
                         "--reason", f"失败{i}")
            rcs.append(rc)
        st = _read_state(ws, "c3")
        aborted = st.get("status") == "aborted" and st.get("abort_reason") == "circuit_breaker"
        rca, outa = _run(ws, "c3", "advance", "--task-id", "c3", "--workspace", str(ws),
                         "--phase", "FREEZE", "--checkpoint", "cp-001", "--note", "n")
        ok = rcs == [0] * 5 and aborted and rca != 0
        _check("C3 failures 熔断终态（advance 拒绝）", ok,
               f"fail_rcs={rcs} status={st.get('status')} "
               f"reason={st.get('abort_reason')} advance_after={rca}")


def case_c4_finish_keeps_aborted() -> None:
    """C4：熔断后 finish rc=0 但不得改写 status=aborted（熔断信号不可被抹掉）。"""
    with tempfile.TemporaryDirectory(prefix="ceil-c4-") as tmp:
        ws = Path(tmp)
        _run(ws, "c4", "init", "--task-id", "c4", "--workspace", str(ws))
        for i in range(1, 6):
            _run(ws, "c4", "fail", "--task-id", "c4", "--workspace", str(ws),
                 "--reason", f"失败{i}")
        rcf, _ = _run(ws, "c4", "finish", "--task-id", "c4", "--workspace", str(ws))
        st = _read_state(ws, "c4")
        ok = rcf == 0 and st.get("status") == "aborted"
        _check("C4 finish 熔断后不改写状态", ok,
               f"finish={rcf} status={st.get('status')}（期望仍 aborted）")


def main() -> int:
    if not STATE_IO.is_file():
        print(f"❌ 找不到 state_io.py: {STATE_IO}")
        return 2
    print("=" * 68)
    print("编排层四项硬上限语义锁定（turns/tokens=告警 · max_time/failures=终态）")
    print("=" * 68)
    case_c1_turns_warn()
    case_c2_tokens_warn()
    case_c3_failures_abort()
    case_c4_finish_keeps_aborted()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("-" * 68)
    if failed:
        print(f"❌ {len(failed)}/{len(RESULTS)} 条用例失败: {failed}")
        return 1
    print(f"✅ {len(RESULTS)}/{len(RESULTS)} 条语义锁定全部符合设计")
    return 0


if __name__ == "__main__":
    sys.exit(main())
