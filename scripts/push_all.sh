#!/usr/bin/env bash
# push_all.sh — 三仓库一站式 push（research-ops 方案 3 机制 · v2 工程化版）
# 用法：
#   bash scripts/push_all.sh ["<commit message>"]        # 交互模式（有 modified 时询问提交）
#   bash scripts/push_all.sh --auto ["<commit message>"] # 无人值守模式（modified 时自动提交）
# 设计要点：
#   1. TLS 瞬断自愈：内置 HTTP/1.1 + 3 次重试（实测 GitHub TLS unexpected eof 场景）
#   2. 防 git add . 误提交：先 status 体检列出改动，auto 模式仅 git add -u（不收未跟踪新文件）
#   3. 导出重打包已移除（2026-11-08 裁决：exports zip 为冗余离线副本，真源已收官，不再生成）
#   4. 全中文注释 · 带日志 · set -euo pipefail
set -euo pipefail

# ── 参数解析 ──
MODE="interactive"
if [ "${1:-}" = "--auto" ]; then
  MODE="auto"
  shift
fi
MSG="${1:-chore: auto push by push_all.sh}"

# ── 三仓库绝对路径 ──
PKG="/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab"
OPS="/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32/research-ops"
H5="/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5"

# ── 带重试的推送函数（TLS 瞬断自愈核心）──
# $1=仓库路径 $2=refspec；HTTP/1.1 绕过 HTTP/2 帧同步类瞬断，最多 3 次、间隔 5s
push_with_retry() {
  local repo="$1" refspec="$2" attempt
  for attempt in 1 2 3; do
    echo "  [尝试 $attempt/3] git -C $(basename "$repo") push $refspec"
    if git -C "$repo" -c http.version=HTTP/1.1 push origin $refspec 2>&1 | tail -3; then
      echo "  ✓ 推送成功"
      return 0
    fi
    [ "$attempt" -lt 3 ] && { echo "  ⚠️ 失败，5 秒后重试…"; sleep 5; }
  done
  echo "  ✗ 三次重试均失败（$repo ← $refspec）" >&2
  return 1
}

# ── 第 1 步：三仓库体检（防误提交运行时文件）──
echo "═══ 1/3 三仓库体检 ═══"
declare -a DIRTY_REPOS=()      # 有工作树改动的仓库
declare -a AHEAD_REPOS=()      # 有未推送提交的仓库
for r in "$PKG" "$OPS" "$H5"; do
  [ -d "$r/.git" ] || { echo "  ⚠️ 跳过（非 git 仓或不存在）：$r"; continue; }
  name=$(basename "$r")
  modified=$(git -C "$r" status --short | wc -l | tr -d ' ')
  # ahead 按各仓实际上游分支统计（专家包/research-ops 上游不同名，@{u} 自动解析）
  ahead=$(git -C "$r" log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
  echo "── $name ──  modified=$modified  ahead=$ahead"
  if [ "$modified" -gt 0 ]; then
    echo "  ⚠️ 改动文件（前 5 条）:"
    git -C "$r" status --short | head -5 | sed 's/^/    /'
    DIRTY_REPOS+=("$r")
  fi
  if [ "$ahead" -gt 0 ]; then
    echo "  ⚠️ 未推送提交（前 3 条）:"
    git -C "$r" log --oneline @{u}..HEAD | head -3 | sed 's/^/    /'
    AHEAD_REPOS+=("$r:$ahead")
  fi
done

# ── 第 2 步：提交决策（interactive 询问 / auto 自动）──
echo "═══ 2/3 提交决策（模式：$MODE）═══"
for r in "${DIRTY_REPOS[@]:-}"; do
  [ -z "$r" ] && continue
  name=$(basename "$r")
  if [ "$MODE" = "auto" ]; then
    # 防误提交：auto 模式只收已跟踪文件的改动（git add -u），不收未跟踪新文件
    git -C "$r" add -u
    if git -C "$r" diff --cached --quiet; then
      echo "  $name: 无已跟踪改动可提交，跳过"
    else
      git -C "$r" commit -q -m "$MSG"
      echo "  $name: 已自动提交（仅已跟踪文件）→ $MSG"
    fi
  else
    printf "  %s：提交以上改动？(y=提交并推送 / n=跳过该仓) " "$name"
    read -r ans
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
      git -C "$r" add -u
      git -C "$r" commit -q -m "$MSG" || { echo "  $name: 无可提交内容，跳过"; continue; }
      echo "  $name: 已提交"
      AHEAD_REPOS+=("$r:just-committed")
    else
      echo "  $name: 跳过（改动保留在工作树，不推送）"
    fi
  fi
done

# ── 第 3 步：按序推送（专家包 → research-ops → 04_H5），各自 refspec ──
echo "═══ 3/3 推送 ═══"
FAIL=0
echo "── push 专家包 (main) ──"
git -C "$PKG" log --oneline @{u}..HEAD 2>/dev/null | grep -q . \
  && push_with_retry "$PKG" "main" || echo "  （无未推送提交，跳过）"

echo "── push research-ops (research-ops-track) ──"
git -C "$OPS" log --oneline @{u}..HEAD 2>/dev/null | grep -q . \
  && push_with_retry "$OPS" "main:research-ops-track" || echo "  （无未推送提交，跳过）"

echo "── push 04_H5 (main) ──"
git -C "$H5" log --oneline @{u}..HEAD 2>/dev/null | grep -q . \
  && push_with_retry "$H5" "main" || echo "  （无未推送提交，跳过）"

# ── 推送后状态复核 ──
echo "═══ 推送后状态 ═══"
for r in "$PKG" "$OPS" "$H5"; do
  [ -d "$r/.git" ] || continue
  ahead=$(git -C "$r" log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
  modified=$(git -C "$r" status --short | wc -l | tr -d ' ')
  echo "  $(basename "$r"): ahead=$ahead  modified=$modified"
done

echo "==> push_all.sh 完成"
