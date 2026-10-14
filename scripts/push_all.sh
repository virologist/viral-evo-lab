#!/usr/bin/env bash
# push_all.sh — 三仓库一站式 push（方案 3 待建机制）
# 用法：bash scripts/push_all.sh "<commit message>"
set -e
MSG="${1:-chore: auto push by push_all.sh}"

# 三仓库绝对路径
PKG="/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab"
OPS="/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32/research-ops"
H5="/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5"

# 1) git status 体检（防误提交运行时文件）
for r in "$PKG" "$OPS" "$H5"; do
  echo "── $(basename $r) ──"
  cd "$r"
  modified=$(git status --short | wc -l | tr -d ' ')
  ahead=$(git log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
  echo "  modified=$modified  ahead=$ahead"
  if [ "$modified" -gt 0 ]; then
    echo "  ⚠️  modified files (last 3):"
    git status --short | head -3 | sed 's/^/    /'
  fi
  if [ "$ahead" -gt 0 ]; then
    echo "  ⚠️  un-pushed (last 3):"
    git log --oneline @{u}..HEAD | head -3 | sed 's/^/    /'
  fi
done

# 2) 询问是否推送（防 push 误提交）
read -p "==> Push all three? (y/N) " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 0; }

# 3) 按序推送（专家包 → research-ops → 04_H5）
echo "── push 专家包 (main) ──"
git -C "$PKG" push origin main 2>&1 | tail -2

echo "── push research-ops (research-ops-track) ──"
git -C "$OPS" push origin main:research-ops-track 2>&1 | tail -2

echo "── push 04_H5 (main) ──"
git -C "$H5" push origin main 2>&1 | tail -2

# 4) 推送后状态
echo "── 推送后状态 ──"
for r in "$PKG" "$OPS" "$H5"; do
  ahead=$(git -C "$r" log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
  modified=$(git -C "$r" status --short | wc -l | tr -d ' ')
  echo "  $(basename $r): ahead=$ahead  modified=$modified"
done

# 5) 重打包导出（如有改动）
if [ "$modified" -gt 0 ] || [ "$ahead" -gt 0 ]; then
  echo "── 重打包导出 (research-ops/exports/) ──"
  python3 "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts/package_expert.py" \
    "$PKG" "$OPS/exports" 2>&1 | tail -2
fi

echo "==> push_all.sh 完成"
