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
    """C3 agents 数组引用的文件必须存在。"""
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
