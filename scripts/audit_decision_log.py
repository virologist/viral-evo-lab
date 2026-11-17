#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_decision_log.py —— 决策台账只读审计（2026-11-09 · 遗留 backlog 清项）
=========================================================================
背景：docs/authorization_matrix.md §四 规定「无 decision_log 记录的裁决 = 未发生」，
但实证核查发现全包脚本**零消费端**（仅 check_gates.py 一句注释），台账最后更新
2026-10-15（25 天前）。CLAUDE.md:117 明确待办「decision_log 审计例行化」——
本脚本即该待办的落地：把「台账是否健康、是否还在被写」变成可机器检查项，
补上「生产者 → 消费者」断链（LRN-014 同构）。

边界（诚实声明，防过度设计）：
  - **只读审计，不代写台账**——与 check_gates.py「脚本只校验落盘台账，不代写」同口径
  - 不做「某次具体裁决是否有对应条目」的语义对账：台账 decision 为自由文本，
    机械匹配不可靠；该对账仍属主理人 T2 人工纪律（authorization_matrix.md §四）
  - 不自动创建/补写/修复任何文件；陈旧只提醒（EXIT=6），不擅自改数据

用法：
    python3 scripts/audit_decision_log.py <decision_log.csv>
        [--max-age-days 30] [--min-entries 1] [--tiers <逗号分隔>] [--json]

退出码契约：
    0 = 健康（结构合法 + 字段完整 + 未超陈旧阈值）
    3 = 结构性失败（文件缺失/不可读/CSV 畸形/缺必需列/条目数不足）
    5 = 内容违规（必填字段为空 / ts 不可解析 / tier 不在白名单）
    6 = 陈旧提醒（最新条目超过 --max-age-days；与 5 叠加时优先 5）
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# authorization_matrix.md §四 规定的六列；§三 有 tier=强制升级，台账实测另有通知档/执行档
REQUIRED_COLS = ("ts", "actor", "decision_type", "decision", "rationale", "tier")
DEFAULT_TIERS = frozenset({"通知档", "执行档", "决策档", "强制升级"})

EXIT_OK = 0
EXIT_STRUCT = 3
EXIT_CONTENT = 5
EXIT_STALE = 6


def now_canonical() -> datetime:
    """R3（2026-11-17 · F1 修复）：统一时间基准到 +08:00 naive。

    与 hypothesis_watch.now_canonical 同范式（PK-R2-001）。旧实现
    datetime.now().astimezone() 依赖系统本地时区，与 naive 输入按本地解释的
    parse_ts 相减时，跨 TZ 主机 age_days 整数边界翻转（实测同一台账在 UTC 判
    13 天 HEALTHY/EXIT=0、在 Asia/Shanghai 判 14 天 STALE/EXIT=6）。
    """
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


def parse_ts(raw: str) -> datetime | None:
    """ISO8601 解析（fromisoformat 原生支持 Z/+HH:MM 后缀）；返回 +08 naive。

    R3（2026-11-17 · F1 修复）：旧实现 naive 输入裸调 d.astimezone() 按系统
    本地时区解释 → 同一台账跨 TZ 裁决翻转（PK-R2-001 同构复发）。现改为：
    aware 输入（Z/+00:00/-05:00 等）显式 canonicalize 到 +08:00 再转 naive；
    naive 输入按本包既有 +08 语境直接解释（不依赖系统本地时区）。
    绝不对 naive dt 裸调 astimezone()。
    """
    try:
        d = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    if d.tzinfo is not None:
        d = d.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    return d


