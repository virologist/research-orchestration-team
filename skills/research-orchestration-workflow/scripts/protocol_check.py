"""
协议合规单元测试脚本 / Protocol Compliance Unit Tests

参考 references/agent-protocol.md，对外发消息信封、状态同步、冲突仲裁等
关键契约做确定性校验。真实模拟协议层，便于集成前发现回归。

信封主套件校验当前 SSOT §2「消息信封（result_envelope v2.4）」：
6 必填字段（agent_id / task_id / phase / status / confidence /
deliverable_summary）、小写四值 status、0-100 confidence、type 枚举、
evidence 数组、context_ref.mode 等。
已废弃的 ACP v2.0 信封逻辑原样保留为 check_envelope_v20，仅供
run_legacy_envelope_tests() 的历史 fixture 回归使用，
**不参与当前协议合规判定**。

本脚本的门禁口径（v2.3.0 迭代闭环 Phase C · 协议门禁强化）：
- 集成仿真段改为**真校验**：阶段序列与 state_io.py 的 PHASES 逐项比对，
  阶段间依赖（dep 指向的 msg_id 必须由更早的上游阶段产出）真断言，
  不再出现"无条件打印 ✅"的自证式绿灯。
- 证据链三校验（ref 格式 / GRADE / 降级标注）接入 v2.4 **主套件**，
  不再只在 legacy 路径被调用。
- context_ref 口径统一：§2 仍为"推荐"，但 HANDOFF 类型升级为"必填"。

Usage:
    python3 protocol_check.py             # 全部用例
    python3 protocol_check.py envelope    # 信封套件（v2.4 主套件 + ACP v2.0 历史回归）
    python3 protocol_check.py conflict    # 仅冲突仲裁套件
    python3 protocol_check.py integration # 仅集成仿真套件
"""

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────
# 信封校验：主校验 result_envelope v2.4（§2 SSOT）
#           check_envelope_v20 为已废弃 ACP v2.0 的历史 fixture 回归保留
# ─────────────────────────────────────────────────────────────────────

# ── 已废弃 ACP v2.0 常量（仅服务历史 fixture 回归，不代表当前协议）──
REQUIRED_FIELDS_V20 = ["v", "msg_id", "ts", "from", "to", "type", "trace_id",
                       "status", "confidence", "context_ref", "payload"]
VALID_TYPES = {"TASK", "RESULT", "CLARIFY", "REVIEW", "ERROR", "STATUS", "HANDOFF"}
VALID_STATUS_V20 = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "BLOCKED"}
# v2.1.2：domain-expert 拆为 3 atomic 后执行者集合扩容（超集，兼容历史 fixture）
_ATOMIC_EXECUTORS = {"domain-expert-biomed", "domain-expert-ai", "domain-expert-general"}
EVIDENCE_PRODUCERS = {"domain-expert", "methodological-reviewer"} | _ATOMIC_EXECUTORS

# ── 当前 result_envelope v2.4 常量（SSOT §2）──
REQUIRED_FIELDS_V24 = ["agent_id", "task_id", "phase", "status", "confidence",
                       "deliverable_summary"]
VALID_STATUS_V24 = {"success", "partial", "failed", "blocked"}
VALID_CONTEXT_MODES = {"full", "summary", "ref"}
# 执行者/审查者集合（用 agent_id 判定；分析者、整合者不强制 evidence[]）
EVIDENCE_PRODUCERS_V24 = {
    "domain-expert-biomed", "domain-expert-ai", "domain-expert-general",
    "methodological-reviewer",
}

# ── 证据链校验常量（证据链三校验：ref 格式 / GRADE / 降级标注）──
# 协议 §2 的 evidence[].ref 允许形态（PMID|DOI|URL|路径 四类）：
#   1) http(s):// 开头的 URL
#   2) PMID:12345678 或纯数字 PMID / PMC 开头的 PMC 编号
#   3) DOI:10.xxxx/yyy 或裸 DOI
#   4) arXiv 编号（arXiv 前缀 + 数字 + 版本号）
#   5) path:/绝对路径 或 state://cp-NNN 检查点指针 或 /开头的落盘绝对路径
#   6) <文件名>:<行号> 形态的本地行级引用
REF_PATTERNS = (
    re.compile(r"^https?://\S+$"),
    re.compile(r"^PMID:\d+$"),
    re.compile(r"^\d+$"),
    re.compile(r"^PMC\d+$"),
    re.compile(r"^DOI:10\.\d{4,}/\S+$"),
    re.compile(r"^10\.\d{4,}/\S+$"),
    re.compile(r"^arXiv:\d{4}\.\d{4,5}(v\d+)?$"),
    re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$"),
    re.compile(r"^path:/\S*$"),
    re.compile(r"^state://\S+$"),
    re.compile(r"^/\S+$"),
    re.compile(r"^[^:\s]+:\d+$"),
)

# 降级标记字面量：工具降级链「三源全败则降置信输出」要求每条 evidence 写明
# 来源不可用，不得编造 DOI/PMID/URL。本标记只允许出现在降级场景。
SOURCE_UNAVAILABLE_MARK = "source_unavailable"

# context_ref.pointer 的允许形态（协议 §4 上下文传递的回引指针）：
#   1) state://cp-NNN        —— 检查点指针（与 state_io.py 的 cp-NNN 约定一致）
#   2) state:// + 合法路径段  —— 如 state://phase2/...
#   3) https?://...          —— 外部 URL
#   4) <路径>:<行号>         —— 本地文件行级引用，如 scripts/foo.py:120
# pointer 形态非法会让回引既无法定位又静默通过（既不计入覆盖、也不报错），
# 故必须作为门禁拦截。
CONTEXT_POINTER_PATTERNS = (
    re.compile(r"^state://cp-\d{3,}$"),
    re.compile(r"^state://[\w./-]+$"),
    re.compile(r"^https?://\S+$"),
    re.compile(r"^[^:\s]+:\d+$"),
)

# HANDOFF 回引专用的检查点指针形态：只有 `state://cp-NNN` 才可能构成
# 「覆盖全部 cp-*」的覆盖；非 cp-* 指针是死引用（既不计入覆盖也不报错）。
CHECKPOINT_POINTER_PATTERN = re.compile(r"^state://cp-\d{3,}$")

# 降级标记的承载字段约定：写在 evidence 条目的 used_for / grade / note /
# status / source 任意一个字段的字符串值里即视为已标注。工具降级链原文是
# 「grade 或 used_for 中标注 source_unavailable 并写明三源失败原因」，
# 故 grade 亦为合法承载位。
DEGRADE_MARKER_FIELDS = ("used_for", "grade", "note", "status", "source")


