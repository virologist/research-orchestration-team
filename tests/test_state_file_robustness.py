#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""状态文件健壮性 / 检查点一致性 / 孤儿 tmp 清理的注入式锁定（R7）

=====================================================================
R6 把「运行时序与终态污染」查完了，R7 转向 §10.5 里仍未覆盖的方向：
**状态文件本身的健壮性**（半损坏状态文件）、**跨层一致性**（协议 §3 的
检查点编号约定 vs 落盘实现）、**崩溃恢复**（SIGKILL 留下的孤儿 tmp）。

R7 Phase A 做了 11 组状态文件实验，实锤 2 个 P0 + 3 个 P1：

  P0-1 半损坏状态文件 → 裸 Traceback（E7，13 组组合命中）：
    `load_state` 原先只做 JSON 解析层校验。文件是**合法 JSON 但缺关键
    字段**时（被外部改写 / 旧版本状态文件 / 部分写盘后编辑），下游子命令
    直接 `state["phase"]` / `state["status"]` → 裸 KeyError Traceback。
    违反「业务报错必须有可读文案、无裸 Traceback」的既有契约。
  P0-2 缺 status 时 budget/fail 假绿（E8）：
    `budget` / `fail` 在状态文件缺 `status` 时 **rc=0 放行**，把「未知
    状态」静默当成 running 处理并继续写盘——凭空替主理人断言了状态。
  P1-1 budget 触顶文案宣称「熔断」实为告警（E9）：
    registry §Loop 终止硬上限明确把 turns/tokens 定为**告警层**（主理人
    语义裁量），只有 max_time/failures 是**终态熔断层**。原文案写「按协议
    熔断」会让调用方以为 status 已变 aborted、后续推进会被拒，实际
    status 仍是 running、advance 照常放行——文案与行为脱节
    （FM-R2-03 同族复发：语义分层在压缩成一句话时丢失关键限定）。
  P1-2 检查点编号与阶段序号解耦（E3，三处）：
    协议 §3 约定「检查点编号 = 阶段序号」（cp-001=FREEZE…）。原实现只
    校验**形态**（cp-[0-9]{3,}），不校验编号一致性，于是：
      - 编号可以乱写（第 1 个阶段记成 cp-007）；
      - 同一编号可被复用（checkpoints 里出现两条 state://cp-007）；
      - marker 因 `if not marker.exists()` 永不重写，与状态文件脱节。
  P1-3 SIGKILL 崩溃留下孤儿 tmp（E1/E5）：
    tmp 名带 PID 隔离并发写者；进程在 write_text 与 os.replace 之间被杀
    就留下 `_state.json.tmp.<pid>`，此后**永远不会被清理**——反复崩溃即
    无界堆积的磁盘泄漏。

本文件把这些行为**锁死**：任何一处被改回去，本测试立即红。

用例（12 条）：
  R1 缺 status 的状态文件 → budget 拒绝（rc=3），无裸 Traceback   ← P0-1
  R2 缺 phase 的状态文件 → resume 拒绝（rc=3），无裸 Traceback    ← P0-1
  R3 缺 task_id 的状态文件 → finish 拒绝（rc=3），无裸 Traceback  ← P0-1
  R4 缺 turn 的状态文件 → advance 拒绝（rc=3），无裸 Traceback    ← P0-1
  R5 空对象状态文件 → init 拒绝（rc=3），无裸 Traceback           ← P0-1
  R6 status 取值非法 → 拒绝（rc=3），不静默当成 running          ← P0-2
  R7 phase 取值非法 → 拒绝（rc=3）                               ← P0-2
  R8 turn 为 bool → 拒绝（rc=3，bool 不算 int）                   ← P0-1
  R9 结构损坏时状态文件不被改写（护栏完整性）                     ← P0-1
  R10 budget 触顶文案是「告警层」而非「熔断」                    ← P1-1
  R11 检查点编号必须等于阶段序号（乱写/复用均拒）                ← P1-2
  R12 孤儿 tmp 被清理（写盘后不再残留）                           ← P1-3

纪律（见 docs/harness-iteration-loop.md §10.3.2 / FM-R2-06）：
  - 每条用例独立临时目录，逐条独立取 rc，不串成一条命令只看整体 rc；
  - 负例不仅断言 rc 翻转，还要断言**失败原因归属于被测分支**
    （输出含业务报错文案、且无 Traceback），避免被无关校验抢先拦截造成假检出；
  - 自包含：只依赖标准库与本包文件，包根向上逐层探测标志目录，
    不用 `parents[N]` 硬索引（Linux /tmp 浅层布局会 IndexError）。

