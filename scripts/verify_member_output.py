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
        [--sources <目录...>] [--gate] [--require-tag] [--no-checklist]

行为：
    1. 定位 run-dir 下 <task-id>__<member>.md（支持多成员，逐个核）
    2. 提取关键数字（与 verify_numbers.py 同口径：pct/n=/p=/D′/CI）
    3. 在权威源 grep 同值（默认仅 csv/json 计算产物；md 叙述循环自证禁入）
    4. 输出裁决：PASS（exit 0）/ DEGRADE（exit 5，含未溯源清单）
    5. --gate 时把 gate_mode="block" 写入 output-check.json；check_gates.py 的 G4
       读取该字段，DEGRADE 未处置即判 FAIL——阻断信号可传导到下游门禁（C4 修复）
    6. 默认写 <run-dir>/<task-id>__output-check.json（与 checklist 同 schema 风格）

退出码：0 = 全过；3 = artifact 缺失；5 = 存在未溯源数字（--gate 时阻断）；2 = 参数非法（task_id 白名单拦截）

T-C2 决策记录（2026-10-15 · coder 拍板）：不实施 commit_hash 锚定。
理由：
    1. 防"核验后改动"已由 artifact_mtimes mtime 指纹（v1.3.1 C1 修复，
       check_gates.py G4 消费）确定性覆盖——核验后任何写盘都会使指纹失配；
    2. research-ops 为 OneDrive 目录、非 git 仓库，commit_hash 无从取值，
       引入 hash 需先给研究目录建仓，运维成本与收益不成比例；
    3. mtime 在正常工作流下不可伪造（OneDrive 同步保真），且已与 G4 门禁闭环。
若未来 research-ops 纳入 git 管理，可重开此项：把 commit_hash 并入
output-check.json 的 artifact_mtimes 同级字段即可。
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
    ap.add_argument("--require-tag", action="store_true",
                    help="严审模式：透传 verify_numbers.load_sources，未标记权威源一律拒收（默认关闭，向后兼容）")
    args = ap.parse_args()
    # R3（2026-11-17 · F2 修复）：task_id 拼路径前白名单校验——{task_id}__
    # 直接进 glob/写盘文件名，含 "/" / ".." 可越界读写（盲检已复现读 run_dir 外
    # 文件报 OK）。白名单 [A-Za-z0-9][A-Za-z0-9_-]* 与存量形态（T-20261015-M2、
    # T-FUZZ 等）完全兼容；显式拒绝路径成分与 shell 元字符。
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", args.task_id):
        print(f"❌ task_id 含非法字符（仅允许字母/数字/下划线/连字符，且不以 _- 开头，长度 ≤128）: "
              f"{args.task_id!r}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"❌ run-dir 不存在: {run_dir}", file=sys.stderr)
        return 3

    artifacts = sorted(
        a for a in run_dir.glob(f"{args.task_id}__*.md")
        # C3（2026-11-07）：排除元文件——与 check_gates.py LEAD_SUFFIXES 口径对齐，
        # 防止 checklist/output-check 等主理人侧文件被当作成员 artifact 参与数字核验
        # R4（backlog①）：同 check_gates 改精确尾匹配，消除 task_id 含元后缀子串的组合死锁
        if not any(a.stem == f"{args.task_id}{s}" for s in
                   ("__checklist", "__output-check", "__gates", "spawn_prompt"))
    )
    if not artifacts:
        print(f"❌ 未找到 artifact: {run_dir}/{args.task_id}__*.md", file=sys.stderr)
        return 3

    sources = args.sources or autodetect_sources()
    if not sources:
        print("⚠️  未找到权威源（RESEARCH_OPS_DIR 未设且无 research-ops/ 子目录）",
              file=sys.stderr)
        print("   产出端核验跳过——主理人须人工确认或补 --sources", file=sys.stderr)
        return 0  # 不阻断（确定性工具缺失≠产出有问题）

    pool = _vn.load_sources(sources, args.exclude, require_tag=args.require_tag)
    print(f"📂 权威源池: {len(pool)} 字符（{len(sources)} 个目录）")

    all_unverified = []
    for art in artifacts:
        member = art.stem.split("__", 1)[1] if "__" in art.stem else art.stem
        text, dec_err = _vn.read_text_checked(art)
        if text is None:
            # R4.1/R4.2：不可解码或含 NUL/U+FFFD 的产出 fail-closed 记未溯源哨兵
            # → verdict=DEGRADE，禁止吞字节当"无数字"而误判 PASS（G4 block 据此拦截）。
            # 无 BOM UTF-16 的 NUL 交错是合法 UTF-8，须显式检测（盲检🔴1）。
            print(f"🔴 {member}: 产出不可解码（{dec_err}）——按未溯源计",
                  file=sys.stderr)
            all_unverified.append({"member": member, "kind": "decode_error",
                                   "value": f"<不可解码:{dec_err}>"})
            continue
        # R4.3/R4.5（两路盲检 + 主代理对抗）：数字被符号/空白劈开、关键标记被隔开、
        # Unicode 等价形态（全角/圈号/上标）、声明存在却零提取——都使数字正则静默
        # 失配 → nums 为空 → 「无数字即全溯源」fail-open。统一走 _vn.prepare_numbers
        # 单一入口（NFKC 归一化 + 隔断 + 声明总闸），记未溯源哨兵 → DEGRADE。
        ok, nums, reason = _vn.prepare_numbers(text, min_digits=2)
        if not ok:
            print(f"🔴 {member}: 产出含{reason}（数字正则会失配）——按未溯源计",
                  file=sys.stderr)
            all_unverified.append({"member": member, "kind": "split_number",
                                   "value": f"<{reason}:正则会失配>"})
            continue
        unverified = []
        for kind, val, _ in nums:
            cands = _vn.float_candidates(val)
            # R4.3（盲检🟠4）：子串匹配改 token 边界匹配（单一事实源
            # _vn.pool_has_number）——p=0.94 不得被池中 0.9441 洗白。
            if not any(_vn.pool_has_number(pool, c) for c in cands):
                unverified.append({"kind": kind, "value": val})
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
            "gate_mode": "block" if args.gate else "warn",
            "sources_used": sources,
        }
        _g = _load_guard()
        if _g: _g.guard_or_exit(str(run_dir / f"{args.task_id}__output-check.json"))  # R-10a 只读区守卫
        out = run_dir / f"{args.task_id}__output-check.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 {out}")

    if all_unverified:
        print(f"\n裁决: DEGRADE_TO_PARTIAL（{len(all_unverified)} 个未溯源数字）")
        print("  处置：成员产出标 [待人工核验] 后重传，或主理人核 URL 后写 waivers.json 放行")
        if args.gate:
            print("  ⛔ 阻断模式：gate_mode=block 已写入 output-check.json，"
                  "check_gates.py 的 G4 必判 FAIL；未处置不得进入下游 WF")
        return 5
    print("\n裁决: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
