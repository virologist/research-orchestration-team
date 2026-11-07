#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""routing_eval.py 的注入式自测（mutation-based 负例 + 1 条正向）

## 为什么需要这个脚本（与 manifest_check_selftest.py 同一思路）

只测「干净仓库下 routing_eval.py 返回 0」无法区分「它真的在检查」与「它永远返回 0」。
本脚本把**整个包**复制到 tempfile 临时目录，故意破坏副本的单一处，然后断言：

  1. `python3 routing_eval.py --root <case_dir>` 退出码为 1（硬失败，不是放行）
  2. 输出命中**预期检查项文案**（而不是碰巧因为别的原因失败）

## 为什么用「自愈基准副本」以及 raw_probe 护栏

归一化（sanitize_pristine）会重写 tools 行、给 description 追加触发词，这本身会
「修好」真实仓库里的 R2 / R4 缺陷。历史缺陷（对抗实验 B1/B2p）：若真实仓库本就
存在这类路由不一致，selftest 仍会先把它修好再跑负例，得到 10/10 PASS —— 等于用
自愈夹具掩盖真实缺陷，而直跑 `routing_eval.py --root <副本>` 其实是 rc=1。

因此准备阶段分两步，且顺序不可颠倒：

  1. **raw_probe（准备阶段护栏，不计入 CASES 用例数）**：复制出的**原始未归一化
     副本**直接跑 `routing_eval.py --root <raw_copy>`，要求 rc=0。若 rc≠0，说明
     真实仓库存在路由不一致，selftest 打印「拒绝用自愈夹具掩盖」并 return 1，
     不再跑任何负例。
  2. **归一化（仅用于负例基准）**：仅在 raw_probe 通过后，才把副本归一为
     R1-R5 已知全绿（见 sanitize_pristine），再注入单一破坏。归一化后的副本
     **仅用于证明校验器逻辑**，输出显式标注「不代表真实仓库合规」。

本自测要证明的是「校验器能否捕获被注入的破坏」；真实仓库是否合规由第 1 步
raw_probe 保证，而非被夹具掩盖。归一化只动 tools 行内容与 description 文案，
不动成员集合 / 表格 / 条目标题 / plugin.json，故不影响 R1 / R3 负例。

## 用例

  P1 正向：归一化基准副本 → rc=0（并断言汇总 PASS 文案）
  N1 删除某个成员 MD                       → R1 命中「成员集合」
  N2 删掉某 description 的前 3 个触发词     → R2 命中「关键触发词」
  N3 删除 registry 一条 `**routing**:` 行   → R3 命中「结构完整」
  N4 删除 Loop 表 max_turns 行              → R3 命中「结构完整」（Loop 子检查）
  N5 tools 行塞入裸词「政策文件库」         → R4 命中「工具名」
  N6 tools 行塞入空后缀 `mcp__`             → R4 命中「工具名」（mcp__ 后缀非空子检查）
  N7 删除整个 `### moderate` 权限档章节     → R3 命中「权限档」（按章节标题判定）
  N8 在 atomic MD description 注入伪造 mcp__GHOST_TOOL → R5 命中 `extra=`
  N9 在 atomic MD description 注入裸词「政策文件库」   → R5 命中「疑似非工具名裸词」

## 用例数

  共 10 条：1 条正向（P1）+ 9 条负例（N1~N9）。raw_probe 为准备阶段护栏，不计入用例数。
  N8 证明解析器认 `mcp__` 前缀（②）；N9 证明解析器认不带反引号 / 不带前缀的
  非工具名裸词（④），两条合起来防止 R5 的「无 token → PASS」分支退化成永久放行。
  裸词 WebFetch（③内置工具裸词）由交付时的破坏验证单独覆盖。

## 用法

  python3 scripts/routing_eval_selftest.py                    # 全部用例
  python3 scripts/routing_eval_selftest.py -k N5             # 只跑编号/说明含该子串的用例
  python3 scripts/routing_eval_selftest.py --root <dir>      # 指定被复制的源仓库根（对抗验证用）

## 退出码

  0 = 全部用例行为符合预期
  1 = 存在不符合预期的用例（校验器可能已退化）、基准副本无法归一，
      或 raw_probe 发现真实仓库路由不一致（拒绝用自愈夹具掩盖）
  2 = 环境错误（找不到源仓库根 / routing_eval.py / 无匹配用例）

