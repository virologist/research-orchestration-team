#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness_eval.py 的注入式自测（负例套件）

## 为什么需要这个脚本

`harness_eval.py` 是「校验器」。但如果只测它的**正向**行为（干净仓库下 rc=0），
就无法区分「它真的在检查」与「它只是永远返回 0」。这正是本项目历史上踩过的坑：
CI 的术语清单写成了精确串，导致真实存在的违规因插入词而漏检，形成**假绿**。

本脚本用**注入式负例**证明校验器仍然有效：每一条都先把仓库复制到临时目录、
故意破坏一处、然后断言：

  1. 校验器退出码为 1（硬失败，而不是 rc=0 放行）
  2. 输出中命中**预期的检查项文案**（而不是碰巧因为别的原因失败）

条件 2 很重要 —— 只断言退出码会让「任何错误都算通过」，掩盖检查项本身的失效。

## 用例分组

  N1-N12   H1-H12 各一条破坏型负例（注入破坏 → 期望 rc=1 + 命中预期文案）
  R1       反向用例（H11 加后缀破坏 → 期望 rc=0，子串匹配语义不变）

## 与 manifest_check_selftest 的关系

  manifest_check_selftest.py  →  校验 manifest / 资产 / 版本 / 术语
  harness_eval_selftest.py   →  校验 Harness Engineering 12 项设计模式

两者互不替代。前者防「manifest 漂移」；后者防「harness 退化」。

## 用法

  python3 scripts/harness_eval_selftest.py          # 全部用例
  python3 scripts/harness_eval_selftest.py -k N5    # 只跑名字含 N5 的用例

## 退出码

  0 = 全部用例行为符合预期
  1 = 存在不符合预期的用例（校验器可能已退化）
  2 = 环境错误（找不到仓库根 / harness_eval.py）

## 依赖

仅标准库，Python >= 3.9。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "scripts" / "harness_eval.py"
COPY_EXCLUDE = {".git", "__pycache__", ".backups"}

# 每个用例：(编号, 说明, 期望命中的输出片段, 期望退出码, 破坏函数)
CASES = []


def case(cid, desc, expect, mutate, expect_rc=1):
    CASES.append((cid, desc, expect, expect_rc, mutate))


# ── H 组：Harness Engineering 12 项破坏型负例 ────────────────────────────
# N1：H1 agent-registry.md 缺失
def n1(root):
    (root / "skills/research-orchestration-workflow/references/agent-registry.md").unlink()
case("N1", "H1 agent-registry.md 缺失", "agent-registry.md", n1)


# N2：H2 team-lead 缺 max_time（其他两个保留）
def n2(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("max_time", "max_dur"),
        encoding="utf-8",
    )
case("N2", "H2 team-lead 缺 max_time", "max_time", n2)


# N3：H3 protocol 缺 per-step（替换为近义词 end-step）
# 用大小写无关替换，避免漏过 "Per-step Verification" 之类
def n3(root):
    path = root / "skills/research-orchestration-workflow/references/agent-protocol.md"
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(r"per[\s_-]?step", "end-step", text, flags=re.IGNORECASE)
    path.write_text(new_text, encoding="utf-8")
case("N3", "H3 protocol per-step 替换为近义词", "per-step", n3)


# N4：H4 SKILL.md 缺 compact（替换为 collapse）
def n4(root):
    path = root / "skills/research-orchestration-workflow/SKILL.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("compact", "collapse"),
        encoding="utf-8",
    )
case("N4", "H4 SKILL.md compact 替换为近义词", "compact", n4)


# N5：H5 atomic subagent 缺失（删 domain-expert-ai.md）
def n5(root):
    (root / "agents/domain-expert-ai.md").unlink()
case("N5", "H5 atomic subagent 拆分缺 ai", "atomic subagent 拆分缺", n5)


# N6：H6 registry 缺 dangerous
def n6(root):
    path = root / "skills/research-orchestration-workflow/references/agent-registry.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("dangerous", "forbidden"),
        encoding="utf-8",
    )
case("N6", "H6 权限分层缺 dangerous", "权限分级缺", n6)


