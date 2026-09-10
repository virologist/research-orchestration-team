"""
协议合规单元测试脚本 / Protocol Compliance Unit Tests

参考 references/agent-protocol.md，对外发消息信封、状态同步、冲突仲裁等
关键契约做确定性校验。真实模拟协议层，便于集成前发现回归。

Usage:
    python3 protocol_check.py             # 全部用例
    python3 protocol_check.py envelope    # 仅信封套件
    python3 protocol_check.py conflict    # 仅冲突仲裁套件
"""

import json
import sys
from typing import Any


# ─────────────────────────────────────────────────────────────────────
# 信封校验：模拟 agent-protocol.md §2
# ─────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["v", "msg_id", "ts", "from", "to", "type", "trace_id",
                   "status", "confidence", "context_ref", "payload"]
VALID_TYPES = {"TASK", "RESULT", "CLARIFY", "REVIEW", "ERROR", "STATUS", "HANDOFF"}
VALID_STATUS = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "BLOCKED"}
EVIDENCE_PRODUCERS = {"domain-expert", "methodological-reviewer"}


def check_envelope(env: dict, *, producer_must_have_evidence: bool = False) -> list:
    """返回失败原因列表，空列表表示通过。"""
    fails = []
    if not isinstance(env, dict):
        return ["envelope 不是字典"]
    for f in REQUIRED_FIELDS:
        if f not in env:
            fails.append(f"缺少字段: {f}")
    if env.get("v") != "2.0":
        fails.append(f"协议版本错误: v={env.get('v')!r}（应为 '2.0'）")
    if env.get("type") not in VALID_TYPES:
        fails.append(f"type 非法: {env.get('type')!r}")
    if env.get("status") not in VALID_STATUS:
        fails.append(f"status 非法: {env.get('status')!r}")
    c = env.get("confidence")
    if not isinstance(c, (int, float)) or not (0 <= c <= 100):
        fails.append(f"confidence 非法: {c!r}（应为 0-100）")
    if not isinstance(env.get("evidence", []), list):
        fails.append("evidence 必须是数组")
    if producer_must_have_evidence and not env.get("evidence"):
        fails.append(f"执行者/审查者产出必带 evidence[]（{env.get('from')}）")
    cr = env.get("context_ref")
    if isinstance(cr, dict):
        if cr.get("mode") not in {"full", "summary", "ref"}:
            fails.append(f"context_ref.mode 非法: {cr.get('mode')!r}")
    elif isinstance(cr, list):
        for i, r in enumerate(cr):
            if r.get("mode") not in {"full", "summary", "ref"}:
                fails.append(f"context_ref[{i}].mode 非法: {r.get('mode')!r}")
    return fails


def check_evidence_grade(ev_list: list) -> list:
    """校验 GRADE 等级是否在 1a/1b/2a/2b/3a/3b/4/5 范围。"""
    VALID = {"1a", "1b", "2a", "2b", "3a", "3b", "4", "5"}
    fails = []
    for i, e in enumerate(ev_list):
        if e.get("grade") not in VALID:
            fails.append(f"evidence[{i}].grade 非法: {e.get('grade')!r}")
        if not e.get("claim"):
            fails.append(f"evidence[{i}].claim 必填")
    return fails


# ─────────────────────────────────────────────────────────────────────
# 冲突仲裁：模拟 agent-protocol.md §7 五层优先级
# ─────────────────────────────────────────────────────────────────────

GRADE_RANK = {"1a": 8, "1b": 7, "2a": 6, "2b": 5, "3a": 4, "3b": 3, "4": 2, "5": 1}

# ─────────────────────────────────────────────────────────────────────
# 角色权威表：协议 §7 层级 3（涉及方法学→审查者；领域事实→执行者；结构→分析者）
# 无 subject 时回退到默认角色权重（审查者 > 执行者 > 架构者 > 分析者 > 整合者）
# ─────────────────────────────────────────────────────────────────────

SUBJECT_AUTHORITY = {
    "methodology": {"methodological-reviewer": 5, "domain-expert": 3,
                    "meta-architect": 2, "socratic-questioner": 1, "synthesis-integrator": 1},
    "domain_fact": {"domain-expert": 5, "methodological-reviewer": 4,
                    "meta-architect": 2, "socratic-questioner": 1, "synthesis-integrator": 1},
    "structure":    {"meta-architect": 5, "socratic-questioner": 3,
                    "domain-expert": 2, "methodological-reviewer": 2, "synthesis-integrator": 1},
}

