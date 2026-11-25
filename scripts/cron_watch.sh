#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# cron_watch.sh —— P4 B-5 跨会话巡检包装（v1.5.9 · 2026-11-10）
# ==============================================================
# 背景：B-1 的 poll_run_dir.py 是「阶段节点人工触发」的秒级巡检；B-5 要的是
#       跨会话场景——主理人不在线时也能周期性记下「哪些产出没落盘/撞限」。
# 本脚本只做调度适配，不重写巡检判定（单一事实源 = poll_run_dir.py）：
#   - 从 spawn_manifest.jsonl 汇总活跃 task_id，逐个跑 --from-manifest 巡检
#   - 结构化结果追加到 <state-dir>/cron_watch.jsonl + 文本日志
#   - noclobber（O_EXCL）文件锁防并发 cron 叠加；只读判定，不改任何产出文件
# 边界：不自动修复、不重派、不发外部通知；跨会话告警的推送通道未排期。
#
# 用法：
#   bash scripts/cron_watch.sh --run-dir <dir> --state-dir <dir>
#        [--task-id <T-xxx>|--all] [--pkg-root <包根>]
# 退出码：0 = 全部巡检 PASS（含锁冲突跳过）；5 = 至少一个任务 NOT_READY；
#         3 = 参数/环境错误；poll_run_dir.py 的其它退出码原样透传

set -u

RUN_DIR=""
STATE_DIR=""
TASK_ID="--all"
PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --run-dir|--state-dir|--task-id|--pkg-root)
      [ $# -ge 2 ] || { echo "❌ $1 缺少参数值" >&2; exit 3; }
      case "$1" in
        --run-dir)   RUN_DIR="$2" ;;
        --state-dir) STATE_DIR="$2" ;;
        --task-id)   TASK_ID="$2" ;;
        --pkg-root)  PKG_ROOT="$2" ;;
      esac
      shift 2 ;;
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
  echo "⏭ 上一轮巡检仍在进行，跳过本次（锁: ${LOCK}）" >&2; exit 0
fi
trap 'rm -f "$LOCK" 2>/dev/null || true' EXIT

# 汇总活跃任务：优先 manifest 的 task_id；任务 ID 白名单防路径注入
if [ "$TASK_ID" = "--all" ]; then
  TASKS="$(python3 - "$RUN_DIR" <<'PY'
import json, re, sys
from pathlib import Path
# R4.2（盲检🟠）：原 errors="replace" 会把 UTF-16 manifest 吞成 U+FFFD → 全部
# JSON 行解析失败 → TASKS 空 → "本轮无巡检对象"，监控静默失效。改用严格读；
# 不可解码时明示错误并非零退出，禁止静默降级为"无任务"。
# 说明：heredoc 内 __file__ 指向 <stdin>，故从 argv[1]（RUN_DIR）定位脚本目录不可靠，
# 这里内联与 _text_guard.has_forbidden 同款 Unicode 类别检测，保持单一判定口径。
import unicodedata
_ALLOWED_WS = set("\t\n\r\v\f")
def _emoji(cp):
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF
def _bad_text(s):
    # R4.3：与 _text_guard.has_forbidden 同款 span 判定——把连续 emoji/Cf 视为
    # 一段；非 ZWJ 的 Cf 一律拒绝；emoji/ZWJ 段紧贴 ASCII 数字（夹断数字串）拒绝。
    n = len(s); i = 0
    while i < n:
        ch = s[i]
        if ch in _ALLOWED_WS:
            i += 1; continue
        if ch == "\ufffd" or unicodedata.category(ch) == "Cc":
            return True
        if _emoji(ord(ch)) or unicodedata.category(ch) == "Cf":
            j = i; non_zwj = False
            while j < n and (_emoji(ord(s[j])) or s[j] == "\u200d" or unicodedata.category(s[j]) == "Cf"):
                if unicodedata.category(s[j]) == "Cf" and s[j] != "\u200d":
                    non_zwj = True
                j += 1
            left = s[i-1] if i > 0 else ""
            right = s[j] if j < n else ""
            if non_zwj or left.isdigit() or right.isdigit():
                return True
            i = j; continue
        i += 1
    return False
p = Path(sys.argv[1]) / "spawn_manifest.jsonl"
ids = []
if p.is_file():
    try:
        txt = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        txt = None; err = f"{type(e).__name__}: {e}"
    if txt is not None and _bad_text(txt):
        txt = None; err = "含 Cc/Cf/U+FFFD 不可见字符（疑二进制污染）"
    if txt is None:
        print(f"[cron_watch] manifest 不可解码（{err}）——拒绝静默跳过巡检", file=sys.stderr)
        sys.exit(3)
    for line in txt.splitlines():
        try: ev = json.loads(line)
        except Exception: continue
        t = ev.get("task_id") if isinstance(ev, dict) else None
        if isinstance(t, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", t) and t not in ids:
            ids.append(t)
        elif isinstance(t, str) and t.strip():
            # R4.3（盲检🟠B）：manifest 里有 task_id 但被白名单过滤（超长/非法字符）
            # → 原实现静默丢弃 → ids 空 → 下方「本轮无巡检对象」EXIT=0，监控失效。
            # 与「manifest 根本没有 task_id」区分开：前者是异常，拒绝静默跳过。
            print(f"[cron_watch] manifest 中 task_id 非法（长度/字符集不合规）: {t[:80]!r}",
                  file=sys.stderr)
            sys.exit(3)
print(" ".join(ids))
PY
)"
# R4.3（2026-11-20 · 盲检🔴5）：命令替换 `VAR="$(python3 ...)"` 会吞掉内联
# python 的 sys.exit(3)——赋值语句成功 → $?=0 → 空 TASKS → 下方 exit 0
# "本轮无巡检对象"，监控静默失效（实测 UTF-16 manifest 下 EXIT=0）。
# 立即捕获内联 python 真实退出码，非零则原样透传，禁止静默降级。
TASKS_RC=$?
if [ "${TASKS_RC}" -ne 0 ]; then
  echo "❌ manifest 汇总失败（内联校验 EXIT=${TASKS_RC}）——拒绝静默跳过巡检" >&2
  exit "${TASKS_RC}"
fi
else
  if ! printf '%s' "$TASK_ID" | grep -Eq '^[A-Za-z0-9_-]{1,64}$'; then
    echo "❌ task_id 非法（仅允许字母数字下划线连字符）: $TASK_ID" >&2; exit 3
  fi
  TASKS="$TASK_ID"
fi

if [ -z "$TASKS" ]; then
  # R4.10（盲检 A🟠7）：manifest 含 task_id 字段却全被白名单过滤 = 监控静默失效，
  # 不得以「无任务」跳过；显式 EXIT=3 让失效可见。
  if python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));rows = d if isinstance(d, list) else [d]
raise SystemExit(0 if any(isinstance(x,dict) and "task_id" in x for x in rows) else 1)' "$RUN_DIR/spawn_manifest.jsonl" 2>/dev/null; then
    echo "❌ manifest 含 task_id 字段但全部非法——拒绝静默跳过巡检" >&2; exit 3
  fi
  echo "⏭ manifest 无 task_id 字段，本轮无巡检对象" >&2; exit 0
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
