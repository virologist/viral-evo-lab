#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_evidence_check.py —— G6 抽查留痕硬门（v1.5.9 · SOP T-D1 销项）
==========================================================================
背景：agent-harness-sop T-A1 的 V2-2 条款写明「抽查未通过 = 未交付」，
      但实测 check_gates.py 只验 artifact 存在（G3），抽查契约完全依赖主理人
      自觉 → 软门。T-D1 建议在 check_gates.py 加 G6：
      spawn_manifest.jsonl 中含 ≥2 条 evidence_check 记录，actor=lead，
      value=抽查真值 + reason，exit 5 阻断。

本脚本是该硬门的**独立可执行形态**，同时供 check_gates.py 内联调用：
  - 只读：不写 spawn_manifest、不补记录、不改任何文件
  - 只验**形式要件**：file:行号定位 + 原文摘录 + reason + actor + 条数
  - **不验语义真伪**：摘录是否真的来自被指文件属 LLM/主理人 T1 领域，
    脚本伪造「已核真」才是真正的诚实性事故（见 ADR-002）

spawn_manifest.jsonl 每行一个 JSON 对象，evidence_check 事件格式：
    {"event": "evidence_check", "ts": "...", "actor": "lead",
     "task_id": "T-xxx", "reason": "要害证据抽查",
     "value": {"file": "path/to/source.md", "line": 42,
               "excerpt": "原文 1-2 行摘录"}}
  兼容 "type": "evidence_check"；value 为字符串时按 "path:行号" 严格校验，
  但因无法携带摘录，仍判不合格（防只有定位没有原文的空壳记录）。

用法：
    python3 scripts/verify_evidence_check.py <run_dir>
        [--task-id <T-xxx>] [--json]

退出码契约：
    0 = 形式要件全部满足（≥2 条合格且无不合格记录）
    3 = 结构失败（manifest 缺失 / 行非法 JSON / 行非对象）
    5 = 门禁 FAIL（记录不足 2 条 / 存在不合格记录）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_STRUCT = 3
EXIT_FAIL = 5

MIN_RECORDS = 2
RE_LOCATOR = re.compile(r"^.+\.([A-Za-z0-9]+):(\d+)$")


def _is_nonempty(v) -> bool:
    """字符串非空且非纯空白。"""
    return isinstance(v, str) and bool(v.strip())


def _validate(ev: dict, task_id: str) -> list[str]:
    """核对单条 evidence_check 的形式要件，返回问题列表（空 = 合格）。"""
    bad: list[str] = []
    if ev.get("actor") != "lead":
        bad.append("actor 非 lead（抽查须主理人本人执行）")
    if task_id and ev.get("task_id") not in (None, "", task_id):
        bad.append(f"task_id={ev.get('task_id')!r} 与当前任务不符")
    if not _is_nonempty(ev.get("reason")):
        bad.append("reason 缺失/空白")
    val = ev.get("value")
    if isinstance(val, dict):
        if not _is_nonempty(val.get("file")):
            bad.append("value.file 缺失")
        line = val.get("line")
        if not (isinstance(line, int) or (_is_nonempty(line) and str(line).isdigit())):
            bad.append("value.line 非行号")
        if not _is_nonempty(val.get("excerpt")):
            bad.append("value.excerpt 缺失（无原文摘录）")
    elif isinstance(val, str):
        # 字符串只有定位、没有摘录 → 明确判不合格，不静默放行
        if not RE_LOCATOR.match(val.strip()):
            bad.append("value 非 file:行号 形式")
        bad.append("value 为字符串，缺原文摘录字段（须用对象形式）")
    else:
        bad.append("value 缺失 / 类型非法")
    return bad


def check(run_dir: Path, task_id: str = "") -> tuple[int, dict]:
    """只读校验主逻辑：返回 (退出码, 报告字典)；供 check_gates 内联复用。"""
    rep: dict = {
        "run_dir": str(run_dir),
        "task_id": task_id,
        "manifest": str(run_dir / "spawn_manifest.jsonl"),
        "total": 0,
        "valid": 0,
        "invalid": [],
        "structural_errors": [],
        "verdict": "",
    }
    path = run_dir / "spawn_manifest.jsonl"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        rep["structural_errors"].append(
            f"spawn_manifest.jsonl 不可读: {type(e).__name__}: {e}")
        rep["verdict"] = "MANIFEST_UNREADABLE"
        return EXIT_STRUCT, rep

    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as e:
            rep["structural_errors"].append(f"第 {i} 行非法 JSON: {e.msg}")
            continue
        if not isinstance(ev, dict):
            rep["structural_errors"].append(f"第 {i} 行非 JSON 对象")
            continue
        if ev.get("event") != "evidence_check" and ev.get("type") != "evidence_check":
            continue
        rep["total"] += 1
        bad = _validate(ev, task_id)
        if bad:
            rep["invalid"].append({"line": i, "problems": bad})
        else:
            rep["valid"] += 1

    if rep["structural_errors"]:
        rep["verdict"] = "MANIFEST_INVALID"
        return EXIT_STRUCT, rep
    if rep["total"] < MIN_RECORDS or rep["invalid"] or rep["valid"] < MIN_RECORDS:
        rep["verdict"] = "FAIL"
        return EXIT_FAIL, rep
    rep["verdict"] = "PASS"
    return EXIT_OK, rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="G6 抽查留痕硬门：≥2 条 lead 的 evidence_check（只读）")
    ap.add_argument("run_dir", help="run_dir 目录（内含 spawn_manifest.jsonl）")
    ap.add_argument("--task-id", default="", help="可选：只认该任务的抽查记录")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI 消费）")
    args = ap.parse_args()

    rc, rep = check(Path(args.run_dir).expanduser(), args.task_id)
    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ G6 抽查留痕 {args.task_id or '(全部任务)'} ═══")
    print(f"manifest: {rep['manifest']}")
    print(f"记录 {rep['total']} | 合格 {rep['valid']} | 不合格 {len(rep['invalid'])}")
    for item in rep["invalid"]:
        print(f"  ❌ 第 {item['line']} 行: {'；'.join(item['problems'])}")
    for e in rep["structural_errors"]:
        print(f"  ❌ 结构: {e}")
    if rep["total"] < MIN_RECORDS:
        print(f"  ❌ 抽查记录不足 {MIN_RECORDS} 条（实得 {rep['total']}）")
    print(f"\n裁决: {rep['verdict']} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
