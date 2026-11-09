#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""manifest_check.py 的注入式自测（负例套件）

## 为什么需要这个脚本

`manifest_check.py` 是「校验器」。但如果只测它的**正向**行为（干净仓库下 rc=0），
就无法区分「它真的在检查」与「它只是永远返回 0」。这正是本项目历史上踩过的坑：
CI 的术语清单写成了精确串，导致真实存在的违规因插入词而漏检，形成**假绿**。

本脚本用**注入式负例**证明校验器仍然有效：每一条都先把仓库复制到临时目录、
故意破坏一处、然后断言：

  1. 校验器退出码为 1（硬失败，而不是 rc=0 放行）
  2. 输出中命中**预期的检查项文案**（而不是碰巧因为别的原因失败）

条件 2 很重要 —— 只断言退出码会让「任何错误都算通过」，掩盖检查项本身的失效。

## 用例分组

  A 组（N1–N8）  manifest / 资产 / 版本 / 术语
  B 组（N9–N11） 契约章节（C9）
  C 组（N12–N17）市场清单（C10）
  D 组（N18–N19）Team 型 settings.json（C12）
  E 组（N20–N21）旧团队规模表述（C8 规则扩充）
  F 组（N22–N23）C8 声明式豁免（负例拦截 / 正例护栏）
  G 组（N24–N26）成员 ID 集合一致性（C13）

其中 N11 是**反向用例**：破坏一种契约标记但保留另一种，期望校验器**放行**（rc=0），
用于确认 C9 接受三种等价命名，而不是只认一种。
N23 同为**正向用例**：注入带豁免标记的审计文档，期望 rc=0 且 C8 汇总出现豁免计数，
用于确认「带标记放行」没有退化成「什么都不扫」。

## 用法

  python3 scripts/manifest_check_selftest.py          # 全部用例
  python3 scripts/manifest_check_selftest.py -k N12   # 只跑名字含 N12 的用例

## 退出码

  0 = 全部用例行为符合预期
  1 = 存在不符合预期的用例（校验器可能已退化）
  2 = 环境错误（找不到仓库根 / manifest_check.py）

## 依赖

仅标准库，Python >= 3.9。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "scripts" / "manifest_check.py"
COPY_EXCLUDE = {".git", "__pycache__", ".backups"}

# 每个用例：(编号, 说明, 期望命中的输出片段, 期望退出码, 破坏函数)
CASES = []


def case(cid, desc, expect, mutate, expect_rc=1):
    CASES.append((cid, desc, expect, expect_rc, mutate))


def _mutate_manifest(root: Path, manifest: str, **fields):
    """读写 plugin.json 的辅助函数，保持用例定义简短。"""
    path = root / manifest
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in fields.items():
        data[key] = value
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── A 组：manifest / 资产 / 版本 / 术语 ──────────────────────────────────────
def n1(root):
    _mutate_manifest(root, ".codebuddy-plugin/plugin.json", version="9.9.9")
case("N1", "双 manifest 版本漂移", "字段不一致: version", n1)


def n2(root):
    # 2026-09-30 教训：replace 若找不到目标串会静默空转（displayDescription 文案
    # 曾从「五级冲突仲裁」改为「五级仲裁」，第三次踩精确串匹配脆弱的坑）。
    # 改为 append 式注入：无论现文案如何，都保证出现废弃表述 → 校验器必被触发。
    path = root / ".codebuddy-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["displayDescription"]["zh"] = data["displayDescription"]["zh"] + "（旧三级仲裁遗留）"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N2", "废弃术语回归（旧仲裁层级表述）", "旧仲裁层级表述", n2)


def n3(root):
    (root / "avatars/team.png").unlink()
case("N3", "头像文件缺失", "头像缺失", n3)


def n4(root):
    version = json.loads(
        (root / ".codebuddy-plugin/plugin.json").read_text(encoding="utf-8")
    )["version"]
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    assert f"> **版本**：{version}" in text, "基准副本中未找到 README 版本行"
    path.write_text(
        text.replace(f"> **版本**：{version}", "> **版本**：1.0.0"), encoding="utf-8"
    )
case("N4", "README 版本漂移", "与 manifest version", n4)


def n5(root):
    _mutate_manifest(root, ".codebuddy-plugin/plugin.json", skills="./no-such-dir")
