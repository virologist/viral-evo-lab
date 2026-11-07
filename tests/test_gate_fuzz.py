#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门禁输入 fuzz 回归套件（P3-R4 · 2026-11-07）
=====================================================================
背景：前三轮交叉验证连续抓到同构缺陷——check_gates.py 的不同 JSON 消费点
      未做类型判定，畸形输入抛未捕获异常 → EXIT=1、gates.json 不落盘、
      G1–G5 全体失效（R2 waivers / R3 output-check / P3.1 envelope issues）。

本套件把「永不崩溃」固化为可自动复跑的回归门禁：
  对信封 / waivers / output-check 的所有畸形形态逐一实跑，断言
    ① 退出码 ∈ {0, 3, 5}（绝不 1）
    ② stdout+stderr 无 Traceback
    ③ gates.json 必须落盘（门禁报告不能因输入畸形而消失）
  另含 1 个合规基线用例，断言正常路径 EXIT=0。

运行：python3 tests/test_gate_fuzz.py  或  pytest tests/ -q
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
CHECK_GATES = PKG / "scripts" / "check_gates.py"
TASK_ID = "T-FUZZ"

BASE_ENV = {
    "agent_id": "phylo-analyst",
    "task_id": TASK_ID,
    "phase": 1,
    "status": "success",
    "confidence": 90,
    "deliverable_summary": "fuzz 基线产出",
    "issues": [],
}

# 每个用例：(名称, artifact 内容, waivers 对象或 None, output-check 对象或 None)
CASES = [
    ("基线（合规，应 EXIT=0）", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": {}}),
    # ---- 信封畸形 ----
    ("信封顶层 list", "[1, 2, 3]\n", None, {"artifact_mtimes": {}}),
    ("信封顶层 null", "null\n", None, {"artifact_mtimes": {}}),
    ("信封顶层标量", "42\n", None, {"artifact_mtimes": {}}),
    ("信封 issues=dict", json.dumps(dict(BASE_ENV, issues={"a": 1})) + "\n", None, {"artifact_mtimes": {}}),
    ("信封 issues=int", json.dumps(dict(BASE_ENV, issues=7)) + "\n", None, {"artifact_mtimes": {}}),
    ("信封 issues=bool", json.dumps(dict(BASE_ENV, issues=True)) + "\n", None, {"artifact_mtimes": {}}),
    ("信封 issues=str", json.dumps(dict(BASE_ENV, issues="oops")) + "\n", None, {"artifact_mtimes": {}}),
    ("信封 phase=bool", json.dumps(dict(BASE_ENV, phase=True)) + "\n", None, {"artifact_mtimes": {}}),
    ("信封 confidence=str", json.dumps(dict(BASE_ENV, confidence="high")) + "\n", None, {"artifact_mtimes": {}}),
    ("信封缺字段", json.dumps({"agent_id": "x"}) + "\n", None, {"artifact_mtimes": {}}),
    ("信封非法 JSON", "{not json}\n", None, {"artifact_mtimes": {}}),
    # ---- waivers 畸形（R2 同构点）----
    ("waivers 顶层 list", json.dumps(BASE_ENV) + "\n", [1, 2], {"artifact_mtimes": {}}),
    ("waivers 顶层 null", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": {}}),
    ("waivers value=list", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": ["0.79"]}]}, {"artifact_mtimes": {}}),
    ("waivers value=dict", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": {"a": 1}}]}, {"artifact_mtimes": {}}),
    ("waivers value=bool", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": True}]}, {"artifact_mtimes": {}}),
    ("waivers 元素非对象", json.dumps(BASE_ENV) + "\n",
     {"waivers": ["oops"]}, {"artifact_mtimes": {}}),
    ("waivers 字段非 list", json.dumps(BASE_ENV) + "\n",
     {"waivers": {"a": 1}}, {"artifact_mtimes": {}}),
    # ---- output-check 畸形（R3 同构点）----
    ("output-check 顶层 list", json.dumps(BASE_ENV) + "\n", None, [1, 2]),
    ("output-check 顶层 null", json.dumps(BASE_ENV) + "\n", None, None),
    ("output-check 顶层 str", json.dumps(BASE_ENV) + "\n", None, "oops"),
    ("output-check mtimes=list", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": [1]}),
    ("output-check mtimes=str", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": "x"}),
]


def _write(path: Path, obj) -> None:
    if obj is None:
        return
    path.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")


def run_case(name: str, artifact_text: str, waivers, oc) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="gate_fuzz_") as td:
        d = Path(td)
        (d / f"{TASK_ID}__phylo-analyst.md").write_text(artifact_text, encoding="utf-8")
        # 合规基线需要 checklist 才能 G5 PASS
        if name.startswith("基线"):
            _write(d / f"{TASK_ID}__checklist.json", {"hallucinated": 0})
        _write(d / f"{TASK_ID}__waivers.json", waivers)
        # output-check 为 None 时写显式 JSON null，覆盖「合法 JSON 但非对象」
        if oc is None:
            (d / f"{TASK_ID}__output-check.json").write_text("null\n", encoding="utf-8")
        else:
            _write(d / f"{TASK_ID}__output-check.json", oc)
        cmd = [sys.executable, str(CHECK_GATES), str(d), TASK_ID]
        if name.startswith("基线"):
            # 信封自带 confidence=90 / phase=1，须给权威源，否则 G2 会（正确地）判未溯源
            src = d / "sources"
            src.mkdir()
            (src / "truth.csv").write_text("90\n1\n", encoding="utf-8")
            cmd += ["--sources", str(src)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        problems = []
        if p.returncode not in (0, 3, 5):
            problems.append(f"exit={p.returncode}（应 ∈ {{0,3,5}}）")
        if "Traceback" in out:
            problems.append("出现 Traceback")
        if not (d / f"{TASK_ID}__gates.json").is_file():
            problems.append("gates.json 未落盘")
        if name.startswith("基线") and p.returncode != 0:
            problems.append(f"基线应 EXIT=0，实为 {p.returncode}")
        if problems:
            return False, f"{name}: " + "; ".join(problems) + f" | {out.strip()[:160]}"
        return True, f"{name}: OK (exit={p.returncode})"


def test_gate_fuzz() -> None:
    """pytest 入口：任一畸形输入导致崩溃即 FAIL。"""
    failures = []
    for name, art, wv, oc in CASES:
        ok, msg = run_case(name, art, wv, oc)
        if not ok:
            failures.append(msg)
    assert not failures, "门禁 fuzz 失败:\n  " + "\n  ".join(failures)


def main() -> int:
    ok_n = 0
    for name, art, wv, oc in CASES:
        ok, msg = run_case(name, art, wv, oc)
        print(("  ✅ " if ok else "  ❌ ") + msg)
        ok_n += int(ok)
    print(f"\nfuzz 用例 {len(CASES)} | 通过 {ok_n} | 失败 {len(CASES) - ok_n}")
    return 0 if ok_n == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
