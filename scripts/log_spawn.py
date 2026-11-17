#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_spawn.py —— spawn manifest 留痕（R2-3 修复 · 2026-10-15）
============================================================
背景：run-dir 里只有装配产物与产出文件，"哪次 Agent 调用对应哪份装配产物"
无法事后审计（R2 诊断协作维度残余风险）。

用法（主理人每次 spawn 后立即执行）：
    python3 scripts/log_spawn.py <run-dir> <task-id> <member-id> <agent-task-id> \
        [--subagent-type general-purpose]

行为：追加一行到 <run-dir>/spawn_manifest.jsonl
    {"ts", "task_id", "member", "agent_task_id", "subagent_type", "spawn_file"}
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


import importlib.util  # noqa: E402

def _load_guard():
    """R-10a：加载同目录 guard_readonly（只读区写盘守卫）；加载失败不阻断（降级为无守卫）。"""
    here = Path(__file__).resolve().parent
    try:
        spec = importlib.util.spec_from_file_location("guard_readonly", here / "guard_readonly.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # L3 盲检 Y6：放宽捕获面（半损坏也降级不崩溃）
        print(f"⚠ guard_readonly 加载失败（守卫降级）: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="spawn manifest 留痕")
    ap.add_argument("run_dir")
    ap.add_argument("task_id")
    ap.add_argument("member")
    ap.add_argument("agent_task_id")
    ap.add_argument("--subagent-type", default="general-purpose")
    args = ap.parse_args()
    # R3（2026-11-17 · F2 修复）：task_id 拼路径前白名单校验——{task_id}__
    # 直接进 glob/写盘文件名，含 "/" / ".." 可越界读写（盲检已复现读 run_dir 外
    # 文件报 OK）。白名单 [A-Za-z0-9][A-Za-z0-9_-]* 与存量形态（T-20261015-M2、
    # T-FUZZ 等）完全兼容；显式拒绝路径成分与 shell 元字符。
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.task_id):
        print(f"❌ task_id 含非法字符（仅允许字母/数字/下划线/连字符，且不以 _- 开头）: "
              f"{args.task_id!r}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    _g = _load_guard()
    if _g: _g.guard_or_exit(run_dir)  # R-10a 只读区守卫
    run_dir.mkdir(parents=True, exist_ok=True)
    spawn_file = run_dir / f"spawn__{args.member}.md"
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "task_id": args.task_id,
        "member": args.member,
        "agent_task_id": args.agent_task_id,
        "subagent_type": args.subagent_type,
        "spawn_file": str(spawn_file) if spawn_file.is_file() else f"{spawn_file}(缺失!)",
    }
    out = run_dir / "spawn_manifest.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"✅ {out} += {args.member} @ {args.agent_task_id}")
    if "缺失" in entry["spawn_file"]:
        print("  ⚠️ 装配产物不存在——先跑 assemble 再 spawn", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
