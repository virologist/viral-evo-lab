#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_decision_records.py —— 架构裁决的机器消费端（v1.5.9 · ADR-001）
==========================================================================
背景：v1.5.8 把 `--require-tag` 的默认值裁决写成「一句结论 + 不改代码」，
      文档里没有任何机制能发现「后来有人悄悄翻转了默认值」——与本包反复
      踩到的「治理断言无消费端」同构（见 LEARNINGS LRN-021）。

本脚本把 docs/decision_records.json 变成**可校验契约**：
  - 只读；不改裁决、不改代码、不生成任何文件
  - 逐条 record 检查 verification.cli_sites 的形态锚与 tests 的存活锚
  - 对 ADR-001 额外断言三处 CLI 仍为 action="store_true" 且无 default=True
  - 任一违反 → EXIT=5 / VIOLATION（防「裁决还在、实现已翻」）

边界（诚实声明）：
  - 只验**形态**，不验运行语义；运行语义由 test_gate_fuzz.py 行为级用例负责
  - 不硬编码工作区路径：`--pkg-root` / `--records` 均可覆盖（供 fixture 测试）
  - 裁决变更是人工动作：先改 JSON + 完成 enable_when/migration，再改代码

用法：
    python3 scripts/check_decision_records.py [--pkg-root <包根>]
        [--records <裁决.json>] [--json]

退出码契约：
    0 = 全部裁决与实现一致
    3 = 结构失败（裁决文件缺失/畸形 / 必填字段缺失 / cli_sites 文件不存在）
    5 = 裁决被违反（形态锚被改 / 测试锚消失 / 默认值被翻转）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_STRUCT = 3
EXIT_VIOLATION = 5

# 形态锚：`add_argument("--require-tag", action="store_true"`（容忍空白与换行）
RE_STORE_TRUE = re.compile(
    r"""add_argument\(\s*["']--require-tag["']\s*,\s*action=["']store_true["']""")
# 任何把默认值翻成 True 的写法都算违反（容忍空白）
RE_DEFAULT_TRUE = re.compile(r"""default\s*=\s*True""")

# 各 rule 的额外形态锚：(文件, 必须出现的子串元组)
RULE_ANCHORS: dict[str, dict[str, tuple[str, ...]]] = {
    "require_tag_default_off": {},
    "g6_opt_in_visible": {
        "scripts/check_gates.py": ("--require-evidence-check", "skipped_gates", "G6 抽查留痕"),
    },
    "anchor_refresh_acked": {
        "scripts/check_baseline_anchors.py": ("--i-acknowledge-refresh", "--refresh", "refresh_history"),
    },
    "decision_log_readonly": {
        "scripts/reconcile_decisions.py": ("台账", "--draft-out", "decision_log.csv"),
    },
}


def _read_text(path: Path) -> str:
    """统一读文本：BOM 与 UTF-8 变体由 utf-8-sig 兜住。"""
    return path.read_text(encoding="utf-8-sig")


