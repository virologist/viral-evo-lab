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

L3（2026-11-09）：补「行为断言」层——原套件只断言不崩溃，
      无法发现「门禁恒判 PASS/FAIL」的静默失效。現增：
    ④ CASES 可声明期望的门禁结果（G1/G2/G4 ok 布尔），逐项断言；
    ⑤ 新增 WF4 workflow 变体归一化用例族；
    ⑥ 新增 G4 waiver 放行五路径用例（放行/无签名/无理由/值不匹配/部分覆盖）；
    ⑦ 新增 gate_mode 与处置门禁行为回归。

v1.5.8（2026-11-09 · 遗留 backlog 清理轮）：行为级用例 6 → **9**，
      新增三组「生产者-消费者闭环」回归——G3 FAIL 早退落盘 / decision_log
      只读审计退出码与不代写 / 包外基线锚对账；当时的 main() total 同步。

v1.5.10（2026-11-10 · 当前口径补正）：行为级用例 9 → **15**，共 **60/60**
      （45 CASES + 15 行为级）。v1.5.9 新增五组裁决/门禁/对账/锚刷新/cron
      回归（9→14）；v1.5.10 再补一组「当前口径一致性」守卫回归（14→15）。
      main() 的 total = len(CASES) + 15 —— 本段为 v1.5.10 时点基线，
      上方 v1.5.8 段属历史记录，不得据其推断当前用例数。

v1.5.11（2026-11-10 · 终验盲检 R6 加固）：用例数不变，仍为 45 CASES +
      15 行为级 = 60/60。修正本套件的三处自审漏洞——①守卫第 11 项补
      `last_updated: 2026-11-10` 正向锚（防日期换成任意旧值仍全绿）；
      ② `_wording_counts()` 改为只在 `main()` 函数体内取 total（原全文
      re.search 先命中 docstring 自己，属自证），并加「仅改 main() total
      必被抓」反向断言；      ③反向金丝雀扩为逐锚回退（5 文件 13 个正向锚
      摘除 + 3 个旧口径串注入），逐项断言第 11 项 FAIL；锚清单直接取守卫
      模块的 WORDING_* 常量（单一事实源），只调 check_current_wording()
      并只复制被检 5 文件，实测 157s → 约 10s。本段为 v1.5.11 时点基线。

v1.5.12（2026-11-10 · 终验盲检 R7 收敛）：用例数不变。第三次盲检指出
      `_wording_counts()` 的 doc 正则用「v1.5.x 跨行 …（45 CASES + N 行为级）」
      宽匹配，实际命中 v1.5.10 **历史段**，自称「当前基线」的上段数字被改成 14
      仍会全绿。现改为显式机器锚 `CURRENT_BASELINE = 45 CASES + N 行为级`，
      `_wording_counts` 只认本锚；并补「仅改当前基线声明数字必被抓」反向
      断言。守卫正向锚 13 → 14（加 CURRENT_BASELINE 存活锚），逐锚回退
      16 → 17 次。**当前基线以本锚为准。**
      当前基线机器锚（唯一被 _wording_counts 读取）：
      CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61

运行：python3 tests/test_gate_fuzz.py  或  pytest tests/ -q
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
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

# 每个用例：(名称, artifact 内容, waivers 对象或 None, output-check 对象或 None, 期望)
# 期望为 None = 只断言不崩溃；否则为 dict，可含：
#   "gates": {"G1": True, "G2": False, "G4": False}  —— 门禁期望结果
#   "exit": 0 | 3 | 5                              —— 期望退出码
#   "sources": True                               —— 是否提供权威源
CASES = [
    ("基线（合规，应 EXIT=0）", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": {}},
     {"exit": 0, "gates": {"G1": True, "G5": True}, "sources": True}),
    # ---- 信封畸形 ----
    ("信封顶层 list", "[1, 2, 3]\n", None, {"artifact_mtimes": {}}, None),
    ("信封顶层 null", "null\n", None, {"artifact_mtimes": {}}, None),
    ("信封顶层标量", "42\n", None, {"artifact_mtimes": {}}, None),
    ("信封 issues=dict", json.dumps(dict(BASE_ENV, issues={"a": 1})) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封 issues=int", json.dumps(dict(BASE_ENV, issues=7)) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封 issues=bool", json.dumps(dict(BASE_ENV, issues=True)) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封 issues=str", json.dumps(dict(BASE_ENV, issues="oops")) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封 phase=bool", json.dumps(dict(BASE_ENV, phase=True)) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封 confidence=str", json.dumps(dict(BASE_ENV, confidence="high")) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封缺字段", json.dumps({"agent_id": "x"}) + "\n", None, {"artifact_mtimes": {}}, None),
    ("信封非法 JSON", "{not json}\n", None, {"artifact_mtimes": {}}, None),
    # ---- waivers 畸形（R2 同构点）----
    ("waivers 顶层 list", json.dumps(BASE_ENV) + "\n", [1, 2], {"artifact_mtimes": {}}, None),
    ("waivers 顶层 null", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": {}}, None),
    ("waivers value=list", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": ["0.79"]}]}, {"artifact_mtimes": {}}, None),
    ("waivers value=dict", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": {"a": 1}}]}, {"artifact_mtimes": {}}, None),
    ("waivers value=bool", json.dumps(BASE_ENV) + "\n",
     {"waivers": [{"gate": "G2", "value": True}]}, {"artifact_mtimes": {}}, None),
    ("waivers 元素非对象", json.dumps(BASE_ENV) + "\n",
     {"waivers": ["oops"]}, {"artifact_mtimes": {}}, None),
    ("waivers 字段非 list", json.dumps(BASE_ENV) + "\n",
     {"waivers": {"a": 1}}, {"artifact_mtimes": {}}, None),
    # ---- output-check 畸形（R3 同构点）----
    ("output-check 顶层 list", json.dumps(BASE_ENV) + "\n", None, [1, 2], None),
    ("output-check 顶层 null", json.dumps(BASE_ENV) + "\n", None, None, None),
    ("output-check 顶层 str", json.dumps(BASE_ENV) + "\n", None, "oops", None),
    ("output-check mtimes=list", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": [1]}, None),
    ("output-check mtimes=str", json.dumps(BASE_ENV) + "\n", None, {"artifact_mtimes": "x"}, None),
    # ---- C1（2026-11-08）：WF4 假说锚定字段条件触发 ----
    ("WF4合规（应 EXIT=0）", json.dumps(dict(BASE_ENV, workflow="WF4", hypothesis_anchor={
        "hypothesis_id": "HX", "biological_question": "占位问题",
        "falsification_condition": "占位条件"})) + "\n", None, {"artifact_mtimes": {}},
     {"exit": 0, "gates": {"G1": True}, "sources": True}),
    ("WF4缺 anchor（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="WF4")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("WF4 anchor 畸形（str）", json.dumps(dict(BASE_ENV, workflow="WF4",
                                              hypothesis_anchor="oops")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    # ---- L3（2026-11-09）：workflow 变体归一化不得被绕过 ----
    ("workflow=WF4/analysis（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="WF4/analysis")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("workflow=wf4 小写（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="wf4")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("workflow=WF4 分析执行（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="WF4 分析执行")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("workflow=analysis（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="analysis")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("workflow=wf4-分析（应 G1 FAIL）", json.dumps(dict(BASE_ENV, workflow="wf4-分析")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}}),
    ("workflow=WF1（非分析类，G1 应 PASS）", json.dumps(dict(BASE_ENV, workflow="WF1")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}}),
    # ---- L3：no_hypothesis_justification 允许并列在信封顶层 ----
    ("顶层 no_hypothesis_justification（应 G1 PASS）", json.dumps(dict(
        BASE_ENV, workflow="WF4",
        hypothesis_anchor={"biological_question": "Q", "falsification_condition": "C"},
        no_hypothesis_justification="纯方法学校验，无活跃假说可锚")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}}),
    # ---- L3（2026-11-09 · A-1）：sidecar 交叉核验（workflow 生产者 + 防规避）----
    # 背景：workflow 字段全包无任何生产者 → G1 锚定校验是死代码；
    # 且成员自报 workflow 可降级规避（自报 = 自证清白）。
    # 现由主理人下发落 sidecar，门禁做类别级双向比对。
    ("A1 下发WF4+回传WF1（谎报规避，应 G1 FAIL）", json.dumps(
        dict(BASE_ENV, workflow="WF1")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}, "sidecar": "WF4"}),
    ("A1 下发WF4+回传缺workflow（应 G1 FAIL）", json.dumps(BASE_ENV) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}, "sidecar": "WF4"}),
    ("A1 下发WF4+回传WF4+有anchor（应 G1 PASS）", json.dumps(dict(
        BASE_ENV, workflow="WF4", hypothesis_anchor={
            "hypothesis_id": "H1", "biological_question": "Q",
            "falsification_condition": "C"})) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}, "sidecar": "WF4"}),
    ("A1 下发WF4+回传WF4+无anchor（应 G1 FAIL）", json.dumps(
        dict(BASE_ENV, workflow="WF4")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}, "sidecar": "WF4"}),
    ("A1 下发WF4+回传analysis（表述差异，应 G1 PASS）", json.dumps(dict(
        BASE_ENV, workflow="analysis", hypothesis_anchor={
            "hypothesis_id": "H1", "biological_question": "Q",
            "falsification_condition": "C"})) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}, "sidecar": "WF4"}),
    ("A1 下发WF4分析执行+回传WF4（表述差异，应 G1 PASS）", json.dumps(dict(
        BASE_ENV, workflow="WF4", hypothesis_anchor={
            "hypothesis_id": "H1", "biological_question": "Q",
            "falsification_condition": "C"})) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}, "sidecar": "WF4 分析执行"}),
    ("A1 无sidecar+回传WF1（存量链路，应 G1 PASS）", json.dumps(
        dict(BASE_ENV, workflow="WF1")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}}),
    ("A1 无sidecar+回传缺workflow（存量链路，应 G1 PASS）", json.dumps(BASE_ENV) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}}),
    ("A1 下发WF1+回传WF1（非分析类，应 G1 PASS）", json.dumps(
        dict(BASE_ENV, workflow="WF1")) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": True}, "sidecar": "WF1"}),
    ("A1 下发WF1+回传WF4（伪造升级，应 G1 FAIL）", json.dumps(
        dict(BASE_ENV, workflow="WF4", hypothesis_anchor={
            "hypothesis_id": "H1", "biological_question": "Q",
            "falsification_condition": "C"})) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False}, "sidecar": "WF1"}),
    ("A1 sidecar 顶层非对象（应 G1 FAIL，不得降级）", json.dumps(BASE_ENV) + "\n",
     None, {"artifact_mtimes": {}}, {"gates": {"G1": False},
                                    "sidecar": {"task_id": TASK_ID, "workflow": 42}}),
]


def _write(path: Path, obj) -> None:
    if obj is None:
        return
    path.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")


# 合规 checklist（A-7 修复后 G5 要求 verdict=PASS；空壳 checklist 不再算留痕）
PASS_CHECKLIST = {
    "ts": "2026-11-09T00:00:00",
    "task_id": TASK_ID,
    "items_total": 4,
    "items_passed": 4,
    "sources_checked": 1,
    "hallucinated": 0,
    "verdict": "PASS",
    "note": "fuzz 基线",
}


def _read_gates(d: Path) -> dict:
    """读回 gates.json 的门禁结果（供行为断言）。

    gates.json 的 gate 名为展示文案（如 "G1 信封完整"），
    此处按 "G1" 前缀归一为 "G1"，便于断言。
    """
    p = d / f"{TASK_ID}__gates.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    gates = data.get("gates") if isinstance(data, dict) else None
    if not isinstance(gates, list):
        return {}
    out = {}
    for g in gates:
        if not isinstance(g, dict) or "gate" not in g:
            continue
        name = str(g["gate"])
        code = name.split()[0] if name else ""
        out[code] = bool(g.get("ok"))
        out[name] = bool(g.get("ok"))
    return out


def run_case(name: str, artifact_text: str, waivers, oc, expect=None) -> tuple[bool, str]:
    expect = expect or {}
    with tempfile.TemporaryDirectory(prefix="gate_fuzz_") as td:
        d = Path(td)
        (d / f"{TASK_ID}__phylo-analyst.md").write_text(artifact_text, encoding="utf-8")
        # L3（2026-11-09 · A-1）：落主理人工作流声明 sidecar（交叉核验权威源）
        # expect["sidecar"] 为 None → 不落 sidecar（存量链路）；
        # 为字符串 → 落该 workflow 值；为 dict → 落原始对象（含畸形态测试）。
        sc = expect.get("sidecar", None)
        if isinstance(sc, dict):
            (d / f"{TASK_ID}__workflow.json").write_text(
                json.dumps(sc, ensure_ascii=False) + "\n", encoding="utf-8")
        elif isinstance(sc, str):
            (d / f"{TASK_ID}__workflow.json").write_text(
                json.dumps({"task_id": TASK_ID, "member": "phylo-analyst",
                            "workflow": sc}, ensure_ascii=False) + "\n", encoding="utf-8")
        # 需要 G5 PASS 的用例（基线 / 明确要求 exit=0）补合规 checklist
        if name.startswith(("基线", "WF4合规")):
            _write(d / f"{TASK_ID}__checklist.json", PASS_CHECKLIST)
        _write(d / f"{TASK_ID}__waivers.json", waivers)
        # output-check 为 None 时写显式 JSON null，覆盖「合法 JSON 但非对象」
        if oc is None:
            (d / f"{TASK_ID}__output-check.json").write_text("null\n", encoding="utf-8")
        else:
            _write(d / f"{TASK_ID}__output-check.json", oc)
        cmd = [sys.executable, str(CHECK_GATES), str(d), TASK_ID]
        if expect.get("sources"):
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
        if "exit" in expect and p.returncode != expect["exit"]:
            problems.append(f"{name} 应 EXIT={expect['exit']}，实为 {p.returncode}")
        # 行为断言：门禁结果必须符合期望（原套件只断言不崩溃，抓不到静默失效）
        want_gates = expect.get("gates") or {}
        if want_gates:
            got = _read_gates(d)
            if not got:
                problems.append("gates.json 无可读门禁结果")
            for gname, want_ok in want_gates.items():
                if gname not in got:
                    problems.append(f"门禁 {gname} 未出现在 gates.json")
                elif got[gname] != want_ok:
                    problems.append(f"门禁 {gname} 期望 {'PASS' if want_ok else 'FAIL'}，实为 "
                                    f"{'PASS' if got[gname] else 'FAIL'}")
        if problems:
            return False, f"{name}: " + "; ".join(problems) + f" | {out.strip()[:200]}"
        return True, f"{name}: OK (exit={p.returncode})"


def test_gate_fuzz() -> None:
    """pytest 入口：任一畸形输入导致崩溃或行为不符即 FAIL。"""
    failures = []
    for name, art, wv, oc, expect in CASES:
        ok, msg = run_case(name, art, wv, oc, expect)
        if not ok:
            failures.append(msg)
    assert not failures, "门禁 fuzz 失败:\n  " + "\n  ".join(failures)

    # R4.22（盲检双路 13 项坐实 fail-open 回归）——刻意复用本函数：零新增
    # `def test_*`，不动脚本 main() 的 CASES+16 行为级机器锚。每项自建最小
    # fixture + 真实 CLI 实跑，断言 fail-closed，正字对照保持合法。
    def _rc(script: str, *args: str) -> int:
        return subprocess.run([sys.executable, str(PKG / "scripts" / script), *args],
                              capture_output=True, text=True, timeout=60).returncode

    with tempfile.TemporaryDirectory(prefix="r422_") as td:
        d = Path(td)
        # A1 audit_decision_log 未来 ts → 内容违规 5
        led = d / "decision_log.csv"
        led.write_text("ts,actor,decision_type,decision,rationale,tier\n"
                       "2099-01-01T00:00:00+08:00,lead,x,y,z,通知档\n", encoding="utf-8")
        assert _rc("audit_decision_log.py", str(led), "--max-age-days", "30") == 5, \
            "R4.22 A1 未来台账 ts 须 EXIT=5"
        # A2 hypothesis_watch 未来 last_updated 吞 fatal → REVIEW 5
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "last_updated": "2099-01-01T00:00:00+08:00", "active_hypotheses": []}), encoding="utf-8")
        (ro / "00_governance" / "redteam_ledger.csv").write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            "F-R422,fatal,closed,2026-11-28,证伪\n", encoding="utf-8")
        assert _rc("hypothesis_watch.py", "--research-ops", str(ro)) == 5, \
            "R4.22 A2 未来池基准吞 fatal 须 EXIT=5"
        # A3 poll 未来 mtime → NOT_READY 5
        run3 = d / "run3"; run3.mkdir()
        art3 = run3 / "T-X__phylo-analyst.md"
        art3.write_text("# deliverable\n", encoding="utf-8")
        os.utime(art3, (2 ** 31, 2 ** 31))  # 2038 未来
        assert _rc("poll_run_dir.py", str(run3), "T-X", "--expected", "phylo-analyst") == 5, \
            "R4.22 A3 未来 mtime 须 EXIT=5"
        # A4 poll CJK 兼容字插撞限词 → 撞限 5
        for f in run3.glob("*.md"):
            f.unlink()
        art4 = run3 / "T-X__phylo-analyst.md"
        art4.write_text("<!-- 轮\uf900次耗尽：产出不完整 -->\n", encoding="utf-8")
        assert _rc("poll_run_dir.py", str(run3), "T-X", "--expected", "phylo-analyst") == 5, \
            "R4.22 A4 CJK 兼容字隔断撞限词须 EXIT=5"
        # A9 数字声明 prime 复合 token → 3；B1 引号豁免 pABC → 3
        src9 = d / "src9"; src9.mkdir()
        (src9 / "truth.csv").write_text("n,30\np,0.9441\n", encoding="utf-8")
        a9 = d / "a9.md"; a9.write_text("样本 n = 30\u20325\n", encoding="utf-8")
        assert _rc("verify_numbers.py", str(a9), "--sources", str(src9)) == 3, \
            "R4.22 A9 prime 复合 token 须 EXIT=3"
        b1 = d / "b1.md"; b1.write_text('"pABC=0.94"\n', encoding="utf-8")
        assert _rc("verify_numbers.py", str(b1), "--sources", str(src9)) == 3, \
            "R4.22 B1 引号豁免伪造声明须 EXIT=3"
        # B5 可见内容 BLANK Lo 视觉空白 → G6 不合格 5
        g6 = d / "g6"; g6.mkdir()
        (g6 / "spawn_manifest.jsonl").write_text(
            json.dumps({"event": "spawn", "task_id": "T-X", "member": "phylo-analyst"}) + "\n",
            encoding="utf-8")
        (g6 / "T-X__phylo-analyst.md").write_text(json.dumps(BASE_ENV) + "\n", encoding="utf-8")
        (g6 / "T-X__checklist.json").write_text(json.dumps({
            "verdict": "PASS", "items_total": 1, "items_passed": 1,
            "sources_checked": 1, "hallucinated": 0}) + "\n", encoding="utf-8")
        blank = "\U00013441" * 4
        (g6 / "T-X__evidence_check.json").write_text(json.dumps({
            "checks": [{"kind": "抽查", "actor": blank, "reason": blank, "excerpt": blank,
                        "line": 1, "file": "x.md"}]}) + "\n", encoding="utf-8")
        ev_rc = _rc("verify_evidence_check.py", str(g6))
        assert ev_rc in (3, 5), f"R4.22 B5 BLANK 视觉空白须不合格，实为 EXIT={ev_rc}"
        # A5 G4 gate_mode 大小写变体 → 阻断态信号不得消失 5
        gm = d / "gm"; gm.mkdir(); (gm / "src").mkdir()
        (gm / "src" / "t.csv").write_text("90\n", encoding="utf-8")
        (gm / "T-X__phylo-analyst.md").write_text(json.dumps(BASE_ENV) + "\n", encoding="utf-8")
        (gm / "T-X__checklist.json").write_text(json.dumps({
            "verdict": "PASS", "items_total": 1, "items_passed": 1,
            "sources_checked": 1, "hallucinated": 0}) + "\n", encoding="utf-8")
        oc5 = {"artifact_mtimes": {}, "verdict": "DEGRADE", "gate_mode": "BLOCK",
               "unverified": [{"member": "phylo-analyst", "kind": "n_eq", "value": "777"}]}
        (gm / "T-X__output-check.json").write_text(json.dumps(oc5) + "\n", encoding="utf-8")
        assert _rc("check_gates.py", str(gm), "T-X", "--sources", str(gm / "src")) == 5, \
            "R4.22 A5 gate_mode=BLOCK 不得静默放行"
        # A6 require-tag default 真值别名 → 在 test_decision_records_guard 中
        # 复用其完整最小包 fixture 加断言（见该函数末尾 R4.22 段），此处不重复。
        # A7 锚 source commit=""+tag → 结构错 3；A8 硬链接代写台账 → 拒绝 3
        anch = json.loads((PKG / "integrity_manifest.json").read_text(encoding="utf-8"))
        anch["source"] = {"tag": "v1.5.8", "commit": ""}
        af = d / "anchor.json"; af.write_text(json.dumps(anch), encoding="utf-8")
        assert _rc("check_baseline_anchors.py", "--anchors", str(af),
                   "--pkg-root", str(PKG)) == 3, "R4.22 A7 commit 空串须 EXIT=3"
        recon = d / "recon"; (recon / "run").mkdir(parents=True)
        (recon / "decision_log.csv").write_text(
            "ts,actor,decision_type,decision,rationale,tier\n"
            "2026-11-27T10:00:00+08:00,lead,initial,基线,初始,通知档\n",
            encoding="utf-8", newline="")
        (recon / "run" / "T-X__waivers.json").write_text(
            json.dumps({"waivers": [{"gate": "G2", "value": "79", "reason": "x"}]}), encoding="utf-8")
        os.link(recon / "decision_log.csv", recon / "DRAFT.csv")
        assert _rc("reconcile_decisions.py", "--run-dirs", str(recon / "run"),
                   "--ledger", str(recon / "decision_log.csv"),
                   "--draft-out", str(recon / "DRAFT.csv")) == 3, \
            "R4.22 A8 硬链接别名代写台账须 EXIT=3"
        # B3 G4 ts 未来/非字符串 → 内容锚不可信（配合阻断态时 FAIL）。
        # 无阻断信号的纯 PASS 态 G4 不拦截属设计（见 CHANGELOG 残留披露），
        # 此处断言「未来 ts + DEGRADE 未处置」仍 FAIL，锁定修复语义。
        (gm / "T-X__output-check.json").write_text(json.dumps({
            "artifact_mtimes": {}, "ts": "2099-01-01T00:00:00", "verdict": "DEGRADE",
            "gate_mode": "block",
            "unverified": [{"member": "phylo-analyst", "kind": "n_eq", "value": "777"}]}),
            encoding="utf-8")
        assert _rc("check_gates.py", str(gm), "T-X", "--sources", str(gm / "src")) == 5, \
            "R4.22 B3 未来 ts 阻断态仍须 EXIT=5"
        # A10 V5 任务包非字符串类型混淆 → 本包调用层类型预检拒绝 4
        bad_v5 = {"objective": "d", "output_format": "md", "constraints": [],
                  "task_boundary": "仅本任务",
                  "acceptance_criteria": [{"check": "存在", "judge_mode": 0, "threshold": 0}]}
        v5f = d / "v5.json"; v5f.write_text(json.dumps(bad_v5, ensure_ascii=False), encoding="utf-8")
        assert subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                               "--member", "literature-scout", "--task-file", str(v5f),
                               "--check-task-package", "--out", str(d / "spawn.md")],
                              capture_output=True, text=True, timeout=60).returncode == 4, \
            "R4.22 A10 非字符串 judge_mode/threshold 须 EXIT=4"

        # ── R4.23（v1.5.39 双路盲检 5 组坐实 fail-open 回归）────────────
        # A-1 reviewed_at 未来使复核验收恒真 → INCOMPLETE 6
        state = ro / "00_governance" / "hypothesis_watch_state.json"
        state.write_text(json.dumps({"handled_finding_ids": [],
                                     "reviewed_at": "2099-01-01T00:00:00+08:00"}), encoding="utf-8")
        # 需池超期且无未处置 fatal，才走到 reviewed_at 判据
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "last_updated": "2026-01-01T00:00:00+08:00", "active_hypotheses": []}), encoding="utf-8")
        (ro / "00_governance" / "redteam_ledger.csv").write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            "F-OK,low,closed,2026-01-02,非致命\n", encoding="utf-8")
        assert _rc("hypothesis_watch.py", "--research-ops", str(ro),
                   "--check-disposition") == 6, "R4.23 A-1 未来 reviewed_at 须 INCOMPLETE/6"
        # A-2 \b 与提取口径漂移：样本n（CJK 紧邻）复合 token 须 3
        a2 = d / "r423_a2.md"; a2.write_text("样本n = 30\u20325\n", encoding="utf-8")
        assert _rc("verify_numbers.py", str(a2), "--sources", str(src9)) == 3, \
            "R4.23 A-2 CJK 紧邻 prime 复合 token 须 EXIT=3"
        # B-2 CJK 兼容字隔断 check_scope 黑名单 → 3
        b2 = d / "r423_b2.md"; b2.write_text("事故编号见 PP 41\uf900034380\n", encoding="utf-8")
        assert _rc("check_scope.py", str(b2)) == 3, \
            "R4.23 B-2 CJK 兼容字隔断黑名单须 EXIT=3"
        # A-3 default 浮点真值别名 → 5（复用 A6 的脚本，构造浮点注入）
        cli2 = d / "r423_cli"; (cli2 / "scripts").mkdir(parents=True)
        (cli2 / "docs").mkdir(); (cli2 / "tests").mkdir()
        # 6 个 rule 锚文件齐备（同 test_decision_records_guard），否则结构错误 3
        for n2 in ("check_gates.py", "verify_numbers.py", "verify_member_output.py",
                   "verify_evidence_check.py", "reconcile_decisions.py", "check_baseline_anchors.py"):
            src2 = (PKG / "scripts" / n2).read_text(encoding="utf-8")
            if n2 == "check_gates.py":
                src2 = src2.replace('action="store_true",\n                    help="严审模式',
                                    'action="store_true", default=0.5,\n                    help="严审模式', 1)
            (cli2 / "scripts" / n2).write_text(src2, encoding="utf-8")
        (cli2 / "docs" / "decision_records.json").write_bytes(
            (PKG / "docs" / "decision_records.json").read_bytes())
        (cli2 / "tests" / "anchors.py").write_text(
            "# " + "\n# ".join(("test_require_tag_gate", "require_tag 闸三点接线存活",
                               "test_g6_evidence_gate", "test_anchor_refresh_guard",
                               "test_reconcile_decisions")),
            encoding="utf-8")
        assert _rc("check_decision_records.py", "--pkg-root", str(cli2), "--json") == 5, \
            "R4.23 A-3 default=0.5 浮点真值别名须 EXIT=5"
        # A-4/B-3 V5 围栏 + 前置散文使双实现解析漂移 → 4
        fence = d / "r423_v5.md"
        fence.write_text('```json\n' + json.dumps(bad_v5, ensure_ascii=False) +
                         '\n```\n说明：阈值取自 config/foo.yaml}\n', encoding="utf-8")
        assert _rc("assemble_spawn_prompt.py", "--member", "literature-scout",
                   "--task-file", str(fence), "--check-task-package",
                   "--out", str(d / "spawn2.md")) == 4, \
            "R4.23 A-4 围栏 JSON 类型预检漂移须 EXIT=4"


