#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# cron_watch.sh —— P4 B-5 跨会话巡检包装（v1.5.9 · 2026-11-10）
# ==============================================================
# 背景：B-1 的 poll_run_dir.py 是「阶段节点人工触发」的秒级巡检；B-5 要的是
#       跨会话场景——主理人不在线时也能周期性记下「哪些产出没落盘/撞限」。
# 本脚本只做调度适配，不重写巡检判定（单一事实源 = poll_run_dir.py）：
#   - 从 spawn_manifest.jsonl 汇总活跃 task_id，逐个跑 --from-manifest 巡检
#   - 结构化结果追加到 <state-dir>/cron_watch.jsonl + 文本日志
#   - mkdir 原子锁防并发 cron 叠加；只读判定，不改任何产出文件
# 边界：不自动修复、不重派、不发外部通知；跨会话告警的推送通道未排期。
#
# 用法：
#   bash scripts/cron_watch.sh --run-dir <dir> --state-dir <dir>
#        [--task-id <T-xxx>|--all] [--pkg-root <包根>]
# 退出码：0 = 全部巡检 PASS；5 = 至少一个任务 NOT_READY；3 = 参数/环境错误

set -u

RUN_DIR=""
STATE_DIR=""
TASK_ID="--all"
PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --run-dir)   RUN_DIR="$2"; shift 2 ;;
    --state-dir) STATE_DIR="$2"; shift 2 ;;
    --task-id)   TASK_ID="$2"; shift 2 ;;
    --pkg-root)  PKG_ROOT="$2"; shift 2 ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "❌ 未知参数: $1" >&2; exit 3 ;;
  esac
done

if [ -z "$RUN_DIR" ] || [ -z "$STATE_DIR" ] || [ ! -d "$RUN_DIR" ]; then
  echo "❌ --run-dir / --state-dir 必填且 run_dir 须存在" >&2; exit 3
fi
POLL="$PKG_ROOT/scripts/poll_run_dir.py"
if [ ! -f "$POLL" ]; then
  echo "❌ 巡检脚本不存在: $POLL" >&2; exit 3
fi
mkdir -p "$STATE_DIR" || { echo "❌ state_dir 不可创建" >&2; exit 3; }

# 原子锁：noclobber 的 `>` 以 O_EXCL 建文件，cron 叠加时后者跳过。
# 不用 mkdir 目录锁：实测 macOS 沙箱下 rmdir 返回 Operation not permitted，
# 会留下死锁导致后续巡检永久跳过（v1.5.9 首轮测试实测抓到）。
LOCK="$STATE_DIR/.cron_watch.lock"
if ! (set -o noclobber; : > "$LOCK") 2>/dev/null; then
  echo "⏭ 上一轮巡检仍在进行，跳过本次（锁: $LOCK）" >&2; exit 0
fi
trap 'rm -f "$LOCK" 2>/dev/null || true' EXIT

# 汇总活跃任务：优先 manifest 的 task_id；任务 ID 白名单防路径注入
if [ "$TASK_ID" = "--all" ]; then
  TASKS="$(python3 - "$RUN_DIR" <<'PY'
import json, re, sys
from pathlib import Path
p = Path(sys.argv[1]) / "spawn_manifest.jsonl"
ids = []
if p.is_file():
    for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        try: ev = json.loads(line)
        except Exception: continue
        t = ev.get("task_id") if isinstance(ev, dict) else None
        if isinstance(t, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", t) and t not in ids:
            ids.append(t)
print(" ".join(ids))
PY
)"
else
  if ! printf '%s' "$TASK_ID" | grep -Eq '^[A-Za-z0-9_-]{1,64}$'; then
    echo "❌ task_id 非法（仅允许字母数字下划线连字符）: $TASK_ID" >&2; exit 3
  fi
  TASKS="$TASK_ID"
fi

if [ -z "$TASKS" ]; then
  echo "⏭ manifest 中无有效 task_id，本轮无巡检对象" >&2; exit 0
fi

WORST=0
for t in $TASKS; do
  OUT="$(python3 "$POLL" "$RUN_DIR" "$t" --from-manifest 2>&1)"
  RC=$?
  [ "$RC" -gt "$WORST" ] && WORST="$RC"
  TS="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '%s\n' "{\"ts\":\"$TS\",\"task_id\":\"$t\",\"exit\":$RC,\"summary\":\"$(printf '%s' "$OUT" | tail -1 | sed 's/"/\\"/g')\"}" \
    >> "$STATE_DIR/cron_watch.jsonl"
  printf '\n=== %s %s (EXIT=%s) ===\n%s\n' "$TS" "$t" "$RC" "$OUT" >> "$STATE_DIR/cron_watch.log"
  echo "[$TS] $t EXIT=$RC"
done

# cron 场景只需 0/5 二值；poll 的其他退出码透传（便于排障）
if [ "$WORST" -eq 0 ]; then exit 0; fi
if [ "$WORST" -eq 5 ]; then exit 5; fi
exit "$WORST"