case("N5", "skills 指向不存在的目录", "skills 指向的目录不存在", n5)


def n6(root):
    path = root / ".codebuddy-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["teamInfo"]["leadAgent"] = "nobody"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N6", "leadAgent 不在 agents 中", "leadAgent 不在 agents 列表中", n6)


def n7(root):
    path = root / ".codebuddy-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["agents"][0] = "./agents/nope.md"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N7", "agent 文件不存在", "不存在: ./agents/nope.md", n7)


def n8(root):
    path = root / ".claude-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["author"]["email"] = "someone@example.com"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N8", "占位邮箱回归", "占位邮箱", n8)


# ── B 组：契约章节（C9）────────────────────────────────────────────────────
def n9(root):
    path = root / "agents/synthesis-integrator.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("## 接口契约", "## 随便什么标题"),
        encoding="utf-8",
    )
case("N9", "整合者契约章节被移除", "synthesis-integrator 未找到契约章节", n9)


def n10(root):
    """v2.1.0 起：domain-expert 拆为 3 个 atomic（biomed/ai/general）。
    测试契约章节被改名时，仍选一个存在的 atomic 验证 C9 漏报。"""
    path = root / "agents/domain-expert-biomed.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("## v2.1.0 协议合规契约", "## 无关章节"),
        encoding="utf-8",
    )
case("N10", "atomic 成员契约章节被改名", "domain-expert-biomed 未找到契约章节", n10)


def n11(root):
    """反向用例：抹掉一种契约标记但补上另一种，C9 应放行。"""
    path = root / "agents/socratic-questioner.md"
    text = path.read_text(encoding="utf-8").replace("协议合规契约", "协议合规约定")
    path.write_text(text + "\n<!-- 接口契约 -->\n", encoding="utf-8")
case("N11", "契约标记换用等价命名（应放行）", "契约章节: 接口契约", n11, expect_rc=0)


# ── C 组：市场清单（C10）──────────────────────────────────────────────────
def n12(root):
    (root / ".claude-plugin/marketplace.json").unlink()
case("N12", "Claude 侧市场文件缺失", "市场文件缺失", n12)


def n13(root):
    (root / ".codebuddy-plugin/marketplace.json").unlink()
case("N13", "WorkBuddy 侧市场文件缺失", "市场文件缺失", n13)


def n14(root):
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"][0]["name"] = "some-other-plugin"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N14", "市场未收录本插件", "未收录本插件", n14)


def n15(root):
    path = root / ".codebuddy-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"][0]["source"] = "./plugins/nope"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N15", "市场 source 无法解析", "source 无法解析", n15)


def n16(root):
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["name"] = "inconsistent-name"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N16", "两份市场名不一致", "两份市场名不一致", n16)


def n17(root):
    (root / ".claude-plugin/marketplace.json").write_text("{ not json", encoding="utf-8")
case("N17", "市场文件 JSON 非法", "市场文件 JSON 非法", n17)


# ── D 组：Team 型 settings.json（C12）────────────────────────────────────
def n18(root):
    (root / "settings.json").unlink()
case("N18", "Team 型包根 settings.json 被删", "包根缺 settings.json", n18)