# N7：H7 team-lead 缺 metrics（大小写无关替换）
def n7(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(r"metric|observability|telemetry", "monitoring", text, flags=re.IGNORECASE)
    path.write_text(new_text, encoding="utf-8")
case("N7", "H7 team-lead 缺 metrics/observability", "metrics", n7)


# N8：H8 team-lead 缺 budget（保留 token）
def n8(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("budget", "quota"),
        encoding="utf-8",
    )
case("N8", "H8 team-lead 缺 token budget", "token budget", n8)


# N9：H9 LEARNING.md 缺失
def n9(root):
    (root / "skills/research-orchestration-workflow/references/LEARNING.md").unlink()
case("N9", "H9 LEARNING.md 缺失", "LEARNING.md", n9)


# N10：H10 team-lead 缺 circuit/熔断（大小写无关替换）
def n10(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    text = path.read_text(encoding="utf-8")
    # 同时处理 "circuit" 和 "熔断"
    new_text = re.sub(r"circuit|熔断", "intervention", text, flags=re.IGNORECASE)
    path.write_text(new_text, encoding="utf-8")
case("N10", "H10 team-lead 缺 circuit breaker", "circuit", n10)


# N11：H11 team-lead 缺 plan_execution
def n11(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("plan_execution", "plan_exec"),
        encoding="utf-8",
    )
case("N11", "H11 team-lead 缺 plan_execution", "plan_execution", n11)


# N12：H12 agent-registry.md 缺失（与 N1 触发相同，但 H12 检测路径不同）
def n12(root):
    (root / "skills/research-orchestration-workflow/references/agent-registry.md").unlink()
case("N12", "H12 agent-registry.md 缺失（另一检查路径）", "agent-registry.md", n12)


# ── R 组：反向用例（保留语义等价 → 应放行）────────────────────────────────
# R1：H11 plan_execution 加后缀 → 子串匹配仍命中 → 应放行
def r1(root):
    path = root / "agents/research-orchestration-team-team-lead.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("plan_execution", "plan_execution_signal"),
        encoding="utf-8",
    )
case("R1", "H11 plan_execution 加后缀（语义不变，应放行）", "", r1, expect_rc=0)


# ── 主流程 ─────────────────────────────────────────────────────────────
def run_case(pristine: Path, tmp_root: Path, cid: str, desc: str,
             expect: str, expect_rc: int, mutate) -> bool:
    """复制干净仓库 → mutate → 跑校验器 → 断言 rc + 命中预期文案。"""
    case_dir = tmp_root / cid
    shutil.copytree(pristine, case_dir, ignore=shutil.ignore_patterns(*COPY_EXCLUDE))
    mutate(case_dir)

    try:
        proc = subprocess.run(
            [sys.executable, str(CHECKER)],
            cwd=case_dir, capture_output=True, text=True, timeout=30,
        )
        output = proc.stdout + proc.stderr
        rc_ok = (proc.returncode == expect_rc)
        hit_ok = (expect in output) if expect else True  # 反向用例 expect 为空，跳过命中检查
        ok = rc_ok and hit_ok

        # 输出可读标记
        marker = "✅" if ok else "❌"
        if expect_rc == 1:
            msg = f"{marker} {cid} {desc}: rc={proc.returncode}（期望 {expect_rc}）"
            if not hit_ok:
                msg += f" 命中预期='{expect}' → False"
        else:
            msg = f"{marker} {cid} {desc}: rc={proc.returncode}（期望 {expect_rc}）"

        print(f"  {msg}")
        return ok

    except subprocess.TimeoutExpired:
        print(f"  ❌ {cid} {desc}: 超时（30s）")
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="harness_eval.py 的注入式自测")
    parser.add_argument("-k", "--keyword", default=None,
                        help="只跑名字含此关键字的用例")
    args = parser.parse_args(argv)

    if not CHECKER.is_file():
        print(f"❌ 找不到 {CHECKER}", file=sys.stderr)
        return 2

    cases = CASES
    if args.keyword:
        cases = [c for c in CASES if args.keyword in c[0] or args.keyword in c[1]]

    print(f"🔍 Harness eval selftest — {len(cases)} 条用例\n")

    with tempfile.TemporaryDirectory(prefix="harness-selftest-") as td:
        pristine = Path(td) / "pristine"
        shutil.copytree(REPO_ROOT, pristine, ignore=shutil.ignore_patterns(*COPY_EXCLUDE))

        tmp_root = Path(td) / "cases"
        tmp_root.mkdir()

        passed = 0
        failed = 0
        for cid, desc, expect, expect_rc, mutate in cases:
            ok = run_case(pristine, tmp_root, cid, desc, expect, expect_rc, mutate)
            if ok:
                passed += 1
            else:
                failed += 1

    total = len(cases)
    print("\n" + "=" * 64)
    if failed == 0:
        print(f"✅ 自测通过：{passed}/{total} 条行为均符合预期")
        return 0
    else:
        print(f"❌ 自测未通过：{passed}/{total} 通过（{failed} 条不符合预期）")
        print("   提示：校验器可能已退化，或某条检查项的文案被改动。")
        return 1


if __name__ == "__main__":
    sys.exit(main())