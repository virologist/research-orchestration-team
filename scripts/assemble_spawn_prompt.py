#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容 shim（v3.4.2 P0-1 分发修复，2026-10-15；原 v3.4.1 R9 shared-core 下沉）
==============================================================================
本包的实现已下沉至联邦共享件：my-experts/plugins/shared-core/assemble_spawn_prompt.py
（4 个无差异包共用同一份真源，消除 378 行 x 4 的拷贝漂移）。
本文件保留入口兼容——sop-stages.md / 各成员 MD 均引用 scripts/assemble_spawn_prompt.py。

解析顺序（两级，先联邦后兜底）：
  1. 联邦真源：从「专家包根的父目录」起逐级向上找 shared-core/assemble_spawn_prompt.py
     （最多 4 层）。安装态路径 .../marketplaces/my-experts/plugins/<pkg> 的父目录即为
     plugins/，命中联邦 core —— 真源优先，运行时不产生漂移。
  2. vendor 兜底：<pkg>/vendor/shared-core/assemble_spawn_prompt.py。
     仅在联邦 core 缺失时启用（git clone 后直跑 / CI / 离线开发态），
     保证 `git clone → python3 scripts/assemble_spawn_prompt.py --list-members` 开箱可用。
  3. 两者皆无 → exit 3（保留原诊断信息）。

防漂移：
  tests/test_vendor_core.py 在安装态（联邦 core 存在）比对 vendor 副本 sha256，
  不一致即 FAIL 并提示 sync 命令；联邦缺失时自动 SKIP（git/CI 场景不误报）。
  shim 自身另有「命中即校验」：解析到的 core 若与本包 vendor/shared-core/VENDOR.json
  登记的 sha256 不一致 → 拒绝加载并退出（fail-closed），避免祖先目录里的旧版/
  被篡改同名文件被静默加载并绕过哈希门禁（FM-R1-03）。

调试：
  SHIM_DEBUG=1 python3 scripts/assemble_spawn_prompt.py --list-members
  → stderr 打印解析到的 core 路径与来源（federal / vendor）。

环境变量：
  EXPERT_DIR  显式指定专家包根（core 内优先级：--expert-dir > EXPERT_DIR > 位置反推）
  SHIM_DEBUG  打印 core 解析来源
