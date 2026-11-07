#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由结构一致性评估器（routing_eval · R1-R5）

## 定位（重要）

本脚本做的是 **路由结构一致性** 评估，不是「工具真实性」校验：
它只回答「registry / 成员 MD / plugin.json 三方写的路由信息是否对得上、条目是否齐全、
工具名写法是否像工具」，**不回答**「这台机器上到底装没装某个 MCP server」。

  SSOT（单一事实源） = skills/research-orchestration-workflow/references/agent-registry.md
  被比对对象       = agents/*.md 的 frontmatter `description`
                     + .codebuddy-plugin/plugin.json 的 teamInfo / agentName

## 五组检查（每组独立 FAIL 计数，逐条给「文件路径:行号 + 具体差异」）

  R1 成员集合一致
     registry「团队成员一览」表格的 agent_id 集合
       == agents/*.md 文件名（去 .md）集合
       == plugin.json 中 teamInfo.memberAgents ∪ {agentName 主理人} 集合
     三方两两取差集报告，任一不一致即 FAIL；另加一条 SSOT 内部一致性：
     「团队成员一览」表格 与「触发条件」### 条目标题必须一致（防 SSOT 自身漂移）。

  R2 关键触发词覆盖
     从 registry 每个 agent 条目的 `**trigger**:` 行取前 3 个关键词
     （按 ` / ` 或 `、` 分隔），要求这 3 个词都出现在对应成员 MD 的
     frontmatter `description` 中；缺哪个词就报哪个词。

  R3 条目结构完整
     每个 agent 条目必须同时含 `trigger` / `routing`；
     权限三档 safe / moderate / dangerous 必须作为 `###` 章节存在且正文非空
     （按章节标题判定，杜绝「safe / moderate / dangerous 三档」这类兜底词让被删章节蒙混过关）；
     Loop 硬停止表必须含 max_turns / max_time / max_token / circuit_breaker 四行。

  R4 工具名合法性（软校验）
     registry 每个 `**tools**:` 行里反引号包裹的工具名，必须是宿主内置工具白名单
     （WebFetch, WebSearch, Read, Grep, Glob, Write, Edit, Bash, Agent, Skill）之一，
     或以 `mcp__` 开头且后缀非空；行内出现「政策文件库」这类非工具名裸词即 FAIL。

  R5 工具集合一致性（3 个 atomic MD × 1 项）
     读每个 atomic MD 的 frontmatter `description`，复用 R4 的 tool_ok / 内置白名单
     抽取四类 token：①反引号内工具名 ②mcp__ 前缀名 ③内置工具裸词（无反引号无前缀）
     ④非工具名裸词（如「政策文件库」，直接判 FAIL）。与该 agent_id 在 registry 的
     `tools` 行集合比对：一个 token 都不枚举、也无非法裸词 → PASS（已单源化，无漂移面，
     detail 注明「description 未枚举工具，工具清单以 registry 为 SSOT」）；一旦枚举则
     必须与 registry 集合完全相等，缺项 / 多项 / 形态非法 token / 非工具名裸词全部
     FAIL，明细给出文件路径:行号、`missing=[...]`、`extra=[...]` 与「疑似非工具名裸词」。
     伪造名 mcp__GHOST_TOOL 之类必然落入 extra。R4 只校验 registry 自身命名形态、
     从不比对 MD，本组补上这个盲区。遍历范围严格锁定 3 个 atomic MD，非 atomic
     成员的 description 不参与本组。

## R2 为什么只查前 3 个触发词（阈值理由，刻意设计）

registry 的 trigger 词表是一份**长清单**（例如生医条目有 18 个词），而成员 MD 的
frontmatter description 只摘取其中一部分作为「触发词」示例，两者本就不等长；
且长清单里存在带修饰语的词（如「任意科研规划」「任何需要澄清的任务」），与 MD 里
的简洁同义写法（「科研规划」「澄清」）严格串比对会产生大量**假红**。
因此 R2 只取每个 trigger 行**最靠前的 3 个词**作为覆盖下限：这 3 个是语义最核心、
最稳定、最不该漏的关键词，既能拦住「description 完全没同步 registry」这种真漂移，
又不会因词表长度差异和同义改写把正常仓库判死。这是刻意放宽的阈值，不是遗漏。

## R4 为什么是软校验（不做本机 MCP 存在性硬校验）

部署机器不同：A 机器装了 mcp__biomcp，B 机器可能没装。若在本脚本里硬校验「MCP server
是否真实存在」，CI / 用户机器会因环境差异**假红**。故 R4 仅校验命名形态（白名单或
mcp__ 前缀且后缀非空），真实可用性由 agent-registry.md 的降级链保障。运行时输出里
会明确打印：「R4 仅校验命名形态，真实可用性由 agent-registry.md 降级链保障」。

## R5 为什么做集合比对 + 为什么单源化后无漂移面

R4 只校验 registry 自身 `**tools**:` 行的命名形态，**从不读 agents/*.md**：成员 MD
的 description 里工具名可以漂移、甚至伪造（把某工具名改成 mcp__GHOST_TOOL，因 mcp__
前缀形态合法，R4 仍全绿）——这是 v2.2.0 对抗验证实证的发布阻断项。R5 直接比对
MD description 与 registry tools 行：要么「一个 token 都不枚举」（工具清单以 registry
为 SSOT，无双源漂移面，PASS），要么「枚举了就与 registry 完全相等」（否则缺项 / 多项 /
形态非法一律 FAIL）。第 1 层已把 3 个 atomic MD 的 description 工具枚举段改为一句
纯文本引用，从根上消除双源；R5 则是防止日后有人再把工具名写回 MD 的护栏。
token 解析器覆盖四类（见 description_tool_tokens）：反引号内 token / mcp__ 前缀名 /
不带反引号也不带前缀的内置工具裸词 / 非工具名裸词（判「疑似非工具名裸词」FAIL），
统一用 tool_ok 分类，不另造白名单。内置裸词全文扫（含触发词段）以防伪造，仅对
「恰好是触发词表 `、` 分隔项」的白名单词豁免——ai 触发词表含「RAG、Agent、多智能体」，
其中 Agent 恰是内置白名单词，不豁免会让已单源化 description 假红。
④ 只取每个 `+` 之后紧邻的短裸段（到下一个句读为止），跳过第一个 `+` 之前的
角色散文，避免整段 prose 被当成工具槽位。故干净（单源化）仓库 3/3 PASS，
注入任一类别均会 FAIL。

## 用法

  python3 scripts/routing_eval.py                 # 自动定位仓库根（不依赖 cwd）
  python3 scripts/routing_eval.py --root <dir>   # 显式指定仓库根
  python3 scripts/routing_eval.py -v             # 输出每个通过项

## 退出码

  0 = 全部通过（N/N PASS）
  1 = 存在 FAIL 项（R1-R5 任一不一致）
  2 = 参数 / 关键文件缺失（仓库根、registry、plugin.json、agents 目录、JSON 非法）

## 依赖

仅标准库，Python >= 3.10。无第三方依赖，无硬编码绝对路径。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── 路径常量（全部相对仓库根；禁止散落在函数内的绝对路径字面量）──────────────
AGENTS_DIR = "agents"
REFS_DIR = "skills/research-orchestration-workflow/references"
REGISTRY_REL = f"{REFS_DIR}/agent-registry.md"
PLUGIN_REL = ".codebuddy-plugin/plugin.json"

# 宿主内置工具白名单（R4）
BUILTIN_TOOLS = frozenset({
    "WebFetch", "WebSearch", "Read", "Grep", "Glob",
    "Write", "Edit", "Bash", "Agent", "Skill",
})
MCP_PREFIX = "mcp__"

PERMISSION_TIERS = ("safe", "moderate", "dangerous")
LOOP_KEYS = ("max_turns", "max_time", "max_token", "circuit_breaker")
TRIGGER_HEAD = 3  # R2 只查前 3 个触发词，理由见模块 docstring

# R5 只比对这 3 个 atomic MD 的 frontmatter description（与 registry tools 行集合）
ATOMIC_IDS = ("domain-expert-biomed", "domain-expert-ai", "domain-expert-general")

GROUP_NAMES = {
    "R1": "成员集合一致",
    "R2": "关键触发词覆盖",
    "R3": "条目结构完整",
    "R4": "工具名合法性（软校验）",
    "R5": "工具集合一致性",
}


# ── 数据结构 ───────────────────────────────────────────────────────────────
@dataclass
class Entry:
    """registry「触发条件」section 下的一个 `### agent_id（中文名）` 条目。"""
    agent_id: str
    line: int                                   # ### 标题行号（1-based）
    trigger_line: int = 0                       # **trigger**: 行号
    trigger_keywords: list[str] = field(default_factory=list)
    has_trigger: bool = False
    has_routing: bool = False
    tools_lines: list[tuple[int, list[str]]] = field(default_factory=list)  # (行号, token 列表)


@dataclass
class Check:
    """一个原子检查项。details 在 FAIL 时给「文件路径:行号 + 具体差异」；R5 的 PASS 也带一条单源化说明。"""
    group: str
    label: str
    passed: bool
    details: list[str] = field(default_factory=list)


# ── registry 解析 ───────────────────────────────────────────────────────────
def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """按 `## ` 标题切分，返回 {标题: (起始索引, 结束索引)}，半开区间、0-based。
    起始索引指向标题**之后**的第一行；结束索引指向下一个标题行（不含）。
    """
    starts: list[tuple[str, int]] = []
    for i, ln in enumerate(lines):
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            starts.append((m.group(1), i + 1))
    out: dict[str, tuple[int, int]] = {}
    for idx, (title, start) in enumerate(starts):
        end = (starts[idx + 1][1] - 1) if idx + 1 < len(starts) else len(lines)
        out[title] = (start, end)
    return out


def _section(sections: dict[str, tuple[int, int]], keyword: str) -> tuple[int, int]:
    """取标题含 keyword 的第一个 section；找不到返回 (0, 0)。"""
    for title, span in sections.items():
        if keyword in title:
            return span
    return (0, 0)


def parse_table_ids(lines: list[str], start: int, end: int) -> dict[str, int]:
    """解析「团队成员一览」表格第一列反引号包裹的 agent_id → 行号。
    表头 `| agent_id |` 与分隔行无反引号，天然跳过；其它 section 的表格不在此范围。
    """
    out: dict[str, int] = {}
    for i in range(start, min(end, len(lines))):
        m = re.match(r"^\|\s*`([^`]+)`\s*\|", lines[i])
        if m:
            out[m.group(1).strip()] = i + 1
    return out


def parse_trigger_keywords(line: str) -> list[str]:
    """取 `**trigger**:` 行冒号后的关键词，按 ` / ` 或 `、` 分隔。"""
    body = line.split("**trigger**:", 1)[1]
    return [seg.strip() for seg in re.split(r"\s*/\s*|、", body) if seg.strip()]