## 依赖

仅标准库，Python >= 3.10。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_REL = Path("scripts") / "routing_eval.py"
REGISTRY_REL = "skills/research-orchestration-workflow/references/agent-registry.md"
COPY_EXCLUDE = {".git", "__pycache__", ".backups"}

# 与 routing_eval.py 保持一致的最小判定逻辑（自测保持独立，不 import 校验器）
BUILTIN_TOOLS = frozenset({
    "WebFetch", "WebSearch", "Read", "Grep", "Glob",
    "Write", "Edit", "Bash", "Agent", "Skill",
})
MCP_PREFIX = "mcp__"

# 每个用例：(编号, 说明, 期望命中的输出片段, 期望退出码, 破坏函数)
CASES: list[tuple] = []


def case(cid, desc, expect, mutate, expect_rc=1):
    CASES.append((cid, desc, expect, expect_rc, mutate))


# ── 基准副本归一化：把副本变成「R1-R5 已知全绿」────────────────────────────
def _tool_ok(token: str) -> bool:
    return token in BUILTIN_TOOLS or (token.startswith(MCP_PREFIX) and len(token) > len(MCP_PREFIX))


def _parse_entries_mini(lines: list[str]) -> dict[str, list[str]]:
    """只取「触发条件」section 下每个条目的 trigger 关键词（与校验器同源）。"""
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith("## ") and "触发条件" in ln), 0
    )
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
    )
    heads = []
    for i in range(start, end):
        m = re.match(r"^###\s+([A-Za-z0-9_-]+)（", lines[i])
        if m:
            heads.append((m.group(1), i))
    out: dict[str, list[str]] = {}
    for idx, (aid, h) in enumerate(heads):
        e = heads[idx + 1][1] if idx + 1 < len(heads) else end
        for j in range(h + 1, e):
            if "**trigger**:" in lines[j]:
                body = lines[j].split("**trigger**:", 1)[1]
                out[aid] = [s.strip() for s in re.split(r"\s*/\s*|、", body) if s.strip()]
                break
    return out


def _append_keywords(text: str, words: list[str]) -> str:
    """把 words 追加进 frontmatter 的 description 值（兼容单行引号与多行兜底），
    使校验器 R2 的前 3 触发词必然命中。
    """
    lines = text.splitlines(keepends=True)
    fm_end = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    d = next(
        (i for i in range(1, fm_end) if re.match(r"^description\s*:", lines[i])), None
    )
    if d is None:
        return text
    raw = lines[d].rstrip("\r\n")
    newline = lines[d][len(raw):]
    suffix = " " + "、".join(words)
    m = re.match(r'^(\s*description\s*:\s*")(.*)("\s*)$', raw)
    if m:
        lines[d] = m.group(1) + m.group(2) + suffix + m.group(3) + newline
    else:
        lines[d] = raw + suffix + newline  # 兜底：非引号格式则行尾追加
    return "".join(lines)


def sanitize_pristine(root: Path) -> None:
    """把基准副本归一为 R1-R5 全绿：只修「命名形态」与「触发词覆盖」两处噪声。"""
    reg = root / REGISTRY_REL
    lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)

    # ① R4：每条 **tools**: 行重写为只保留合法反引号工具名，去掉「政策文件库」等裸词
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*-\s*\*\*tools\*\*:\s*)(.*?)(\r?\n)?$", ln)
        if not m:
            continue
        prefix, body, newline = m.group(1), m.group(2), m.group(3) or ""
        ticks = [t.strip() for t in re.findall(r"`([^`]+)`", body) if t.strip()]
        legal = [t for t in ticks if _tool_ok(t)]
        lines[i] = prefix + " / ".join(f"`{t}`" for t in legal) + newline
    reg.write_text("".join(lines), encoding="utf-8")

    # ② R2：把每个条目的前 3 个触发词补进对应成员 MD 的 description
    entries = _parse_entries_mini(reg.read_text(encoding="utf-8").splitlines())
    for aid, kws in entries.items():
        words = kws[:3]
        if not words:
            continue
        md = root / "agents" / f"{aid}.md"
        if not md.is_file():
            continue
        md.write_text(_append_keywords(md.read_text(encoding="utf-8"), words), encoding="utf-8")