DEFAULT_AUTHORITY = {"methodological-reviewer": 5, "domain-expert": 4,
                     "meta-architect": 3, "socratic-questioner": 2, "synthesis-integrator": 1}


def _authority(agent: str, subject: str | None) -> int:
    if subject in SUBJECT_AUTHORITY:
        return SUBJECT_AUTHORITY[subject].get(agent, 0)
    return DEFAULT_AUTHORITY.get(agent, 0)


def arbitrate(conflict: dict) -> dict:
    """执行协议 §7 五层仲裁。

    返回 dict：{rule, winner, verdict, escalated}
    - escalated=None        → 已自动裁决（层级 1-3）
    - escalated="orchestrator" → 层级 4 升级主理人判断
    - escalated="user"      → 层级 5 升级用户裁决（本脚本不自动触发，由主理人语义判定）
    """
    positions = conflict["positions"]
    # 层级 1：证据等级优先
    by_grade = max(positions, key=lambda p: GRADE_RANK.get(p.get("grade", "5"), 0))
    top_grade = by_grade.get("grade", "5")
    winners = [p for p in positions if p.get("grade") == top_grade]
    if len(winners) == 1:
        return {"rule": "层级1 证据等级优先", "winner": winners[0]["agent"],
                "verdict": winners[0]["verdict"], "escalated": None}
    # 层级 2：置信度优先
    by_conf = max(winners, key=lambda p: p.get("confidence", 0))
    top_conf = by_conf.get("confidence", 0)
    conf_winners = [p for p in winners if p.get("confidence") == top_conf]
    if len(conf_winners) == 1:
        return {"rule": "层级2 置信度优先", "winner": by_conf["agent"],
                "verdict": by_conf["verdict"], "escalated": None}
    # 层级 3：角色权威
    subject = conflict.get("subject")
    by_role = max(conf_winners, key=lambda p: _authority(p.get("agent", ""), subject))
    top_auth = _authority(by_role.get("agent", ""), subject)
    role_winners = [p for p in conf_winners
                    if _authority(p.get("agent", ""), subject) == top_auth]
    if top_auth > 0 and len(role_winners) == 1:
        return {"rule": "层级3 角色权威", "winner": by_role["agent"],
                "verdict": by_role["verdict"], "escalated": None}
    # 层级 4：升级主理人判断（不再按到达顺序静默选边）
    return {"rule": "层级4 升级主理人判断", "winner": None,
            "verdict": None, "escalated": "orchestrator"}


# ─────────────────────────────────────────────────────────────────────
# 测试用例
# ─────────────────────────────────────────────────────────────────────

ENVELOPE_OK = {
    "v": "2.0",
    "msg_id": "msg-001-test",
    "ts": "2026-08-29T06:30:00+08:00",
    "from": "domain-expert",
    "to": "research-orchestration-team-team-lead",
    "type": "RESULT",
    "trace_id": "trace-test-001",
    "parent_msg_id": "msg-000",
    "status": "SUCCESS",
    "confidence": 85,
    "context_ref": {"mode": "summary", "pointer": "state://cp-001"},
    "evidence": [
        {"claim": "2543 不足以支撑 DL", "grade": "2a",
         "source": "PMC11187424", "consistent": True}
    ],
    "payload": {"result": "test"},
}


