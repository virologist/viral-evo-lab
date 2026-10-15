#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_gates.py —— 团队级脚本化门禁（D2/M3 修复 · 2026-10-15）
============================================================
把 quality-gates.md 中"团队级"门禁从文字变成可执行检查。
收 envelope 时主理人一条命令跑完全部门禁，替代人工逐项核对。

用法：
    python3 scripts/check_gates.py <run-dir> <task-id> [--sources <目录...>]

门禁清单（G1-G5，全部确定性）：
    G1 信封完整   artifact 首个 JSON 含 6 必填字段且 status ∈ {success,partial,failed,blocked}
                  （T-B2 强化：phase:int / confidence:0-100 类型校验 + 期望 vs 实际字段对照输出）
    G2 数字溯源   关键数字（n=/p=/D′/百分比/CI）在权威源 grep 得到（复用 verify_member_output）
    G3 产出落盘   <task-id>__<member>.md 至少一份存在
    G4 核验留痕   output-check.json 已生成（G2 的落盘凭证）
    G5 审判留痕   checklist.json 已生成（T0/T1 的落盘凭证）

退出码：0 = 全过；3 = artifact 缺失；5 = 任一门禁 FAIL
边界：只做结构性/确定性检查；"产出质量好不好"归 LLM 与人。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_ENV = ["agent_id", "task_id", "phase", "status", "confidence", "deliverable_summary"]
VALID_STATUS = {"success", "partial", "failed", "blocked"}


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


