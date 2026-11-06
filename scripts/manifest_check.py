#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专家包一致性校验器（manifest 对等 / 资产完整性 / 版本一致 / 废弃表述）

## 为什么需要这个脚本

本包同时发布给 Claude Code 与 WorkBuddy，因此维护两份 manifest：
  - .claude-plugin/plugin.json   （Claude Code 标准）
  - .codebuddy-plugin/plugin.json（WorkBuddy 标准）
两份文件都靠人工维护。历史上出现过「一边改了、另一边忘改」的偏差：
例如 WorkBuddy 侧的 displayDescription 残留了已废弃的「三级冲突仲裁」表述，
而 CI 原有的 grep 因为匹配的是精确串「三级仲裁」而漏检（假绿）。
本脚本把这类偏差变成 CI 可拦截的硬错误，替代纯人工 review。

## 校验项

  C1 两份 manifest 存在且为合法 JSON
  C2 两份 manifest 的「共享字段」逐项一致
  C3 agents 数组引用的 .md 文件全部存在（两份都查）
  C4 skills 字段为字符串且指向存在的目录（WorkBuddy 第一方约定："./skills"）
  C5 头像文件（avatar + members[].avatar）全部存在
  C6 teamInfo 的 lead / member 与 agents 列表自洽
  C7 README 头部声明的版本号与 manifest 的 version 一致
  C8 仓库内不得残留已废弃表述（比 CI 的 grep 更严格，支持跨字符匹配）
  C9 团队每个 agent 的 MD 都声明了契约章节（新成员不得裸奔入场）
  C10 市场描述文件 marketplace.json 存在且指向本插件（缺它则一键安装失效）
  C11 每个 agent 的 MD 具备结构合法的 YAML frontmatter（宿主据此注册代理）
  C12 Team 型包根 settings.json 存在且单键 agent 指向主理人（官方 validate_expert 硬要求）

## C11 的动机与解析范围（重要）

C1–C10 全都只读 manifest 与目录结构，**没有一条读过 agent MD 的内容结构**。
frontmatter 一旦损坏，宿主（Claude Code / WorkBuddy）会静默地加载不了该代理，
而 manifest 校验依旧全绿 —— 这是一种「发布物看起来完整、实际运行时缺人」的故障。
v2.0.2 发布后由独立验证者注入破坏用例发现：删掉 frontmatter 结束分隔符后校验器
仍返回 rc=0。实测更宽：完全删除 frontmatter、YAML 结构非法、name 与文件名不符、
description 缺失或为空 —— 六种破坏形态全部放行。

C11 的解析器**不是**通用 YAML 解析器，只覆盖 frontmatter 实际使用的子集：

  - 顶层与一层嵌套的 `键: 值`
  - 标量：裸值 / 单引号 / 双引号 / 块标量指示符（| > |- >- 等）
  - 缩进序列项（`- 值`）
  - 空行与整行注释

超出该子集的结构会**报错而非放行**（fail-closed）。这是刻意的：本包的 6 个 agent
都用简单结构，遇到解析器不认识的东西应当让人工看一眼，而不是默默判绿。
选择纯标准库实现而非依赖 PyYAML，是为了维持本脚本「零依赖可直接在 CI 运行」的约定，
同时避免出现「本地有 PyYAML 更严、CI 没装更松」的双重判定标准。

## 用法

  python3 scripts/manifest_check.py              # 自动定位仓库根
  python3 scripts/manifest_check.py --root <dir> # 显式指定仓库根
  python3 scripts/manifest_check.py -v           # 输出每个通过项

## 退出码

  0 = 全部通过
  1 = 存在校验失败项
  2 = 用法 / 环境错误（如仓库根不含 manifest）

## 依赖

仅标准库，Python >= 3.9。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 路径常量（相对仓库根；禁止散落在函数内的字面量）────────────────────────
CLAUDE_MANIFEST = ".claude-plugin/plugin.json"
CODEBUDDY_MANIFEST = ".codebuddy-plugin/plugin.json"
CLAUDE_MARKETPLACE = ".claude-plugin/marketplace.json"
CODEBUDDY_MARKETPLACE = ".codebuddy-plugin/marketplace.json"
README = "README.md"

# 两份 manifest 必须逐项一致的字段
SHARED_FIELDS = (
    "name",
    "version",
    "license",
    "homepage",
    "repository",
    "agents",
    "skills",
)

