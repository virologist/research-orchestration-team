#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rot.py — Research Orchestration Toolkit（科研编排团统一 CLI 入口）

一条命令完成过去需要照抄 18 行清单的重复确定性操作，并落盘结构化证据：

    python3 scripts/rot.py check      全部门禁逐条独立 rc + 证据报告
    python3 scripts/rot.py verify     文档 ↔ 仓库实际 全量差集（发布契约第 5 条脚本化）
    python3 scripts/rot.py sample     对真实任务产出跑 A1–A9 断言
    python3 scripts/rot.py feedback   反馈记录完整性 / 规则膨胀 / 认可样例状态
    python3 scripts/rot.py roadmap    打印工作地图摘要
    python3 scripts/rot.py report     汇总最近一次检查报告与四种状态

纪律：
  - 逐条独立取 rc，绝不把多条命令串成一条只看整体 rc（沙箱截断会伪装成全绿）。
  - 跳过（SKIP）不计入通过，状态标「尚未验证」。
  - rc≠0/1 先查命令、路径、参数，不直接归因为门禁失效。
  - 语义与价值判断不进自动断言；程序只登记人工确认点。

退出码：0 通过 / 1 校验失败 / 2 文件不存在 / 3 参数缺失。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MARKERS = ("workmap.json", ".codebuddy-plugin")
S = "skills/research-orchestration-workflow/scripts"
PLATFORM_STEPS = {"Checkout", "Setup Python", "Set up job", "Post Setup Python",
                  "Post Checkout", "Complete job"}
REPORT_DIR = Path(".harness-runs/verify")


def find_root(start: Path | None = None) -> Path | None:
    """向上逐层探测包根，禁用 parents[N] 硬索引（跨平台布局差异会 IndexError）。"""
    p = (start or Path(__file__).resolve()).absolute()
    for cand in [p, *p.parents]:
        if all((cand / m).exists() for m in MARKERS):
            return cand
    return None


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# ── 门禁注册表：与 workmap.json 的 gates.static / structural 一一对应 ──────
GATES: list[tuple[str, list[str], int]] = [
    ("manifest_check", ["scripts/manifest_check.py"], 0),
    ("manifest_check_selftest", ["scripts/manifest_check_selftest.py"], 0),
    ("protocol_envelope", [f"{S}/protocol_check.py", "envelope"], 0),
    ("protocol_conflict", [f"{S}/protocol_check.py", "conflict"], 0),
    ("protocol_integration", [f"{S}/protocol_check.py", "integration"], 0),
    ("protocol_check_selftest", [f"{S}/protocol_check_selftest.py"], 0),
    ("phase_normalization", ["scripts/test_phase_normalization.py"], 0),
    ("harness_eval", ["scripts/harness_eval.py"], 0),
    ("harness_eval_selftest", ["scripts/harness_eval_selftest.py"], 0),
    ("routing_eval", ["scripts/routing_eval.py"], 0),
    ("routing_eval_selftest", ["scripts/routing_eval_selftest.py"], 0),
    ("vendor_core", ["tests/test_vendor_core.py"], 0),
    ("state_ceilings", ["tests/test_state_ceilings.py"], 0),
    ("state_io_guards", ["tests/test_state_io_guards.py"], 0),
    ("lead_source_of_truth", ["tests/test_lead_source_of_truth.py"], 0),
    ("state_runtime_sequencing", ["tests/test_state_runtime_sequencing.py"], 0),
    ("state_file_robustness", ["tests/test_state_file_robustness.py"], 0),
    ("topic_scoring_edge", [f"{S}/topic_scoring.py", "--topic", "边界探针",
                             "--originality", "11", "--feasibility", "7",
                             "--value-density", "9", "--data-availability", "7",
                             "--competition", "6", "--cognition", "8",
                             "--resource-fit", "7", "--sustainability", "7"], 1),
    ("workmap_check", ["scripts/workmap_check.py"], 0),
    ("workmap_check_selftest", ["scripts/workmap_check.py", "--self-test"], 0),
    ("sample_check_selftest", ["scripts/sample_check.py", "--self-test"], 0),
    ("feedback_check", ["scripts/rot.py", "feedback"], 0),
]


