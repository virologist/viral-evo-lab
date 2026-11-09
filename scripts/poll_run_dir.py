#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
poll_run_dir.py —— run_dir 落盘巡检（P4 监控设计 §3 方案 B 落地 · 2026-10-15）
=============================================================================
背景：主理人此前用 TaskOutput 阻塞等待成员完成，队头一旦挂起全队陪等。
方案 B = 非阻塞轮询：每阶段跑一次本脚本做秒级巡检，对照"期望成员清单"
与实际落盘的 <task-id>__<member>.md，缺谁/谁卡了一目了然。

判定规则（确定性，看文件 + mtime + 头部撞限标注）：
    OK      <task-id>__<member>.md 存在且 mtime 距今 < yellow-min 分钟
    黄超时  存在但 mtime 距今 >= yellow-min 分钟（落盘后久未更新，留意）
    缺失    文件不存在（成员未产出或派工未达）
    红超时  存在但 >= red-min 分钟未更新
    撞限    文件头 3 行含「轮次耗尽」标注（R-13a · 2026-11-09：产出不完整，
            主理人声明"文件存在且无撞限标注 = Phase 完成"——本脚本负责把
            该判据的标注侧落成机械检查，带标注 = 视为未完成）

期望清单来源（二选一）：
    --expected 人工逗号分隔（显式，优先）
    --from-manifest 读 <run-dir>/spawn_manifest.jsonl 自动生成
    （R-13c · 2026-11-09 接线：spawn_manifest 由 log_spawn.py 写入，
     此前只写不读——本参数补上消费端，打通断点续跑第 1 步）

退出码：0 = 期望成员全部落盘、无红超时、无撞限（黄超时仅警告，不失败）
        5 = 有缺失 / 红超时 / 撞限 / 期望清单无法确定
边界：回答"到齐没有/新鲜没有/有没有撞限"；"产出对不对"归 check_gates.py 与人。

用法：
    # 例：期望 literature-scout 与 research-diagnostician 两员产出
    python3 scripts/poll_run_dir.py research-ops/_harness_runs/T-20261015-M2 \\
        T-20261015-M2 --expected literature-scout,research-diagnostician \\
        --yellow-min 15 --red-min 30

    # 从 spawn_manifest 自动生成期望清单（断点续跑第 1 步机械化）
    python3 scripts/poll_run_dir.py research-ops/_harness_runs/T-xxx \\
        T-xxx --from-manifest

    # 典型节奏：spawn 后每 2-3 分钟跑一次；exit 0 即可进入 check_gates.py