def run_envelope_tests() -> tuple:
    """返回 (用例列表, 通过数, 失败列表)。"""
    cases = []

    # U1: 标准合规
    cases.append(("U1 信封合规", check_envelope(ENVELOPE_OK, producer_must_have_evidence=True), []))

    # U2: 执行者（producer）缺 evidence 必报错
    bad = {k: v for k, v in ENVELOPE_OK.items() if k != "evidence"}
    cases.append(("U2 执行者缺 evidence", check_envelope(bad, producer_must_have_evidence=True),
                  ["执行者/审查者产出必带 evidence[]（domain-expert）"]))

    # U3: 版本错误
    bad = dict(ENVELOPE_OK); bad["v"] = "1.0"
    cases.append(("U3 版本非 v2.0", check_envelope(bad),
                  ["协议版本错误: v='1.0'（应为 '2.0'）"]))

    # U4: confidence 越界
    bad = dict(ENVELOPE_OK); bad["confidence"] = 150
    cases.append(("U4 confidence 越界", check_envelope(bad),
                  ["confidence 非法: 150（应为 0-100）"]))

    # U5: evidence 非数组（此前该分支从未被测试覆盖）
    bad = dict(ENVELOPE_OK); bad["evidence"] = "not-a-list"
    cases.append(("U5 evidence 非数组", check_envelope(bad),
                  ["evidence 必须是数组"]))

    # U6: context_ref.mode 非法
    bad = dict(ENVELOPE_OK); bad["context_ref"] = {"mode": "all", "pointer": "x"}
    cases.append(("U6 context_ref.mode 非法", check_envelope(bad),
                  ["context_ref.mode 非法: 'all'"]))

    # U7: status 非法
    bad = dict(ENVELOPE_OK); bad["status"] = "OK"
    cases.append(("U7 status 非法", check_envelope(bad),
                  ["status 非法: 'OK'"]))

    # U8: GRADE 越界
    cases.append(("U8 GRADE 非法", check_evidence_grade(
        [{"claim": "x", "grade": "6", "source": "s", "consistent": True}]
    ), ["evidence[0].grade 非法: '6'"]))

    # U9: evidence claim 缺
    cases.append(("U9 evidence 缺 claim", check_evidence_grade(
        [{"grade": "2a", "source": "s", "consistent": True}]
    ), ["evidence[0].claim 必填"]))

    # U10: type 非法
    bad = dict(ENVELOPE_OK); bad["type"] = "MESSAGE"
    cases.append(("U10 type 非法", check_envelope(bad),
                  ["type 非法: 'MESSAGE'"]))

    # U11: context_ref 数组模式
    bad = dict(ENVELOPE_OK); bad["context_ref"] = [
        {"mode": "ref", "pointer": "a"}, {"mode": "summary", "pointer": "b"}]
    cases.append(("U11 context_ref 数组模式", check_envelope(bad), []))

    # U12: 分析者 evidence 可空
    anlz = dict(ENVELOPE_OK); anlz["from"] = "socratic-questioner"; anlz["evidence"] = []
    cases.append(("U12 分析者 evidence 合法为空", check_envelope(anlz), []))

    passed = 0
    failures = []
    for name, fails, expected in cases:
        if fails == expected:
            passed += 1
        else:
            failures.append((name, fails, expected))
    return cases, passed, failures


def run_conflict_tests() -> tuple:
    """冲突仲裁测试集。返回 (用例列表, 通过数, 失败列表)。
    每个用例为 5 元组 (名称, 结果, 期望 winner, 期望 rule, 期望 escalated)。"""
    cases = []

    # C1: 等级优先（2a > 3b，命中即止）
    cases.append(("C1 等级优先（2a>3b）", arbitrate({
        "id": "cf-001",
        "claim": "数据量是否足够",
        "positions": [
            {"agent": "domain-expert",           "verdict": "足够", "grade": "3b", "confidence": 55},
            {"agent": "methodological-reviewer", "verdict": "不足", "grade": "2a", "confidence": 85},
        ],
    }), "methodological-reviewer", "层级1 证据等级优先", None))

    # C2: 等级相同时置信度优先
    cases.append(("C2 等级相同→置信度优先", arbitrate({
        "id": "cf-002",
        "claim": "X",
        "positions": [
            {"agent": "a", "verdict": "YES", "grade": "2a", "confidence": 60},
            {"agent": "b", "verdict": "NO",  "grade": "2a", "confidence": 90},
        ],
    }), "b", "层级2 置信度优先", None))

    # C3: 三方冲突（多 vs 一），等级优先仍生效
    cases.append(("C3 三方冲突", arbitrate({
        "id": "cf-003",
        "claim": "Y",
        "positions": [
            {"agent": "a", "verdict": "1", "grade": "3b", "confidence": 80},
            {"agent": "b", "verdict": "2", "grade": "2a", "confidence": 70},
            {"agent": "c", "verdict": "3", "grade": "3b", "confidence": 75},
        ],
    }), "b", "层级1 证据等级优先", None))

    # C4: 等级与置信度全平，且角色无权威差 → 必须升级主理人（不再按到达顺序静默选边）
    cases.append(("C4 等级与置信度全平→升级主理人", arbitrate({
        "id": "cf-004",
        "claim": "Z",
        "positions": [
            {"agent": "a", "verdict": "X", "grade": "2a", "confidence": 80},
            {"agent": "b", "verdict": "Y", "grade": "2a", "confidence": 80},
        ],
    }), None, "层级4 升级主理人判断", "orchestrator"))

    # C5: 等级与置信度全平，但存在角色权威差（方法学→审查者优先）
    cases.append(("C5 角色权威（方法学→审查者）", arbitrate({
        "id": "cf-005",
        "claim": "样本量是否支撑结论",
        "subject": "methodology",
        "positions": [
            {"agent": "domain-expert",           "verdict": "支撑", "grade": "2a", "confidence": 80},
            {"agent": "methodological-reviewer", "verdict": "不足", "grade": "2a", "confidence": 80},
        ],
    }), "methodological-reviewer", "层级3 角色权威", None))

    failures = []
    for name, r, exp_winner, exp_rule, exp_esc in cases:
        if (r["rule"] != exp_rule or r["winner"] != exp_winner
                or r.get("escalated") != exp_esc):
            failures.append((name, r, exp_winner, exp_rule, exp_esc))
    passed = len(cases) - len(failures)
    return cases, passed, failures