def check_envelope_v20(env: dict, *, producer_must_have_evidence: bool = False) -> list:
    """已废弃 ACP v2.0 信封校验（仅用于历史 fixture 回归）。

    逻辑与原实现逐字一致，常量改名为 *_V20。返回失败原因列表，空列表表示通过。
    **不要用于当前协议合规判定**。
    """
    fails = []
    if not isinstance(env, dict):
        return ["envelope 不是字典"]
    for f in REQUIRED_FIELDS_V20:
        if f not in env:
            fails.append(f"缺少字段: {f}")
    if env.get("v") != "2.0":
        fails.append(f"协议版本错误: v={env.get('v')!r}（应为 '2.0'）")
    if env.get("type") not in VALID_TYPES:
        fails.append(f"type 非法: {env.get('type')!r}")
    if env.get("status") not in VALID_STATUS_V20:
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


def _context_ref_present(cr: Any) -> bool:
    """判断 context_ref 是否在**结构层**存在且可判定。

    这里只判「结构」不判「指针内容」也不判「mode 取值」：
    - dict：须为非空 dict
    - list：须非空，且每个元素都是 dict
    - 其他（None / 空 / 非 dict 非 list）：视为缺失

    mode 非法与 pointer 缺失各有专属失败原因（context_ref.mode 非法 /
    context_ref.pointer 缺失），不在此处笼统报「context_ref 必填」，
    避免同一处缺陷产生两条失败原因。
    """
    if isinstance(cr, dict):
        return bool(cr)
    if isinstance(cr, list):
        return bool(cr) and all(isinstance(r, dict) for r in cr)
    return False


def _is_valid_context_pointer(pointer: str) -> bool:
    """判断 context_ref.pointer 是否命中允许的回引指针形态。

    允许形态见 CONTEXT_POINTER_PATTERNS（state://cp-NNN / state:// 路径段 /
    http(s) URL / <路径>:<行号>）。
    """
    return any(p.match(pointer) for p in CONTEXT_POINTER_PATTERNS)


def _check_context_pointer(entry: dict, label: str,
                           *, require_checkpoint: bool = False) -> list:
    """校验单条 context_ref 条目的 pointer 形态。返回失败原因列表（空 = 通过）。

    mode 语义（协议 §4 上下文传递）：
    - full：全量拷贝，不需要指针 → pointer 可空
    - summary：结构化摘要，指针可空
    - ref：靠指针定位（JIT retrieval）→ pointer **必填**

    mode 不在合法三值内时**不判 pointer**：mode 非法已由「context_ref.mode
    非法」单独报出，避免同一处缺陷产生两条失败原因。

    require_checkpoint=True（仅 HANDOFF 回引）：pointer 必须是
    `state://cp-NNN` 检查点指针 —— 只有 cp-* 指针才可能构成「覆盖全部
    cp-*」的覆盖，非 cp-* 指针是死引用（既不计入覆盖也不报错 → 静默漏检）。

    失败原因：
    - pointer 为空且 mode == "ref" → "<label>.pointer 缺失"
    - pointer 非空但形态非法       → "<label>.pointer 格式非法: {pointer!r}"
    """
    fails = []
    mode = entry.get("mode")
    if mode not in VALID_CONTEXT_MODES:
        return fails
    pointer = entry.get("pointer")
    if pointer is None or not str(pointer).strip():
        if mode == "ref":
            fails.append(f"{label}.pointer 缺失")
        return fails
    pointer_str = str(pointer)
    if not _is_valid_context_pointer(pointer_str):
        fails.append(f"{label}.pointer 格式非法: {pointer!r}")
        return fails
    if require_checkpoint and not CHECKPOINT_POINTER_PATTERN.match(pointer_str):
        fails.append(f"{label}.pointer 格式非法: {pointer!r}")
    return fails


def _invalid_pointers(context_refs: list, *, require_checkpoint: bool = False) -> list:
    """找出回引条目中 pointer 形态非法的项。返回失败原因列表（空 = 通过）。

    覆盖层专用：check_handoff_coverage 原本只做字符串集合覆盖，形态错的
    pointer 既不计入覆盖、也不报错 → 会静默通过。本函数把这类条目显式计入
    失败原因。

    require_checkpoint=True（HANDOFF 回引）：pointer 必须是 `state://cp-NNN`；
    非 cp-* 指针是死引用，无法构成任何检查点的覆盖，必须显式报出。
    """
    bad = []
    for cr in context_refs:
        if not isinstance(cr, dict):
            continue
        pointer = cr.get("pointer", "")
        if not pointer:
            continue
        pointer_str = str(pointer)
        if not _is_valid_context_pointer(pointer_str):
            bad.append(f"context_ref.pointer 格式非法: {pointer!r}")
        elif require_checkpoint and not CHECKPOINT_POINTER_PATTERN.match(pointer_str):
            bad.append(f"context_ref.pointer 格式非法: {pointer!r}")
    return bad


def check_envelope(env: dict, *, producer_must_have_evidence: bool = False,
                   require_context_ref: bool = False) -> list:
    """result_envelope v2.4 主校验。返回失败原因列表，空列表表示通过。

    §2 SSOT：6 必填字段缺一即判 partial；status 小写四值；
    confidence 为 0-100 数值；type 若存在须在枚举内；evidence 须为数组；
    执行者/审查者（用 agent_id 判定）在 producer_must_have_evidence=True
    且 evidence 为空时强制报错；context_ref 支持 dict 与 list 两种形态。

    require_context_ref：§2 把 context_ref 列为"推荐"，但协议 §8 要求
    HANDOFF 回传必须带回引、且主理人 HANDOFF 须覆盖全部 cp-* 检查点，
    因此对 type == "HANDOFF" 的信封由调用方打开该开关，把口径从
    "推荐"升级为"必填"（缺失或为空 → "context_ref 必填"）。
    """
    fails = []
    if not isinstance(env, dict):
        return ["envelope 不是字典"]
    for f in REQUIRED_FIELDS_V24:
        if f not in env:
            fails.append(f"缺少字段: {f}")
    t = env.get("type")
    if t is not None and t not in VALID_TYPES:
        fails.append(f"type 非法: {t!r}")
    if env.get("status") not in VALID_STATUS_V24:
        fails.append(f"status 非法: {env.get('status')!r}")
    c = env.get("confidence")
    if not isinstance(c, (int, float)) or not (0 <= c <= 100):
        fails.append(f"confidence 非法: {c!r}（应为 0-100）")
    if not isinstance(env.get("evidence", []), list):
        fails.append("evidence 必须是数组")
    if producer_must_have_evidence and not env.get("evidence"):
        if env.get("agent_id") in EVIDENCE_PRODUCERS_V24:
            fails.append(f"执行者/审查者产出必带 evidence[]（{env.get('agent_id')}）")
    cr = env.get("context_ref")
    # HANDOFF 回引硬约束：context_ref 必须存在且非空（dict 需带 mode/pointer，
    # list 需至少有一个元素），否则回引链断裂。
    # 判定收敛到 _context_ref_present 一处，失败原因文案只在这里产出，
    # 保证注入式 selftest 能用唯一锚点定位（多锚点会让注入错配静默空转）。
    if require_context_ref and not _context_ref_present(cr):
        fails.append("context_ref 必填")
    # HANDOFF 的回引必须是检查点指针（只有 cp-* 指针才可能构成「覆盖全部
    # cp-*」的覆盖）；其余类型的 context_ref 只要求通用指针形态合法。
    is_handoff = t == "HANDOFF"
    if isinstance(cr, dict):
        # 空 dict 已被「context_ref 必填」覆盖（若开启该约束），不再叠加
        # mode 非法，避免同一处缺陷产生两条失败原因。
        if cr and cr.get("mode") not in VALID_CONTEXT_MODES:
            fails.append(f"context_ref.mode 非法: {cr.get('mode')!r}")
        else:
            # pointer 形态校验（mode 合法时才判，mode 非法已单独报出）
            fails.extend(_check_context_pointer(cr, "context_ref",
                                                require_checkpoint=is_handoff))
    elif isinstance(cr, list):
        for i, r in enumerate(cr):
            if not isinstance(r, dict):
                # 健壮性：list 元素不是 dict 时旧实现会 AttributeError 崩溃，
                # 改为显式失败原因。
                fails.append(f"context_ref[{i}] 必须是字典")
                continue
            if r.get("mode") not in VALID_CONTEXT_MODES:
                fails.append(f"context_ref[{i}].mode 非法: {r.get('mode')!r}")
            else:
                # list 形态逐条校验 pointer（带下标，便于定位是哪一条回引）
                fails.extend(_check_context_pointer(r, f"context_ref[{i}]",
                                                    require_checkpoint=is_handoff))
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


