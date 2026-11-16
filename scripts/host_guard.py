#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""host_guard.py — 宿主接管看门狗（Team 型包根 settings.json 自愈）

## 背景（为什么需要这个脚本）

Team 型专家包的包根 settings.json（内容 `{"agent": "<插件名>-team-lead"}`）
是官方 validate_expert 的硬性要求，但宿主（WorkBuddy ExpertPluginService）
会在运行期间反复删除该文件。实测时间线（均通过 rot.py check 的 C12 判红
连锁发现）：

  2026-11-15  settings.json 被删 → git restore 恢复 → 分钟级后再次被删
  2026-11-16  同样形态再次发生（跨会话累计 5+ 次），且删除行为持续回灌

宿主删除属于平台侧行为，仓库侧无法阻止其发生，只能做到：
  1. 检测 —— discover 该文件是否缺失 / 损坏（detect）
  2. 修复 —— 从 git HEAD 恢复，git 不可用时回退为直接写入（repair）
  3. 留痕 —— 每次事件（检测态 / 动作 / sha256 / git 结果）追加 JSONL
     证据到 .harness-runs/host_guard.log（该目录已被 .gitignore 忽略）

## 设计约束

  - 定位包根：从 __file__ 向上逐层探测 `.codebuddy-plugin/plugin.json` +
    `workmap.json` 双标记（与 rot.py 的 find_root 同法，禁 parents[N] 硬
    索引——跨平台布局差异会 IndexError）。
  - 期望内容：读 .codebuddy-plugin/plugin.json 的 name 字段，构造
    `{"agent": "<name>-team-lead"}`，不写死插件名字面量。
  - 修复以 git 为准：`git checkout HEAD -- settings.json`（cwd=包根）。
    成功后必须复核 sha256 与 `git show HEAD:settings.json` 一致才算修复
    成功；git 失败（如临时副本不是 git 仓）时回退直接写入构造内容。
  - 防误报 / 防日志爆炸：宿主分钟级回灌时，若日志里最后一条是 60 秒内
    的成功修复则跳过本次重复修复（log_skip 记录），避免每次 check 都写
    一条修复事件把日志撑爆。
  - stdlib only；不 import rot.py（避免与统一 CLI 耦合，本脚本必须能被
    任意宿主脚本以路径加载独立运行）。
  - 全中文注释。

## 用法

  python3 scripts/host_guard.py             # 默认：detect → repair → report
  python3 scripts/host_guard.py --check     # 只检测不修复（接管态 rc=2）
  python3 scripts/host_guard.py --self-test # 4 组注入负例（临时副本上做）

## 退出码

  0 = 健康态，或接管态但修复成功
  1 = 接管 / 损坏态且修复失败
  2 = --check 模式下检出接管 / 损坏态（只报告不修复）
  3 = 环境错误（找不到包根 / manifest）

## self-test 的 4 组负例

  ST1 健康态不误报：原样副本 detect() == healthy
  ST2 删除后检测为接管态：unlink settings.json 后 detect() == taken_over
  ST3 修复后内容与 HEAD 全等：repair() 后字节与 git show HEAD 一致
  ST4 损坏态检测为损坏态：写入非法 JSON 后 detect() == corrupted

  全部用例在临时副本上执行，绝不触碰真仓库。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# ── 常量 ────────────────────────────────────────────────────────────────────
# 包根判定标记：与 rot.py 的 MARKERS 保持同语义（manifest + 工作地图真值源）
MARKERS = (".codebuddy-plugin/plugin.json", "workmap.json")
# 目标文件（相对包根）
SETTINGS_REL = "settings.json"
MANIFEST_REL = ".codebuddy-plugin/plugin.json"
# 证据日志（相对包根；.harness-runs/ 已被 .gitignore 忽略，无需改 ignore 规则）
LOG_REL = Path(".harness-runs") / "host_guard.log"
# 防回灌窗口：距上次成功修复不足该秒数时跳过重复修复
REPAIR_COOLDOWN_SECONDS = 60


def find_root(start: Path | None = None) -> Path | None:
    """从 start（默认本脚本位置）向上逐层探测包根。

    与 rot.py 的 find_root 同法：遍历 [自身, *parents]，全部标记命中才算
    包根。禁用 parents[N] 硬索引——脚本可能被复制到任意深度的临时目录运行。
    """
    p = (start or Path(__file__).resolve()).absolute()
    for cand in [p, *p.parents]:
        if all((cand / m).exists() for m in MARKERS):
            return cand
    return None


def _expected_agent() -> str | None:
    """从包根 manifest 读 name，构造期望的 agent 值 `<name>-team-lead`。

    manifest 缺失 / JSON 非法 / 无 name 时返回 None（调用方按环境错误处理）。
    """
    root = find_root()
    if root is None:
        return None
    try:
        data = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
        name = data.get("name")
        return f"{name}-team-lead" if isinstance(name, str) and name.strip() else None
    except Exception:
        return None