"""

import hashlib
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)                                  # 调用方专家包根
_CORE_NAME = "assemble_spawn_prompt.py"
_MAX_UP = 4                                                    # 向上查找最大层数

# 联邦 core 相对「某目录」的路径；vendor 兜底路径
_FEDERAL_REL = os.path.join("shared-core", _CORE_NAME)
_VENDOR_REL = os.path.join("vendor", "shared-core", _CORE_NAME)
_VENDOR_MANIFEST_REL = os.path.join("vendor", "shared-core", "VENDOR.json")


def _find_federal() -> str | None:
    """联邦真源：从专家包根的【父目录】起逐级向上找（不含包内自身）。

    不写死层数——安装态路径随 marketplace 嵌套深度变化
    （.../marketplaces/my-experts/plugins/<pkg>）。
    从父目录起步是关键：若包含 _PKG 自身，安装态会把包内任何 shared-core/
    误判为真源，反而制造第二份副本。
    """
    d = os.path.dirname(_PKG)
    for _ in range(_MAX_UP):
        cand = os.path.join(d, _FEDERAL_REL)
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _find_vendor() -> str | None:
    """vendor 兜底副本：包内 vendor/shared-core/。"""
    cand = os.path.join(_PKG, _VENDOR_REL)
    return cand if os.path.isfile(cand) else None


def _sha256(path: str) -> str:
    """计算文件 sha256（分块读取，避免大文件一次性进内存）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_sha256() -> str | None:
    """从本包 vendor/shared-core/VENDOR.json 读出登记的期望 sha256。

    读不到 / 解析失败 / 字段缺失 → 返回 None（跳过校验，不误报）。
    本函数只读 VENDOR.json，绝不修改 vendor/ 或联邦 shared-core/。
    """
    manifest = os.path.join(_PKG, _VENDOR_MANIFEST_REL)
    try:
        with open(manifest, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    expected = data.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return None
    return expected


_FEDERAL = _find_federal()
_VENDOR = _find_vendor()
_CORE = _FEDERAL or _VENDOR
_SOURCE = "federal" if _FEDERAL else ("vendor" if _VENDOR else None)


def _verify_core_integrity() -> None:
    """命中即校验：core 的 sha256 必须与 VENDOR.json 登记值一致，否则拒绝加载。

    为什么必须 fail-closed（FM-R1-03）：
      _find_federal() 从包根父目录起逐级向上查找 shared-core/。若祖先目录里存在
      旧版或被篡改的同名文件，它会被抢先命中并静默加载——此时 tests/test_vendor_core.py
      的 V4 比对的是「联邦 vs vendor 副本」，只要两者同时被同一次篡改就会一起漂移，
      哈希门禁被绕过，坏代码直接进运行时。

    三种情形：
      ① 校验通过 → 正常加载。
      ② 校验不通过 → 打印诊断并 exit 4（明确区别于 exit 3「core 缺失」）。
      ③ 无法校验（VENDOR.json 缺失/损坏/无合法 sha256）→ 放行但显式告警。
         理由：git clone / CI 态若 vendor 目录未随包分发，校验能力不存在，
         此时阻断运行会制造新的假红；告警保留可观测性。
    """
    if _CORE is None:
        return
    expected = _expected_sha256()
    if expected is None:
        sys.stderr.write(
            "[assemble_spawn_prompt shim] ⚠️ 跳过 core 哈希校验："
            "读不到 %s 中的合法 sha256（文件缺失/损坏/字段非法）。\n"
            "  来源: %s\n" % (_VENDOR_MANIFEST_REL, _SOURCE)
        )
        return
    try:
        actual = _sha256(_CORE)
    except OSError as exc:
        sys.stderr.write(
            "[assemble_spawn_prompt shim] ❌ core 读取失败，无法校验哈希：%s\n" % exc
        )
        sys.exit(4)
    if actual != expected:
        sys.stderr.write(
            "[assemble_spawn_prompt shim] ❌ core 哈希校验失败，拒绝加载。\n"
            "  core 路径: %s\n"
            "  来源: %s\n"
            "  期望 sha256: %s\n"
            "  实际 sha256: %s\n"
            "  常见原因：祖先目录里存在旧版或被篡改的同名 shared-core 副本。\n"
            "  处置：核对该文件与联邦真源是否一致；一致则执行 sync 命令刷新 VENDOR.json，\n"
            "        不一致则清理该路径。\n"
            "  sync: cp <联邦真源>/%s vendor/shared-core/ && 更新 VENDOR.json 的 sha256/lines/synced_at\n"
            % (_CORE, _SOURCE, expected, actual, _CORE_NAME)
        )
        sys.exit(4)


_verify_core_integrity()


def _debug(msg: str) -> None:
    if os.environ.get("SHIM_DEBUG"):
        sys.stderr.write(f"[assemble_spawn_prompt shim] {msg}\n")


if _CORE is None:
    sys.stderr.write(
        "[assemble_spawn_prompt shim] shared-core 缺失（自 %s 向上 %d 层未找到联邦件，"
        "且包内无 vendor 兜底）\n"
        "  本包实现已下沉至联邦共享件。请确认安装态 .../plugins/shared-core/ 存在；\n"
        "  若在 git 仓库结构中运行，请确认 vendor/shared-core/ 已随仓库分发，\n"
        "  或从 vet-med-ppt-team 仓库的 shared-core/ 取回。\n" % (_PKG, _MAX_UP))
    sys.exit(3)
_debug(f"core = {_CORE}（来源: {_SOURCE}）")

# 专家包根显式传给 core（core 内优先级：--expert-dir > EXPERT_DIR > 位置反推）
os.environ.setdefault("EXPERT_DIR", _PKG)

_spec = importlib.util.spec_from_file_location("_shared_core_assemble_spawn_prompt", _CORE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# 八阶段名的唯一事实源是 skills/research-orchestration-workflow/scripts/state_io.py
# 的 PHASES；此处逐字复刻而不直接 import：state_io 所在目录名含连字符，无法作为
# 常规包导入，且 shim 启动阶段应保持零依赖（仅标准库），避免在加载联邦 core 前
# 引入额外失败点。仅在 argv 层做归一化：不修改联邦 core / vendor 副本，
# 避免 VENDOR.json 哈希漂移。
PHASE_NAMES = ["FREEZE", "IDENTIFY", "COLLAPSE", "CLARIFY", "ALIGN",
               "EXECUTE", "REVIEW", "NEXT"]
_PHASE_NAME_TO_NUM = {name: str(i + 1) for i, name in enumerate(PHASE_NAMES)}


def _normalize_phase_argv(argv):
    """把 --phase <阶段名> / --phase=<阶段名> 归一化为 1-8 的字符串阶段号。

    合法阶段名（大小写不敏感）转编号；整数字符串与非法值原样透传
    （非法值交给 core 的 argparse 报错，禁止静默吞掉）；--phase 后无值也
    原样透传。返回归一化后的 argv 副本，由调用方写回 sys.argv。
    """
    out = list(argv)
    for i, tok in enumerate(out):
        if tok == "--phase":
            if i + 1 < len(out):
                mapped = _PHASE_NAME_TO_NUM.get(out[i + 1].upper())
                if mapped is not None:
                    out[i + 1] = mapped
        elif tok.startswith("--phase="):
            val = tok.split("=", 1)[1]
            mapped = _PHASE_NAME_TO_NUM.get(val.upper())
            if mapped is not None:
                out[i] = "--phase=" + mapped
    return out


if __name__ == "__main__":
    # 必须在 _mod.main() 执行前生效：core 的 argparse 在 main() 内解析 sys.argv。
    sys.argv = _normalize_phase_argv(sys.argv)
    sys.exit(_mod.main())
