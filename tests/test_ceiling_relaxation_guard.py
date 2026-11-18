#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#22 熔断阈值主动放宽——告警 + 留痕护栏的注入式测试
====================================================================
审计 #22：fail 的逐次抬高后门已在 v2.5.4 封堵（只允许收紧），但 init/budget
作为 registry 明确授权的上限写入口，仍可主动放宽熔断阈值（max_failures /
max_time）——如 `budget --max-failures 99`，属设计语义、非 bug。

裁决（O2 / ADR-0022）：不改 rc 语义（放宽仍允许，保持向后兼容），但补护栏——
熔断层阈值被放宽时：① stderr 告警；② 写入 notes 留痕（可追溯、可观测）。
告警层 turns/tokens 放宽不触发本护栏（R7 P1-1 语义分层）。

本测试锁定：
  R1 init --max-failures 99（> 默认 5）→ rc=0 + 告警文案 + notes 留痕
  R2 budget --max-failures 99（> 已落盘）→ rc=0 + 告警 + notes 留痕
  R3 budget 收紧 max_failures（< 已落盘）→ rc=0 + 无告警 + 无留痕
  R4 fail --max-failures 抬高（后门）→ 仍被忽略 + 告警（v2.5.4 语义不回退）
  R5 budget --max-turns/--max-tokens 放宽（告警层）→ 不触发熔断告警文案
  R6 budget --max-time 放宽（熔断层）→ 告警 + 留痕

仅标准库；子进程真调 CLI；用临时目录，不写仓库、不依赖本机私有环境。
用法：python3 tests/test_ceiling_relaxation_guard.py
退出码：0 全过 | 1 有失败 | 2 环境错误
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
GUARD_TOKEN = "熔断阈值被放宽"


