#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workmap_check.py — 工作地图一致性校验器（W1–W12）

检查 workmap.json 是否是一张「可执行、可验收」的地图，而不是又一份说明文字：
  - 阶段依赖无环、依赖目标真实存在
  - 每个阶段的工具路径真实存在（manual 除外）
  - 每条验收条件要么有可复跑的程序检查，要么显式标 human=true
  - 任务引用的阶段 / 验收条件 / 人工确认点全部有定义
  - 人读视图 WORKMAP.md 与机器真值源双向一致
  - 反馈规则的分类、转化优先级、上限齐全

退出码：0 通过 / 1 校验失败 / 2 文件不存在 / 3 参数缺失。
支持 --root 指定包根；默认向上逐层探测（禁止 parents[N] 硬索引，跨机器布局差异大）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import shutil
from pathlib import Path

MARKERS = ("workmap.json", ".codebuddy-plugin")
STATUS_LABELS = ("自动验证通过", "AI 评估通过", "人工确认通过", "尚未验证")


def find_root(start: Path | None = None) -> Path | None:
    """向上逐层探测包根：同时存在 workmap.json 与 .codebuddy-plugin/ 的目录。"""
    p = (start or Path(__file__).resolve()).absolute()
    for cand in [p, *p.parents]:
        if all((cand / m).exists() for m in MARKERS):
            return cand
    return None


def load(root: Path) -> dict:
    p = root / "workmap.json"
    return json.loads(p.read_text(encoding="utf-8"))