def _has_source_unavailable(ev: dict) -> bool:
    """判断一条 evidence 是否带有降级标记 source_unavailable。

    约定（见 DEGRADE_MARKER_FIELDS）：标记写在 used_for / grade / note /
    status / source 任意一个字段的字符串值里即视为已标注。工具降级链要求
    「grade 或 used_for 中标注 source_unavailable 并写明三源失败原因」，
    因此 grade 也纳入承载字段。
    """
    for field in DEGRADE_MARKER_FIELDS:
        val = ev.get(field)
        if isinstance(val, str) and SOURCE_UNAVAILABLE_MARK in val:
            return True
    return False


def _is_valid_ref(ref: str) -> bool:
    """判断 evidence[].ref 是否命中协议 §2 允许的引用形态。"""
    return any(p.match(ref) for p in REF_PATTERNS)


def _claim_text(ev: dict) -> str:
    """取证据条目的「结论」文本。

    v2.4 的 §2 信封用 used_for（"该证据支撑哪条结论"）承载结论，
    历史 ACP v2.0 用 claim 承载同一语义。两者任一非空即视为已写明结论，
    两者都空才判「claim 必填」。
    """
    for field in ("claim", "used_for"):
        val = ev.get(field)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _check_ref_formats(ev_list: list, *, degraded: bool = False) -> list:
    """证据链校验分支 1：ref 格式。返回失败原因列表（空 = 通过）。

    每条 evidence 必须有非空 ref，且命中协议 §2 允许的引用形态
    （URL / PMID / PMC / DOI / arXiv / path: / state:// / 落盘路径 /
    文件名:行号）。缺失 → evidence[i].ref 缺失；
    格式不匹配 → evidence[i].ref 格式非法: {ref!r}。

    degraded=True（三源全败降置信输出场景）允许 ref 为空——降级场景如实写
    「未检索到」是合规的；但 ref 若非空仍须命中允许形态，避免降级场景
    夹带编造或畸形引用。
    """
    fails = []
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        ref = e.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            if not degraded:
                fails.append(f"evidence[{i}].ref 缺失")
        elif not _is_valid_ref(ref.strip()):
            fails.append(f"evidence[{i}].ref 格式非法: {ref!r}")
    return fails


def _check_degrade_marks(ev_list: list, *, degraded: bool = False) -> list:
    """证据链校验分支 3：降级标注双向约束。返回失败原因列表（空 = 通过）。

    degraded=True（三源全败降置信输出场景）：每条 evidence **必须**出现
    降级标记 source_unavailable（承载位见 DEGRADE_MARKER_FIELDS），
    缺失 → evidence[i] 降级场景缺 source_unavailable 标注。

    degraded=False（非降级场景）：出现降级标记即不合规（降级标记只在降级
    场景可用，否则等于用降级话术掩盖未检索），
    → evidence[i] 非降级场景不应出现 source_unavailable。
    """
    fails = []
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            continue
        marked = _has_source_unavailable(e)
        if degraded:
            if not marked:
                fails.append(f"evidence[{i}] 降级场景缺 source_unavailable 标注")
        elif marked:
            fails.append(f"evidence[{i}] 非降级场景不应出现 source_unavailable")
    return fails


def check_evidence_chain(ev_list: list, *, degraded: bool = False) -> list:
    """证据链三校验（v2.4 主套件调用）。返回失败原因列表，空列表表示通过。

    三类校验：
    1. **ref 格式**：每条 evidence 必须有非空 ref，且命中协议 §2 允许的
       引用形态（URL / PMID / PMC / DOI / arXiv / path: / state:// /
       落盘路径 / 文件名:行号）。缺失 → evidence[i].ref 缺失；
       格式不匹配 → evidence[i].ref 格式非法: {ref!r}。
    2. **GRADE**：复用 check_evidence_grade 的逻辑（grade 枚举 + 结论必填），
       失败原因文案统一为 evidence[i].grade 非法 / evidence[i].claim 必填。
    3. **降级标注**：degraded=True（三源全败降置信输出场景）允许 ref 为空，
       但**必须**在证据条目上出现降级标记，否则失败
       evidence[i] 降级场景缺 source_unavailable 标注；
       反之，非降级场景出现降级标记即不合规，失败
       evidence[i] 非降级场景不应出现 source_unavailable。

    degraded=True 时 ref 缺失不报错（降级场景允许「未检索到」如实标注），
    但 ref 若非空仍须命中允许形态，避免降级场景夹带编造或畸形引用。

    实现要点（口径统一的关键）：
    - v2.4 的 §2 信封用 used_for 承载结论，历史 ACP v2.0 用 claim 承载同一
      语义。校验前把两者归一（claim 为空则用 used_for 补齐），再交给
      check_evidence_grade 判定，避免为 v2.4 另写一套枚举规则。
    - 降级场景允许把降级标记写进 grade 字段（此时 grade 承载的是标记而非
      GRADE 等级），此时不对该条做等级枚举校验。
    """
    if not isinstance(ev_list, list):
        return ["evidence 必须是数组"]

    fails = []
    for i, e in enumerate(ev_list):
        if not isinstance(e, dict):
            fails.append(f"evidence[{i}] 必须是字典")

    # ── 校验 1：ref 格式 ──
    fails.extend(_check_ref_formats(ev_list, degraded=degraded))

    # ── 校验 3：降级标注双向约束 ──
    fails.extend(_check_degrade_marks(ev_list, degraded=degraded))

    # ── 校验 2：GRADE（复用既有 check_evidence_grade，失败文案口径统一）──
    # 归一后再交给既有函数判定，枚举规则只有一份，不重复实现。
    normalized = []
    for e in ev_list:
        if not isinstance(e, dict):
            # 非字典条目已在上面单独报错，此处放一个恒合规占位避免重复报错
            normalized.append({"grade": "4", "claim": "-"})
            continue
        ne = dict(e)
        if not ne.get("claim"):
            # v2.4 用 used_for 承载结论（与 legacy claim 同义）
            ne["claim"] = _claim_text(e)
        if degraded:
            grade_val = ne.get("grade")
            if isinstance(grade_val, str) and SOURCE_UNAVAILABLE_MARK in grade_val:
                # 降级场景允许 grade 字段承载降级标记，此时 grade 承载的是
                # 标记而非 GRADE 等级，按最低合法等级占位、不做等级枚举校验
                ne["grade"] = "5"
        normalized.append(ne)
    fails.extend(check_evidence_grade(normalized))
    return fails


