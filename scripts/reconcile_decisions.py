#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reconcile_decisions.py —— 决策事件的只读候选对账（v1.5.9 · ADR-004）
==========================================================================
背景：v1.5.8 已给 decision_log.csv 补上结构审计（audit_decision_log.py），
      但「某次裁决是否真的有台账条目」仍是纯人工 T2。语义级逐条终裁属
      主理人纪律（decision 是自由文本，机械匹配不可靠），机器**不该代写**；
      机器该做的是把候选差异摊开，缩小人工核对面。

本脚本：
  - 只读扫描 run_dir 中的决策事件源（waivers / gates / checklist / manifest / 策略文件）
  - 与 decision_log.csv 做**候选**粗匹配，输出未匹配候选与匹配行号
  - 可选 --draft-out 生成 DRAFT CSV（每条带 [DRAFT·待人工终裁] 前缀）
  - **绝不写台账**：--draft-out 指向 decision_log.csv 或同名文件一律 EXIT=3 拒绝

边界（诚实声明）：
  - matched 只是「文本命中」，不是「已落盘」确证；unmatched 只是待人工核对候选
  - 不解析自由文本语义，不做时间戳/档位推断，不替代 audit_decision_log.py 的结构检查
  - 路径不硬编码：--ledger / --run-dirs / --draft-out 全部由调用方给出

用法：
    python3 scripts/reconcile_decisions.py --run-dirs <dir...> --ledger <decision_log.csv>
        [--task-id <T-xxx>] [--draft-out <DRAFT.csv>] [--json]

退出码契约：
    0 = 完成对账（无论是否存在未匹配候选）
    3 = 结构失败（台账不可读/表头非法 / run_dir 不存在 / 写台账路径被拒）
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

EXIT_OK = 0
EXIT_STRUCT = 3
LEDGER_FIELDS = ["ts", "actor", "decision_type", "decision", "rationale", "tier"]
DRAFT_PREFIX = "[DRAFT·待人工终裁]"


def _load_json(path: Path, warnings: list[str]):
    """畸形 JSON 不崩溃：记 warning 并返回 None。"""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        warnings.append(f"{path.name}: {type(e).__name__}: {e}")
        return None


