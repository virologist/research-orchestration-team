#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主理人事实源一致性锁定（R5-E4 组合态盲区修复）
=====================================================================
R5 再诊断实锤（2026-11-10，断言组合态审计 E4）：

  manifest 内存在两个「主理人」字段：`agentName`（C12 读取）与
  `teamInfo.leadAgent` + `members[].role == "lead"`（C13 读取，声明位）。
  修复前二者是**双重事实源**——把主理人三处（agentName / leadAgent /
  role 声明位）同步漂移到同一普通成员时：
    - C2 对等：两侧同步改 → 绿
    - C13 内部自洽：leadAgent == 声明位 → 绿
    - C12：读 agentName，与 settings.json 同步改后也绿
  即「主理人换人」可以静默通过全部 74 项门禁。修复后 C12 以 C13 的
  声明位为唯一事实源，agentName 降级为兼容字段：存在但 ≠ 声明位即红。

本测试把修复语义锁死（对临时目录里的整包副本注入，不碰真实仓库）：
  M1  基线：原始仓库 manifest_check rc=0（前置自检）
  M2  三处同步漂移（agentName + leadAgent + role，含 settings）→ rc=0
      —— 事实源已整体迁移，属于「合法换主理人」，不应误伤
  M3  agentName 漂移但声明位不动 → rc=1 且命中「agentName … 不一致」
  M4  leadAgent 漂移但 role 声明位不动 → rc=1 且命中 C13 声明位文案
  M5  role 声明位漂移但 leadAgent 不动 → rc=1 且命中 C13 声明位文案
  M6  settings.json 与声明位漂移一致 → rc=0（C12 跟随新事实源）

判定同时断言 rc 与失败文案归属（FM-R2-06 纪律）。

用法：python3 tests/test_lead_source_of_truth.py
退出码：0 全部通过 | 1 有失败 | 2 环境错误
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent

OLD_LEAD = "research-orchestration-team-team-lead"
NEW_LEAD = "synthesis-integrator"

RESULTS: list[tuple[str, bool, str]] = []


def _clone_pkg() -> Path:
    """整包克隆到临时目录（APFS cp -cR 优先，copytree 兜底）。"""
    tmp = Path(tempfile.mkdtemp(prefix="lead-sot-"))
    dst = tmp / "pkg"
    proc = subprocess.run(["cp", "-cR", str(PKG), str(dst)], capture_output=True)
    if proc.returncode != 0:
        shutil.copytree(
            PKG, dst,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".backups"),
        )
    return dst


def _drift(pkg: Path, *, agent_name=False, lead_agent=False, role=False,
           settings=False, new_lead=NEW_LEAD, old_lead=OLD_LEAD) -> None:
    """按开关做各字段漂移（只动 codebuddy 侧——C12/C13 读它；C2 会拦单侧，
    故 manifest 两个市场侧都改，settings 按开关）。"""
    for name in (".codebuddy-plugin/plugin.json", ".claude-plugin/plugin.json"):
        p = pkg / name
        d = json.loads(p.read_text(encoding="utf-8"))
        for m in d.get("members", []):
            if not isinstance(m, dict):
                continue
            if m.get("id") == old_lead and role:
                m["role"] = "member"
            elif m.get("id") == new_lead and role:
                m["role"] = "lead"
        if agent_name and "agentName" in d:
            d["agentName"] = new_lead
        ti = d.get("teamInfo")
        if ti is not None and lead_agent:
            ti["leadAgent"] = new_lead
            ma = ti.get("memberAgents", [])
            if new_lead in ma:
                ma.remove(new_lead)
            if old_lead not in ma:
                ma.append(old_lead)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    if settings:
        (pkg / "settings.json").write_text(
            json.dumps({"agent": new_lead}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")


def _run_checker(pkg: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(pkg / "scripts" / "manifest_check.py"), "-v"],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _check(name: str, ok: bool, detail: str) -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name} | {detail}")
    RESULTS.append((name, ok, detail))


def main() -> int:
    print("=" * 68)
    print("主理人事实源一致性锁定（C12 × C13 组合态，R5-E4 修复）")
    print("=" * 68)
    if not (PKG / "scripts" / "manifest_check.py").is_file():
        print(f"❌ 找不到校验器: {PKG / 'scripts' / 'manifest_check.py'}")
        return 2

    # M1 基线
    pkg = _clone_pkg()
    rc, out = _run_checker(pkg)
    _check("M1 基线副本 rc=0", rc == 0 and "Traceback" not in out,
           f"rc={rc}")

    # M2 三处+settings 同步漂移 = 合法换主理人 → rc=0
    pkg = _clone_pkg()
    _drift(pkg, agent_name=True, lead_agent=True, role=True, settings=True)
    rc, out = _run_checker(pkg)
    _check("M2 事实源整体迁移（合法换主理人）rc=0", rc == 0,
           f"rc={rc}（漂移 agentName+leadAgent+role+settings 全同步）")

    # M3 agentName 单独漂移 → C12 新断言红
    pkg = _clone_pkg()
    _drift(pkg, agent_name=True)
    rc, out = _run_checker(pkg)
    hit = "agentName" in out and "不一致" in out
    _check("M3 agentName 漂移（声明位不动）→ 红 + 归属 C12 新断言",
           rc == 1 and hit, f"rc={rc} 命中={hit}")

    # M4 leadAgent 漂移但 role 不动 → C13 声明位断言红
    pkg = _clone_pkg()
    _drift(pkg, lead_agent=True)
    rc, out = _run_checker(pkg)
    hit = "声明位" in out or "leadAgent" in out
    _check("M4 leadAgent 漂移（role 不动）→ 红 + 归属 C13",
           rc == 1 and hit, f"rc={rc} 命中={hit}")

    # M5 role 声明位漂移但 leadAgent 不动 → C13 声明位断言红
    pkg = _clone_pkg()
    _drift(pkg, role=True)
    rc, out = _run_checker(pkg)
    hit = "声明位" in out
    _check("M5 role 声明位漂移（leadAgent 不动）→ 红 + 归属 C13",
           rc == 1 and hit, f"rc={rc} 命中={hit}")

    # M6 settings 跟随声明位 → C12 放行（声明位事实源生效）
    # 注意：agentName 是兼容字段，新语义下「存在则必须 == 声明位」，故合法
    # 换主理人也必须同步 agentName —— 这正是 M2 全同步 rc=0、M3 单独漂
    # agentName 红的语义。M6 验证 C12 跟随「声明位+settings」这一新事实源。
    pkg = _clone_pkg()
    _drift(pkg, agent_name=True, lead_agent=True, role=True, settings=True)
    rc, out = _run_checker(pkg)
    _check("M6 settings+agentName 跟随新声明位 → rc=0（C12 用新事实源）", rc == 0,
           f"rc={rc}")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print("-" * 68)
    if failed:
        print(f"❌ {len(failed)}/{len(RESULTS)} 条用例失败: {failed}")
        return 1
    print(f"✅ {len(RESULTS)}/{len(RESULTS)} 条事实源锁定全部符合设计")
    return 0


if __name__ == "__main__":
    sys.exit(main())
