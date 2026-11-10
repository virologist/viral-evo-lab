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
      main() 的 total = len(CASES) + 15 —— 本段为当前基线，上方 v1.5.8
      段属历史记录，不得据其推断当前用例数。

运行：python3 tests/test_gate_fuzz.py  或  pytest tests/ -q
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
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

        (root / "docs" / "decision_records.json").unlink()
        rc, rep = run()
        assert rc == 3 and rep["verdict"] == "RECORDS_UNREADABLE", \
            f"裁决文件消失应 EXIT=3: rc={rc} rep={rep}"


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
        assert rc == 3 and any("改锚刷绿" in e for e in rep["structural_errors"]), \
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


def test_current_wording_guard() -> None:
    """v1.5.10（L3 盲检 R5）：当前口径一致性守卫的正 / 反向行为回归。

    背景：v1.5.9 代码已升到 G1-G6，但 CLI help、quality-gates.md 权威门表、
    主理人 T1 条款仍写五门，cron 锁注释仍写已废弃的 mkdir 目录锁，本文件
    docstring 用例数停在 v1.5.8——而全量测试仍全绿。本用例真跑 --help、
    真加载守卫，并用「旧口径」包副本反向验证第 11 项确会 FAIL（防恒真），
    最后校验 docstring 与 main() 声明的用例数一致。
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

    # 3) 反向金丝雀：把包复制一份并改回旧口径，第 11 项必须真实 FAIL
    with tempfile.TemporaryDirectory(prefix="wording_guard_") as td:
        fake = Path(td) / "pkg"
        shutil.copytree(PKG, fake, ignore=shutil.ignore_patterns(
            ".git", ".pytest_cache", "__pycache__"))
        cg = fake / "scripts" / "check_gates.py"
        cg.write_text(cg.read_text(encoding="utf-8").replace(
            "G1-G6 一条命令全查", "G1-G5 一条命令全查"), encoding="utf-8")
        bad_res = gmod._checks_at(fake)
        assert len(bad_res) == 11, f"守卫项数异常：{len(bad_res)}"
        assert not bad_res[10][0], \
            f"金丝雀失败：旧口径 fixture 下第 11 项仍 PASS（恒真嫌疑）：{bad_res[10][1]}"

    # 4) docstring 与 main() 用例数口径一致（防「补了新段但 total 没同步」复发）
    src = (PKG / "tests" / "test_gate_fuzz.py").read_text(encoding="utf-8")
    m_total = re.search(r"total = len\(CASES\) \+ (\d+)", src)
    m_doc = re.search(r"v1\.5\.10.*?（45 CASES \+ (\d+) 行为级）", src, re.S)
    assert m_total and m_doc and m_total.group(1) == m_doc.group(1), \
        (f"docstring 与 main() 用例数不一致: total={m_total and m_total.group(1)} "
         f"doc={m_doc and m_doc.group(1)}")


def main() -> int:
    ok_n = 0
    for name, art, wv, oc, expect in CASES:
        ok, msg = run_case(name, art, wv, oc, expect)
        print(("  ✅ " if ok else "  ❌ ") + msg)
        ok_n += int(ok)
    print(f"\nfuzz 用例 {len(CASES)} | 通过 {ok_n} | 失败 {len(CASES) - ok_n}")
    # 行为级用例（pytest 入口亦覆盖，此处供独立脚本运行）
    for fn in (test_g4_waiver_release, test_gate_mode_blocks, test_disposition_gate,
               test_require_tag_gate, test_poll_hitlimit_and_manifest,
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
    total = len(CASES) + 15
    print(f"\n合计 {total} | 通过 {ok_n} | 失败 {total - ok_n}")
    return 0 if ok_n == total else 1


if __name__ == "__main__":
    sys.exit(main())