def _events_from(run_dir: Path, task_id: str, warnings: list[str]) -> list[dict]:
    """从 run_dir 提取候选决策事件；只保留能结构化描述的部分。"""
    out: list[dict] = []

    def add(kind: str, value: str, reason: str, source: str, tid: str = ""):
        if task_id and tid and tid != task_id:
            return
        out.append({"kind": kind, "value": str(value)[:180], "reason": str(reason)[:180],
                    "source": source, "task_id": tid or task_id})

    for p in sorted(run_dir.glob("*__waivers.json")):
        obj = _load_json(p, warnings)
        tid = p.name.split("__")[0]
        if isinstance(obj, dict) and isinstance(obj.get("waivers"), list):
            for w in obj["waivers"]:
                if isinstance(w, dict):
                    add("G2-waiver", w.get("value", ""), w.get("reason", ""), p.name, tid)

    for p in sorted(run_dir.glob("*__gates.json")):
        obj = _load_json(p, warnings)
        tid = p.name.split("__")[0]
        if isinstance(obj, dict):
            for g in obj.get("gates", []) if isinstance(obj.get("gates"), list) else []:
                if isinstance(g, dict) and g.get("ok") is False:
                    add("gate-FAIL", g.get("gate", ""), g.get("detail", ""), p.name, tid)
            for s in obj.get("skipped_gates", []) if isinstance(obj.get("skipped_gates"), list) else []:
                add("gate-SKIP", str(s)[:120], "未评估门显式留痕（ADR-002）", p.name, tid)

    for p in sorted(run_dir.glob("*__checklist.json")):
        obj = _load_json(p, warnings)
        tid = p.name.split("__")[0]
        if isinstance(obj, dict):
            note = obj.get("note")
            if isinstance(note, str) and note.strip():
                add("checklist-note", obj.get("verdict", ""), note, p.name, tid)

    pol = run_dir / "evidence_check_policy.json"
    if pol.is_file():
        obj = _load_json(pol, warnings)
        if isinstance(obj, dict) and obj.get("enabled") is True:
            add("policy-enable", "G6 强制启用", str(obj.get("reason", "任务级策略")), pol.name)

    man = run_dir / "spawn_manifest.jsonl"
    if man.is_file():
        try:
            for i, line in enumerate(man.read_text(encoding="utf-8-sig").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError as e:
                    warnings.append(f"spawn_manifest 第 {i} 行非法 JSON: {e.msg}")
                    continue
                if isinstance(ev, dict) and ev.get("event") == "decision":
                    add("spawn-decision", ev.get("value", ""), ev.get("reason", ""),
                        f"{man.name}:{i}", str(ev.get("task_id", "")))
        except (OSError, UnicodeError) as e:
            warnings.append(f"{man.name}: {type(e).__name__}: {e}")
    return out


def reconcile(run_dirs: list[Path], ledger: Path, task_id: str = "") -> tuple[int, dict]:
    """只读主逻辑：返回 (退出码, 报告字典)。"""
    rep: dict = {
        "ledger": str(ledger), "run_dirs": [str(p) for p in run_dirs],
        "events": 0, "matched": [], "unmatched": [], "parse_warnings": [],
        "structural_errors": [], "verdict": "",
    }
    try:
        with ledger.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        hdr = list(rows[0].keys()) if rows else []
        if rows and not all(k in hdr for k in ("decision", "rationale")):
            rep["structural_errors"].append("台账表头缺 decision/rationale 列")
    except (OSError, UnicodeError, csv.Error) as e:
        rep["structural_errors"].append(f"台账不可读: {type(e).__name__}: {e}")
        rep["verdict"] = "LEDGER_UNREADABLE"
        return EXIT_STRUCT, rep
    if rep["structural_errors"]:
        rep["verdict"] = "LEDGER_SCHEMA_INVALID"
        return EXIT_STRUCT, rep
    for p in run_dirs:
        if not p.is_dir():
            rep["structural_errors"].append(f"run_dir 不存在: {p}")
    if rep["structural_errors"]:
        rep["verdict"] = "RUN_DIR_INVALID"
        return EXIT_STRUCT, rep

    blob = "\n".join(f"{r.get('decision', '')} {r.get('rationale', '')}" for r in rows)
    events: list[dict] = []
    for p in run_dirs:
        events.extend(_events_from(p, task_id, rep["parse_warnings"]))
    rep["events"] = len(events)
    for ev in events:
        # 候选粗匹配：value 或 task_id 命中台账任一行即列为 matched（附行号）
        hits = [i + 2 for i, r in enumerate(rows)
                if (ev["value"] and ev["value"] in blob)
                or (ev["task_id"] and ev["task_id"] in f"{r.get('decision', '')} {r.get('rationale', '')}")]
        if hits:
            rep["matched"].append({**ev, "ledger_lines": hits[:5]})
        else:
            rep["unmatched"].append(ev)
    rep["verdict"] = "RECONCILED" if not rep["unmatched"] else "CANDIDATES_PENDING"
    return EXIT_OK, rep


def write_draft(rep: dict, out: Path, ledger: Path) -> tuple[int, str]:
    """生成待人工终裁草稿；**拒绝写入任何名为 decision_log.csv 的路径**。"""
    if out.expanduser().resolve() == ledger.expanduser().resolve() \
            or out.name.lower() == "decision_log.csv":
        return EXIT_STRUCT, "拒绝：draft-out 指向台账或同名文件（ADR-004 脚本不代写台账）"
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=LEDGER_FIELDS)
            w.writeheader()
            for ev in rep["unmatched"]:
                w.writerow({
                    "ts": ts, "actor": "lead", "decision_type": "auto-candidate",
                    "decision": f"{DRAFT_PREFIX} {ev['kind']} {ev['value']}",
                    "rationale": f"候选源 {ev['source']}；reason={ev['reason']}；须人工终裁后方可落台账",
                    "tier": "通知档",
                })
    except (OSError, UnicodeError, csv.Error) as e:
        return EXIT_STRUCT, f"草稿写入失败: {type(e).__name__}: {e}"
    return EXIT_OK, str(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="决策事件只读候选对账（绝不代写台账；DRAFT 须人工终裁）")
    ap.add_argument("--run-dirs", nargs="+", required=True, help="run_dir 目录（可多个）")
    ap.add_argument("--ledger", required=True, help="decision_log.csv 台账路径")
    ap.add_argument("--task-id", default="", help="可选：只认该任务的事件")
    ap.add_argument("--draft-out", default=None, help="可选：把未匹配候选写成 DRAFT CSV")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI 消费）")
    args = ap.parse_args()

    ledger = Path(args.ledger).expanduser()
    run_dirs = [Path(p).expanduser() for p in args.run_dirs]
    rc, rep = reconcile(run_dirs, ledger, args.task_id)
    if rc == EXIT_OK and args.draft_out:
        wrc, msg = write_draft(rep, Path(args.draft_out).expanduser(), ledger)
        rep["draft_out"] = msg
        if wrc != EXIT_OK:
            rep["structural_errors"].append(msg)
            rep["verdict"] = "DRAFT_REFUSED"
            rc = wrc
    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ 决策候选对账 ═══\n台账: {rep['ledger']}")
    print(f"事件 {rep['events']} | 命中 {len(rep['matched'])} | 待人工终裁 {len(rep['unmatched'])}")
    for ev in rep["unmatched"][:10]:
        print(f"  ⚠ {ev['kind']}: {ev['value'][:60]} ← {ev['source']}")
    for w in rep["parse_warnings"][:5]:
        print(f"  ⚠ 解析: {w}")
    for e in rep["structural_errors"]:
        print(f"  ❌ 结构: {e}")
    if rep.get("draft_out"):
        print(f"草稿: {rep['draft_out']}（[DRAFT] 前缀，禁止直接追加台账）")
    print(f"\n裁决: {rep['verdict']} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