def parse_tools_tokens(body: str) -> list[str]:
    """解析 `**tools**:` 行：反引号工具名 + 去掉反引号内容后残留的裸词。
    裸词正是「政策文件库」这类失真写法（往往没加反引号），必须一并纳入校验，
    只查反引号内会把它漏掉 —— 这正是本包的历史缺陷。
    """
    ticks = [t.strip() for t in re.findall(r"`([^`]+)`", body) if t.strip()]
    residue = re.sub(r"`[^`]*`", " ", body)
    residue = re.sub(r"[（(][^）)]*[）)]", " ", residue)  # 去掉括号内的说明文字
    bare = [seg.strip() for seg in re.split(r"[/、,，]", residue) if seg.strip()]
    return ticks + bare


def tool_ok(token: str) -> bool:
    """R4 命名形态判定：内置白名单，或 mcp__ 前缀且后缀非空。"""
    if token in BUILTIN_TOOLS:
        return True
    return token.startswith(MCP_PREFIX) and len(token) > len(MCP_PREFIX)


def description_tool_tokens(desc_text: str) -> tuple[set[str], list[str]]:
    """从成员 MD 的 frontmatter `description` 抽取工具名 token（R5 用）。

    四类候选统一用 tool_ok（复用 R4 的 BUILTIN_TOOLS / MCP_PREFIX，不另造一套）分类：
      ① 反引号内的 token       如 `WebFetch` / `mcp__pubmed`
      ② mcp__ 前缀名           如 mcp__pubmed / mcp__GHOST_TOOL / 空后缀 mcp__
      ③ 宿主内置工具裸词       不带反引号、不带前缀的 WebFetch / Read / Bash ...
      ④ 非工具名裸词           「政策文件库」之类，tool_ok=False → 疑似非工具名裸词 FAIL
    文件路径 `references/...`、字段名 `tools` 等非工具声明被忽略，不误判。

    返回 (tokens, illegal)：tokens = 合法工具名集合；illegal = 非工具名裸词 /
    形态非法 token（如空后缀 mcp__），一律令 R5 FAIL。

    范围：mcp__ 名 / 反引号 token / 内置裸词全文扫（含触发词段，防伪造）；
    触发词表里恰好等于内置白名单词的项（ai 的「RAG、Agent、多智能体」中 Agent）
    豁免——它是路由关键词而非工具声明，否则已单源化 description 会假红。
    ④ 只取每个 `+` 之后紧邻的短裸段（本仓库工具枚举既有写法；到下一个句读 /
    分隔符为止），跳过第一个 `+` 之前的角色散文，避免整段 prose 被当成工具槽位。
    """
    tokens: set[str] = set()
    illegal: list[str] = []

    # 去掉 frontmatter 的 `description:` 前缀与外层引号，只留值文本
    value = re.sub(r"^\s*description\s*:\s*", "", desc_text).strip()
    value = value.strip('"').strip()

    # ② mcp__ 前缀名（全文，含反引号内的 mcp__ 名与空后缀非法形态）
    for m in re.finditer(r"mcp__[A-Za-z0-9_-]*", value):
        tok = m.group(0)
        tokens.add(tok)
        if not tool_ok(tok):
            illegal.append(tok)

    # ① 反引号内的 token：tool_ok 者是工具名；非工具的反引号内容（文件路径 /
    #    字段名 / 代码字面量）不是工具声明，忽略。
    for t in re.findall(r"`([^`]+)`", value):
        t = t.strip()
        if tool_ok(t):
            tokens.add(t)
        elif t.startswith(MCP_PREFIX):
            illegal.append(t)

    # ③ 宿主内置工具裸词（全文，ASCII 词边界；反引号内与裸写都覆盖）
    trigger_parts = re.split(r"触发词\s*[:：]", value, maxsplit=1)
    head = trigger_parts[0]
    trigger_items: set[str] = set()
    if len(trigger_parts) > 1:
        trigger_items = {
            x.strip().strip('"').strip("。") for x in re.split(r"[、,，]", trigger_parts[1])
        }
    for name in BUILTIN_TOOLS:
        pat = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
        if not re.search(pat, value):
            continue
        # 仅作为触发词表的 `、` 分隔项出现、且未在角色/工具声明区出现 → 豁免
        if name in trigger_items and not re.search(pat, head):
            continue
        tokens.add(name)

    # ④ 非工具名裸词：`+` 连接的工具清单槽位（如 `WebFetch + mcp__pubmed + 政策文件库`）。
    #    只取每个 `+` 之后紧邻的短裸段（到下一个句读 / 分隔符为止），跳过第一个 `+`
    #    之前的角色散文，避免整段 prose 被当成工具槽位。
    for seg in re.split(r"\+", value)[1:]:
        s = re.sub(r"`([^`]*)`", r"\1", seg)
        s = re.sub(r"[（(][^）)]*[）)]", " ", s)
        s = re.split(r"[。；;、,，/]", s)[0].strip().strip("\"'").strip()
        if not s or len(s) > 24:
            continue
        if tool_ok(s):
            tokens.add(s)
        else:
            illegal.append(s)

    return tokens, illegal


