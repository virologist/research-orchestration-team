#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shim 层 --phase 阶段名归一化自检（P0-2 配套）
============================================
用 subprocess 真调 scripts/assemble_spawn_prompt.py，观察 stderr 与退出码。
合法阶段名应被映射为 1-8 阶段号后进入业务逻辑（--task-file /dev/null → rc=3，
不是失败）；整数与非法值原样透传，非法值仍由 core 的 argparse 报
invalid int value（rc=2）；--phase 缺值由 argparse 正常报错、不得崩溃。

用法：python3 scripts/test_phase_normalization.py
退出码：0 全部用例通过 | 1 有失败用例
"""

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)
_SHIM = os.path.join(_PKG, "scripts", "assemble_spawn_prompt.py")

_PHASE_NAMES = ["FREEZE", "IDENTIFY", "COLLAPSE", "CLARIFY", "ALIGN",
                "EXECUTE", "REVIEW", "NEXT"]

# 固定公共参数；--phase 相关参数由各用例追加，缺值用例需让 --phase 落在末尾。
_BASE = ["--member", "domain-expert-biomed",
         "--task-id", "R1-PHASE-SELFTEST", "--task-file", "/dev/null"]

_RESULTS = []


def _run(extra):
    proc = subprocess.run([sys.executable, _SHIM] + _BASE + extra,
                          capture_output=True, text=True)
    return proc.returncode, proc.stderr, proc.stdout


def _check(name, extra, expect):
    """expect: (rc, stderr) -> (bool, 说明)。断言真检查 stderr 内容，不只看 rc。"""
    rc, stderr, _stdout = _run(extra)
    ok, detail = expect(rc, stderr)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} | rc={rc} | {detail}")
    _RESULTS.append((name, ok))


def _expect_normalized(rc, stderr):
    """合法阶段名：须不再出现 int 转换错误，并进入业务逻辑（/dev/null → rc=3）。"""
    if "invalid int value" in stderr:
        return False, "stderr 仍含 'invalid int value'（未归一化）"
    if "Traceback" in stderr:
        return False, "stderr 含 Traceback（未捕获异常）"
    if rc != 3:
        return False, f"期望 rc=3（进入业务逻辑），实得 rc={rc}"
    if "任务包" not in stderr and "task" not in stderr.lower():
        return False, "stderr 未见任务包提示，未进入业务逻辑"
    return True, "阶段名已归一化为整数号并通过 argparse"


def _expect_passthrough_int(rc, stderr):
    """整数透传：行为与改动前一致（rc=3，无 int 转换错误）。"""
    if "invalid int value" in stderr:
        return False, "整数被误判为非法 int"
    if rc != 3:
        return False, f"期望 rc=3（行为不变），实得 rc={rc}"
    return True, "整数原样透传，行为不变"


def _expect_passthrough_bogus(value):
    """非法值透传：仍由 core 的 argparse 报错并回显原值，禁止静默吞掉。"""
    def _f(rc, stderr):
        if rc != 2:
            return False, f"期望 rc=2（argparse 报错），实得 rc={rc}"
        if "invalid int value" not in stderr:
            return False, "非法值未触发 'invalid int value'（被静默吞掉？）"
        if value not in stderr:
            return False, f"stderr 未回显原值 '{value}'"
        return True, "非法值原样透传并触发 argparse 报错"
    return _f


def _expect_missing_value(rc, stderr):
    """--phase 无值：argparse 正常报错，不出现未捕获异常。"""
    if "Traceback" in stderr:
        return False, "stderr 含 Traceback（未捕获异常，崩溃）"
    if rc != 2:
        return False, f"期望 rc=2（argparse 正常报错），实得 rc={rc}"
    if "expected one argument" not in stderr and "invalid int value" not in stderr:
        return False, "stderr 未见 argparse 的缺值/类型转换报错"
    return True, "缺值由 argparse 正常报错，未崩溃"


def main():
    print("=" * 64)
    print("shim --phase 阶段名归一化自检（P0-2）")
    print("=" * 64)

    print("\n[组 1] 8 个阶段名 × `--phase NAME`")
    for n in _PHASE_NAMES:
        _check(f"--phase {n}", ["--phase", n], _expect_normalized)

    print("\n[组 2] 8 个阶段名 × `--phase=NAME`")
    for n in _PHASE_NAMES:
        _check(f"--phase={n}", [f"--phase={n}"], _expect_normalized)

    print("\n[组 3] 大小写混合")
    for tok in ["cLaRiFy", "nExT", "freeze"]:
        _check(f"--phase {tok}", ["--phase", tok], _expect_normalized)
    for tok in ["ReViEw", "aLiGn"]:
        _check(f"--phase={tok}", [f"--phase={tok}"], _expect_normalized)

    print("\n[组 4] 整数透传（行为不变）")
    _check("--phase 3", ["--phase", "3"], _expect_passthrough_int)
    _check("--phase=8", ["--phase=8"], _expect_passthrough_int)

    print("\n[组 5] 非法值透传（仍报 invalid int value，rc=2）")
    _check("--phase BOGUS", ["--phase", "BOGUS"], _expect_passthrough_bogus("BOGUS"))
    _check("--phase=BOGUS", ["--phase=BOGUS"], _expect_passthrough_bogus("BOGUS"))

    print("\n[组 6] --phase 缺值不崩溃")
    _check("--phase（无值）", ["--phase"], _expect_missing_value)

    total = len(_RESULTS)
    passed = sum(1 for _, ok in _RESULTS if ok)
    failed = total - passed
    print("\n" + "-" * 64)
    print(f"汇总：用例 {total} | 通过 {passed} | 失败 {failed}")
    print("-" * 64)
    if failed:
        print("FAILED: " + ", ".join(n for n, ok in _RESULTS if not ok))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