def detect(root: Path) -> str:
    """检测包根 settings.json 的状态。

    返回三种状态字符串：
      healthy     —— 存在、JSON 合法、含非空字符串 agent 键
      taken_over  —— 文件不存在（宿主接管态）
      corrupted   —— 存在但 JSON 非法，或缺非空 agent 键（损坏态）
    """
    path = root / SETTINGS_REL
    if not path.exists():
        return "taken_over"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "corrupted"
    agent = data.get("agent") if isinstance(data, dict) else None
    if isinstance(agent, str) and agent.strip():
        return "healthy"
    return "corrupted"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _head_bytes(root: Path) -> bytes | None:
    """读 git HEAD 版本的 settings.json 字节；git 不可用 / 未跟踪返回 None。"""
    r = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{SETTINGS_REL}"],
        capture_output=True,
    )
    return r.stdout if r.returncode == 0 else None


def _last_repair_recent(root: Path, seconds: int = REPAIR_COOLDOWN_SECONDS) -> bool:
    """日志末尾若存在 60 秒内的成功修复事件则返回 True（防回灌重复修复）。

    只看文件尾部若干行（回灌场景日志增长快，全量解析浪费 IO）；解析失败
    一律视为「无近期修复」——宁可多修一次，不可漏修。
    """
    log = root / LOG_REL
    if not log.is_file():
        return False
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines[-20:]):
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("event") == "repair" and rec.get("repaired") is True:
                ts = datetime.fromisoformat(rec.get("timestamp"))
                if datetime.now() - ts <= timedelta(seconds=seconds):
                    return True
            return False  # 只看最后一条 repair 记录，更早的不再回溯
    except Exception:
        return False
    return False


def repair(root: Path) -> dict:
    """把 settings.json 恢复为期望内容。返回修复结果字典（供 report 落盘）。

    路径一（首选）：git checkout HEAD -- settings.json（cwd=包根）。
      恢复后复核 sha256 与 git show HEAD:settings.json 一致 → 修复成功。
    路径二（回退）：git 不可用（临时副本非 git 仓 / 未安装 git）时直接
      写入构造内容 {"agent": "<name>-team-lead"} 并 chmod 644。构造内容
      来自 manifest 的 name 字段，不写死插件名字面量。
    两路都失败 → repaired=False，调用方据其给非零退出码。
    """
    result: dict = {
        "event": "repair",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "state_before": detect(root),
        "method": None,
        "sha_before": None,
        "sha_after": None,
        "git_result": None,
        "repaired": False,
    }
    path = root / SETTINGS_REL
    if path.exists():
        result["sha_before"] = _sha256(path.read_bytes())

    head = _head_bytes(root)

    # ── 路径一：git 恢复 ────────────────────────────────────────────────
    if head is not None:
        r = subprocess.run(
            ["git", "-C", str(root), "checkout", "HEAD", "--", SETTINGS_REL],
            capture_output=True, text=True,
        )
        result["git_result"] = (
            f"checkout rc={r.returncode}"
            + (f" stderr={r.stderr.strip()[:120]}" if r.returncode != 0 else "")
        )
        if r.returncode == 0 and path.exists():
            after = path.read_bytes()
            if _sha256(after) == _sha256(head):
                # 复核与 HEAD 全等才算修复成功（防 checkout 半途失败误报）
                result.update(method="git_checkout", sha_after=_sha256(after),
                              repaired=True)
                return result

    # ── 路径二：直接写入构造内容（git 不可用或 checkout 复核失败）──────
    expected_agent = _expected_agent()
    if expected_agent is None:
        # manifest 都读不出来 → 连期望内容都构造不了，修复必然失败
        result["git_result"] = result["git_result"] or "manifest 不可读，无法构造期望内容"
        return result
    payload = json.dumps({"agent": expected_agent}, ensure_ascii=False, indent=2) + "\n"
    try:
        path.write_text(payload, encoding="utf-8")
        os.chmod(path, 0o644)
        result.update(method="direct_write", sha_after=_sha256(path.read_bytes()),
                      repaired=True)
        return result
    except OSError as exc:
        result["git_result"] = f"direct_write 失败: {type(exc).__name__}: {exc}"
        return result


def report(root: Path, record: dict) -> None:
    """把事件记录追加为 JSONL 一行到 .harness-runs/host_guard.log。

    目录不存在则 mkdir -p；写日志失败不抛异常（留痕是尽力而为，不能让
    日志故障反过来阻断修复或 check 主流程）。
    """
    log = root / LOG_REL
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 证据落盘失败不阻断主流程；修复结果仍以返回值 / 退出码为准