def parse_entries(lines: list[str], start: int, end: int) -> dict[str, Entry]:
    """解析「触发条件」section 下的每个 `### agent_id（...）` 条目。
    只在该 section 内取标题，避免把「工具与权限」下的 `### safe/moderate/dangerous`
    误当成成员条目。
    """
    heads: list[tuple[str, int]] = []
    for i in range(start, min(end, len(lines))):
        m = re.match(r"^###\s+([A-Za-z0-9_-]+)（", lines[i])
        if m:
            heads.append((m.group(1), i))

    out: dict[str, Entry] = {}
    for idx, (aid, h) in enumerate(heads):
        hard_end = heads[idx + 1][1] if idx + 1 < len(heads) else end
        body_end = hard_end
        for j in range(h + 1, min(hard_end, len(lines))):
            if re.match(r"^(---|##\s)", lines[j]):
                body_end = j
                break

        entry = Entry(agent_id=aid, line=h + 1)
        for j in range(h + 1, min(body_end, len(lines))):
            ln = lines[j]
            if "**trigger**:" in ln:
                entry.has_trigger = True
                entry.trigger_line = j + 1
                entry.trigger_keywords = parse_trigger_keywords(ln)
            if "**routing**:" in ln:
                entry.has_routing = True
            tm = re.match(r"^\s*-\s*\*\*tools\*\*:\s*(.*)$", ln)
            if tm:
                entry.tools_lines.append((j + 1, parse_tools_tokens(tm.group(1))))
        out[aid] = entry
    return out