def test_g4_waiver_release() -> None:
    """L3（2026-11-09）：G4 阻断态的 waiver 放行五路径行为回归。

    背景：G4 的提示与文档均声称「主理人核 URL 后写 waivers.json 放行」，
    但原实现完全不读 waiver——实测写好 waivers.json 后 G4 仍判 FAIL，
    文档承诺与代码行为背离，主理人只剩违反诚实性红线的「人工裁量跳过」。

    本用例固化五条路径：
      ① 无 waivers → G4 FAIL（阻断生效）
      ② value+reason+authorized_by 齐备 → G4 PASS（放行生效）
      ③ 缺 authorized_by → G4 FAIL（防自我授权）
      ④ 缺 reason → G4 FAIL（防空口放行）
      ⑤ 值不匹配 → G4 FAIL（放行不得张冠李戴）
    """
    with tempfile.TemporaryDirectory(prefix="g4_waiver_") as td:
        d = Path(td)
        run = d / "run"
        run.mkdir()
        src = d / "src"
        src.mkdir()
        (src / "truth.csv").write_text("90\n1\n", encoding="utf-8")
        art = run / f"{TASK_ID}__phylo-analyst.md"
        art.write_text(
            json.dumps(dict(BASE_ENV, workflow="WF4", hypothesis_anchor={
                "hypothesis_id": "HX", "biological_question": "Q",
                "falsification_condition": "C"})) + "\n样本量 n=777。\n",
            encoding="utf-8")
        (run / f"{TASK_ID}__checklist.json").write_text(
            json.dumps(PASS_CHECKLIST, ensure_ascii=False) + "\n", encoding="utf-8")
        (run / f"{TASK_ID}__output-check.json").write_text(json.dumps({
            "ts": "2026-11-09T00:00:00", "task_id": TASK_ID,
            "checked_artifacts": [art.name], "artifact_mtimes": {},
            "unverified": [{"member": "phylo-analyst", "kind": "n_eq", "value": "777"}],
            "verdict": "DEGRADE", "gate_mode": "block",
            "sources_used": [str(src)]}, ensure_ascii=False) + "\n", encoding="utf-8")

        def g4_ok(waiver_obj) -> bool:
            wp = run / f"{TASK_ID}__waivers.json"
            if waiver_obj is None:
                wp.unlink(missing_ok=True)
            else:
                wp.write_text(json.dumps(waiver_obj, ensure_ascii=False) + "\n", encoding="utf-8")
            p = subprocess.run(
                [sys.executable, str(CHECK_GATES), str(run), TASK_ID, "--sources", str(src)],
                capture_output=True, text=True, timeout=60)
            got = _read_gates(run)
            return got.get("G4", False)

        full = {"waivers": [{"gate": "G2", "value": "777",
                             "reason": "外部引文 arXiv:2506.12482",
                             "authorized_by": "team-lead"}]}
        assert g4_ok(None) is False, "无 waivers 时 G4 必须 FAIL（阻断生效）"
        assert g4_ok(full) is True, "齐备 waiver 必须放行 G4（文档承诺的放行路径须真实存在）"
        no_sign = {"waivers": [{"gate": "G2", "value": "777",
                                 "reason": "外部引文 arXiv:2506.12482"}]}
        assert g4_ok(no_sign) is False, "缺 authorized_by 的 waiver 不得放行（防自我授权）"
        no_reason = {"waivers": [{"gate": "G2", "value": "777", "authorized_by": "team-lead"}]}
        assert g4_ok(no_reason) is False, "缺 reason 的 waiver 不得放行（防空口放行）"
        mismatch = {"waivers": [{"gate": "G2", "value": "999",
                                 "reason": "r", "authorized_by": "team-lead"}]}
        assert g4_ok(mismatch) is False, "值不匹配的 waiver 不得放行（防张冠李戴）"


def test_disposition_gate() -> None:
    """L3（2026-11-09）：假说治理触发器（hypothesis_watch）行为回归。

    覆盖三类断言：
      ① 畸形输入（state 顶层 list/str/null、非字符串元素；假说池顶层 list/str）
         一律退出码 ∈ {0,3,5,6} 且无 Traceback——退出码契约不得破裂；
      ② 干净项目（无待处置 + 池未超期）跑 --check-disposition 判 PASS(0)，
         不因「台账文件不存在」误阻断存量项目；
      ③ 有未处置 fatal 时判 EXIT=6，且畸形 state 不得让 fatal 漏报。
    """
    hw = PKG / "scripts" / "hypothesis_watch.py"
    with tempfile.TemporaryDirectory(prefix="disp_gate_") as td:
        d = Path(td)
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        hyp_p = ro / "context_stack" / "confirmed_hypotheses.json"
        led_p = ro / "00_governance" / "redteam_ledger.csv"
        st_p = ro / "00_governance" / "hypothesis_watch_state.json"
        hyp_p.write_text(json.dumps({
            "last_updated": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        led_p.write_text("finding_id,severity,status,closed_date,finding_summary\n",
                         encoding="utf-8")

        def run(*extra) -> tuple[int, str]:
            p = subprocess.run([sys.executable, str(hw), "--research-ops", str(ro), *extra],
                               capture_output=True, text=True, timeout=60)
            return p.returncode, p.stdout + p.stderr

        # ① 畸形 state：不崩溃、退出码合法
        for bad in ('[1,2,3]', '"oops"', 'null', '{"handled_finding_ids":[{"a":1}]}',
                    '{"handled_finding_ids":"notalist"}'):
            st_p.write_text(bad + "\n", encoding="utf-8")
            rc, out = run()
            assert rc in (0, 3, 5, 6), f"畸形 state {bad} 退出码越界: {rc}"
            assert "Traceback" not in out, f"畸形 state {bad} 抛未捕获异常"

        # ① 畸形假说池：退出码 3（结构畸形）
        for bad in ('[1,2]', '"str"', 'null', '{bad json'):
            hyp_p.write_text(bad + "\n", encoding="utf-8")
            rc, out = run()
            assert rc == 3, f"畸形假说池 {bad} 应 EXIT=3，实为 {rc}"
            assert "Traceback" not in out, f"畸形假说池 {bad} 抛未捕获异常"
        hyp_p.write_text(json.dumps({
            "last_updated": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")

        # ② 干净项目：无台账也应 PASS（不误阻断存量项目）
        st_p.unlink(missing_ok=True)
        rc, out = run("--check-disposition")
        assert rc == 0, f"干净项目不应被 --check-disposition 误阻断（实为 {rc}）: {out[-200:]}"

        # ③ 有未处置 fatal → EXIT=6；畸形 state 不得让 fatal 漏报
        led_p.write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            "H-99,fatal,closed," + (datetime.now().strftime("%Y-%m-%d")) + ",证伪\n",
            encoding="utf-8")
        rc, out = run("--check-disposition")
        assert rc == 6, f"有未处置 fatal 时应 EXIT=6，实为 {rc}"
        st_p.write_text("[1,2,3]\n", encoding="utf-8")
        rc, out = run()
        assert rc == 5, f"畸形 state 下 fatal 不得漏报（应 EXIT=5 REVIEW_REQUIRED），实为 {rc}"
        assert "H-99" in out, "畸形 state 下 fatal finding 必须被报出"

        # R4.3（盲检🔴2）：closed_date 带小数秒（ISO 变体）不得让 severe 闭环漏报。
        # 假说池更新设早一日，闭环设今日+小数秒 → 应判 late_fatal → EXIT=5。
        st_p.unlink(missing_ok=True)
        hyp_p.write_text(json.dumps({
            "last_updated": "2026-11-18T00:00:00+08:00",
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        led_p.write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            "F-R43,severe,closed,2026-11-19T10:30:00.123456+08:00,小数秒闭环\n",
            encoding="utf-8")
        rc, out = run()
        assert rc == 5 and "F-R43" in out, \
            f"小数秒 severe 闭环须判 REVIEW_REQUIRED/EXIT=5，实为 rc={rc}: {out[-300:]}"

        # R4.3（盲检🔴3）：active_hypotheses 元素为非 dict（如 int 5）时，原
        # `(h or {})` 返回该 int → `k not in 5` 抛 TypeError → 未捕获 traceback
        # EXIT=1（契约仅 0/3/5/6）。须只告警不崩。
        hyp_p.write_text(json.dumps({
            "last_updated": "2026-11-18T00:00:00+08:00",
            "active_hypotheses": [5]}) + "\n", encoding="utf-8")
        rc, out = run()
        assert "Traceback" not in out, f"非 dict 假说条目不得抛未捕获异常: {out[-300:]}"
        assert rc in (0, 3, 5, 6), f"非 dict 假说条目退出码越界: {rc}"

        # R4.12（盲检 A🔴1）：UTF-16BE 无 BOM 台账的 NUL 在 UTF-8 下是合法
        # 字节，裸 open(utf-8-sig) 吞入后列名含 NUL → finding_id 取不到 →
        # fatal 证伪被静默忽略（CLEAN/EXIT=0，fail-open）。须严格读 → EXIT=3。
        hyp_p.write_text(json.dumps({
            "last_updated": "2026-11-18T00:00:00+08:00",
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        led_p.write_bytes(
            ("finding_id,severity,status,closed_date,finding_summary\n"
             "F-R412,fatal,closed,2026-11-19T10:30:00+08:00,证伪\n").encode("utf-16-be"))
        rc, out = run()
        assert rc == 3, f"无 BOM UTF-16 台账须严格读 EXIT=3（不得 CLEAN 放行），实为 {rc}: {out[-200:]}"
        assert "Traceback" not in out, f"UTF-16 台账不得抛未捕获异常: {out[-200:]}"

        # R4.13（盲检 B🔴2）：future last_updated + 同日带毫秒 closed fatal，
        # 原 `cd > hyp_updated` 严格比较相等即判「不晚于」→ CLEAN/EXIT=0
        # （fatal 证伪静默吞）。须按「同日即算晚于」保守判 EXIT=5。
        future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000000+08:00")
        hyp_p.write_text(json.dumps({
            "last_updated": future,
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        led_p.write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            f"F-R413,fatal,closed,{future},未来同日证伪\n", encoding="utf-8")
        rc, out = run()
        assert rc == 5 and "F-R413" in out, \
            f"未来同日 fatal 须 REVIEW_REQUIRED/EXIT=5，实为 rc={rc}: {out[-200:]}"

        # R4.15（盲检 A🔴6）：ZWJ(Cf) 附在 severity 'fatal‍' 末尾——_row_str
        # 只 strip（ZWJ 非空白），精确比较失配 → fatal 证伪静默 CLEAN。
        # has_forbidden 现拒字母侧 ZWJ → 严格读 EXIT=3（证据源污染）。
        today = datetime.now().strftime("%Y-%m-%d")
        hyp_p.write_text(json.dumps({
            "last_updated": today,
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        led_p.write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            f"F-R415,fatal\u200d,closed,{today},ZWJ证伪\n", encoding="utf-8")
        rc, out = run()
        assert rc == 3, f"severity ZWJ 污染须 EXIT=3（不得 CLEAN），实为 rc={rc}: {out[-200:]}"

        # R4.19（盲检 B🔴7）：severity 非 ASCII 字母同形（fatαl/fataл）NFKC
        # 不收敛 → norm≠fatal → 漏报。须保守计入 late_fatal EXIT=5；合法
        # fatal 同结构对照仍 EXIT=5（不得因扩展检测而漏）。
        hyp_p.write_text(json.dumps({
            "last_updated": today,
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}),
            encoding="utf-8")
        for label, sev in (("Greek", "fat\u03b1l"), ("Cyrillic", "fata\u043b")):
            led_p.write_text(
                "finding_id,severity,status,closed_date,finding_summary\n"
                f"F-R419-{label},{sev},closed,{today},同形证伪\n", encoding="utf-8")
            rc, out = run()
            assert rc == 5, f"R4.19 severity {label} 同形须 REVIEW_REQUIRED EXIT=5，实为 {rc}"


    # R4.20（盲检 A🔴5 / A🔴6）：ZWSP waiver 空口放行、核验记录写完后
    # 再改写 artifact 的时序篡改，均须 G4 FAIL。
    with tempfile.TemporaryDirectory(prefix="g4_r420_") as td:
        d = Path(td)
        (d / "T-FUZZ__phylo-analyst.md").write_text("n = 777\n", encoding="utf-8")
        oc = {"artifact_mtimes": {}, "gate_mode": "block", "verdict": "DEGRADE",
              "unverified": [{"member": "phylo-analyst", "kind": "n_eq", "value": "777"}]}
        (d / "T-FUZZ__output-check.json").write_text(json.dumps(oc), encoding="utf-8")
        (d / "T-FUZZ__waivers.json").write_text(json.dumps({"waivers": [
            {"gate": "G2", "value": "777", "reason": "\u200b",
             "authorized_by": "lead"}]}), encoding="utf-8")
        (d / "T-FUZZ__checklist.json").write_text(json.dumps(PASS_CHECKLIST), encoding="utf-8")
        cg = PKG / "scripts" / "check_gates.py"
        r = subprocess.run([sys.executable, str(cg), str(d), "T-FUZZ"],
                           capture_output=True, text=True)
        assert r.returncode == 5, "R4.20 ZWSP waiver 不得放行 G2/G4"
        # 合法明文理由对照：waiver 生效，整体可 PASS
        (d / "T-FUZZ__waivers.json").write_text(json.dumps({"waivers": [
            {"gate": "G2", "value": "777", "reason": "已核对权威源 URL",
             "authorized_by": "lead"}]}), encoding="utf-8")
        r = subprocess.run([sys.executable, str(cg), str(d), "T-FUZZ"],
                           capture_output=True, text=True)
        rep = json.loads((d / "T-FUZZ__gates.json").read_text(encoding="utf-8"))
        g4 = next(g for g in rep["gates"] if str(g["gate"]).startswith("G4"))
        assert g4["ok"] is True, "R4.20 明文理由 waiver 应解除 G4 阻断"
        # 时序篡改：核验记录写完后 artifact 又被改（无指纹映射也须捕获）
        (d / "T-FUZZ__waivers.json").write_text("null\n", encoding="utf-8")
        (d / "T-FUZZ__output-check.json").write_text(
            json.dumps({"artifact_mtimes": {}, "gate_mode": "block",
                        "verdict": "PASS"}), encoding="utf-8")
        (d / "T-FUZZ__phylo-analyst.md").write_text("n = 777\n改动\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(cg), str(d), "T-FUZZ"],
                           capture_output=True, text=True)
        rep = json.loads((d / "T-FUZZ__gates.json").read_text(encoding="utf-8"))
        g4 = next(g for g in rep["gates"] if str(g["gate"]).startswith("G4"))
        assert g4["ok"] is False, "R4.20 核验后时序篡改须 G4 FAIL"

    # R4.21（盲检 B🔴7/B🔴8）：G5 消费侧自洽 + G4 ts 内容锚互证。
    with tempfile.TemporaryDirectory(prefix="r421_gate_") as td:
        d = Path(td); (d / "sources").mkdir()
        (d / "sources" / "truth.csv").write_text("90\n1\n", encoding="utf-8")
        art = d / "T-FUZZ__phylo-analyst.md"
        art.write_text(json.dumps(BASE_ENV) + "\n", encoding="utf-8")
        (d / "T-FUZZ__waivers.json").write_text("null\n", encoding="utf-8")
        (d / "T-FUZZ__output-check.json").write_text(
            json.dumps({"artifact_mtimes": {}}), encoding="utf-8")
        def g5rc(ocl):
            (d / "T-FUZZ__checklist.json").write_text(json.dumps(ocl), encoding="utf-8")
            return subprocess.run([sys.executable, str(CHECK_GATES), str(d), TASK_ID,
                                   "--sources", str(d / "sources")],
                                  capture_output=True, text=True).returncode
        assert g5rc({"ts": "2026-11-27T00:00:00", "task_id": TASK_ID,
                     "items_total": 4, "items_passed": 4, "sources_checked": 1,
                     "hallucinated": 0, "verdict": "PASS"}) == 0, "R4.21 合规 checklist 须 EXIT=0"
        assert g5rc({"ts": "2026-11-27T00:00:00", "task_id": TASK_ID,
                     "items_total": 1, "items_passed": 0, "sources_checked": 1,
                     "hallucinated": 99, "verdict": "PASS"}) == 5, "R4.21 不自洽 checklist 须 EXIT=5"


def test_tc3_timezone_canonicalize() -> None:
    """R2（2026-11-15 · T-C3）：parse_dt 必须 canonicalize 带偏移输入到 +08:00，
    不得静默丢弃偏移量。旧实现 dt.replace(tzinfo=None) 对 Z/+0000/-05:00 丢 8h，
    导致 late_fatal 漏报、age_days 偏差。两层断言：

      ① 单元层：parse_dt 对四种时区输入产出确定的 +08 naive 时间；
      ② 端到端：构造 `last_updated=+08 23:00` + `closed_date=Z 16:00`
         （=次日 00:00 +08）场景——旧实现把 closed_date 的 UTC 16:00 误当
         naive 16:00（vs 池 23:00）判「早于」→ 漏报 late_fatal（EXIT=0）；
         修复后 canonicalize 到 +08 判次日 00:00 > 23:00 → 必报 REVIEW_REQUIRED(5)。
    """
    hw_path = PKG / "scripts" / "hypothesis_watch.py"
    spec = importlib.util.spec_from_file_location("_hw_tc3", hw_path)
    assert spec is not None and spec.loader is not None, "hypothesis_watch 无法加载"
    hw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hw)
    from datetime import datetime as _dt

    # ① 单元层：带偏移输入 → 确定的 +08 naive（不再依赖系统本地时区）
    assert hw.parse_dt("2026-11-10T04:00:00Z") == _dt(2026, 11, 10, 12, 0, 0), \
        "Z(UTC 04:00) 须 canonicalize 为 +08 12:00（旧实现误为 04:00）"
    assert hw.parse_dt("2026-11-10T04:00:00+0000") == _dt(2026, 11, 10, 12, 0, 0), \
        "+0000 须 canonicalize 为 +08 12:00"
    assert hw.parse_dt("2026-11-10T07:00:00-05:00") == _dt(2026, 11, 10, 20, 0, 0), \
        "-05:00(07:00) 须 canonicalize 为 +08 20:00（旧实现误为 07:00）"
    assert hw.parse_dt("2026-11-10T12:00:00+08:00") == _dt(2026, 11, 10, 12, 0, 0), \
        "+08:00 输入须保持不变"
    assert hw.parse_dt("2026-11-10") == _dt(2026, 11, 10, 0, 0, 0), \
        "纯日期 → 午夜 naive"
    assert hw.parse_dt(123) is None and hw.parse_dt("garbage") is None, \
        "非字符串/坏串 → None（不崩、不静默）"

    # ② 端到端：旧实现 EXIT=0（漏报），修复后必须 EXIT=5
    with tempfile.TemporaryDirectory(prefix="tc3_tz_") as td:
        d = Path(td)
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "last_updated": "2026-11-10T23:00:00+08:00",
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "c"}]}) + "\n",
            encoding="utf-8")
        (ro / "00_governance" / "redteam_ledger.csv").write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            "H-99,fatal,closed,2026-11-10T16:00:00Z,证伪晚于假说池更新\n",
            encoding="utf-8")
        p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro)],
                           capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"hypothesis_watch 崩溃: {out[:300]}"
        assert p.returncode == 5, \
            f"T-C3 修复后须报 late_fatal(EXIT=5)，实为 {p.returncode}（漏报回归！）"
        assert "H-99" in out, "late_fatal finding 必须被报出"

    # ── R2 回补回归集合（③④⑤⑥）──────────────────────────────────────
    # 刻意复用本函数而非新增行为级函数：不动 CURRENT_BASELINE 机器锚
    # （45 CASES + 16 行为级 = 61）与守卫第 11 项的计数相等校验——
    # 历史 v1.5.10/11/12 三次因计数联动返工，此处保持计数不变。
    import os as _os
    from datetime import timedelta as _td

    # ③ 跨 TZ 裁决一致性（🔴-1）。以 now_canonical() 动态构造边界时间戳，
    #    使「回退到 datetime.now()」时 +08 侧 age_days=15 / UTC 侧=14 → 裁决翻转；
    #    修复后两侧同基准，必须同判 5。动态基准避免时间炸弹。
    with tempfile.TemporaryDirectory(prefix="tc3_env_") as td:
        d = Path(td)
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        boundary = (hw.now_canonical() - _td(days=15, hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "last_updated": boundary + "+08:00", "active_hypotheses": []}) + "\n",
            encoding="utf-8")
        (ro / "00_governance" / "redteam_ledger.csv").write_text(
            "finding_id,severity,status,closed_date,finding_summary\n", encoding="utf-8")
        rcs = []
        for tz in ("Asia/Shanghai", "UTC"):
            p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro)],
                               capture_output=True, text=True, timeout=60,
                               env=dict(_os.environ, TZ=tz))
            assert "Traceback" not in (p.stdout + p.stderr), f"{tz} 下 hypothesis_watch 崩溃"
            rcs.append((tz, p.returncode))
        assert [c for _, c in rcs] == [5, 5], \
            f"跨 TZ 裁决翻转（回退前 +08=5 / UTC=0）: {rcs}"

    # ④ naive ISO 不得静默吞掉证伪发现（🔴-2）
    assert hw.parse_dt("2026-11-10T12:00:00") == _dt(2026, 11, 10, 12, 0, 0), \
        "无偏移 ISO datetime 须按 +08 naive 解析"
    assert hw.parse_dt("2026-11-10 12:00:00") == _dt(2026, 11, 10, 12, 0, 0), \
        "空格分隔 datetime 须按 +08 naive 解析"
    with tempfile.TemporaryDirectory(prefix="tc3_naive_") as td:
        d = Path(td)
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        fresh = (hw.now_canonical() - _td(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "last_updated": fresh + "+08:00", "active_hypotheses": []}) + "\n",
            encoding="utf-8")
        closed = (hw.now_canonical() - _td(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        (ro / "00_governance" / "redteam_ledger.csv").write_text(
            "finding_id,severity,status,closed_date,finding_summary\n"
            f"H-77,fatal,closed,{closed},naive-iso-证伪发现\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro)],
                           capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"naive ISO 场景崩溃: {out[:300]}"
        assert p.returncode == 5 and "H-77" in out, \
            f"naive ISO closed_date 被静默吞掉（EXIT={p.returncode}）"

    # ⑤ render_context_stack 畸形 JSON 须走契约码 3，不得 traceback（🔴-3）
    with tempfile.TemporaryDirectory(prefix="tc3_render_") as td:
        d = Path(td)
        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(
            "[]\n", encoding="utf-8")
        render = PKG / "scripts" / "render_context_stack.py"
        p = subprocess.run([sys.executable, str(render), "--research-ops", str(ro),
                            "--which", "hyp"], capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"畸形 JSON 仍触发 traceback: {out[:300]}"
        assert p.returncode == 3, f"畸形 JSON 须 EXIT=3，实为 {p.returncode}"

    # ⑥ gen_integrity_manifest --help 只读，不得刷新 generated 写盘（🟠-1）
    gen = PKG / "scripts" / "gen_integrity_manifest.py"
    manifest = PKG / "integrity_manifest.json"
    before = manifest.read_bytes()
    p = subprocess.run([sys.executable, str(gen), "--help"],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "usage" in p.stdout.lower(), \
        f"--help 须打印帮助且 EXIT=0: {p.returncode} {p.stdout[:200]}"
    assert manifest.read_bytes() == before, "--help 不得写盘（否则可静默洗白基线）"

    # ── R3 回补回归集合（⑦⑧⑨，2026-11-17）──────────────────────────
    # 同策略：复用本函数追加断言，不动机器锚计数。
    import re as _re2

    # ⑦ F1：audit_decision_log naive 台账跨 TZ 裁决一致性。
    #    回退形态：parse_ts 裸 astimezone() + now().astimezone() → UTC 判 13 天
    #    HEALTHY/0、Shanghai 判 14 天 STALE/6。修复后三环境同 EXIT 同 age。
    #    动态构造：ts=now-16d+8h 的 naive 串（age 恰在 13 阈值之上的边界区）。
    adl_path = PKG / "scripts" / "audit_decision_log.py"
    adl_spec = importlib.util.spec_from_file_location("_adl_r3", adl_path)
    adl = importlib.util.module_from_spec(adl_spec)
    adl_spec.loader.exec_module(adl)
    ts_naive = (adl.now_canonical() - _td(days=16, hours=-8)).strftime("%Y-%m-%dT%H:%M:%S")
    with tempfile.TemporaryDirectory(prefix="r3_f1_") as td:
        d = Path(td)
        (d / "decision_log.csv").write_text(
            "ts,actor,decision_type,decision,rationale,tier\n"
            f"{ts_naive},tester,route,approve,r3-f1-regression,通知档\n", encoding="utf-8")
        rcs = []
        for tz in ("UTC", "Asia/Shanghai"):
            p = subprocess.run([sys.executable, str(adl_path), str(d / "decision_log.csv"),
                                "--max-age-days", "13", "--json"],
                               capture_output=True, text=True, timeout=60,
                               env=dict(_os.environ, TZ=tz))
            rep = json.loads(p.stdout)
            rcs.append((tz, p.returncode, rep["age_days"], rep["verdict"]))
        assert len({(c, a) for _, c, a, _ in rcs}) == 1, f"跨 TZ 裁决翻转: {rcs}"
        # age=16±1（now-16d+8h 的 naive 串，跨日边界 ±1 属正常），核心断言=跨 TZ 一致 + STALE
        assert rcs[0][3] == "STALE" and 15 <= rcs[0][2] <= 17, f"动态基准偏移: {rcs}"

    # ⑧ F2：task_id 白名单——六脚本对 ../ 形态一律参数错误码，不产生越界文件。
    with tempfile.TemporaryDirectory(prefix="r3_f2_") as td:
        d = Path(td)
        rd = d / "rd"
        rd.mkdir()
        (d.parent / "probe_marker").touch() if False else None
        evil_dir = d / "escape"
        evil_dir.mkdir()
        probes = [  # (脚本, 参数样式, 期望 rc)
            ("check_gates.py", 2, 2), ("verify_member_output.py", 2, 2),
            ("poll_run_dir.py", 5, 5), ("write_checklist.py", 2, 2),
            ("log_spawn.py", 2, 2),
        ]
        for script, _, want_rc in probes:
            sp = PKG / "scripts" / script
            p = subprocess.run([sys.executable, str(sp), str(rd), "../escape"],
                               capture_output=True, text=True, timeout=60)
            out = p.stdout + p.stderr
            assert "Traceback" not in out, f"{script} 对恶意 task_id 崩溃: {out[:200]}"
            assert p.returncode == want_rc, \
                f"{script} 须拒收 ../escape（期望 {want_rc}），实为 {p.returncode}"
        # 无越界文件落在 rd 与 escape 目录
        assert not list(rd.iterdir()), "rd 被越界写入"
        assert not list(evil_dir.iterdir()), "escape 目录被越界写入"

    # ⑨ B-3：gen_integrity_manifest --check 对损坏清单走 EXIT=3，零 traceback。
    gen_manifest = PKG / "integrity_manifest.json"
    m_bak = gen_manifest.read_bytes()
    try:
        gen_manifest.write_bytes(b"{ broken")
        p = subprocess.run([sys.executable, str(gen), "--check"],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 3 and "Traceback" not in p.stderr, \
            f"损坏清单须 EXIT=3 无 traceback，实为 rc={p.returncode}"
    finally:
        gen_manifest.write_bytes(m_bak)

    # ⑩ R3.1（2026-11-17 盲检回补）：非 UTF-8 输入三入口须走契约码，零 traceback。
    #    同根因（UnicodeDecodeError 未入捕获面）三实例：check_gates sidecar /
    #    hypothesis_watch 台账 / assemble_spawn_prompt --task-file。
    with tempfile.TemporaryDirectory(prefix="r3_uni_") as td:
        d = Path(td)
        rd = d / "rd"
        rd.mkdir()
        (rd / "T-S__m.md").write_text("artifact\n", encoding="utf-8")
        (rd / "T-S__workflow.json").write_bytes(b"\x00\xff binary sidecar")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "check_gates.py"),
                            str(rd), "T-S"], capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"check_gates 二进制 sidecar 崩溃: {out[:200]}"
        assert p.returncode in (0, 3, 5), f"check_gates 须走契约码，实为 {p.returncode}"
        assert (rd / "T-S__gates.json").is_file(), "G1 起点崩溃导致 gates.json 未落盘"

        ro = d / "ro"
        (ro / "context_stack").mkdir(parents=True)
        (ro / "00_governance").mkdir(parents=True)
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text(
            '{"last_updated":"2026-11-16","active_hypotheses":[]}\n', encoding="utf-8")
        (ro / "00_governance" / "redteam_ledger.csv").write_bytes(b"\x00\xff binary ledger")
        p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro)],
                           capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"hypothesis_watch 二进制台账崩溃: {out[:200]}"
        assert p.returncode == 3, f"证据源畸形须 EXIT=3，实为 {p.returncode}"

        bad_tf = d / "bad_task.md"
        bad_tf.write_bytes(b"\x00\xff binary task")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                            "--member", "literature-scout", "--task-file", str(bad_tf)],
                           capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"assemble 二进制任务包崩溃: {out[:200]}"
        assert p.returncode == 3, f"任务包无效须 EXIT=3，实为 {p.returncode}"

        # ⑪ R3.2（2026-11-17 第二轮盲检回补）：JSON 池/处置台账/成员 MD/plugin.json/
        # team-contract 五个裸读点——UnicodeDecodeError 须转契约码，零 traceback。
        import shutil as _shutil
        bad_bin = d / "bad.bin"
        bad_bin.write_bytes(b"\x00\xff binary")

        # a) hypothesis_watch JSON 池（load_json_obj 通道）
        ro2 = d / "ro2"
        (ro2 / "context_stack").mkdir(parents=True)
        (ro2 / "00_governance").mkdir(parents=True)
        (ro2 / "00_governance" / "redteam_ledger.csv").write_text("x\n", encoding="utf-8")
        _shutil.copyfile(bad_bin, ro2 / "context_stack" / "confirmed_hypotheses.json")
        p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro2)],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "hw 假说池二进制崩溃"
        assert p.returncode == 3, f"假说池非 UTF-8 须 EXIT=3，实为 {p.returncode}"

        # b) hypothesis_watch state（load_json_obj 通道二）
        (ro2 / "context_stack" / "confirmed_hypotheses.json").write_text(
            '{"last_updated":"2026-11-16","active_hypotheses":[]}\n', encoding="utf-8")
        _shutil.copyfile(bad_bin, ro2 / "00_governance" / "hypothesis_watch_state.json")
        p = subprocess.run([sys.executable, str(hw_path), "--research-ops", str(ro2)],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "hw state 二进制崩溃"
        assert p.returncode in (0, 5, 6), f"state 畸形须保守契约码，实为 {p.returncode}"

        # c/d/e) assemble：成员 MD / plugin.json / team-contract
        y = d / "expert"
        (y / ".codebuddy-plugin").mkdir(parents=True)
        (y / "agents").mkdir()
        (y / "skills/viral-evo-core/references").mkdir(parents=True)
        (y / ".codebuddy-plugin" / "plugin.json").write_text(
            '{"teamInfo":{"memberAgents":["phylo-analyst"]}}', encoding="utf-8")
        _shutil.copyfile(bad_bin, y / "agents" / "phylo-analyst.md")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                            "--member", "phylo-analyst", "--expert-dir", str(y)],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "assemble 成员 MD 二进制崩溃"
        assert p.returncode == 3, f"成员 MD 非 UTF-8 须 EXIT=3，实为 {p.returncode}"

        (y / "agents" / "phylo-analyst.md").write_text("# m\n", encoding="utf-8")
        _shutil.copyfile(bad_bin, y / ".codebuddy-plugin" / "plugin.json")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                            "--member", "phylo-analyst", "--expert-dir", str(y)],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "assemble plugin.json 二进制崩溃"
        assert p.returncode == 3, f"plugin.json 非 UTF-8 须 EXIT=3，实为 {p.returncode}"

        (y / ".codebuddy-plugin" / "plugin.json").write_text(
            '{"teamInfo":{"memberAgents":["phylo-analyst"]}}', encoding="utf-8")
        _shutil.copyfile(bad_bin, y / "skills/viral-evo-core/references/team-contract.md")
        task_ok = d / "ok_task.md"
        task_ok.write_text("# 任务\n内容\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                            "--member", "phylo-analyst", "--expert-dir", str(y),
                            "--task-file", str(task_ok)],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "assemble team-contract 二进制崩溃"
        assert p.returncode == 0, f"契约非 UTF-8 应降级不阻断，实为 {p.returncode}"

        # ⑫ R4（2026-11-18 backlog 回补）：组合死锁解除 + member 白名单。
        # a) task_id 含元后缀子串（x__gates）不再误杀成员 artifact（LEAD_SUFFIXES 尾匹配）
        rd2 = d / "rd2"
        rd2.mkdir()
        (rd2 / "x__gates__phylo-analyst.md").write_text("artifact\n", encoding="utf-8")
        (rd2 / "x__gates__checklist.md").write_text("meta\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "check_gates.py"),
                            str(rd2), "x__gates"], capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert "Traceback" not in out, "check_gates 组合 task_id 崩溃"
        assert "1 份 artifact" in out, f"成员 artifact 被元后缀子串误杀（组合死锁复发）: {out[:200]}"
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "verify_member_output.py"),
                            str(rd2), "x__gates"], capture_output=True, text=True, timeout=60)
        assert p.returncode != 3, "vmo 组合死锁复发（artifact 未找到）"

        # b) log_spawn member 白名单（生产端闭合）
        rd3 = d / "rd3"
        rd3.mkdir()
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "log_spawn.py"),
                            str(rd3), "T-F", "../evil", "at-1"],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 2 and "Traceback" not in (p.stdout + p.stderr),             f"log_spawn member ../evil 须 EXIT=2，实为 {p.returncode}"
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "log_spawn.py"),
                            str(rd3), "T-F", "phylo-analyst", "at-1"],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "log_spawn 合法 member 崩溃"
        assert (rd3 / "spawn_manifest.jsonl").is_file(), "合法 member 未落 manifest"


