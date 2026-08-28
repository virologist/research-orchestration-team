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
# 默认记忆目录：优先取 --memory-dir，其次取工作区 .workbuddy/memory
# ─────────────────────────────────────────────────────────────────────

DEFAULT_MEMORY_ROOT = (
    Path(os.environ.get("WORKBUDDY_WORKSPACE", "~")).expanduser()
    / ".workbuddy" / "memory"
)

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
        d = DEFAULT_MEMORY_ROOT
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

    # 归一化：去掉括号内差异（如"（重复测试）"），取前 15 字符作 key
    normalized = re.sub(r"[（(].*?[)）]", "", note).strip()
    key = normalized[:15]
    if key and key in content:
        print(f"⏭️  跳过重复条目（key={key!r}）")
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