def check(root: Path, verbose: bool = False) -> tuple[list[str], list[str]]:
    """返回 (失败项, 通过项)。"""
    fails: list[str] = []
    oks: list[str] = []

    def ck(code: str, cond: bool, msg: str) -> None:
        (oks if cond else fails).append(f"{code} {'OK' if cond else 'FAIL'} {msg}")

    mapp = root / "workmap.json"
    if not mapp.is_file():
        return ["W1 FAIL workmap.json 不存在"], []
    doc = root / "WORKMAP.md"
    if not doc.is_file():
        return ["W1 FAIL WORKMAP.md 不存在"], []

    try:
        d = load(root)
    except json.JSONDecodeError as e:
        return [f"W1 FAIL workmap.json 非法 JSON: {e}"], []

    # W1 结构与版本
    ck("W1", d.get("schema") == "rot-workmap/v1" and bool(d.get("version")),
       "schema / version 齐备")
    ck("W1", d.get("status_labels") == list(STATUS_LABELS) and bool(d.get("status_rule")),
       "四种状态标签齐全且有状态判定规则")

    phases = d.get("phases", [])
    pids = [p.get("id") for p in phases]
    ck("W2", len(phases) == 8 and len(set(pids)) == 8 and all(pids),
       f"8 个阶段且 ID 唯一 ({len(phases)})")

    # W3 依赖存在且无环
    dep_ok = True
    for p in phases:
        for dep in p.get("depends_on", []):
            if dep not in pids:
                dep_ok = False
                fails.append(f"W3 FAIL {p['id']} 依赖未定义阶段 {dep}")
    graph = {p["id"]: p.get("depends_on", []) for p in phases}
    seen: set[str] = set()

    def has_cycle(node: str, stack: set[str]) -> bool:
        if node in stack:
            return True
        if node in seen:
            return False
        stack.add(node)
        for nxt in graph.get(node, []):
            if has_cycle(nxt, stack):
                return True
        stack.discard(node)
        seen.add(node)
        return False

    cyc = any(has_cycle(pid, set()) for pid in pids)
    ck("W3", dep_ok and not cyc, "依赖目标全部存在且依赖图无环")

    # W4 工具路径真实存在
    bad_tools = []
    for p in phases:
        tool = p.get("tool")
        if tool in (None, "manual"):
            continue
        if not (root / tool).is_file():
            bad_tools.append(f"{p['id']}->{tool}")
    ck("W4", not bad_tools, f"阶段工具路径真实存在 {bad_tools or 'OK'}")

    hgates = d.get("human_gates", {})
    bad_gates = [f"{p['id']}->{p['gate']}" for p in phases
                 if p.get("gate") and p["gate"] not in hgates]
    ck("W5", not bad_gates, f"阶段门禁均已在 human_gates 登记 {bad_gates or 'OK'}")

    # W6 验收规则：非人工必须有可复跑的检查
    rules = d.get("acceptance_rules", [])
    rids = [r.get("id") for r in rules]
    ck("W6", len(set(rids)) == len(rids) and all(rids), f"验收规则 ID 唯一 ({len(rules)})")
    bad_rules = []
    for r in rules:
        if r.get("human"):
            if r.get("check") is not None:
                bad_rules.append(f"{r['id']} 人工项却挂了 check")
        else:
            c = r.get("check") or ""
            if not c.startswith("sample_check:"):
                bad_rules.append(f"{r['id']} 非人工项无 sample_check 映射")
            elif not (root / "scripts/sample_check.py").is_file():
                bad_rules.append(f"{r['id']} 映射脚本不存在")
    ck("W6", not bad_rules, f"每条规则有检查或显式交人工 {bad_rules or 'OK'}")

    # 检查函数名在 sample_check.py 里真实定义（防映射指向空气）
    if (root / "scripts/sample_check.py").is_file():
        impl = (root / "scripts/sample_check.py").read_text(encoding="utf-8")
        missing = [r["check"].split(":", 1)[1] for r in rules
                   if not r.get("human") and r.get("check")
                   and not re.search(rf"def {re.escape(r['check'].split(':', 1)[1])}\s*\(", impl)]
        ck("W6", not missing, f"映射的检查函数真实定义 {missing or 'OK'}")

    # W7 任务引用完整性
    tasks = d.get("tasks", [])
    bad_tasks = []
    for t in tasks:
        for phase in t.get("phases", []):
            if phase not in pids:
                bad_tasks.append(f"{t['id']} 引用未定义阶段 {phase}")
        for a in t.get("acceptance", []):
            if a not in rids:
                bad_tasks.append(f"{t['id']} 引用未定义验收 {a}")
        for g in t.get("human_gates", []):
            if g not in hgates:
                bad_tasks.append(f"{t['id']} 引用未定义人工点 {g}")
        if not t.get("output") or not t.get("input"):
            bad_tasks.append(f"{t['id']} 缺输入输出定义")
    ck("W7", len(tasks) == 3 and not bad_tasks,
       f"3 个任务引用全部有定义 {bad_tasks or 'OK'}")

    # W8 每个任务至少有一条自动验收 + 一条覆盖语义/价值的人工项（全局）
    ck("W8", all(any(not next(r for r in rules if r["id"] == a)["human"]
                     for a in t.get("acceptance", [])) for t in tasks)
       and any(r.get("human") for r in rules),
       "每个任务至少一条自动验收，且存在显式人工项")

    # W9 gates 注册
    gates = d.get("gates", {})
    static = gates.get("static", [])
    ck("W9", len(static) == 18 and len(set(static)) == 18,
       f"静态门禁 18 条且无重复 ({len(static)})")
    ck("W9", bool(gates.get("structural")) and bool(gates.get("documentation"))
       and gates.get("task_samples") == ["T1", "T2", "T3"],
       "结构/文档/样例三组门禁已登记")

    # W10 人读视图与机器真值源双向一致
    md = doc.read_text(encoding="utf-8")
    miss_md = [x for x in [*pids, *rids, *[t["id"] for t in tasks]] if x not in md]
    ck("W10", not miss_md, f"json 中的阶段/规则/任务 ID 全部出现在 WORKMAP.md {miss_md or 'OK'}")
    ck("W10", all(label in md for label in STATUS_LABELS),
       "四种状态标签在人读视图中齐全")
    ck("W10", "rot.py check" in md and "feedback/RULES.md" in md,
       "统一入口与反馈规则在人读视图中有指向")

    # W11 反馈机制
    fb = d.get("feedback", {})
    ck("W11", fb.get("conversion_order", [None])[0] == "工具修复"
       and bool(fb.get("single_request")) and bool(fb.get("long_term_rule"))
       and bool(fb.get("rule_cap")) and bool(fb.get("accepted_example_status")),
       "反馈分类 / 转化优先级 / 规则上限 / 样例状态齐全")

    # W12 地图 ↔ 真实样例断言不得漂移（自动项必须逐条对齐，人工项不得混入）
    tp = root / "test-prompts.json"
    if not tp.is_file():
        fails.append("W12 FAIL test-prompts.json 不存在")
    else:
        cases = json.loads(tp.read_text(encoding="utf-8"))
        human_ids = {r["id"] for r in rules if r.get("human")}
        drift = []
        by_task = {t["id"]: t for t in tasks}
        for c in cases:
            cid = c["id"]
            key = f"test-prompts.json#{cid}"
            owner = next((tid for tid, t in by_task.items() if t.get("sample") == key), None)
            if owner is None:
                drift.append(f"#{cid} 无任务认领该样例")
                continue
            expected_auto = [a for a in by_task[owner]["acceptance"] if a not in human_ids]
            got = c.get("assertions", [])
            if got != expected_auto:
                drift.append(f"#{cid}/{owner} 期望自动断言 {expected_auto} 实为 {got}")
            if any(a in human_ids for a in got):
                drift.append(f"#{cid} 把人工项混进自动断言")
            if not c.get("human_review"):
                drift.append(f"#{cid} 缺人工复核声明")
        ck("W12", len(cases) == 3 and not drift,
           f"3 个真实样例断言与地图自动验收逐条对齐 {drift or 'OK'}")

    if verbose:
        for line in oks:
            print("  " + line)
    return fails, oks


