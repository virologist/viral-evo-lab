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


def main() -> int:
    ap = __import__("argparse").ArgumentParser(
        description="R9/R14 纪律审判落盘工具：生成 task_id__checklist.json + .md")
    ap.add_argument("run_dir", help="运行目录")
    ap.add_argument("task_id", help="任务 ID")
    ap.add_argument("--items", type=int, default=8, help="checklist 总项数")
    ap.add_argument("--passed", type=int, default=None, help="通过项数（默认=items）")
    ap.add_argument("--sources-checked", type=int, default=0, help="权威源核验数")
    ap.add_argument("--hallucinated", type=int, default=0, help="未溯源数字数")
    ap.add_argument("--note", default="", help="一句话备注")
    args = ap.parse_args()
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