# ── 破坏函数（每条只破坏一处）──────────────────────────────────────────────
def p1(root):
    """正向：自愈基准副本不做任何破坏。"""
    pass


def n1(root):
    """删除一个成员 MD → agents/*.md 集合缺员 → R1 三方差集。"""
    path = root / "agents" / "socratic-questioner.md"
    assert path.is_file(), "基准副本缺 socratic-questioner.md"
    path.unlink()


def n2(root):
    """删掉 domain-expert-general 的 description 里前 3 个关键触发词（删全 3 个，
    覆盖关键词解析的细微差异，确保稳定触发 R2）。"""
    reg = (root / REGISTRY_REL).read_text(encoding="utf-8")
    words = _parse_entries_mini(reg.splitlines()).get("domain-expert-general", [])
    assert len(words) >= 3, "基准副本 registry 无 domain-expert-general 前 3 触发词"
    md = root / "agents" / "domain-expert-general.md"
    text = md.read_text(encoding="utf-8")
    for w in words[:3]:
        assert w in text, f"基准副本 description 缺触发词「{w}」"
        text = text.replace(w, "")
    md.write_text(text, encoding="utf-8")


def n3(root):
    """删除 registry 里第一条 `**routing**:` 行 → 某条目缺 routing → R3。"""
    reg = root / REGISTRY_REL
    lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if "**routing**:" in ln:
            del lines[i]
            break
    else:
        raise AssertionError("基准副本 registry 无 **routing**: 行")
    reg.write_text("".join(lines), encoding="utf-8")


def n4(root):
    """删除 Loop 硬停止表 max_turns 行 → R3 的 Loop 四行检查缺一行。"""
    reg = root / REGISTRY_REL
    lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if re.match(r"^\|\s*max_turns\s*\|", ln):
            del lines[i]
            break
    else:
        raise AssertionError("基准副本 Loop 表无 max_turns 行")
    reg.write_text("".join(lines), encoding="utf-8")


def _inject_tools(root: Path, extra: str) -> None:
    """往第一条 **tools**: 行行尾（换行前）追加一个槽位。"""
    reg = root / REGISTRY_REL
    lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if re.match(r"^\s*-\s*\*\*tools\*\*:", ln):
            raw = ln.rstrip("\r\n")
            newline = ln[len(raw):]
            lines[i] = raw + extra + newline
            break
    else:
        raise AssertionError("基准副本 registry 无 **tools**: 行")
    reg.write_text("".join(lines), encoding="utf-8")


def n5(root):
    """tools 行塞入非工具名裸词「政策文件库」→ R4 命名形态失败。"""
    _inject_tools(root, " / 政策文件库")


def n6(root):
    """tools 行塞入 `mcp__`（空后缀）→ R4 的 mcp__ 后缀非空检查失败。"""
    _inject_tools(root, f" / `{MCP_PREFIX}`")


def n7(root):
    """删除整个 `### moderate` 权限档章节（标题到下一个 ### / ## 标题前全部删掉）
    → R3 按章节标题判定应检出「权限档」缺失。

    这是对抗实验 A4/A4b 的回归用例：旧 R3 用全文 `\\b moderate \\b` 找词，
    第 76 行「safe / moderate / dangerous 三档」兜底词会让删章节蒙混过关。
    """
    reg = root / REGISTRY_REL
    lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(
        (i for i, ln in enumerate(lines) if re.match(r"^###\s+moderate\b", ln)), None
    )
    if start is None:
        raise AssertionError("基准副本 registry 无 ### moderate 权限档标题")
    end = next(
        (i for i in range(start + 1, len(lines))
         if re.match(r"^#{2,3}\s", lines[i])), len(lines)
    )
    del lines[start:end]
    reg.write_text("".join(lines), encoding="utf-8")


