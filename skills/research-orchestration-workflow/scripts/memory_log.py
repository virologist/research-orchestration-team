"""
持久记忆自动写入脚本 / Persistent Memory Logger

将团队运行的关键信息（决策、用户偏好、项目约定、经验教训）自动写入
工作区 `.workbuddy/memory/`，对应 agent-protocol.md §4 三级记忆中的
「持久记忆（跨会话）」层。主理人在任务收尾时调用，实现记忆自动化。

Usage:
    python3 memory_log.py --note "用户要求所有输出用中文" --type preference
    python3 memory_log.py --note "H9N2换株决策=降档" --type decision --trace-id trace-h9n2-001
    python3 memory_log.py --note "测试发现TeamCreate不可用时降级为代产出" --type lesson
    python3 memory_log.py --dry-run --note "预览将写入的内容"

--type 可选：decision(决策) | preference(用户偏好) | convention(项目约定) | lesson(经验教训)
--target 可选：daily(默认,追加到当天日志) | longterm(写入 MEMORY.md,按 key 去重)
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# 默认记忆目录：按优先级解析——显式 env > 当前工作区探测 > 用户级 fallback
# ─────────────────────────────────────────────────────────────────────

def _default_memory_root() -> Path:
    """解析记忆目录（项目工作区 .workbuddy/memory 优先，避免误写用户级）。"""
    ws = os.environ.get("WORKBUDDY_WORKSPACE")
    if ws:
        return Path(ws).expanduser() / ".workbuddy" / "memory"
    # 当前工作目录若是工作区（含 .workbuddy 目录），就地写入项目记忆
    if (Path.cwd() / ".workbuddy").is_dir():
        return Path.cwd() / ".workbuddy" / "memory"
    # 最后手段：用户级记忆（跨项目），告警提示调用方
    print("⚠️ 未检测到 WORKBUDDY_WORKSPACE 且当前目录无 .workbuddy，回退到用户级记忆目录",
          file=sys.stderr)
    return Path.home() / ".workbuddy" / "memory"

TYPE_LABELS = {
    "decision": "🔀 决策",
    "preference": "⭐ 用户偏好",
    "convention": "📐 项目约定",
    "lesson": "🧠 经验教训",
}


def resolve_memory_dir(override: str | None) -> Path:
    if override:
        d = Path(override).expanduser()
    else:
        d = _default_memory_root()
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_entry(note: str, mtype: str, trace_id: str | None) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    label = TYPE_LABELS.get(mtype, "📌 记录")
    lines = [f"- [{now}] {label}：{note}"]
    if trace_id:
        lines.append(f"  （trace_id: {trace_id}）")
    return "\n".join(lines) + "\n"


def append_daily(memory_dir: Path, entry: str, dry_run: bool) -> Path:
    today = datetime.date.today().isoformat()
    f = memory_dir / f"{today}.md"
    header = f"# {today}\n\n"
    content = ""
    if f.exists():
        content = f.read_text(encoding="utf-8")
        if not content.startswith("#"):
            content = header + content
    else:
        content = header
    content += entry
    if not dry_run:
        f.write_text(content, encoding="utf-8")
    return f


def append_longterm(memory_dir: Path, note: str, mtype: str, dry_run: bool) -> tuple:
    """写入 MEMORY.md 并去重。返回 (文件路径, 是否实际写入)。"""
    f = memory_dir / "MEMORY.md"
    content = f.read_text(encoding="utf-8") if f.exists() else ""
    if not content.startswith("#"):
        content = "# 长期项目记忆\n\n" + content

    # 归一化：去掉括号内差异（如"（重复测试）"），用完整归一化内容作 key
    # （前 N 字前缀会误判——前 15 字相同但第 16 字不同的不同条目会被误去重）
    normalized = re.sub(r"[（(].*?[)）]", "", note).strip()
    if normalized and normalized in content:
        print(f"⏭️  跳过重复条目（key={normalized!r}）")
        return f, False
    content += build_entry(note, mtype, None)
    if not dry_run:
        f.write_text(content, encoding="utf-8")
    return f, True


def main():
    ap = argparse.ArgumentParser(description="持久记忆自动写入")
    ap.add_argument("--note", required=True, help="记忆内容")
    ap.add_argument("--type", choices=list(TYPE_LABELS), default="decision", help="记忆类型")
    ap.add_argument("--trace-id", default=None, help="任务追踪 ID")
    ap.add_argument("--target", choices=["daily", "longterm"], default="daily", help="写入目标")
    ap.add_argument("--memory-dir", default=None, help="覆盖记忆目录")
    ap.add_argument("--dry-run", action="store_true", help="仅预览不写入")
    args = ap.parse_args()

    memory_dir = resolve_memory_dir(args.memory_dir)
    entry = build_entry(args.note, args.type, args.trace_id)

    # 落到用户级 fallback 时提示（项目级记忆应显式传 --memory-dir 或设置 WORKBUDDY_WORKSPACE）
    if (args.memory_dir is None
            and not os.environ.get("WORKBUDDY_WORKSPACE")
            and not (Path.cwd() / ".workbuddy").is_dir()):
        print("⚠️  未检测到项目工作区，已落到用户级记忆（~/.workbuddy/memory）。"
              "如需写入项目记忆，请传 --memory-dir 或设置 WORKBUDDY_WORKSPACE")

    print(f"📂 记忆目录: {memory_dir}")
    print(f"📝 待写入: {entry.rstrip()}")
    if args.dry_run:
        print("🔍 dry-run 模式，未实际写入")
        return

    if args.target == "longterm":
        f, written = append_longterm(memory_dir, args.note, args.type, dry_run=False)
        print(f"✅ 已写入长期记忆: {f}" if written else f"⏭️  未写入（重复或 dry-run）: {f}")
    else:
        f = append_daily(memory_dir, entry, dry_run=False)
        print(f"✅ 已追加当日记忆: {f}")


if __name__ == "__main__":
    main()