def audit(path: Path, min_entries: int, max_age_days: int | None,
          tiers: set[str]) -> tuple[int, dict]:
    """只读审计主逻辑：返回 (退出码, 报告字典)。所有失败路径都有确定性退出码。"""
    rep: dict = {
        "path": str(path),
        "exists": False,
        "entries": 0,
        "columns": [],
        "missing_columns": [],
        "violations": [],
        "duplicates": 0,
        "by_tier": {},
        "by_type": {},
        "newest": "",
        "oldest": "",
        "age_days": None,
        "max_age_days": max_age_days,
        "verdict": "",
    }

    if not path.is_file():
        rep["verdict"] = "MISSING"
        return EXIT_STRUCT, rep
    rep["exists"] = True

    # utf-8-sig 顺带剥 BOM（与 poll_run_dir 的 manifest 读取同口径）
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        rep["violations"].append(f"台账不可读或非合法 CSV: {type(e).__name__}: {e}")
        rep["verdict"] = "UNREADABLE"
        return EXIT_STRUCT, rep

    if not rows or not rows[0]:
        rep["verdict"] = "EMPTY"
        return EXIT_STRUCT, rep

    header = [c.strip() for c in rows[0]]
    rep["columns"] = header
    missing = [c for c in REQUIRED_COLS if c not in header]
    rep["missing_columns"] = missing
    if missing:
        rep["verdict"] = "SCHEMA_MISSING"
        return EXIT_STRUCT, rep

    idx = {c: header.index(c) for c in REQUIRED_COLS}
    seen: set[tuple] = set()
    parsed_times: list[datetime] = []
    valid_rows = 0

    for lineno, row in enumerate(rows[1:], start=2):
        if not row or all(not c.strip() for c in row):
            continue  # 空行跳过（台账常见尾随空行）
        if len(row) != len(header):
            rep["violations"].append(
                f"L{lineno}: 列数 {len(row)} ≠ 表头 {len(header)}（CSV 畸形）")
            continue
        rec = {c: row[idx[c]].strip() for c in REQUIRED_COLS}
        valid_rows += 1

        for c in REQUIRED_COLS:
            if not rec[c]:
                rep["violations"].append(f"L{lineno}: 必填列 {c} 为空")

        t = parse_ts(rec["ts"])
        if t is None:
            rep["violations"].append(f"L{lineno}: ts 不是合法 ISO8601: {rec['ts']!r}")
        else:
            parsed_times.append(t)

        if rec["tier"] and rec["tier"] not in tiers:
            rep["violations"].append(
                f"L{lineno}: tier={rec['tier']!r} 不在白名单 {sorted(tiers)}")
            # 非法 tier 仍计入分布，便于诊断
        rep["by_tier"][rec["tier"] or "<空>"] = rep["by_tier"].get(rec["tier"] or "<空>", 0) + 1
        rep["by_type"][rec["decision_type"] or "<空>"] = (
            rep["by_type"].get(rec["decision_type"] or "<空>", 0) + 1)

        key = tuple(rec[c] for c in REQUIRED_COLS)
        if key in seen:
            rep["duplicates"] += 1
        seen.add(key)

    rep["entries"] = valid_rows
    if parsed_times:
        rep["newest"] = max(parsed_times).isoformat(timespec="seconds")
        rep["oldest"] = min(parsed_times).isoformat(timespec="seconds")
        # R3（F1）：比较基准与 parse_ts 输出同为 +08 naive，跨 TZ 主机裁决一致
        age = (now_canonical() - max(parsed_times)).days
        rep["age_days"] = age

    # 结构层：条目数下限
    if valid_rows < min_entries:
        rep["violations"].append(
            f"条目数 {valid_rows} < --min-entries {min_entries}（台账可能未例行维护）")
        rep["verdict"] = "TOO_FEW"
        return EXIT_STRUCT, rep

    # 内容层：任一违规即 5（优先于陈旧）
    if rep["violations"]:
        rep["verdict"] = "CONTENT_VIOLATION"
        return EXIT_CONTENT, rep

    # 陈旧层：只提醒，不改数据
    if max_age_days is not None and rep["age_days"] is not None \
            and rep["age_days"] > max_age_days:
        rep["verdict"] = "STALE"
        return EXIT_STALE, rep

    rep["verdict"] = "HEALTHY"
    return EXIT_OK, rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="决策台账只读审计（不代写）：结构/字段/档位/陈旧四查")
    ap.add_argument("csv_path", help="decision_log.csv 路径")
    ap.add_argument("--max-age-days", type=int, default=30,
                    help="最新条目超过 N 天判陈旧 EXIT=6；0 = 禁用陈旧检查（默认 30）")
    ap.add_argument("--min-entries", type=int, default=1,
                    help="条目数下限，不足判 EXIT=3（默认 1）")
    ap.add_argument("--tiers", default=",".join(sorted(DEFAULT_TIERS)),
                    help="合法 tier 白名单（逗号分隔）；新增档位须同步本参数或脚本默认值")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI/脚本消费）")
    args = ap.parse_args()

    tiers = {t.strip() for t in args.tiers.split(",") if t.strip()}
    max_age = args.max_age_days if args.max_age_days > 0 else None
    rc, rep = audit(Path(args.csv_path).expanduser(), args.min_entries, max_age, tiers)

    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ decision_log 审计 ═══\n台账: {rep['path']}")
    if not rep["exists"]:
        print(f"❌ 台账不存在（EXIT={rc}）")
        return rc
    print(f"表头: {','.join(rep['columns']) or '<空>'}")
    print(f"条目: {rep['entries']} | 重复行: {rep['duplicates']}")
    if rep["newest"]:
        print(f"时间跨度: {rep['oldest']} → {rep['newest']}"
              f"（最新距今 {rep['age_days']} 天，阈值 {rep['max_age_days']} 天）")
    if rep["by_tier"]:
        print("按 tier: " + " / ".join(f"{k}={v}" for k, v in sorted(rep["by_tier"].items())))
    if rep["by_type"]:
        print("按 decision_type: " + " / ".join(
            f"{k}={v}" for k, v in sorted(rep["by_type"].items())))
    if rep["missing_columns"]:
        print(f"❌ 缺必需列: {rep['missing_columns']}")
    for v in rep["violations"][:10]:
        print(f"  ❌ {v}")
    if len(rep["violations"]) > 10:
        print(f"  … 另有 {len(rep['violations']) - 10} 条违规")
    label = {EXIT_OK: "✅ HEALTHY", EXIT_STRUCT: "❌ 结构失败",
             EXIT_CONTENT: "❌ 内容违规", EXIT_STALE: "⚠ STALE（陈旧）"}
    print(f"\n裁决: {rep['verdict']} {label.get(rc, '')} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