def _inject_description_token(root: Path, agent_id: str, token: str) -> None:
    """往 atomic MD 的单行双引号 description 值内追加 ` + <token>`（不含引号，
    不破坏 YAML / frontmatter 结构）。在 sanitize_pristine 归一之后的用例副本上
    调用；sanitize 只重写 registry **tools**: 行 + 给 description 追加触发词，
    不会删除 / 改写已注入的 token，故注入不会被洗掉。
    """
    md = root / "agents" / f"{agent_id}.md"
    lines = md.read_text(encoding="utf-8").splitlines(keepends=True)
    fm_end = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    d = next(
        (i for i in range(1, fm_end) if re.match(r"^description\s*:", lines[i])), None
    )
    if d is None:
        raise AssertionError(f"基准副本 {agent_id}.md 无 description 行")
    raw = lines[d].rstrip("\r\n")
    newline = lines[d][len(raw):]
    m = re.match(r'^(\s*description\s*:\s*")(.*)("\s*)$', raw)
    if not m:
        raise AssertionError(f"基准副本 {agent_id} description 非单行双引号格式")
    lines[d] = m.group(1) + m.group(2) + " + " + token + m.group(3) + newline
    md.write_text("".join(lines), encoding="utf-8")


def n8(root):
    """在某个 atomic MD 的 frontmatter description 注入伪造工具名 mcp__GHOST_TOOL
    → R5 工具集合一致性应命中 `extra=`（覆盖解析器 ② mcp__ 前缀名）。

    raw_probe 针对未归一的原始副本仍要求 rc=0（真实仓库 3 个 atomic MD 已单源化、
    description 未枚举工具）。
    """
    _inject_description_token(root, "domain-expert-biomed", "mcp__GHOST_TOOL")


def n9(root):
    """在某个 atomic MD 的 frontmatter description 注入「不带反引号、不带 mcp__
    前缀」的裸词「政策文件库」→ R5 应判「疑似非工具名裸词」FAIL。

    覆盖解析器 ④ 非工具名裸词分支：证明「无 token → PASS」放行分支不是只看
    mcp__ 前缀，裸词同样会被抓。注入发生在归一之后的用例副本上，不会被
    sanitize_pristine 洗掉；raw_probe 对未归一原始副本仍要求 rc=0。
    """
    _inject_description_token(root, "domain-expert-biomed", "政策文件库")


# ── 用例注册 ───────────────────────────────────────────────────────────────
case("P1", "自愈基准副本全绿", "PASS", p1, expect_rc=0)
case("N1", "删除一个成员 MD → R1 成员集合", "成员集合", n1)
case("N2", "删掉 description 前 3 个关键触发词 → R2", "关键触发词", n2)
case("N3", "删除一条 **routing**: 行 → R3 结构完整", "结构完整", n3)
case("N4", "删除 Loop 表 max_turns 行 → R3 结构完整", "结构完整", n4)
case("N5", "tools 行塞入裸词「政策文件库」→ R4 工具名", "工具名", n5)
case("N6", "tools 行塞入空后缀 mcp__ → R4 工具名", "工具名", n6)
case("N7", "删除整个 ### moderate 权限档章节 → R3 权限档", "权限档", n7)
case("N8", "description 注入伪造 mcp__GHOST_TOOL → R5 工具集合一致性", "extra=", n8)
case("N9", "description 注入裸词「政策文件库」→ R5 非工具名裸词", "疑似非工具名裸词", n9)


# ── 复制与执行 ─────────────────────────────────────────────────────────────
def make_copy(src: Path, dst: Path) -> None:
    shutil.copytree(
        src, dst, symlinks=True,
        ignore=lambda _d, names: [n for n in names if n in COPY_EXCLUDE],
    )


def run_checker(case_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(case_dir / "scripts" / "routing_eval.py"),
         "--root", str(case_dir)],
        capture_output=True, text=True,
    )