def check(pkg_root: Path, records_path: Path) -> tuple[int, dict]:
    """只读校验主逻辑：返回 (退出码, 报告字典)。"""
    rep: dict = {
        "pkg_root": str(pkg_root),
        "records": str(records_path),
        "checked": 0,
        "violations": [],
        "structural_errors": [],
        "verdict": "",
    }

    try:
        obj = json.loads(_read_text(records_path))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        rep["structural_errors"].append(
            f"裁决文件不可读或非合法 JSON: {type(e).__name__}: {e}")
        rep["verdict"] = "RECORDS_UNREADABLE"
        return EXIT_STRUCT, rep

    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        rep["structural_errors"].append("schema_version 非 1 / 顶层非对象")
    recs = obj.get("records") if isinstance(obj, dict) else None
    if not isinstance(recs, list) or not recs:
        rep["structural_errors"].append("records 缺失 / 非数组 / 为空")
    if rep["structural_errors"]:
        rep["verdict"] = "RECORDS_SCHEMA_INVALID"
        return EXIT_STRUCT, rep

    for rec in recs:
        if not isinstance(rec, dict):
            rep["structural_errors"].append("record 非对象")
            continue
        rid = rec.get("id", "<无 id>")
        for field in ("id", "title", "status", "decided_at", "decision", "verification"):
            if not rec.get(field):
                rep["structural_errors"].append(f"{rid}: 缺必填字段 {field}")
        ver = rec.get("verification")
        if not isinstance(ver, dict) or not ver.get("rule"):
            rep["structural_errors"].append(f"{rid}: verification.rule 缺失")
            continue
        rule = ver["rule"]
        if rule not in RULE_ANCHORS:
            rep["structural_errors"].append(f"{rid}: 未知 rule={rule!r}（拒绝对未知裁决放行）")
            continue
        if rec.get("status") not in ("accepted", "superseded"):
            rep["structural_errors"].append(f"{rid}: status 非法")
        rep["checked"] += 1

        sites = ver.get("cli_sites")
        if not isinstance(sites, list) or not sites:
            rep["structural_errors"].append(f"{rid}: cli_sites 缺失 / 为空")
            continue
        for rel in sites:
            f = pkg_root / rel
            try:
                src = _read_text(f)
            except (OSError, UnicodeError) as e:
                rep["structural_errors"].append(f"{rid}: {rel} 不可读: {type(e).__name__}")
                continue
            # ADR-001：三处 CLI 必须保持默认关闭
            if rule == "require_tag_default_off":
                if not RE_STORE_TRUE.search(src):
                    rep["violations"].append(f"{rid}: {rel} 已非 action=\"store_true\" 形态")
                if RE_DEFAULT_TRUE.search(src):
                    rep["violations"].append(f"{rid}: {rel} 出现 default=True（默认值被翻转）")
            # 其余 rule：文件内形态锚必须齐备
            for needle in RULE_ANCHORS[rule].get(rel, ()):
                if needle not in src:
                    rep["violations"].append(f"{rid}: {rel} 缺形态锚 {needle!r}")

        # 测试锚：在 tests/ 下任一 .py 中出现即可（防测试被静默删除）
        tests = ver.get("tests")
        if not isinstance(tests, list) or not tests:
            rep["structural_errors"].append(f"{rid}: tests 缺失 / 为空")
            continue
        test_src = ""
        try:
            for p in sorted((pkg_root / "tests").glob("*.py")):
                test_src += _read_text(p) + "\n"
        except (OSError, UnicodeError) as e:
            rep["structural_errors"].append(f"{rid}: tests/ 不可读: {type(e).__name__}: {e}")
        for anchor in tests:
            if anchor not in test_src:
                rep["violations"].append(f"{rid}: 测试锚 {anchor!r} 在 tests/ 中消失")

    if rep["structural_errors"]:
        rep["verdict"] = "RECORDS_SCHEMA_INVALID"
        return EXIT_STRUCT, rep
    if rep["violations"]:
        rep["verdict"] = "VIOLATION"
        return EXIT_VIOLATION, rep
    rep["verdict"] = "OK"
    return EXIT_OK, rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="架构裁决机器消费端：只读校验裁决与实现是否一致（不改任何文件）")
    default_root = Path(__file__).resolve().parent.parent
    ap.add_argument("--pkg-root", default=str(default_root),
                    help="待校验的包根（默认本脚本所在专家包根；可供 fixture 覆盖）")
    ap.add_argument("--records", default=None,
                    help="裁决 JSON 路径（默认 <pkg-root>/docs/decision_records.json）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI 消费）")
    args = ap.parse_args()

    root = Path(args.pkg_root).expanduser().resolve()
    rec = Path(args.records).expanduser().resolve() if args.records \
        else root / "docs" / "decision_records.json"
    rc, rep = check(root, rec)
    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ 裁决一致性校验 ═══\n包根: {rep['pkg_root']}\n裁决: {rep['records']}")
    print(f"记录 {rep['checked']} | 违反 {len(rep['violations'])} | 结构错误 {len(rep['structural_errors'])}")
    for v in rep["violations"]:
        print(f"  ❌ 违反: {v}")
    for e in rep["structural_errors"]:
        print(f"  ❌ 结构: {e}")
    print(f"\n裁决: {rep['verdict']} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
