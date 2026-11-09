#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_gates.py —— 团队级脚本化门禁（D2/M3 修复 · 2026-10-15）
============================================================
把 quality-gates.md 中"团队级"门禁从文字变成可执行检查。
收 envelope 时主理人一条命令跑完全部门禁，替代人工逐项核对。

用法：
    python3 scripts/check_gates.py <run-dir> <task-id> [--sources <目录...>]
        [--require-tag] [--require-evidence-check]

门禁清单（G1-G6，全部确定性）：
    G1 信封完整   artifact 首个 JSON 含 6 必填字段且 status ∈ {success,partial,failed,blocked}
                  （T-B2 强化：phase:int / confidence:0-100 类型校验 + 期望 vs 实际字段对照输出）
    G2 数字溯源   关键数字（n=/p=/D′/百分比/CI）在权威源 grep 得到（复用 verify_member_output）
    G3 产出落盘   <task-id>__<member>.md 至少一份存在
    G4 核验留痕   output-check.json 已生成（G2 的落盘凭证）；gate_mode=block
                  且 verdict≠PASS 时判 FAIL（C4：--gate 阻断信号传导）；
                  L3（2026-11-09）：消费 <task-id>__waivers.json 人工放行——
                  须 value+reason+authorized_by 三项齐全且覆盖全部未溯源数字
    G5 审判留痕   checklist.json 已生成（T0/T1 的落盘凭证）
    G6 抽查留痕   spawn_manifest.jsonl 含 ≥2 条 lead 的 evidence_check
                  （file:行号 + 原文摘录 + reason）；ADR-002 裁决：**默认不强制**，
                  须 --require-evidence-check 或 run_dir 下 evidence_check_policy.json
                  显式启用。未启用时 gates.json 的 skipped_gates 显式记名，不静默跳过；
                  启用后不合格 EXIT=5。只验形式要件，语义真伪归主理人 T1。

退出码：0 = 全过；3 = artifact 缺失；5 = 任一门禁 FAIL
边界：只做结构性/确定性检查；"产出质量好不好"归 LLM 与人。
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_ENV = ["agent_id", "task_id", "phase", "status", "confidence", "deliverable_summary"]
VALID_STATUS = {"success", "partial", "failed", "blocked"}



