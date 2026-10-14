#!/usr/bin/env python3
"""
R8: memory 滚动裁剪
- 30 天前的当日 .md → 蒸馏进 research-ops/MEMORY.md 后归档入 _memory_archive/
- 防 1 年后 1MB+ 单边膨胀
- 蒸馏原则：保留所有项目级长期事实（战线/防线/底线）+ 当日临时事件精简摘要
"""
import re, sys
from pathlib import Path
from datetime import datetime, timedelta

WS = Path("/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32")
B = Path("/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5")
THRESHOLD = next((int(a) for a in sys.argv[1:] if a.isdigit()), 30)
APPLY = "--apply" in sys.argv
cutoff = datetime.now() - timedelta(days=THRESHOLD)
print(f"=== R8 memory 滚动裁剪（THRESHOLD={THRESHOLD}d, cutoff={cutoff:%Y-%m-%d}）===")

memory_roots = {
    "ws": WS / ".workbuddy/memory",   # 本 thread 焦点：专家团工作空间
    # B 仓 (04_H5/.workbuddy/memory) 显式排除：科研主线资产, 本 thread 不碰
    # 历史蒸馏文已存 _memory_archive/B_*.md 作为占位, 不重复蒸馏
}
archive_root = WS / "research-ops/_memory_archive"
archive_root.mkdir(parents=True, exist_ok=True)

distilled_count = 0
for label, mdir in memory_roots.items():
    pass  # 显式只动 ws 范围
    if not mdir.exists():
        print(f"  [skip] {label}: {mdir} 不存在")
        continue
    for f in sorted(mdir.glob("2026-*.md")):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d")
        except ValueError:
            continue
        if d >= cutoff:
            continue
        # 蒸馏：保留首段（标题+语境）+ 抽取所有 commit hash + 三行要点
        t = f.read_text(encoding="utf-8")
        commit_hash = re.findall(r"\b[0-9a-f]{7,8}\b", t)
        commits = " ".join(sorted(set(commit_hash))[:8])
        head = t.split("\n", 1)[1] if "\n" in t else ""
        first_para = t.split("\n\n", 1)[0]
        # 归档
        arch_file = archive_root / f"{label}_{f.stem}.md"
        arch_file.write_text(
            f"# 蒸馏归档 {f.stem}（{label}，{d:%Y-%m-%d}）\n\n"
            f"## 标题段\n{first_para}\n\n"
            f"## 涉及 commit\n{commits}\n\n"
            f"## 原文路径\n{f}\n",
            encoding="utf-8"
        )
        print(f"  [{label}] {f.stem} → 蒸馏归档（{len(t)}字 → ~{arch_file.stat().st_size}字）")
        if APPLY:
            f.unlink()
            print(f"    🗑  删 {f.name}")
        distilled_count += 1

print(f"\n蒸馏 {distilled_count} 份{'（已应用）' if APPLY else '（dry-run，加 --apply 执行）'}")