def parse_loop_keys(lines: list[str], start: int, end: int) -> dict[str, int]:
    """解析「Loop 终止硬上限」表格第一列的 key → 行号（中文表头不匹配，天然跳过）。"""
    out: dict[str, int] = {}
    for i in range(start, min(end, len(lines))):
        m = re.match(r"^\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|", lines[i])
        if m:
            out[m.group(1)] = i + 1
    return out


def parse_permission_tiers(reg_text: str) -> tuple[dict[str, tuple[int, bool]], int]:
    """按 `###` 章节标题判定 safe / moderate / dangerous 三档是否存在且正文非空。

    历史缺陷：旧实现用 `re.search(r"\\b" + tier + r"\\b", reg_text)` 在**全文**找词，
    删掉整个 `### moderate` 章节后，registry 第 76 行「safe / moderate / dangerous
    三档」与 Changelog 的说明文字仍会提供兜底词，导致 R3 全绿、章节删除漏检。
    本实现只认 `### safe|moderate|dangerous` 章节标题，并要求标题下有实质正文。

    返回 (tiers, authz_line)：
      tiers[tier] = (heading_line, body_nonempty)
        heading_line : ### 标题行号（1-based）；0 表示全文缺该 ### 标题
        body_nonempty: 从该标题到下一个 ### / ## 标题之间的正文是否有实质内容
      authz_line : 「## 工具与权限」章节起始行号（1-based），缺档时用于定位，找不到为 0
    """
    lines = reg_text.splitlines()
    # 所有 ### / ## 标题行（0-based），用于界定每档正文的右边界
    boundaries = [i for i, ln in enumerate(lines) if re.match(r"^#{2,3}\s", ln)]
    authz_line = next(
        (i + 1 for i, ln in enumerate(lines)
         if re.match(r"^##\s", ln) and "工具与权限" in ln), 0
    )

    found: dict[str, int] = {}  # tier -> 标题行索引（0-based）
    for m in re.finditer(r"^###\s+(safe|moderate|dangerous)\b", reg_text, re.M):
        tier = m.group(1)
        if tier not in found:
            found[tier] = reg_text.count("\n", 0, m.start())

    tiers: dict[str, tuple[int, bool]] = {}
    for tier in PERMISSION_TIERS:
        if tier not in found:
            tiers[tier] = (0, False)
            continue
        h = found[tier]
        next_h = next((b for b in boundaries if b > h), len(lines))
        body = lines[h + 1:next_h]
        # 实质内容 = 去掉纯空白行与纯 Markdown 分隔线（如 `---`）后仍有内容，
        # 防止「删空表格只留 --- 分隔线」也蒙混过关。
        substantive = False
        for ln in body:
            stripped = ln.strip()
            if stripped and not re.fullmatch(r"[-=_*~]{3,}", stripped):
                substantive = True
                break
        tiers[tier] = (h + 1, substantive)
    return tiers, authz_line