# ─────────────────────────────────────────────────────────────────────
# 集成仿真：阶段流水线（声明一次，随后与 state_io.py 的 PHASES 交叉校验）
# ─────────────────────────────────────────────────────────────────────

# 阶段流水线的唯一声明处。每条声明：
#   stage     阶段名（只在此处声明一次，后续与 state_io.py 的 PHASES 比对）
#   msg_id    本阶段产出的消息 ID
#   dep       本阶段依赖的上游 msg_id（首阶段为空，其余必须非空）
#   upstream  本阶段的上游阶段名（必须出现在更早位置）
#   producers 本阶段参与产出的角色
#   requires  消费本阶段产出所要求的上游参与角色
# 依赖是否真实成立由 run_pipeline_tests 逐条断言，不再靠无条件打印绿灯。
PIPELINE_STAGES = (
    {"stage": "FREEZE",   "msg_id": "msg-001", "dep": "",
     "upstream": (), "producers": ("meta-architect",), "requires": ()},
    {"stage": "IDENTIFY", "msg_id": "msg-002", "dep": "msg-001",
     "upstream": ("FREEZE",), "producers": ("meta-architect",),
     "requires": ("meta-architect",)},
    {"stage": "COLLAPSE", "msg_id": "msg-003", "dep": "msg-002",
     "upstream": ("IDENTIFY",),
     "producers": ("socratic-questioner", "methodological-reviewer"),
     "requires": ("meta-architect",)},
    {"stage": "CLARIFY",  "msg_id": "msg-004", "dep": "msg-003",
     "upstream": ("COLLAPSE",), "producers": ("socratic-questioner",),
     "requires": ("socratic-questioner",)},
    {"stage": "ALIGN",    "msg_id": "msg-005", "dep": "msg-004",
     "upstream": ("CLARIFY",), "producers": ("meta-architect",),
     "requires": ("socratic-questioner",)},
    {"stage": "EXECUTE",  "msg_id": "msg-006", "dep": "msg-005",
     "upstream": ("ALIGN",),
     "producers": ("domain-expert-biomed", "domain-expert-ai",
                   "domain-expert-general"),
     "requires": ("meta-architect",)},
    {"stage": "REVIEW",   "msg_id": "msg-008", "dep": "msg-006",
     "upstream": ("EXECUTE",), "producers": ("methodological-reviewer",),
     "requires": ("domain-expert-biomed",)},
    {"stage": "NEXT",     "msg_id": "msg-010", "dep": "msg-008",
     "upstream": ("REVIEW",), "producers": ("meta-architect",),
     "requires": ("methodological-reviewer",)},
)