def _load_guard():
    """R-10a：加载同目录 guard_readonly（只读区写盘守卫）；加载失败不阻断（降级为无守卫）。"""
    here = Path(__file__).resolve().parent
    try:
        spec = importlib.util.spec_from_file_location("guard_readonly", here / "guard_readonly.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # L3 盲检 Y6：放宽捕获面（半损坏也降级不崩溃）
        print(f"⚠ guard_readonly 加载失败（守卫降级）: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def load_member_output():
    """复用 verify_member_output 的核验逻辑（同目录 import；C3 修复：异常转 exit 3 契约）。"""
    here = Path(__file__).resolve().parent
    try:
        spec = importlib.util.spec_from_file_location("vmo", here / "verify_member_output.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except (OSError, SyntaxError) as e:
        print(f"❌ verify_member_output.py 加载失败: {e}", file=sys.stderr)
        sys.exit(3)


import importlib.util  # noqa: E402  （置于此处供 load_member_output 使用）

ENVELOPE_SKIP_CHARS = 2000  # C2 修复（审计 2026-10-15）：信封 summary 无长度上限，400 字符会截断合法信封


def _load_verify_numbers():
    """L3（2026-11-09 · A-4）：加载 verify_numbers 模块（浮点候选集单一事实源）。

    G2 与 G4 的 waiver 匹配必须用**同一套**候选集，否则同一台账在两侧
    可能得到相反裁决（实测 0.795 / 0.7900 分歧）。
    """
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("vn_gate", here / "verify_numbers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_evidence_check():
    """ADR-002 / SOP T-D1：加载 G6 抽查留痕硬门（同目录 import）。

    独立脚本形态见 verify_evidence_check.py；此处只做内联复用，
    避免 check_gates 与 CLI 双份实现漂移（单一事实源）。
    """
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("evidence_check_gate", here / "verify_evidence_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _evidence_policy_enabled(run_dir: Path) -> bool:
    """任务级策略文件：{"enabled": true} 即启用 G6。畸形/缺失按未启用处理，不崩溃。"""
    p = run_dir / "evidence_check_policy.json"
    if not p.is_file():
        return False
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
        return isinstance(obj, dict) and obj.get("enabled") is True
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def normalize_workflow(wf_raw) -> str:
    """L3（2026-11-09）：workflow 字段归一化——把变体收敛到分析类判定。

    原实现只认精确大写 "WF4" / "ANALYSIS"，
    于是 "WF4/analysis"、"WF4 分析执行"、"wf4"、"analysis" 等自然写法
    全部绕过假说锚定校验——而这些恰是成员最可能写出的形态。

    A-2 修复（2026-11-09）：改为**子串包含**判定。原实现用分隔符切 token
    再严格相等，仍漏触发「数据WF4」「分析质控」「WF4.1」「WF4分析执行」
    「WF4。」「WF_4」「analysis质控」等 11 种以上自然写法——
    成员写什么就漏什么，门禁形同虚设。
    判定：转大写后，若含 "WF4" / "ANALYSIS" / "分析" 任一关键词即视为分析类。

    A-1 修复（2026-11-09）：增 `workflow_class` 归一化——把任意声明收敛到
    **两个类别**（"analysis" / "other"），用于 sidecar 与信封的**类别级**
    交叉核验。类别级比对可容忍 `WF4 分析执行` vs `WF4` 这类表述差异，
    同时仍能抓住「成员把分析类谎报为非分析类」的规避行为。
    """
    if not isinstance(wf_raw, str):
        return ""
    s = wf_raw.strip().upper()
    if not s:
        return ""
    if "WF4" in s or "ANALYSIS" in s or "分析" in s:
        return "WF4"
    # 下划线/点分隔的编号变体（WF_4 / WF.4 / WF 4 已在上面命中）
    if re.search(r"WF[\s_.\-]*4", s):
        return "WF4"
    return s


def workflow_class(wf_raw) -> str:
    """L3（2026-11-09 · A-1 修复）：workflow 类别归一化（analysis / other）。

    交叉核验只用类别级判定，理由：
      - 表述差异（`WF4 分析执行` vs `WF4` vs `analysis`）不应被误判为违规；
      - 类别翻转（analysis → other）才是真实的规避行为，必须拦。
    """
    return "analysis" if normalize_workflow(wf_raw) == "WF4" else "other"


def load_workflow_sidecar(run_dir: Path, task_id: str) -> tuple[dict | None, str]:
    """L3（2026-11-09 · A-1 修复）：读主理人下发的工作流声明 sidecar。

    sidecar 由 assemble_spawn_prompt.py --workflow 落盘：
        <run-dir>/<task_id>__workflow.json
    返回 (对象|None, 错误说明)。sidecar 缺失返回 (None, "")（非错误——
    存量链路无 sidecar，须退回「只信信封」旧行为，不得误阻断存量产出）。
    """
    p = run_dir / f"{task_id}__workflow.json"
    if not p.is_file():
        return None, ""
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, f"sidecar 解析失败: {type(e).__name__}: {e}"
    if not isinstance(obj, dict):
        return None, f"sidecar 顶层须为对象（实为 {type(obj).__name__}）"
    return obj, ""


def _pending_manual_marked(unverified: list, artifacts: list) -> tuple[int, str]:
    """L3（2026-11-09 · A-5 修复）：解析成员的 [待人工核验] 标注。

    背景：文档（team-lead T1 / quality-gates / verify_member_output 输出）
    承诺两条处置路径——①成员在产出中把未溯源数字标 `[待人工核验]` 后重传，
    ②主理人核 URL 后写 waivers.json 放行。但**路径①在代码里只有 print 文案、
    没有任何解析逻辑**：标注了 `[待人工核验]` 的产出照样被 G2/G4 判 FAIL，
    主理人因此只剩文档明令禁止的「人工裁量跳过」——这是把主理人推入
    违反诚实性红线的路径。

    本函数实现路径①：未溯源数字的**数值**若在 artifact 正文中紧邻
    `[待人工核验]` 标记，视为该数字已被成员显式声明「待人工核验」，
    可解除该数字的阻断（但仍须在 G2 明细中可见，不静默消失）。

    返回 (已标注数量, 摘要)。仅对该数字本身放行，不放行整份 artifact。
    """
    if not isinstance(unverified, list) or not unverified:
        return 0, ""
    try:
        texts = {a.name: a.read_text(encoding="utf-8", errors="ignore") for a in artifacts}
    except OSError:
        return 0, ""
    # 标注形态：数字与标记可被空白/标点分隔（"n=777 [待人工核验]" / "n=777（待人工核验）"）
    marker_pat = re.compile(
        r"(?P<num>\d{1,6}(?:\.\d+)?)\s*[^\n]{0,40}?\[?\s*待人工核验\s*\]?", re.I)
    marked = 0
    detail: list[str] = []
    for u in unverified:
        if not isinstance(u, dict):
            continue
        val = str(u.get("value", "")).strip()
        if not val:
            continue
        hit = False
        for text in texts.values():
            for m in marker_pat.finditer(text):
                if m.group("num") != val:
                    continue
                # 数字与标记之间不得跨越句子边界（防止远处无关标记误配）
                seg = text[max(0, m.start() - 60):m.end() + 40]
                if "待人工核验" in seg:
                    hit = True
                    break
            if hit:
                break
        if hit:
            marked += 1
            detail.append(val)
    return marked, (", ".join(detail[:5]) if detail else "")


def check_envelope(art: Path, sidecar_wf: str = "", sidecar_note: str = "") -> tuple[bool, str]:
    """G1：artifact 头部找 JSON 信封，验 6 必填 + status 合法 + 类型校验；issues 一并消费（R2-10）。

    T-B2 落地于 G1 强化（2026-10-15）：
      1. detail 附"期望字段清单 vs 实际字段清单"对照一行（diff 一目了然）；
      2. 补类型校验 phase:int / confidence:0-100（存在性 ≠ 合法性——
         "88" 字符串、"high" 这类漂移值此前会静默通过）。

    A-1 修复（2026-11-09）：接入 sidecar 交叉核验。
      背景：workflow 字段全包无任何生产者 → 假说锚定校验是死代码；
      且即便成员写，成员也可自报 WF1 规避（自报 = 自证清白）。
      现由主理人下发时落 sidecar（权威源），门禁做**类别级**双向比对：
        - sidecar=analysis + 信封 workflow 缺失 → FAIL（未回传工作流）
        - sidecar=analysis + 信封 workflow=other   → FAIL（擅自降级规避）
        - sidecar=other   + 信封 workflow=analysis → FAIL（擅自升级，伪造分析约束）
        - 无 sidecar（存量链路）→ 退回「只信信封」旧行为，不误阻断存量产出
    """
    try:
        head = art.read_text(encoding="utf-8", errors="ignore")[:ENVELOPE_SKIP_CHARS]
    except OSError as e:
        return False, f"读取失败: {e}"
    # 信封可能是独立 JSON 行/块——逐行尝试解析含 agent_id 的 JSON 对象
    for line in head.splitlines():
        line = line.strip().rstrip(",")
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # P3-R4：行首 '{' 前缀检查已挡住多数非对象，此处补显式判定作防御性兜底
        if not isinstance(obj, dict):
            continue
        if "agent_id" not in obj:
            continue
        missing = [k for k in REQUIRED_ENV if k not in obj or obj[k] in ("", None)]
        actual = sorted(obj.keys())
        # T-B2 对照行：期望 vs 实际（哪怕全过也输出，审计可 grep）
        cmp_txt = (f"字段对照 期望{sorted(REQUIRED_ENV)} vs 实际{actual}"
                   f"{' 缺' + str(missing) if missing else ' 无缺'}")
        if missing:
            return False, cmp_txt
        if str(obj.get("status", "")).lower() not in VALID_STATUS:
            return False, f"status 非法: {obj.get('status')} | {cmp_txt}"
        # T-B2 类型校验：phase 须为 int；confidence 须为 0-100 数值
        phase = obj.get("phase")
        if not isinstance(phase, int) or isinstance(phase, bool):
            return False, f"phase 类型漂移（须 int，实为 {type(phase).__name__}:{phase!r}） | {cmp_txt}"
        conf = obj.get("confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not (0 <= conf <= 100):
            return False, f"confidence 越界/类型漂移（须 0-100 数值，实为 {conf!r}） | {cmp_txt}"
        # C1（2026-11-08 · 元层审计第 1 轮）：假说锚定字段按 workflow 条件触发。
        # 仅当信封显式声明分析类 workflow 时强校验，存量信封与 fuzz 基线一律不受影响
        # （防 P3.1 同构崩溃：新增校验不得使畸形输入回归失效）。
        # L3（2026-11-09）：workflow 变体归一化——"WF4/analysis"、"WF4 分析执行"、
        # "analysis" 等写法此前绕过校验；现统一收敛为 WF4 分析类判定。
        # A-1 修复（2026-11-09）：sidecar 交叉核验——主理人下发声明为权威源，
        # 成员自报 workflow 不得降级规避（自报不可信 = 自证清白）。
        env_wf = obj.get("workflow")
        wf = normalize_workflow(env_wf)
        anchor_txt = ""
        # 类别级交叉核验（sidecar 缺失时 sidecar_wf 为空 → 跳过，全凭信封）
        if sidecar_wf:
            sc_cls = workflow_class(sidecar_wf)
            env_cls = workflow_class(env_wf) if env_wf else ""
            if env_cls != sc_cls:
                if not env_wf:
                    return False, (
                        "信封缺 workflow 字段（主理人已声明 "
                        f"workflow={sidecar_wf!r}）——须原样回传 | {cmp_txt}")
                return False, (
                    f"信封 workflow={env_wf!r} 与主理人下发声明 "
                    f"workflow={sidecar_wf!r} 类别不符"
                    f"（下发={sc_cls} / 回传={env_cls}）——不得改写任务性质 | {cmp_txt}")
            anchor_txt = f" | workflow✓{sc_cls}"
        if wf == "WF4":
            anchor = obj.get("hypothesis_anchor")
            if not isinstance(anchor, dict):
                return False, f"分析类任务（WF4）缺 hypothesis_anchor（须为对象） | {cmp_txt}"
            need = ("biological_question", "falsification_condition")
            miss_a = [k for k in need
                      if not isinstance(anchor.get(k), str) or not anchor[k].strip()]
            if miss_a:
                return False, f"hypothesis_anchor 缺/空 {miss_a} | {cmp_txt}"
            has_id = isinstance(anchor.get("hypothesis_id"), str) and anchor["hypothesis_id"].strip()
            # L3（2026-11-09）：no_hypothesis_justification 允许并列在信封顶层
            # （契约正本写作「hypothesis_id（或 no_hypothesis_justification）」并列字段），
            # 原实现只在 anchor 内查，导致按文档写在顶层的合法信封被误判 FAIL。
            just_val = anchor.get("no_hypothesis_justification")
            if not (isinstance(just_val, str) and just_val.strip()):
                just_val = obj.get("no_hypothesis_justification")
            has_just = isinstance(just_val, str) and just_val.strip()
            if not (has_id or has_just):
                return False, "hypothesis_anchor 须有 hypothesis_id 或 no_hypothesis_justification | " + cmp_txt
            anchor_txt = " | anchor=OK"
        # R2-10：issues 消费——非空则浮出门禁详情（主理人 T1 逐条处置的输入）
        issues = obj.get("issues")
        if issues is None:
            issues = []
        elif not isinstance(issues, list):
            # P3-R4：非数组值会令 len()/切片抛 TypeError → EXIT=1、gates.json
            # 不落盘、G1-G5 全体失效。畸形值明确判 FAIL，而非让门禁消失。
            return False, f"issues 须为数组（实为 {type(issues).__name__}） | {cmp_txt}"
        issues_txt = f" | issues×{len(issues)}: {'; '.join(map(str, issues[:2]))}" if issues else ""
        return True, (f"agent_id={obj.get('agent_id')} status={obj.get('status')} "
                      f"confidence={obj.get('confidence')}{issues_txt}{anchor_txt} | {cmp_txt}")
    return False, "头部 2000 字符内未找到含 agent_id 的 JSON 信封"


def _float_eq_str(num_str: str, waiver_str: str) -> bool:
    """C7（2026-11-07）：数值等值容差比较——'0.79' vs '0.790' 视为同一放行条目。

    双方均可解析为 float 时按数值比较；任一方不可解析返回 False（回退精确匹配语义）。
    """
    try:
        return abs(float(num_str) - float(waiver_str)) < 1e-12
    except (ValueError, TypeError):
        return False


def load_waivers(run_dir: Path, task_id: str) -> dict:
    """R2-2（2026-10-15）：读 <task-id>__waivers.json（人工放行台账）。
    格式：{"waivers": [{"gate": "G2", "value": "79", "reason": "外部引文 arXiv:...", "authorized_by": "..."}]}
    授权规则见 docs/authorization_matrix.md——G2 放行须主理人署名，防自我授权。

    L3（2026-11-09）：原实现以 value 为 key 收编全部门禁的 waiver，
    但 G4 阻断态放行时需要区分「哪条 waiver 覆盖了哪个未溯源数字」，
    故此处保留完整条目（含 gate / reason / authorized_by），
    匹配逻辑下沉到 _waiver_covers / _g4_waiver_hit。
    """
    wp = run_dir / f"{task_id}__waivers.json"
    if not wp.is_file():
        return {}
    try:
        data = json.loads(wp.read_text(encoding="utf-8"))
        out = {}
        for w in data.get("waivers", []) or []:
            if not isinstance(w, dict):
                continue
            v = w.get("value")
            # P3-R2（2026-11-07）：value 仅接受可哈希标量。list/dict 作 key 会抛
            # unhashable TypeError，令 G1-G5 整体失效（对抗性复查抓出，高严重度）。
            if isinstance(v, (str, int, float)) and not isinstance(v, bool):
                out[str(v)] = w
        return out
    except (json.JSONDecodeError, OSError, TypeError, ValueError, AttributeError):
        return {}


def _waiver_authorized(w: dict) -> bool:
    """waiver 有效性：须有主理人署名 + 非空理由（防自我授权与空口放行）。

    授权规则见 docs/authorization_matrix.md §二/§四——决策级放行须署名，
    且每次行使必须落 decision_log.csv（脚本只校验落盘台账，不代写）。
    """
    by = w.get("authorized_by")
    reason = w.get("reason")
    return (isinstance(by, str) and by.strip() != ""
            and isinstance(reason, str) and reason.strip() != "")


def _waiver_covers(w: dict, val: str, cands: set) -> bool:
    """waiver 是否覆盖给定数字（精确 / 候选串 / 浮点容差三路，与 G2 同口径）。"""
    wv = w.get("value")
    if not isinstance(wv, (str, int, float)):
        return False
    wv_s = str(wv)
    if wv_s == val or any(str(c) == wv_s for c in cands):
        return True
    return any(_float_eq_str(str(c), wv_s) for c in cands)


def _g4_waiver_hit(unverified: list, waivers: dict) -> tuple[bool, list[str]]:
    """L3（2026-11-09）：G4 阻断态的 waiver 放行判定。

    背景：G4 的阻断提示与 team-lead/CLAUDE 文档均声称「主理人核 URL 后写
    waivers.json 放行」，但原实现**完全不读 waiver**——实测写好 waivers.json
    后 G4 仍判 FAIL（EXIT=5），文档承诺与代码行为背离，且主理人没有合法放行路径
    （只剩「人工裁量跳过」这一违反诚实性红线的出路）。

    放行条件（三条全满足，缺一即不放行）：
      1. 该未溯源数字被某条 waiver 覆盖（值三路匹配，同 G2 口径）；
      2. 该 waiver 有非空 authorized_by（主理人署名，防自我授权）；
      3. 该 waiver 有非空 reason（外部引文 URL/出处，防空口放行）。
    未覆盖的未溯源数字仍阻断——**部分放行不解除阻断**，防止用一条 waiver
    掩盖其余问题。

    A-4 修复（2026-11-09）：候选集统一走 verify_numbers.float_candidates
    （原自造一套 .2f/.3f/.4f，与 G2 的 .3f/.4f/.5f 分歧，同一台账在两侧
    可能得到相反裁决）。
    """
    if not isinstance(unverified, list) or not waivers:
        return False, []
    try:
        _vn = _load_verify_numbers()
    except Exception:
        _vn = None
    remaining = []
    covered = []
    for u in unverified:
        if not isinstance(u, dict):
            remaining.append(u)
            continue
        val = str(u.get("value", ""))
        if _vn is not None:
            cands = _vn.float_candidates(val)
        else:
            try:
                f = float(val)
                cands = {val, f"{f:.3f}", f"{f:.4f}", f"{f:.5f}"}
            except (ValueError, TypeError):
                cands = {val}
        hit = None
        for w in waivers.values():
            if not isinstance(w, dict):
                continue
            if not _waiver_authorized(w):
                continue
            if _waiver_covers(w, val, cands):
                hit = w
                break
        if hit is None:
            remaining.append(u)
        else:
            covered.append(f"{val}（{hit.get('authorized_by')}）")
    if not remaining:
        return True, covered
    return False, covered


def main() -> int:
    ap = argparse.ArgumentParser(description="团队级脚本化门禁：G1-G5 一条命令全查")
    ap.add_argument("run_dir")
    ap.add_argument("task_id")
    ap.add_argument("--sources", nargs="*", default=None, help="权威源（默认自动探测）")
    ap.add_argument("--require-tag", action="store_true",
                    help="严审模式：G2 权威源池只接受带 source_tag: authoritative 标记的文件（默认关闭，向后兼容）")
    ap.add_argument("--require-evidence-check", action="store_true",
                    help="ADR-002：启用 G6 抽查留痕硬门（默认不强制；也可由 evidence_check_policy.json 启用）")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    # 成员 artifact = task_id__<member>.md；排除主理人生成的元文件
    LEAD_SUFFIXES = ("__checklist", "__output-check", "__gates", "spawn_prompt")
    artifacts = sorted(
        a for a in run_dir.glob(f"{args.task_id}__*.md")
        if not any(s in a.stem for s in LEAD_SUFFIXES)
    )
    results = []
    skipped_gates: list[str] = []   # ADR-002：SKIP 必须留痕，禁止静默恒 PASS

    def record(gate: str, ok: bool, detail: str):
        results.append((gate, ok, detail))
        print(f"  {'✅' if ok else '❌'} {gate}: {detail}")

    def write_report() -> str:
        """P0-2（2026-11-09 · 遗留清理轮）：所有退出路径共用落盘，防 G3 FAIL 零留痕。

        背景：AUDIT_STATE §9 已记「G3 FAIL 不落 gates.json」与诚实性红线相关且
        优先级高于其他 B 桶项，但此前 `if not g3: return 3` 在落盘前直接返回。
        本函数抽出后供早退路径与正常路径共用；**EXIT=3 契约不变，仅补留痕**。
        run_dir 不存在时无法落盘（stderr 警告，不改退出码）；只读区由守卫 EXIT=7 拦截。
        """
        verdict = "PASS" if all(ok for _, ok, _ in results) else "FAIL"
        report = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "task_id": args.task_id,
            "gates": [{"gate": g, "ok": ok, "detail": d} for g, ok, d in results],
            "verdict": verdict,
        }
        if skipped_gates:
            # ADR-002 诚实性：未评估的门不记进 gates，但必须显式列名，
            # 防「把 SKIP 伪装成 PASS」的语义空壳化。
            report["skipped_gates"] = list(skipped_gates)
        out = run_dir / f"{args.task_id}__gates.json"
        if not run_dir.is_dir():
            print(f"⚠ 无法落盘门禁报告（run_dir 不存在）: {run_dir}", file=sys.stderr)
            return verdict
        _g = _load_guard()
        if _g:
            _g.guard_or_exit(str(out))  # R-10a 只读区守卫
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n裁决: {verdict} → {out}")
        return verdict

    g6_enabled = args.require_evidence_check or _evidence_policy_enabled(run_dir)

    def run_g6():
        """ADR-002 / SOP T-D1：G6 抽查留痕硬门。

        默认不强制，但 SKIP 必须写进 skipped_gates——不把「没检查」写成 PASS。
        启用后内联复用 verify_evidence_check.check，单一事实源，不复制判定逻辑。
        """
        if not g6_enabled:
            skipped_gates.append(
                "G6 抽查留痕（默认未强制；--require-evidence-check 或 evidence_check_policy.json 可启用）")
            print("  ⏭ G6 抽查留痕: SKIP（已写入 skipped_gates，非 PASS）")
            return
        try:
            mod = _load_evidence_check()
        except Exception as e:
            record("G6 抽查留痕", False, f"硬门加载失败 {type(e).__name__}: {e}")
            return
        rc6, rep6 = mod.check(run_dir, args.task_id)
        detail = (f"记录 {rep6['total']} / 合格 {rep6['valid']} / "
                  f"不合格 {len(rep6['invalid'])} / 裁决 {rep6['verdict']}")
        if rep6["invalid"]:
            detail += "；首条问题=" + "；".join(rep6["invalid"][0]["problems"])
        record("G6 抽查留痕", rc6 == 0, detail[:240])

    print(f"═══ 团队级门禁 {args.task_id} ═══")

    # G3 产出落盘
    g3 = bool(artifacts)
    record("G3 产出落盘", g3, f"{len(artifacts)} 份 artifact" if g3 else f"{run_dir}/{args.task_id}__*.md 无一存在")
    if not g3:
        # 早退时 G6 未评估 → 显式记名，不静默。EXIT=3 契约不变。
        skipped_gates.append("G6 抽查留痕（G3 早退，未评估）")
        write_report()  # P0-2：失败也落盘（EXIT=3 契约不变）
        return 3

    # G1 信封（逐 artifact）
    # A-1 修复（2026-11-09）：读取主理人下发的工作流声明 sidecar 作权威源，
    # 与成员信封做**双向类别级交叉核验**——成员自报 workflow 不得降级规避。
    # sidecar 缺失 = 存量链路 → 不传 sidecar_wf，退回「只信信封」旧行为。
    sidecar, sc_err = load_workflow_sidecar(run_dir, args.task_id)
    sidecar_wf = ""
    if sc_err:
        # sidecar 存在但畸形：不可静默降级为「无声明」——那等于让主理人的
        # 权威声明因一次写坏就整体失效。判 G1 FAIL（须修 sidecar 重跑）。
        record("G1 信封完整", False,
               f"工作流声明 sidecar 解析失败：{sc_err}——须修复后重跑（不得降级为无声明）")
        sidecar_wf = None  # 标记：跳过逐 artifact 校验，避免误报
    elif sidecar:
        sidecar_wf = sidecar.get("workflow") or ""
        if not isinstance(sidecar_wf, str) or not sidecar_wf.strip():
            record("G1 信封完整", False,
                   "工作流声明 sidecar 缺 workflow 字段或非字符串——须修复后重跑")
            sidecar_wf = None
    else:
        sidecar_wf = ""

    if sidecar_wf is not None:
        env_ok, env_detail = True, []
        for art in artifacts:
            try:
                ok, detail = check_envelope(art, sidecar_wf=sidecar_wf)
            except Exception as e:  # P3-R4：任何未预料的解析异常都转成 G1 FAIL
                ok, detail = False, f"信封解析异常（已拦截）: {type(e).__name__}: {e}"
            env_ok = env_ok and ok
            env_detail.append(f"{art.stem.split('__',1)[-1]}: {detail}")
        record("G1 信封完整", env_ok, " | ".join(env_detail)[:180])

    # G2 数字溯源 + G4 核验留痕（复用 verify_member_output）
    vmo = load_member_output()
    sources = args.sources or vmo.autodetect_sources()
    # L3（2026-11-09）：waivers 提到外层——G4 阻断态放行同样要读它
    # （原实现只在 G2 分支内定义，G4 段取不到，文档承诺的放行路径是死路）。
    waivers = load_waivers(run_dir, args.task_id)
    if not sources:
        record("G2 数字溯源", False, "无权威源可核（须配 RESEARCH_OPS_DIR 或 --sources）")
        g2_ok, unverified_n = False, -1
    else:
        pool = vmo._vn.load_sources(sources, ["_trash", "_archive"], require_tag=args.require_tag)
        unverified_n = 0
        waived_n = 0
        marked_n = 0
        unverified_detail = []
        # L3（2026-11-09 · A-5）：收集「成员已标 [待人工核验]」的数字值，
        # 使该数字在 G2 侧不再计 FAIL（与 G4 同口径）。
        # 关键：标注是**逐数字**放行，不是整份 artifact 免检——
        # 未标注的数字照常 FAIL，可见性不受影响。
        marked_vals: set[str] = set()
        for art in artifacts:
            text = art.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(
                    r"(?P<num>\d{1,6}(?:\.\d+)?)\s*[^\n]{0,40}?\[?\s*待人工核验\s*\]?", text, re.I):
                seg = text[max(0, m.start() - 60):m.end() + 40]
                if "待人工核验" in seg:
                    marked_vals.add(m.group("num"))
        for art in artifacts:
            text = art.read_text(encoding="utf-8", errors="ignore")
            for kind, val, _ in vmo._vn.extract_numbers(text, min_digits=2):
                cands = vmo._vn.float_candidates(val)
                if not any(c in pool for c in cands):
                    # C7（2026-11-07）：waiver 匹配走 float_candidates 容差（原精确串匹配，
                    # 0.79 与 0.790 等值浮点无法放行）。
                    # P3-R1 修复（2026-11-07）：原嵌套 genexpr 误用外层未定义的 w → NameError
                    # （对抗性复查抓出，fatal）。正确逻辑：候选值对每个 waiver value 做容差比较。
                    # P3-R2：补回非数值/带单位 waiver 的精确匹配（C7 重写时遗失），
                    # 与候选值精确匹配、浮点容差三路并存，避免合法放行条目静默失效。
                    # L3（2026-11-09）：补授权校验——无署名/无理由的条目不算有效放行
                    # （与 G4 同口径，防空口 waiver 静默放行一切）。
                    hit_waiver = any(
                        _waiver_covers(w, val, cands)
                        for w in waivers.values()
                        if isinstance(w, dict) and _waiver_authorized(w)
                    )
                    if hit_waiver:
                        waived_n += 1   # R2-2：人工放行台账内的数字不计 FAIL
                    elif val in marked_vals:
                        # L3（2026-11-09 · A-5）：成员已在产出中显式标 [待人工核验]
                        # ——文档承诺的处置路径①。该数字不计 FAIL（但明细中可见）。
                        marked_n += 1
                    else:
                        unverified_n += 1
                        unverified_detail.append(f"{kind}:{val}")
        g2_ok = unverified_n == 0
        if g2_ok and waived_n == 0 and marked_n == 0:
            detail = "全部溯源"
        else:
            parts = []
            if waived_n:
                parts.append(f"{waived_n} 个经 waiver 人工放行（见 waivers.json）")
            if marked_n:
                parts.append(f"{marked_n} 个已标 [待人工核验]（成员显式声明待核）")
            if unverified_n:
                parts.append(f"{unverified_n} 个未溯源: {', '.join(unverified_detail[:4])}"
                             "（外部引文数字可写 waivers.json 人工放行，见 authorization_matrix.md）")
            detail = "；".join(parts)
        record("G2 数字溯源", g2_ok, detail)

    # G4 核验留痕（C1 修复：核对 artifact mtime 指纹，防核验后改动绕过）
    oc = run_dir / f"{args.task_id}__output-check.json"
    if not oc.is_file():
        record("G4 核验留痕", False, "output-check.json 缺失（跑 verify_member_output 即生成）")
    else:
        try:
            oc_data = json.loads(oc.read_text(encoding="utf-8"))
            # P3-R3（2026-11-07）：顶层非对象（数组/标量/null）与 artifact_mtimes
            # 非对象都会令 .get 抛 AttributeError，导致 EXIT=1 且 G5/gates.json 不落盘。
            if not isinstance(oc_data, dict):
                raise ValueError("output-check.json 顶层须为对象")
            mtimes = oc_data.get("artifact_mtimes", {})
            if not isinstance(mtimes, dict):
                raise ValueError("artifact_mtimes 须为对象")
            tampered = [
                a.name for a in artifacts
                if a.name in mtimes and int(a.stat().st_mtime) != mtimes[a.name]
            ]
            gate_mode = oc_data.get("gate_mode")
            # L3（2026-11-09 · A-3 修复）：原实现用 if/elif 组织，
            # 阻断态分支**短路**了 mtime 篡改检测——实测「篡改 artifact + 写 waiver」
            # 可让全门禁 EXIT=0（击穿诚实性红线）。
            # 现改为两个**独立**判定：篡改与阻断态各自评估，任一触发即 G4 FAIL。
            # 二者的处置路径不同（篡改=重跑核验；阻断态=标注重传或 waiver 放行），
            # 互不遮蔽、互不吞并。
            problems: list[str] = []   # 阻断原因（任一非空即 G4 FAIL）
            resolved: list[str] = []   # 解除说明（记录可见性，不构成阻断）

            # 判定一：核验后篡改（mtime 指纹）
            if tampered:
                problems.append(f"artifact 在核验后被修改（mtime 不符）: {tampered}——须重跑 verify_member_output")

            # 判定二：阻断态 DEGRADE 未处置
            # A-6 修复：verdict 缺失(None)在 block 态下**不得**豁免——
            # 「没有 verdict」不等于「核验通过」，否则 output-check.json 被截断即可绕过阻断。
            block_mode = gate_mode == "block"
            verdict_val = oc_data.get("verdict")
            verdict_missing = verdict_val is None
            blocked = block_mode and (verdict_val != "PASS" or verdict_missing)
            if blocked:
                # L3（2026-11-09）：补 waiver 放行路径——文档与提示均声称
                # 「主理人核 URL 后写 waivers.json 放行」，但原实现不读 waiver，
                # 写好 waivers.json 仍判 FAIL，主理人只剩「人工裁量跳过」这一
                # 违反诚实性红线的出路。放行条件：waiver 覆盖全部未溯源数字 +
                # 有署名 + 有理由；部分覆盖不解除阻断。
                unverified = oc_data.get("unverified")
                if not isinstance(unverified, list):
                    unverified = []
                waived_all, covered = _g4_waiver_hit(unverified, waivers)
                # A-5 修复：处置路径①「成员补 [待人工核验] 重传」须真实可解析——
                # 原实现只有 print 文案，代码里无解析逻辑，该路径实际不解除任何门禁，
                # 主理人因此只剩文档明令禁止的「人工裁量跳过」。
                marked, marked_detail = _pending_manual_marked(unverified, artifacts)
                if waived_all and unverified:
                    # 已放行 → 阻断**解除**，仅留可见性说明
                    resolved.append(
                        f"阻断态 DEGRADE 已由 waivers.json 人工放行（{len(covered)} 个未溯源数字经署名放行）")
                elif marked:
                    resolved.append(
                        f"阻断态 DEGRADE 已由成员标注 [待人工核验] 处置（{marked} 项）：{marked_detail}")
                else:
                    extra = ""
                    if covered:
                        extra = f"（已放行 {len(covered)} 个: {', '.join(covered[:3])}）"
                    problems.append(
                        "阻断态 DEGRADE 未处置（gate_mode=block）"
                        + ("（verdict 字段缺失——无 verdict 不等于核验通过）" if verdict_missing else "")
                        + "：须成员补 [待人工核验] 重传，或主理人核 URL 后写 waivers.json 放行"
                          "（须 value+reason+authorized_by 署名）；禁止仅凭人工裁量跳过" + extra)

            if problems:
                record("G4 核验留痕", False, "；".join(problems))
            elif resolved:
                record("G4 核验留痕", True, f"{oc.name}（mtime 指纹一致；" + "；".join(resolved) + "）")
            else:
                record("G4 核验留痕", True, f"{oc.name}（mtime 指纹一致，无阻断态未处置）")
        except (json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError) as e:
            record("G4 核验留痕", False, f"output-check.json 解析失败: {e}")

    # G5 审判留痕
    # L3（2026-11-09 · A-7 修复）：原实现只判文件存在，不看审判判罚状态——
    # 空壳 checklist（{} 或 hallucinated>0 的 DEGRADE）与合规 checklist 等价，
    # 「审判未真正通过」被完全忽略。现须 verdict=PASS（缺失 verdict 视为未通过，
    # 防「截断文件即绕过」）。
    cl = run_dir / f"{args.task_id}__checklist.json"
    if not cl.is_file():
        record("G5 审判留痕", False, "checklist.json 缺失（跑 write_checklist 即生成）")
    else:
        try:
            cd = json.loads(cl.read_text(encoding="utf-8"))
            if not isinstance(cd, dict):
                raise ValueError("checklist.json 顶层须为对象")
            cverdict = cd.get("verdict")
            if cverdict != "PASS":
                record("G5 审判留痕", False,
                       f"审判未通过（verdict={cverdict!r}，须 PASS）"
                       + ("——verdict 字段缺失即视为未通过" if cverdict is None else
                          "——须处置幻觉/未过项后重跑 write_checklist"))
            else:
                extra = ""
                if cd.get("hallucinated"):
                    extra = f"（hallucinated={cd.get('hallucinated')}）"
                record("G5 审判留痕", True, f"{cl.name}（verdict=PASS{extra}）")
        except (json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError) as e:
            record("G5 审判留痕", False, f"checklist.json 解析失败: {e}")

    # G6 抽查留痕（ADR-002 · SOP T-D1 硬门；默认 SKIP 但显式留名）
    run_g6()

    # 落盘门禁报告（P0-2：与 G3 早退路径共用 write_report，单一事实源）
    verdict = write_report()
    return 0 if verdict == "PASS" else 5


if __name__ == "__main__":
    sys.exit(main())