# ── 成员 MD / plugin.json 解析 ──────────────────────────────────────────────
def extract_description(lines: list[str]) -> tuple[str, int]:
    """提取 frontmatter 的 `description:` 值文本与该行行号（1-based）。
    兼容单行 `description: "..."` 与多行缩进值：从 description 行起收集后续缩进行。
    """
    if not lines or lines[0].strip() != "---":
        return "", 0
    fm_end = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    for i in range(1, fm_end):
        if re.match(r"^description\s*:", lines[i]):
            parts = [lines[i]]
            j = i + 1
            while j < fm_end and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                parts.append(lines[j])
                j += 1
            return "\n".join(parts), i + 1
    return "", 0


def load_agent_descriptions(root: Path) -> dict[str, tuple[str, int]]:
    """{agent_id: (description 文本, 行号)}，来自 agents/*.md 文件名（去 .md）。"""
    out: dict[str, tuple[str, int]] = {}
    for p in sorted((root / AGENTS_DIR).glob("*.md")):
        out[p.stem] = extract_description(p.read_text(encoding="utf-8").splitlines())
    return out


def load_plugin(root: Path) -> tuple[set[str], int]:
    """返回 (memberAgents ∪ {agentName} 集合, memberAgents 所在行号)。"""
    text = (root / PLUGIN_REL).read_text(encoding="utf-8")
    data = json.loads(text)
    team = data.get("teamInfo", {}) or {}
    ids: set[str] = set(team.get("memberAgents", []) or [])
    lead = data.get("agentName", "")
    if lead:
        ids.add(lead)
    member_line = next(
        (i for i, ln in enumerate(text.splitlines(), 1) if '"memberAgents"' in ln), 1
    )
    return ids, member_line