def load_state_phases() -> list:
    """按文件路径加载 state_io.py，读出 PHASES 常量（八阶段状态机序列）。

    目录名 research-orchestration-workflow 含连字符，不能用常规 import 语句，
    故用 importlib.util.spec_from_file_location 按路径加载。读不到就抛错，
    不静默回退到内置序列——回退会让「阶段序列一致」这条断言在环境异常时假绿。
    """
    state_io_path = Path(__file__).resolve().parent / "state_io.py"
    if not state_io_path.is_file():
        raise FileNotFoundError(f"找不到 state_io.py: {state_io_path}")
    spec = importlib.util.spec_from_file_location("_pc_state_io", state_io_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法为 {state_io_path} 创建加载规格")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    phases = getattr(module, "PHASES", None)
    if not isinstance(phases, (list, tuple)) or not phases:
        raise AttributeError("state_io.py 未提供可用的 PHASES 常量")
    return list(phases)


def load_agent_ids() -> list | None:
    """读 agents/*.md 文件名集合（与 manifest C13 同源的成员真值源）。

    返回 None = 目录不可读（selftest 副本态只复制单文件）→ 调用方应 SKIP，
    不因环境缺文件而误报。空目录返回 []（fail-closed 交由调用方判红）。
    """
    agents_dir = Path(__file__).resolve().parents[3] / "agents"
    if not agents_dir.is_dir():
        return None
    return sorted(p.stem for p in agents_dir.glob("*.md") if p.is_file())


def run_pipeline_tests() -> tuple:
    """集成仿真：阶段流水线真校验。返回 (用例列表, 通过数, 失败列表)。

    用例为 (名称, 是否通过, 详情) 三元组，失败列表为 (名称, 详情) 二元组。
    两类断言：
    - **阶段序列一致**：PIPELINE_STAGES 的阶段名与顺序必须与 state_io.py 的
      PHASES 逐项相同。
    - **依赖关系成立**：每个非首阶段的 dep 必须非空、且 dep 指向的 msg_id
      必须由更早阶段产出；上游阶段名必须出现在更早位置；requires 声明的
      角色必须已在上游阶段参与。

    此前该段是无条件打印 ✅ 的自证式绿灯（不校验任何东西），现已改为真断言。
    """
    cases = []

    # ── 断言 1：阶段序列与 state_io.py 的 PHASES 一致 ──
    try:
        phases = load_state_phases()
    except Exception as exc:
        # 读不到 state_io.py 属环境异常（不是协议违规），但绝不能静默放行：
        # 若此处回退到内置序列，「阶段序列一致」这条断言在环境异常时会假绿。
        # 失败原因写 stderr（环境异常通道），判定结果仍进失败列表 → 退出码 1。
        detail = f"无法加载 state_io.PHASES: {type(exc).__name__}: {exc}"
        print(f"❌ {detail}", file=sys.stderr)
        cases.append(("阶段序列与 state_io.PHASES 一致", False, detail))
        return cases, 0, [(n, d) for n, ok, d in cases if not ok]

    declared = [s["stage"] for s in PIPELINE_STAGES]
    seq_ok = declared == list(phases)
    cases.append((
        "阶段序列与 state_io.PHASES 一致",
        seq_ok,
        f"{len(declared)} 阶段逐项一致" if seq_ok
        else f"声明序列={declared} 与 state_io.PHASES={list(phases)} 不一致",
    ))

    # ── 断言 2：逐阶段依赖成立 ──
    produced = {}   # 阶段名 → 该阶段产出的 msg_id
    roles = set()   # 已参与阶段的角色集合
    for idx, s in enumerate(PIPELINE_STAGES):
        name = s["stage"]
        dep = s.get("dep", "")
        upstream = s.get("upstream", ())
        problems = []
        if idx > 0:
            if not dep:
                problems.append("dep 为空")
            elif dep not in produced.values():
                problems.append(f"dep {dep} 未由更早阶段产出")
            if not upstream:
                problems.append("未声明上游阶段")
            for u in upstream:
                if u not in produced:
                    problems.append(f"上游阶段 {u} 不在更早位置")
            # dep 必须真的来自声明的上游阶段：声明 upstream=("COLLAPSE",)
            # 就必须依赖 COLLAPSE 产出的 msg_id，否则依赖声明与实际脱节
            #（只查「某个更早阶段产出过」会放过「依赖挂错阶段」这种真缺陷）。
            for u in upstream:
                if u in produced and dep != produced[u]:
                    problems.append(
                        f"dep {dep} 与声明上游 {u} 的产出 {produced[u]} 不一致")
            for r in s.get("requires", ()):
                if r not in roles:
                    problems.append(f"所需角色 {r} 未在上游阶段参与")
        ok = not problems
        detail = (f"dep={dep}" if ok else "；".join(problems))
        cases.append((f"阶段 {name} 依赖成立", ok, detail))
        produced[name] = s.get("msg_id", "")
        roles.update(s.get("producers", ()))

    # ── 断言 3：流水线成员引用 ⊆ agents/*.md 真值源 ──
    # R2 审计实锤（B16b）：producers 注入幽灵成员 ID（GHOST-MEMBER）时集成套件
    # 仍 rc=0——「阶段依赖成立」断言只查引用是否在上游参与过，不查引用是否是
    # 真实存在的成员。真值源与 manifest C13 同源（agents/*.md 文件名）；
    # 目录不可读（selftest 单文件副本态）时 SKIP 不误报，目录为空时 fail-closed。
    agent_ids = load_agent_ids()
    if agent_ids is None:
        cases.append(("流水线成员引用 ⊆ agents/*.md 真值源", True,
                      "SKIP：agents/ 目录不可读（单文件副本态），不误报"))
    elif not agent_ids:
        cases.append(("流水线成员引用 ⊆ agents/*.md 真值源", False,
                      "agents/*.md 真值源为空（空集合一律判红）"))
    else:
        truth = set(agent_ids)
        ghosts = sorted(roles - truth)
        ok = not ghosts
        cases.append(("流水线成员引用 ⊆ agents/*.md 真值源", ok,
                      f"引用 {len(roles)} 个成员全部真实存在" if ok
                      else f"幽灵成员 ID（不在 agents/*.md）: {ghosts}"))

    failures = [(n, d) for n, ok, d in cases if not ok]
    return cases, len(cases) - len(failures), failures


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
                    "meta-architect": 2, "socratic-questioner": 1, "synthesis-integrator": 1,
                    # v2.1.2 atomic 继承原 domain-expert 权重
                    "domain-expert-biomed": 3, "domain-expert-ai": 3, "domain-expert-general": 3},
    "domain_fact": {"domain-expert": 5, "methodological-reviewer": 4,
                    "meta-architect": 2, "socratic-questioner": 1, "synthesis-integrator": 1,
                    "domain-expert-biomed": 5, "domain-expert-ai": 5, "domain-expert-general": 5},
    "structure":    {"meta-architect": 5, "socratic-questioner": 3,
                    "domain-expert": 2, "methodological-reviewer": 2, "synthesis-integrator": 1,
                    "domain-expert-biomed": 2, "domain-expert-ai": 2, "domain-expert-general": 2},
}

DEFAULT_AUTHORITY = {"methodological-reviewer": 5, "domain-expert": 4,
                     "meta-architect": 3, "socratic-questioner": 2, "synthesis-integrator": 1,
                     # v2.1.2 atomic 继承原 domain-expert 默认权重
                     "domain-expert-biomed": 4, "domain-expert-ai": 4, "domain-expert-general": 4}


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

# 已废弃 ACP v2.0 历史 fixture（仅供 run_legacy_envelope_tests 回归）
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

# 当前 result_envelope v2.4 fixture（6 必填 + 常见扩展字段）
ENVELOPE_OK_V24 = {
    "agent_id": "domain-expert-biomed",
    "task_id": "task-v24-001",
    "phase": "EXECUTE",
    "status": "success",
    "confidence": 88,
    "deliverable_summary": "完成领域检索与证据评级",
    "type": "RESULT",
    "trace_id": "trace-v24-001",
    "msg_id": "msg-001-domain-expert-biomed",
    "parent_msg_id": "msg-000",
    "context_ref": {"mode": "summary", "pointer": "state://cp-006"},
    "evidence": [
        {"type": "source", "ref": "PMC11187424",
         "used_for": "2543 不足以支撑 DL", "grade": "2a", "recency": "近12月"}
    ],
    "issues": [],
    "next_agent_hint": "methodological-reviewer",
    "metrics": {"duration_ms": 0, "retry_count": 0},
    "payload": {"result": "test"},
}


def check_envelope_full(env: dict, *, degraded: bool = False) -> list:
    """v2.4 主套件的统一校验入口：信封 + 证据链 + HANDOFF 回引硬约束。

    这是「当前协议合规判定」的唯一入口，三层校验一次跑完：
    1. **信封层**（check_envelope）：6 必填字段 / status 四值 / confidence /
       type 枚举 / evidence 数组 / context_ref.mode。
    2. **证据链层**（check_evidence_chain）：ref 格式 + GRADE + 降级标注。
       只对 EVIDENCE_PRODUCERS_V24 成员（执行者/审查者）强制——分析者与
       整合者按协议 §2 本就不产出事实性证据，evidence[] 可为空。
    3. **HANDOFF 回引层**：type == "HANDOFF" 的信封必须带合法 context_ref
       （协议 §8 的 HANDOFF 回传硬约束，把 §2 的「推荐」在此类型上升级为
       「必填」）。

    degraded=True：三源全败降置信输出场景，证据链层进入降级口径
    （ref 允许缺失，但必须逐条标注 source_unavailable）。
    """
    is_handoff = isinstance(env, dict) and env.get("type") == "HANDOFF"
    # 只调一次 check_envelope：分开调会把同一处缺陷报两遍（如 mode 非法
    # 与 context_ref 必填重复出现），失败原因列表要求一条缺陷一条原因。
    fails = list(check_envelope(
        env,
        producer_must_have_evidence=True,
        require_context_ref=is_handoff,
    ))
    ev_list = env.get("evidence") if isinstance(env, dict) else None
    if isinstance(ev_list, list) and ev_list:
        # 仅执行者/审查者受证据链约束（协议 §2：分析者、整合者可为空）
        if env.get("agent_id") in EVIDENCE_PRODUCERS_V24:
            fails.extend(check_evidence_chain(ev_list, degraded=degraded))
    return fails