def test_gate_mode_blocks() -> None:
    """L3（2026-11-09）：gate_mode 行为回归——阻断信号必须传导。

    gate_mode=block + verdict=DEGRADE → G4 FAIL；
    gate_mode=warn + verdict=DEGRADE → G4 不因阻断信号而 FAIL（向后兼容）；
    gate_mode=block + verdict=PASS → G4 PASS。
    """
    with tempfile.TemporaryDirectory(prefix="gate_mode_") as td:
        d = Path(td)
        run = d / "run"
        run.mkdir()
        src = d / "src"
        src.mkdir()
        (src / "truth.csv").write_text("90\n1\n", encoding="utf-8")
        art = run / f"{TASK_ID}__phylo-analyst.md"
        art.write_text(json.dumps(BASE_ENV) + "\n", encoding="utf-8")
        (run / f"{TASK_ID}__checklist.json").write_text(
            json.dumps(PASS_CHECKLIST, ensure_ascii=False) + "\n", encoding="utf-8")

        def g4_ok(gate_mode: str, verdict: str) -> bool:
            (run / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "ts": "2026-11-09T00:00:00", "task_id": TASK_ID,
                "checked_artifacts": [art.name], "artifact_mtimes": {},
                "unverified": [], "verdict": verdict, "gate_mode": gate_mode,
                "sources_used": [str(src)]}, ensure_ascii=False) + "\n", encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(run), TASK_ID, "--sources", str(src)],
                capture_output=True, text=True, timeout=60)
            return _read_gates(run).get("G4", False)

        assert g4_ok("block", "DEGRADE") is False, "阻断态 DEGRADE 必须判 FAIL"
        assert g4_ok("block", "PASS") is True, "阻断态 PASS 应判 PASS"
        assert g4_ok("warn", "DEGRADE") is True, "warn 态不因阻断信号判 FAIL（向后兼容）"

        # R4.1（backlog A）：[待人工核验] 标注必须绑定所属成员，禁止跨成员洗白。
        with tempfile.TemporaryDirectory(prefix="manual_mark_") as td2:
            rd = Path(td2)
            src2 = rd / "src"
            src2.mkdir()
            (src2 / "truth.csv").write_text("123456\n", encoding="utf-8")  # 不含 777777
            env_s = json.dumps(BASE_ENV) + "\n"
            (rd / f"{TASK_ID}__alice.md").write_text(
                env_s + "样本 n=777777 [待人工核验]\n", encoding="utf-8")
            (rd / f"{TASK_ID}__bob.md").write_text(
                env_s + "样本 n=777777\n", encoding="utf-8")  # 同数字，未标注
            # 场景①：bob 的未溯源数字（仅 alice 标注）→ G2 必须 FAIL
            (rd / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "task_id": TASK_ID, "artifact_mtimes": {},
                "unverified": [{"member": "bob", "kind": "n_eq", "value": "777777"}],
                "verdict": "DEGRADE", "gate_mode": "block"}, ensure_ascii=False),
                encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(rd), TASK_ID, "--sources", str(src2)],
                capture_output=True, text=True, timeout=60)
            g2 = _read_gates(rd).get("G2", False)
            g4 = _read_gates(rd).get("G4", False)
            assert g2 is False and g4 is False, \
                "跨成员标注串味：alice 的标注不得洗白 bob 未标注的同数字（G2/G4 须 FAIL）"
            # 场景②：数字所属成员自己标注（alice）→ 可放行，证明不是一刀切全 FAIL
            (rd / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "task_id": TASK_ID, "artifact_mtimes": {},
                "unverified": [{"member": "alice", "kind": "n_eq", "value": "777777"}],
                "verdict": "DEGRADE", "gate_mode": "block"}, ensure_ascii=False),
                encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(rd), TASK_ID, "--sources", str(src2)],
                capture_output=True, text=True, timeout=60)
            assert _read_gates(rd).get("G4", False) is True, \
                "成员标注自己的数字应放行（G4 PASS），防止修成全 FAIL 误伤"

            # R4.2（盲检🔴2）：endswith 后缀匹配会被 T__foo__alice.md 命中，
            # 使多段前缀副产物的标注洗白 T__alice.md 的数字。精确匹配后须 G4 FAIL。
            (rd / f"{TASK_ID}__alice.md").write_text(
                env_s + "样本 n=777777\n", encoding="utf-8")  # alice 自己未标注
            (rd / f"{TASK_ID}__foo__alice.md").write_text(
                env_s + "777777 [待人工核验]\n", encoding="utf-8")  # 副产物标注
            (rd / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "task_id": TASK_ID, "artifact_mtimes": {},
                "unverified": [{"member": "alice", "kind": "n_eq", "value": "777777"}],
                "verdict": "DEGRADE", "gate_mode": "block"}, ensure_ascii=False),
                encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(rd), TASK_ID, "--sources", str(src2)],
                capture_output=True, text=True, timeout=60)
            assert _read_gates(rd).get("G4", False) is False, \
                "多段前缀副产物（T__foo__alice.md）的标注不得洗白 alice 的数字"

            # R4.3（盲检🔴6）：部分标注不得解除整段阻断——与 waivers 路径
            # 「部分放行不解除阻断」同纪律。2 项未溯源只标 1 项 → G4 须 FAIL。
            (rd / f"{TASK_ID}__alice.md").write_text(
                env_s + "样本 n=777777 [待人工核验]；另 n=888888 未标注\n", encoding="utf-8")
            (rd / f"{TASK_ID}__foo__alice.md").unlink(missing_ok=True)
            (rd / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "task_id": TASK_ID, "artifact_mtimes": {},
                "unverified": [{"member": "alice", "kind": "n_eq", "value": "777777"},
                               {"member": "alice", "kind": "n_eq", "value": "888888"}],
                "verdict": "DEGRADE", "gate_mode": "block"}, ensure_ascii=False),
                encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(rd), TASK_ID, "--sources", str(src2)],
                capture_output=True, text=True, timeout=60)
            assert _read_gates(rd).get("G4", False) is False, \
                "2 项未溯源仅标 1 项属部分标注，不得解除 G4 阻断"

            # R4.3（盲检🔴2）：邻近标注洗白——"n=111 及 n=222 [待人工核验]" 中，
            # 原 marker_pat 允许间隔内含其他数字（finditer 非重叠消费），222 的
            # 标注被归给未标注的 111 → G2/G4 误判 PASS。标注只归属紧邻其前者。
            (rd / f"{TASK_ID}__alice.md").write_text(
                env_s + "n=111 及 n=222 [待人工核验]\n", encoding="utf-8")
            (rd / f"{TASK_ID}__bob.md").unlink(missing_ok=True)
            (rd / f"{TASK_ID}__output-check.json").write_text(json.dumps({
                "task_id": TASK_ID, "artifact_mtimes": {},
                "unverified": [{"member": "alice", "kind": "n_eq", "value": "111"}],
                "verdict": "DEGRADE", "gate_mode": "block"}, ensure_ascii=False),
                encoding="utf-8")
            subprocess.run(
                [sys.executable, str(CHECK_GATES), str(rd), TASK_ID, "--sources", str(src2)],
                capture_output=True, text=True, timeout=60)
            assert _read_gates(rd).get("G2", False) is False, \
                "邻近标注（另一个数字的）不得洗白未标注数字（G2 须 FAIL）"
            assert _read_gates(rd).get("G4", False) is False, \
                "邻近标注（另一个数字的）不得解除 G4 阻断"


