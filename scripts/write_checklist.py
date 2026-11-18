#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_checklist.py —— R9/R14 纪律审判落盘工具（L1 · 2026-10-14）
执行：生成 <run-dir>/<task_id>__checklist.json（机器读） + .md（人读）
用法：python3 scripts/write_checklist.py <run-dir> <task_id> \
        --items 4 --passed 3 --sources-checked 2 --hallucinated 1 \
        --note "T0 3项过; T1 数字核验 V1 警告放过"
JSON schema 强制, 拒绝手写三行 .md 格式不可聚合的痛点
"""
import json
import sys
from datetime import datetime
from pathlib import Path

REQUIRED = ["ts", "task_id", "items_total", "items_passed",
           "sources_checked", "hallucinated", "verdict", "note"]


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
    ap = __import__("argparse").ArgumentParser(
        description="R9/R14 纪律审判落盘工具：生成 task_id__checklist.json + .md（退出码：0=PASS；2=参数非法；5=DEGRADE）")
    ap.add_argument("run_dir", help="运行目录")
    ap.add_argument("task_id", help="任务 ID")
    ap.add_argument("--items", type=int, default=8, help="checklist 总项数")
    ap.add_argument("--passed", type=int, default=None, help="通过项数（默认=items）")
    ap.add_argument("--sources-checked", type=int, default=0, help="权威源核验数")
    ap.add_argument("--hallucinated", type=int, default=0, help="未溯源数字数")
    ap.add_argument("--note", default="", help="一句话备注")
    args = ap.parse_args()
    # R3（2026-11-17 · F2 修复）：task_id 拼路径前白名单校验——{task_id}__
    # 直接进 glob/写盘文件名，含 "/" / ".." 可越界读写（盲检已复现读 run_dir 外
    # 文件报 OK）。白名单 [A-Za-z0-9][A-Za-z0-9_-]* 与存量形态（T-20261015-M2、
    # T-FUZZ 等）完全兼容；显式拒绝路径成分与 shell 元字符。
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", args.task_id):
        print(f"❌ task_id 含非法字符（仅允许字母/数字/下划线/连字符，且不以 _- 开头，长度 ≤128）: "
              f"{args.task_id!r}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    task_id = args.task_id
    items_total = args.items
    items_passed = args.passed if args.passed is not None else items_total
    sources_checked = args.sources_checked
    hallucinated = args.hallucinated
    note = args.note

    verdict = "PASS" if (items_passed == items_total and hallucinated == 0) else "DEGRADE"

    payload = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "task_id": task_id,
        "items_total": items_total,
        "items_passed": items_passed,
        "sources_checked": sources_checked,
        "hallucinated": hallucinated,
        "verdict": verdict,
        "note": note,
    }
    # 字段完整性断言（防御性：永远不会被静默漏字段）
    miss = [k for k in REQUIRED if k not in payload]
    if miss:
        print(f"❌ schema 缺字段: {miss}", file=sys.stderr); return 3

    _g = _load_guard()
    if _g: _g.guard_or_exit(run_dir)  # R-10a 只读区守卫
    run_dir.mkdir(parents=True, exist_ok=True)
    json_p = run_dir / f"{task_id}__checklist.json"
    md_p = run_dir / f"{task_id}__checklist.md"
    json_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = (f"# checklist {task_id}\n"
          f"- ts: {payload['ts']}\n- verdict: **{verdict}**\n"
          f"- items: {items_passed}/{items_total} | sources_checked: {sources_checked} | "
          f"hallucinated: {hallucinated}\n- note: {note}\n")
    md_p.write_text(md, encoding="utf-8")
    print(f"✅ {json_p}")
    print(f"✅ {md_p}")
    return 0 if verdict == "PASS" else 5


if __name__ == "__main__":
    sys.exit(main())