def self_test(root: Path) -> int:
    """注入式负例：逐条破坏 workmap 副本，断言校验器 rc=1 且命中预期检查项。"""
    cases = [
        ("W3 依赖环", "cycle", lambda d: d["phases"][0].update(depends_on=["P8"]), "W3"),
        ("W4 工具路径不存在", "badtool", lambda d: d["phases"][0].update(tool="scripts/NO_SUCH.py"), "W4"),
        ("W6 规则缺检查", "nocheck", lambda d: d["acceptance_rules"][1].update(check=None), "W6"),
        ("W7 任务引用不存在阶段", "badphase", lambda d: d["tasks"][0].update(phases=["P1", "PX"]), "W7"),
        ("W10 人读视图 ID 缺失", "baddoc", None, "W10"),
        ("W11 转化优先级被改", "badfb", lambda d: d["feedback"].update(conversion_order=["文字规则"]), "W11"),
        ("W12 样例断言与地图漂移", "badcase", None, "W12"),
    ]
    print("=== workmap_check 注入式负例自测 ===")
    ok = True
    with tempfile.TemporaryDirectory(prefix="rot_wm_") as td:
        base = Path(td) / "pkg"
        # 最小副本：软链回包内真实文件，只复制需要 mutate 的三个
        base.mkdir()
        (base / ".codebuddy-plugin").mkdir()
        for rel in ["workmap.json", "WORKMAP.md", "test-prompts.json", "scripts/sample_check.py",
                    "skills/research-orchestration-workflow/scripts/state_io.py",
                    "skills/research-orchestration-workflow/scripts/topic_scoring.py",
                    "scripts/assemble_spawn_prompt.py"]:
            src, dst = root / rel, base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        for label, key, mutate, expect in cases:
            d = json.loads((base / "workmap.json").read_text(encoding="utf-8"))
            if mutate:
                mutate(d)
            (base / "workmap.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            md_orig = (root / "WORKMAP.md").read_text(encoding="utf-8")
            md_text = md_orig.replace("| **T1 科研选题**", "| 科研选题") if key == "baddoc" else md_orig
            (base / "WORKMAP.md").write_text(md_text, encoding="utf-8")
            tp_orig = (root / "test-prompts.json").read_text(encoding="utf-8")
            if key == "badcase":
                tpd = json.loads(tp_orig)
                tpd[0]["assertions"] = ["A1"]  # 人为制造漂移
                (base / "test-prompts.json").write_text(json.dumps(tpd, ensure_ascii=False, indent=2), encoding="utf-8")
            fs, _ = check(base)
            hit = any(f.startswith(expect) and "FAIL" in f for f in fs)
            print(f"[{'OK ' if hit else 'BAD'}] {label:<28} 期望命中 {expect}；实际失败项 {[f.split()[0] for f in fs][:6]}")
            ok &= hit
            # 还原
            (base / "workmap.json").write_text((root / "workmap.json").read_text(encoding="utf-8"), encoding="utf-8")
            (base / "WORKMAP.md").write_text(md_orig, encoding="utf-8")
            (base / "test-prompts.json").write_text(tp_orig, encoding="utf-8")
    print("SELFTEST: " + ("ALL GREEN" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="工作地图一致性校验器 W1–W11")
    ap.add_argument("--root", help="包根路径（默认自动向上探测）")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印全部通过项")
    ap.add_argument("--self-test", action="store_true", help="注入式负例自测")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else find_root()
    if root is None or not (root / "workmap.json").is_file():
        print("❌ 未找到包根（workmap.json + .codebuddy-plugin）", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test(root)
    fails, oks = check(root, verbose=a.verbose)
    for f in fails:
        print("  " + f)
    if fails:
        print(f"❌ 工作地图校验失败：{len(fails)} 项")
        return 1
    print(f"✅ 工作地图校验通过：{len(oks)} 项（W1–W12）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
