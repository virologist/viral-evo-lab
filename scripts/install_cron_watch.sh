#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# install_cron_watch.sh —— P4 B-5 调度注册器（v1.5.9 · 2026-11-10）
# ================================================================
# 职责边界：本脚本**默认 dry-run**，只打印将要注册的 crontab 块，不改系统。
#   --install  才写 crontab；--uninstall 只移除带标记的块，不动其他条目。
#   未经用户显式执行 --install，任何系统调度都不会被安装（权限红线）。
# 幂等：重复 --install 先滤掉旧标记块再追加，不会叠加多行。
# 可测：CRONTAB_BIN 环境变量可指向替身脚本，供 CI 验证调用行为。
#
# 用法：
#   bash scripts/install_cron_watch.sh --run-dir <dir> --state-dir <dir>
#        [--schedule "*/10 * * * *"] [--install|--uninstall]
# 退出码：0 = 成功（含 dry-run）；3 = 参数/环境错误；5 = crontab 写回失败

set -u

RUN_DIR=""
STATE_DIR=""
SCHEDULE="*/10 * * * *"
MODE="dry-run"
CRONTAB_BIN="${CRONTAB_BIN:-crontab}"
MARK_BEGIN="# BEGIN viral-evo-lab B-5 (managed; do not edit)"
MARK_END="# END viral-evo-lab B-5"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --run-dir)    RUN_DIR="$2"; shift 2 ;;
    --state-dir)  STATE_DIR="$2"; shift 2 ;;
    --schedule)   SCHEDULE="$2"; shift 2 ;;
    --install)    MODE="install"; shift ;;
    --uninstall)  MODE="uninstall"; shift ;;
    -h|--help)    sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "❌ 未知参数: $1" >&2; exit 3 ;;
  esac
done

if [ -z "$RUN_DIR" ] || [ -z "$STATE_DIR" ]; then
  echo "❌ --run-dir / --state-dir 必填" >&2; exit 3
fi
if [ ! -f "$SELF_DIR/cron_watch.sh" ]; then
  echo "❌ cron_watch.sh 不存在: $SELF_DIR" >&2; exit 3
fi

CRON_LINE="$SCHEDULE /bin/bash $SELF_DIR/cron_watch.sh --run-dir $RUN_DIR --state-dir $STATE_DIR >> $STATE_DIR/cron_stdout.log 2>&1"
BLOCK="$(printf '%s\n%s\n%s\n' "$MARK_BEGIN" "$CRON_LINE" "$MARK_END")"

if [ "$MODE" = "dry-run" ]; then
  echo "═══ B-5 调度 dry-run（未修改 crontab）═══"
  printf '%s\n' "$BLOCK"
  echo "执行 --install 才会写入系统调度；本脚本不擅自注册。"
  exit 0
fi

# 读取现有 crontab；无 crontab 时 crontab -l 返回非 0，按空处理
CURRENT="$($CRONTAB_BIN -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "$CURRENT" | awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
  $0 == b { skip=1; next }
  $0 == e { skip=0; next }
  !skip { print }
')"

if [ "$MODE" = "uninstall" ]; then
  NEW="$FILTERED"
else
  NEW="$(printf '%s\n%s\n' "$FILTERED" "$BLOCK" | sed '/^$/N;/^\n$/D')"
fi

if printf '%s\n' "$NEW" | $CRONTAB_BIN - 2>/dev/null; then
  echo "✅ crontab 已更新（mode=$MODE）；标记块之外的条目保持原样"
  printf '%s\n' "$BLOCK"
  exit 0
fi
echo "❌ crontab 写回失败（mode=$MODE）；未确认系统调度已变更" >&2
exit 5
