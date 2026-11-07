#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harness Engineering 评估器（注入式正向校验）

评估对象基于 2026-09 检索到的专家级规范：
  - Anthropic Harness Engineering (Boeckeler / HumanLayer / Schmid)
  - LangChain / Vercel / Manus 实测数据（Terminal Bench 52.8% → 66.5%）
  - Claude Code Workflows (v2.1.154+) + Ralph Loop（Anthropic 双相模式）
  - Orchestrator Pattern（两步 LLM 调用，比 agentic loop 省 70%）
  - METR 研究："先建 eval 再动 Harness"是 2026 分水岭

## 为什么需要这个脚本

manifest_check.py 检查的是**发行卫生**（双 manifest 对等 / 资产完整性 / 版本一致）。
但 manifest 全绿不等于 harness 健康 —— 一个 prompt 内部如果缺 loop 硬停止 / 缺
per-step verification / 缺阶段边界 compact / 缺 atomic subagent 拆分，照样能上架，
照样能"看起来工作"，但遇到长任务 / 多 agent / 跨会话就会失败。

本脚本把 harness 的 12 项设计模式变成**正向校验**：每条都是一条具体可观测的代码
事实（如「文件存在」「文本包含关键字」「schema 字段齐全」），不依赖主观评分。

## 校验项 H1-H12

  H1  路由机制升级 — agent-registry.md 单一事实源（含 agent_id / trigger / tools）
  H2  Loop 硬停止 — team-lead prompt 含 max_turns / max_time / max_token 三层
  H3  Per-step verification — protocol 提及 per-step verify（非仅 final-output）
  H4  阶段边界 compact — SKILL.md 含 compact 指令（防止上下文累积）
  H5  Atomic subagent — 博域闻拆为 domain-expert-biomed / ai / general 三文件
  H6  权限分层 — registry 含 safe / moderate / dangerous 三档
  H7  Eval & Observability — team-lead 含 metrics / observability 字段
  H8  Token budget — team-lead 含 token budget 跟踪（context as scarce resource）
  H9  LEARNING.md — 跨会话连续性（Anthropic Ralph Loop 模式）
  H10 Circuit breaker — team-lead 含失败熔断机制（5 次失败 → 升级用户）
  H11 plan_execution — team-lead 含 plan_execution 元工具（信号触发串行模式）
  H12 agent-registry 单一事实源 — refs/agent-registry.md 存在且结构化

## 与 manifest_check 的区别

  manifest_check.py  →  发行卫生（文件 / 版本 / 术语 / 资产）
  harness_eval.py    →  Harness Engineering（路由 / loop / 上下文 / observability）

两者互不替代。前者保证「能装」；后者保证「能用好」。

## 用法

  python3 scripts/harness_eval.py               # 自动定位仓库根
  python3 scripts/harness_eval.py --root <dir>  # 显式指定仓库根
  python3 scripts/harness_eval.py -v            # 输出每个通过项

## 退出码

  0 = 全部通过（v2.1.0+ 期望）
  1 = 存在校验失败项（v2.0.2 基线期望）
  2 = 用法 / 环境错误（如仓库根不含 manifest）

## 依赖

仅标准库，Python >= 3.9。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# ── 路径常量（相对仓库根；禁止散落在函数内的字面量）────────────────────────
AGENTS_DIR = "agents"
REFS_DIR = "skills/research-orchestration-workflow/references"
SKILL_DIR = "skills/research-orchestration-workflow"
TEAM_LEAD = "research-orchestration-team-team-lead.md"
REGISTRY = "agent-registry.md"
PROTOCOL = "agent-protocol.md"
SKILL_MD = "SKILL.md"
LEARNING = "LEARNING.md"


# ── 校验项定义（H1-H12）──────────────────────────────────────────────
# 每个 check 返回 (passed: bool, message: str)
# message 在失败时说明缺什么；通过时为空字符串（-v 时输出"✅ Hx"）

def check_h1_routing_registry(root: Path) -> tuple[bool, str]:
    """H1: 路由机制升级 — agent-registry.md 单一事实源"""
    registry = root / REFS_DIR / REGISTRY
    if not registry.exists():
        return False, f"{REGISTRY}=文件不存在（路由仍是静态决策树，无单一事实源）"
    content = registry.read_text()
    # 必须含三个关键字段：agent_id / trigger / tools
    required_fields = ["agent_id", "trigger", "tools"]
    missing = [f for f in required_fields if f not in content]
    if missing:
        return False, f"{REGISTRY} 缺关键字段: {missing}"
    return True, ""


