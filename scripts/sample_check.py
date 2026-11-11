#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sample_check.py — 真实任务样例的结构化断言执行器

把 test-prompts.json 里原本只有文字的 expected，转成可复跑的机器检查：
  - 每条断言返回 (PASS/FAIL, 证据片段)，证据必须能指回产出文件
  - 产出文件按 sha256 记录，内容变化后重跑即可比对（不缓存旧结论）
  - --self-test 用正例/反例证明每条断言真的会红（延续本项目注入式负例纪律）

语义质量、文献真实性、价值取舍**不在本脚本判定范围**，须人工复核（workmap A10/A11）。

退出码：0 全部通过 / 1 有断言失败 / 2 文件或产出缺失 / 3 参数缺失。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MARKERS = ("workmap.json", ".codebuddy-plugin")
DECISIONS = ("维持", "升档", "降档", "止损")
LIST_ITEM = re.compile(r"(?m)^\s*(?:[-*]|\d+[.、)]|[①②③④⑤⑥])\s+\S")


def find_root(start: Path | None = None) -> Path | None:
    p = (start or Path(__file__).resolve()).absolute()
    for cand in [p, *p.parents]:
        if all((cand / m).exists() for m in MARKERS):
            return cand
    return None


def _ev(text: str, pattern: str, limit: int = 120) -> str:
    m = re.search(pattern, text, re.M | re.S)
    return (m.group(0)[:limit].replace("\n", " ") if m else "（无命中）")


# ── 断言实现：签名统一 (text, case, root) -> (bool, 证据) ──────────────────

def nonempty_language(text: str, case: dict, root: Path) -> tuple[bool, str]:
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    ok = bool(text.strip()) and zh >= 40
    return ok, f"长度={len(text)} 中文字符={zh}（要求非空且中文 >= 40）"


def grade_bucket(text: str, case: dict, root: Path) -> tuple[bool, str]:
    hit = re.search(r"[SABC]\s*档|分档[:：]\s*[SABC]", text)
    forbidden = re.search(r"暂未定档|未定档|待定档", text)
    return bool(hit) and not forbidden, f"分档命中={_ev(text, r'[SABC]\s*档|分档[:：]\s*[SABC]')} 禁词={'命中' if forbidden else '无'}"


def stop_loss(text: str, case: dict, root: Path) -> tuple[bool, str]:
    if "止损线" not in text:
        return False, "未出现「止损线」"
    pos = text.index("止损线")
    seg = text[pos:pos + 700]
    items = LIST_ITEM.findall(seg)
    return len(items) >= 3, f"止损线后列表项={len(items)}（要求 >= 3）｜首项={_ev(seg, r'(?m)^\s*(?:[-*]|\d+[.、)]|[①②③])\s+\S.{0,60}')}"


def grade_label(text: str, case: dict, root: Path) -> tuple[bool, str]:
    hit = re.search(r"GRADE|证据等级|3[ab]|2[ab]|1[ab]", text, re.I)
    return bool(hit), f"证据等级命中={_ev(text, r'GRADE|证据等级|3[ab]|2[ab]|1[ab]')}"


def review_decision(text: str, case: dict, root: Path) -> tuple[bool, str]:
    hit = [d for d in DECISIONS if d in text]
    bad = re.search(r"(?:结论|决策|判定|结果为)\s*[:：]?\s*(?:待定|观察|暂缓)|(?:^|\n)\s*(?:待定|观察)\s*$", text)
    return bool(hit) and not bad, f"决策词={hit or '无'} 结案禁词={'命中' if bad else '无'}"


def scoring_edge(text: str, case: dict, root: Path) -> tuple[bool, str]:
    """工具行为断言：评分越界必须 rc=1 且报错，不静默钳制。"""
    s = root / "skills/research-orchestration-workflow/scripts/topic_scoring.py"
    if not s.is_file():
        return False, f"脚本不存在 {s}"
    p = subprocess.run([sys.executable, str(s), "--topic", "边界探针",
                        "--originality", "11", "--feasibility", "7", "--value-density", "9",
                        "--data-availability", "7", "--competition", "6", "--cognition", "8",
                        "--resource-fit", "7", "--sustainability", "7"],
                       capture_output=True, text=True, timeout=30, cwd=root)
    err = (p.stdout + p.stderr).strip().replace("\n", " ")[:160]
    ok = p.returncode == 1 and ("超出有效范围" in err or "评分失败" in err)
    return ok, f"rc={p.returncode} 输出={err}"