运行：python3 tests/test_state_file_robustness.py
退出码：0 = 全部通过；1 = 有用例失败；2 = 环境错误。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ── 包根定位：向上逐层找「同时存在 agents/ 与 .codebuddy-plugin/」的目录 ──
def _find_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "agents").is_dir() and (parent / ".codebuddy-plugin").is_dir():
            return parent
    raise RuntimeError("找不到包根：向上未探测到 agents/ + .codebuddy-plugin/ 标志目录")


ROOT = _find_root()
STATE_IO = ROOT / "skills" / "research-orchestration-workflow" / "scripts" / "state_io.py"
CASES = []


def case(cid, desc, fn):
    """登记一条用例。fn() -> (通过?, 明细)。"""
    CASES.append((cid, desc, fn))


def run(*args) -> tuple:
    """执行一次 state_io 子命令，返回 (rc, stdout+stderr)。"""
    p = subprocess.run([sys.executable, str(STATE_IO), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read_state(ws: Path, task: str) -> dict:
    """读落盘状态文件（判定唯一真值源）。"""
    return json.loads(
        (ws / ".harness-runs" / task / "_state.json").read_text(encoding="utf-8")
    )


def write_raw_state(ws: Path, task: str, payload: dict) -> None:
    """把状态文件替换为指定内容（合法 JSON，但字段可缺失/非法）。"""
    (ws / ".harness-runs" / task / "_state.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def no_traceback(out: str) -> bool:
    """输出里不得出现裸 Traceback——业务报错必须有可读文案。"""
    return "Traceback (most recent call last)" not in out


def corrupt_case(cid, desc, payload, cmd_args, expect_field):
    """构造一条「半损坏状态文件」用例。

    断言三件事（缺一不可，FM-R2-06）：
      1. rc == 3（fail fast，与 JSON 损坏同级）；
      2. 输出**指名具体字段**（证明失败原因归属结构校验分支，
         而非被别处的校验抢先拦截）；
      3. 无裸 Traceback。
    """
    def fn():
        with tempfile.TemporaryDirectory(prefix=f"r7-{cid.lower()}-") as tmp:
            ws = Path(tmp)
            run("init", "--task-id", "t", "--workspace", str(ws))
            write_raw_state(ws, "t", payload)
            rc, out = run(cmd_args[0], "--task-id", "t", "--workspace", str(ws),
                          *cmd_args[1:])
            ok = (rc == 3
                  and expect_field in out
                  and no_traceback(out))
            detail = (f"rc={rc}（期望 3）"
                      f"字段提示含 {expect_field!r}={'是' if expect_field in out else '否'}"
                      f" 无Traceback={'是' if no_traceback(out) else '否'}")
            return ok, detail
    case(cid, desc, fn)


# ── R1 ~ R8：半损坏状态文件必须 fail fast，禁止裸 Traceback ──────────

corrupt_case(
    "R1", "缺 status 的状态文件 → budget 拒绝（rc=3），无裸 Traceback",
    {"task_id": "t", "turn": 0, "phase": "FREEZE", "checkpoints": []},
    ("budget", "--turns", "5"), "status",
)

corrupt_case(
    "R2", "缺 phase 的状态文件 → resume 拒绝（rc=3），无裸 Traceback",
    {"task_id": "t", "turn": 0, "status": "running", "checkpoints": []},
    ("resume",), "phase",
)

corrupt_case(
    "R3", "缺 task_id 的状态文件 → finish 拒绝（rc=3），无裸 Traceback",
    {"turn": 0, "status": "running", "phase": "FREEZE", "checkpoints": []},
    ("finish",), "task_id",
)

corrupt_case(
    "R4", "缺 turn 的状态文件 → advance 拒绝（rc=3），无裸 Traceback",
    {"task_id": "t", "status": "running", "phase": "FREEZE", "checkpoints": []},
    ("advance", "--phase", "FREEZE"), "turn",
)

corrupt_case(
    "R5", "空对象状态文件 → init 拒绝（rc=3），无裸 Traceback",
    {},
    ("init",), "缺字段",
)

corrupt_case(
    "R6", "status 取值非法 → 拒绝（rc=3），不静默当成 running",
    {"task_id": "t", "turn": 0, "phase": "FREEZE", "checkpoints": [],
     "status": "paused"},
    ("budget", "--turns", "5"), "status",
)

corrupt_case(
    "R7", "phase 取值非法 → 拒绝（rc=3）",
    {"task_id": "t", "turn": 0, "phase": "BOGUS", "checkpoints": [],
     "status": "running"},
    ("resume",), "phase",
)

corrupt_case(
    "R8", "turn 为 bool → 拒绝（rc=3，bool 不算 int）",
    {"task_id": "t", "turn": True, "phase": "FREEZE", "checkpoints": [],
     "status": "running"},
    ("advance", "--phase", "FREEZE"), "turn",
)


# ── R9：结构损坏时状态文件不被改写（护栏完整性）─────────────────────

def case_r9_corrupt_state_untouched():
    """R9：结构损坏被拒后，状态文件**逐字节未变**。

    防止「校验失败但顺手把文件规范化/补全了」这类半修复——那等于
    静默重建（R7 P0-1 的处置口径明确禁止）。
    """
    with tempfile.TemporaryDirectory(prefix="r7-r9-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t", "--workspace", str(ws))
        payload = {"task_id": "t", "turn": 0, "phase": "FREEZE"}
        write_raw_state(ws, "t", payload)
        sp = ws / ".harness-runs" / "t" / "_state.json"
        before = sp.read_bytes()
        rc, out = run("budget", "--task-id", "t", "--workspace", str(ws),
                      "--turns", "5")
        after = sp.read_bytes()
        ok = (rc == 3 and before == after and no_traceback(out))
        return ok, (f"rc={rc}（期望 3）文件未变={'是' if before == after else '否'}"
                    f" 无Traceback={'是' if no_traceback(out) else '否'}")


case("R9", "结构损坏被拒后状态文件逐字节未变（不静默重建）",
     case_r9_corrupt_state_untouched)


# ── R10：budget 触顶文案必须表达「告警层」，不能宣称「熔断」 ─────────

def case_r10_budget_ceiling_is_warning_not_circuit_break():
    """R10：budget 触顶文案是**告警层**，不是「熔断」。

    registry §Loop 终止硬上限把 turns/tokens 定为告警层（主理人裁量），
    只有 max_time/failures 才是终态熔断层。文案若写「熔断」，调用方会
    误以为 status 已变 aborted、后续推进会被拒——实际 status 仍是
    running、advance 照常放行。
    """
    with tempfile.TemporaryDirectory(prefix="r7-r10-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t", "--workspace", str(ws))
        rc, out = run("budget", "--task-id", "t", "--workspace", str(ws),
                      "--turns", "999")
        st = read_state(ws, "t")
        has_warn = "告警" in out
        wrongly_says_break = "按协议熔断" in out
        still_running = st.get("status") == "running"
        # 文案必须既表明是告警层、又不得宣称已熔断；且实际未熔断
        ok = (rc == 0 and has_warn and not wrongly_says_break
              and still_running and no_traceback(out))
        return ok, (f"rc={rc} 含告警字样={'是' if has_warn else '否'} "
                    f"误称熔断={'是' if wrongly_says_break else '否'} "
                    f"status={st.get('status')!r}（期望 running）")


case("R10", "budget 触顶文案表达「告警层」而非「熔断」",
     case_r10_budget_ceiling_is_warning_not_circuit_break)


# ── R11：检查点编号必须等于阶段序号 ──────────────────────────────────

def case_r11_checkpoint_number_must_match_turn():
    """R11：检查点编号 ≡ 阶段序号；乱写与复用均被拒。

    协议 §3 约定「检查点编号 = 阶段序号」（cp-001=FREEZE、cp-002=IDENTIFY…）。
    protocol_check 的 HANDOFF 覆盖校验按这个约定动态生成 cp 清单，编号一旦
    与阶段序号脱节，跨层校验即失效。
    """
    with tempfile.TemporaryDirectory(prefix="r7-r11-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t", "--workspace", str(ws))
        problems = []

        # 乱写：第 1 个检查点传 cp-007 → 必须拒绝
        rc, out = run("advance", "--task-id", "t", "--workspace", str(ws),
                      "--phase", "FREEZE", "--checkpoint", "cp-007")
        if rc != 1:
            problems.append(f"乱写编号 rc={rc}（期望 1）")
        if "阶段序号" not in out:
            problems.append("缺少阶段序号提示（失败原因归属不明）")
        if no_traceback(out) is False:
            problems.append("出现裸 Traceback")

        # 正确编号 → 放行
        rc, out = run("advance", "--task-id", "t", "--workspace", str(ws),
                      "--phase", "FREEZE", "--checkpoint", "cp-001")
        if rc != 0:
            problems.append(f"正确编号 rc={rc}（期望 0）")

        # 复用：第 2 个检查点传 cp-001 → 必须拒绝
        rc, out = run("advance", "--task-id", "t", "--workspace", str(ws),
                      "--phase", "IDENTIFY", "--checkpoint", "cp-001")
        if rc != 1:
            problems.append(f"复用编号 rc={rc}（期望 1）")

        # 复用被拒后，状态文件里的 checkpoints 不得出现重复指针
        st = read_state(ws, "t")
        refs = [c.get("snapshot_ref") for c in st["checkpoints"]]
        if len(refs) != len(set(refs)):
            problems.append(f"checkpoints 出现重复指针: {refs}")

        # 第 2 个检查点用正确编号 → 放行，且 marker 与状态一致
        rc, out = run("advance", "--task-id", "t", "--workspace", str(ws),
                      "--phase", "IDENTIFY", "--checkpoint", "cp-002")
        if rc != 0:
            problems.append(f"第2个正确编号 rc={rc}（期望 0）")
        st = read_state(ws, "t")
        refs = [c.get("snapshot_ref") for c in st["checkpoints"]]
        if refs != ["state://cp-001", "state://cp-002"]:
            problems.append(f"checkpoints 序列异常: {refs}")

        # marker 文件内容必须与落盘状态一致（marker 可重写）
        marker = ws / ".harness-runs" / "t" / "checkpoints" / "cp-002.md"
        if not marker.is_file():
            problems.append("cp-002 marker 缺失")
        else:
            body = marker.read_text(encoding="utf-8")
            if "IDENTIFY" not in body:
                problems.append("marker 内容与落盘阶段不一致（marker 未重写）")

        ok = not problems
        return ok, ("；".join(problems) if problems else
                    "乱写/复用均拒绝，正确编号放行，marker 与状态一致")


case("R11", "检查点编号必须等于阶段序号（乱写/复用均拒）",
     case_r11_checkpoint_number_must_match_turn)


# ── R12：孤儿 tmp 清理 ───────────────────────────────────────────────

def case_r12_orphan_tmp_cleaned():
    """R12：写盘时清理**已确认孤儿**的 tmp。

    tmp 名带 PID 隔离并发写者；进程在 write_text 与 os.replace 之间被
    SIGKILL 就留下孤儿。反复崩溃即无界堆积的磁盘泄漏。
    """
    with tempfile.TemporaryDirectory(prefix="r7-r12-") as tmp:
        ws = Path(tmp)
        run("init", "--task-id", "t", "--workspace", str(ws))
        d = ws / ".harness-runs" / "t"
        orphan = d / "_state.json.tmp.999999"
        orphan.write_text("orphan", encoding="utf-8")
        rc, out = run("budget", "--task-id", "t", "--workspace", str(ws),
                      "--turns", "1")
        ok = (rc == 0 and not orphan.exists() and no_traceback(out))
        left = sorted(f.name for f in d.iterdir() if ".tmp." in f.name)
        return ok, (f"rc={rc} 孤儿已清理={'是' if not orphan.exists() else '否'} "
                    f"残留 tmp={left}")


case("R12", "孤儿 tmp 被清理（写盘后不再残留）", case_r12_orphan_tmp_cleaned)


# ── 主流程 ────────────────────────────────────────────────────────────

def main() -> int:
    if not STATE_IO.is_file():
        print(f"❌ 找不到 state_io.py: {STATE_IO}", file=sys.stderr)
        return 2
    print(f"── R7 状态文件健壮性锁定：{len(CASES)} 条用例 ──")
    failed = 0
    for cid, desc, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - 用例自身异常也要计入失败
            ok, detail = False, f"用例执行异常: {type(exc).__name__}: {exc}"
        mark = "✅" if ok else "❌"
        print(f"  {mark} {cid} {desc}")
        if not ok:
            print(f"      ↳ {detail}")
            failed += 1
    print()
    print(f"[rc] failed={failed} → {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
