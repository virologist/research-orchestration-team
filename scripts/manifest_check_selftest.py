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

其中 N11 是**反向用例**：破坏一种契约标记但保留另一种，期望校验器**放行**（rc=0），
用于确认 C9 接受三种等价命名，而不是只认一种。

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
    path = root / ".codebuddy-plugin/plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["displayDescription"]["zh"] = data["displayDescription"]["zh"].replace(
        "五级冲突仲裁", "三级冲突仲裁"
    )
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
    path = root / "agents/domain-expert.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("## v2.0 协议合规契约", "## 无关章节"),
        encoding="utf-8",
    )
case("N10", "成员契约章节被改名", "domain-expert 未找到契约章节", n10)


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