# 头像字段：顶层 avatar + members[].avatar
AVATAR_TOP_KEY = "avatar"
AVATAR_MEMBER_KEY = "avatar"

# 参与废弃表述扫描的文本文件类型
SCAN_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml"}

# 扫描时跳过的目录名（版本控制、缓存、本地产物）
SKIP_DIRS = {".git", "__pycache__", ".backups", "node_modules", ".venv", "dist", "build"}

# 扫描豁免：以下文件需要「引用」已废弃术语本身，不能算违规
#   - 审计文档：用于记录「曾经用过、现已修复」的术语
#   - 规则定义文件：本脚本自身就是术语清单的宿主，必然包含这些字面量
#   - 自测文件：负例用例必须真的写出违规文本才能验证校验器有效
SCAN_EXEMPT = {
    "CHANGELOG.md",                          # 审计：记录历次修复涉及的术语
    "docs/REDTEAM-REPORT.md",                # 审计：报告中引用被修复的术语
    "scripts/manifest_check.py",             # 规则宿主：FORBIDDEN_PATTERNS 字面量所在文件
    "scripts/manifest_check_selftest.py",    # 自测宿主：负例需构造违规文本
}

# 已废弃表述（正则）。这些是历史版本用语，正文中出现即为回归。# 注意：用宽松模式而非精确串，避免「三级冲突仲裁」这类插入词导致漏检。
FORBIDDEN_PATTERNS = (
    (r"三级[^，。；\n]{0,6}仲裁", "旧仲裁层级表述（现为五级仲裁）"),
    (r"六阶段", "旧状态机表述（现为八阶段）"),
    (r"5\s*人协作", "旧团队规模表述（现为六人）"),
    (r"Six-role", "旧英文角色数表述（现为 Six-agent）"),
    (r"six-role research", "旧英文角色数表述（现为 Six-agent）"),
    (r"L1-L3\s*conflict", "旧仲裁层级范围（现为 L1-L5）"),
    (r"msg_type", "旧信封字段名（现为 type）"),
    (r"任意一维\s*<\s*90", "旧 FREEZE 量纲表述（现为完整度 0-100% + 风险维 0-10）"),
    (r"五项核心任务", "v1 遗留任务模型（现为三大任务 + 八阶段状态机）"),
    (r"5-task", "v1 遗留任务模型（现为三大任务 + 八阶段状态机）"),
    (r"example\.(com|org)", "占位邮箱 / URL，发布前必须替换"),
)

# 契约章节标记：每个 agent MD 必须至少命中其一，用于固化「新成员不得裸奔入场」的不变式。
#   - 分析 / 执行 / 审查型成员：使用「v2.0 协议合规契约」
#   - 整合者：使用「接口契约」（输入 / 输出信封）
#   - 主理人：使用「Harness 运行时规范 v2.0」
# 三者命名不同但语义等价，故并列接受；新增成员必须至少采用其中一种。
CONTRACT_SECTION_MARKERS = (
    "协议合规契约",
    "接口契约",
    "Harness 运行时规范",
)

# ── C11 frontmatter 校验常量 ────────────────────────────────────────────────
FRONTMATTER_FENCE = "---"

# 每个 agent MD 的 frontmatter 必须提供的顶层字段（值为空视为缺失）
FRONTMATTER_REQUIRED = ("name", "description")

# description 最短长度：过短则宿主无法据此判断何时启用该代理
FRONTMATTER_MIN_DESCRIPTION = 10

# 结束分隔符的搜索上限。frontmatter 本应只有几十行；超出这个窗口还找不到
# 结束符，说明首行 `---` 是正文里的一条水平线，或结束符已被误删。
FRONTMATTER_MAX_LINES = 200

# 需要与 manifest members[] 交叉核对的展示字段
FRONTMATTER_CROSSCHECK_FIELDS = ("displayName", "profession")

# 键名允许的字符集
FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

# 块标量指示符（其后内容原样保留，不做标量校验）
BLOCK_SCALAR_INDICATORS = {"|", ">", "|-", ">-", "|+", ">+"}

# 流式集合的配对括号
FLOW_PAIRS = {"[": "]", "{": "}"}