# ── 检查项构造 ──────────────────────────────────────────────────────────────
def _diff_details(
    label_a: str, ids_a: set[str], loc_a: str,
    label_b: str, ids_b: set[str], loc_b: str,
) -> list[str]:
    """生成两两差集明细，逐条给出文件路径:行号 + 具体差异。"""
    extra_a = sorted(ids_a - ids_b)
    extra_b = sorted(ids_b - ids_a)
    out = [f"{loc_a}（{label_a}）与 {loc_b}（{label_b}）不一致"]
    if extra_a:
        out.append(f"  {label_a} 多出: {extra_a}（见 {loc_a}）")
        for x in extra_a:
            out.append(f"    差异成员「{x}」仅在 {label_a} 出现，{label_b} 缺失")
    if extra_b:
        out.append(f"  {label_b} 多出: {extra_b}（见 {loc_b}）")
        for x in extra_b:
            out.append(f"    差异成员「{x}」仅在 {label_b} 出现，{label_a} 缺失")
    return out


def build_checks(
    reg_text: str,
    table_ids: dict[str, int],
    entries: dict[str, Entry],
    loop_keys: dict[str, int],
    loop_section_line: int,
    agent_desc: dict[str, tuple[str, int]],
    agent_ids: set[str],
    plugin_ids: set[str],
    plugin_member_line: int,
) -> list[Check]:
    checks: list[Check] = []

    # ── R1 成员集合一致（三方两两差集 + SSOT 内部一致性）───────────────────
    tbl_loc = f"{REGISTRY_REL}:{min(table_ids.values()) if table_ids else 0}（团队成员一览表格）"
    ent_loc = f"{REGISTRY_REL}:{min((e.line for e in entries.values()), default=0)}（触发条件条目标题）"
    md_loc = f"{AGENTS_DIR}/ 目录（*.md 文件名集合）"
    plg_loc = f"{PLUGIN_REL}:{plugin_member_line}（teamInfo.memberAgents + agentName）"

    tbl_set = set(table_ids)
    ent_set = set(entries)
    r1_pairs = [
        ("registry 表格", tbl_set, tbl_loc, "触发条件条目", ent_set, ent_loc),
        ("registry 表格", tbl_set, tbl_loc, "agents/*.md", agent_ids, md_loc),
        ("registry 表格", tbl_set, tbl_loc, "plugin.json", plugin_ids, plg_loc),
        ("agents/*.md", agent_ids, md_loc, "plugin.json", plugin_ids, plg_loc),
    ]
    for label_a, ids_a, loc_a, label_b, ids_b, loc_b in r1_pairs:
        ok = ids_a == ids_b
        checks.append(Check(
            "R1",
            f"R1 成员集合一致 · {label_a} ↔ {label_b}",
            ok,
            [] if ok else _diff_details(label_a, ids_a, loc_a, label_b, ids_b, loc_b),
        ))

    # ── R2 关键触发词覆盖（每个条目一项，只查前 3 个词）────────────────────
    for aid, entry in entries.items():
        keywords = entry.trigger_keywords[:TRIGGER_HEAD]
        desc_text, desc_line = agent_desc.get(aid, ("", 0))
        missing = [w for w in keywords if w not in desc_text]
        details: list[str] = []
        if not entry.has_trigger or len(keywords) < TRIGGER_HEAD:
            details.append(
                f"{REGISTRY_REL}:{entry.trigger_line or entry.line} 条目 {aid} 的 trigger 行"
                f"不足 {TRIGGER_HEAD} 个关键词（实际 {len(keywords)} 个）"
            )
        if desc_line == 0:
            details.append(
                f"{AGENTS_DIR}/{aid}.md 不存在或 frontmatter 无 description"
                f"（成员集合差异见 R1）"
            )
        for w in missing:
            details.append(
                f"{AGENTS_DIR}/{aid}.md:{desc_line} frontmatter description"
                f" 缺关键触发词「{w}」（源自 {REGISTRY_REL}:{entry.trigger_line}）"
            )
        checks.append(Check(
            "R2", f"R2 关键触发词覆盖 · {aid}（前 {TRIGGER_HEAD} 词）",
            bool(keywords) and len(keywords) >= TRIGGER_HEAD and not missing and desc_line > 0,
            details,
        ))

    # ── R3 条目结构完整 ────────────────────────────────────────────────────
    # 3.1 每个条目必须同时含 trigger / routing
    for aid, entry in entries.items():
        lacks = []
        if not entry.has_trigger:
            lacks.append("**trigger**")
        if not entry.has_routing:
            lacks.append("**routing**")
        checks.append(Check(
            "R3", f"R3 结构完整 · 条目 {aid} 字段",
            not lacks,
            [f"{REGISTRY_REL}:{entry.line} 条目 {aid} 缺 {' / '.join(lacks)} 行"] if lacks else [],
        ))
    # 3.2 权限三档：必须作为 ### 章节存在且正文非空（按章节标题判定，
    #     杜绝「safe / moderate / dangerous 三档」这类兜底词让被删章节蒙混过关）
    tiers, authz_line = parse_permission_tiers(reg_text)
    for tier in PERMISSION_TIERS:
        heading_line, body_nonempty = tiers[tier]
        if heading_line == 0:
            loc = f"{REGISTRY_REL}:{authz_line}" if authz_line else REGISTRY_REL
            details = [
                f"{loc}（工具与权限章节）缺权限档「{tier}」的 ### 章节标题"
                f"（应有 `### {tier}（...）` 标题行；全文其它位置的兜底词不计入）"
            ]
        elif not body_nonempty:
            details = [
                f"{REGISTRY_REL}:{heading_line} 权限档「{tier}」章节正文为空"
                f"（### {tier} 标题到下一个 ### / ## 标题之间须有至少一行实质内容）"
            ]
        else:
            details = []
        checks.append(Check(
            "R3", f"R3 结构完整 · 权限档 {tier}",
            not details,
            details,
        ))
    # 3.3 Loop 硬停止表四行
    for key in LOOP_KEYS:
        ok = key in loop_keys
        checks.append(Check(
            "R3", f"R3 结构完整 · Loop 表 {key} 行",
            ok,
            [f"{REGISTRY_REL}:{loop_section_line}（Loop 终止硬上限表）缺 {key} 行"] if not ok else [],
        ))

    # ── R4 工具名合法性（软校验，每个 **tools**: 行一项）──────────────────
    for entry in entries.values():
        for line_no, tokens in entry.tools_lines:
            illegal = [t for t in tokens if not tool_ok(t)]
            details = [
                f"{REGISTRY_REL}:{line_no} 工具名「{t}」非内置白名单且非"
                f" {MCP_PREFIX} 前缀且后缀非空（疑似非工具名裸词）"
                for t in illegal
            ]
            checks.append(Check(
                "R4", f"R4 工具名合法性 · {REGISTRY_REL}:{line_no}",
                not illegal,
                details,
            ))

    # ── R5 工具集合一致性（每个 atomic MD 一项；补 R4 不比对 MD 的盲区）──────
    for aid in ATOMIC_IDS:
        md_file = f"{AGENTS_DIR}/{aid}.md"
        desc_text, desc_line = agent_desc.get(aid, ("", 0))
        md_tokens, illegal = description_tool_tokens(desc_text)
        entry = entries.get(aid)
        reg_tokens: set[str] = set()
        tools_loc = REGISTRY_REL
        if entry is not None:
            for _ln, toks in entry.tools_lines:
                reg_tokens.update(toks)
            if entry.tools_lines:
                tools_loc = f"{REGISTRY_REL}:{entry.tools_lines[0][0]}"

        label = f"R5 工具集合一致性 · {md_file}"
        if not md_tokens and not illegal:
            # 已单源化：description 不枚举任何工具名、也无非法裸词，无双源漂移面
            checks.append(Check(
                "R5", label, True,
                [f"{md_file}:{desc_line} description 未枚举工具，工具清单以 registry 为 SSOT"],
            ))
            continue

        missing = sorted(reg_tokens - md_tokens)
        extra = sorted(md_tokens - reg_tokens)
        passed = not missing and not extra and not illegal
        details = [
            f"{md_file}:{desc_line} frontmatter description 出现工具名 token 或非法裸段，"
            f"与 {tools_loc}（tools 行）不一致（已单源化的 description 不应枚举工具）",
            f"  missing={missing}（registry 有、description 缺）",
            f"  extra={extra}（description 有、registry 无；伪造 / 漂移工具名）",
            f"  illegal={sorted(set(illegal))}（形态非法 token）",
        ]
        if illegal:
            # 「疑似非工具名裸词」只在确有非法裸词时出现，供 N9 精确断言
            details.append(
                f"  → 疑似非工具名裸词 {sorted(set(illegal))}"
                f"（工具清单槽位内 tool_ok=False，判定与 R4 一致）"
            )
        checks.append(Check("R5", label, passed, [] if passed else details))

    return checks