def clarify_round(text: str, case: dict, root: Path) -> tuple[bool, str]:
    r1 = re.search(r"Round\s*1|第一轮|第\s*1\s*轮", text, re.I)
    q = len(re.findall(r"[？?]", text))
    return bool(r1) and q >= 5, f"Round1={'有' if r1 else '无'} 问号数={q}（要求 >= 5）"


def no_premature_plan(text: str, case: dict, root: Path) -> tuple[bool, str]:
    bad = re.search(r"选题评分卡|分档建议|S\s*档|A\s*档|B\s*档|C\s*档", text)
    return not bad, f"提前给方案的痕迹={'命中 ' + _ev(text, r'选题评分卡|分档建议|[SABC]\s*档') if bad else '无'}"


def next_action(text: str, case: dict, root: Path) -> tuple[bool, str]:
    hit = re.search(r"推翻条件|下一步|后续动作|前置动作|建议动作", text)
    return bool(hit), f"后续动作命中={_ev(text, r'推翻条件|下一步|后续动作|前置动作|建议动作')}"


CHECKS = {
    "nonempty_language": nonempty_language,
    "grade_bucket": grade_bucket,
    "stop_loss": stop_loss,
    "grade_label": grade_label,
    "review_decision": review_decision,
    "scoring_edge": scoring_edge,
    "clarify_round": clarify_round,
    "no_premature_plan": no_premature_plan,
    "next_action": next_action,
}

RULE_TO_CHECK = {
    "A1": "nonempty_language", "A2": "grade_bucket", "A3": "stop_loss",
    "A4": "grade_label", "A5": "review_decision", "A6": "scoring_edge",
    "A7": "clarify_round", "A8": "no_premature_plan", "A9": "next_action",
}


def load_cases(root: Path) -> list[dict]:
    p = root / "test-prompts.json"
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_output(run_dir: Path, case: dict) -> Path | None:
    cid = case["id"]
    for name in (f"TP-{cid}.md", f"{cid}.md", f"case{cid}.md", f"TP-{cid}.txt"):
        p = run_dir / name
        if p.is_file():
            return p
    return None


def run(root: Path, run_dir: Path, json_out: Path | None = None) -> int:
    cases = load_cases(root)
    report = {"schema": "rot-sample-report/v1", "run_dir": str(run_dir), "cases": [], "summary": {}}
    ok_all = True
    print("=== 真实任务样例结构化断言 ===")
    for c in cases:
        rules = c.get("assertions")
        if not rules:
            print(f"[BAD] case #{c['id']} 缺 assertions 字段（fail-closed）")
            ok_all = False
            continue
        out = resolve_output(run_dir, c)
        entry = {"case_id": c["id"], "name": c["name"], "output_file": str(out) if out else None,
                 "sha256": None, "checks": [], "status": "尚未验证"}
        if out is None:
            entry["checks"].append({"rule": "-", "result": "MISSING", "evidence": "产出文件缺失"})
            entry["status"] = "尚未验证"
            print(f"[BAD] #{c['id']} {c['name']:<28} 产出文件缺失（查过 TP-{c['id']}.md / {c['id']}.md）")
            ok_all = False
            report["cases"].append(entry)
            continue
        text = out.read_text(encoding="utf-8", errors="replace")
        entry["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        for r in rules:
            fn = CHECKS.get(RULE_TO_CHECK.get(r, ""))
            if fn is None:
                entry["checks"].append({"rule": r, "result": "FAIL", "evidence": f"无对应检查函数 {r}"})
                ok_all = False
                continue
            good, ev = fn(text, c, root)
            entry["checks"].append({"rule": r, "check": fn.__name__,
                                    "result": "PASS" if good else "FAIL", "evidence": ev})
            ok_all &= good
            print(f"[{'OK ' if good else 'BAD'}] #{c['id']} {r:<3} {fn.__name__:<20} {ev[:110]}")
        entry["status"] = "自动验证通过" if all(x["result"] == "PASS" for x in entry["checks"]) else "自动验证未通过"
        entry["human_review"] = "A10/A11 语义与价值判断仍待人工确认"
        report["cases"].append(entry)

    report["summary"] = {
        "cases": len(cases),
        "passed": sum(1 for e in report["cases"] if e["status"] == "自动验证通过"),
        "all_green": ok_all,
        "note": "结构化断言通过 ≠ 语义质量通过；A10/A11 必须人工确认，不得标为自动验证通过",
    }
    print(f"\n汇总：{report['summary']['passed']}/{report['summary']['cases']} 用例结构化断言通过；"
          f"{'ALL GREEN' if ok_all else 'FAILED'}")
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"结构化报告已落盘：{json_out}")
    return 0 if ok_all else 1


