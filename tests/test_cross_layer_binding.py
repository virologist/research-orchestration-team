#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#28 协议层 ↔ 落盘状态跨层绑定契约的独立注入式测试
====================================================================
审计 #28 实锤：信封 phase/task_id 与落盘状态完全不符时，协议校验仍返回
空失败列表（rc=0）——协议层与状态机层之间没有绑定契约。本测试锁定
protocol_check.check_envelope_state_binding 的四条契约：
  1. task_id == 落盘 task_id
  2. phase ∈ {当前 phase, 下一阶段}
  3. turn（若带）∈ {落盘 turn, turn+1}
  4. 落盘终态（done/aborted）时信封 phase 只能为 NEXT

正例 3 组 + 注入负例 5 组，全部判定「失败原因列表」内容，不采信文案。
用 importlib 按路径加载 protocol_check（目录名含连字符，不能常规 import）。
仅标准库；不写仓库、不依赖本机私有环境。
用法：python3 tests/test_cross_layer_binding.py
退出码：0 全过 | 1 有失败 | 2 环境错误
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
PC_PATH = PKG / "skills" / "research-orchestration-workflow" / "scripts" / "protocol_check.py"

RESULTS: list[tuple[str, bool, str]] = []
TERMINAL = "NEXT"
PHASES = ["FREEZE", "IDENTIFY", "COLLAPSE", "CLARIFY", "ALIGN",
          "EXECUTE", "REVIEW", "NEXT"]


def _load_checker():
    if not PC_PATH.is_file():
        raise FileNotFoundError(str(PC_PATH))
    spec = importlib.util.spec_from_file_location("_pc_cross_layer", PC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.check_envelope_state_binding


def _ck(checker, name, env, state, must_contain=None, want_clean=False):
    got = checker(env, state, PHASES)
    if want_clean:
        ok = got == []
        detail = f"got={got}"
    else:
        ok = all(tok in " ".join(got) for tok in must_contain) and bool(got)
        detail = f"got={got} need={must_contain}"
    RESULTS.append((name, ok, detail))


def main() -> int:
    try:
        checker = _load_checker()
    except Exception as exc:
        print(f"❌ 无法加载协议校验器: {exc}", file=sys.stderr)
        return 2

    S = {"task_id": "task-x", "phase": "EXECUTE", "turn": 3, "status": "running"}
    E = {"task_id": "task-x", "phase": "EXECUTE", "turn": 3, "status": "success"}

    # 正例
    _ck(checker, "X1 完全对齐 → 绿", E, S, want_clean=True)
    _ck(checker, "X2 在途信封(下一阶段 turn+1) → 绿",
        {"task_id": "task-x", "phase": "REVIEW", "turn": 4}, S, want_clean=True)
    _ck(checker, "X3 缺 turn 向后兼容 → 绿",
        {"task_id": "task-x", "phase": "EXECUTE"}, S, want_clean=True)

    # 注入负例（上一轮报告承诺的 4 组 + 终态正例）
    _ck(checker, "X4 task_id 不符 → 红", {**E, "task_id": "task-OTHER"}, S,
        must_contain=["task_id 不符"])
    _ck(checker, "X5 phase 跳级 → 红", {**E, "phase": "NEXT"}, S,
        must_contain=["phase 未对齐"])
    _ck(checker, "X6 turn 越界 → 红", {**E, "turn": 9}, S,
        must_contain=["turn 未对齐"])
    _ck(checker, "X7 终态声明执行中 phase → 红", E, {**S, "status": "done"},
        must_contain=["落盘终态"])
    _ck(checker, "X8 终态声明 NEXT → 绿", {"task_id": "task-x", "phase": "NEXT"},
        {**S, "status": "aborted", "phase": "NEXT"}, want_clean=True)

    print("=== #28 跨层绑定契约注入测试 ===")
    failed = 0
    for name, ok, detail in RESULTS:
        print(f"  {'✅' if ok else '❌'} {name}" + (f"  · {detail}" if not ok else ""))
        if not ok:
            failed += 1
    print(f"\n[rc] {len(RESULTS)-failed}/{len(RESULTS)} 通过 → {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