# ── 仓库根定位（参照 harness_eval.py，起点为本文件位置，不依赖 cwd）──────────
def find_repo_root(start: Path) -> Path | None:
    """上溯定位仓库根（须同时含 .claude-plugin 与 .codebuddy-plugin）。"""
    cur = start.resolve().parent
    for _ in range(8):
        if (cur / ".claude-plugin").exists() and (cur / ".codebuddy-plugin").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="路由结构一致性评估器（R1-R5）")
    parser.add_argument("--root", type=Path, default=None, help="仓库根（默认自动定位）")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出每个通过项")
    args = parser.parse_args(argv)

    root = args.root.resolve() if args.root else find_repo_root(Path(__file__))
    if root is None or not root.is_dir():
        print("❌ 找不到仓库根（须同时含 .claude-plugin 与 .codebuddy-plugin）", file=sys.stderr)
        return 2

    registry = root / REGISTRY_REL
    plugin = root / PLUGIN_REL
    agents_dir = root / AGENTS_DIR
    for p, desc in ((registry, "SSOT registry"), (plugin, "plugin.json"), (agents_dir, "agents 目录")):
        if not p.exists():
            print(f"❌ 关键文件/目录缺失: {p}（{desc}）", file=sys.stderr)
            return 2

    try:
        plugin_ids, plugin_member_line = load_plugin(root)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"❌ 无法解析 {plugin}: {exc}", file=sys.stderr)
        return 2

    reg_text = registry.read_text(encoding="utf-8")
    lines = reg_text.splitlines()
    sections = _sections(lines)

    table_ids = parse_table_ids(lines, *_section(sections, "团队成员一览"))
    entries = parse_entries(lines, *_section(sections, "触发条件"))
    loop_start, loop_end = _section(sections, "Loop 终止硬上限")
    loop_keys = parse_loop_keys(lines, loop_start, loop_end)
    loop_section_line = loop_start  # 0-based 索引；仅作定位提示
    agent_desc = load_agent_descriptions(root)
    agent_ids = set(agent_desc)

    checks = build_checks(
        reg_text, table_ids, entries, loop_keys, loop_section_line,
        agent_desc, agent_ids, plugin_ids, plugin_member_line,
    )

    print("🔍 路由结构一致性评估（routing_eval · R1-R5）")
    print(f"   仓库根: {root}")
    print(f"   SSOT  : {REGISTRY_REL}")
    print(f"   被比对: {AGENTS_DIR}/*.md frontmatter description + {PLUGIN_REL} teamInfo")
    print(f"   说明  : R2 仅查 trigger 行前 {TRIGGER_HEAD} 个关键词（刻意阈值，避免词表远长于 description 造成过严假红）")
    print("   说明  : R4 仅校验命名形态，真实可用性由 agent-registry.md 降级链保障")
    print("   说明  : R5 比对 3 个 atomic MD description 与 registry tools 行；未枚举工具即视为单源化")
    print()

    for group in ("R1", "R2", "R3", "R4", "R5"):
        group_checks = [c for c in checks if c.group == group]
        gp = sum(1 for c in group_checks if c.passed)
        gf = len(group_checks) - gp
        print(f"【{group} {GROUP_NAMES[group]}】 {gp}/{len(group_checks)} PASS（{gf} FAIL）")
        for c in group_checks:
            if c.passed:
                if args.verbose:
                    print(f"   ✅ {c.label}")
                    for d in c.details:
                        print(f"      └─ {d}")
            else:
                print(f"   ❌ {c.label}")
                for d in c.details:
                    print(f"      └─ {d}")
        print()

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = total - passed
    print("=" * 72)
    print(f"{'✅' if failed == 0 else '⚠️'} 路由结构一致性: {passed}/{total} PASS（{failed} FAIL）")
    print("=" * 72)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