def run_case(pristine: Path, workdir: Path, cid, desc, expect, expect_rc, mutate) -> bool:
    case_dir = workdir / cid
    if case_dir.exists():
        shutil.rmtree(case_dir)
    make_copy(pristine, case_dir)
    try:
        mutate(case_dir)
    except Exception as exc:  # 用例自身前置断言失败也要计入失败，而不是崩掉整个自测
        print(f"  ⚠️  {cid} {desc}: 用例前置处理失败 —— {exc}")
        return False

    proc = run_checker(case_dir)
    output = proc.stdout + proc.stderr
    hit = expect in output
    ok = proc.returncode == expect_rc and hit
    mark = "✅" if ok else "❌"
    print(
        f"  {mark} {cid} {desc}: rc={proc.returncode}（期望 {expect_rc}）"
        f" 命中预期='{expect}' → {hit}"
    )
    if not ok:
        for line in output.splitlines():
            if "❌" in line or "⚠️" in line:
                print("       ", line.strip())
    shutil.rmtree(case_dir, ignore_errors=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="routing_eval.py 注入式负例自测")
    parser.add_argument("-k", "--filter", default=None, help="只跑编号/说明含该子串的用例")
    parser.add_argument(
        "--root", type=Path, default=None,
        help="指定被复制的源仓库根（默认脚本所在仓库）；供对抗验证指向带缺陷副本",
    )
    args = parser.parse_args()

    source_root = args.root.resolve() if args.root else REPO_ROOT
    source_checker = source_root / CHECKER_REL
    if not source_checker.is_file():
        print(f"❌ 找不到校验器: {source_checker}")
        return 2
    if not (source_root / ".codebuddy-plugin/plugin.json").is_file():
        print(f"❌ 源仓库根定位有误（无 plugin.json）: {source_root}")
        return 2

    selected = [
        c for c in CASES
        if not args.filter
        or args.filter.lower() in c[0].lower()
        or args.filter.lower() in c[1].lower()
    ]
    if not selected:
        print(f"❌ 无匹配用例: {args.filter}")
        return 2

    print("=" * 72)
    print(f"routing_eval 注入式自测  源仓库根: {source_root}")
    print(f"用例数: {len(selected)}")
    print("=" * 72)

    failures = 0
    with tempfile.TemporaryDirectory(prefix="routing-eval-selftest-") as tmp:
        tmp_path = Path(tmp)
        pristine = tmp_path / "pristine"
        print("\n准备基准副本…")
        make_copy(source_root, pristine)

        # ── raw_probe：未归一化原始副本的真实合规护栏（准备阶段，不计入用例数）──
        # 若真实仓库本就有 R2 / R4 路由不一致，sanitize_pristine 会先把它「修好」
        # 再测，导致虚假 PASS。故必须先对原始副本要求 rc=0，否则拒绝继续。
        raw = run_checker(pristine)
        raw_summary = next(
            (ln.strip() for ln in raw.stdout.splitlines() if "路由结构一致性:" in ln),
            "（无汇总行）",
        )
        print(f"  [raw_probe 护栏] 未归一化原始副本 rc={raw.returncode}（期望 0）  {raw_summary}")
        if raw.returncode != 0:
            print("❌ 真实仓库存在路由不一致，selftest 拒绝用自愈夹具掩盖", file=sys.stderr)
            print("   raw_probe 直接对未归一化副本跑 routing_eval.py 已返回非 0；"
                  "sanitize_pristine 会先修好这些缺陷再测，继续跑负例只会得到虚假的 PASS。"
                  "请先修复真实仓库的路由不一致。", file=sys.stderr)
            print(raw.stdout, file=sys.stderr)
            print(raw.stderr, file=sys.stderr)
            return 1

        # ── 归一化：仅在真实仓库已确认合规后，用于构造稳定的负例基准 ──────────
        sanitize_pristine(pristine)
        print("  基准已归一化，仅证明校验器逻辑，不代表真实仓库合规"
              "（真实仓库合规由上方 raw_probe 护栏保证）")

        # 护栏：归一后的基准必须 rc=0，否则所有负例都失去意义
        probe = run_checker(pristine)
        summary = next(
            (ln.strip() for ln in probe.stdout.splitlines() if "路由结构一致性:" in ln),
            "（无汇总行）",
        )
        print(f"  基准副本自检 rc={probe.returncode}（期望 0）  {summary}")
        if probe.returncode != 0:
            print(probe.stdout)
            print(probe.stderr, file=sys.stderr)
            print("❌ 基准副本未能归一为全绿，自测终止（先检查 sanitize_pristine）")
            return 1

        print("\n逐条注入破坏并断言校验器响应：")
        for cid, desc, expect, expect_rc, mutate in selected:
            if not run_case(pristine, tmp_path, cid, desc, expect, expect_rc, mutate):
                failures += 1

    passed = len(selected) - failures
    print("\n" + "=" * 72)
    if failures:
        print(f"❌ 路由 eval 自测: {passed}/{len(selected)} PASS（{failures} 条行为不符合预期）")
        print("   提示：校验器可能已退化，或某条检查项文案被改动。")
        print("=" * 72)
        return 1
    print(f"✅ 路由 eval 自测: {passed}/{len(selected)} PASS（全部行为符合预期）")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