def check_h2_loop_terminator(root: Path) -> tuple[bool, str]:
    """H2: Loop 硬停止 — max_turns / max_time / max_token 三层"""
    team_lead = root / AGENTS_DIR / TEAM_LEAD
    if not team_lead.exists():
        return False, f"{TEAM_LEAD}=team-lead 不存在"
    content = team_lead.read_text()
    required = ["max_turns", "max_time", "max_token"]
    missing = [r for r in required if r not in content]
    if missing:
        return False, f"loop 硬停止缺: {missing}"
    return True, ""


def check_h3_per_step_verification(root: Path) -> tuple[bool, str]:
    """H3: Per-step verification — protocol 提及 per-step verify（非仅 final-output）"""
    protocol = root / REFS_DIR / PROTOCOL
    if not protocol.exists():
        return False, f"{PROTOCOL}=agent-protocol.md 不存在"
    content = protocol.read_text()
    # 必须含 per-step（连字符或下划线）或中文"逐 step"
    keywords = ["per-step", "per_step", "per step", "逐 step", "perstep"]
    if not any(k in content.lower() for k in keywords):
        return False, "protocol 未提及 per-step verification（仅 final-output 校验不够）"
    return True, ""


def check_h4_stage_boundary_compact(root: Path) -> tuple[bool, str]:
    """H4: 上下文治理 — 阶段边界 compact 指令"""
    skill_md = root / SKILL_DIR / SKILL_MD
    if not skill_md.exists():
        return False, f"{SKILL_MD}=SKILL.md 不存在"
    content = skill_md.read_text()
    # 必须含 compact（阶段边界触发而非 token 阈值）
    if "compact" not in content.lower():
        return False, "SKILL.md 未提及阶段边界 compact（context as scarce resource 缺位）"
    return True, ""


def check_h5_atomic_subagent(root: Path) -> tuple[bool, str]:
    """H5: 博域闻拆分 — atomic subagent（biomed / ai / general）"""
    agents_dir = root / AGENTS_DIR
    expected = ["domain-expert-biomed.md", "domain-expert-ai.md", "domain-expert-general.md"]
    existing = [p.name for p in agents_dir.glob("domain-expert*.md")]
    missing = [e for e in expected if e not in existing]
    if missing:
        return False, f"atomic subagent 拆分缺: {missing}（现仅 {existing}）"
    return True, ""


def check_h6_permission_layer(root: Path) -> tuple[bool, str]:
    """H6: 权限分层 — registry 须有 safe/moderate/dangerous 三个 ### 章节，且正文非空。

    v2.2.0 部署门禁修复：旧实现用 `r not in content` 全文子串匹配，删掉整个
    `### moderate` 章节后，第 76 行「safe / moderate / dangerous 三档」与
    Changelog 的兜底词仍让 H6 误判 PASS。现改为按章节标题判定，杜绝兜底词放行。
    """
    registry = root / REFS_DIR / REGISTRY
    if not registry.exists():
        return False, "无 registry，无法验证权限分层"
    reg_text = registry.read_text(encoding="utf-8")

    # 只认 ### 章节标题，不认散落在引言 / Changelog 里的档位词
    headings = {
        m.group(1): m
        for m in re.finditer(r"^###\s+(safe|moderate|dangerous)\b", reg_text, re.M)
    }

    for tier in ("safe", "moderate", "dangerous"):
        m = headings.get(tier)
        if m is None:
            return False, f"权限分级缺标题: {tier}（registry 未定义 ### {tier} 章节）"

        # 正文 = 标题行结束之后，到下一个 ### / ## 标题之前的区间
        # （从标题行的行尾起算，排除标题行本身残留的括号说明，避免空正文被误判为有内容）
        line_end = reg_text.find("\n", m.start())
        body_start = line_end + 1 if line_end != -1 else len(reg_text)
        next_heading = re.search(r"^#{2,3}\s", reg_text[body_start:], re.M)
        body_end = body_start + next_heading.start() if next_heading else len(reg_text)
        if not reg_text[body_start:body_end].strip():
            return False, f"权限分级正文为空: {tier}（### {tier} 章节缺实质内容）"
    return True, ""


def check_h7_observability(root: Path) -> tuple[bool, str]:
    """H7: Eval & Observability — metrics / observability 字段"""
    team_lead = root / AGENTS_DIR / TEAM_LEAD
    if not team_lead.exists():
        return False, f"{TEAM_LEAD}=team-lead 不存在"
    content = team_lead.read_text().lower()
    if not any(k in content for k in ["metric", "observability", "telemetry", "metrics"]):
        return False, "team-lead 缺 metrics / observability 字段（无法衡量 harness 健康）"
    return True, ""


def check_h8_token_budget(root: Path) -> tuple[bool, str]:
    """H8: Token budget — context as scarce resource"""
    team_lead = root / AGENTS_DIR / TEAM_LEAD
    if not team_lead.exists():
        return False, f"{TEAM_LEAD}=team-lead 不存在"
    content = team_lead.read_text().lower()
    # token + budget 必须同时存在
    if not ("token" in content and "budget" in content):
        return False, "team-lead 缺 token budget 跟踪（context as scarce resource 缺位）"
    return True, ""