def run_cmd(root: Path, args: list[str], timeout: int = 240) -> dict:
    """执行一条命令，独立取 rc，返回结构化证据。"""
    rel = args[0]
    f = root / rel
    if not f.is_file():
        return {"rc": 2, "duration_s": 0.0, "status": "尚未验证",
                "evidence": f"文件不存在：{rel}", "cmd": "python3 " + " ".join(args)}
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, *args], cwd=root, capture_output=True,
                           text=True, timeout=timeout)
        dur = round(time.time() - t0, 2)
        lines = [x.strip() for x in (p.stdout + "\n" + p.stderr).splitlines() if x.strip()]
        tail = " | ".join(lines[-3:])[:400]
        return {"rc": p.returncode, "duration_s": dur, "cmd": "python3 " + " ".join(args),
                "evidence": tail,
                "evidence_sha256": hashlib.sha256((p.stdout + p.stderr).encode("utf-8", "replace")).hexdigest()[:16]}
    except subprocess.TimeoutExpired:
        return {"rc": 137, "duration_s": round(time.time() - t0, 2),
                "status": "尚未验证", "evidence": f"TIMEOUT >{timeout}s（未执行完，不算通过）",
                "cmd": "python3 " + " ".join(args)}


def cmd_check(root: Path, fast: bool = False, json_only: bool = False) -> int:
    report = {"schema": "rot-check-report/v1",
              "timestamp": datetime.now().isoformat(timespec="seconds"),
              "root": str(root), "git_head": git(root, "rev-parse", "--short", "HEAD"),
              "mode": "fast" if fast else "full", "items": [], "summary": {}}
    if not json_only:
        print("=== rot.py check · 全仓门禁逐条独立执行 ===")
    slow = {"manifest_check_selftest", "harness_eval_selftest"}
    ok = True
    for name, args, expected in GATES:
        if fast and name in slow:
            item = {"id": name, "expected_rc": expected, "rc": None, "status": "尚未验证",
                    "evidence": "--fast 跳过（未执行，不计入通过）", "cmd": "python3 " + " ".join(args),
                    "duration_s": 0.0}
            report["items"].append(item)
            if not json_only:
                print(f"[SKIP] {name:<30} 尚未验证（--fast）")
            continue
        r = run_cmd(root, args)
        r.update({"id": name, "expected_rc": expected})
        r["status"] = "自动验证通过" if r["rc"] == expected else "自动验证未通过"
        if r["rc"] not in (0, 1) and r["rc"] is not None:
            r["status"] = "尚未验证"  # rc=2/3/127/137 先查命令，不算门禁失败
        report["items"].append(r)
        ok &= (r["status"] == "自动验证通过")
        if not json_only:
            mark = "OK " if r["status"] == "自动验证通过" else "BAD"
            print(f"[{mark}] {name:<30} rc={str(r['rc']):<3} 期望={expected:<2} "
                  f"{r['duration_s']:>6.1f}s  {r['evidence'][:95]}")
    passed = sum(1 for x in report["items"] if x["status"] == "自动验证通过")
    skipped = sum(1 for x in report["items"] if x["status"] == "尚未验证")
    report["summary"] = {"total": len(GATES), "passed": passed, "skipped": skipped,
                         "failed": len(GATES) - passed - skipped, "all_green": ok and skipped == 0,
                         "note": "结构化门禁通过 ≠ 任务产出质量通过；A10/A11 与 CK 人工确认点仍需人工复核"}
    out = root / REPORT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"report-{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not json_only:
        print(f"\n汇总：{passed} 自动验证通过 / {report['summary']['failed']} 未通过 / {skipped} 尚未验证")
        print(f"结构化证据已落盘：{out / 'latest.json'}")
        print("RESULT: " + ("ALL GREEN" if report["summary"]["all_green"] else "NOT GREEN"))
    return 0 if report["summary"]["all_green"] else 1


