#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""protocol_check.py 的注入式自测（退出码链路回归 + 门禁有效性回归）

只验证「干净副本返回 0」无法区分校验器「真的在判定」与「永远返回 0」。
本脚本把 protocol_check.py 复制到 tempfile 临时目录，按需注入一处破坏，
再逐套件断言退出码：

  P1 干净副本 envelope                    -> rc=0
  N1 注入 status 非法值（GARBAGE）        -> envelope    rc=1
  N2 注入集成违规检出失效（漏检 cp-008）  -> integration rc=1
  P2 干净副本 conflict 与 integration     -> 两者均 rc=0

v2.3.0 Phase C 批次 4 新增（工作面 A：协议门禁强化）：
  N3 注入破坏 integration 阶段序列        -> integration rc=1
  N4 注入破坏 evidence ref 格式校验分支  -> envelope    rc=1
  N5 注入破坏降级场景 source_unavailable  -> envelope    rc=1
  N6 注入破坏 HANDOFF 的 context_ref 必填 -> envelope    rc=1
  N7 注入破坏冲突仲裁层级 2 置信度比较    -> conflict    rc=1
  N8 注入破坏信封层 pointer 格式校验分支  -> envelope    rc=1
  N9 注入破坏覆盖层 pointer 形态校验      -> integration rc=1
  N10 注入破坏 context_ref list 形态逐条校验分支 -> envelope rc=1
      （R2 P1-1 重构：原 N10 与 N6 锚点重复，改为覆盖 list 分支这一独立维度）
  N11 注入幽灵成员 ID 到流水线 producers（整包副本态）-> integration rc=1
      （R2 P0-2 配套：真值源断言「流水线成员引用 ⊆ agents/*.md」的负例）
  P3 干净副本全量套件                     -> all         rc=0

注入采用「锚点唯一性 + 落盘校验」：锚点在副本中必须恰好出现 1 次，替换后
旧串必须消失、目标串必须出现，否则用例前置断言失败（不静默空转）。

每条用例还断言输出标记：rc=1 时输出必须含 ❌，rc=0 时输出不得含 ❌。

仅用标准库，脚本自身 sys.exit(0/1)；不写仓库，只写 tempfile。
不依赖网络，不依赖本机私有环境（如 ~/.workbuddy/mcp.json）。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "protocol_check.py"

# 注入锚点（与 protocol_check.py 保持同步；改字即会让对应用例前置断言失败）
ANCHOR_STATUS = '"status": "success"'
INJECT_STATUS = '"status": "GARBAGE"'
ANCHOR_INTEGRATION = "check_handoff_coverage(checkpoints, ok_refs[:-1])"
INJECT_INTEGRATION = "check_handoff_coverage(checkpoints, ok_refs)"

# N3：把阶段流水线的某个阶段名改错（错名不含任何被 C8 扫描命中的历史废弃
# 术语字面量，只用与 state_io.PHASES 明显不同的伪阶段名）。
ANCHOR_PHASE = '"stage": "COLLAPSE"'
INJECT_PHASE = '"stage": "COLLAPSED"'

# N4：把证据 ref 格式校验分支改成恒返回空列表（校验彻底失效）
# 锚点取「分支体首行 + 紧随的 ref 取值行」，保证在 protocol_check.py 中唯一命中。
ANCHOR_REF_BODY = '''    fails = []
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        ref = e.get("ref")'''
INJECT_REF_BODY = '''    fails = []
    return []  # 注入破坏：ref 格式校验恒返回空列表
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        ref = e.get("ref")'''

# N5：把降级标注校验分支改成恒返回空列表（降级场景失去约束）
ANCHOR_DEGRADE_BODY = '''    fails = []
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        marked = _has_source_unavailable(e)'''
INJECT_DEGRADE_BODY = '''    fails = []
    return []  # 注入破坏：降级标注校验恒返回空列表
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        marked = _has_source_unavailable(e)'''

# N6：把 HANDOFF 的 context_ref 必填判定短路（恒判为存在）
ANCHOR_CTX_REQUIRED = '''    if require_context_ref and not _context_ref_present(cr):
        fails.append("context_ref 必填")'''
INJECT_CTX_REQUIRED = '''    if require_context_ref and not _context_ref_present(cr):
        pass  # 注入破坏：context_ref 必填判定被短路'''

# N7：把冲突仲裁层级 2 的置信度比较改成恒等（永远取第一个）
ANCHOR_CONF_COMPARE = '''    by_conf = max(winners, key=lambda p: p.get("confidence", 0))'''
INJECT_CONF_COMPARE = '''    by_conf = max(winners, key=lambda p: 0)  # 注入破坏：置信度比较恒等'''

# N8：把信封层的 pointer 格式校验分支改成恒返回空列表（pointer 形态校验失效）
# 锚点取「pointer 校验函数体的判定行」，在 protocol_check.py 中唯一命中。
ANCHOR_PTR_CHECK = '''    if not _is_valid_context_pointer(pointer_str):
        fails.append(f"{label}.pointer 格式非法: {pointer!r}")
        return fails'''
INJECT_PTR_CHECK = '''    if not _is_valid_context_pointer(pointer_str):
        return fails  # 注入破坏：pointer 格式校验恒返回空
    if False:
        fails.append(f"{label}.pointer 格式非法: {pointer!r}")
        return fails'''

# N9：把覆盖层的 pointer 形态校验改成恒返回空列表
# （覆盖层原本只做字符串集合覆盖，形态错的 pointer 静默通过）
# 锚点覆盖**整个两分支块**（通用形态非法 + HANDOFF 非 cp-* 指针），
# 两个分支都改为不追加失败原因 —— 只短路其中一个分支无法废掉校验：
# 集成段的反例指针 state://phase2/xxx 属「通用形态合法」，它是被第二个
# 分支（require_checkpoint 的 cp-* 要求）抓到的。
ANCHOR_PTR_INV = '''        if not _is_valid_context_pointer(pointer_str):
            bad.append(f"context_ref.pointer 格式非法: {pointer!r}")
        elif require_checkpoint and not CHECKPOINT_POINTER_PATTERN.match(pointer_str):
            bad.append(f"context_ref.pointer 格式非法: {pointer!r}")'''
INJECT_PTR_INV = '''        if not _is_valid_context_pointer(pointer_str):
            pass  # 注入破坏：覆盖层 pointer 形态校验失效
        elif require_checkpoint and not CHECKPOINT_POINTER_PATTERN.match(pointer_str):
            pass  # 注入破坏：覆盖层 pointer 形态校验失效'''

# N10：破坏 context_ref 的 **list 形态**逐条校验分支（R2 P1-1 重构：
# 原 N10 与 N6 锚点逐字相同、注入同一位置，13 条里有一条纯重复。改为把
# check_envelope 的 list 分支整体替换为恒跳过——覆盖「list 形态逐条校验」
# 这一独立失败维度，与 N6（dict 形态必填判定）互不重叠。锚点取 list 分支
# 起始行到函数 return（含），整段替换保证缩进合法且唯一命中。）
ANCHOR_LIST_BRANCH = '''    elif isinstance(cr, list):
        for i, r in enumerate(cr):
            if not isinstance(r, dict):
                # 健壮性：list 元素不是 dict 时旧实现会 AttributeError 崩溃，
                # 改为显式失败原因。
                fails.append(f"context_ref[{i}] 必须是字典")
                continue
            if r.get("mode") not in VALID_CONTEXT_MODES:
                fails.append(f"context_ref[{i}].mode 非法: {r.get('mode')!r}")
            else:
                # list 形态逐条校验 pointer（带下标，便于定位是哪一条回引）
                fails.extend(_check_context_pointer(r, f"context_ref[{i}]",
                                                    require_checkpoint=is_handoff))
    return fails'''
INJECT_LIST_BRANCH = '''    elif isinstance(cr, list):
        pass  # 注入破坏：list 形态逐条校验被整体短路
    return fails'''

# 用例：(编号, 说明, 套件列表, 注入(old,new)或 None, 期望 rc, 期望命中片段或 None)
# 期望 rc=0 且未给命中片段时，额外要求输出中不出现失败标记。
CASES = [
    ("P1", "干净副本 envelope", ["envelope"], None, 0, None),
    ("N1", "注入 status=GARBAGE 使主套件判定失败", ["envelope"],
     (ANCHOR_STATUS, INJECT_STATUS), 1, "❌"),
    ("N2", "注入集成违规检出失效（漏检 cp-008）", ["integration"],
     (ANCHOR_INTEGRATION, INJECT_INTEGRATION), 1, "❌"),
    ("P2", "干净副本 conflict 与 integration", ["conflict", "integration"], None, 0, None),
    ("N3", "注入破坏阶段流水线序列（阶段名改错）", ["integration"],
     (ANCHOR_PHASE, INJECT_PHASE), 1, "❌"),
    ("N4", "注入破坏 evidence ref 格式校验分支", ["envelope"],
     (ANCHOR_REF_BODY, INJECT_REF_BODY), 1, "❌"),
    ("N5", "注入破坏降级场景 source_unavailable 校验", ["envelope"],
     (ANCHOR_DEGRADE_BODY, INJECT_DEGRADE_BODY), 1, "❌"),
    ("N6", "注入破坏 HANDOFF 的 context_ref 必填校验", ["envelope"],
     (ANCHOR_CTX_REQUIRED, INJECT_CTX_REQUIRED), 1, "❌"),
    ("N7", "注入破坏冲突仲裁层级 2 置信度比较", ["conflict"],
     (ANCHOR_CONF_COMPARE, INJECT_CONF_COMPARE), 1, "❌"),
    ("N8", "注入破坏信封层 pointer 格式校验分支", ["envelope"],
     (ANCHOR_PTR_CHECK, INJECT_PTR_CHECK), 1, "❌"),
    ("N9", "注入破坏覆盖层 pointer 形态校验", ["integration"],
     (ANCHOR_PTR_INV, INJECT_PTR_INV), 1, "❌"),
    ("N10", "注入破坏 context_ref list 形态逐条校验分支", ["envelope"],
     (ANCHOR_LIST_BRANCH, INJECT_LIST_BRANCH), 1, "❌"),
    ("N11", "注入幽灵成员到流水线 producers（整包副本态）", ["integration"],
     ('"upstream": ("FREEZE",), "producers": ("meta-architect",),',
      '"upstream": ("FREEZE",), "producers": ("meta-architect", "GHOST-MEMBER"),'),
     1, "幽灵成员"),
    ("P3", "干净副本全量套件", ["all"], None, 0, None),
]


def inject_replace(path: Path, old: str, new: str) -> None:
    """精确替换一处，并强制断言锚点唯一且注入确实落盘。"""
    text = path.read_text(encoding="utf-8")
    n = text.count(old)
    assert n == 1, f"锚点 {old!r} 在副本中出现 {n} 次（期望 1），拒绝静默 no-op"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    after = path.read_text(encoding="utf-8")
    assert old not in after, f"注入未落盘：旧串 {old!r} 仍残留"
    assert new in after, f"注入未落盘：目标串 {new!r} 未出现"


def run_case(cid, desc, suites, mutate, expect_rc, expect_hit) -> bool:
    with tempfile.TemporaryDirectory(prefix="pc-rc-selftest-") as tmp:
        checker = Path(tmp) / "protocol_check.py"
        shutil.copy2(CHECKER, checker)
        # 阶段流水线校验会按路径加载 state_io.py（importlib 按文件路径加载），
        # 副本目录里没有该文件 → 必须一并复制，否则 N3 会在加载阶段就抛错，
        # 变成「因缺文件而失败」而非「因门禁生效而失败」，属假红。
        state_io_src = CHECKER.parent / "state_io.py"
        state_io_dst = Path(tmp) / "state_io.py"
        if state_io_src.is_file():
            shutil.copy2(state_io_src, state_io_dst)
        # N11（流水线幽灵成员）需要 agents/*.md 真值源：单文件副本态下新断言
        # 按 design SKIP 放行，会让负例「注入了却不变红」假绿。因此本用例走
        # 整包副本（whole_pkg=True 时把整个包复制到临时目录再注入）。
        whole_pkg = (cid == "N11")
        if whole_pkg:
            pkg_src = CHECKER.parents[3]
            pkg_dst = Path(tmp) / "pkg"
            shutil.copytree(
                pkg_src, pkg_dst,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".backups"),
            )
            checker = pkg_dst / "skills/research-orchestration-workflow/scripts/protocol_check.py"
        if mutate is not None:
            try:
                inject_replace(checker, mutate[0], mutate[1])
            except AssertionError as exc:
                print(f"  ❌ {cid} {desc}: 前置断言失败 —— {exc}")
                return False
        rcs = []
        outputs = []
        for suite in suites:
            proc = subprocess.run(
                [sys.executable, str(checker), suite],
                capture_output=True, text=True, encoding="utf-8",
            )
            rcs.append(proc.returncode)
            outputs.append(proc.stdout + proc.stderr)
        joined = "\n".join(outputs)
        rc_ok = all(rc == expect_rc for rc in rcs)
        if expect_hit is not None:
            # 大小写无关匹配（re.IGNORECASE），避免标记字符变体导致漏命中
            hit_ok = re.search(re.escape(expect_hit), joined, re.IGNORECASE) is not None
        elif expect_rc == 0:
            hit_ok = "❌" not in joined
        else:
            hit_ok = True
        ok = rc_ok and hit_ok
        mark = "✅" if ok else "❌"
        print(f"  {mark} {cid} {desc}: 套件={'/'.join(suites)}  "
              f"rc={','.join(str(r) for r in rcs)}（期望 {expect_rc}）  命中预期={hit_ok}")
        if not ok:
            for line in joined.splitlines():
                if "❌" in line or "Traceback" in line:
                    print("       ", line.strip())
        return ok


def main() -> int:
    if not CHECKER.is_file():
        print(f"❌ 找不到校验器: {CHECKER}")
        return 1
    print("=" * 72)
    print(f"protocol_check 退出码注入式自测  校验器: {CHECKER}")
    print(f"用例数: {len(CASES)}")
    print("=" * 72)
    print("\n逐条执行：")
    failures = 0
    for cid, desc, suites, mutate, expect_rc, expect_hit in CASES:
        if not run_case(cid, desc, suites, mutate, expect_rc, expect_hit):
            failures += 1
    passed = len(CASES) - failures
    print("\n" + "=" * 72)
    if failures:
        print(f"❌ 自测未通过：{passed}/{len(CASES)} 条行为符合预期（{failures} 条不符）")
        print("=" * 72)
        return 1
    print(f"✅ 自测通过：{passed}/{len(CASES)} 条行为均符合预期")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
