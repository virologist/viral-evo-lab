#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
poll_run_dir.py —— run_dir 落盘巡检（P4 监控设计 §3 方案 B 落地 · 2026-10-15）
=============================================================================
背景：主理人此前用 TaskOutput 阻塞等待成员完成，队头一旦挂起全队陪等。
方案 B = 非阻塞轮询：每阶段跑一次本脚本做秒级巡检，对照"期望成员清单"
与实际落盘的 <task-id>__<member>.md，缺谁/谁卡了一目了然。

判定规则（确定性，只看文件与 mtime）：
    OK    <task-id>__<member>.md 存在且 mtime 距今 < yellow-min 分钟
    黄超时 存在但 mtime 距今 >= yellow-min 分钟（落盘后久未更新，留意）
    缺失   文件不存在（成员未产出或派工未达）
    红超时 缺失持续无法从 mtime 判断，故红级仅对"存在但 >= red-min 分钟未更新"生效

退出码：0 = 期望成员全部落盘且无红超时（黄超时仅警告，不失败）
        5 = 有缺失，或存在红超时
边界：只回答"到齐没有/新鲜没有"；"产出对不对"归 check_gates.py 与人。

用法：
    # 例：期望 literature-scout 与 research-diagnostician 两员产出
    python3 scripts/poll_run_dir.py research-ops/_harness_runs/T-20261015-M2 \\
        T-20261015-M2 --expected literature-scout,research-diagnostician \\
        --yellow-min 15 --red-min 30

    # 典型节奏：spawn 后每 2-3 分钟跑一次；exit 0 即可进入 check_gates.py
"""
import argparse
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="run_dir 落盘巡检：期望成员清单 vs 实际落盘，秒级非阻塞")
    ap.add_argument("run_dir", help="演练运行目录（如 research-ops/_harness_runs/T-xxx）")
    ap.add_argument("task_id", help="任务 ID（如 T-20261015-M2）")
    ap.add_argument("--expected", required=True,
                    help="期望落盘的成员清单，逗号分隔（如 literature-scout,research-diagnostician）")
    ap.add_argument("--yellow-min", type=int, default=15, help="黄超时阈值（分钟，默认 15）")
    ap.add_argument("--red-min", type=int, default=30, help="红超时阈值（分钟，默认 30）")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"❌ run_dir 不存在: {run_dir}", file=sys.stderr)
        return 5

    expected = [m.strip() for m in args.expected.split(",") if m.strip()]
    if not expected:
        print("❌ --expected 为空", file=sys.stderr)
        return 5

    now = time.time()
    ok, missing, yellow, red = [], [], [], []
    for member in expected:
        f = run_dir / f"{args.task_id}__{member}.md"
        if not f.is_file():
            missing.append(member)
            continue
        age_min = (now - f.stat().st_mtime) / 60
        if age_min >= args.red_min:
            red.append(f"{member}({age_min:.0f}min)")
        elif age_min >= args.yellow_min:
            yellow.append(f"{member}({age_min:.0f}min)")
        else:
            ok.append(member)

    print(f"═══ 落盘巡检 {args.task_id} ═══")
    print(f"OK    ({len(ok)}): {', '.join(ok) if ok else '—'}")
    print(f"超时  ({len(yellow) + len(red)}): "
          f"黄[>= {args.yellow_min}min] {', '.join(yellow) if yellow else '—'} | "
          f"红[>= {args.red_min}min] {', '.join(red) if red else '—'}")
    print(f"缺失  ({len(missing)}): {', '.join(missing) if missing else '—'}")

    if missing or red:
        print(f"\n裁决: NOT_READY（缺失 {len(missing)} / 红超时 {len(red)}）→ 勿进 G 闸，先派工补位或人工介入")
        return 5
    print("\n裁决: READY → 可跑 check_gates.py 收 envelope")
    if yellow:
        print(f"  ⚠️  黄超时成员建议人工确认是否已收工（落盘后 {args.yellow_min}+ 分钟无更新）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
