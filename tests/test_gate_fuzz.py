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

运行：python3 tests/test_gate_fuzz.py  或  pytest tests/ -q
"""
import json
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


def main() -> int:
    ok_n = 0
    for name, art, wv, oc, expect in CASES:
        ok, msg = run_case(name, art, wv, oc, expect)
        print(("  ✅ " if ok else "  ❌ ") + msg)
        ok_n += int(ok)
    print(f"\nfuzz 用例 {len(CASES)} | 通过 {ok_n} | 失败 {len(CASES) - ok_n}")
    # 行为级用例（pytest 入口亦覆盖，此处供独立脚本运行）
    for fn in (test_g4_waiver_release, test_gate_mode_blocks, test_disposition_gate,
               test_require_tag_gate, test_poll_hitlimit_and_manifest, test_legacy_package_check_fallback):
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
            ok_n += 1
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e}")
    total = len(CASES) + 6
    print(f"\n合计 {total} | 通过 {ok_n} | 失败 {total - ok_n}")
    return 0 if ok_n == total else 1


if __name__ == "__main__":
    sys.exit(main())