def run_guard(root: Path, check_only: bool = False) -> tuple[int, str]:
    """默认主流程：detect →（接管 / 损坏时）repair → report。

    返回 (退出码, 人读消息)：
      健康态           → (0, 健康)
      接管 / 损坏+check_only → (2, 只检测模式提示)
      接管 / 损坏+修复成功   → (0, 已修复)
      接管 / 损坏+修复失败   → (1, 修复失败)
    """
    state = detect(root)
    if state == "healthy":
        return 0, "[host-guard] settings.json 健康，无需修复"

    if check_only:
        return 2, f"[host-guard] 检测到 settings.json 处于 {state} 态（--check 只检测不修复）"

    # 防回灌：60 秒内已成功修复过则跳过（记一条 log_skip 事件，不重复 repair）
    if _last_repair_recent(root):
        report(root, {"event": "log_skip",
                      "timestamp": datetime.now().isoformat(timespec="seconds"),
                      "state": state,
                      "reason": f"60 秒内已有成功修复，跳过重复修复（防回灌日志爆炸）"})
        return 0, "[host-guard] settings.json 异常但 60 秒内刚修复过，跳过重复修复"

    result = repair(root)
    result["detected_state"] = state
    report(root, result)
    if result["repaired"]:
        return 0, f"[host-guard] 检测到宿主接管，已自动修复 settings.json（method={result['method']}）"
    return 1, f"[host-guard] settings.json 处于 {state} 态且修复失败（{result['git_result']}）"


# ── self-test：4 组注入负例（全部在临时副本上做，不动真仓库）───────────────
def self_test() -> int:
    """在真仓库的临时副本上验证 detect / repair 的三种状态语义。

    ST1 健康态不误报          —— 原样副本 detect() 应为 healthy
    ST2 删除后检测为接管态     —— unlink 后 detect() 应为 taken_over
    ST3 修复后内容与 HEAD 全等 —— repair() 后 sha256 与 git show HEAD 一致
    ST4 损坏态检测为损坏态     —— 写非法 JSON 后 detect() 应为 corrupted

    返回 0 = 4/4 通过；1 = 有失败。
    """
    src = find_root()
    if src is None:
        print("❌ 未找到包根（workmap.json + .codebuddy-plugin/plugin.json）")
        return 3

    results: list[tuple[str, bool, str]] = []
    tmp = Path(tempfile.mkdtemp(prefix="host-guard-selftest-"))
    try:
        # 复制真仓库到临时目录（排除 .git —— ST3 需要副本里也有 git 历史，
        # 但 cp -cR 克隆 .git 有 CoW 语义风险；改为浅复制工作树后在副本里
        # git init + 提交，保证 HEAD 版本可控且与真仓库 git 完全隔离）。
        dst = tmp / "pkg"
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".backups",
                                          ".harness-runs"),
        )
        # 副本内构造独立 git 仓：以「当前真仓库 HEAD 内容」为初始提交，
        # 这样 ST3 的「与 HEAD 全等」断言有明确锚点。
        def _git(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(["git", "-C", str(dst), *args],
                                  capture_output=True, text=True)

        _git("init", "-q")
        _git("config", "user.email", "guard-selftest@local")
        _git("config", "user.name", "host-guard-selftest")
        _git("add", "-A")
        _git("commit", "-q", "-m", "selftest baseline")
        head_sha = None
        r = _git("show", f"HEAD:{SETTINGS_REL}")
        if r.returncode == 0:
            head_sha = _sha256(r.stdout.encode("utf-8"))

        def check(name: str, ok: bool, detail: str) -> None:
            mark = "✅" if ok else "❌"
            print(f"  {mark} {name} | {detail}")
            results.append((name, ok, detail))

        # ST1 健康态不误报
        st = detect(dst)
        check("ST1 健康态不误报", st == "healthy", f"detect={st}")

        # ST2 删除后检测为接管态
        (dst / SETTINGS_REL).unlink()
        st = detect(dst)
        check("ST2 删除后检测为接管态", st == "taken_over", f"detect={st}")

        # ST3 修复后内容与 HEAD 全等（副本有独立 git 历史，走 git_checkout 路径）
        rep = repair(dst)
        ok = (
            rep["repaired"]
            and rep["method"] == "git_checkout"
            and head_sha is not None
            and rep["sha_after"] == head_sha
            and (dst / SETTINGS_REL).exists()
        )
        check("ST3 修复后内容与 HEAD 全等", ok,
              f"method={rep['method']} repaired={rep['repaired']} "
              f"sha_match={rep['sha_after'] == head_sha if head_sha else '无HEAD'}")

        # ST4 损坏态检测为损坏态（写入非法 JSON）
        (dst / SETTINGS_REL).write_text("{ not json", encoding="utf-8")
        st = detect(dst)
        check("ST4 损坏态检测为损坏态", st == "corrupted", f"detect={st}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [n for n, ok, _ in results if not ok]
    print("-" * 60)
    if failed:
        print(f"❌ self-test 未通过：{len(failed)}/{len(results)} 条失败: {failed}")
        return 1
    print(f"✅ self-test 通过：{len(results)}/{len(results)} 条")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="宿主接管看门狗：检测 → 自动修复 → 报警证据落盘（settings.json）")
    ap.add_argument("--check", action="store_true",
                    help="只检测不修复（接管 / 损坏态退出码 2）")
    ap.add_argument("--self-test", action="store_true",
                    help="4 组注入负例（临时副本上执行，不动真仓库）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = find_root()
    if root is None:
        print("❌ 未找到包根（workmap.json + .codebuddy-plugin/plugin.json）",
              file=sys.stderr)
        return 3
    rc, msg = run_guard(root, check_only=args.check)
    print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
