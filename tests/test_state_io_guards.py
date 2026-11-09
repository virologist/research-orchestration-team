#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""state_io 输入护栏的注入式验证（R3-P0-1 / R3-P1-2 + 回归护栏）。

背景：R3 再诊断实锤两处缺陷——
  1. 协议标准形态是 `state://cp-NNN`，但 cmd_advance 旧实现按裸名拼路径，
     主理人按文档传带前缀的值时会拼出 `checkpoints/state:/cp-NNN.md`，
     父目录不存在 → 裸 Traceback（rc=1 但输出是堆栈，无业务报错）。
  2. task_id 直接拼进 runs/<task_id>/ 目录名，路径分隔符可建子目录、
     `..` 可穿越到 runs 根外任意落盘。

R3 修复引入的**回归**（本文件 G1 锁定）：`--checkpoint` 是可选参数，
归一化函数把「未传（None）」与「非法形态」都返回 None，而 cmd_advance
用 `is None` 判错 → 不带检查点的正常推进被误拒。故空值必须返回 `""`、
非法值才返回 None。

纪律（见 docs/harness-iteration-loop.md §10.3.2 / FM-R2-06）：
  - 每条用例独立临时目录，逐条独立取 rc，不串成一条命令只看整体 rc；
  - 负例不仅断言 rc 翻转，还要断言**失败原因归属于被测分支**
    （输出含业务报错文案、且无 Traceback），避免被无关校验抢先拦截造成假检出；
  - 自包含：只依赖标准库与本包文件，包根向上逐层探测标志目录，
    不用 `parents[N]` 硬索引（Linux /tmp 浅层布局会 IndexError）。

运行：python3 tests/test_state_io_guards.py
退出码：0 = 全部通过；1 = 有用例失败。
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


def new_task(tid="t1"):
    """建独立临时工作区并 init，返回目录路径。"""
    ws = Path(tempfile.mkdtemp(prefix="sio-guard-"))
    rc, _ = run("init", "--task-id", tid, "--workspace", str(ws))
    assert rc == 0, "init 前置失败"
    return ws


def advance(ws, tid, phase="FREEZE", checkpoint=None, note="n"):
    """按给定 checkpoint 推进一次；checkpoint=None 表示不传该参数。"""
    argv = ["advance", "--task-id", tid, "--workspace", str(ws), "--phase", phase]
    if checkpoint is not None:
        argv += ["--checkpoint", checkpoint]
    if note:
        argv += ["--note", note]
    return run(*argv)


def state_of(ws, tid):
    return json.loads((ws / ".harness-runs" / tid / "_state.json").read_text(encoding="utf-8"))


# ── G1：回归护栏 —— 不带检查点的正常推进必须放行 ──────────────────────────
def g1():
    ws = new_task("g1")
    rc, out = advance(ws, "g1")
    ok = rc == 0 and "已推进到" in out
    return ok, f"rc={rc}（期望 0）；输出={'已推进到' in out}；{out.strip()[:70]}"


# ── G2：协议标准形态 state://cp-NNN 归一化后落盘正确 ─────────────────────
def g2():
    ws = new_task("g2")
    rc, out = advance(ws, "g2", checkpoint="state://cp-001")
    marker = ws / ".harness-runs" / "g2" / "checkpoints" / "cp-001.md"
    bad_dir = ws / ".harness-runs" / "g2" / "checkpoints" / "state:"
    ref = state_of(ws, "g2")["checkpoints"][-1].get("snapshot_ref")
    ok = (rc == 0 and marker.is_file() and not bad_dir.exists()
          and ref == "state://cp-001" and "Traceback" not in out)
    return ok, f"rc={rc} marker={marker.is_file()} 无state:目录={not bad_dir.exists()} ref={ref}"


# ── G3：裸 cp-NNN 向后兼容 ──────────────────────────────────────────────
def g3():
    ws = new_task("g3")
    rc, _ = advance(ws, "g3", checkpoint="cp-001")
    marker = ws / ".harness-runs" / "g3" / "checkpoints" / "cp-001.md"
    return rc == 0 and marker.is_file(), f"rc={rc} marker={marker.is_file()}（期望均真）"