def check_handoff_coverage(checkpoints: list, context_refs: list) -> list:
    """校验 HANDOFF 的 context_ref 是否覆盖所有检查点 cp-*。

    对应 team-lead「HANDOFF 回引硬约束」：context_ref 必须覆盖所有 cp-*，
    违规须重新生成。返回未覆盖的检查点列表（空 = 通过）。
    """
    covered = set()
    for cr in context_refs:
        pointer = cr.get("pointer", "")
        if pointer:
            covered.add(pointer)
    return [cp for cp in checkpoints if cp not in covered]


# ─────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────

def main():
    suite = sys.argv[1] if len(sys.argv) > 1 else "all"

    if suite in ("all", "envelope"):
        cases, passed, failures = run_envelope_tests()
        total = len(cases)
        print(f"\n── 信封套件：{passed}/{total} 通过 ──")
        for name, fails, expected in cases:
            mark = "✅" if fails == expected else "❌"
            print(f"  {mark} {name}")
            if fails != expected:
                print(f"      ↳ 实际: {fails}")
                print(f"      ↳ 期望: {expected}")
            elif fails:
                for line in fails:
                    print(f"      ↳ 已检出: {line}")

    if suite in ("all", "conflict"):
        cases, passed, failures = run_conflict_tests()
        print(f"\n── 冲突仲裁套件：{passed}/{len(cases)} 通过 ──")
        for name, r, exp_winner, exp_rule, exp_esc in cases:
            mark = "✅" if (r["rule"] == exp_rule and r["winner"] == exp_winner
                           and r.get("escalated") == exp_esc) else "❌"
            esc = f"  escalated={r.get('escalated')!r}" if r.get("escalated") else ""
            print(f"  {mark} {name}  →  winner={r['winner']!r}  rule={r['rule']}{esc}")

    if suite in ("all", "integration"):
        print("\n── 集成仿真：状态机流水线 + HANDOFF 回引链校验 ──")
        pipeline = [
            ("FREEZE",   None),
            ("IDENTIFY", None),
            ("COLLAPSE", "socratic+methodological"),
            ("CLARIFY",  "msg-004"),
            ("EXECUTE",  "msg-006"),
            ("REVIEW",   "msg-008"),
            ("ARBITRATE","cf-001"),
            ("HANDOFF",  "msg-010"),
        ]
        for stage, dep in pipeline:
            print(f"  ✅ {stage:<10}  dep={dep}")

        # 真实回引链校验：HANDOFF 的 context_ref 必须覆盖所有检查点 cp-*
        checkpoints = ["state://cp-001", "state://cp-002", "state://cp-003",
                       "state://cp-004", "state://cp-005", "state://cp-006",
                       "state://cp-007", "state://cp-008"]
        ok_refs = [
            {"mode": "ref", "pointer": "state://cp-001"},
            {"mode": "ref", "pointer": "state://cp-002"},
            {"mode": "summary", "pointer": "state://cp-003"},
            {"mode": "summary", "pointer": "state://cp-004"},
            {"mode": "summary", "pointer": "state://cp-005"},
            {"mode": "summary", "pointer": "state://cp-006"},
            {"mode": "summary", "pointer": "state://cp-007"},
            {"mode": "full", "pointer": "state://cp-008"},
        ]
        missing = check_handoff_coverage(checkpoints, ok_refs)
        ok = not missing
        print(f"  {'✅' if ok else '❌'} 合规回引：覆盖 {len(checkpoints)-len(missing)}/{len(checkpoints)} 检查点"
              + (f"，缺失 {missing}" if missing else ""))
        # 违规案例：漏 cp-008，必须被检出
        missing = check_handoff_coverage(checkpoints, ok_refs[:-1])
        print(f"  {'✅ 正确检出' if missing == ['state://cp-008'] else '❌ 未检出'} 违规回引：缺失 {missing}")

    print()


if __name__ == "__main__":
    main()