def check_envelope(art: Path) -> tuple[bool, str]:
    """G1：artifact 头部找 JSON 信封，验 6 必填 + status 合法 + 类型校验；issues 一并消费（R2-10）。

    T-B2 落地于 G1 强化（2026-10-15）：
      1. detail 附"期望字段清单 vs 实际字段清单"对照一行（diff 一目了然）；
      2. 补类型校验 phase:int / confidence:0-100（存在性 ≠ 合法性——
         "88" 字符串、"high" 这类漂移值此前会静默通过）。
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
        # R2-10：issues 消费——非空则浮出门禁详情（主理人 T1 逐条处置的输入）
        issues = obj.get("issues") or []
        issues_txt = f" | issues×{len(issues)}: {'; '.join(map(str, issues[:2]))}" if issues else ""
        return True, (f"agent_id={obj.get('agent_id')} status={obj.get('status')} "
                      f"confidence={obj.get('confidence')}{issues_txt} | {cmp_txt}")
    return False, "头部 2000 字符内未找到含 agent_id 的 JSON 信封"


def load_waivers(run_dir: Path, task_id: str) -> dict:
    """R2-2（2026-10-15）：读 <task-id>__waivers.json（人工放行台账）。
    格式：{"waivers": [{"gate": "G2", "value": "79", "reason": "外部引文 arXiv:...", "authorized_by": "..."}]}
    授权规则见 docs/authorization_matrix.md——G2 放行须主理人署名，防自我授权。
    """
    wp = run_dir / f"{task_id}__waivers.json"
    if not wp.is_file():
        return {}
    try:
        data = json.loads(wp.read_text(encoding="utf-8"))
        return {w.get("value"): w for w in data.get("waivers", []) if w.get("value")}
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="团队级脚本化门禁：G1-G5 一条命令全查")
    ap.add_argument("run_dir")
    ap.add_argument("task_id")
    ap.add_argument("--sources", nargs="*", default=None, help="权威源（默认自动探测）")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    # 成员 artifact = task_id__<member>.md；排除主理人生成的元文件
    LEAD_SUFFIXES = ("__checklist", "__output-check", "__gates", "spawn_prompt")
    artifacts = sorted(
        a for a in run_dir.glob(f"{args.task_id}__*.md")
        if not any(s in a.stem for s in LEAD_SUFFIXES)
    )
    results = []

    def record(gate: str, ok: bool, detail: str):
        results.append((gate, ok, detail))
        print(f"  {'✅' if ok else '❌'} {gate}: {detail}")

    print(f"═══ 团队级门禁 {args.task_id} ═══")

    # G3 产出落盘
    g3 = bool(artifacts)
    record("G3 产出落盘", g3, f"{len(artifacts)} 份 artifact" if g3 else f"{run_dir}/{args.task_id}__*.md 无一存在")
    if not g3:
        return 3

    # G1 信封（逐 artifact）
    env_ok, env_detail = True, []
    for art in artifacts:
        ok, detail = check_envelope(art)
        env_ok = env_ok and ok
        env_detail.append(f"{art.stem.split('__',1)[-1]}: {detail}")
    record("G1 信封完整", env_ok, " | ".join(env_detail)[:180])

    # G2 数字溯源 + G4 核验留痕（复用 verify_member_output）
    vmo = load_member_output()
    sources = args.sources or vmo.autodetect_sources()
    if not sources:
        record("G2 数字溯源", False, "无权威源可核（须配 RESEARCH_OPS_DIR 或 --sources）")
        g2_ok, unverified_n = False, -1
    else:
        pool = vmo._vn.load_sources(sources, ["_trash", "_archive"])
        unverified_n = 0
        waived_n = 0
        unverified_detail = []
        waivers = load_waivers(run_dir, args.task_id)
        for art in artifacts:
            text = art.read_text(encoding="utf-8", errors="ignore")
            for kind, val, _ in vmo._vn.extract_numbers(text, min_digits=2):
                cands = vmo._vn.float_candidates(val)
                if not any(c in pool for c in cands):
                    if val in waivers:
                        waived_n += 1   # R2-2：人工放行台账内的数字不计 FAIL
                    else:
                        unverified_n += 1
                        unverified_detail.append(f"{kind}:{val}")
        g2_ok = unverified_n == 0
        detail = ("全部溯源" if g2_ok and waived_n == 0 else
                  (f"{waived_n} 个经 waiver 人工放行（见 waivers.json）" if g2_ok
                   else f"{unverified_n} 个未溯源: {', '.join(unverified_detail[:4])}"
                        f"（外部引文数字可写 waivers.json 人工放行，见 authorization_matrix.md）"))
        record("G2 数字溯源", g2_ok, detail)

    # G4 核验留痕（C1 修复：核对 artifact mtime 指纹，防核验后改动绕过）
    oc = run_dir / f"{args.task_id}__output-check.json"
    if not oc.is_file():
        record("G4 核验留痕", False, "output-check.json 缺失（跑 verify_member_output 即生成）")
    else:
        try:
            oc_data = json.loads(oc.read_text(encoding="utf-8"))
            mtimes = oc_data.get("artifact_mtimes", {})
            tampered = [
                a.name for a in artifacts
                if a.name in mtimes and int(a.stat().st_mtime) != mtimes[a.name]
            ]
            if tampered:
                record("G4 核验留痕", False,
                       f"artifact 在核验后被修改（mtime 不符）: {tampered}——须重跑 verify_member_output")
            else:
                record("G4 核验留痕", True, f"{oc.name}（mtime 指纹一致）")
        except (json.JSONDecodeError, OSError) as e:
            record("G4 核验留痕", False, f"output-check.json 解析失败: {e}")

    # G5 审判留痕
    cl = run_dir / f"{args.task_id}__checklist.json"
    record("G5 审判留痕", cl.is_file(), str(cl.name) if cl.is_file() else "checklist.json 缺失（跑 write_checklist 即生成）")

    # 落盘门禁报告
    verdict = "PASS" if all(ok for _, ok, _ in results) else "FAIL"
    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "task_id": args.task_id,
        "gates": [{"gate": g, "ok": ok, "detail": d} for g, ok, d in results],
        "verdict": verdict,
    }
    out = run_dir / f"{args.task_id}__gates.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n裁决: {verdict} → {out}")
    return 0 if verdict == "PASS" else 5


if __name__ == "__main__":
    sys.exit(main())
