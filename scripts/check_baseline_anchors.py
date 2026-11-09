#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_baseline_anchors.py —— 关键防线文件的包外基线对账（v1.5.8 · P2-7）
==========================================================================
背景：历史事故「联邦分发用旧基线覆盖 tests/」发生过两次，导致 CI 静默 0 覆盖。
      现有防御是包内跨文件互锚（guard ↔ test_vendor_core V7），但两个文件
      **同时**被旧基线覆盖时，包内没有任何参照能证明「防线被换了」。
      `AUDIT_STATE.md` §12 / Known Issues 一直把此列为「人工 diff 兜底」。

本脚本补上**包外独立参照**：基线 JSON 存放在审计区（不在专家包 git 仓内），
记录关键防线文件的 sha256 与字节数；本脚本只读对账，不改任何文件。

边界（诚实声明，防过度设计）：
  - **只读**：不生成、不修复、不改写锚文件；发现漂移只报告并 EXIT=5
  - **不硬编码路径**：`--anchors` 必填、`--pkg-root` 可覆盖（默认本包根）
  - 只比 sha256 + bytes，**不判断漂移是否合理**：正常改动后应重新生成基线，
    而不是改锚来「刷绿」；锚里 `source.tag/commit` 即为此留的溯源字段
  - 路径安全：锚内相对路径拒绝绝对路径 / `..` 逃逸 / `.git` 目录

锚 JSON 格式：
    {
      "schema_version": 1,
      "generated": "2026-11-09T...",
      "source": {"tag": "v1.5.8", "commit": "<hash>", "note": "..."},
      "files": {"tests/test_contract_guard.py": {"sha256": "...", "bytes": 12345}}
    }

用法：
    python3 scripts/check_baseline_anchors.py --anchors <包外基线.json>
        [--pkg-root <包根>] [--json]

退出码契约：
    0 = 全部一致
    3 = 结构失败（锚缺失/畸形 / files 非对象 / 条目字段非法 / 路径不安全）
    5 = 漂移（文件缺失 / 哈希或字节数不符）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_STRUCT = 3
EXIT_DRIFT = 5


def _sha256(path: Path) -> str:
    """文件 sha256；读取失败由调用方按「漂移」处理。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_rel(rel: str) -> bool:
    """锚内相对路径合法性：非空 str、非绝对、无 .. 逃逸、不进 .git。"""
    if not isinstance(rel, str) or not rel.strip() or rel.startswith(("/", "\\")):
        return False
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or ".git" in p.parts:
        return False
    return True


def check(anchors: Path, pkg_root: Path) -> tuple[int, dict]:
    """只读对账主逻辑：返回 (退出码, 报告字典)。所有失败路径有确定性退出码。"""
    rep: dict = {
        "anchors": str(anchors),
        "pkg_root": str(pkg_root),
        "expected": 0,
        "matched": 0,
        "missing": [],
        "mismatched": [],
        "structural_errors": [],
        "verdict": "",
    }

    try:
        obj = json.loads(anchors.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        rep["structural_errors"].append(
            f"锚文件不可读或非合法 JSON: {type(e).__name__}: {e}")
        rep["verdict"] = "ANCHOR_UNREADABLE"
        return EXIT_STRUCT, rep

    if not isinstance(obj, dict):
        rep["structural_errors"].append("锚文件顶层非对象")
        rep["verdict"] = "ANCHOR_NOT_OBJECT"
        return EXIT_STRUCT, rep
    if obj.get("schema_version") != 1:
        rep["structural_errors"].append(
            f"schema_version={obj.get('schema_version')!r} 非 1（未知锚格式，拒绝对账）")
    files = obj.get("files")
    if not isinstance(files, dict) or not files:
        rep["structural_errors"].append("files 缺失 / 非对象 / 为空")
    if rep["structural_errors"]:
        rep["verdict"] = "ANCHOR_SCHEMA_INVALID"
        return EXIT_STRUCT, rep

    rep["expected"] = len(files)
    for rel, meta in sorted(files.items()):
        if not _safe_rel(rel):
            rep["structural_errors"].append(f"非法锚路径: {rel!r}")
            continue
        if not isinstance(meta, dict) or not isinstance(meta.get("sha256"), str) \
                or len(meta["sha256"]) != 64 or not isinstance(meta.get("bytes"), int):
            rep["structural_errors"].append(f"{rel}: 条目缺合法 sha256/bytes")
            continue
        target = pkg_root / rel
        try:
            data = target.read_bytes()
        except OSError:
            rep["missing"].append(rel)
            continue
        got_sha = hashlib.sha256(data).hexdigest()
        if got_sha != meta["sha256"] or len(data) != meta["bytes"]:
            rep["mismatched"].append({
                "path": rel,
                "expected_sha256": meta["sha256"][:12],
                "actual_sha256": got_sha[:12],
                "expected_bytes": meta["bytes"],
                "actual_bytes": len(data),
            })
        else:
            rep["matched"] += 1

    if rep["structural_errors"]:
        rep["verdict"] = "ANCHOR_SCHEMA_INVALID"
        return EXIT_STRUCT, rep
    if rep["missing"] or rep["mismatched"]:
        rep["verdict"] = "DRIFT"
        return EXIT_DRIFT, rep
    rep["verdict"] = "OK"
    return EXIT_OK, rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="关键防线文件包外基线只读对账（不生成/修复锚文件）")
    ap.add_argument("--anchors", required=True,
                    help="包外基线 JSON 路径（必填；不硬编码，锚文件应不在专家包仓内）")
    ap.add_argument("--pkg-root", default=str(Path(__file__).resolve().parent.parent),
                    help="待对账的包根（默认本脚本所在专家包根）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI 消费）")
    args = ap.parse_args()

    rc, rep = check(Path(args.anchors).expanduser(), Path(args.pkg_root).expanduser())
    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ 包外基线对账 ═══\n锚: {rep['anchors']}\n包根: {rep['pkg_root']}")
    print(f"条目 {rep['expected']} | 一致 {rep['matched']} | 缺失 {len(rep['missing'])}"
          f" | 漂移 {len(rep['mismatched'])}")
    for rel in rep["missing"]:
        print(f"  ❌ 缺失: {rel}")
    for m in rep["mismatched"]:
        print(f"  ❌ 漂移: {m['path']} sha {m['expected_sha256']}… → {m['actual_sha256']}…"
              f" / bytes {m['expected_bytes']} → {m['actual_bytes']}")
    for e in rep["structural_errors"]:
        print(f"  ❌ 结构: {e}")
    label = {EXIT_OK: "✅ OK", EXIT_STRUCT: "❌ 锚结构失败", EXIT_DRIFT: "❌ 漂移"}
    print(f"\n裁决: {rep['verdict']} {label.get(rc, '')} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
