#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_member_output.py —— 产出端数字核验关卡（A · 2026-10-14 V1 升级）
=====================================================================
动机：V1（装配时）只核 task_payload 输入端；成员产出（run-dir 落盘 artifact）
仍靠主理人手工跑 verify_numbers.py——"已落盘工具未触发"的老毛病。
本脚本把产出端核验固化为**一条命令**，主理人收 envelope 时必跑。

用法：
    python3 scripts/verify_member_output.py <run-dir> <task-id> \
        [--sources <目录...>] [--gate] [--no-checklist]

行为：
    1. 定位 run-dir 下 <task-id>__<member>.md（支持多成员，逐个核）
    2. 提取关键数字（与 verify_numbers.py 同口径：pct/n=/p=/D′/CI）
    3. 在权威源 grep 同值（默认仅 csv/json 计算产物；md 叙述循环自证禁入）
    4. 输出裁决：PASS（exit 0）/ DEGRADE（exit 5，含未溯源清单）
    5. --gate 时 exit 5 阻断后续流程（供 CI/主理人工作流串联）
    6. 默认写 <run-dir>/<task-id>__output-check.json（与 checklist 同 schema 风格）

退出码：0 = 全过；3 = artifact 缺失；5 = 存在未溯源数字（--gate 时阻断）
"""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 复用 verify_numbers.py 的提取/匹配逻辑（同目录 import，防漂移）
_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("verify_numbers", _HERE / "verify_numbers.py")
_vn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vn)


def autodetect_sources() -> list:
    """权威源自动探测：env RESEARCH_OPS_DIR → CWD/research-ops → 本仓 outputs/。"""
    cands = []
    env_v = os.environ.get("RESEARCH_OPS_DIR", "").strip()
    if env_v and Path(env_v).is_dir():
        cands.append(env_v)
    cwd_ro = Path.cwd() / "research-ops"
    if cwd_ro.is_dir():
        cands.append(str(cwd_ro.resolve()))
    # 展开为含 outputs/data/results 的具体目录
    sources = []
    for base in cands:
        for sub in ("outputs", "data", "results", "context_stack/outputs"):
            d = Path(base) / sub
            if d.is_dir():
                sources.append(str(d))
    return sources or cands


def main() -> int:
    ap = argparse.ArgumentParser(description="产出端数字核验：run-dir artifact 关键数字 grep 权威源")
    ap.add_argument("run_dir", help="本轮运行目录")
    ap.add_argument("task_id", help="任务 ID")
    ap.add_argument("--sources", nargs="*", default=None,
                    help="权威源目录/文件（默认自动探测）")
    ap.add_argument("--exclude", nargs="*", default=["_trash", "_archive"],
                    help="排除路径关键字")
    ap.add_argument("--gate", action="store_true",
                    help="阻断模式：存在未溯源数字时 exit 5（供工作流串联）")
    ap.add_argument("--no-checklist", action="store_true",
                    help="不写 output-check.json")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"❌ run-dir 不存在: {run_dir}", file=sys.stderr)
        return 3

    artifacts = sorted(run_dir.glob(f"{args.task_id}__*.md"))
    if not artifacts:
        print(f"❌ 未找到 artifact: {run_dir}/{args.task_id}__*.md", file=sys.stderr)
        return 3

    sources = args.sources or autodetect_sources()
    if not sources:
        print("⚠️  未找到权威源（RESEARCH_OPS_DIR 未设且无 research-ops/ 子目录）",
              file=sys.stderr)
        print("   产出端核验跳过——主理人须人工确认或补 --sources", file=sys.stderr)
        return 0  # 不阻断（确定性工具缺失≠产出有问题）

    pool = _vn.load_sources(sources, args.exclude)
    print(f"📂 权威源池: {len(pool)} 字符（{len(sources)} 个目录）")

    all_unverified = []
    for art in artifacts:
        text = art.read_text(encoding="utf-8", errors="ignore")
        nums = _vn.extract_numbers(text, min_digits=2)
        unverified = []
        for kind, val, _ in nums:
            cands = {val}
            try:
                f = float(val)
                cands |= ({f"{f:.2f}", f"{f:.3f}", f"{f:.4f}"} if f >= 1
                          else {f"{f:.3f}", f"{f:.4f}", f"{f:.5f}"})
            except ValueError:
                pass
            if not any(c in pool for c in cands):
                unverified.append({"kind": kind, "value": val})
        member = art.stem.split("__", 1)[1] if "__" in art.stem else art.stem
        if unverified:
            print(f"🔴 {member}: {len(unverified)} 个未溯源数字")
            for u in unverified[:5]:
                print(f"    {u['kind']}: {u['value']}")
            all_unverified.extend([{"member": member, **u} for u in unverified])
        else:
            print(f"✅ {member}: {len(nums)} 个数字全部溯源")

    # 落盘 output-check.json（C1 修复：记录 artifact mtime 指纹，防核验后改动绕过留痕）
    if not args.no_checklist:
        verdict = "PASS" if not all_unverified else "DEGRADE"
        payload = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "task_id": args.task_id,
            "checked_artifacts": [a.name for a in artifacts],
            "artifact_mtimes": {a.name: int(a.stat().st_mtime) for a in artifacts},
            "unverified": all_unverified,
            "verdict": verdict,
            "sources_used": sources,
        }
        out = run_dir / f"{args.task_id}__output-check.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 {out}")

    if all_unverified:
        print(f"\n裁决: DEGRADE_TO_PARTIAL（{len(all_unverified)} 个未溯源数字）")
        print("  处置：成员产出标 [待人工核验] 后重传，或主理人工核后放行")
        return 5
    print("\n裁决: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