def ck_line(lines: list[str], code: str, cond: bool, msg: str) -> bool:
    lines.append(f"[{'OK ' if cond else 'BAD'}] {code} {msg}")
    return cond


def cmd_verify(root: Path) -> int:
    """文档 ↔ 仓库实际 全量差集核对：把 README 发布契约第 5 条变成程序检查。"""
    print("=== rot.py verify · 全量文档差集核对（FM-R2-07 根治项）===")
    lines: list[str] = []
    ok = True
    rd = (root / "README.md").read_text(encoding="utf-8")
    cb = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    ch = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    wm = json.loads((root / "workmap.json").read_text(encoding="utf-8"))

    tests = sorted(p.name for p in (root / "tests").glob("*.py"))
    miss = [n for n in tests if n not in rd or n not in cb]
    ok &= ck_line(lines, "V1", not miss, f"tests/ {len(tests)} 个文件均在 README 结构树与 CONTRIBUTING 命令清单 {miss or 'OK'}")

    scripts = sorted(p.name for p in (root / "scripts").glob("*.py"))
    miss2 = [n for n in scripts if n not in rd]
    ok &= ck_line(lines, "V2", not miss2, f"scripts/ {len(scripts)} 个脚本均在 README 结构树 {miss2 or 'OK'}")

    core = ["workmap.json", "WORKMAP.md", "feedback/RULES.md", "feedback/RECORDS.jsonl",
            "test-prompts.json"]
    miss3 = [n for n in core if n.split("/")[-1] not in rd and n not in rd]
    ok &= ck_line(lines, "V3", not miss3, f"新增核心交付物均在 README 登记 {miss3 or 'OK'}")

    wf = (root / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    steps = [l.strip()[8:] for l in wf.splitlines() if l.strip().startswith("- name:")]
    gates_n = len([s for s in steps if s not in PLATFORM_STEPS])
    expect_n = (len(wm["gates"]["static"]) + len(wm["gates"]["structural"])
                + len(wm["gates"]["documentation"]))
    ok &= ck_line(lines, "V4", gates_n == expect_n,
                  f"CI 门禁 step {gates_n} == workmap 登记 {expect_n}"
                  f"（18 静态 + 4 结构 + 1 文档差集；yml 内平台 step {len(steps)-gates_n}）")

    v1 = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    v2 = json.loads((root / ".codebuddy-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    m = re.search(r"> \*\*版本\*\*：([\d.]+)", rd)
    ok &= ck_line(lines, "V5", v1 == v2 == m.group(1) == wm["version"],
                  f"四处版本一致 {v1}/{v2}/{m.group(1) if m else '?'}/{wm['version']}")

    hist = [tuple(int(x) for x in mm.groups()) for mm in
            re.finditer(r"- \*\*v(\d+)\.(\d+)\.(\d+)\*\*", rd)]
    ok &= ck_line(lines, "V6", hist == sorted(hist) and f"## [{v1}]" in ch,
                  f"README 版本历史 {len(hist)} 条严格升序；CHANGELOG 有 [{v1}] 段")

    st = (root / "docs/harness-iteration-loop.md").read_text(encoding="utf-8")
    ok &= ck_line(lines, "V7", "起始状态" in st and "FM-R2-07" in st,
                  "状态文件 §10 入口轮次与最新失败模式已登记")

    le = (root / "skills/research-orchestration-workflow/references/LEARNING.md").read_text(encoding="utf-8")
    ok &= ck_line(lines, "V8", "FM-R2-07" in le and (root / "feedback/RECORDS.jsonl").is_file(),
                  "LEARNING 回流与结构化反馈记录均在位")

    ok &= ck_line(lines, "V9", "5. **全量文档差集核对" in rd,
                  "README 发布契约第 5 条在位（本命令即其实现）")

    cmds = [l for l in cb.splitlines() if l.startswith("python3 ")]
    # 只在「命令清单区块」内检查旧计数；版本历史里引用旧数字属合法历史描述，
    # 全文扫会把合法记录误判为口径矛盾（FM-R1-04 同族：验收前提需先界定范围）。
    try:
        blk = rd[rd.index("# 3. 健康检查"):rd.index("> **validate_expert.py 的已知限制**")]
    except ValueError:
        blk = ""
    ok &= ck_line(lines, "V10", "rot.py check" in cb and len(cmds) >= 18 and bool(blk)
                  and "集成仿真 10/10" in blk and "协议注入式负例自测 14 条" in blk
                  and "9/9" not in blk,
                  f"统一入口在 CONTRIBUTING、本地命令 {len(cmds)} 条、命令清单区块计数口径无矛盾")

    for l in lines:
        print("  " + l)
    print("VERIFY: " + ("ALL GREEN" if ok else "FAILED"))
    return 0 if ok else 1


VALID_TYPES = {"tool_fix", "program_check", "accepted_example", "long_term_rule", "single_request"}
VALID_STATUS = {"自动验证通过", "AI 评估通过", "人工确认通过", "尚未验证", "archived"}
REQUIRED_FIELDS = ("id", "type", "source", "evidence", "conversion", "check", "status", "created")


def cmd_feedback(root: Path) -> int:
    """反馈记录完整性与规则膨胀检查（F1–F8）。"""
    print("=== rot.py feedback · 反馈记录与规则膨胀检查 ===")
    lines: list[str] = []
    ok = True
    p = root / "feedback/RECORDS.jsonl"
    if not p.is_file():
        print("  [BAD] F1 RECORDS.jsonl 不存在")
        return 1
    recs = []
    bad = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            recs.append(r)
            if any(k not in r for k in REQUIRED_FIELDS):
                bad.append(f"line {i} 缺字段")
        except json.JSONDecodeError as e:
            bad.append(f"line {i} 非法 JSON: {e}")
    ok &= ck_line(lines, "F1", not bad, f"{len(recs)} 条记录字段齐全 {bad or 'OK'}")
    ids = [r.get("id") for r in recs]
    ok &= ck_line(lines, "F2", len(ids) == len(set(ids)), "id 唯一")
    ok &= ck_line(lines, "F3", all(r.get("type") in VALID_TYPES for r in recs),
                  "type 均在白名单（工具修复/程序检查/认可样例/长期规则/单次要求）")
    ok &= ck_line(lines, "F4", all(r.get("status") in VALID_STATUS for r in recs),
                  "status 均为四种状态之一或 archived")

    missing = [f"{r['id']}->{r['check']}" for r in recs
               if r.get("type") in ("tool_fix", "program_check", "long_term_rule")
               and (not r.get("check") or not (root / r["check"]).is_file())]
    ok &= ck_line(lines, "F5", not missing, f"承接检查路径真实存在 {missing or 'OK'}")

    cap = int(re.search(r"(\d+)", wm_rule_cap(root)).group(1))
    active = [r for r in recs if r.get("type") == "long_term_rule" and r.get("status") != "archived"]
    ok &= ck_line(lines, "F6", len(active) <= cap, f"长期规则 {len(active)}/{cap} 条，未超上限")

    ex = sorted((root / "feedback/accepted").glob("*.md"))
    shape_ok = all(all(k in f.read_text(encoding="utf-8") for k in
                       ("来源与证据", "为什么算好", "可复跑", "状态")) for f in ex)
    # 只检查「状态行是否被直接标为人工确认通过」；正文里出现「不标人工确认通过」不算冒充
    no_fake = all(not re.search(r"^\*\*状态\*\*：\s*\*{0,2}人工确认通过",
                                f.read_text(encoding="utf-8"), re.M) for f in ex)
    ok &= ck_line(lines, "F7", len(ex) >= 3 and shape_ok and no_fake,
                  f"认可样例 {len(ex)} 个、四段结构齐全、未冒充用户确认")

    ru = (root / "feedback/RULES.md").read_text(encoding="utf-8")
    ok &= ck_line(lines, "F8", all(k in ru for k in ("工具修复", "程序检查", "认可样例", "文字规则", "上限 24 条")),
                  "RULES.md 转化优先级与上限在位")
    for l in lines:
        print("  " + l)
    print("FEEDBACK: " + ("ALL GREEN" if ok else "FAILED"))
    return 0 if ok else 1


def wm_rule_cap(root: Path) -> str:
    d = json.loads((root / "workmap.json").read_text(encoding="utf-8"))
    return d["feedback"]["rule_cap"]


def cmd_roadmap(root: Path) -> int:
    d = json.loads((root / "workmap.json").read_text(encoding="utf-8"))
    print(f"工作地图 {d['version']} · {d['purpose']}")
    print("\n任务：")
    for t in d["tasks"]:
        print(f"  {t['id']} {t['name']:<14} 阶段 {'→'.join(t['phases']):<28} "
              f"验收 {','.join(t['acceptance']):<22} 人工点 {','.join(t['human_gates']) or '—'}")
    print("\n人工确认点（程序不代替）：")
    for k, v in d["human_gates"].items():
        print(f"  {k:<10} {v['when']} → {v['what']}（{v['skippable']}）")
    print("\n状态：" + " / ".join(d["status_labels"]))
    return 0


def cmd_report(root: Path) -> int:
    p = root / REPORT_DIR / "latest.json"
    if not p.is_file():
        print("尚未生成检查报告，请先跑 python3 scripts/rot.py check")
        return 2
    r = json.loads(p.read_text(encoding="utf-8"))
    print(f"最近报告 {r['timestamp']} · HEAD {r['git_head']} · 模式 {r['mode']}")
    for label in ("自动验证通过", "自动验证未通过", "尚未验证"):
        items = [x["id"] for x in r["items"] if x["status"] == label]
        print(f"  {label}: {len(items)}" + (f"  {items}" if label != "自动验证通过" else ""))
    print("  人工确认通过: 0（本工具无权标注；A10/A11 与 CK 点须由用户确认）")
    print("  证据文件: " + str(p))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="科研编排团统一 CLI 入口",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="全仓门禁逐条独立 rc + 结构化证据落盘")
    c.add_argument("--fast", action="store_true", help="跳过两条耗时 selftest（标尚未验证，不计通过）")
    c.add_argument("--json-only", action="store_true", help="只落盘，不打印明细")
    sub.add_parser("verify", help="文档 ↔ 仓库实际 全量差集核对")
    s = sub.add_parser("sample", help="对真实任务产出跑 A1–A9 断言")
    s.add_argument("--run-dir", required=True)
    s.add_argument("--json", dest="json_out")
    sub.add_parser("feedback", help="反馈记录完整性与规则膨胀检查")
    sub.add_parser("roadmap", help="打印工作地图摘要")
    sub.add_parser("report", help="汇总最近检查报告的四种状态")
    a = ap.parse_args()
    root = find_root()
    if root is None:
        print("❌ 未找到包根（workmap.json + .codebuddy-plugin）", file=sys.stderr)
        return 2
    if a.cmd == "check":
        return cmd_check(root, fast=a.fast, json_only=a.json_only)
    if a.cmd == "verify":
        return cmd_verify(root)
    if a.cmd == "feedback":
        return cmd_feedback(root)
    if a.cmd == "roadmap":
        return cmd_roadmap(root)
    if a.cmd == "report":
        return cmd_report(root)
    if a.cmd == "sample":
        rd = Path(a.run_dir).resolve()
        if not rd.is_dir():
            print(f"❌ 产出目录不存在：{rd}", file=sys.stderr)
            return 2
        args = ["scripts/sample_check.py", "--run-dir", str(rd)]
        if a.json_out:
            args += ["--json", str(Path(a.json_out).resolve())]
        r = run_cmd(root, args)
        print(r["evidence"])
        return 0 if r["rc"] == 0 else 1
    return 3


if __name__ == "__main__":
    sys.exit(main())