# ── G4/G5：非法 checkpoint 必须优雅拒绝且失败原因归属于本分支 ────────────
def _bad_cp(raw):
    ws = new_task("g4")
    rc, out = advance(ws, "g4", checkpoint=raw)
    ok = rc == 1 and "非法 checkpoint 名" in out and "Traceback" not in out
    return ok, f"rc={rc}（期望 1）业务报错={'非法 checkpoint 名' in out} 无堆栈={'Traceback' not in out}"


def g4():
    return _bad_cp("../evil")


def g5():
    return _bad_cp("state://../evil")


# ── G6/G7：非法 task_id 在统一入口被拒（rc=2），且 runs 根外无落盘 ───────
def _bad_tid(tid):
    ws = Path(tempfile.mkdtemp(prefix="sio-tid-"))
    rc, out = run("init", "--task-id", tid, "--workspace", str(ws))
    # 未消毒时 `../escape-probe` 会在 ws 根或 ws 父目录下建目录，两处都不能出现
    escaped = (not (ws / "escape-probe").exists()
               and not (ws.parent / "escape-probe").exists())
    ok = rc == 2 and "非法 task_id" in out and "Traceback" not in out and escaped
    return ok, (f"rc={rc}（期望 2）业务报错={'非法 task_id' in out} "
                f"无堆栈={'Traceback' not in out} 无越界目录={escaped}")


def g6():
    return _bad_tid("../escape-probe")


def g7():
    return _bad_tid("a/b")


# ── G8：合法 task_id 边界（1~64 字符，允许 . _ -）─────────────────────────
def g8():
    ws = Path(tempfile.mkdtemp(prefix="sio-ok-"))
    rc, _ = run("init", "--task-id", "task.1_a-b", "--workspace", str(ws))
    ok = rc == 0 and (ws / ".harness-runs" / "task.1_a-b" / "_state.json").is_file()
    return ok, f"rc={rc}（期望 0）状态文件落盘={(ws / '.harness-runs' / 'task.1_a-b' / '_state.json').is_file()}"


# ── G9：空字符串 checkpoint 等价于不带检查点 ──────────────────────────────
def g9():
    ws = new_task("g9")
    rc, out = advance(ws, "g9", checkpoint="")
    ok = rc == 0 and "已推进到" in out
    return ok, f"rc={rc}（期望 0，空串视为不带检查点）"


# ── G10：超长 task_id（65 字符）被拒 ─────────────────────────────────────
def g10():
    ws = Path(tempfile.mkdtemp(prefix="sio-long-"))
    rc, out = run("init", "--task-id", "a" * 65, "--workspace", str(ws))
    ok = rc == 2 and "非法 task_id" in out
    return ok, f"rc={rc}（期望 2）业务报错={'非法 task_id' in out}"


case("G1", "不带 checkpoint 的正常推进放行（R3 回归锁定）", g1)
case("G2", "state://cp-NNN 归一化 → checkpoints/cp-NNN.md", g2)
case("G3", "裸 cp-NNN 向后兼容", g3)
case("G4", "非法 checkpoint ../evil 优雅拒绝", g4)
case("G5", "带前缀的非法 checkpoint 同样拒绝", g5)
case("G6", "非法 task_id 路径穿越被拒（rc=2）", g6)
case("G7", "非法 task_id 含路径分隔符被拒（rc=2）", g7)
case("G8", "合法 task_id 边界字符放行", g8)
case("G9", "空 checkpoint 等价于不带", g9)
case("G10", "超长 task_id（65 字符）被拒", g10)


def main() -> int:
    print("=" * 68)
    print("state_io 输入护栏注入式验证（R3-P0-1 / R3-P1-2 + 回归护栏）")
    print("=" * 68)
    assert STATE_IO.is_file(), f"state_io.py 不存在：{STATE_IO}"
    passed = 0
    for cid, desc, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as exc:  # 用例自身异常必须显式报红，不能静默跳过
            ok, detail = False, f"用例抛出异常：{type(exc).__name__}: {exc}"
        mark = "✅" if ok else "❌"
        print(f"  {mark} {cid} {desc} | {detail}")
        passed += int(ok)
    print("-" * 68)
    print(f"{'✅' if passed == len(CASES) else '❌'} {passed}/{len(CASES)} 条输入护栏验证符合设计")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
