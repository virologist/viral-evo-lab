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
    python3 scripts/hypothesis_watch.py --check-disposition [--research-ops <路径>]
        （只读验收「告警→处置」闭环；供 T2 与假说相关 WF 入口作前置门禁）

退出码：0 = 无需复查 / 处置完整；5 = 需要复查（deprecate/复核挂起）；
        3 = **无法产出裁决**（输入缺失或证据源畸形）；6 = **可产出裁决但处置不完整**
边界：只做"时间差与状态比对"（确定性）；"某发现是否真的证伪某假说"是语义判断，归 LLM/人。

退出码 3 与 6 的判别原则（A-8 · L3 2026-11-09 口径统一）：
  两者的区别不是「哪个文件坏了」，而是**坏掉后还能不能算出裁决**：
  - EXIT=3（无法裁决）：`confirmed_hypotheses.json`（假说池）畸形、
    `redteam_ledger.csv`（**证据源**）畸形或读取失败、必填文件缺失
    —— 晚于池更新的 fatal/severe 根本算不出来，没有任何可交付的判定。
  - EXIT=6（可裁决但不合规）：`hypothesis_watch_state.json`（**处置记录**）畸形
    —— 证据源完好，late_fatal 已算出；台账坏了只是「处置证据不可信」，
      保守按「未处置」计（宁可多提醒，不可漏提醒），仍能给出可执行的判定。
  换言之：证据源坏 → 无法裁决（3）；处置记录坏 → 保守判未处置（6）。

L3（2026-11-09）：三处 JSON 消费点此前直接 .get()/构造 set，畸形输入抛未捕获异常
→ EXIT=1（违反退出码契约）、门禁静默失效。全部转契约退出码（结构畸形），
并在 --check-disposition 下区分「无待处置项」与「有未处置项」——干净项目不再被
缺 state 误阻断（EXIT=0），避免存量项目被门禁拦死。
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


def parse_dt(s):
    """解析时间字符串；非字符串输入一律返回 None（不抛异常）。

    L3（2026-11-09）：原实现直接 s.strip()，last_updated/closed_date 为
    dict/list/int 时抛 AttributeError → EXIT=1。台账字段类型不可信，
    解析失败按「无法判定」处理（跳过该行），不崩。
    """
    if not isinstance(s, str):
        return None
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


