#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R4：V4 step↔gate 集合比对的注入式负例测试
====================================================================
审计 R4 实锤旧 V4 只判数量（`gates_n == expect_n`），23==23 的「数字巧合」
掩盖了集合不对应（protocol 三子门禁共用一个 step、两个 heredoc smoke step
无独立 gate）。一旦增删 step，数量口径会再次假绿。

本测试直接调用 rot.py 的 `v4_set_check` 纯函数，注入 5 组破坏：
  N1 删一个 CI step        → 必须判红（映射有、CI 无）
  N2 新增/改名一个 CI step → 必须判红（CI 有、映射无）
  N3 删一个 gate 登记      → 必须判红（映射有、登记无 → 幽灵 gate）
  N4 加一个 gate 登记      → 必须判红（登记有、映射无 → 无 step 盯防）
  N5 映射结构非法(空列表)  → 必须判红
  N6 合法输入              → 必须判绿

判定只看函数返回的布尔值，不采信诊断文案。全标准库，无 IO 副作用。
用法：python3 tests/test_v4_set_check.py
退出码：0 全过 | 1 有失败
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "scripts"))
import rot  # noqa: E402

PLATFORM = {"Checkout", "Setup Python", "Set up job", "Post Setup Python",
            "Post Checkout", "Complete job"}

RESULTS: list[tuple[str, bool, str]] = []


def _baseline() -> tuple[dict, list[str]]:
    wm = json.loads((PKG / "workmap.json").read_text(encoding="utf-8"))
    wf = (PKG / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    steps = [l.strip()[8:] for l in wf.splitlines() if l.strip().startswith("- name:")]
    return wm, steps


def _ck(name: str, got: bool, want: bool, detail: str) -> None:
    ok = got == want
    RESULTS.append((name, ok, f"got={got} want={want} {detail}"))


def main() -> int:
    wm, steps = _baseline()

    # N6 合法基线 → 绿
    ok, msg = rot.v4_set_check(wm, steps, PLATFORM)
    _ck("N6 合法基线判绿", ok, True, "")

    # N1 删一个 CI step（取映射里非 smoke 的一个）→ 红
    w = copy.deepcopy(wm)
    victim = next(k for k, v in w["ci_step_map"].items()
                  if v and not str(v[0]).startswith("@smoke:"))
    s2 = [s for s in steps if s != victim]
    ok, msg = rot.v4_set_check(w, s2, PLATFORM)
    _ck("N1 删 CI step 判红", ok, False, f"(删 {victim}) {msg[:70]}")

    # N2 新增一个 CI step → 红
    s3 = steps + ["Ghost Gate Step (injected)"]
    ok, msg = rot.v4_set_check(wm, s3, PLATFORM)
    _ck("N2 增 CI step 判红", ok, False, msg[:70])

    # N3 删一个 gate 登记 → 映射里出现幽灵 gate → 红
    w = copy.deepcopy(wm)
    g = w["gates"]["static"].pop()
    ok, msg = rot.v4_set_check(w, steps, PLATFORM)
    _ck("N3 删 gate 登记判红", ok, False, f"(删 {g}) {msg[:70]}")

    # N4 加一个幽灵 gate 登记 → 登记有映射无 → 红
    w = copy.deepcopy(wm)
    w["gates"]["static"].append("ghost_gate_injected")
    ok, msg = rot.v4_set_check(w, steps, PLATFORM)
    _ck("N4 增 gate 登记判红", ok, False, msg[:70])

    # N5 映射结构非法（某 step 映射空列表）→ 红
    w = copy.deepcopy(wm)
    w["ci_step_map"]["Package consistency check"] = []
    ok, msg = rot.v4_set_check(w, steps, PLATFORM)
    _ck("N5 映射空列表判红", ok, False, msg[:70])

    # N7 缺 ci_step_map → 红（契约未登记 fail-closed）
    w = copy.deepcopy(wm)
    del w["ci_step_map"]
    ok, msg = rot.v4_set_check(w, steps, PLATFORM)
    _ck("N7 缺映射字段判红", ok, False, msg[:70])

    print("=== R4 V4 集合比对注入负例 ===")
    failed = 0
    for name, ok, detail in RESULTS:
        mark = "✅" if ok else "❌"
        print(f"  {mark} {name}" + (f"  · {detail}" if not ok else ""))
        if not ok:
            failed += 1
    print(f"\n[rc] {len(RESULTS)-failed}/{len(RESULTS)} 通过 → {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