def n19(root):
    (root / "settings.json").write_text(
        json.dumps({"agent": "wrong-lead-id"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
case("N19", "settings.json agent 与主理人不一致", "与 manifest 主理人", n19)


# ── E 组：旧团队规模表述（v2.2.0 C8 新增规则）────────────────────────────
def n20(root):
    # append 式注入：与 N2 同法，保证无论现文案如何都出现旧规模表述。
    # 用「六人编排团」而非裸「六人」，验证新规则不会误伤 README 版本史里的
    # 「v2.0.0 六人团队」这类合法历史描述。
    path = root / ".codebuddy-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["displayDescription"]["zh"] = data["displayDescription"]["zh"] + "（旧六人编排团遗留）"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N20", "旧团队规模表述回归（六人编排团）", "旧团队规模表述", n20)


def n21(root):
    # 注入到隐藏目录下的 .claude-plugin/marketplace.json：验证 C8 的 rglob
    # 扫描确实覆盖市场清单，防止「用户可见描述」成为护栏盲区。
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"][0]["description"] = (
        data["plugins"][0]["description"] + " (legacy Six-agent build)"
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
case("N21", "marketplace.json 旧 Six-agent 规模表述回归", "旧团队规模表述", n21)


# ── F 组：C8 声明式豁免（N22 负例 / N23 正例护栏）──────────────────────────
# 负例注入的废弃词用运行时拼接构造：避免本文件源码里出现连续字面量被 C8 自检
# 扫到（自指假红）。拼接结果命中 C8「旧状态机表述」规则，形态单一、不误伤其它规则。
_C8_LEGACY_TERM = "六" + "阶段"
_C8_EXEMPT_MARKER = "<!-- c8-exempt: audit-history -->"


def _inject_audit_md(root: Path, with_marker: bool) -> None:
    """在临时副本 docs/ 下注入一份审计类 md，并断言注入真的落盘。

    锚点错配 / 路径写错会静默 no-op，负例会「什么都没注入却仍按预期失败」形成假绿，
    因此每条注入后都回读文件，校验废弃词与豁免标记的实际存在状态。
    """
    docs = root / "docs"
    # 副本通常已含 docs/，仅在缺失时才建目录：某些宿主沙箱的 Path.mkdir 会对
    # 已存在目录抛 FileExistsError（即使 exist_ok=True），能不调用就不调用。
    if not docs.is_dir():
        docs.mkdir(parents=True, exist_ok=True)
    path = docs / "c8-audit-injected.md"
    lines = []
    if with_marker:
        lines.append(_C8_EXEMPT_MARKER)
    lines += ["# C8 注入用例", "复述历史失败模式术语：" + _C8_LEGACY_TERM]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written = path.read_text(encoding="utf-8")
    assert _C8_LEGACY_TERM in written, f"{path.name}: 废弃词未落盘"
    assert (_C8_EXEMPT_MARKER in written) is with_marker, f"{path.name}: 豁免标记落盘状态不符"


def n22(root):
    _inject_audit_md(root, with_marker=False)
case("N22", "未标记审计文档含废弃表述（应拦截）", "旧状态机表述", n22)


def n23(root):
    _inject_audit_md(root, with_marker=True)
# 正向护栏：不仅断言 rc=0，还断言 C8 汇总里出现「声明式豁免文件」计数，
# 证明文件是「被标记豁免」而非「压根没进扫描」。
case("N23", "带声明式豁免标记的审计文档（应放行且计数）", "声明式豁免文件", n23, expect_rc=0)


# ── G 组：成员 ID 集合一致性（C13）────────────────────────────────────────
# 注入纪律（本项目反复踩坑的点，务必照做）：
#   1. 锚点唯一命中 —— 改之前先断言锚点串在文件中只出现一次，否则用例报错退出。
#      锚点改错位置会造成「注入无效但测试仍绿」的假绿。
#   2. 替换后落盘校验 —— 替换完重新读文件，断言旧串已消失、新串已出现。
#
# 成员 ID 不写死成字面量：探针 ID 一律从 agents/*.md 文件名集合里动态取出，
# 避免脚本里出现一份「手抄的成员名单」——那份名单本身就是漂移的来源。

C13_PROTOCOL_REL = "skills/research-orchestration-workflow/references/agent-protocol.md"
C13_REGISTRY_REL = "skills/research-orchestration-workflow/references/agent-registry.md"
C13_CODEBUDDY_MANIFEST = ".codebuddy-plugin/plugin.json"


def _c13_truth_ids(root: Path) -> list[str]:
    """从 agents/*.md 文件名取成员 ID 真值源（与 C13 校验器同源）。"""
    return sorted(p.stem for p in (root / "agents").glob("*.md") if p.is_file())


def _c13_replace_once(path: Path, old: str, new: str) -> None:
    """唯一命中替换 + 落盘校验；锚点不唯一或替换未生效都直接断言失败。"""
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (
        f"锚点在 {path.name} 中出现 {text.count(old)} 次（应恰为 1 次），"
        "拒绝注入以防改错位置造成假绿"
    )
    path.write_text(text.replace(old, new), encoding="utf-8")
    written = path.read_text(encoding="utf-8")
    assert old not in written, f"{path.name}: 旧锚点未消失"
    assert new in written, f"{path.name}: 新锚点未落盘"


def _c13_pick_probe(root: Path) -> str:
    """从真值源里挑一个非主理人的成员 ID 作为注入探针。

    「谁是主理人」不靠成员 ID 字面量判断，而是读 manifest 的 members[].role
    字段（role == "lead" 即主理人）—— 探针本身仍从 agents/*.md 文件名集合取，
    脚本里不出现任何手抄的成员名单。
    """
    manifest = root / C13_CODEBUDDY_MANIFEST
    data = json.loads(manifest.read_text(encoding="utf-8"))
    lead_ids = {
        m.get("id") for m in (data.get("members") or [])
        if isinstance(m, dict) and m.get("role") == "lead"
    }
    truth = set(_c13_truth_ids(root))
    candidates = [i for i in truth if i not in lead_ids]
    assert candidates, "真值源里找不到非主理人的探针成员 ID"
    return sorted(candidates)[0]


def n24(root):
    """协议 §1 角色矩阵：删掉一行里的一个成员 ID。

    探针取「角色矩阵里成员 ID 列含多个 <br> 分隔 ID」的数据行，删掉其中一个 ID
    后该行少一个成员 → 与真值源集合不等 → C13 必须报出「缺少」。
    """
    path = root / C13_PROTOCOL_REL
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 限定在 §1 小节内（到下一个「## 」为止），避免误收协议其它章节的表格
    body: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## 1. 角色矩阵"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)

    truth = set(_c13_truth_ids(root))
    target_line = None
    for line in body:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cells) < 2:
            continue
        if set(cells[0]) <= set("-: "):       # 分隔行
            continue
        ids = re.findall(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", cells[1])
        if len(ids) >= 2 and all(i in truth for i in ids):
            target_line = line
            break
    assert target_line is not None, "协议 §1 里找不到含多个成员 ID 的数据行"

    cells = [c.strip() for c in target_line.strip().split("|")[1:-1]]
    ids = re.findall(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", cells[1])
    # 删掉第一个 ID，保留其余 ID 及其 <br> 分隔结构
    new_cell = "<br>".join(f"`{i}`" for i in ids[1:])
    old_cell = cells[1]
    assert old_cell != new_cell, "目标单元格重建后与原值相同"

    # 锚点用整行：整行在全文中唯一（断言后 replace 才安全）
    assert text.count(target_line) == 1, (
        f"协议 §1 目标行在全文出现 {text.count(target_line)} 次（应恰为 1 次），"
        "拒绝注入以防改错位置造成假绿"
    )
    new_line = target_line.replace(old_cell, new_cell, 1)
    assert new_line != target_line, "目标行重建后与原值相同"

    path.write_text(text.replace(target_line, new_line), encoding="utf-8")
    written = path.read_text(encoding="utf-8")
    assert target_line not in written, "协议 §1 旧行未消失"
    assert new_line in written, "协议 §1 新行未落盘"


case("N24", "协议 §1 角色矩阵少一个成员 ID", "C13 成员 ID 集合不一致", n24)


def n25(root):
    """registry 团队成员一览：把某一行的 agent_id 改成一个不存在的 ID。

    探针取真值源里第一个成员 ID，用它定位 registry 里的那一行并改写。
    """
    path = root / C13_REGISTRY_REL
    probe = _c13_pick_probe(root)
    old_row = f"| `{probe}` |"
    assert path.read_text(encoding="utf-8").count(old_row) == 1, (
        f"registry 里的探针行不唯一: {old_row!r}"
    )
    # 伪造一个不存在的成员 ID（运行时拼接，非手抄成员名单）
    ghost = "nonexistent-" + "agent"
    new_row = f"| `{ghost}` |"
    _c13_replace_once(path, old_row, new_row)


case("N25", "registry 团队成员一览出现不存在的成员 ID", "C13 成员 ID 集合不一致", n25)


def n26(root):
    """WorkBuddy manifest：members[] 里删掉一个成员。"""
    path = root / C13_CODEBUDDY_MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    members = data.get("members") or []
    assert len(members) >= 2, "members[] 成员不足，无法构造删除用例"
    # 探针成员 ID 从真值源取（不写死字面量），且必须是 lead 之外的那一个
    truth = set(_c13_truth_ids(root))
    victim = None
    for member in members:
        mid = member.get("id")
        if mid in truth and member.get("role") != "lead":
            victim = mid
            break
    assert victim is not None, "members[] 里找不到可删除的非 lead 成员"

    data["members"] = [m for m in members if m.get("id") != victim]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    written = json.loads(path.read_text(encoding="utf-8"))
    written_ids = [m.get("id") for m in (written.get("members") or [])]
    assert victim not in written_ids, "members[] 删除未落盘"
    assert len(written_ids) == len(members) - 1, "members[] 删除数量不符"


case("N26", "WorkBuddy manifest members[] 少一个成员", "C13 成员 ID 集合不一致", n26)


# ── H 组：C8 规则覆盖矩阵补全（N27–N29，R2 新增）──────────────────────────
# R2 审计实锤：FORBIDDEN_PATTERNS 13 条规则中仅 5 条被 N2/N8/N20/N21/N22 覆盖，
# 其余规则的正则一旦被误改（退化），没有任何负例会红。N27 一次性覆盖全部
# 缺口规则；N28/N29 补 C13 三个无负例分支（声明位互换 / 重复 ID / 目录删除）。
# 注入文本全部运行时拼接：本文件虽在 SCAN_EXEMPT 白名单，仍守「不在源码里
# 写连续废弃字面量」的纪律（避免未来有人移白名单时自指假红）。


def n27(root):
    """一条临时 .md 同时写入 7 条无负例规则的违规文本，断言每条规则的
    desc 全部命中。运行时拼接规则锚点：期望命中的 desc 清单与 C8 规则表
    的 desc 字段逐字同步——desc 改名时本用例前置断言会失败（防漂移）。"""
    # 运行时拼接违规文本（不出现连续字面量）
    legacy_terms = [
        ("Six" + "-role",                 "旧英文角色数表述（现为 Eight-agent）"),
        ("six-role" + " research",        "旧英文角色数表述（现为 Eight-agent）"),
        ("L1-L3" + " " + "conflict",      "旧仲裁层级范围（现为 L1-L5）"),
        ("msg" + "_" + "type",            "旧信封字段名（现为 type）"),
        ("任意一维" + "<90",              "旧 FREEZE 量纲表述（现为完整度 0-100% + 风险维 0-10）"),
        ("五项" + "核心任务",             "v1 遗留任务模型（现为三大任务 + 八阶段状态机）"),
        ("5" + "-task",                   "v1 遗留任务模型（现为三大任务 + 八阶段状态机）"),
    ]
    docs = root / "docs"
    if not docs.is_dir():
        docs.mkdir(parents=True, exist_ok=True)
    path = docs / "c8-matrix-injected.md"
    lines = ["# C8 规则矩阵负例（R2 N27）"]
    for term, _desc in legacy_terms:
        lines.append(f"历史表述复述：{term}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written = path.read_text(encoding="utf-8")
    for term, _desc in legacy_terms:
        assert term in written, f"N27 前置断言失败：{term!r} 未落盘"


case("N27", "C8 七条缺口规则批量回归（Six-role/L1-L3/msg_type/量纲/v1 模型）",
     "残留废弃表述", n27)


def n28(root):
    """C13 主理人声明位互换攻击：lead 的 role 改 member + 普通成员改 lead
    （leadAgent 字段不动）。断言「leadAgent 与主理人声明位不一致」判红。"""
    path = root / C13_CODEBUDDY_MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    lead_id = data["teamInfo"]["leadAgent"]
    victim = None
    for m in data.get("members") or []:
        if m.get("id") != lead_id:
            victim = m.get("id")
            break
    assert victim, "N28 前置断言失败：找不到非 lead 成员"
    for m in data["members"]:
        if m.get("id") == lead_id:
            m["role"] = "member"
        elif m.get("id") == victim:
            m["role"] = "lead"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    written = json.loads(path.read_text(encoding="utf-8"))
    roles = {m.get("id"): m.get("role") for m in written.get("members") or []}
    assert roles.get(lead_id) == "member" and roles.get(victim) == "lead", \
        "N28 前置断言失败：角色互换未落盘"


case("N28", "C13 leadAgent 与主理人声明位不一致（角色互换）",
     "主理人声明位不一致", n28)


def n29(root):
    """C13 单元格内成员 ID 重复：协议 §1 多 ID 单元格把首个 ID 重复一次。
    断言「成员 ID 重复出现」判红（duplicates 分支从未有负例）。"""
    path = root / C13_PROTOCOL_REL
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_sec = False
    target = None
    for line in lines:
        if line.startswith("## 1. 角色矩阵"):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if in_sec and line.startswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 2:
                ids = re.findall(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", cells[1])
                if len(ids) >= 2:
                    target = (line, cells, ids)
                    break
    assert target, "N29 前置断言失败：协议 §1 无多 ID 单元格"
    line, cells, ids = target
    dup_cell = "<br>".join(f"`{i}`" for i in [ids[0]] + ids)
    assert text.count(line) == 1, "N29 锚点行不唯一"
    new_line = line.replace(cells[1], dup_cell, 1)
    path.write_text(text.replace(line, new_line), encoding="utf-8")
    written = path.read_text(encoding="utf-8")
    assert line not in written and new_line in written, "N29 注入未落盘"


case("N29", "C13 单元格内成员 ID 重复出现（duplicates 分支）",
     "成员 ID 重复出现", n29)


def n30(root):
    """C13 真值源目录整体删除（fail-closed 路径）。
    断言「真值源目录不存在」判红。"""
    shutil.rmtree(root / "agents")
    assert not (root / "agents").exists(), "N30 前置断言失败：agents/ 未删除"


case("N30", "C13 agents/ 目录整体删除（fail-closed）",
     "C13 真值源目录不存在", n30)


def make_copy(src: Path, dst: Path) -> None:
    shutil.copytree(
        src, dst, symlinks=True,
        ignore=lambda _d, names: [n for n in names if n in COPY_EXCLUDE],
    )


def run_case(pristine: Path, workdir: Path, cid, desc, expect, expect_rc, mutate):
    case_dir = workdir / cid
    if case_dir.exists():
        shutil.rmtree(case_dir)
    make_copy(pristine, case_dir)
    try:
        mutate(case_dir)
    except AssertionError as exc:
        print(f"  ⚠️  {cid} {desc}: 用例本身前置断言失败 —— {exc}")
        return False

    proc = subprocess.run(
        [sys.executable, str(case_dir / "scripts" / "manifest_check.py"), "-v"],
        capture_output=True, text=True,
    )
    hit = expect in proc.stdout
    ok = proc.returncode == expect_rc and hit
    mark = "✅" if ok else "❌"
    print(
        f"  {mark} {cid} {desc}: rc={proc.returncode}（期望 {expect_rc}）"
        f" 命中预期='{expect}' → {hit}"
    )
    if not ok:
        for line in proc.stdout.splitlines():
            if "❌" in line or "✅" in line:
                print("       ", line.strip())
    shutil.rmtree(case_dir, ignore_errors=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="manifest_check.py 注入式负例自测")
    parser.add_argument("-k", "--filter", default=None, help="只跑编号/说明含该子串的用例")
    args = parser.parse_args()

    if not CHECKER.is_file():
        print(f"❌ 找不到校验器: {CHECKER}")
        return 2
    if not (REPO_ROOT / ".claude-plugin/plugin.json").is_file():
        print(f"❌ 仓库根定位有误（无 manifest）: {REPO_ROOT}")
        return 2

    selected = [c for c in CASES if not args.filter or args.filter.lower() in c[0].lower()
                or args.filter.lower() in c[1].lower()]
    if not selected:
        print(f"❌ 无匹配用例: {args.filter}")
        return 2

    print("=" * 72)
    print(f"manifest_check 注入式自测  仓库根: {REPO_ROOT}")
    print(f"用例数: {len(selected)}")
    print("=" * 72)

    failures = 0
    with tempfile.TemporaryDirectory(prefix="rot-selftest-") as tmp:
        tmp_path = Path(tmp)
        pristine = tmp_path / "pristine"
        print("\n准备基准副本…")
        make_copy(REPO_ROOT, pristine)

        for cid, desc, expect, expect_rc, mutate in selected:
            if not run_case(pristine, tmp_path, cid, desc, expect, expect_rc, mutate):
                failures += 1

    print("\n" + "=" * 72)
    if failures:
        print(f"❌ 自测未通过：{failures}/{len(selected)} 条行为不符合预期")
        print("   提示：校验器可能已退化，或某条检查项的文案被改动。")
        print("=" * 72)
        return 1
    print(f"✅ 自测通过：{len(selected)}/{len(selected)} 条行为均符合预期")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