def test_require_tag_gate() -> None:
    """C3（2026-11-08）：产出端 require_tag 闸行为级守卫——未标记源必须被拒。

    同一份含数字的 artifact 分别喂「未打 source_tag」与「已打 source_tag」的
    权威源：--require-tag 开启后前者 DEGRADE(5)、后者 PASS(0)；关闭开关时
    未标记源仍可载入（向后兼容，防存量任务被误杀）。
    """
    with tempfile.TemporaryDirectory(prefix="tag_gate_") as td:
        d = Path(td)
        art = d / "out.md"
        art.write_text("样本量 n=1234。\n", encoding="utf-8")
        src = d / "sources"
        src.mkdir()
        untagged = src / "raw.csv"
        untagged.write_text("1234\n", encoding="utf-8")
        tagged = src / "tagged.csv"
        tagged.write_text("# source_tag: authoritative\n1234\n", encoding="utf-8")
        vn = PKG / "scripts" / "verify_numbers.py"

        def run(flag: bool, source: Path) -> int:
            cmd = [sys.executable, str(vn), str(art), "--sources", str(source)]
            if flag:
                cmd.append("--require-tag")
            return subprocess.run(cmd, capture_output=True, text=True, timeout=60).returncode

        assert run(True, untagged) == 5, "未标记源在 --require-tag 下必须被拒（DEGRADE）"
        assert run(True, tagged) == 0, "已标记源在 --require-tag 下应放行（PASS）"
        assert run(False, untagged) == 0, "默认关闭开关时须向后兼容"

        # R4.1（backlog D）：UTF-16/畸形编码产出必须 fail-closed（契约码 3），
        # 禁止 errors="ignore" 吞字节造成「PASS checked=0」误放行（fail-open）。
        bad = d / "utf16.md"
        bad.write_bytes(b"\xff\xfe" + "样本 n=7777 。\n".encode("utf-16-le"))
        rc = subprocess.run([sys.executable, str(vn), str(bad), "--sources", str(src)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"UTF-16 产出须不可解码 EXIT=3（不得吞字节误放行），实为 {rc}"

        # R4.1（backlog C）：超长 task_id 拼路径不得触发 OSError traceback（EXIT=1）；
        # 六脚本白名单加长度上限后须统一走参数非法码（2）。
        wc = PKG / "scripts" / "write_checklist.py"
        long_id = "T-" + "a" * 5000
        p = subprocess.run([sys.executable, str(wc), str(d), long_id,
                            "--items", "3", "--passed", "3"],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), \
            "超长 task_id 不得抛未捕获 OSError traceback"
        assert p.returncode in (2, 5), \
            f"超长 task_id 应走参数非法码（2），实为 {p.returncode}"

        # R4.2（盲检🔴1）：无 BOM 的 UTF-16（NUL 交错在 UTF-8 下合法）不得
        # 被当空文本误判 PASS——必须显式检测 NUL → EXIT=3（fail-closed）。
        nb = d / "utf16_nobom.md"
        nb.write_bytes("p = 0.999\nn = 888\n".encode("utf-16-be"))  # 无 BOM
        (d / "s2").mkdir(exist_ok=True)
        (d / "s2" / "a.csv").write_text("p,0.111\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(nb), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"无 BOM UTF-16 产出须 NUL 检测 → EXIT=3，实为 {rc}"

        # R4.2（主代理对抗实证）：非 NUL 的 C0 控制字符（U+0001）交错在数字旁
        # 会让正则静默失配 → checked=0 → PASS fail-open。须一并检测 → EXIT=3。
        c0 = d / "c0_inject.md"
        c0.write_bytes(b"n\x01=\x01888\n")
        rc = subprocess.run([sys.executable, str(vn), str(c0), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"C0 控制字符交错产出须 EXIT=3（非 PASS），实为 {rc}"

        # R4.3（盲检🟠）：合法 emoji ZWJ 序列（U+200D 两侧皆 emoji）不得被 Cf
        # 一刀切误拒（fail-close 误伤），但 ZWJ/ZWSP 夹数字仍须 EXIT=3（fail-open）。
        emo = d / "emoji_ok.md"
        emo.write_text("家族 👨\u200d👩\u200d👧 样本量 n=888。\n", encoding="utf-8")
        pemo = subprocess.run([sys.executable, str(vn), str(emo), "--sources", str(d / "s2")],
                              capture_output=True, text=True, timeout=60)
        rc = pemo.returncode
        # 关键是不得被当成不可解码污染（EXIT=3）；数字核验结果 0/5 取决于
        # 888 是否在源中，本 fixture 源不含 888 → 正常为 5（未溯源），非误拒。
        assert rc != 3, f"合法 emoji ZWJ 产出不得误拒为不可解码 EXIT=3，实为 {rc}"
        zwjnum = d / "zwj_num.md"
        zwjnum.write_text("n=8\u200d88\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(zwjnum), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"ZWJ 夹数字须检测为污染 EXIT=3（防 fail-open），实为 {rc}"
        # R4.3 复核（主代理对抗实证）：emoji(So) 夹进数字串（n=8👨‍👩88）同样
        # 让数字正则静默失配 → checked=0 → PASS fail-open。合法 emoji 放行
        # 不能以打开此通道为代价；emoji/ZWJ 段紧贴 ASCII 数字须 EXIT=3。
        emonum = d / "emoji_num.md"
        emonum.write_text("n=8👨\u200d👩88\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(emonum), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"emoji 夹数字须检测为污染 EXIT=3（防 fail-open），实为 {rc}"

        # R4.3（两路独立盲检交叉验证 🔴1）：「数字被非数字字符劈开」与
        # 「关键标记与数字被隔开」两种形态都会让数字正则静默失配 → checked=0
        # → PASS fail-open。三个必测变体：
        #   ① emoji 插在 = 与数字之间（p = 👨‍👩 0.9）
        #   ② 范围外符号 ⭐(U+2B50) 夹在数字内部（n=8⭐88）
        #   ③ 组合音标 U+0301 夹在数字内部（p = 0́.9）
        #   ④ 空白拆段（n = 1 2 3）——has_split_number 只管非空白隔断，此前漏网
        for label, payload in (
                ("emoji隔开标记", "p = \U0001F468\u200d\U0001F469 0.9\n"),
                ("符号劈开数字", "n=8\u2b5088\n"),
                ("音标劈开数字", "p = 0\u0301.9\n"),
                ("空白拆段数字", "n = 1 2 3\n")):
            f_split = d / f"split_{label}.md"
            f_split.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_split), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 3, f"{label} 须 EXIT=3（数字正则失配防 fail-open），实为 {rc}"

        # R4.5（两路盲检 9🔴+6🟠 + 主代理对抗实证）：13 个「声明存在却零提取」
        # fail-open 变体全部须拒绝 PASS。两类期望：
        #   - NFKC 可归一化（①⑧²／全角＝％［］数字）→ 正则恢复提取 → 未溯源 EXIT=5；
        #   - 归一化后仍隔断（CJK紧邻走边界判据除外的 9符号/小数点空白拆/逗号·中点·
        #     阿拉伯小数点/连字符拆段）→ prepare_numbers 声明总闸 → EXIT=3。
        # 合法对照（纯文字 / n=5 小 n）须保持 EXIT=0，不得 fail-close 误拒。
        for label, payload, want_rc in (
                ("CJK紧邻声明", "实验p=0.8，差异显著。\n", 5),
                ("圈号数字", "结论：p = ①.⑧，差异极显著。\n", 5),
                ("上标数字", "n = 8²8\n", 5),
                ("全角百分号", "保护率 95％（权威源无）。\n", 5),
                ("全角等号", "p＝0.8\n", 5),
                ("全角方括号CI", "CI ［0.1，0.2］\n", 5),
                ("9符号劈开", "n = 1©©©©©©©©©2，样本量见此。\n", 3),
                ("小数点空白拆", "p = 0 . 8，差异显著。\n", 3),
                ("全角数字小数点", "p = ０．９４\n", 5),
                ("逗号小数点", "p = 0,94\n", 3),
                # R4.12：中点/阿拉伯小数点 NFKC 不收敛，经 _EQUIV_TRANS 语义
                # 等价映射为 ASCII '.' 后正确提取 0.94 → 权威源无 → EXIT=5
                # （旧口径 rc=3 是隔断 fail-closed，现已精确化为「未溯源」）。
                ("中点小数点", "p = 0·94\n", 5),
                ("阿拉伯小数点", "p = ٠٫٩٤\n", 5),
                ("连字符拆段", "n = 1-2-3\n", 3)):
            f_u = d / f"uni_{label}.md"
            f_u.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_u), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc and rc != 0, \
                f"{label} 须 EXIT={want_rc}（不得 PASS），实为 {rc}"
        # 合法对照：纯文字（无声明）与小 n（min_digits 有意跳过）不得误拒
        for label, payload in (("纯文字", "本研究分析了进化关系\n"),
                               ("小n跳过", "n = 5\n")):
            f_ok = d / f"ok_{label}.md"
            f_ok.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_ok), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 0, f"{label} 不得 fail-close 误拒，实为 {rc}"

        # R4.12（盲检 A🔴2 多语小数点 + 主代理对抗实证）：语义等价映射后正确
        # 提取（未溯源 EXIT=5），句号型小数点定点 fail-closed（EXIT=3），
        # 合法中文句号句读不得误拒（EXIT=0）。
        for label, payload, want_rc in (
                ("片假名中点", "p = 0･94\n", 5),
                ("全角句点", "p = 0．94\n", 5),
                ("阿拉伯千分位", "n = 1٬234\n", 5),
                ("中文句号小数点", "n = 30。5\n", 3),
                ("半角句点小数点", "n = 30｡5\n", 3),
                # 合法句读：源池 s2 无 30 → 正常 EXIT=5（未溯源），但绝不可
                # 被句号型定点检测误判为隔断 fail-close（EXIT=3）。
                ("合法中文句号句读", "样本 n = 30。结果显示有效。\n", None)):
            f_r = d / f"r412_{label}.md"
            f_r.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            if want_rc is None:
                assert rc != 3, f"R4.12 {label} 不得 fail-close 误拒（EXIT=3），实为 {rc}"
            else:
                assert rc == want_rc, f"R4.12 {label} 须 EXIT={want_rc}，实为 {rc}"

        # R4.13（8🔴，主代理逐条独立复现）：Sm/fullwidth 符号隔断声明、池中
        # 逗号延续洗白、CI 花括号、float 截断候选、check_scope Mn 隔断。
        r13src = d / "r13_src"
        r13src.mkdir(exist_ok=True)
        (r13src / "pool.csv").write_text(
            "metric,value\nx,94,500\np,0.944\n", encoding="utf-8")
        for label, payload, want_rc in (
                ("Sm符号隔断声明", "结果 p\u2b30 = 0.94（伪造）\n", 3),
                ("CI花括号", "结果 CI ｛0.1, 0.2｝（伪造）\n", 5),
                ("池中逗号延续洗白", "样本 n = 94（权威池仅 94,500）\n", 5),
                ("float截断候选洗白", "结果 p = 0.94412（权威池仅 0.944）\n", 5)):
            f_r13 = d / f"r13_{label}.md"
            f_r13.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r13), "--sources", str(r13src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc, f"R4.13 {label} 须 EXIT={want_rc}（不得 PASS=0），实为 {rc}"
        # 合法对照：CSV 双数字字段须正常溯源 EXIT=0；CI 方括号形态须正常
        # 提取（源池无 0.1 → 未溯源 EXIT=5，但绝不可 fail-close 隔断 EXIT=3）。
        csv_src = d / "s_csv"
        csv_src.mkdir(exist_ok=True)
        (csv_src / "p.csv").write_text("metric,value\nn,30\np,0.9441\n", encoding="utf-8")
        f_csv = d / "r13ok_csv.md"
        f_csv.write_text("样本 n = 30，p = 0.9441\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_csv), "--sources", str(csv_src)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 0, f"R4.13 合法 CSV 双字段须溯源 EXIT=0，实为 {rc}"
        f_ci = d / "r13ok_ci.md"
        f_ci.write_text("结果 CI [0.1, 0.2]\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_ci), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc != 3, f"R4.13 合法 CI 方括号不得 fail-close 隔断 EXIT=3，实为 {rc}"
        # check_scope：Mn 插进事故值 1094 须仍判污染 EXIT=3
        scope = PKG / "scripts" / "check_scope.py"
        sc_f = d / "r13_scope.py"
        sc_f.write_text("x = 10\u030194\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(scope), str(sc_f)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"R4.13 check_scope Mn 隔断事故值须 EXIT=3，实为 {rc}"

        # R4.14（盲检 A 7🔴，全部主代理独立复现）：Sm/Pd/Po 劈开数字前缀洗白、
        # 预组合同形/希腊同形声明标记、prime 变体、池逗号 4+ 位回溯绕过、
        # check_scope/poll 非 Mn 符号隔断、G6 line=true（后者在 G6 函数内）。
        r14src = d / "r14_src"
        r14src.mkdir(exist_ok=True)
        for label, payload, pool, want_rc in (
                ("Sm劈开前缀洗白", "样本 n = 88\u2b3088（伪造）\n", "value\n88\n", 3),
                ("Po全角感叹劈开", "样本 n = 94\uff0194（伪造）\n", "value\n94\n", 3),
                ("预组合同形n", "ń = 94\n", "value\n0.11\n", 5),
                ("希腊同形nu", "ν = 94\n", "value\n0.11\n", 5),
                ("prime变体acute", "d\u00b4=0.94\n", "value\n0.11\n", 5),
                ("池逗号4位洗白", "样本 n = 94\n", "value\n94,5000\n", 5)):
            (r14src / "pool.csv").write_text(pool, encoding="utf-8")
            f_r14 = d / f"r14_{label}.md"
            f_r14.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r14), "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc, \
                f"R4.14 {label} 须 EXIT={want_rc}（不得 PASS=0），实为 {rc}"
        # 合法对照：多语小数点 / 全角逗号 CI / 合法数字格式不得 fail-close 误拒
        for label, payload in (("多语小数点", "p = 0\u00b794\n"),
                               ("全角逗号CI", "CI ［0.1\uff0c0.2］\n"),
                               ("千分位", "1,234.5\n"), ("时间", "10:30\n")):
            f_ok = d / f"r14ok_{label}.md"
            f_ok.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_ok), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc != 3, f"R4.14 合法 {label} 不得 fail-close EXIT=3，实为 {rc}"
        # check_scope 非 Mn 符号隔断（Sm ⬰ / Po ！ / Pd —）须判污染 EXIT=3
        for label, payload in (("Sm", "x = 10\u2b3094\n"),
                               ("Po", "x = 10\uff0194\n"), ("Pd", "x = 10\u201494\n")):
            sc_f = d / f"r14_scope_{label}.py"
            sc_f.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(scope), str(sc_f)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 3, f"R4.14 check_scope {label} 隔断事故值须 EXIT=3，实为 {rc}"

        # R4.15（盲检 A🔴2/3/4/5，主代理逐条独立复现）：ZWJ 隔断事故叙事、
        # 劈开上限 {1,8} 绕过（9 分隔符）、前置分隔符破坏 all() 判据、
        # Co/Me 类漏检——四者均让前缀被池中洗白或黑名单失配。
        sc_zwj = d / "r15_scope_zwj.md"
        sc_zwj.write_text("位\u200d置映射错（具体事故）\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(scope), str(sc_zwj)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"R4.15 ZWJ 隔断事故叙事须 EXIT=3，实为 {rc}"
        for label, payload in (
                ("9分隔符上限", "样本 n = 94" + "×" * 9 + "7，伪造。\n"),
                ("前置分隔符", "样本 n = 94,⬰7，伪造。\n"),
                ("Co私有区", "样本 n = 94\ue0007，伪造。\n"),
                ("Me组合环", "样本 n = 94\u20dd7，伪造。\n")):
            (r14src / "pool.csv").write_text("value\n94\n", encoding="utf-8")
            f_r15 = d / f"r15_{label}.md"
            f_r15.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r15),
                                 "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 3, f"R4.15 {label} 须 EXIT=3（不得 PASS=0），实为 {rc}"

        # R4.16（盲检 A🔴1/2）：Unicode 名称语义同形声明（ɲ/ŋ/ϕ 非 NFKC
        # 可分解）→ 零提取 PASS；池中字母后缀（94e5/94kg）洗白整数声明。
        for label, payload, pool, want_rc in (
                ("IPA同形n声明", "样本 ɲ = 888 只\n", "other,0.5\n", 3),
                ("希腊phi同形", "样本 ϕ = 0.94\n", "other,0.5\n", 3),
                ("池中科学计数洗白", "n = 94\n", "val\n94e5\n", 5),
                ("池中百分号洗白", "n = 94\n", "val\n94%\n", 5)):
            (r14src / "pool.csv").write_text(pool, encoding="utf-8")
            f_r16 = d / f"r16_{label}.md"
            f_r16.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r16),
                                 "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc, \
                f"R4.16 {label} 须 EXIT={want_rc}（不得 PASS=0），实为 {rc}"
        # 合法对照：预组合 ń 经 NFD 转 ASCII（EXIT=5 非 3）、CSV 双字段正常溯源
        f_nfd = d / "r16ok_nfd.md"
        f_nfd.write_text("ń = 94\n", encoding="utf-8")
        (r14src / "pool.csv").write_text("val\n0.11\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_nfd),
                             "--sources", str(r14src)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc != 3, f"R4.16 预组合 ń 不得 fail-close EXIT=3，实为 {rc}"

        # R4.17（盲检 3🔴）：① 同形声明泛化——ɣ(LATIN GAMMA→p)/ס(HEBREW
        # SAMEKH→n) 及 Mn 隔断的 ɲ\u0301 均零提取 PASS，须 fail-closed；
        # ② 权威池多语小数点——产出 n=94 被池中 94·5 / 94٫5 洗白。
        for label, payload, pool, want_rc in (
                ("gamma同形声明", "样本 ɣ = 888 只\n", "other,0.5\n", 3),
                ("samekh同形声明", "样本 ס = 888 只\n", "other,0.5\n", 3),
                ("Mn隔断同形", "样本 ɲ\u0301 = 888 只\n", "other,0.5\n", 3),
                ("池中点洗白", "n = 94\n", "val\n94·5\n", 5),
                ("池中阿小数点洗白", "n = 94\n", "val\n94٫5\n", 5)):
            (r14src / "pool.csv").write_text(pool, encoding="utf-8")
            f_r17 = d / f"r17_{label}.md"
            f_r17.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r17),
                                 "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc, \
                f"R4.17 {label} 须 EXIT={want_rc}（不得 PASS=0），实为 {rc}"
        # 合法对照：ASCII n / 纯池中整数 / CSV 浮点字段不得误伤
        for label, payload, pool in (
                ("ASCII声明", "n = 94\n", "val\n94\n"),
                ("CSV浮点字段", "p = 0.9441\n", "val\n30,0.9441\n")):
            (r14src / "pool.csv").write_text(pool, encoding="utf-8")
            f_r17ok = d / f"r17ok_{label}.md"
            f_r17ok.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r17ok),
                                 "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 0, f"R4.17 合法对照 {label} 不得误伤 EXIT={rc}"
        # 池归一化后 CSV 浮点字段仍溯源（0.9441 in 30,0.9441）

        # R4.18（两路盲检交叉印证，主代理逐条独立复现）：① 池右边界按语义
        # 类别判据——浮点 e5/%、整数 $/° 后缀洗白；② 同形声明排除名单漏洞
        # ——假名 ん/ニ、非字母 mark ★/Co；③ check_scope 黑名单 % 永假 +
        # 跨行事故叙事 + 非 ASCII Nd 数字（泰文 PMID）。
        for label, payload, pool, want_rc in (
                ("浮点e5洗白", "样本 p = 0.94\n", "val\n0.94e5\n", 5),
                ("浮点百分号洗白", "样本 p = 0.94\n", "val\n0.94%\n", 5),
                ("整数货币洗白", "样本 n = 94\n", "val\n94$\n", 5),
                ("整数度数洗白", "样本 n = 94\n", "val\n94°\n", 5),
                ("平假名同形", "样本 \u3093 = 94\n", "val\n0.11\n", 3),
                ("片假名同形", "样本 \u30cb = 94\n", "val\n0.11\n", 3),
                ("符号mark同形", "样本 \u2605 = 94\n", "val\n0.11\n", 3),
                ("私用区mark同形", "样本 \ue000 = 94\n", "val\n0.11\n", 3)):
            (r14src / "pool.csv").write_text(pool, encoding="utf-8")
            f_r18 = d / f"r18_{label}.md"
            f_r18.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_r18),
                                 "--sources", str(r14src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc, \
                f"R4.18 {label} 须 EXIT={want_rc}（不得 PASS=0），实为 {rc}"
        # check_scope：% 字面量黑名单 + 跨行事故叙事 + 泰文 Nd 数字 PMID
        scope18 = PKG / "scripts" / "check_scope.py"
        for label, payload in (
                ("事故值百分号", "事故错误值 20.58%\n"),
                ("事故叙事跨行", "位置映射\n错误\n"),
                ("泰文数字PMID", "PP \u0e54\u0e51\u0e50\u0e53\u0e54\u0e53\u0e58\u0e50\n")):
            f_sc18 = d / f"r18_scope_{label}.md"
            f_sc18.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(scope18), str(f_sc18)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 3, f"R4.18 check_scope {label} 须 EXIT=3，实为 {rc}"

        # R4.7（两路盲检 6🔴，全部主代理独立复现）：
        # A🔴 CJK 紧邻 n= 空白拆段（\b 边界漂移）；B1 诱饵数字短路声明总闸；
        # B3 逗号未作数字边界（n=94 被池中 0,94 洗白）；B4 NFKC 不覆盖的排版/
        # 同形字等价（D’ / CI【】 / ρ）；B5 小 n 豁免把顿号当句读。
        cjk = d / "r47_cjk.md"
        cjk.write_text("研究记录\n样本n = 1 2 3\n结论成立\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(cjk), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"CJK 紧邻空白拆段须 EXIT=3，实为 {rc}"

        decoy_src = d / "s_decoy"
        decoy_src.mkdir(exist_ok=True)
        (decoy_src / "a.csv").write_text("n,30\np,0.05\n", encoding="utf-8")
        for label, payload, want_rc in (
                ("诱饵逗号", "样本 n = 30，结果 p = 0,94（伪造）\n", 3),
                ("诱饵连字符", "样本 n = 30；另一声明 n = 1-2-3（伪造）\n", 3),
                ("小n顿号", "样本 n = 5、94（伪造的 94 被顿号隔断）\n", 3)):
            f_d = d / f"r47_{label}.md"
            f_d.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_d), "--sources", str(decoy_src)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == want_rc and rc != 0, f"{label} 须 EXIT={want_rc}（不得 PASS），实为 {rc}"

        comma_src = d / "s_comma"
        comma_src.mkdir(exist_ok=True)
        (comma_src / "a.csv").write_text("European value 0,94\n", encoding="utf-8")
        f_comma = d / "r47_comma.md"
        f_comma.write_text("样本 n = 94（池中只有 0,94）\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_comma), "--sources", str(comma_src)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 5, f"n=94 不得被池中 0,94 逗号洗白（须 EXIT=5），实为 {rc}"

        for label, payload in (
                ("弯引号D'", "结果 D’=0.94（U+2019，伪造）\n"),
                ("中文方括号CI", "CI【0.10, 0.20】（假造 CI）\n"),
                ("同形字rho", "结果 ρ=0.94（希腊 rho，伪造）\n")):
            f_g = d / f"r47_{label}.md"
            f_g.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_g), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 5, f"{label} 须归一化后提取并判未溯源 EXIT=5，实为 {rc}"

        # 合法对照不得被逐声明总闸误拒（不得 EXIT=3）
        for label, payload in (
                ("小n句读", "样本 n = 5，p = 0.111\n"),
                ("n示例", "样本量 n = 30 例\n"),
                ("常规CI", "CI [0.1, 0.2]\n")):
            f_l = d / f"r47_ok_{label}.md"
            f_l.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_l), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc in (0, 5), f"合法对照 {label} 不得 fail-close 误拒为 3，实为 {rc}"

        # R4.8（盲检 A🔴1）：守卫层与提取层各写正则导致口径漂移——11 个声明
        # 变体（小写 d/ci、CI 冒号/等号、p 冒号、西里尔同形字）原全 PASS。
        # 提取 PATTERNS 统一大小写/[=:]/CI 可选分隔符，守卫 full_re 复用同一对象。
        for label, payload in (
                ("小写d", "结果 d'=0.94（伪造）\n"),
                ("大写D", "结果 D'=0.94（伪造）\n"),
                ("prime符", "结果 d′=0.94（伪造）\n"),
                ("小写ci", "结果 ci [0.10, 0.20]（伪造）\n"),
                ("CI冒号", "结果 CI: [0.10, 0.20]（伪造）\n"),
                ("CI等号", "结果 CI = [0.10, 0.20]（伪造）\n"),
                ("p冒号", "结果 p: 0.94（伪造）\n"),
                ("西里尔CI", "结果 СІ [0.10, 0.20]（伪造）\n"),
                ("西里尔p", "结果 р: 0.94（伪造）\n")):
            f_v = d / f"r48_{label}.md"
            f_v.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_v), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 5, f"{label} 须提取后判未溯源 EXIT=5（不得 PASS），实为 {rc}"
        # 顿号并列的小 n 声明是合法中文句，不得被 B5 修复误伤为 EXIT=3
        f_dun = d / "r48_dunhao.md"
        f_dun.write_text("样本量 n = 5、p = 0.111\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_dun), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc in (0, 5), f"顿号并列合法声明不得 fail-close 误拒，实为 {rc}"

        # R4.8（盲检 B🔴2）：冒号声明的隔断检测须与提取/小 n 判定同口径。
        # KEY_MARKERS 原只认 '='，n: 1 2 3 零提取 → checked=0 → PASS。
        f_colon = d / "r48_colon_split.md"
        f_colon.write_text("样本 n: 1 2 3\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_colon), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"冒号空白拆段须 fail-closed EXIT=3，实为 {rc}"
        # R4.8（盲检 B🟠3）：CSV 字段分隔符逗号不得当数字延续，否则 p,0.111
        # 中的合法字段值无法溯源（fail-close 误拒）。
        f_csv = d / "r48_csv_field.md"
        f_csv.write_text("结果 p = 0.111 与权威一致\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_csv), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 0, f"CSV 字段值须正常溯源 EXIT=0，实为 {rc}"

        # R4.9（盲检 B🔴1）：ZWJ(U+200D)/VS16(U+FE0F) 插在声明标记与 = 之间，
        # 原 has_forbidden 放行、KEY_MARKERS 漏检 → checked=0 → PASS。
        for label, payload in (("ZWJ的p", "p\u200d=0.94\n"),
                               ("ZWJ的n", "n\u200d=94\n"),
                               ("VS16的p", "p\ufe0f=0.94\n")):
            f_z = d / f"r49_{label}.md"
            f_z.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_z), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc in (3, 5), f"{label} 不可见隔断须 fail-closed，实为 {rc}"
        # R4.9（盲检 B🔴2）：同形字/多语百分号（NFKC 不收敛）——п/η/٪ 原全 PASS
        for label, payload in (("西里尔п", "п = 94\n"),
                               ("希腊eta", "η = 94\n"),
                               ("阿文百分号", "保护率 95\u066a\n")):
            f_e = d / f"r49_{label}.md"
            f_e.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_e), "--sources", str(d / "s2")],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc in (3, 5), f"{label} 同形字须 fail-closed，实为 {rc}"
        # R4.9（盲检 B🟠4）：CSV 双数字字段 30,0.9441 中两值均须正常溯源
        d_csv = d / "s3"
        d_csv.mkdir(exist_ok=True)
        (d_csv / "a.csv").write_text("source_tag: authoritative\nn,p\n30,0.9441\n", encoding="utf-8")
        f_dual = d / "r49_csv_dual.md"
        f_dual.write_text("样本 n = 30，p = 0.9441\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_dual), "--sources", str(d_csv)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 0, f"CSV 双数字字段须正常溯源 EXIT=0，实为 {rc}"
        # 合法 emoji ZWJ 不得被 ZWJ 隔断守卫误伤
        f_ezwj = d / "r49_emoji.md"
        f_ezwj.write_text("家族 👨‍👩‍👧 样本量 n = 30\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_ezwj), "--sources", str(d / "s2")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc in (0, 5), f"合法 emoji ZWJ 不得 fail-close 误拒，实为 {rc}"

        # R4.10（盲检 A🔴2/3/4）：守卫独立于 min_digits + 提取 token 边界。
        # --min-digits 1 不得关闭声明守卫；n=1234567 / 1234% 不得截断洗白。
        f_m1 = d / "r410_min1.md"; f_m1.write_text("p = 0,94\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_m1), "--sources", str(d / "s2"),
                             "--min-digits", "1"], capture_output=True, text=True,
                            timeout=60).returncode
        assert rc == 3, f"min-digits=1 不得关闭声明守卫（须 EXIT=3），实为 {rc}"
        for label, payload, pool_val in (("n超长", "n = 1234567\n", "123456"),
                                         ("pct超长", "1234%\n", "234")):
            sub = d / f"r410_{label}"; sub.mkdir(exist_ok=True)
            (sub / "a.csv").write_text(f"metric,value\nother,{pool_val}\n", encoding="utf-8")
            f_x = d / f"r410_{label}.md"; f_x.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_x), "--sources", str(sub)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc in (3, 5), f"{label} 截断片段不得洗白，实为 {rc}"
        # CI/dprime 个位整数部分合法（原 \d\.\d+ 只认个位 → fail-close 误拒）
        d_ci = d / "r410_ci"; d_ci.mkdir(exist_ok=True)
        (d_ci / "a.csv").write_text("metric,value\nlow,12.3\nhigh,45.6\n", encoding="utf-8")
        f_ci = d / "r410_ci.md"; f_ci.write_text("CI [12.3, 45.6]\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_ci), "--sources", str(d_ci)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 0, f"CI 多位整数部分须正常溯源 EXIT=0，实为 {rc}"
        # 合法并列声明不得被 token 右边界误伤
        d_multi = d / "r410_multi_src"; d_multi.mkdir(exist_ok=True)
        (d_multi / "a.csv").write_text("metric,value\nn,30\np,0.111\n", encoding="utf-8")
        f_multi = d / "r410_multi.md"
        f_multi.write_text("样本 n = 30，p = 0.111\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(vn), str(f_multi), "--sources", str(d_multi)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 0, f"中文逗号并列声明不得误拒 EXIT=0，实为 {rc}"

        # R4.3（盲检🟠4）：数字 grep 原为子串匹配——p=0.94 被权威源里的 0.9441
        # 洗白（假阳性 PASS）、p=0.98 被 10.980 洗白。改 token 边界匹配后，
        # 两者都必须判未溯源 EXIT=5。
        for label, payload, pool_val in (("0.94", "p = 0.94\n", "0.9441"),
                                         ("0.98", "p=0.98\n", "10.980")):
            sub = d / f"sub_{label}"
            sub.mkdir(exist_ok=True)
            (sub / "pool.csv").write_text(f"value\n{pool_val}\n", encoding="utf-8")
            f_sub = d / f"sub_{label}.md"
            f_sub.write_text(payload, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(f_sub), "--sources", str(sub)],
                                capture_output=True, text=True, timeout=60).returncode
            assert rc == 5, f"{label} 不得被池中 {pool_val} 子串洗白（须 EXIT=5），实为 {rc}"

        # R4.2（盲检🔴6）：check_scope 不可解码/控制字符污染文件不得误判 clean(0)，
        # 须报无法核验 → EXIT=3（fail-closed）。
        cs = PKG / "scripts" / "check_scope.py"
        dirty = d / "dirty.md"
        dirty.write_bytes("# 事故\nPP 41034380\n".encode("utf-16"))
        rc = subprocess.run([sys.executable, str(cs), str(dirty)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"不可解码污染文件须 EXIT=3（非 clean），实为 {rc}"

        # R4.2（盲检🔴4）：confirmed_hypotheses.json 顶层非对象（合法 JSON []）
        # 不得 AttributeError 崩溃（EXIT=1），须降级跳过（无 traceback）。
        asm = PKG / "scripts" / "assemble_spawn_prompt.py"
        ro = d / "ro"; (ro / "context_stack").mkdir(parents=True)
        (ro / "context_stack" / "confirmed_hypotheses.json").write_text("[]", encoding="utf-8")
        taskf = d / "task.txt"; taskf.write_text("test task", encoding="utf-8")
        env = dict(os.environ, RESEARCH_OPS_DIR=str(ro))
        p = subprocess.run([sys.executable, str(asm), "--expert-dir", str(PKG),
                            "--member", "literature-scout", "--task-file", str(taskf),
                            "--no-autodetect"], capture_output=True, text=True,
                           timeout=60, env=env)
        assert "Traceback" not in (p.stdout + p.stderr), "assemble 顶层非对象不得崩溃"
        assert p.returncode != 1, f"assemble 畸形知识态不得 EXIT=1，实为 {p.returncode}"

        # R4.2（盲检🔴5）：validate_contracts plugin.json 顶层非对象须 EXIT=5
        # （契约仅 0/5），不得 AttributeError traceback EXIT=1。用副本改 manifest。
        import shutil
        pcopy = d / "pkgcopy"
        shutil.copytree(PKG, pcopy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        (pcopy / ".codebuddy-plugin" / "plugin.json").write_text("[]", encoding="utf-8")
        p = subprocess.run([sys.executable, str(pcopy / "scripts" / "validate_contracts.py")],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in (p.stdout + p.stderr), "validate_contracts 畸形 manifest 不得崩溃"
        assert p.returncode == 5, f"畸形 manifest 须 EXIT=5，实为 {p.returncode}"

        # R4.3（盲检🔴1）：version 字段为 list/dict 时 set(values) 抛 TypeError
        # → EXIT=1（契约仅 0/5）。须记契约缺失 → EXIT=5。
        mvf = pcopy / ".codebuddy-plugin" / "plugin.json"
        # 上一步把顶层写成 []，先恢复为合法对象基底（真实 plugin.json）
        mvf.write_bytes((PKG / ".codebuddy-plugin" / "plugin.json").read_bytes())
        mobj = json.loads(mvf.read_text(encoding="utf-8"))
        mobj["version"] = ["1.5.20", "bad"]
        mvf.write_text(json.dumps(mobj), encoding="utf-8")
        p = subprocess.run([sys.executable, str(pcopy / "scripts" / "validate_contracts.py")],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 5 and "Traceback" not in (p.stdout + p.stderr), \
            f"version=list 须 EXIT=5 不得崩溃，实为 {p.returncode}: {p.stderr[-200:]}"

        # R4.3（盲检🔴3）：assemble plugin.json 的 teamInfo 非对象 / members 元素
        # 非对象不得 AttributeError 崩溃 EXIT=1（契约无 1）。
        for bad_field, bad_val in (("teamInfo", ["malformed"]), ("members", ["bad-str"])):
            pj = pcopy / ".codebuddy-plugin" / "plugin.json"
            # 每次从合法基底重建，避免上一迭代畸形字段累积
            pj.write_bytes((PKG / ".codebuddy-plugin" / "plugin.json").read_bytes())
            obj = json.loads(pj.read_text(encoding="utf-8"))
            obj.pop("teamInfo", None); obj.pop("members", None)
            obj[bad_field] = bad_val
            pj.write_text(json.dumps(obj), encoding="utf-8")
            p = subprocess.run([sys.executable, str(asm), "--expert-dir", str(pcopy),
                                "--member", "literature-scout", "--task-file", str(taskf),
                                "--no-autodetect"], capture_output=True, text=True,
                               timeout=60, env=env)
            assert "Traceback" not in (p.stdout + p.stderr) and p.returncode != 1, \
                f"{bad_field}={bad_val} 不得崩溃 EXIT=1，实为 {p.returncode}: {p.stderr[-200:]}"

        # R4.19（盲检 B🔴1/2/5/6）：verify_numbers 四类 fail-open 回归。
        import tempfile as _tf
        with _tf.TemporaryDirectory(prefix="vn_r419_") as td:
            vn_d = Path(td)
            pool = vn_d / "pool.csv"
            pool.write_text("metric,value\nother,0.11\n", encoding="utf-8")
            vn = PKG / "scripts" / "verify_numbers.py"

            def vn_rc(text: str, source: Path = pool) -> int:
                f = vn_d / "artifact.md"
                f.write_text(text, encoding="utf-8")
                return subprocess.run(
                    [sys.executable, str(vn), str(f), "--sources", str(source), "--json"],
                    capture_output=True, text=True, timeout=60).returncode

            # B🔴1：prime 豁免泛化——d+任意非ASCII字母须拦；合法 d′ 仍 EXIT=5。
            for label, mark in (("IPA", "\u0272"), ("Greek", "\u03b1"), ("Cyrillic", "\u0433")):
                assert vn_rc(f"样本 d{mark}=0.94（伪造）\n") == 3, \
                    f"R4.19 d+{label} 非prime mark 须同形守卫 EXIT=3"
            assert vn_rc("样本 d′=0.94（合法prime）\n") == 5, \
                "R4.19 合法 d′ 不得被误杀（须未溯源 EXIT=5）"
            # B🔴2：CJK Lo 隔断 p/n 声明须拦（合法「样本 n = 94」仍 EXIT=5 已验）。
            for text in ("样本 p量=0.94（伪造）\n", "样本 n量=94（伪造）\n"):
                assert vn_rc(text) == 3, f"R4.19 CJK 隔断声明须 EXIT=3: {text!r}"
            # B🔴5：池左边界字母前缀洗白须拒。
            pool.write_text("metric,raw\ncase,id94\n", encoding="utf-8")
            assert vn_rc("样本 n = 94\n") == 5, "R4.19 池 id94 不得洗白 n=94"
            pool.write_text("metric,raw\ncase,x0.94\n", encoding="utf-8")
            assert vn_rc("结果 p = 0.94\n") == 5, "R4.19 池 x0.94 不得洗白 p=0.94"
            # B🔴6：Pc（下划线/undertie）数值延续须拒。
            for sep in ("_", "\u203f"):
                pool.write_text(f"metric,raw\ncase,0.94{sep}5\n", encoding="utf-8")
                assert vn_rc("结果 p = 0.94\n") == 5, \
                    f"R4.19 池 0.94{sep!r}5 不得洗白 p=0.94"


    # R4.20（盲检 B🔴6 / A🟠8）：ASCII 隔断与池符号前缀 fail-closed，
    # 合法 `p = 0.94` 不误伤。
    with tempfile.TemporaryDirectory(prefix="vn_r420_") as td:
        d = Path(td)
        (d / "pool.csv").write_text("metric,value\nother,0.94\n", encoding="utf-8")
        (d / "sym.csv").write_text("metric,value\nother,\u20ac0.94\n", encoding="utf-8")
        vn = PKG / "scripts" / "verify_numbers.py"
        for text, src, want in (("结果 pA=0.94\n", "pool.csv", 3),
                                ("样本 nA=94\n", "pool.csv", 3),
                                ("结果 p = 0.94\n", "pool.csv", 0),
                                ("结果 p=0.94\n", "sym.csv", 5)):
            (d / "a.md").write_text(text, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(vn), str(d / "a.md"),
                                 "--sources", str(d / src), "--json"],
                                capture_output=True, text=True).returncode
            assert rc == want, f"R4.20 vn {text!r}/{src} 须 EXIT={want}，实为 {rc}"

    # R4.21（盲检 A🔴1/A🔴2/B🔴1）：数字劈开类别 Cn + {1,64} 有界 + 短 mid 上限
    # 三处 fail-open 回归——Cn/65×Sm 隔断须 EXIT=3；pABC/pXYZ 长 mid 隔断须 EXIT=3。
    with tempfile.TemporaryDirectory(prefix="r421_vn_") as td:
        d = Path(td)
        (d / "t09.csv").write_text("0.9\n", encoding="utf-8")
        (d / "pool.csv").write_text("0.11\n", encoding="utf-8")
        def vr(src, truth):
            (d / "a.md").write_text(src, encoding="utf-8")
            return subprocess.run([sys.executable, str(PKG / "scripts" / "verify_numbers.py"),
                                   str(d / "a.md"), "--sources", str(d / truth), "--json"],
                                  capture_output=True, text=True).returncode
        assert vr("p = 0.9\u03784\n", "t09.csv") == 3, "R4.21 Cn 隔断数字须 EXIT=3"
        assert vr("p = 0.9" + "\u2b30" * 65 + "4\n", "t09.csv") == 3, "R4.21 65×Sm 隔断须 EXIT=3"
        assert vr("n = 94\u03785\n", "t09.csv") in (3, 5), "R4.21 n 声明 Cn 隔断不得 PASS"
        assert vr("结果 pABC=0.94\n", "pool.csv") == 3, "R4.21 pABC 长 mid 隔断须 EXIT=3"
        assert vr("结果 pXYZ:0.94\n", "pool.csv") == 3, "R4.21 pXYZ 冒号隔断须 EXIT=3"
        assert vr("结果 pA=0.94\n", "pool.csv") == 3, "R4.21 pA 短 mid 对照须 EXIT=3"


def test_poll_hitlimit_and_manifest() -> None:
    """R-13a/c（2026-11-09）：撞限标注消费 + --from-manifest 行为级守卫。

    三断言（对照 2026-11-09 任务 B 取证实测的缺陷）：
      1. 头部带「轮次耗尽」标注的 artifact → NOT_READY / EXIT=5（此前判 READY）
      2. --from-manifest 从 spawn_manifest.jsonl 自动生成期望清单 → 正常巡检
      3. manifest 缺失 → EXIT=5（不静默放行）
    """
    with tempfile.TemporaryDirectory(prefix="poll_hl_") as td:
        d = Path(td) / "r"
        d.mkdir(parents=True)
        poll = PKG / "scripts" / "poll_run_dir.py"

        def run(*args: str) -> tuple[int, str]:
            p = subprocess.run([sys.executable, str(poll), str(d), "T-P"] + list(args),
                               capture_output=True, text=True, timeout=60)
            return p.returncode, p.stdout + p.stderr

        # 断言 1：撞限标注 → EXIT=5
        (d / "T-P__literature-scout.md").write_text(
            "<!-- 轮次耗尽，产出不完整：已完成 1/3，剩余 2 -->\n# p\n", encoding="utf-8")
        rc, out = run("--expected", "literature-scout")
        assert rc == 5 and "撞限" in out, f"撞限标注必须 NOT_READY/EXIT=5，实际 rc={rc}"
        # R4.13（盲检 A🔴5）：Mn 组合符插进「轮次耗尽」（轮\u0301次耗尽）让
        # 子串失配 → 不完整产出被判 READY。归一化后须仍判撞限 EXIT=5。
        (d / "T-P__literature-scout.md").write_text(
            "<!-- 轮\u0301次耗尽，产出不完整 -->\n# p\n", encoding="utf-8")
        rc, out = run("--expected", "literature-scout")
        assert rc == 5 and "撞限" in out, \
            f"Mn 隔断撞限标注须 NOT_READY/EXIT=5，实为 rc={rc}: {out[-200:]}"
        # R4.14（盲检 A🔴6）：非 Mn 符号（Sm ⬰ / So ★ / Po ！）隔断撞限词同样
        # 让子串失配 → READY。匹配用途归一化须剥非 ASCII S*/P* → EXIT=5。
        for label, sep in (("Sm", "\u2b30"), ("So", "\u2605"), ("Po", "\uff01")):
            (d / "T-P__literature-scout.md").write_text(
                f"<!-- 轮{sep}次耗尽，产出不完整 -->\n# p\n", encoding="utf-8")
            rc, out = run("--expected", "literature-scout")
            assert rc == 5 and "撞限" in out, \
                f"R4.14 {label} 隔断撞限须 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # R4.15（盲检 A🔴1）：ZWJ(Cf U+200D) 插进「轮次耗尽」—has_forbidden
        # 原只拒 ZWJ 紧贴数字，CJK 侧放行 → READY fail-open。须 EXIT=5。
        (d / "T-P__literature-scout.md").write_text(
            "轮\u200d次耗尽：产出不完整\n# p\n", encoding="utf-8")
        rc, out = run("--expected", "literature-scout")
        assert rc == 5 and "撞限" in out, \
            f"R4.15 ZWJ 隔断撞限须 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # R4.16（盲检 A🔴3）：拉丁扩展字母 ɲ(U+0272) 插进撞限词——
        # normalize_for_matching 剥非 ASCII Ll/Lu/Lt/Lm（保留 CJK）→ EXIT=5。
        for label, sep in (("IPA n", "\u0272"), ("ENG", "\u014b")):
            (d / "T-P__literature-scout.md").write_text(
                f"轮{sep}次耗尽：产出不完整\n# p\n", encoding="utf-8")
            rc, out = run("--expected", "literature-scout")
            assert rc == 5 and "撞限" in out, \
                f"R4.16 {label} 隔断撞限须 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # R4.17（盲检🔴3）：Mc(间距组合符 U+0903)/Me(封闭组合符 U+20DD) 插进
        # 撞限词——normalize_for_matching 剥全 M* 类 → 仍判撞限 EXIT=5。
        for label, sep in (("Mc visarga", "\u0903"), ("Me enclosing", "\u20dd")):
            (d / "T-P__literature-scout.md").write_text(
                f"轮{sep}次耗尽：产出不完整\n# p\n", encoding="utf-8")
            rc, out = run("--expected", "literature-scout")
            assert rc == 5 and "撞限" in out, \
                f"R4.17 {label} 隔断撞限须 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # R4.18（盲检🔴4，纯 CJK 投影）：Nd(阿拉伯 ١)/Zs(空格 NBSP)/No(½)/
        # Lm(ʰ)/Co(私用区)/ASCII(!) 插进撞限词——类别枚举补不完，改纯 CJK 投影。
        for label, sep in (("Nd digit", "\u0661"), ("space", " "), ("NBSP", "\u00a0"),
                           ("No fraction", "\u00bd"), ("Lm modifier", "\u02b0"),
                           ("Co private", "\ue000"), ("ASCII !", "\uff01")):
            (d / "T-P__literature-scout.md").write_text(
                f"轮{sep}次耗尽：产出不完整\n# p\n", encoding="utf-8")
            rc, out = run("--expected", "literature-scout")
            assert rc == 5 and "撞限" in out, \
                f"R4.18 {label} 隔断撞限须 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # 正常文件 → READY
        (d / "T-P__literature-scout.md").write_text("# 正常产出\n", encoding="utf-8")
        rc, _ = run("--expected", "literature-scout")
        assert rc == 0, f"无标注文件应 READY，实际 rc={rc}"
        # 断言 2：--from-manifest 自动清单
        (d / "spawn_manifest.jsonl").write_text(
            '{"task_id":"T-P","member":"literature-scout"}\n', encoding="utf-8")
        rc, _ = run("--from-manifest")
        assert rc == 0, f"--from-manifest 应自动生成清单并 READY，实际 rc={rc}"
        # 断言 3：manifest 缺失 → EXIT=5
        (d / "spawn_manifest.jsonl").unlink()
        rc, out = run("--from-manifest")
        assert rc == 5, f"manifest 缺失必须 EXIT=5，实际 rc={rc}"

        # R4.2（盲检🔴3）：UTF-16 撞限标注（errors="replace" 会吞成 U+FFFD）不得
        # 误判 READY——须严格读 + 控制字符检测 → 保守判撞限 NOT_READY/EXIT=5。
        (d / "T-P__literature-scout.md").write_bytes(
            "<!-- 轮次耗尽：产出不完整 -->\n# p\n".encode("utf-16"))
        rc, out = run("--expected", "literature-scout")
        assert rc == 5 and "撞限" in out, \
            f"UTF-16 撞限标注须 NOT_READY/EXIT=5，实为 rc={rc}"

        # R4.3（盲检🟠C）：撞限标注被挪到第 9 行（原实现只看前 8 行）→ 漏检 →
        # 不完整产出被判 READY/EXIT=0。撞限标注是成员显式写入的产出内容，位置
        # 不应受限——须全文扫描。该行须精确落在第 9 行（>8 行窗口）。
        (d / "T-P__literature-scout.md").write_text(
            "\n".join([f"# 正文第 {i} 行" for i in range(1, 9)]
                      + ["<!-- 轮次耗尽，产出不完整：已完成 1/3，剩余 2 -->"]
                      + ["# 尾注"]) + "\n", encoding="utf-8")
        rc, out = run("--expected", "literature-scout")
        assert rc == 5 and "撞限" in out, \
            f"第 9 行撞限标注须 NOT_READY/EXIT=5（不得因位置漏检），实为 rc={rc}"

        # R4.19（盲检 A🔴3）：manifest 含非法 member（路径注入）须 fail-closed
        # EXIT=5，不得静默跳过缩水期望清单仍判 READY（与 cron_watch 非法 id 同口径）。
        (d / "T-P__literature-scout.md").write_text("# 正常产出\n", encoding="utf-8")
        (d / "spawn_manifest.jsonl").write_text(
            '{"task_id":"T-P","member":"literature-scout"}\n'
            '{"task_id":"T-P","member":"../evil"}\n', encoding="utf-8")
        rc, out = run("--from-manifest")
        assert rc == 5 and "非法 member" in out, \
            f"R4.19 非法 member 须清单无法确定 EXIT=5，实为 rc={rc}: {out[-200:]}"
        # 合法 mixture：spawn + evidence_check（无 member 事件）不得被误伤。
        (d / "spawn_manifest.jsonl").write_text(
            '{"task_id":"T-P","member":"literature-scout"}\n'
            '{"event":"evidence_check","actor":"lead","reason":"抽查"}\n', encoding="utf-8")
        rc, out = run("--from-manifest")
        assert rc == 0, \
            f"R4.19 spawn+evidence_check 混合清单须正常 READY，实为 rc={rc}: {out[-200:]}"


    # R4.20（盲检 B🔴7）：type=spawn + 非字符串 member 不得被当非 spawn
    # 事件静默跳过；合法清单仍 READY。
    with tempfile.TemporaryDirectory(prefix="poll_r420_") as td:
        d = Path(td)
        (d / "T-X__literature-scout.md").write_text("产出\n", encoding="utf-8")
        mf = d / "spawn_manifest.jsonl"
        good = '{"task_id":"T-X","member":"literature-scout"}\n'
        mf.write_text(good, encoding="utf-8")
        poll = PKG / "scripts" / "poll_run_dir.py"
        def prc():
            return subprocess.run([sys.executable, str(poll), str(d), "T-X",
                                   "--from-manifest"], capture_output=True, text=True).returncode
        assert prc() == 0, "R4.20 合法 manifest 须 READY"
        mf.write_text(good + '{"task_id":"T-X","type":"spawn",'
                      '"member":["research-diagnostician"]}\n', encoding="utf-8")
        assert prc() == 5, "R4.20 type=spawn 非字符串 member 须 EXIT=5"

    # R4.21（盲检 B🔴4）：event 优先 type 的黑名单跳过 → 畸形 spawn 行 READY。
    # 任一键含 spawn 语义（含尾随空白）即 fail-closed EXIT=5；已知非 spawn
    # 事件（evidence_check）继续跳过。
    with tempfile.TemporaryDirectory(prefix="r421_poll_") as td:
        d = Path(td)
        (d / "T-RT__literature-scout.md").write_text("产出\n", encoding="utf-8")
        mf = d / "spawn_manifest.jsonl"
        def prc():
            return subprocess.run([sys.executable, str(PKG / "scripts" / "poll_run_dir.py"),
                                   str(d), "T-RT", "--from-manifest"],
                                  capture_output=True, text=True).returncode
        mf.write_text('{"task_id":"T-RT","member":"literature-scout"}\n'
                      '{"event":"evidence_check","actor":"lead"}\n', encoding="utf-8")
        assert prc() == 0, "R4.21 已知非 spawn 事件须正常 READY"
        mf.write_text('{"task_id":"T-RT","member":"literature-scout"}\n'
                      '{"task_id":"T-RT","type":"spawn","event":"evidence_check",'
                      '"member":["victim"]}\n', encoding="utf-8")
        assert prc() == 5, "R4.21 type=spawn+event 伪装须 EXIT=5"
        mf.write_text('{"task_id":"T-RT","member":"literature-scout"}\n'
                      '{"task_id":"T-RT","event":"spawn\\t","member":["victim"]}\n',
                      encoding="utf-8")
        assert prc() == 5, "R4.21 event=spawn 尾随空白须 EXIT=5"


def test_legacy_package_check_fallback() -> None:
    """R-12a（2026-11-09）：vendor V5 → legacy 子串校验回退链行为级守卫。

    锁定既有行为（此前零测试覆盖，回退通道可能被静默改动）：
      1. 散文任务包（无 JSON 结构）+ 默认路径 → V5 拒收（EXIT≠0）
      2. 同输入 + --legacy-package-check → 放行（EXIT=0，mode=legacy-forced）
    回退是「真实退化通道」：legacy 会放行 V5 拒收的输入——这是设计取舍
    （A1 回退开关，正常情况勿用），本测试防止它被静默改为默认或移除。
    """
    with tempfile.TemporaryDirectory(prefix="legacy_fb_") as td:
        d = Path(td)
        asm = PKG / "scripts" / "assemble_spawn_prompt.py"
        task_file = d / "task.txt"
        # 含四要素字样的散文（legacy 子串校验可被"糊弄"——这正是其已知缺陷）
        task_file.write_text(
            "objective：示例目标 output_format：md constraints：只读 task_boundary：仅本任务",
            encoding="utf-8")

        def run(*args: str) -> tuple[int, str]:
            p = subprocess.run(
                [sys.executable, str(asm), "--task-file", str(task_file),
                 "--member", "literature-scout", "--task-id", "T-LG",
                 "--check-task-package", *args],
                capture_output=True, text=True, timeout=60)
            return p.returncode, p.stdout + p.stderr

        rc_v5, _ = run()
        assert rc_v5 != 0, f"散文任务包在 V5 校验下必须被拒，实际 rc={rc_v5}"
        rc_lg, out_lg = run("--legacy-package-check")
        assert rc_lg == 0 and "legacy" in out_lg, \
            f"--legacy-package-check 应放行且注明 legacy 模式，实际 rc={rc_lg}"


def test_g3_fail_still_writes_report() -> None:
    """P0-2（2026-11-09 · 遗留清理轮）：G3 FAIL 早退路径必须落 gates.json。

    历史缺陷：check_gates.py 的 `if not g3: return 3` 在报告落盘之前直接返回，
    门禁失败零留痕（AUDIT_STATE §9 已标高优先级）。本用例锁定修复：
      ① run_dir 无任何成员 artifact → EXIT=3（退出码契约不变）
      ② gates.json 必须存在，verdict=FAIL，G3 记为 false
      ③ 补 1 份 artifact 重跑 → 报告被同一 write_report 重写且 G3 翻为 true
    """
    with tempfile.TemporaryDirectory(prefix="g3report_") as td:
        d = Path(td)
        cmd = [sys.executable, str(CHECK_GATES), str(d), TASK_ID]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert p.returncode == 3, f"G3 FAIL 必须 EXIT=3，实际 {p.returncode} | {out[:200]}"
        assert "Traceback" not in out, f"G3 早退路径异常: {out[:300]}"
        report = d / f"{TASK_ID}__gates.json"
        assert report.is_file(), "G3 FAIL 时 gates.json 未落盘（失败零留痕）"
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data.get("verdict") == "FAIL", f"verdict 应为 FAIL: {data.get('verdict')}"
        assert _read_gates(d).get("G3") is False, "G3 未以 FAIL 记入报告"

        # 覆盖语义：补产出后重跑，报告须由同一 write_report 重写、G3 翻正
        (d / f"{TASK_ID}__phylo-analyst.md").write_text("# 产出\n", encoding="utf-8")
        p2 = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert p2.returncode in (0, 5), f"有产出时应进入完整门禁，实际 {p2.returncode}"
        assert _read_gates(d).get("G3") is True, "补产出后 G3 未翻为 PASS"


def test_decision_log_audit() -> None:
    """P0-1（2026-11-09 · 遗留清理轮）：decision_log 只读审计的退出码契约。

    §13 实证「decision_log.csv 零脚本消费端」。本用例锁定新增消费端的行为：
      0 健康 / 3 结构失败（缺文件·缺列·条目不足）/ 5 内容违规（空值·坏 ts·坏 tier）
      / 6 陈旧提醒；`--max-age-days 0` 禁用陈旧检查；`--json` 供机器消费。
    另在每条路径上断言**台账字节不变**——脚本只校验落盘台账，不代写。
    """
    script = PKG / "scripts" / "audit_decision_log.py"
    header = "ts,actor,decision_type,decision,rationale,tier\n"
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    good = f"{now},lead,G2-waiver,放行示例,理由,通知档\n"
    old = "2020-01-01T00:00:00+08:00,lead,G2-waiver,陈旧条目,理由,通知档\n"

    def run(csv_path: Path, *args: str) -> tuple[int, str]:
        before = csv_path.read_bytes() if csv_path.is_file() else b""
        p = subprocess.run(
            [sys.executable, str(script), str(csv_path), *args],
            capture_output=True, text=True, timeout=60)
        after = csv_path.read_bytes() if csv_path.is_file() else b""
        assert after == before, "只读契约被破坏：审计脚本改写了台账"
        out = p.stdout + p.stderr
        assert "Traceback" not in out, f"审计脚本崩溃: {out[:300]}"
        return p.returncode, out

    with tempfile.TemporaryDirectory(prefix="decision_audit_") as td:
        d = Path(td)
        csv_path = d / "decision_log.csv"

        # 健康 + JSON 消费端
        csv_path.write_text(header + good, encoding="utf-8")
        rc, out = run(csv_path, "--json", "--max-age-days", "0")
        assert rc == 0, f"健康台账应 EXIT=0，实际 {rc} | {out[:200]}"
        rep = json.loads(out)
        assert rep["verdict"] == "HEALTHY" and rep["entries"] == 1 and rep["exit_code"] == 0

        # 陈旧提醒 / 禁用陈旧检查
        csv_path.write_text(header + old, encoding="utf-8")
        rc, out = run(csv_path, "--json", "--max-age-days", "1")
        assert rc == 6 and json.loads(out)["verdict"] == "STALE", f"陈旧应 EXIT=6: {out[:200]}"
        rc, _ = run(csv_path, "--json", "--max-age-days", "0")
        assert rc == 0, "--max-age-days 0 应禁用陈旧检查"

        # 结构失败：文件缺失 / 缺必需列 / 条目数不足
        rc, out = run(d / "absent.csv", "--json")
        assert rc == 3 and json.loads(out)["verdict"] == "MISSING"
        csv_path.write_text("ts,actor,decision\n" + f"{now},lead,缺列\n", encoding="utf-8")
        rc, out = run(csv_path, "--json")
        assert rc == 3 and json.loads(out)["verdict"] == "SCHEMA_MISSING"
        csv_path.write_text(header + good, encoding="utf-8")
        rc, out = run(csv_path, "--json", "--min-entries", "2")
        assert rc == 3 and json.loads(out)["verdict"] == "TOO_FEW"

        # 内容违规：空必填 / 坏 ts / 非法 tier（三种独立形态）
        for bad_row in (
            f"{now},lead,G2-waiver,,理由,通知档\n",
            "not-a-timestamp,lead,G2-waiver,坏时间,理由,通知档\n",
            f"{now},lead,G2-waiver,坏档位,理由,越权档\n",
        ):
            csv_path.write_text(header + bad_row, encoding="utf-8")
            rc, out = run(csv_path, "--json")
            assert rc == 5 and json.loads(out)["verdict"] == "CONTENT_VIOLATION", \
                f"内容违规应 EXIT=5: {bad_row.strip()} | {out[:200]}"


def test_baseline_anchor_roundtrip() -> None:
    """P2-7（2026-11-09 · 遗留清理轮）：包外基线锚只读对账的退出码契约。

    锁定「双测试文件同覆」的包外兜底：锚一致 → 0；哈希/字节漂移或文件缺失
    → 5；锚畸形（缺 files / 路径逃逸）→ 3；且对账全程**不改包内任何文件**。
    锚路径由 --anchors 传入，测试自包含（不依赖审计区真实锚文件）。
    """
    script = PKG / "scripts" / "check_baseline_anchors.py"
    rels = ("tests/test_contract_guard.py", "tests/test_vendor_core.py",
            "tests/test_gate_fuzz.py", "scripts/check_gates.py")
    before = {r: (PKG / r).read_bytes() for r in rels}

    def fresh_files() -> dict:
        return {
            r: {"sha256": hashlib.sha256((PKG / r).read_bytes()).hexdigest(),
                "bytes": (PKG / r).stat().st_size}
            for r in rels
        }

    with tempfile.TemporaryDirectory(prefix="baseline_anchor_") as td:
        anchor = Path(td) / "anchors.json"

        def run(obj) -> tuple[int, dict]:
            anchor.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            p = subprocess.run(
                [sys.executable, str(script), "--anchors", str(anchor), "--json"],
                capture_output=True, text=True, timeout=60)
            out = p.stdout + p.stderr
            assert "Traceback" not in out, f"对账脚本崩溃: {out[:300]}"
            try:
                rep = json.loads(out)
            except json.JSONDecodeError:
                raise AssertionError(f"--json 输出不可解析: {out[:300]}")
            return p.returncode, rep

        base = {"schema_version": 1, "generated": "2026-11-09T00:00:00",
                "source": {"tag": "v1.5.8", "note": "self-contained test"},
                "files": fresh_files()}
        rc, rep = run(base)
        assert rc == 0 and rep["verdict"] == "OK" and rep["matched"] == len(rels), \
            f"一致锚应 EXIT=0: rc={rc} rep={rep}"

        # R4.1（backlog B）：commit 与 HEAD 不一致属契约表「漂移」→ EXIT=5（非 3），
        # 且继续 files 对账（expected>0），不再提前 return 丢失明细。
        bad_commit = json.loads(json.dumps(base, ensure_ascii=False))
        bad_commit["source"]["commit"] = "0" * 40
        rc, rep = run(bad_commit)
        assert rc == 5 and rep["verdict"] == "DRIFT" \
            and any("commit" in e for e in rep.get("drift_errors", [])) \
            and rep["expected"] == len(rels), \
            f"commit 漂移应 EXIT=5 且继续对账: rc={rc} rep={rep}"

        tampered = json.loads(json.dumps(base, ensure_ascii=False))
        tampered["files"][rels[0]]["sha256"] = "0" * 64
        rc, rep = run(tampered)
        assert rc == 5 and rep["verdict"] == "DRIFT" \
            and any(m["path"] == rels[0] for m in rep["mismatched"]), \
            f"哈希漂移应 EXIT=5: rc={rc} rep={rep}"

        absent = json.loads(json.dumps(base, ensure_ascii=False))
        absent["files"]["scripts/does_not_exist.py"] = {"sha256": "0" * 64, "bytes": 1}
        rc, rep = run(absent)
        assert rc == 5 and "scripts/does_not_exist.py" in rep["missing"], \
            f"文件缺失应判漂移 EXIT=5: rc={rc} rep={rep}"

        rc, rep = run({"schema_version": 1})
        assert rc == 3 and rep["verdict"] == "ANCHOR_SCHEMA_INVALID", \
            f"缺 files 应 EXIT=3: rc={rc} rep={rep}"
        rc, rep = run({"schema_version": 1,
                       "files": {"../escape.py": {"sha256": "0" * 64, "bytes": 1}}})
        assert rc == 3 and rep["verdict"] == "ANCHOR_SCHEMA_INVALID", \
            f"路径逃逸应 EXIT=3: rc={rc} rep={rep}"

    assert all((PKG / r).read_bytes() == b for r, b in before.items()), \
        "对账脚本改动了包内文件（只读契约被破坏）"


    # R4.20（盲检 A🔴3 / B🔴3 / A🟠10）：set_defaults 翻转、cli_sites
    # 白名单内子集缩水、schema_version bool 均须 fail-closed。
    with tempfile.TemporaryDirectory(prefix="drec_r420_") as td:
        d = Path(td)
        (d / "scripts").mkdir(); (d / "tests").mkdir()
        base = json.loads((PKG / "docs" / "decision_records.json").read_text(encoding="utf-8"))
        art = next(r for r in base["records"]
                   if r["verification"]["rule"] == "require_tag_default_off")
        base["records"] = [art]
        pj = d / "records.json"
        for name in ("check_gates.py", "verify_numbers.py", "verify_member_output.py"):
            (d / "scripts" / name).write_text(
                'ap.add_argument("--require-tag", action="store_true")\n', encoding="utf-8")
        (d / "tests" / "anchors.py").write_text(
            "# test_require_tag_gate\n# require_tag 闸三点接线存活\n", encoding="utf-8")
        pj.write_text(json.dumps(base), encoding="utf-8")
        drec = PKG / "scripts" / "check_decision_records.py"
        def drc():
            return subprocess.run([sys.executable, str(drec), "--pkg-root", str(d),
                                   "--records", str(pj), "--json"],
                                  capture_output=True, text=True).returncode
        assert drc() == 0, "R4.20 未翻转裁决基线须 OK"
        (d / "scripts" / "verify_numbers.py").write_text(
            'ap.add_argument("--require-tag", action="store_true")\n'
            'ap.set_defaults(require_tag=True)\n', encoding="utf-8")
        assert drc() == 5, "R4.20 set_defaults(require_tag=True) 须 VIOLATION"
        (d / "scripts" / "verify_numbers.py").write_text(
            'ap.add_argument("--require-tag", action="store_true", default=True)\n',
            encoding="utf-8")
        art["verification"]["cli_sites"] = ["scripts/check_gates.py"]
        pj.write_text(json.dumps(base), encoding="utf-8")
        assert drc() == 3, "R4.20 cli_sites 子集须结构错误"
        art["verification"]["cli_sites"] = ["scripts/check_gates.py",
                                            "scripts/verify_numbers.py",
                                            "scripts/verify_member_output.py"]
        base["schema_version"] = True
        pj.write_text(json.dumps(base), encoding="utf-8")
        assert drc() == 3, "R4.20 schema_version true 须结构错误"


    # R4.20（盲检 A🟠11）：删除锚 source 字段不得绕过 commit 溯源校验。
    with tempfile.TemporaryDirectory(prefix="anchor_r420_") as td:
        d = Path(td)
        anchor = d / "anchors.json"
        anchor.write_text(json.dumps({"schema_version": 1,
                                      "files": {"scripts/_text_guard.py": {
                                          "sha256": "0" * 64, "bytes": 1}}}), encoding="utf-8")
        r = subprocess.run([sys.executable, str(PKG / "scripts" / "check_baseline_anchors.py"),
                            "--anchors", str(anchor), "--json"], capture_output=True, text=True)
        rep = json.loads(r.stdout)
        assert r.returncode == 3 and rep["verdict"] == "ANCHOR_SOURCE_INVALID", \
            f"R4.20 锚 source 缺失须结构错误，实为 rc={r.returncode} rep={rep}"

    # R4.21（盲检 B🔴5）：source={} / commit=null / commit="" 借假值跳过
    # commit 溯源——须与「删掉 source」同口径 EXIT=3。
    with tempfile.TemporaryDirectory(prefix="r421_anch_") as td:
        d = Path(td)
        rel = "tests/test_vendor_core.py"
        entry = {"sha256": hashlib.sha256((PKG / rel).read_bytes()).hexdigest(),
                 "bytes": (PKG / rel).stat().st_size}
        for src in ({}, {"commit": None}, {"commit": ""}):
            anchor = d / "a.json"
            anchor.write_text(json.dumps({"schema_version": 1, "source": src,
                                          "files": {rel: entry}}, ensure_ascii=False),
                              encoding="utf-8")
            rc = subprocess.run([sys.executable, str(PKG / "scripts" / "check_baseline_anchors.py"),
                                 "--anchors", str(anchor), "--json"],
                                capture_output=True, text=True).returncode
            assert rc == 3, f"R4.21 锚 source={src!r} 无溯源字段须 EXIT=3"


def test_decision_records_guard() -> None:
    """ADR-001（v1.5.9）：裁决必须有机器消费端，且「翻转默认值」会被抓住。

    fixture 隔离：复制最小包结构到 /tmp，不碰真包。三种形态：
      正常 → EXIT=0；给 CLI 加 default=True → EXIT=5/VIOLATION；
      删裁决文件 → EXIT=3。防「文档还写着保持关闭、代码已悄悄翻转」。
    """
    script = PKG / "scripts" / "check_decision_records.py"
    rels = [
        "scripts/check_gates.py", "scripts/verify_numbers.py",
        "scripts/verify_member_output.py", "scripts/verify_evidence_check.py",
        "scripts/reconcile_decisions.py", "scripts/check_baseline_anchors.py",
    ]
    anchors = ("test_require_tag_gate", "require_tag 闸三点接线存活",
               "test_g6_evidence_gate", "test_anchor_refresh_guard",
               "test_reconcile_decisions")
    with tempfile.TemporaryDirectory(prefix="adr_guard_") as td:
        root = Path(td) / "pkg"
        (root / "scripts").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "tests").mkdir()
        for rel in rels:
            (root / rel).write_bytes((PKG / rel).read_bytes())
        (root / "docs" / "decision_records.json").write_bytes(
            (PKG / "docs" / "decision_records.json").read_bytes())
        (root / "tests" / "anchors.py").write_text(
            "# 测试锚存活占位\n" + "".join(f"# {a}\n" for a in anchors), encoding="utf-8")

        def run() -> tuple[int, dict]:
            p = subprocess.run(
                [sys.executable, str(script), "--pkg-root", str(root), "--json"],
                capture_output=True, text=True, timeout=60)
            assert "Traceback" not in p.stdout + p.stderr, "裁决守卫崩溃"
            return p.returncode, json.loads(p.stdout)

        rc, rep = run()
        assert rc == 0 and rep["verdict"] == "OK" and rep["checked"] >= 4, \
            f"正常形态应 EXIT=0: rc={rc} rep={rep}"

        cg = root / "scripts" / "check_gates.py"
        src = cg.read_text(encoding="utf-8")
        assert 'action="store_true"' in src
        cg.write_text(src.replace('action="store_true"', 'action="store_true", default=True', 1),
                      encoding="utf-8")
        rc, rep = run()
        assert rc == 5 and rep["verdict"] == "VIOLATION" \
            and any("default=True" in v for v in rep["violations"]), \
            f"默认值被翻转应 EXIT=5: rc={rc} rep={rep}"

        # R4.18（盲检🔴7）：形态锚正则须在归一化源码上匹配——全角等号
        # `default＝True`（U+FF1D）翻转默认值同样须 EXIT=5。
        cg.write_text(src.replace('action="store_true"', 'action="store_true", default\uff1dTrue', 1),
                      encoding="utf-8")
        rc, rep = run()
        assert rc == 5 and rep["verdict"] == "VIOLATION", \
            f"R4.18 全角等号翻转默认值须 EXIT=5: rc={rc} rep={rep}"

        (root / "docs" / "decision_records.json").unlink()
        rc, rep = run()
        assert rc == 3 and rep["verdict"] == "RECORDS_UNREADABLE", \
            f"裁决文件消失应 EXIT=3: rc={rc} rep={rep}"

        # R4.3（盲检🔴4）：cli_sites / tests 元素非字符串须记结构错误 EXIT=3，
        # 不得 TypeError 崩溃 EXIT=1（契约仅 0/3/5）。
        dr = root / "docs" / "decision_records.json"
        base_rec = {"id": "ADR-R43", "title": "t", "status": "accepted",
                    "decided_at": "2026-01-01", "decision": "d"}
        for field, badval in (("cli_sites", [{"bad": 1}]), ("tests", [123])):
            ver = {"rule": "require_tag_default_off", "cli_sites": [], "tests": ["test_require_tag_gate"]}
            ver[field] = badval
            dr.write_text(json.dumps({"schema_version": 1,
                                      "records": [dict(base_rec, verification=ver)]}),
                          encoding="utf-8")
            p = subprocess.run([sys.executable, str(script), "--pkg-root", str(root), "--json"],
                               capture_output=True, text=True, timeout=60)
            assert p.returncode == 3 and "Traceback" not in p.stderr, \
                f"{field} 非字符串元素应结构错误 EXIT=3，实为 {p.returncode}: {p.stderr[-200:]}"

        # R4.13（盲检 B🔴3）：verification.rule 为 list/dict 时 unhashable →
        # `rule not in RULE_ANCHORS` 抛 TypeError → EXIT=1（契约外崩溃）。
        for bad_rule in (["x"], {"k": "v"}):
            ver = {"rule": bad_rule, "cli_sites": ["scripts/check_gates.py"],
                   "tests": ["test_require_tag_gate"]}
            dr.write_text(json.dumps({"schema_version": 1,
                                      "records": [dict(base_rec, verification=ver)]}),
                          encoding="utf-8")
            p = subprocess.run([sys.executable, str(script), "--pkg-root", str(root), "--json"],
                               capture_output=True, text=True, timeout=60)
            assert p.returncode == 3 and "Traceback" not in p.stderr, \
                f"rule 容器 {bad_rule!r} 应结构错误 EXIT=3，实为 {p.returncode}: {p.stderr[-200:]}"

        # R4.22（盲检 A🔴6/B🔴2）：default 真值别名（1 / 变量）与 default=True
        # 语义等价地把 ADR-001 默认值翻成 ON，字面形态锚零命中。复用本 fixture
        # 的完整裁决记录：恢复 records → 三处 CLI 恢复 → 仅把 check_gates.py
        # 的 store_true 改 default=1 → 须 EXIT=5/VIOLATION。
        dr.write_bytes((PKG / "docs" / "decision_records.json").read_bytes())
        cg = root / "scripts" / "check_gates.py"
        cg.write_bytes((PKG / "scripts" / "check_gates.py").read_bytes())
        src = cg.read_text(encoding="utf-8")
        cg.write_text(src.replace('action="store_true",\n                    help="严审模式',
                                  'action="store_true", default=1,\n                    help="严审模式', 1),
                      encoding="utf-8")
        rc, rep = run()
        assert rc == 5 and rep["verdict"] == "VIOLATION", \
            f"R4.22 A6 default=1 真值别名须 EXIT=5: rc={rc} rep={rep}"

        # R4.3（盲检🟠A）：契约正本/SKILL 文件缺失不得被静默跳过却输出
        # 「全员契约完整」虚假 PASS（删文件反而 PASS、留空文件反而 FAIL）。
        import shutil
        vcroot = Path(td) / "vcpkg"
        (vcroot / "scripts").mkdir(parents=True)
        (vcroot / "agents").mkdir()
        (vcroot / "skills" / "viral-evo-core").mkdir(parents=True)
        (vcroot / ".codebuddy-plugin").mkdir()
        (vcroot / ".claude-plugin").mkdir()
        shutil.copy(PKG / "scripts" / "validate_contracts.py", vcroot / "scripts" / "validate_contracts.py")
        (vcroot / ".codebuddy-plugin" / "plugin.json").write_text('{"version":"1.0"}', encoding="utf-8")
        (vcroot / ".claude-plugin" / "plugin.json").write_text('{"version":"1.0"}', encoding="utf-8")
        (vcroot / "agents" / "foo.md").write_text(
            "result_envelope 能力边界 路由判定表", encoding="utf-8")
        (vcroot / "skills" / "viral-evo-core" / "SKILL.md").write_text(
            "assemble_spawn_prompt 数字必溯源 禁项目叙事 GOVERNANCE_BOUNDARIES 主理人 team-lead",
            encoding="utf-8")
        # 故意不创建 skills/viral-evo-core/references/team-contract.md
        p = subprocess.run([sys.executable, str(vcroot / "scripts" / "validate_contracts.py")],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 5, \
            f"契约正本缺失须 EXIT=5（不得虚假 PASS），实为 {p.returncode}"
        assert "全员契约完整" not in p.stdout, \
            "契约正本缺失时不得输出「全员契约完整」虚假结论"

        # R4.6（两路盲检结构🔴）：六项结构缺陷回归，全部复用本函数（零新增函数）。
        # ① validate_contracts 删光 agents 后不得虚假 PASS：副本清空 agents/*.md
        vcempty = root / "vc_empty"
        if vcempty.exists():
            shutil.rmtree(vcempty, ignore_errors=True)
        shutil.copytree(vcroot, vcempty)
        for ag in (vcempty / "agents").glob("*.md"):
            ag.unlink()
        p = subprocess.run([sys.executable, str(vcempty / "scripts" / "validate_contracts.py")],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 5 and "成员层不齐" in p.stdout, \
            f"agents 全删须 EXIT=5 且明示不齐，实为 rc={p.returncode}"

        # ② check_scope：md 标题行隐藏事故数字不得判 clean（须 EXIT=3）
        cs = PKG / "scripts" / "check_scope.py"
        hidden = root / "scope_hidden.md"
        hidden.write_text("# 事故复盘：PP 41034380 位置映射错误\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(cs), str(hidden)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"md 标题隐藏事故数字须 EXIT=3，实为 {rc}"
        # R4.8（盲检 A🟠2/B🟠4）：治理正本豁免改为包内规范路径精确匹配。
        # 任意副本目录的同名文件不得借 basename 骗取豁免（须 EXIT=3）。
        gov = root / "GOVERNANCE_BOUNDARIES.md"
        gov.write_text("# 黑名单词说明：PP 41034380 是事故编号\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(cs), str(gov)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"副本同名治理文件不得豁免，实为 {rc}"

        # ③ hypothesis_watch：closed fatal 空日期 / 尾空格 severity 均须进 REVIEW_REQUIRED
        hw = PKG / "scripts" / "hypothesis_watch.py"
        hro = root / "hwro"
        (hro / "context_stack").mkdir(parents=True, exist_ok=True)
        (hro / "00_governance").mkdir(parents=True, exist_ok=True)
        (hro / "context_stack" / "confirmed_hypotheses.json").write_text(
            '{"last_updated":"2026-11-01T00:00:00+08:00",'
            '"active_hypotheses":[{"id":"H1","status":"active","claim":"x"}]}',
            encoding="utf-8")
        for label, csv_line in (
                ("空日期", "F1,severe,closed,,\"证伪发现\""),
                ("尾空格", "F2,\"fatal \",closed,2026-11-20,\"证伪发现\"")):
            (hro / "00_governance" / "redteam_ledger.csv").write_text(
                "finding_id,severity,status,closed_date,closed_summary\n" + csv_line + "\n",
                encoding="utf-8")
            p = subprocess.run([sys.executable, str(hw), "--research-ops", str(hro)],
                               capture_output=True, text=True, timeout=60)
            assert p.returncode in (5, 6) and "REVIEW_REQUIRED" in p.stdout, \
                f"{label} fatal/severe 须进 REVIEW_REQUIRED，实为 rc={p.returncode}"
        # R4.18（盲检🔴5）：severity 同形字（全角 ＦＡＴＡＬ / 西里尔 faтal /
        # 组合音标 fataĺ）经 .lower() 不收敛 ASCII → fatal 证伪发现漏报。
        for label, sev in (("全角FATAL", "\uff26\uff21\uff34\uff21\uff2c"),
                           ("西里尔т", "fa\u0442al"), ("组合Mn", "fatal\u0301")):
            (hro / "00_governance" / "redteam_ledger.csv").write_text(
                "finding_id,severity,status,closed_date,closed_summary\n"
                f"F3,{sev},closed,2026-11-20,\"证伪发现\"\n", encoding="utf-8")
            p = subprocess.run([sys.executable, str(hw), "--research-ops", str(hro)],
                               capture_output=True, text=True, timeout=60)
            assert p.returncode in (5, 6) and "REVIEW_REQUIRED" in p.stdout, \
                f"R4.18 {label} 须进 REVIEW_REQUIRED，实为 rc={p.returncode}"

        # ④ poll_run_dir：200k 之后的撞限标注不得 READY（全文扫描无截断）
        poll = PKG / "scripts" / "poll_run_dir.py"
        prun = root / "poll_big"
        prun.mkdir(exist_ok=True)
        (prun / "T-BIG__alice.md").write_text(
            "A" * 200100 + "\n<!-- 轮次耗尽，产出不完整 -->\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(poll), str(prun), "T-BIG", "--expected", "alice"],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 5 and "NOT_READY" in p.stdout, \
            f"200k 后撞限标注须 NOT_READY，实为 rc={p.returncode}"

        # ⑤ cron_watch：陈旧锁分支不得 unbound variable EXIT=1（契约 0/3/5）
        watch = PKG / "scripts" / "cron_watch.sh"
        crun, cstate = root / "cron_r", root / "cron_s"
        crun.mkdir(exist_ok=True); cstate.mkdir(exist_ok=True)
        (cstate / ".cron_watch.lock").write_text("stale\n", encoding="utf-8")
        p = subprocess.run(["bash", str(watch), "--run-dir", str(crun), "--state-dir", str(cstate)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode in (0, 3, 5) and "unbound variable" not in p.stderr, \
            f"陈旧锁须契约内退出，实为 rc={p.returncode}: {p.stderr[-120:]}"

        # ⑥ assemble V1：0.94 不得被权威池 0.9441 子串洗白（须告警未溯源）
        asmo = root / "asm_ro"
        (asmo / "context_stack" / "outputs").mkdir(parents=True, exist_ok=True)
        (asmo / "context_stack" / "outputs" / "auth.csv").write_text("p,0.9441\n", encoding="utf-8")
        asmt = root / "asm_task.md"
        asmt.write_text("objective: 核验\np = 0.94\noutput_format: md\n"
                        "constraints: 无\ntask_boundary: 无\n", encoding="utf-8")
        env = dict(os.environ, RESEARCH_OPS_DIR=str(asmo))
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                            "--member", "phylo-analyst", "--task-file", str(asmt),
                            "--out", str(root / "asm_out.md")],
                           capture_output=True, text=True, timeout=60, env=env)
        assert "未溯源数字" in p.stdout + p.stderr, \
            "0.94 不得被 0.9441 子串洗白，须 V1 告警未溯源"

        # R4.11（主代理自查）：V1 降级路径（verify_numbers 模块加载失败）不得
        # 重新引入 fail-open——含声明却零提取仍须告警，合法文本不误报。
        probe = root / "v1_degrade_probe.py"
        probe.write_text(
            "import importlib.util,sys\n"
            "from pathlib import Path\n"
            "spec=importlib.util.spec_from_file_location('asp',sys.argv[1])\n"
            "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n"
            "m._load_verify_numbers=lambda: None\n"
            "r=m._auto_verify_payload(Path('/tmp'),sys.argv[2],sys.argv[3])\n"
            "print(len(r['unverified']))\n", encoding="utf-8")
        v1src = root / "v1_degrade_src"
        (v1src / "context_stack" / "outputs").mkdir(parents=True, exist_ok=True)
        (v1src / "context_stack" / "outputs" / "auth.csv").write_text(
            "n,30\np,0.05\n", encoding="utf-8")
        for label, payload, want_alert in (("攻击", "p = 0,94", True),
                                           ("合法", "样本 n = 30，p = 0.05", False)):
            pr = subprocess.run([sys.executable, str(probe),
                                 str(PKG / "scripts" / "assemble_spawn_prompt.py"),
                                 payload, str(v1src)],
                                capture_output=True, text=True, timeout=60)
            assert pr.returncode == 0, f"V1 降级探针崩溃: {pr.stderr[-300:]}"
            n_alert = int(pr.stdout.strip().splitlines()[-1])
            assert (n_alert > 0) == want_alert, \
                f"V1 降级{label}告警数={n_alert}，期望告警={want_alert}"

        # ⑦ R4.7 盲检 B🔴2：G2 必须与守卫同口径复用 prepare_numbers 的归一化结果。
        # 原第二循环用 extract_numbers(原始文本) → 全角 ｎ＝９９ 在守卫处通过、
        # 实际提取零命中 → check_gates 误判 PASS。修复后须 EXIT=5。
        g2src = root / "g2src"
        g2src.mkdir(exist_ok=True)
        (g2src / "a.csv").write_text("source_tag: authoritative\nn = 30\n", encoding="utf-8")
        g2run = root / "g2run"
        g2rd = g2run / TASK_ID
        g2rd.mkdir(parents=True)
        (g2rd / f"{TASK_ID}__phylo-analyst.md").write_text(
            json.dumps(BASE_ENV, ensure_ascii=False)
            + "\n\n样本量 ｎ＝９９（全角，权威源无 99）\n", encoding="utf-8")
        (g2rd / f"{TASK_ID}__checklist.json").write_text('{"verdict": "PASS"}', encoding="utf-8")
        subprocess.run([sys.executable, str(PKG / "scripts" / "verify_member_output.py"),
                        str(g2rd), TASK_ID, "--sources", str(g2src)],
                       capture_output=True, text=True, timeout=60)
        p = subprocess.run([sys.executable, str(CHECK_GATES), str(g2rd), TASK_ID,
                            "--sources", str(g2src)], capture_output=True, text=True, timeout=90)
        assert p.returncode == 5, f"G2 全角声明不得绕过（须 EXIT=5），实为 {p.returncode}"

        # ⑧ R4.7 盲检 B🟠2：check_scope 治理正本豁免须文件名精确相等，
        # 目录名 `GOVERNANCE_BOUNDARIES.md_evil` 不再享受注释行豁免。
        scope_evil = root / "GOVERNANCE_BOUNDARIES.md_evil"
        scope_evil.mkdir(exist_ok=True)
        evil_md = scope_evil / "evil.md"
        evil_md.write_text("# 复盘：PP 41034380\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(PKG / "scripts" / "check_scope.py"), str(evil_md)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 3, f"伪治理目录的标题叙事不得豁免（须 EXIT=3），实为 {p.returncode}"

        # ⑨ R4.8（盲检 A🔴2）：>4300 位整数使 json.loads 抛 ValueError（非
        # JSONDecodeError），原 except 漏捕获 → 契约外 EXIT=1 且报告不落盘。
        big = "9" * 5000
        (root / "spawn_manifest.jsonl").write_text(
            '{"event":"evidence_check","actor":"lead","value":%s}\n' % big, encoding="utf-8")
        rc = subprocess.run([sys.executable, str(PKG / "scripts" / "verify_evidence_check.py"),
                             str(root)], capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"超大整数 JSON 须结构失败 EXIT=3（不得契约外 1），实为 {rc}"
        rc = subprocess.run([sys.executable, str(script), "--records",
                             str(root / "spawn_manifest.jsonl"), "--pkg-root", str(root)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"decision_records 超大整数须 EXIT=3，实为 {rc}"
        # ⑩ R4.8（盲检 A🔴3）：check_scope 的 \b 在 CJK 紧邻处不成立，
        # 具体事故值「1094号」「0.2058的」须照常命中 EXIT=3。
        scope_cjk = root / "scope_cjk.md"
        scope_cjk.write_text("事故编号1094号与错误值0.2058的复盘。\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(cs), str(scope_cjk)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"CJK 紧邻事故值须命中 EXIT=3，实为 {rc}"
        # ⑪ R4.8（盲检 A🟠1）：cron_watch 参数缺值不得在 set -u 下 unbound EXIT=1。
        rc = subprocess.run(["bash", str(PKG / "scripts" / "cron_watch.sh"), "--run-dir"],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"cron 参数缺值须参数错误 EXIT=3，实为 {rc}"

        # R4.9（盲检 B🟠3 + 主代理自查）：超大整数 JSON（>4300 位）使 json.loads
        # 抛 ValueError，多处入口漏捕获 → 契约外 EXIT=1。统一扩捕获面后须落契约码。
        big9 = "9" * 5000
        va = root / "anchors_big.json"
        va.write_text('{"files":{},"source":{"tag":%s}}' % big9, encoding="utf-8")
        rc = subprocess.run([sys.executable, str(PKG / "scripts" / "check_baseline_anchors.py"),
                             "--anchors", str(va)],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"锚文件超大整数须结构失败 EXIT=3，实为 {rc}"
        ctx = root / "ro" / "context_stack"
        ctx.mkdir(parents=True, exist_ok=True)
        (ctx / "confirmed_hypotheses.json").write_text('{"last_updated":%s}' % big9,
                                                        encoding="utf-8")
        rc = subprocess.run([sys.executable, str(PKG / "scripts" / "render_context_stack.py"),
                             "--research-ops", str(root / "ro"), "--which", "hyp"],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"上下文真源超大整数须结构失败 EXIT=3，实为 {rc}"

        # R4.10（盲检 A🟠6/7）：check_scope 事故值全角归一化；cron manifest
        # 含 task_id 字段却全非法时须 fail-closed（不得静默 exit 0）。
        sc_full = root / "scope_fullwidth.md"
        sc_full.write_text("# 编号１０９４号 错误值０．２０５８的复盘\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(PKG / "scripts" / "check_scope.py"),
                             str(sc_full)], capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"全角事故值须归一化命中 EXIT=3，实为 {rc}"
        crun = root / "cron_bad"; crun.mkdir(exist_ok=True)
        (crun / "spawn_manifest.jsonl").write_text('{"task_id":12345}\n', encoding="utf-8")
        rc = subprocess.run(["bash", str(PKG / "scripts" / "cron_watch.sh"),
                             "--run-dir", str(crun), "--state-dir", str(root / "cstate_bad")],
                            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"非法 task_id 须 fail-closed EXIT=3，实为 {rc}"

        # R4.19（盲检 A🔴2）：cli_sites 指向无锚文件不得跳过形态锚检查——
        # 须记结构错误 EXIT=3（拒绝借改裁决 JSON 的 cli_sites 缩水检查范围）。
        drec_root = root / "drec_r419"
        (drec_root / "scripts").mkdir(parents=True, exist_ok=True)
        (drec_root / "tests").mkdir(exist_ok=True)
        (drec_root / "scripts" / "dummy.py").write_text("# no anchors\n", encoding="utf-8")
        (drec_root / "tests" / "anchors.py").write_text(
            "# test_require_tag_gate\n", encoding="utf-8")
        bad_rec = {"schema_version": 1, "records": [{
            "id": "ADR-X", "title": "t", "status": "accepted",
            "decided_at": "2026-01-01", "decision": "d",
            "verification": {"rule": "g6_opt_in_visible",
                             "cli_sites": ["scripts/dummy.py"],
                             "tests": ["test_require_tag_gate"]}}]}
        rec_path = root / "drec_r419.json"
        rec_path.write_text(json.dumps(bad_rec), encoding="utf-8")
        rc = subprocess.run(
            [sys.executable, str(PKG / "scripts" / "check_decision_records.py"),
             "--pkg-root", str(drec_root), "--records", str(rec_path), "--json"],
            capture_output=True, text=True, timeout=60).returncode
        assert rc == 3, f"R4.19 cli_sites 无锚文件须结构错误 EXIT=3，实为 {rc}"

        # R4.19（盲检 A🔴1/B🔴3/B🔴4）：check_scope 数字紧凑投影——中文句号
        # 小数点、千分位逗号使事故值/PMID/commit 黑名单永假须全部命中 EXIT=3。
        for text in ("事故错误值 20。58% 已确认\n", "状态：v6。6 草稿 未发布\n",
                     "备份 file。pre-backup-2026\n", "事故编号 PP 41,034,380，详见\n",
                     "事故 commit 1,094，详见\n"):
            sc = root / "scope_compact.md"
            sc.write_text(text, encoding="utf-8")
            rc = subprocess.run([sys.executable, str(PKG / "scripts" / "check_scope.py"),
                                 str(sc)], capture_output=True, text=True, timeout=60).returncode
            assert rc == 3, f"R4.19 数字紧凑投影须命中 EXIT=3: {text!r}"


    # R4.20（盲检 A🔴4 / B🔴4）：U+2800 / 私用区视觉空白不得凑满 G6，
    # R4.19 已修的 U+115F 与 Cf 须继续 fail-closed。
    with tempfile.TemporaryDirectory(prefix="g6_r420_") as td:
        d = Path(td)
        mf = d / "spawn_manifest.jsonl"
        def g6rc(ch):
            mf.write_text("".join(
                json.dumps({"event": "evidence_check", "actor": "lead", "task_id": "T-X",
                            "reason": ch * 4,
                            "value": {"file": "src.md", "line": i + 1,
                                      "excerpt": ch * 6}}, ensure_ascii=False) + "\n"
                for i in range(2)), encoding="utf-8")
            return subprocess.run([sys.executable,
                                   str(PKG / "scripts" / "verify_evidence_check.py"),
                                   str(d), "--json"], capture_output=True, text=True).returncode
        for ch in ("\u2800", "\ue000", "\u115f", "\u200b"):
            assert g6rc(ch) == 5, f"R4.20 G6 视觉空白 {ch!r} 须 EXIT=5"

    # R4.21（盲检 A🔴4/B🔴2/B🔴6）：check_scope 目录递归 / drec default 括号 /
    # 多语千分位分隔符投影，四处 fail-open 回归。
    with tempfile.TemporaryDirectory(prefix="r421_scope_") as td:
        d = Path(td)
        poison = d / "poison"; poison.mkdir()
        (poison / "evil.md").write_text("# 复盘\n具体 PMID PP 41034380\n", encoding="utf-8")
        src = subprocess.run([sys.executable, str(PKG / "scripts" / "check_scope.py"),
                              str(poison)], capture_output=True, text=True).returncode
        assert src == 3, "R4.21 check_scope 传目录须递归检查 EXIT=3"
        for txt in ("事故编号 PP 41\u066c034\u066c380\n", "事故编号 PP 41\u066b034380\n",
                    "事故编号 PP 41\u30fb034\u30fb380\n"):
            (poison / "evil.md").write_text(txt, encoding="utf-8")
            src = subprocess.run([sys.executable, str(PKG / "scripts" / "check_scope.py"),
                                  str(poison / "evil.md")], capture_output=True, text=True).returncode
            assert src == 3, f"R4.21 多语分隔符投影 {txt!r} 须 EXIT=3"
    with tempfile.TemporaryDirectory(prefix="r421_drec_") as td:
        d = Path(td); (d / "scripts").mkdir(); (d / "tests").mkdir()
        records = json.loads((PKG / "docs" / "decision_records.json").read_text(encoding="utf-8"))
        art = next(r for r in records["records"]
                   if r["verification"]["rule"] == "require_tag_default_off")
        records["records"] = [art]
        (d / "records.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        (d / "tests" / "anchors.py").write_text(
            "# test_require_tag_gate\n# require_tag 闸三点接线存活\n", encoding="utf-8")
        for fn in ("check_gates.py", "verify_numbers.py", "verify_member_output.py"):
            (d / "scripts" / fn).write_text(
                'ap.add_argument("--require-tag", action="store_true", default=(True))\n',
                encoding="utf-8")
        rc = subprocess.run([sys.executable, str(PKG / "scripts" / "check_decision_records.py"),
                             "--pkg-root", str(d), "--records", str(d / "records.json"),
                             "--json"], capture_output=True, text=True).returncode
        assert rc == 5, "R4.21 default=(True) 括号包裹须 EXIT=5"


def test_g6_evidence_gate() -> None:
    """ADR-002 / SOP T-D1：G6 从软门变成可触发硬门，且 SKIP 必须留痕。"""
    script = PKG / "scripts" / "verify_evidence_check.py"

    def ev(line: int, **kw) -> str:
        obj = {"event": "evidence_check", "actor": "lead", "task_id": TASK_ID,
               "reason": "要害证据抽查",
               "value": {"file": "sources/a.md", "line": line, "excerpt": "原文 1-2 行摘录"}}
        obj.update(kw)
        return json.dumps(obj, ensure_ascii=False)

    def run_v(path: Path, *args: str) -> tuple[int, dict]:
        p = subprocess.run([sys.executable, str(script), str(path), *args, "--json"],
                           capture_output=True, text=True, timeout=60)
        assert "Traceback" not in p.stdout + p.stderr, "G6 硬门崩溃"
        return p.returncode, json.loads(p.stdout)

    with tempfile.TemporaryDirectory(prefix="g6_gate_") as td:
        d = Path(td)
        rd = d / "run"
        rd.mkdir()
        man = rd / "spawn_manifest.jsonl"

        # 独立硬门：合格 / 不足 / actor 非 lead / 缺摘录 / 缺 reason / 字符串 value / 坏 JSON
        man.write_text(ev(10) + "\n" + ev(20) + "\n", encoding="utf-8")
        rc, rep = run_v(rd)
        assert rc == 0 and rep["valid"] == 2 and rep["verdict"] == "PASS", f"合格应 PASS: {rep}"
        for bad_lines, label in (
            (ev(10), "仅 1 条"),
            (ev(10, actor="member") + "\n" + ev(20), "actor 非 lead"),
            (ev(10, value={"file": "a.md", "line": 10}) + "\n" + ev(20), "缺摘录"),
            (ev(10, reason="") + "\n" + ev(20), "缺 reason"),
            (ev(10, value="a.md:10") + "\n" + ev(20), "字符串 value"),
        ):
            man.write_text(bad_lines + "\n", encoding="utf-8")
            rc, rep = run_v(rd)
            assert rc == 5 and rep["verdict"] == "FAIL", f"{label} 应 FAIL: rc={rc} rep={rep}"
        man.write_text("{not json}\n", encoding="utf-8")
        rc, rep = run_v(rd)
        assert rc == 3 and rep["verdict"] == "MANIFEST_INVALID", f"坏 JSON 应 EXIT=3: {rep}"
        # R4.14（盲检 A🔴7）：bool 是 int 子类，line=true 曾被当合法行号 →
        # 两条畸形抽查仍判 PASS（valid=2）。须显式排除 bool → FAIL/EXIT=5。
        man.write_text(ev(True) + "\n" + ev(True) + "\n", encoding="utf-8")
        rc, rep = run_v(rd)
        assert rc == 5 and rep["valid"] == 0, \
            f"line=true 须判非行号 FAIL，实为 rc={rc} valid={rep.get('valid')}"
        # R4.18（盲检🔴8）：Cf 零宽字符凭空满足「有 reason」+ line 值域
        # （-1/0 非正数行号）→ 空壳抽查 through。须 FAIL/EXIT=5。
        for label, kw in (("reason ZWSP", {"reason": "\u200b"}),
                          ("excerpt ZWSP", {"value": {"file": "a.md", "line": 10,
                                                      "excerpt": "\u200b"}}),
                          ("line -1", {"value": {"file": "a.md", "line": -1,
                                                 "excerpt": "原文"}}),
                          ("line 0", {"value": {"file": "a.md", "line": 0,
                                                "excerpt": "原文"}})):
            man.write_text(ev(10, **kw) + "\n" + ev(20) + "\n", encoding="utf-8")
            rc, rep = run_v(rd)
            assert rc == 5 and rep["verdict"] == "FAIL", \
                f"R4.18 {label} 须 FAIL/EXIT=5，实为 rc={rc} rep={rep}"

        # check_gates 接线：SKIP 留名 / 显式启用 / 策略文件启用 / 启用后不合格判 FAIL
        (rd / f"{TASK_ID}__phylo-analyst.md").write_text(json.dumps(BASE_ENV) + "\n", encoding="utf-8")
        (rd / f"{TASK_ID}__output-check.json").write_text('{"artifact_mtimes": {}}', encoding="utf-8")
        (rd / f"{TASK_ID}__checklist.json").write_text('{"verdict": "PASS"}', encoding="utf-8")

        def run_g(*args: str) -> tuple[int, dict]:
            p = subprocess.run([sys.executable, str(CHECK_GATES), str(rd), TASK_ID, *args],
                               capture_output=True, text=True, timeout=90)
            assert "Traceback" not in p.stdout + p.stderr, "check_gates 崩溃"
            rep = json.loads((rd / f"{TASK_ID}__gates.json").read_text(encoding="utf-8"))
            return p.returncode, rep

        man.write_text(ev(10) + "\n" + ev(20) + "\n", encoding="utf-8")
        _, rep = run_g()
        assert "G6 抽查留痕" in " ".join(rep.get("skipped_gates", [])), \
            "默认未启用必须写进 skipped_gates（禁止静默 PASS）"
        assert not any(g["gate"] == "G6 抽查留痕" for g in rep["gates"]), \
            "SKIP 不得伪装成 gates 里的 PASS"

        _, rep = run_g("--require-evidence-check")
        g6 = [g for g in rep["gates"] if g["gate"] == "G6 抽查留痕"]
        assert len(g6) == 1 and g6[0]["ok"] is True, f"显式启用后应判 PASS: {rep['gates']}"
        assert not rep.get("skipped_gates"), "启用后不应再列 SKIP"

        man.write_text(ev(10) + "\n", encoding="utf-8")
        _, rep = run_g("--require-evidence-check")
        g6 = [g for g in rep["gates"] if g["gate"] == "G6 抽查留痕"]
        assert len(g6) == 1 and g6[0]["ok"] is False and rep["verdict"] == "FAIL", \
            f"记录不足必须 FAIL: {rep['gates']}"

        (rd / "evidence_check_policy.json").write_text('{"enabled": true}', encoding="utf-8")
        _, rep = run_g()
        assert any(g["gate"] == "G6 抽查留痕" for g in rep["gates"]), \
            "策略文件 enabled 应触发 G6"

        # R4.19（盲检 B🔴8）：Hangul Jamo filler（U+115F，Lo 视觉空白）凑满
        # MIN_RECORDS=2 满足 reason/excerpt「非空」→ 空壳 PASS。须剔除 FILLER
        # 后仍有可见字符，纯 filler 记录判不合格 EXIT=5。
        filler = "\u115f"
        def filler_ev(line: int) -> str:
            return json.dumps({"event": "evidence_check", "actor": "lead",
                               "task_id": TASK_ID, "reason": filler * 3,
                               "value": {"file": "src.md", "line": line,
                                         "excerpt": filler * 5}}, ensure_ascii=False)
        man.write_text(filler_ev(1) + "\n" + filler_ev(2) + "\n", encoding="utf-8")
        rc, rep = run_g("--require-evidence-check")
        assert rc == 5 and rep.get("verdict") == "FAIL", \
            f"R4.19 纯 filler 空壳须 EXIT=5 FAIL，实为 rc={rc}: {rep.get('verdict')}"


    # R4.20（盲检 B🔴5）：status 同形字让 fatal 闭环整行隐身，
    # 且与已修 severity 同形构成组合攻击。
    with tempfile.TemporaryDirectory(prefix="hw_r420_") as td:
        d = Path(td)
        (d / "context_stack").mkdir(); (d / "00_governance").mkdir()
        (d / "context_stack" / "confirmed_hypotheses.json").write_text(
            json.dumps({"active_hypotheses": [{"id": "H-1", "status": "active"}],
                        "last_updated": "2026-11-20"}, ensure_ascii=False), encoding="utf-8")
        led = d / "00_governance" / "redteam_ledger.csv"
        hw = PKG / "scripts" / "hypothesis_watch.py"
        def hwrc(sev, status):
            led.write_text("finding_id,severity,status,closed_date,finding_summary\n"
                           f"F-RT,{sev},{status},2026-11-26,证伪\n", encoding="utf-8")
            return subprocess.run([sys.executable, str(hw), "--research-ops", str(d)],
                                  capture_output=True, text=True).returncode
        assert hwrc("fatal", "clo\u0561ed") == 5, "R4.20 status 同形须 REVIEW_REQUIRED"
        assert hwrc("fat\u0430l", "clo\u0561ed") == 5, "R4.20 双字段组合攻击须 REVIEW_REQUIRED"
        assert hwrc("fatal", "closed") == 5, "R4.20 合法 closed 基线须 REVIEW_REQUIRED"

    # R4.21（盲检 A🔴3/B🔴3/B🔴9）：severity/status 任意非 ASCII 字符隔断
    # （Cn/Nd/Po/Zs）须保守计入 REVIEW_REQUIRED，不得 CLEAN。
    with tempfile.TemporaryDirectory(prefix="r421_hw_") as td:
        hw = Path(td)
        (hw / "context_stack").mkdir()
        (hw / "00_governance").mkdir()
        (hw / "context_stack" / "confirmed_hypotheses.json").write_text(json.dumps({
            "active_hypotheses": [{"id": "H-1", "status": "active", "claim": "x"}],
            "last_updated": "2026-11-20"}, ensure_ascii=False), encoding="utf-8")
        led = hw / "00_governance" / "redteam_ledger.csv"
        def hwrc(sev, st):
            led.write_text(f"finding_id,severity,status,closed_date,finding_summary\n"
                           f"F-X,{sev},{st},2026-11-26,证伪\n", encoding="utf-8")
            return subprocess.run([sys.executable, str(PKG / "scripts" / "hypothesis_watch.py"),
                                   "--research-ops", str(hw)],
                                  capture_output=True, text=True).returncode
        for sev, st in (("fatal\u0378", "closed"), ("fatal", "clo\u0378sed"),
                        ("fatal", "clo\u0663ed"), ("fata\u0663", "closed"),
                        ("fatal\u00b7", "closed"), ("fatal", "clo\u00a0sed")):
            assert hwrc(sev, st) == 5, f"R4.21 severity/status 非 ASCII 隔断 {sev!r}/{st!r} 须 EXIT=5"
        assert hwrc("fat\u03b1l", "closed") == 5, "R4.20 希腊字母对照须 EXIT=5"


def test_reconcile_decisions() -> None:
    """ADR-004：语义对账只出候选，绝不代写台账（含拒写同名文件）。"""
    script = PKG / "scripts" / "reconcile_decisions.py"
    header = "ts,actor,decision_type,decision,rationale,tier\n"
    with tempfile.TemporaryDirectory(prefix="reconcile_") as td:
        d = Path(td)
        ledger = d / "decision_log.csv"
        ledger.write_text(header + "2026-11-10T00:00:00+08:00,lead,process,历史裁决,理由,通知档\n",
                          encoding="utf-8")
        rd = d / "run"
        rd.mkdir()
        (rd / f"{TASK_ID}__waivers.json").write_text(
            json.dumps({"waivers": [{"gate": "G2", "value": "79", "reason": "外部引文"}]}),
            encoding="utf-8")
        (rd / f"{TASK_ID}__gates.json").write_text(
            json.dumps({"gates": [{"gate": "G6 抽查留痕", "ok": False, "detail": "记录 0"}],
                        "skipped_gates": ["G6 抽查留痕（默认未强制）"]}), encoding="utf-8")

        def run(*args: str) -> tuple[int, dict]:
            before = ledger.read_bytes()
            p = subprocess.run(
                [sys.executable, str(script), "--run-dirs", str(rd), "--ledger", str(ledger),
                 *args, "--json"], capture_output=True, text=True, timeout=60)
            assert ledger.read_bytes() == before, "对账脚本改写了台账（只读契约被破坏）"
            assert "Traceback" not in p.stdout + p.stderr, "对账脚本崩溃"
            return p.returncode, json.loads(p.stdout)

        rc, rep = run()
        assert rc == 0 and rep["events"] >= 3 and rep["unmatched"], \
            f"应产出待人工终裁候选: rc={rc} rep={rep}"

        draft = d / "DRAFT.csv"
        rc, rep = run("--draft-out", str(draft))
        assert rc == 0 and draft.is_file(), f"草稿应生成: {rep}"
        assert "[DRAFT·待人工终裁]" in draft.read_text(encoding="utf-8"), \
            "草稿必须带不可直落台账的前缀"

        rc, rep = run("--draft-out", str(ledger))
        assert rc == 3 and "拒绝" in " ".join(rep["structural_errors"]), \
            "指向台账必须拒绝: rc={} rep={}".format(rc, rep)
        rc, rep = run("--draft-out", str(d / "decision_log.csv"))
        assert rc == 3, "同名 decision_log.csv 也必须拒绝"


def test_anchor_refresh_guard() -> None:
    """ADR-003：刷新须 ACK + 理由 + 干净 git 仓；防「改锚刷绿」。"""
    script = PKG / "scripts" / "check_baseline_anchors.py"
    with tempfile.TemporaryDirectory(prefix="anchor_refresh_") as td:
        d = Path(td)
        pkg = d / "pkg"
        (pkg / "tests").mkdir(parents=True)
        target = pkg / "tests" / "guard.py"
        target.write_text("v1\n", encoding="utf-8")
        anchor = d / "BASELINE_ANCHORS.json"
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        anchor.write_text(json.dumps({"schema_version": 1,
                                      "source": {"tag": "v0", "commit": "0" * 40, "note": "fixture"},
                                      "files": {"tests/guard.py": {"sha256": sha, "bytes": 3}}}),
                          encoding="utf-8")

        def run(*args: str) -> tuple[int, dict]:
            p = subprocess.run(
                [sys.executable, str(script), "--anchors", str(anchor),
                 "--pkg-root", str(pkg), *args, "--json"],
                capture_output=True, text=True, timeout=60)
            assert "Traceback" not in p.stdout + p.stderr, "锚脚本崩溃"
            return p.returncode, json.loads(p.stdout)

        base = ("--refresh", "--i-acknowledge-refresh", "--reason", "测试刷新理由：新增防线文件")
        # 非 git 仓 → 拒绝；无 ACK / 理由过短 → 拒绝；锚放包内 → 拒绝
        rc, rep = run(*base)
        assert rc == 3 and "git" in " ".join(rep["structural_errors"]), f"非 git 仓应拒绝: {rep}"
        rc, _ = run("--refresh", "--reason", "测试刷新理由足够长")
        assert rc == 3, "缺 ACK 应拒绝"
        rc, _ = run("--refresh", "--i-acknowledge-refresh", "--reason", "短")
        assert rc == 3, "理由过短应拒绝"

        git = lambda *a: subprocess.run(["git", "-C", str(pkg), *a],
                                        capture_output=True, text=True, timeout=60)
        assert git("init", "-q").returncode == 0
        assert git("add", "-A").returncode == 0
        assert git("-c", "user.name=test", "-c", "user.email=test@local",
                   "commit", "-qm", "fixture").returncode == 0
        head = git("rev-parse", "HEAD").stdout.strip()

        inner = pkg / "inner.json"
        inner.write_bytes(anchor.read_bytes())
        p = subprocess.run(
            [sys.executable, str(script), "--anchors", str(inner), "--pkg-root", str(pkg),
             "--refresh", "--i-acknowledge-refresh", "--reason", "测试刷新理由：锚在包内", "--json"],
            capture_output=True, text=True, timeout=60)
        assert p.returncode == 3 and "包外" in p.stdout, "包内锚必须拒绝"
        inner.unlink()  # 清掉夹具，恢复干净工作区（否则后续刷新会被正确拒绝）

        rc, rep = run(*base)
        assert rc == 0 and rep["verdict"] == "REFRESHED" and rep["commit"] == head, \
            f"干净仓应刷新成功: rc={rc} rep={rep}"
        obj = json.loads(anchor.read_text(encoding="utf-8"))
        assert obj["source"]["commit"] == head and len(obj["refresh_history"]) == 1, \
            "刷新必须写 commit 溯源与 history"

        rc, rep = run()
        assert rc == 0 and rep["verdict"] == "OK", f"刷新后应一致: {rep}"
        # 改锚刷绿：把 commit 换成别的 hash（模拟手工改锚）→ check 必须抓住
        obj["source"]["commit"] = "f" * 40
        anchor.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        rc, rep = run()
        # R4.1（backlog B）：commit 不一致按契约表归「漂移」EXIT=5（原错判 3）
        all_errs = rep["structural_errors"] + rep.get("drift_errors", [])
        assert rc == 5 and any("改锚刷绿" in e for e in all_errs), \
            f"改锚刷绿必须被抓: rc={rc} rep={rep}"

        # 工作区 dirty → 拒绝刷新（防把未提交漂移写进基线）
        target.write_text("v2 changed\n", encoding="utf-8")
        obj["source"]["commit"] = head
        anchor.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        rc, rep = run(*base)
        assert rc == 5 and "不干净" in " ".join(rep["structural_errors"]), \
            f"dirty 工作区应拒绝刷新: rc={rc} rep={rep}"


def test_cron_b5_assets() -> None:
    """P4 B-5：cron 资产可执行、dry-run 不改系统调度、巡检结果落盘。"""
    watch = PKG / "scripts" / "cron_watch.sh"
    installer = PKG / "scripts" / "install_cron_watch.sh"
    for sh in (watch, installer):
        p = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, f"{sh.name} 语法错误: {p.stderr}"

    with tempfile.TemporaryDirectory(prefix="cron_b5_") as td:
        d = Path(td)
        stub = d / "crontab_stub.sh"
        marker = d / "crontab_called"
        stub.write_text(f"#!/usr/bin/env bash\necho called >> {marker}\nexit 0\n", encoding="utf-8")
        env = dict(os.environ, CRONTAB_BIN=str(stub))
        p = subprocess.run(["bash", str(installer), "--run-dir", str(d / "run"),
                            "--state-dir", str(d / "state")],
                           capture_output=True, text=True, timeout=30, env=env)
        assert p.returncode == 0 and "未修改 crontab" in p.stdout \
            and "# BEGIN viral-evo-lab B-5" in p.stdout, f"dry-run 输出异常: {p.stdout}"
        assert not marker.exists(), "dry-run 不得调用 crontab（系统调度零改动）"

        rd, sd = d / "run", d / "state"
        rd.mkdir()
        p = subprocess.run(["bash", str(watch), "--run-dir", str(rd), "--state-dir", str(sd)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 0 and "无巡检对象" in p.stdout + p.stderr, \
            f"空 manifest 应安全跳过: rc={p.returncode} {p.stdout} {p.stderr}"
        assert not (sd / ".cron_watch.lock").exists(), "锁未清理"

        (rd / "spawn_manifest.jsonl").write_text(
            json.dumps({"event": "spawn", "task_id": "T-CRON", "member": "phylo-analyst"}) + "\n",
            encoding="utf-8")
        p = subprocess.run(["bash", str(watch), "--run-dir", str(rd), "--state-dir", str(sd)],
                           capture_output=True, text=True, timeout=60)
        log = sd / "cron_watch.jsonl"
        assert log.is_file() and "T-CRON" in log.read_text(encoding="utf-8"), \
            f"巡检结果须落盘: rc={p.returncode} {p.stdout} {p.stderr}"

        # R4.3（盲检🔴5）：UTF-16 manifest 时内联 py sys.exit(3) 不得被
        # `TASKS="$(...)"` 命令替换吞掉 → 静默降级「无巡检对象」EXIT=0。
        (rd / "spawn_manifest.jsonl").write_bytes(
            json.dumps({"task_id": "T-CRON"}).encode("utf-16"))
        p = subprocess.run(["bash", str(watch), "--run-dir", str(rd), "--state-dir", str(sd)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 3 and "manifest 汇总失败" in p.stderr, \
            f"UTF-16 manifest 须透传 EXIT=3 拒绝静默跳过，实为 {p.returncode}: {p.stderr[-200:]}"

        # R4.3（盲检🟠B）：manifest 有 task_id 但被白名单过滤（超长/非法字符）
        # → 原实现静默丢弃 → 「本轮无巡检对象」EXIT=0，监控失效。须 EXIT=3。
        (rd / "spawn_manifest.jsonl").write_text(
            json.dumps({"task_id": "T" + "x" * 70}) + "\n", encoding="utf-8")
        p = subprocess.run(["bash", str(watch), "--run-dir", str(rd), "--state-dir", str(sd)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 3 and "task_id 非法" in p.stderr, \
            f"非法 task_id 须 EXIT=3 拒绝静默跳过，实为 {p.returncode}: {p.stderr[-200:]}"
        # 对照：manifest 无 task_id 字段 → 正常「无巡检对象」EXIT=0
        (rd / "spawn_manifest.jsonl").write_text(
            json.dumps({"event": "spawn"}) + "\n", encoding="utf-8")
        p = subprocess.run(["bash", str(watch), "--run-dir", str(rd), "--state-dir", str(sd)],
                           capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, f"无 task_id 字段应正常跳过 EXIT=0，实为 {p.returncode}"


def _wording_counts(src: str) -> tuple:
    """返回 (main() 的 total 数字, CURRENT_BASELINE 机器锚声明的行为级数字)。

    v1.5.11：total 不能对全文 `re.search` —— docstring 里也写了同一句话，
    会先命中自己（实测把 main() 改成 +14 断言仍通过），故只在 main() 体内取。
    v1.5.12：doc 不能用 `v1.5.x … （45 CASES + N 行为级）` 宽匹配——实测
    命中 v1.5.10 **历史段**，自称「当前基线」的新段数字改了仍全绿；改为只读
    显式 `CURRENT_BASELINE = 45 CASES + N 行为级` 机器锚。
    """
    main_src = src.rsplit("def main()", 1)[-1]
    m_total = re.search(r"total = len\(CASES\) \+ (\d+)", main_src)
    m_doc = re.search(r"CURRENT_BASELINE\s*=\s*45 CASES \+ (\d+) 行为级", src)
    return (m_total.group(1) if m_total else None,
            m_doc.group(1) if m_doc else None)


def test_current_wording_guard() -> None:
    """v1.5.10 建 / v1.5.11 加固：当前口径一致性守卫的正 / 反向行为回归。

    背景：v1.5.9 代码已升到 G1-G6，但 CLI help、quality-gates.md 权威门表、
    主理人 T1 条款仍写五门，cron 锁注释仍写已废弃的 mkdir 目录锁，本文件
    docstring 用例数停在 v1.5.8——而全量测试仍全绿。
    本用例：①真跑 --help；②真加载守卫断言当前包第 11 项 PASS；
    ③在临时整包副本上**逐锚回退**（摘除每个正向锚 / 注入每个旧口径串，
      清单直接取守卫模块的 WORDING_POSITIVE / WORDING_NEGATIVE 单一事实源），
      逐项断言第 11 项真实 FAIL（防恒真、防漏锚、防两处清单漂移）；
    ④从 main() 体内取 total、从 CURRENT_BASELINE 机器锚取 doc 数字，
      比对并双向反验（仅改 main() / 仅改机器锚，都必须被抓到）。
    """
    # 1) CLI 真跑：--help 必须声明六门
    h = subprocess.run([sys.executable, str(CHECK_GATES), "--help"],
                       capture_output=True, text=True, timeout=30)
    assert h.returncode == 0 and "G1-G6" in h.stdout, \
        f"CLI help 回退为旧口径: rc={h.returncode} {h.stdout[:200]}"

    # 2) 真加载守卫：当前包第 11 项须 PASS
    guard_path = PKG / "tests" / "test_contract_guard.py"
    spec = importlib.util.spec_from_file_location("_wording_guard", guard_path)
    assert spec is not None and spec.loader is not None, "守卫模块无法加载"
    gmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gmod)
    res = gmod._checks_at(PKG)
    assert len(res) == 11, f"守卫项数应为 11，实测 {len(res)}"
    assert res[10][0], f"当前包第 11 项须 PASS：{res[10][1]}"
    assert hasattr(gmod, "WORDING_POSITIVE") and hasattr(gmod, "WORDING_NEGATIVE"), \
        "守卫未暴露锚清单常量（单一事实源缺失）"
    assert res[10] == gmod.check_current_wording(PKG), \
        "守卫第 11 项未接线到 check_current_wording()（抽函数后接线被摘）"

    # 3) 逐锚回退：每个正向锚被摘除、每个旧口径串被注入，第 11 项都须 FAIL
    with tempfile.TemporaryDirectory(prefix="wording_guard_") as td:
        fake = Path(td) / "pkg"
        # check_current_wording() 只读锚清单里的 5 个文件，无需复制整包；
        # 完整守卫的接线已由第 2 步在真实包上验证，此处只测第 11 项行为。
        for rel in sorted({r for r, _ in gmod.WORDING_POSITIVE} |
                          {r for r, _ in gmod.WORDING_NEGATIVE}):
            dst = fake / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((PKG / rel).read_bytes())
        for rel, needles in gmod.WORDING_POSITIVE:
            fp = fake / rel
            orig = fp.read_bytes()
            for needle in needles:
                fp.write_text(orig.decode("utf-8").replace(needle, "⟦锚已摘除⟧"),
                              encoding="utf-8")
                r = gmod.check_current_wording(fake)
                assert not r[0], \
                    f"锚 {rel}:{needle!r} 被摘除后第 11 项仍 PASS（漏锚 / 恒真嫌疑）: {r[1]}"
            fp.write_bytes(orig)
        for rel, needles in gmod.WORDING_NEGATIVE:
            fp = fake / rel
            orig = fp.read_bytes()
            for old in needles:
                fp.write_text(orig.decode("utf-8") + f"\n{old}\n", encoding="utf-8")
                r = gmod.check_current_wording(fake)
                assert not r[0], \
                    f"旧口径串 {old!r} 注入 {rel} 后第 11 项仍 PASS（负锚失效）: {r[1]}"
            fp.write_bytes(orig)

    # 4) docstring 与 main() 用例数一致；反向验证「仅改 main() total」会被抓
    src = (PKG / "tests" / "test_gate_fuzz.py").read_text(encoding="utf-8")
    total_n, doc_n = _wording_counts(src)
    assert total_n and doc_n and total_n == doc_n, \
        f"docstring 与 main() 用例数不一致: total={total_n} doc={doc_n}"
    head, tail = src.rsplit("def main()", 1)
    bad_src = head + "def main()" + tail.replace(
        f"total = len(CASES) + {total_n}",
        f"total = len(CASES) + {int(total_n) + 1}", 1)
    t2, d2 = _wording_counts(bad_src)
    assert t2 != d2, \
        "反向失败：仅改 main() 的 total 未被抓到（疑只读 docstring 自证）"
    # 反向 B（v1.5.12）：仅改「当前基线」机器锚数字，也必须被抓到
    # ——第三次盲检实证：宽正则会命中 v1.5.10 历史段，改本锚仍全绿。
    m_base = re.search(r"(CURRENT_BASELINE\s*=\s*45 CASES \+) (\d+)( 行为级)", src)
    assert m_base, "当前基线机器锚缺失（_wording_counts 无法取到 doc 数字）"
    bad_doc = (src[:m_base.start(2)] + str(int(m_base.group(2)) + 1)
               + src[m_base.end(2):])
    t3, d3 = _wording_counts(bad_doc)
    assert t3 != d3, \
        "反向失败：仅改 CURRENT_BASELINE 数字未被抓到（疑命中历史段）"


def main() -> int:
    ok_n = 0
    for name, art, wv, oc, expect in CASES:
        ok, msg = run_case(name, art, wv, oc, expect)
        print(("  ✅ " if ok else "  ❌ ") + msg)
        ok_n += int(ok)
    print(f"\nfuzz 用例 {len(CASES)} | 通过 {ok_n} | 失败 {len(CASES) - ok_n}")
    # 行为级用例（pytest 入口亦覆盖，此处供独立脚本运行）
    for fn in (test_g4_waiver_release, test_gate_mode_blocks, test_disposition_gate,
               test_tc3_timezone_canonicalize, test_require_tag_gate,
               test_poll_hitlimit_and_manifest,
               test_legacy_package_check_fallback, test_g3_fail_still_writes_report,
               test_decision_log_audit, test_baseline_anchor_roundtrip,
               test_decision_records_guard, test_g6_evidence_gate,
               test_reconcile_decisions, test_anchor_refresh_guard,
               test_cron_b5_assets, test_current_wording_guard):
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
            ok_n += 1
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e}")
    total = len(CASES) + 16
    print(f"\n合计 {total} | 通过 {ok_n} | 失败 {total - ok_n}")
    return 0 if ok_n == total else 1


if __name__ == "__main__":
    sys.exit(main())