def load_json_obj(path: Path) -> tuple[dict | None, str]:
    """L3（2026-11-09）：统一 JSON 消费入口——只接受对象顶层。

    三处消费点（假说池 / 处置台账 / 已处置清单）此前直接 .get()，
    顶层为 list/str/null 时抛 AttributeError → EXIT=1、退出码契约破裂。
    返回 (obj, err)；err 非空表示畸形，调用方须转契约退出码 3。
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"读取失败: {type(e).__name__}: {e}"
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"JSON 不可解析: {e}"
    if not isinstance(obj, dict):
        return None, f"顶层须为对象（实为 {type(obj).__name__}）"
    return obj, ""


def extract_handled_ids(obj: dict) -> tuple[set, list[str]]:
    """L3（2026-11-09）：已处置 finding_id 清单安全提取。

    原实现 set(list) 对含 dict/list 元素抛 TypeError(unhashable)；
    非字符串元素还会让台账比对静默失配。此处只收字符串，
    非字符串元素记为漂移并回报（不崩溃、不静默丢弃）。
    """
    ids = obj.get("handled_finding_ids")
    if ids is None:
        return set(), []
    if not isinstance(ids, list):
        return set(), ["handled_finding_ids 须为数组（实为 %s）" % type(ids).__name__]
    good, drift = set(), []
    for x in ids:
        if isinstance(x, str):
            good.add(x)
        else:
            drift.append(f"非字符串元素: {type(x).__name__}")
    return good, drift


def _row_str(v) -> str:
    """L3（2026-11-09）：台账单元格归一化——非字符串一律转空串。

    csv.DictReader 在短行/多列场景会给 None 或 list 值，
    直接 .lower()/.strip() 会抛 AttributeError。
    """
    return v if isinstance(v, str) else ""


def check_disposition(state_p: Path, late_fatal: list, hyp_updated: datetime,
                      age_days: int, max_age: int,
                      state_obj: dict | None = None,
                      state_err: str = "") -> tuple[bool, list[str]]:
    """C2（2026-11-08 · 元层审计第 1 轮）：只读验收「告警 → 处置」闭环。

    触发器本体只负责报警，处置台账由项目侧 archivist 落盘；此前不存在机器
    可判定的验收点，导致 T2 复选框形同虚设（实测 EXIT=5 而 state 从未生成）。
    本函数纯只读，不写 research-ops；合格须三项全满足：
      1. state 为对象且 handled_finding_ids 是字符串数组；
      2. 无未处置 fatal/severe（调用方已排除 handled，故 late_fatal 非空即覆盖不全）；
      3. 假说池超 max_age 未更新时，reviewed_at 不早于池更新且在有效期内
         （防「只 bump 时间戳、不真复核」）。

    L3（2026-11-09）：修正「干净项目被误阻断」——无任何待处置项且池未超期时
    判 PASS（EXIT=0），不再因「台账文件不存在」返回 EXIT=6 而拦死存量项目。
    台账缺失仅在**确有未处置项**或**池超期待复核**时才算缺口。
    """
    notes: list[str] = []
    need_state = bool(late_fatal) or age_days > max_age

    if not need_state:
        # 无待处置项 + 池未超期 = 无需处置台账（存量项目不会被误阻断）
        return True, ["无待处置 fatal/severe 且假说池未超期——无需处置台账"]

    if state_err:
        return False, [f"处置台账结构异常: {state_err}"]
    if state_obj is None:
        return False, [f"处置台账缺失: {state_p.name}（archivist 复查后须写 handled_finding_ids）"]
    obj = state_obj
    handled = obj.get("handled_finding_ids")
    if not isinstance(handled, list) or any(not isinstance(x, str) for x in handled):
        return False, ["handled_finding_ids 须为字符串数组"]
    notes.append(f"handled_finding_ids 合法（{len(handled)} 条）")
    if late_fatal:
        ids = [_row_str(r.get("finding_id")) for r in late_fatal]
        return False, [f"仍有 {len(ids)} 条 fatal/severe 未处置: {', '.join(ids[:5])}"] + notes
    notes.append("全部 fatal/severe 闭环发现已处置")
    if age_days > max_age:
        rev = parse_dt(obj.get("reviewed_at", ""))
        if rev is None or rev < hyp_updated or (datetime.now() - rev).days > max_age:
            return False, [f"假说池 {age_days} 天未更新，reviewed_at 缺失/过期/早于池更新"] + notes
        notes.append(f"例行复核有效（reviewed_at={obj.get('reviewed_at')}）")
    return True, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="假说治理触发器：假说池 vs 台账闭环时间差比对")
    ap.add_argument("--research-ops", default=None)
    ap.add_argument("--max-age", type=int, default=14,
                    help="假说池最长免复查天数（默认 14）")
    ap.add_argument("--check-disposition", action="store_true",
                    help="只读验收处置闭环：state 存在、结构合法、覆盖全部待处置 finding，且例行复核在有效期内")
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

    hyp, hyp_err = load_json_obj(hyp_p)
    if hyp_err:
        # C1（2026-11-07）：坏 JSON 走契约退出码 3（原实现直接 traceback，违反退出码契约）
        # L3（2026-11-09）：顶层非对象（list/str/null）同样走 3，不再抛 AttributeError
        print(f"❌ 假说池结构异常: {hyp_p}\n   {hyp_err}", file=sys.stderr)
        return 3
    if not isinstance(hyp.get("active_hypotheses"), list):
        print("❌ 假说池结构异常（active_hypotheses 非 list）", file=sys.stderr)
        return 3
    # T-B3（2026-10-15）：字段漂移告警——条目缺 id/status/claim 任一关键字段时
    # 发 warning 但不退出（结构可漂移≠不可用，处置权归 archivist）。
    KEY_FIELDS = ("id", "status", "claim")
    drift = [
        (i, [k for k in KEY_FIELDS if k not in (h or {})])
        for i, h in enumerate(hyp.get("active_hypotheses", []))
        if not isinstance(h, dict) or any(k not in (h or {}) for k in KEY_FIELDS)
    ]
    for i, miss in drift:
        print(f"⚠️  字段漂移: active_hypotheses[{i}] 缺 {miss}（建议 archivist 补齐或下架该条目）",
              file=sys.stderr)
    hyp_updated = parse_dt(hyp.get("last_updated", ""))
    if hyp_updated is None:
        print("❌ 假说池 last_updated 无法解析", file=sys.stderr)
        return 3

    # H1 修复（审计 C1 2026-10-15）：已处置清单按 finding_id 记账，防"bump 时间戳洗白"
    # L3（2026-11-09）：顶层 list/str/null 与非字符串元素此前抛 AttributeError/TypeError
    # → EXIT=1（退出码契约破裂）。此处安全提取；畸形只告警，不崩溃，
    # 且保守按「无已处置」计入 late_fatal（宁可多提醒，不可漏提醒）。
    state_p = Path(ro) / "00_governance/hypothesis_watch_state.json"
    handled: set = set()
    state_obj: dict | None = None
    state_err = ""
    if state_p.is_file():
        state_obj, state_err = load_json_obj(state_p)
        if state_err:
            print(f"⚠️  处置台账结构异常: {state_p.name}（{state_err}）——按未处置计",
                  file=sys.stderr)
        else:
            handled, drift = extract_handled_ids(state_obj)
            for d in drift:
                print(f"⚠️  处置台账字段漂移: {d}（该项不计入已处置）", file=sys.stderr)

    # 台账：晚于假说池更新的 closed fatal/severe（排除已处置）
    # L3（2026-11-09）：CSV 行字段类型不可信（None/int/dict 均可能出现），
    # 统一走 _row_str 归一化，避免 .lower() 抛 AttributeError。
    late_fatal = []
    try:
        with led_p.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except (OSError, csv.Error) as e:
        print(f"❌ 台账读取失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    for row in rows:
        fid = _row_str(row.get("finding_id"))
        if fid in handled:
            continue
        if _row_str(row.get("status")).lower() != "closed":
            continue
        if _row_str(row.get("severity")).lower() not in ("fatal", "severe"):
            continue
        closed_raw = row.get("closed_date") or ""
        cd = parse_dt(closed_raw)
        if cd is None:
            continue
        # H2 修复（审计 2026-10-15）：closed_date 为纯日期时按"同日即算晚于"（避免同日晚闭环漏报）
        if len(_row_str(closed_raw).strip()) <= 10:
            if cd.date() >= hyp_updated.date():
                late_fatal.append(row)
        elif cd > hyp_updated:
            late_fatal.append(row)

    age_days = (datetime.now() - hyp_updated).days
    # T-B3 配套：漂移条目（含非 dict）已告警放行，此处须容错防 .get 崩溃
    active = [h for h in hyp.get("active_hypotheses", []) if isinstance(h, dict) and h.get("status") != "deprecated"]
    deprecated = [h for h in hyp.get("active_hypotheses", []) if isinstance(h, dict) and h.get("status") == "deprecated"]

    print(f"═══ 假说治理触发器 ═══")
    print(f"假说池更新: {hyp.get('last_updated')}（{age_days} 天前）")
    print(f"活跃假说: {len(active)} | 已废弃: {len(deprecated)}")
    print(f"晚于假说池更新的 fatal/severe 闭环发现: {len(late_fatal)} 条")
    for r in late_fatal[:5]:
        print(f"  🔴 {_row_str(r.get('finding_id'))} [{_row_str(r.get('severity'))}] "
              f"closed={_row_str(r.get('closed_date'))} — {_row_str(r.get('finding_summary'))[:60]}")

    alerts = []
    if late_fatal:
        alerts.append(f"{len(late_fatal)} 条 fatal/severe 发现闭环于假说池更新之后——活跃假说可能已被其中某些证伪，须逐条复查（语义判断归主理人）")
    if age_days > args.max_age:
        alerts.append(f"假说池 {age_days} 天未更新（> {args.max_age}）——即使无新证伪，也须例行复核")

    # C2（2026-11-08）：处置闭环只读验收。默认模式行为完全不变；只有显式传
    # --check-disposition 才启用，供 T0/T2 与 WF1/WF3/WF5 入口作前置门禁。
    if args.check_disposition:
        ok, notes = check_disposition(state_p, late_fatal, hyp_updated, age_days,
                                      args.max_age, state_obj=state_obj, state_err=state_err)
        print(f"\n处置闭环验收: {'OK' if ok else 'INCOMPLETE'}")
        for n in notes:
            print(f"  {'✅' if ok else '🔴'} {n}")
        return 0 if ok else 6

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