"""
import argparse
import json
import sys
import time
from pathlib import Path

# R-13a：撞限标注识别串（与主理人 MD 撞限协议条款逐字对应）
HIT_LIMIT_MARK = "轮次耗尽"



def _read_manifest_with_retry(mf: Path, retries: int = 3, base_delay: float = 2.0):
    """R-10b（2026-11-09）：manifest 读取带 3 次指数退避重试（2s/4s/8s）。

    背景：P4 B-4 原为「未排期」；任务 B 指令要求「默认 3 次指数退避并记录
    原因」。落点选择：巡检是最需要重试的场景（OneDrive 同步窗口/并发写入
    可致瞬时读失败）。每次失败原因写 stderr；重试耗尽返回 (None, 原因)。
    """
    import time as _t
    last_err = ""
    for attempt in range(retries):
        try:
            txt = mf.read_text(encoding="utf-8")
            return txt, ""
        except OSError as e:
            last_err = f"第 {attempt + 1}/{retries} 次读取失败: {type(e).__name__}: {e}"
            print(f"⚠ {last_err}，{_t.strftime('%S')}s 后重试…" if attempt < retries - 1 else f"⚠ {last_err}——重试耗尽", file=sys.stderr)
            if attempt < retries - 1:
                _t.sleep(base_delay * (2 ** attempt))
    return None, last_err

def load_expected_from_manifest(run_dir: Path) -> tuple[list[str] | None, str]:
    """R-13c：从 spawn_manifest.jsonl 读期望成员清单。

    返回 (成员列表, 错误串)。成功时错误串为空；失败时列表为 None。
    manifest 缺失/空/全部行畸形 = 无法生成清单（调用方裁决，不静默放行）。
    """
    mf = run_dir / "spawn_manifest.jsonl"
    if not mf.is_file():
        return None, f"spawn_manifest.jsonl 不存在: {mf}"
    txt, rerr = _read_manifest_with_retry(mf)
    if txt is None:
        return None, f"spawn_manifest.jsonl 读取失败（重试耗尽）: {rerr}"
    members: list[str] = []
    bad = 0
    for line in mf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            m = obj.get("member")
            if isinstance(m, str) and m.strip():
                members.append(m.strip())
            else:
                bad += 1
        else:
            bad += 1
    if not members:
        return None, f"spawn_manifest.jsonl 无有效 member 记录（畸形行 {bad}）: {mf}"
    if bad:
        print(f"⚠️ manifest 含 {bad} 条畸形行（已跳过）", file=sys.stderr)
    # 去重保序
    seen: set[str] = set()
    uniq = [m for m in members if not (m in seen or seen.add(m))]
    return uniq, ""


def head_hit_limit(f: Path, lines: int = 3) -> bool:
    """R-13a：读文件头 N 行判断是否带撞限标注。读失败不误判（返回 False）。"""
    try:
        with f.open("r", encoding="utf-8", errors="replace") as fh:
            head = "".join(fh.readline() for _ in range(lines))
        return HIT_LIMIT_MARK in head
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="run_dir 落盘巡检：期望成员清单 vs 实际落盘，秒级非阻塞")
    ap.add_argument("run_dir", help="演练运行目录（如 research-ops/_harness_runs/T-xxx）")
    ap.add_argument("task_id", help="任务 ID（如 T-20261015-M2）")
    ap.add_argument("--expected",
                    help="期望落盘的成员清单，逗号分隔（如 literature-scout,research-diagnostician）")
    ap.add_argument("--from-manifest", action="store_true",
                    help="从 <run-dir>/spawn_manifest.jsonl 自动生成期望清单（与 --expected 二选一）")
    ap.add_argument("--yellow-min", type=int, default=15, help="黄超时阈值（分钟，默认 15）")
    ap.add_argument("--red-min", type=int, default=30, help="红超时阈值（分钟，默认 30）")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"❌ run_dir 不存在: {run_dir}", file=sys.stderr)
        return 5

    # 期望清单：--expected 显式优先；否则 --from-manifest；两者皆无 = 参数错误
    if args.expected:
        expected = [m.strip() for m in args.expected.split(",") if m.strip()]
    elif args.from_manifest:
        expected, err = load_expected_from_manifest(run_dir)
        if expected is None:
            print(f"❌ {err}", file=sys.stderr)
            return 5
    else:
        print("❌ 须指定 --expected 或 --from-manifest（二选一）", file=sys.stderr)
        return 5
    if not expected:
        print("❌ 期望清单为空", file=sys.stderr)
        return 5

    now = time.time()
    ok, missing, yellow, red, hitlimit = [], [], [], [], []
    for member in expected:
        f = run_dir / f"{args.task_id}__{member}.md"
        if not f.is_file():
            missing.append(member)
            continue
        if head_hit_limit(f):
            hitlimit.append(member)
            continue
        age_min = (now - f.stat().st_mtime) / 60
        if age_min >= args.red_min:
            red.append(f"{member}({age_min:.0f}min)")
        elif age_min >= args.yellow_min:
            yellow.append(f"{member}({age_min:.0f}min)")
        else:
            ok.append(member)

    print(f"═══ 落盘巡检 {args.task_id} ═══")
    print(f"OK    ({len(ok)}): {', '.join(ok) if ok else '—'}")
    print(f"超时  ({len(yellow) + len(red)}): "
          f"黄[>= {args.yellow_min}min] {', '.join(yellow) if yellow else '—'} | "
          f"红[>= {args.red_min}min] {', '.join(red) if red else '—'}")
    print(f"缺失  ({len(missing)}): {', '.join(missing) if missing else '—'}")
    print(f"撞限  ({len(hitlimit)}): {', '.join(hitlimit) if hitlimit else '—'}")

    if missing or red or hitlimit:
        reasons = []
        if missing:
            reasons.append(f"缺失 {len(missing)}")
        if red:
            reasons.append(f"红超时 {len(red)}")
        if hitlimit:
            reasons.append(f"撞限 {len(hitlimit)}")
        print(f"\n裁决: NOT_READY（{' / '.join(reasons)}）→ 勿进 G 闸，先派工补位或人工介入")
        if hitlimit:
            print("  ⛔ 撞限成员产出不完整（头部带「轮次耗尽」标注）——按撞限协议续跑或人工裁决，不得收 envelope")
        return 5
    print("\n裁决: READY → 可跑 check_gates.py 收 envelope")
    if yellow:
        print(f"  ⚠️  黄超时成员建议人工确认是否已收工（落盘后 {args.yellow_min}+ 分钟无更新）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