def run_envelope_v24_tests() -> tuple:
    """result_envelope v2.4 主套件。返回 (用例列表, 通过数, 失败列表)。"""
    cases = []

    # V0：完整 fixture（6 必填 + 常见扩展字段）合规
    # 走 check_envelope_full（信封 + 证据链 + HANDOFF 回引三层一起校验），
    # 证明主套件真的在跑证据链校验，而不是只查信封字段。
    cases.append(("V0 完整 v2.4 fixture 合规",
                  check_envelope_full(ENVELOPE_OK_V24), []))

    # V1：合法 6 字段（无任何扩展字段）→ 空失败列表
    minimal = {k: ENVELOPE_OK_V24[k] for k in REQUIRED_FIELDS_V24}
    cases.append(("V1 合法 6 字段（无扩展字段）", check_envelope(minimal), []))

    # V2：原 ACP UPPERCASE SUCCESS 已弃用 → 命中「status 非法」
    bad = dict(ENVELOPE_OK_V24); bad["status"] = "SUCCESS"
    cases.append(("V2 status=SUCCESS（大写已弃用）", check_envelope(bad),
                  ["status 非法: 'SUCCESS'"]))

    # V3：缺 deliverable_summary → 命中「缺少字段」
    bad = {k: v for k, v in ENVELOPE_OK_V24.items() if k != "deliverable_summary"}
    cases.append(("V3 缺 deliverable_summary", check_envelope(bad),
                  ["缺少字段: deliverable_summary"]))

    # V4：confidence 越界 → 命中「confidence 非法」
    bad = dict(ENVELOPE_OK_V24); bad["confidence"] = 150
    cases.append(("V4 confidence=150 越界", check_envelope(bad),
                  ["confidence 非法: 150（应为 0-100）"]))

    # V5：evidence 非数组 → 命中「evidence 必须是数组」
    bad = dict(ENVELOPE_OK_V24); bad["evidence"] = "not-a-list"
    cases.append(("V5 evidence 非数组", check_envelope(bad),
                  ["evidence 必须是数组"]))

    # V6：执行者缺 evidence → 命中（用 agent_id 判定）
    bad = {k: v for k, v in ENVELOPE_OK_V24.items() if k != "evidence"}
    cases.append(("V6 执行者缺 evidence", check_envelope(bad, producer_must_have_evidence=True),
                  ["执行者/审查者产出必带 evidence[]（domain-expert-biomed）"]))

    # V7：分析者 socratic-questioner 的 evidence 合法为空 → 无失败
    anlz = dict(ENVELOPE_OK_V24)
    anlz["agent_id"] = "socratic-questioner"
    anlz["evidence"] = []
    cases.append(("V7 分析者 evidence 合法为空",
                  check_envelope(anlz, producer_must_have_evidence=True), []))

    # V8：context_ref.mode 非法 → 命中
    bad = dict(ENVELOPE_OK_V24); bad["context_ref"] = {"mode": "all", "pointer": "x"}
    cases.append(("V8 context_ref.mode 非法", check_envelope(bad),
                  ["context_ref.mode 非法: 'all'"]))

    # V9：type 非法 → 命中
    bad = dict(ENVELOPE_OK_V24); bad["type"] = "MESSAGE"
    cases.append(("V9 type 非法", check_envelope(bad),
                  ["type 非法: 'MESSAGE'"]))

    # V10：context_ref 数组形态且 mode 合法 → 无失败
    good = dict(ENVELOPE_OK_V24)
    good["context_ref"] = [
        {"mode": "full", "pointer": "state://cp-001"},
        {"mode": "ref", "pointer": "state://cp-002"},
    ]
    cases.append(("V10 context_ref 数组形态合法", check_envelope(good), []))

    # V11：confidence 非数值 → 命中
    bad = dict(ENVELOPE_OK_V24); bad["confidence"] = "high"
    cases.append(("V11 confidence 非数值", check_envelope(bad),
                  ["confidence 非法: 'high'（应为 0-100）"]))

    # V12：status 小写四值均合法
    for s in ("success", "partial", "failed", "blocked"):
        good = dict(ENVELOPE_OK_V24); good["status"] = s
        cases.append((f"V12 status={s} 合法", check_envelope(good), []))

    # ── A2：证据链三校验（ref 格式 / GRADE / 降级标注）──
    # V13：ref 格式非法 → 命中「ref 格式非法」
    bad = dict(ENVELOPE_OK_V24)
    bad["evidence"] = [{"type": "source", "ref": "这是一段没有格式的乱码",
                        "used_for": "支撑结论", "grade": "2a"}]
    cases.append(("V13 evidence.ref 格式非法",
                  check_envelope_full(bad),
                  ["evidence[0].ref 格式非法: '这是一段没有格式的乱码'"]))

    # V14：ref 缺失 → 命中「ref 缺失」
    bad = dict(ENVELOPE_OK_V24)
    bad["evidence"] = [{"type": "source", "used_for": "支撑结论", "grade": "2a"}]
    cases.append(("V14 evidence.ref 缺失",
                  check_envelope_full(bad),
                  ["evidence[0].ref 缺失"]))

    # V15：GRADE 越界 → 命中「grade 非法」（复用 check_evidence_grade）
    bad = dict(ENVELOPE_OK_V24)
    bad["evidence"] = [{"type": "source", "ref": "PMID:12345678",
                        "used_for": "支撑结论", "grade": "6"}]
    cases.append(("V15 evidence.grade 越界",
                  check_envelope_full(bad),
                  ["evidence[0].grade 非法: '6'"]))

    # V16：结论字段缺失（claim 与 used_for 都空）→ 命中「claim 必填」
    bad = dict(ENVELOPE_OK_V24)
    bad["evidence"] = [{"type": "source", "ref": "PMID:12345678", "grade": "2a"}]
    cases.append(("V16 evidence 结论字段缺失",
                  check_envelope_full(bad),
                  ["evidence[0].claim 必填"]))

    # V17：非降级场景出现降级标记 → 不合规
    bad = dict(ENVELOPE_OK_V24)
    bad["evidence"] = [{"type": "source", "ref": "PMID:12345678",
                        "used_for": "支撑结论 source_unavailable", "grade": "2a"}]
    cases.append(("V17 非降级场景出现 source_unavailable",
                  check_envelope_full(bad),
                  ["evidence[0] 非降级场景不应出现 source_unavailable"]))

    # V18：降级场景缺降级标记 → 不合规（degraded=True 时 ref 缺失不报）
    bad = dict(ENVELOPE_OK_V24)
    bad["status"] = "partial"
    bad["evidence"] = [{"type": "source", "used_for": "三源全败", "grade": "2a"}]
    cases.append(("V18 降级场景缺 source_unavailable 标注",
                  check_envelope_full(bad, degraded=True),
                  ["evidence[0] 降级场景缺 source_unavailable 标注"]))

    # V19：降级场景标注齐全 → 合规（status 取 partial，禁止 success）
    good = dict(ENVELOPE_OK_V24)
    good["status"] = "partial"
    good["confidence"] = 35
    good["evidence"] = [{"type": "source", "ref": "",
                          "used_for": "三源全败 source_unavailable：超时",
                          "grade": "source_unavailable"}]
    cases.append(("V19 降级场景标注齐全合规",
                  check_envelope_full(good, degraded=True), []))

    # V20：分析者（socratic-questioner）evidence 为空 → 证据链不适用，合规
    anlz = dict(ENVELOPE_OK_V24)
    anlz["agent_id"] = "socratic-questioner"
    anlz["evidence"] = []
    cases.append(("V20 分析者 evidence 空不受证据链约束",
                  check_envelope_full(anlz), []))

    # ── A3：HANDOFF 的 context_ref 必填 ──
    # V21：HANDOFF 缺 context_ref → 命中「context_ref 必填」
    ho = dict(ENVELOPE_OK_V24)
    ho["type"] = "HANDOFF"
    ho.pop("context_ref")
    cases.append(("V21 HANDOFF 缺 context_ref",
                  check_envelope_full(ho),
                  ["context_ref 必填"]))

    # V22：HANDOFF 的 context_ref 为空 dict → 命中「context_ref 必填」
    ho = dict(ENVELOPE_OK_V24)
    ho["type"] = "HANDOFF"
    ho["context_ref"] = {}
    cases.append(("V22 HANDOFF 的 context_ref 为空",
                  check_envelope_full(ho),
                  ["context_ref 必填"]))

    # V23：HANDOFF 带合法 context_ref → 合规
    ho = dict(ENVELOPE_OK_V24)
    ho["type"] = "HANDOFF"
    ho["context_ref"] = {"mode": "ref", "pointer": "state://cp-006"}
    cases.append(("V23 HANDOFF 带合法 context_ref", check_envelope_full(ho), []))

    # V24：非 HANDOFF 类型缺 context_ref → 仍是「推荐」，不合规性不成立
    nr = dict(ENVELOPE_OK_V24)
    nr.pop("context_ref")
    cases.append(("V24 非 HANDOFF 缺 context_ref 仍为推荐", check_envelope_full(nr), []))

    # ── A5：context_ref.pointer 形态校验 ──
    # V25：pointer 形态非法 → 命中「pointer 格式非法」
    bad = dict(ENVELOPE_OK_V24)
    bad["context_ref"] = {"mode": "ref", "pointer": "这不是一个合法指针"}
    cases.append(("V25 context_ref.pointer 格式非法",
                  check_envelope_full(bad),
                  ["context_ref.pointer 格式非法: '这不是一个合法指针'"]))

    # V26：mode=ref 但缺 pointer → ref 模式靠指针定位，缺指针无意义
    bad = dict(ENVELOPE_OK_V24)
    bad["context_ref"] = {"mode": "ref"}
    cases.append(("V26 mode=ref 缺 pointer",
                  check_envelope_full(bad),
                  ["context_ref.pointer 缺失"]))

    # V27：mode=full 时 pointer 可空 → 合规（full 本就是全量拷贝）
    good = dict(ENVELOPE_OK_V24)
    good["context_ref"] = {"mode": "full"}
    cases.append(("V27 mode=full pointer 可空", check_envelope_full(good), []))

    # V28：mode=summary 时 pointer 可空 → 合规
    good = dict(ENVELOPE_OK_V24)
    good["context_ref"] = {"mode": "summary"}
    cases.append(("V28 mode=summary pointer 可空", check_envelope_full(good), []))

    # V29：list 形态中某条 pointer 非法 → 命中并带下标定位
    bad = dict(ENVELOPE_OK_V24)
    bad["context_ref"] = [
        {"mode": "ref", "pointer": "state://cp-001"},
        {"mode": "ref", "pointer": "坏指针"},
    ]
    cases.append(("V29 list 形态第 2 条 pointer 格式非法",
                  check_envelope_full(bad),
                  ["context_ref[1].pointer 格式非法: '坏指针'"]))

    # V30：HANDOFF 的 pointer 是非 cp-* 的 state:// 路径段 → 死引用，失败
    # （HANDOFF 的回引要覆盖全部 cp-*，只有 cp-* 指针才可能构成覆盖）
    ho = dict(ENVELOPE_OK_V24)
    ho["type"] = "HANDOFF"
    ho["context_ref"] = {"mode": "ref", "pointer": "state://phase2/xxx"}
    cases.append(("V30 HANDOFF 的 pointer 非 cp-* 形态",
                  check_envelope_full(ho),
                  ["context_ref.pointer 格式非法: 'state://phase2/xxx'"]))

    # V31：HANDOFF 的 pointer 是 cp-* → 合规
    ho = dict(ENVELOPE_OK_V24)
    ho["type"] = "HANDOFF"
    ho["context_ref"] = {"mode": "ref", "pointer": "state://cp-006"}
    cases.append(("V31 HANDOFF 的 pointer 为 cp-* 形态", check_envelope_full(ho), []))

    # V32：非 HANDOFF 的 pointer 是 state:// 路径段 → 仍合法
    # （协议 §4 的通用回引指针允许 state:// + 路径段，不限 cp-*）
    nr = dict(ENVELOPE_OK_V24)
    nr["context_ref"] = {"mode": "ref", "pointer": "state://phase2/xxx"}
    cases.append(("V32 非 HANDOFF 的 state:// 路径段 pointer 合法",
                  check_envelope_full(nr), []))

    # V33：list 形态含非 dict 元素 → 显式失败，不崩溃
    bad = dict(ENVELOPE_OK_V24)
    bad["context_ref"] = ["不是字典"]
    cases.append(("V33 context_ref list 含非 dict 元素",
                  check_envelope_full(bad),
                  ["context_ref[0] 必须是字典"]))

    passed = 0
    failures = []
    for name, fails, expected in cases:
        if fails == expected:
            passed += 1
        else:
            failures.append((name, fails, expected))
    return cases, passed, failures