class Checker:
    """收集校验结果；失败项汇总后统一以退出码 1 结束。"""

    def __init__(self, root: Path, verbose: bool = False) -> None:
        self.root = root
        self.verbose = verbose
        self.failures: list[str] = []
        self.passed = 0

    # ── 结果记录 ────────────────────────────────────────────────────────────
    def ok(self, msg: str) -> None:
        self.passed += 1
        if self.verbose:
            print(f"  ✅ {msg}")

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"  ❌ {msg}")

    def section(self, title: str) -> None:
        print(f"\n── {title} ──")

    # ── 工具 ────────────────────────────────────────────────────────────────
    def rel(self, path) -> Path:
        """把 manifest 里的相对路径解析为仓库内的绝对路径。"""
        text = str(path)
        for prefix in ("./", "/"):
            if text.startswith(prefix):
                text = text[len(prefix):]
        return self.root / text

    @staticmethod
    def load_json(path: Path):
        """读取 JSON；失败返回 None 并交由调用方记录。"""
        try:
            with path.open(encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None


def check_c1_c2(chk: Checker):
    """C1 manifest 合法性；C2 共享字段对等。返回 (claude_dict, codebuddy_dict)。"""
    chk.section("C1 manifest 存在性与 JSON 合法性")
    loaded = {}
    for label, rel_path in (("Claude Code", CLAUDE_MANIFEST), ("WorkBuddy", CODEBUDDY_MANIFEST)):
        path = chk.root / rel_path
        if not path.exists():
            chk.fail(f"{label} manifest 缺失: {rel_path}")
            loaded[label] = None
            continue
        data = chk.load_json(path)
        if data is None:
            chk.fail(f"{label} manifest JSON 非法: {rel_path}")
            loaded[label] = None
            continue
        chk.ok(f"{label} manifest 合法: {rel_path} (version={data.get('version')})")
        loaded[label] = data

    claude, codebuddy = loaded.get("Claude Code"), loaded.get("WorkBuddy")

    chk.section("C2 双 manifest 共享字段对等")
    if not claude or not codebuddy:
        chk.fail("C2 跳过：上一步存在无法解析的 manifest")
        return claude, codebuddy

    for field in SHARED_FIELDS:
        left, right = claude.get(field), codebuddy.get(field)
        if left == right:
            chk.ok(f"字段一致: {field}")
        else:
            chk.fail(
                f"字段不一致: {field}\n"
                f"       {CLAUDE_MANIFEST} = {json.dumps(left, ensure_ascii=False)}\n"
                f"       {CODEBUDDY_MANIFEST} = {json.dumps(right, ensure_ascii=False)}"
            )
    return claude, codebuddy


def check_c3_agents(chk: Checker, manifests: dict) -> None:
    """C3 agents 数组引用的文件必须存在（并反向检查孤儿文件）。"""
    chk.section("C3 agents 引用完整性")
    seen: set[str] = set()
    for label, data in manifests.items():
        if not data:
            continue
        agents = data.get("agents")
        if not isinstance(agents, list) or not agents:
            chk.fail(f"{label} manifest 的 agents 应为非空数组")
            continue
        for entry in agents:
            if entry in seen:
                chk.ok(f"agent 文件存在（已查过）: {entry}")
                continue
            if chk.rel(entry).is_file():
                seen.add(entry)
                chk.ok(f"agent 文件存在: {entry}")
            else:
                chk.fail(f"{label} 引用的 agent 文件不存在: {entry}")

    # 反向：agents/ 下不得有未被 manifest 引用的孤儿文件。
    # 孤儿文件同样会被打进发布物（tarball 走 git archive 全量打包），
    # 却不会被宿主加载 —— 属于「体积涨了、能力没涨」的隐性缺陷。
    declared: set[str] = set()
    for data in manifests.values():
        if data:
            declared |= {Path(a).name for a in (data.get("agents") or [])}

    agents_dir = chk.root / "agents"
    if not agents_dir.is_dir():
        chk.fail("agents/ 目录不存在")
        return
    if not declared:
        chk.fail("C3 反向检查跳过：manifest 未声明任何 agent")
        return

    orphans = sorted(p.name for p in agents_dir.glob("*.md") if p.name not in declared)
    if orphans:
        chk.fail(
            f"agents/ 下存在未被 manifest 引用的孤儿文件（会进入发布物但不被加载）: {orphans}"
        )
    else:
        chk.ok(f"agents/ 下无孤儿文件（{len(declared)} 个文件全部被引用）")


def check_c4_skills(chk: Checker, manifests: dict) -> None:
    """C4 skills 必须是字符串目录路径（WorkBuddy 第一方约定 "./skills"）。"""
    chk.section("C4 skills 字段格式与路径")
    for label, data in manifests.items():
        if not data:
            continue
        skills = data.get("skills")
        if not isinstance(skills, str):
            chk.fail(
                f"{label} manifest 的 skills 应为字符串目录路径（如 \"./skills\"），"
                f"实际为 {json.dumps(skills, ensure_ascii=False)}"
            )
            continue
        target = chk.rel(skills)
        if target.is_dir():
            chk.ok(f"{label} skills 指向存在的目录: {skills}")
        else:
            chk.fail(f"{label} skills 指向的目录不存在: {skills}")


def check_c5_avatars(chk: Checker, manifests: dict) -> None:
    """C5 avatar 与 members[].avatar 文件必须存在。"""
    chk.section("C5 头像资源完整性")
    data = manifests.get("WorkBuddy")
    if not data:
        chk.fail("C5 跳过：无 WorkBuddy manifest")
        return

    targets = []
    if data.get(AVATAR_TOP_KEY):
        targets.append(("avatar", data[AVATAR_TOP_KEY]))
    for member in data.get("members") or []:
        if member.get(AVATAR_MEMBER_KEY):
            targets.append((f"members[{member.get('id')}]", member[AVATAR_MEMBER_KEY]))

    if not targets:
        chk.fail("WorkBuddy manifest 未声明任何头像")
        return

    for label, path in targets:
        if chk.rel(path).is_file():
            chk.ok(f"头像存在 ({label}): {path}")
        else:
            chk.fail(f"头像缺失 ({label}): {path}")


def check_c6_team(chk: Checker, manifests: dict) -> None:
    """C6 teamInfo 与 agents / members 自洽。"""
    chk.section("C6 团队结构自洽性")
    data = manifests.get("WorkBuddy")
    if not data:
        chk.fail("C6 跳过：无 WorkBuddy manifest")
        return

    agents = data.get("agents") or []
    agent_ids = {Path(a).stem for a in agents}
    team = data.get("teamInfo") or {}
    lead = team.get("leadAgent")
    members = team.get("memberAgents") or []

    if lead and lead in agent_ids:
        chk.ok(f"leadAgent 与 agents 自洽: {lead}")
    else:
        chk.fail(f"teamInfo.leadAgent 不在 agents 列表中: {lead}")

    unknown = [m for m in members if m not in agent_ids]
    if unknown:
        chk.fail(f"teamInfo.memberAgents 含未知成员: {unknown}")
    else:
        chk.ok(f"memberAgents 全部在 agents 列表中（{len(members)} 人）")

    expected_members = len(agents) - 1
    if lead and len(members) == expected_members:
        chk.ok(f"成员数自洽: agents={len(agents)} = lead 1 + members {len(members)}")
    elif lead:
        chk.fail(f"成员数不自洽: agents={len(agents)}，期望 memberAgents={expected_members}，实际={len(members)}")

    # members[] 的 id 应与 agents 完全对应（顺序不限）
    member_ids = [m.get("id") for m in (data.get("members") or [])]
    if sorted(member_ids) == sorted(agent_ids):
        chk.ok("members[].id 与 agents 一一对应")
    else:
        only_members = sorted(set(member_ids) - agent_ids)
        only_agents = sorted(agent_ids - set(member_ids))
        chk.fail(f"members[].id 与 agents 不对应；仅 members 有={only_members}，仅 agents 有={only_agents}")


def check_c7_version(chk: Checker, manifests: dict) -> None:
    """C7 README 头部版本号必须与 manifest version 一致。"""
    chk.section("C7 README 版本一致性")
    data = manifests.get("WorkBuddy") or manifests.get("Claude Code")
    if not data:
        chk.fail("C7 跳过：无可用 manifest")
        return

    readme_path = chk.root / README
    if not readme_path.is_file():
        chk.fail(f"README 缺失: {README}")
        return

    text = readme_path.read_text(encoding="utf-8")
    match = re.search(r">\s*\*\*版本\*\*[：:]\s*([0-9]+\.[0-9]+\.[0-9]+)", text)
    if not match:
        chk.fail("README 头部未找到形如「> **版本**：x.y.z」的版本声明")
        return

    declared, actual = match.group(1), str(data.get("version"))
    if declared == actual:
        chk.ok(f"README 版本与 manifest 一致: {declared}")
    else:
        chk.fail(f"README 版本({declared}) 与 manifest version({actual}) 不一致")


def check_c8_forbidden(chk: Checker) -> None:
    """C8 扫描废弃表述。"""
    chk.section("C8 废弃表述扫描")
    offenders: dict[str, list[str]] = {}

    for path in sorted(chk.root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        rel = path.relative_to(chk.root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.as_posix() in SCAN_EXEMPT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, desc in FORBIDDEN_PATTERNS:
            for hit in re.finditer(pattern, text):
                line_no = text.count("\n", 0, hit.start()) + 1
                offenders.setdefault(f"{pattern} → {desc}", []).append(
                    f"       {rel}:{line_no}  …{hit.group(0)}…"
                )

    if not offenders:
        chk.ok(f"未发现废弃表述（扫描 {len(FORBIDDEN_PATTERNS)} 条规则）")
        return

    for desc, lines in offenders.items():
        chk.fail(f"残留废弃表述: {desc}")
        for line in lines:
            print(line)


def check_c9_contracts(chk: Checker, manifests: dict) -> None:
    """C9 团队每个 agent 的 MD 必须声明契约章节。

    动机：本包的 6 个 agent 中，分析/执行/审查型成员使用「v2.0 协议合规契约」，
    整合者使用「接口契约」，主理人使用「Harness 运行时规范 v2.0」。三者语义等价
    但命名不同，历史上出现过「新增成员未带任何契约章节」的不一致。此校验把
    「新成员不得裸奔入场」固化为不变式。注意 protocol_check.py 只测协议逻辑本身，
    并不读取 agent MD，所以这条链路此前完全没有自动化保护。
    """
    chk.section("C9 agent 契约章节完整性")
    data = manifests.get("WorkBuddy")
    if not data:
        chk.fail("C9 跳过：无 WorkBuddy manifest")
        return

    id_to_path = {Path(a).stem: a for a in (data.get("agents") or [])}
    team = data.get("teamInfo") or {}
    ordered = [("lead", team.get("leadAgent"))]
    ordered += [("member", m) for m in (team.get("memberAgents") or [])]

    for role, agent_id in ordered:
        if not agent_id:
            continue
        rel_path = id_to_path.get(agent_id)
        if not rel_path:
            chk.fail(f"无法在 agents 中定位 {agent_id}")
            continue
        target = chk.rel(rel_path)
        if not target.is_file():
            chk.fail(f"agent MD 缺失: {rel_path}")
            continue
        text = target.read_text(encoding="utf-8")
        hit = [m for m in CONTRACT_SECTION_MARKERS if m in text]
        if hit:
            chk.ok(f"{role} {agent_id} 契约章节: {hit[0]}")
        else:
            chk.fail(
                f"{role} {agent_id} 未找到契约章节，"
                f"需含 {' 或 '.join(CONTRACT_SECTION_MARKERS)} 之一：{rel_path}"
            )


def check_c10_marketplace(chk: Checker, manifests: dict) -> None:
    """C10 市场描述文件存在且与插件自洽。

    动机：本仓库是「自我托管市场」——仓库根既是市场根（放 marketplace.json），
    又是插件根（放 plugin.json），市场条目用 source "./" 指回仓库自身。
    如果没有 marketplace.json，`/plugin marketplace add owner/repo` 无法工作，
    而 README 却把它写成推荐安装方式 —— 这正是 v2.0.1 之后才发现的问题。
    此校验确保市场文件存在、可解析、且指向本插件。
    """
    chk.section("C10 市场描述文件（marketplace.json）")
    plugin_name = (manifests.get("Claude Code") or {}).get("name")

    loaded = {}
    for label, rel_path in (
        ("Claude Code", CLAUDE_MARKETPLACE),
        ("WorkBuddy", CODEBUDDY_MARKETPLACE),
    ):
        path = chk.root / rel_path
        if not path.exists():
            chk.fail(
                f"{label} 市场文件缺失: {rel_path} —— "
                f"缺它时 `/plugin marketplace add` 无法工作，README 的推荐安装方式会失败"
            )
            loaded[label] = None
            continue
        data = chk.load_json(path)
        if data is None:
            chk.fail(f"{label} 市场文件 JSON 非法: {rel_path}")
            loaded[label] = None
            continue
        loaded[label] = data
        for field in ("name", "owner", "plugins"):
            if not data.get(field):
                chk.fail(f"{rel_path} 缺少字段: {field}")
        entries = data.get("plugins") or []
        if not isinstance(entries, list) or not entries:
            chk.fail(f"{rel_path} 的 plugins 应为非空数组")
            continue
        names = [e.get("name") for e in entries]
        if plugin_name and plugin_name not in names:
            chk.fail(f"{rel_path} 未收录本插件 {plugin_name}；当前收录 {names}")
            continue
        entry = next(e for e in entries if e.get("name") == plugin_name)
        source = entry.get("source")
        if source in ("./", ".", None):
            chk.ok(f"{label} 市场条目指向仓库自身: {plugin_name} ← source={source or './'}")
        else:
            target = chk.rel(source)
            if target.is_dir():
                chk.ok(f"{label} 市场条目 source 可解析: {source}")
            else:
                chk.fail(f"{rel_path} 的 source 无法解析为目录: {source}")

    left, right = loaded.get("Claude Code"), loaded.get("WorkBuddy")
    if left and right:
        if left.get("name") == right.get("name"):
            chk.ok(f"两份市场名一致: {left.get('name')}")
        else:
            chk.fail(f"两份市场名不一致: {left.get('name')} vs {right.get('name')}")
        if [p.get("name") for p in left.get("plugins", [])] == [
            p.get("name") for p in right.get("plugins", [])
        ]:
            chk.ok("两份市场的 plugins 列表一致")
        else:
            chk.fail("两份市场的 plugins 列表不一致")


def _unquote(value: str) -> str:
    """去掉成对包裹的引号，得到可用于比较 / 计长的裸值。"""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _scalar_error(value: str) -> str:
    """检查标量写法是否结构性合法；合法返回空串，否则返回错误说明。"""
    if value == "" or value in BLOCK_SCALAR_INDICATORS:
        return ""
    head = value[0]
    if head in "\"'":
        if len(value) < 2 or not value.endswith(head):
            return f"引号未闭合: {value[:40]}"
        return ""
    if head in FLOW_PAIRS:
        if not value.endswith(FLOW_PAIRS[head]):
            return f"流式集合括号未闭合: {value[:40]}"
        return ""
    return ""


def _parse_frontmatter_block(inner: list[str], offset: int):
    """解析 frontmatter 正文行。返回 (data, errors)。

    只覆盖本包 frontmatter 实际使用的 YAML 子集；遇到不认识的结构一律记错误
    （fail-closed），避免「解析器不懂」被误当成「格式没问题」。
    """
    data: dict = {}
    errors: list[str] = []
    seen_top: dict[str, int] = {}
    nested_seen: dict[str, int] = {}
    current_top: str | None = None
    block_scalar: tuple[str, int] | None = None

    for i, raw in enumerate(inner):
        lineno = offset + i
        if not raw.strip():
            continue

        stripped = raw.rstrip()
        content = stripped.strip()
        indent = len(stripped) - len(stripped.lstrip(" "))

        if "\t" in stripped[:indent]:
            errors.append(f"第 {lineno} 行：缩进不得使用 Tab（YAML 只允许空格）")
            continue
        if content.startswith("#"):
            continue

        # 块标量的续行：缩进深于键行的内容整体视为文本，交给 YAML 宿主处理
        if block_scalar is not None:
            if indent > block_scalar[1]:
                continue
            block_scalar = None

        if content.startswith("- "):
            if indent == 0:
                errors.append(
                    f"第 {lineno} 行：顶层不支持序列项 `- `（frontmatter 顶层应为键值对）"
                )
            elif current_top is None:
                errors.append(f"第 {lineno} 行：序列项无所属的顶层键")
            elif not isinstance(data.get(current_top), dict):
                errors.append(
                    f"第 {lineno} 行：顶层键 `{current_top}` 已是标量，其下不应再有列表项"
                )
            continue

        if ":" not in content:
            errors.append(f"第 {lineno} 行：不是 `键: 值` 结构 → {content[:40]!r}")
            continue

        key, _, value = content.partition(":")
        key, value = key.strip(), value.strip()

        if not FRONTMATTER_KEY_RE.match(key):
            errors.append(f"第 {lineno} 行：键名不合法 `{key}`")
            continue

        scalar_err = _scalar_error(value)
        if scalar_err:
            errors.append(f"第 {lineno} 行：{scalar_err}（键 `{key}`）")
            continue

        if indent == 0:
            if key in seen_top:
                errors.append(
                    f"第 {lineno} 行：顶层键重复 `{key}`（首次出现于第 {seen_top[key]} 行）"
                )
                continue
            seen_top[key] = lineno
            current_top = key
            nested_seen = {}
            if value == "":
                data[key] = {}          # 期待其下出现缩进子项
            else:
                data[key] = _unquote(value)
                if value in BLOCK_SCALAR_INDICATORS:
                    block_scalar = (key, 0)
            continue

        # 缩进层：只允许一层嵌套
        if current_top is None:
            errors.append(f"第 {lineno} 行：缩进项无所属的顶层键")
            continue
        if not isinstance(data.get(current_top), dict):
            errors.append(
                f"第 {lineno} 行：顶层键 `{current_top}` 已是标量，其下不应再有缩进子项"
            )
            continue
        if key in nested_seen:
            errors.append(
                f"第 {lineno} 行：`{current_top}` 下子键重复 `{key}`"
                f"（首次出现于第 {nested_seen[key]} 行）"
            )
            continue
        nested_seen[key] = lineno
        if value == "":
            errors.append(f"第 {lineno} 行：`{current_top}.{key}` 为空值（不支持三层嵌套）")
            continue
        data[current_top][key] = _unquote(value)
        if value in BLOCK_SCALAR_INDICATORS:
            block_scalar = (key, indent)

    return data, errors


def parse_frontmatter(text: str):
    """提取并结构校验 Markdown 的 YAML frontmatter。

    返回 (data, errors, fence_start_line)：
      data   : 顶层键 -> 裸标量字符串 / 子键字典（引号已去除）
      errors : 结构性问题的可读描述（含行号）；空列表表示结构合法
    """
    if text.startswith("\ufeff"):
        return {}, [
            "文件以 UTF-8 BOM 开头，宿主可能无法识别首行分隔符 `---`；请另存为无 BOM 的 UTF-8"
        ], 1

    lines = text.splitlines()
    if not lines:
        return {}, ["文件为空"], 1
    if lines[0].strip() != FRONTMATTER_FENCE:
        return {}, [
            f"缺少起始分隔符 `{FRONTMATTER_FENCE}`（文件第一行必须是它），"
            f"实际为: {lines[0][:40]!r}"
        ], 1

    end = None
    for i in range(1, min(len(lines), FRONTMATTER_MAX_LINES + 1)):
        if lines[i].strip() == FRONTMATTER_FENCE:
            end = i
            break
    if end is None:
        return {}, [
            f"起始分隔符 `{FRONTMATTER_FENCE}` 未在前 {FRONTMATTER_MAX_LINES} 行内找到结束分隔符"
            f"（frontmatter 未闭合，或首行分隔符其实是正文里的水平线）"
        ], 1

    data, errors = _parse_frontmatter_block(lines[1:end], offset=2)
    return data, errors, 1


def check_c11_frontmatter(chk: Checker, manifests: dict) -> None:
    """C11 agent MD 的 frontmatter 必须结构合法、字段齐备，且与 manifest 自洽。

    动机见模块文档字符串「C11 的动机与解析范围」。要点：C1–C10 没有任何一条
    读过 agent MD 的内容结构，frontmatter 损坏会让宿主静默地加载不了该代理，
    而全部 manifest 校验依旧全绿。
    """
    chk.section("C11 agent frontmatter 结构有效性")
    data = manifests.get("WorkBuddy") or manifests.get("Claude Code")
    if not data:
        chk.fail("C11 跳过：无可用 manifest")
        return

    entries = data.get("agents") or []
    if not entries:
        chk.fail("C11 跳过：manifest 未声明任何 agent")
        return

    members = {m.get("id"): m for m in (data.get("members") or [])}

    for entry in entries:
        target = chk.rel(entry)
        rel = Path(str(entry)).as_posix()
        if not target.is_file():
            chk.fail(f"{rel} 不存在，无法校验 frontmatter")
            continue

        fm, errors, _ = parse_frontmatter(target.read_text(encoding="utf-8"))
        if errors:
            chk.fail(
                f"{rel} frontmatter 结构非法：\n"
                + "\n".join(f"       - {e}" for e in errors)
            )
            continue

        problems: list[str] = []

        missing = [k for k in FRONTMATTER_REQUIRED if not str(fm.get(k) or "").strip()]
        if missing:
            problems.append(f"缺少必需字段或值为空: {missing}")

        stem = target.stem
        declared = str(fm.get("name") or "").strip()
        if declared and declared != stem:
            problems.append(
                f"frontmatter name=`{declared}` 与文件名 `{stem}` 不一致"
                f"（宿主按 name 注册代理，文件被改名会导致引用失效）"
            )

        desc = str(fm.get("description") or "").strip()
        if desc and len(desc) < FRONTMATTER_MIN_DESCRIPTION:
            problems.append(
                f"description 过短（{len(desc)} 字符 < {FRONTMATTER_MIN_DESCRIPTION}），"
                f"宿主难以据此判断何时启用该代理"
            )

        member = members.get(stem)
        if member:
            for field in FRONTMATTER_CROSSCHECK_FIELDS:
                md_val, man_val = fm.get(field), member.get(field)
                if isinstance(md_val, dict) and isinstance(man_val, dict):
                    md_norm = {str(k): str(v) for k, v in md_val.items()}
                    man_norm = {str(k): str(v) for k, v in man_val.items()}
                    if md_norm != man_norm:
                        problems.append(
                            f"{field} 与 manifest members[].{field} 不一致："
                            f"MD={json.dumps(md_norm, ensure_ascii=False)} "
                            f"manifest={json.dumps(man_norm, ensure_ascii=False)}"
                        )

        if problems:
            chk.fail(
                f"{rel} frontmatter 校验未通过：\n"
                + "\n".join(f"       - {p}" for p in problems)
            )
        else:
            chk.ok(f"{rel} frontmatter 合法（name={declared}, description {len(desc)} 字符）")


def check_c12_settings(chk: Checker, manifests: dict) -> None:
    """C12 Team 型包根 settings.json 存在且指向主理人。

    动机：官方 validate_expert.py 对 Team 型包硬性要求包根 settings.json
    （报错原文「Team type must have settings.json」）。v2.1.2 后曾依
    「宿主启动时必然删除该文件」的假设将其移除，导致官方校验器报 1 error；
    反证：同类 Team 包 agent-harness-expert 的同格式 settings.json 存活数周。
    本检查把「settings.json 必须在」固化为发行门禁，防止再次被误删。
    """
    chk.section("C12 Team 型包根 settings.json")
    codebuddy = manifests.get("WorkBuddy")
    if codebuddy and codebuddy.get("expertType") != "team":
        chk.ok("非 Team 型包，C12 不适用")
        return
    path = chk.root / "settings.json"
    if not path.exists():
        chk.fail("包根缺 settings.json（官方 validate_expert 对 Team 型为硬要求）")
        return
    data = chk.load_json(path)
    if data is None:
        chk.fail("settings.json JSON 非法")
        return
    agent = data.get("agent")
    lead = None
    if codebuddy:
        lead = codebuddy.get("agentName") or codebuddy.get("teamInfo", {}).get("leadAgent")
    if not agent or not isinstance(agent, str):
        chk.fail("settings.json 缺非空字符串字段 agent")
        return
    if lead and agent != lead:
        chk.fail(f"settings.json agent={agent} 与 manifest 主理人 agentName={lead} 不一致")
        return
    chk.ok(f"settings.json 合法（agent={agent}）")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="专家包一致性校验：manifest 对等 / 资产完整性 / 版本一致 / 废弃表述",
    )
    parser.add_argument("--root", default=None, help="仓库根目录（默认取脚本上级目录）")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出每个通过项")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not (root / CLAUDE_MANIFEST).exists() and not (root / CODEBUDDY_MANIFEST).exists():
        print(f"❌ 仓库根下未找到任何 manifest，请检查 --root：{root}")
        return 2

    print("=" * 72)
    print(f"专家包一致性校验  仓库根: {root}")
    print("=" * 72)

    chk = Checker(root, verbose=args.verbose)
    claude, codebuddy = check_c1_c2(chk)
    manifests = {"Claude Code": claude, "WorkBuddy": codebuddy}
    check_c3_agents(chk, manifests)
    check_c4_skills(chk, manifests)
    check_c5_avatars(chk, manifests)
    check_c6_team(chk, manifests)
    check_c7_version(chk, manifests)
    check_c8_forbidden(chk)
    check_c9_contracts(chk, manifests)
    check_c10_marketplace(chk, manifests)
    check_c11_frontmatter(chk, manifests)
    check_c12_settings(chk, manifests)

    print("\n" + "=" * 72)
    if chk.failures:
        print(f"❌ 校验失败：{len(chk.failures)} 项，通过 {chk.passed} 项")
        print("=" * 72)
        return 1
    print(f"✅ 全部通过：{chk.passed} 项")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