def _run(ws: Path, task: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(STATE_IO), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def _state(ws: Path, task: str) -> dict:
    return json.loads((ws / ".harness-runs" / task / "_state.json").read_text(encoding="utf-8"))


def _notes_hit(st: dict, token: str) -> bool:
    return any(token in (n.get("note", "")) for n in st.get("notes", []))


def _check(name: str, ok: bool, detail: str) -> None:
    print(f"  {'✅' if ok else '❌'} {name} | {detail}")
    RESULTS.append((name, ok, detail))


def case_r1_init_relax() -> None:
    """R1：init --max-failures 99（> 默认 5）→ rc=0 + 告警 + 留痕。"""
    with tempfile.TemporaryDirectory(prefix="cg-r1-") as tmp:
        ws = Path(tmp)
        rc, out = _run(ws, "r1", "init", "--task-id", "r1", "--workspace", str(ws),
                       "--max-failures", "99")
        st = _state(ws, "r1")
        ok = (rc == 0 and st["budget"]["max_failures"] == 99
              and GUARD_TOKEN in out and _notes_hit(st, GUARD_TOKEN))
        _check("R1 init 放宽熔断 → 告警+留痕且 rc=0", ok,
               f"rc={rc} mf={st['budget']['max_failures']} "
               f"warn={GUARD_TOKEN in out} note={_notes_hit(st, GUARD_TOKEN)}")


def case_r2_budget_relax() -> None:
    """R2：budget --max-failures 99（> 已落盘默认 5）→ rc=0 + 告警 + 留痕。"""
    with tempfile.TemporaryDirectory(prefix="cg-r2-") as tmp:
        ws = Path(tmp)
        _run(ws, "r2", "init", "--task-id", "r2", "--workspace", str(ws))
        rc, out = _run(ws, "r2", "budget", "--task-id", "r2", "--workspace", str(ws),
                       "--max-failures", "99")
        st = _state(ws, "r2")
        ok = (rc == 0 and st["budget"]["max_failures"] == 99
              and GUARD_TOKEN in out and _notes_hit(st, GUARD_TOKEN))
        _check("R2 budget 放宽熔断 → 告警+留痕且 rc=0", ok,
               f"rc={rc} mf={st['budget']['max_failures']} "
               f"warn={GUARD_TOKEN in out} note={_notes_hit(st, GUARD_TOKEN)}")


def case_r3_budget_tighten() -> None:
    """R3：budget 收紧 max_failures → rc=0 + 无告警 + 无留痕（收紧是合规操作）。"""
    with tempfile.TemporaryDirectory(prefix="cg-r3-") as tmp:
        ws = Path(tmp)
        # init 用默认阈值 5（不自带放宽），隔离验证 budget 收紧不产生新留痕
        _run(ws, "r3", "init", "--task-id", "r3", "--workspace", str(ws))
        rc, out = _run(ws, "r3", "budget", "--task-id", "r3", "--workspace", str(ws),
                       "--max-failures", "3")
        st = _state(ws, "r3")
        ok = (rc == 0 and st["budget"]["max_failures"] == 3
              and GUARD_TOKEN not in out and not _notes_hit(st, GUARD_TOKEN))
        _check("R3 budget 收紧熔断 → 静默无留痕", ok,
               f"rc={rc} mf={st['budget']['max_failures']} "
               f"warn={GUARD_TOKEN in out} note={_notes_hit(st, GUARD_TOKEN)}")


def case_r4_fail_backdoor_still_closed() -> None:
    """R4：fail --max-failures 抬高（后门）→ 仍被忽略（v2.5.4 不回退）。"""
    with tempfile.TemporaryDirectory(prefix="cg-r4-") as tmp:
        ws = Path(tmp)
        _run(ws, "r4", "init", "--task-id", "r4", "--workspace", str(ws),
             "--max-failures", "5")
        rc, out = _run(ws, "r4", "fail", "--task-id", "r4", "--workspace", str(ws),
                       "--reason", "一次失败", "--max-failures", "99")
        st = _state(ws, "r4")
        ok = (rc == 0 and st["budget"]["max_failures"] == 5
              and "只允许收紧" in out)
        _check("R4 fail 抬高后门仍封堵", ok,
               f"rc={rc} mf={st['budget']['max_failures']}(期望5) blocked={'只允许收紧' in out}")


def case_r5_warn_layer_not_guarded() -> None:
    """R5：budget --max-turns/--max-tokens 放宽（告警层）→ 不触发熔断告警文案。"""
    with tempfile.TemporaryDirectory(prefix="cg-r5-") as tmp:
        ws = Path(tmp)
        _run(ws, "r5", "init", "--task-id", "r5", "--workspace", str(ws),
             "--max-turns", "2", "--max-tokens", "100")
        rc, out = _run(ws, "r5", "budget", "--task-id", "r5", "--workspace", str(ws),
                       "--max-turns", "999", "--max-tokens", "999999")
        st = _state(ws, "r5")
        ok = (rc == 0 and st["budget"]["turns_max"] == 999
              and GUARD_TOKEN not in out and not _notes_hit(st, GUARD_TOKEN))
        _check("R5 告警层放宽不触发熔断护栏", ok,
               f"rc={rc} turns_max={st['budget']['turns_max']} "
               f"warn={GUARD_TOKEN in out} note={_notes_hit(st, GUARD_TOKEN)}")


def case_r6_max_time_relax() -> None:
    """R6：budget --max-time 放宽（熔断层）→ 告警 + 留痕。"""
    with tempfile.TemporaryDirectory(prefix="cg-r6-") as tmp:
        ws = Path(tmp)
        _run(ws, "r6", "init", "--task-id", "r6", "--workspace", str(ws))
        rc, out = _run(ws, "r6", "budget", "--task-id", "r6", "--workspace", str(ws),
                       "--max-time", "99999")
        st = _state(ws, "r6")
        ok = (rc == 0 and st["budget"]["max_time_sec"] == 99999
              and GUARD_TOKEN in out and _notes_hit(st, GUARD_TOKEN))
        _check("R6 budget 放宽 max_time → 告警+留痕", ok,
               f"rc={rc} max_time={st['budget']['max_time_sec']} "
               f"warn={GUARD_TOKEN in out} note={_notes_hit(st, GUARD_TOKEN)}")


def main() -> int:
    if not STATE_IO.is_file():
        print(f"❌ 找不到 state_io.py: {STATE_IO}")
        return 2
    print("=" * 68)
    print("#22 熔断阈值放宽护栏锁定（O2/ADR-0022 · 告警留痕不拦截）")
    print("=" * 68)
    case_r1_init_relax()
    case_r2_budget_relax()
    case_r3_budget_tighten()
    case_r4_fail_backdoor_still_closed()
    case_r5_warn_layer_not_guarded()
    case_r6_max_time_relax()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("-" * 68)
    if failed:
        print(f"❌ {len(failed)}/{len(RESULTS)} 条用例失败: {failed}")
        return 1
    print(f"✅ {len(RESULTS)}/{len(RESULTS)} 条护栏锁定全部符合设计")
    return 0


if __name__ == "__main__":
    sys.exit(main())