def run_legacy_envelope_tests() -> tuple:
    """ACP v2.0 历史 fixture 回归（不用于当前协议合规判定）。

    12 个 U1–U12 用例原样迁移，仅把 check_envelope 换成 check_envelope_v20，
    期望文案一字未改。返回 (用例列表, 通过数, 失败列表)。
    """
    cases = []

    # U1: 标准合规
    cases.append(("U1 信封合规", check_envelope_v20(ENVELOPE_OK, producer_must_have_evidence=True), []))

    # U2: 执行者（producer）缺 evidence 必报错
    bad = {k: v for k, v in ENVELOPE_OK.items() if k != "evidence"}
    cases.append(("U2 执行者缺 evidence", check_envelope_v20(bad, producer_must_have_evidence=True),
                  ["执行者/审查者产出必带 evidence[]（domain-expert）"]))

    # U3: 版本错误
    bad = dict(ENVELOPE_OK); bad["v"] = "1.0"
    cases.append(("U3 版本非 v2.0", check_envelope_v20(bad),
                  ["协议版本错误: v='1.0'（应为 '2.0'）"]))

    # U4: confidence 越界
    bad = dict(ENVELOPE_OK); bad["confidence"] = 150
    cases.append(("U4 confidence 越界", check_envelope_v20(bad),
                  ["confidence 非法: 150（应为 0-100）"]))

    # U5: evidence 非数组（此前该分支从未被测试覆盖）
    bad = dict(ENVELOPE_OK); bad["evidence"] = "not-a-list"
    cases.append(("U5 evidence 非数组", check_envelope_v20(bad),
                  ["evidence 必须是数组"]))

    # U6: context_ref.mode 非法
    bad = dict(ENVELOPE_OK); bad["context_ref"] = {"mode": "all", "pointer": "x"}
    cases.append(("U6 context_ref.mode 非法", check_envelope_v20(bad),
                  ["context_ref.mode 非法: 'all'"]))

    # U7: status 非法
    bad = dict(ENVELOPE_OK); bad["status"] = "OK"
    cases.append(("U7 status 非法", check_envelope_v20(bad),
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
    cases.append(("U10 type 非法", check_envelope_v20(bad),
                  ["type 非法: 'MESSAGE'"]))

    # U11: context_ref 数组模式
    bad = dict(ENVELOPE_OK); bad["context_ref"] = [
        {"mode": "ref", "pointer": "a"}, {"mode": "summary", "pointer": "b"}]
    cases.append(("U11 context_ref 数组模式", check_envelope_v20(bad), []))

    # U12: 分析者 evidence 可空
    anlz = dict(ENVELOPE_OK); anlz["from"] = "socratic-questioner"; anlz["evidence"] = []
    cases.append(("U12 分析者 evidence 合法为空", check_envelope_v20(anlz), []))

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
        pointer = cr.get("pointer", "") if isinstance(cr, dict) else ""
        if pointer:
            covered.add(pointer)
    # 覆盖层补一道 pointer 形态校验：形态错的 pointer 既不计入覆盖、也不报错，
    # 原本会静默通过（漏检）。这里显式计入失败原因。
    missing = [cp for cp in checkpoints if cp not in covered]
    # 覆盖层的 pointer 必须是检查点指针（cp-*）：非 cp-* 指针是死引用，
    # 既不计入覆盖也不报错 → 原实现会静默通过（漏检）。
    return missing + _invalid_pointers(context_refs, require_checkpoint=True)


# ─────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────

def main():
    failed = 0
    suite = sys.argv[1] if len(sys.argv) > 1 else "all"

    if suite in ("all", "envelope"):
        # ── 主套件：result_envelope v2.4（当前 SSOT §2）──
        cases, passed, failures = run_envelope_v24_tests()
        failed += len(failures)
        total = len(cases)
        print(f"\n── result_envelope v2.4 主套件：{passed}/{total} 通过 ──")
        for name, fails, expected in cases:
            mark = "✅" if fails == expected else "❌"
            print(f"  {mark} {name}")
            if fails != expected:
                print(f"      ↳ 实际: {fails}")
                print(f"      ↳ 期望: {expected}")
            elif fails:
                for line in fails:
                    print(f"      ↳ 已检出: {line}")

        # ── 历史 fixture 回归：已废弃 ACP v2.0，不参与当前协议合规判定 ──
        cases, passed, failures = run_legacy_envelope_tests()
        failed += len(failures)
        total = len(cases)
        print(f"\n── ACP v2.0 历史 fixture 回归（不用于当前协议合规判定）：{passed}/{total} 通过 ──")
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
        failed += len(failures)
        print(f"\n── 冲突仲裁套件：{passed}/{len(cases)} 通过 ──")
        for name, r, exp_winner, exp_rule, exp_esc in cases:
            mark = "✅" if (r["rule"] == exp_rule and r["winner"] == exp_winner
                           and r.get("escalated") == exp_esc) else "❌"
            esc = f"  escalated={r.get('escalated')!r}" if r.get("escalated") else ""
            print(f"  {mark} {name}  →  winner={r['winner']!r}  rule={r['rule']}{esc}")

    if suite in ("all", "integration"):
        print("\n── 集成仿真：状态机流水线 + HANDOFF 回引链校验 ──")
        # 真校验：阶段序列与 state_io.py 的 PHASES 交叉比对 + 阶段间依赖成立。
        # 此前该处是无条件打印 ✅ 的自证式绿灯（不校验任何东西），现已改为真断言；
        # 任一断言失败即 failed += 1 并打印 ❌，从而真正拦住退出码。
        cases, passed, failures = run_pipeline_tests()
        failed += len(failures)
        print(f"\n  阶段流水线校验：{passed}/{len(cases)} 通过")
        for name, ok, detail in cases:
            mark = "✅" if ok else "❌"
            print(f"  {mark} {name}  {detail}")

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
        if not ok:
            failed += 1
        print(f"  {'✅' if ok else '❌'} 合规回引：覆盖 {len(checkpoints)-len(missing)}/{len(checkpoints)} 检查点"
              + (f"，缺失 {missing}" if missing else ""))
        # 违规案例：漏 cp-008，必须被检出
        missing = check_handoff_coverage(checkpoints, ok_refs[:-1])
        if missing != ['state://cp-008']:
            failed += 1
        print(f"  {'✅ 正确检出' if missing == ['state://cp-008'] else '❌ 未检出'} 违规回引：缺失 {missing}")

        # 违规案例：pointer 形态非法（如 state://phase2/xxx 这类非检查点指针），
        # 既不计入覆盖也不报错 → 原实现会静默通过，覆盖层必须显式检出。
        # 关键设计：其余 8 个 cp 全部正常覆盖，只多出一条形态非法的条目 ——
        # 这样「覆盖完整」与「形态非法」两个维度互不干扰，才能**单独**证明
        # 形态校验生效（若只用一条非法条目，missing 必然非空，形态校验失效时
        # 也会误判为「检出」，属假绿）。
        bad_refs = list(ok_refs) + [{"mode": "ref", "pointer": "state://phase2/xxx"}]
        bad_result = check_handoff_coverage(checkpoints, bad_refs)
        bad_ok = (len(bad_result) == 1
                  and bad_result[0].startswith("context_ref.pointer 格式非法"))
        if not bad_ok:
            failed += 1
        print(f"  {'✅ 正确检出' if bad_ok else '❌ 未检出'} 违规回引：pointer 形态非法 → {bad_result}")

    print()
    print(f"[rc] failed={failed} → {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
