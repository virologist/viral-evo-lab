#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hypothesis_watch.py —— 假说治理触发器（D1 修复 · 2026-10-15）
==============================================================
背景：deprecate_rule 声称"证伪后即标 deprecated"，但实测 H-ANCHOR-1 从
假说池建档（09-18）到标 deprecated（10-14）隔了 26 天——期间 T1 的
"禁引用已废弃结论"检查一直失效。根因：证伪→登记之间无触发机制。

本脚本 = 确定性触发器：比对假说池更新时间与台账闭环记录，凡出现
"晚于假说池更新的 fatal/severe 闭环发现"即报警，驱动 archivist 复查。

用法：
    python3 scripts/hypothesis_watch.py [--research-ops <路径>] [--max-age 14]

退出码：0 = 无需复查；5 = 需要复查（deprecate/复核挂起）；3 = 文件缺失
边界：只做"时间差与状态比对"（确定性）；"某发现是否真的证伪某假说"是语义判断，归 LLM/人。
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def autodetect_research_ops() -> str:
    env_v = os.environ.get("RESEARCH_OPS_DIR", "").strip()
    if env_v and Path(env_v).is_dir():
        return env_v
    cwd_ro = Path.cwd() / "research-ops"
    if cwd_ro.is_dir():
        return str(cwd_ro.resolve())
    return ""


def parse_dt(s: str):
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S+08:00", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            # 统一为 naive 本地时间（台账与假说池同为 +08:00，混比会 TypeError）
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="假说治理触发器：假说池 vs 台账闭环时间差比对")
    ap.add_argument("--research-ops", default=None)
    ap.add_argument("--max-age", type=int, default=14,
                    help="假说池最长免复查天数（默认 14）")
    args = ap.parse_args()

    ro = args.research_ops or autodetect_research_ops()
    if not ro:
        print("❌ 未找到 research-ops（设 RESEARCH_OPS_DIR 或在 workspace 根运行）", file=sys.stderr)
        return 3
    hyp_p = Path(ro) / "context_stack/confirmed_hypotheses.json"
    led_p = Path(ro) / "00_governance/redteam_ledger.csv"
    if not hyp_p.is_file() or not led_p.is_file():
        print(f"❌ 缺文件: {hyp_p} / {led_p}", file=sys.stderr)
        return 3

    hyp = json.loads(hyp_p.read_text(encoding="utf-8"))
    if not isinstance(hyp.get("active_hypotheses"), list):
        print("❌ 假说池结构异常（active_hypotheses 非 list）", file=sys.stderr)
        return 3
    hyp_updated = parse_dt(hyp.get("last_updated", ""))
    if hyp_updated is None:
        print("❌ 假说池 last_updated 无法解析", file=sys.stderr)
        return 3

    # H1 修复（审计 C1 2026-10-15）：已处置清单按 finding_id 记账，防"bump 时间戳洗白"
    state_p = Path(ro) / "00_governance/hypothesis_watch_state.json"
    handled = set()
    if state_p.is_file():
        try:
            handled = set(json.loads(state_p.read_text(encoding="utf-8")).get("handled_finding_ids", []))
        except (json.JSONDecodeError, OSError):
            handled = set()

    # 台账：晚于假说池更新的 closed fatal/severe（排除已处置）
    late_fatal = []
    with led_p.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            fid = row.get("finding_id", "")
            if fid in handled:
                continue
            if row.get("status", "").lower() != "closed":
                continue
            if row.get("severity", "").lower() not in ("fatal", "severe"):
                continue
            cd = parse_dt(row.get("closed_date", "") or "")
            if cd is None:
                continue
            # H2 修复（审计 2026-10-15）：closed_date 为纯日期时按"同日即算晚于"（避免同日晚闭环漏报）
            if len((row.get("closed_date") or "").strip()) <= 10:
                if cd.date() >= hyp_updated.date():
                    late_fatal.append(row)
            elif cd > hyp_updated:
                late_fatal.append(row)

    age_days = (datetime.now() - hyp_updated).days
    active = [h for h in hyp.get("active_hypotheses", []) if h.get("status") != "deprecated"]
    deprecated = [h for h in hyp.get("active_hypotheses", []) if h.get("status") == "deprecated"]

    print(f"═══ 假说治理触发器 ═══")
    print(f"假说池更新: {hyp['last_updated']}（{age_days} 天前）")
    print(f"活跃假说: {len(active)} | 已废弃: {len(deprecated)}")
    print(f"晚于假说池更新的 fatal/severe 闭环发现: {len(late_fatal)} 条")
    for r in late_fatal[:5]:
        print(f"  🔴 {r.get('finding_id')} [{r.get('severity')}] closed={r.get('closed_date')} — {r.get('finding_summary','')[:60]}")

    alerts = []
    if late_fatal:
        alerts.append(f"{len(late_fatal)} 条 fatal/severe 发现闭环于假说池更新之后——活跃假说可能已被其中某些证伪，须逐条复查（语义判断归主理人）")
    if age_days > args.max_age:
        alerts.append(f"假说池 {age_days} 天未更新（> {args.max_age}）——即使无新证伪，也须例行复核")

    if alerts:
        print("\n裁决: REVIEW_REQUIRED")
        for a in alerts:
            print(f"  ⚠️  {a}")
        print("  处置：archivist 逐条比对 → 需废弃的标 deprecated（改 JSON 后跑 render_context_stack.py）")
        print("  →  复查完成后把处置过的 finding_id 写入 00_governance/hypothesis_watch_state.json")
        print('     （格式 {"handled_finding_ids": ["H-XX", ...]}），本脚本才对其静默')
        return 5
    print("\n裁决: CLEAN（无需复查）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