def self_test(root: Path) -> int:
    """为每条断言构造一对正例/反例，证明断言真的会红（不是永远 True）。"""
    positives = {
        "nonempty_language": "这是一份完整的中文产出，包含足够长度的说明文字，用于验证非空与语言一致性检查确实生效。" * 2,
        "grade_bucket": "综合判断：本选题为 A 档，建议标准投入。",
        "stop_loss": "止损线如下：\n1. 数据截止 2021 年，需补近三年序列\n2. 时间窗口 6 个月\n3. 资源预算不超过 2 人月",
        "grade_label": "证据等级 GRADE 3b，结论可信度中等。",
        "review_decision": "复评结论：降档。推翻条件：补齐样本量后重评。下一步：先做功效分析。",
        "clarify_round": "Round 1 宏观追问：\n1. 研究对象是什么？\n2. 数据从哪来？\n3. 目标期刊是？\n4. 时间预算？\n5. 可投入资源？",
        "no_premature_plan": "当前信息不足，需要先澄清研究方向与数据基础，暂不给出结论。",
        "next_action": "推翻条件：若样本量补足则维持；下一步：先做统计功效分析。",
    }
    negatives = {
        "nonempty_language": "ok",
        "grade_bucket": "结论：暂未定档，需要更多信息。",
        "stop_loss": "本选题暂无明确止损安排，后续再议。",
        "grade_label": "结论可信，直接推进即可。",
        "review_decision": "结论：待定，建议继续观察。",
        "clarify_round": "已给出方案，无需追问。",
        "no_premature_plan": "选题评分卡已生成，分档建议为 B 档。",
        "next_action": "结论如上，无其他说明。",
    }
    print("=== sample_check 断言有效性自测（正例须 PASS / 反例须 FAIL）===")
    ok = True
    for name, fn in CHECKS.items():
        if name == "scoring_edge":
            good, ev = scoring_edge("", {}, root)
            print(f"[{'OK ' if good else 'BAD'}] scoring_edge          工具行为 rc=1 断言：{ev[:100]}")
            ok &= good
            continue
        p = fn(positives[name], {}, root)[0]
        n = fn(negatives[name], {}, root)[0]
        good = p and not n
        print(f"[{'OK ' if good else 'BAD'}] {name:<20} 正例={'PASS' if p else 'FAIL'} 反例={'FAIL' if not n else 'PASS(误绿)'}")
        ok &= good
    print("SELFTEST: " + ("ALL GREEN" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="真实任务样例结构化断言执行器")
    ap.add_argument("--root", help="包根（默认自动探测）")
    ap.add_argument("--run-dir", help="真实任务产出目录（内含 TP-<id>.md）")
    ap.add_argument("--json", dest="json_out", help="结构化报告输出路径")
    ap.add_argument("--self-test", action="store_true", help="断言有效性自测")
    ap.add_argument("--list", action="store_true", help="列出规则→检查函数映射")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else find_root()
    if root is None:
        print("❌ 未找到包根", file=sys.stderr)
        return 2
    if a.list:
        for k, v in RULE_TO_CHECK.items():
            print(f"  {k} -> {v}")
        return 0
    if a.self_test:
        return self_test(root)
    if not a.run_dir:
        print("❌ 缺 --run-dir（或用 --self-test / --list）", file=sys.stderr)
        return 3
    rd = Path(a.run_dir).resolve()
    if not rd.is_dir():
        print(f"❌ 产出目录不存在：{rd}", file=sys.stderr)
        return 2
    return run(root, rd, Path(a.json_out).resolve() if a.json_out else None)


if __name__ == "__main__":
    sys.exit(main())