def check_h9_learning_md(root: Path) -> tuple[bool, str]:
    """H9: LEARNING.md — 跨会话连续性（Anthropic Ralph Loop）"""
    learning = root / REFS_DIR / LEARNING
    if not learning.exists():
        return False, f"{LEARNING}=文件不存在（无跨会话记忆载体）"
    return True, ""


def check_h10_circuit_breaker(root: Path) -> tuple[bool, str]:
    """H10: Circuit breaker — 失败熔断"""
    team_lead = root / AGENTS_DIR / TEAM_LEAD
    if not team_lead.exists():
        return False, f"{TEAM_LEAD}=team-lead 不存在"
    content = team_lead.read_text().lower()
    # 英文或中文皆可
    if not any(k in content for k in ["circuit", "熔断", "circuit breaker"]):
        return False, "team-lead 缺 circuit breaker（失败无熔断机制）"
    return True, ""


def check_h11_plan_execution(root: Path) -> tuple[bool, str]:
    """H11: plan_execution 元工具 — 信号触发串行模式"""
    team_lead = root / AGENTS_DIR / TEAM_LEAD
    if not team_lead.exists():
        return False, f"{TEAM_LEAD}=team-lead 不存在"
    content = team_lead.read_text()
    if "plan_execution" not in content:
        return False, "team-lead 缺 plan_execution 元工具（Orchestrator Pattern 信号）"
    return True, ""


def check_h12_agent_registry(root: Path) -> tuple[bool, str]:
    """H12: agent-registry.md 存在（与 H1 略有重叠，但更基础）"""
    registry = root / REFS_DIR / REGISTRY
    if not registry.exists():
        return False, f"{REGISTRY}=文件不存在"
    return True, ""


# ── 主流程 ─────────────────────────────────────────────────────────
CHECKS = [
    ("H1",  "路由机制升级 (Registry + trigger + tools)",     check_h1_routing_registry),
    ("H2",  "Loop 硬停止 (max_turns + max_time + max_token)", check_h2_loop_terminator),
    ("H3",  "Per-step verification (protocol)",                check_h3_per_step_verification),
    ("H4",  "阶段边界 compact (SKILL.md)",                     check_h4_stage_boundary_compact),
    ("H5",  "Atomic subagent 拆分 (biomed/ai/general)",         check_h5_atomic_subagent),
    ("H6",  "权限分层 (safe/moderate/dangerous)",              check_h6_permission_layer),
    ("H7",  "Eval & Observability (metrics/observability)",     check_h7_observability),
    ("H8",  "Token budget 跟踪 (context as scarce)",            check_h8_token_budget),
    ("H9",  "LEARNING.md (Ralph Loop 跨会话)",                   check_h9_learning_md),
    ("H10", "Circuit breaker (失败熔断)",                       check_h10_circuit_breaker),
    ("H11", "plan_execution 元工具 (Orchestrator 信号)",        check_h11_plan_execution),
    ("H12", "agent-registry.md 单一事实源",                     check_h12_agent_registry),
]


def find_repo_root(start: Path) -> Path | None:
    """定位仓库根（须同时含 .claude-plugin 与 .codebuddy-plugin）。

    v2.2.0 修复：起点从 Path.cwd() 改为本脚本所在位置上溯——
    cwd 依赖导致从任意外部目录调用时 exit 2（实测缺陷），与
    manifest_check.py 的 `Path(__file__)` 定位保持一致。
    """
    cur = Path(__file__).resolve().parent
    for _ in range(8):
        if (cur / ".claude-plugin").exists() and (cur / ".codebuddy-plugin").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness Engineering 评估器（H1-H12）")
    parser.add_argument("--root", type=Path, default=None,
                        help="仓库根（默认自动定位）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="输出每个通过项")
    args = parser.parse_args(argv)

    root = args.root.resolve() if args.root else find_repo_root(Path(__file__))
    if root is None:
        print("❌ 找不到仓库根（须同时含 .claude-plugin 与 .codebuddy-plugin）", file=sys.stderr)
        return 2

    print(f"🔍 Harness eval — 仓库根: {root}\n")

    passed = 0
    failed = 0
    for code, desc, fn in CHECKS:
        ok, msg = fn(root)
        if ok:
            passed += 1
            if args.verbose:
                print(f"  ✅ {code} {desc}")
        else:
            failed += 1
            print(f"  ❌ {code} {desc}")
            print(f"     └─ {msg}")

    total = len(CHECKS)
    print("\n" + "=" * 64)
    print(f"{'✅' if failed == 0 else '⚠️'} Harness eval: {passed}/{total} 通过 ({failed} 项待改进)")
    print("=" * 64)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())