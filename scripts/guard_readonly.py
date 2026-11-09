#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_readonly.py —— 只写目标路径守卫（R-10a · 2026-11-09）
=============================================================
背景：LEARNINGS 已记录实证事故——在 Loop B 只读区（research-ops）原地跑
check_gates.py，门禁报告被硬编码写回 run_dir，覆写历史快照。此前处置全靠
"人记住先 cp 到 /tmp"，无代码拦截。

本守卫 = 写盘前的最后一道机械闸：供各写盘脚本在 write/mkdir 前调用
check_write_target(path)，目标命中只读区即拒绝（EXIT=7）。

只读区判定（按优先级）：
  1. 显式清单：环境变量 VIRAL_EVO_READONLY_DENY（冒号分隔的绝对路径前缀）
  2. 默认兜底：RESEARCH_OPS_DIR 环境变量指向的目录（若已设置）
     ——research-ops 是 Loop B 研究执行环，双环隔离纪律天然只读

边界：
  - 只拦「写目标位于只读区」，不拦正常工作区写入（run_dir 在工作区 = 放行）
  - 不做内容审查、不做递归扫描（调用方逐写盘点接入，零漏报前提 = 接线齐全）
  - 逃生开关 --allow-readonly（或同名 env）供确需写入的受控场景，须人工显式传

退出码：7 = 写目标命中只读区（本脚本独立运行时输出诊断后返回）
"""
from __future__ import annotations

import sys
from pathlib import Path

EXIT_READONLY_VIOLATION = 7


def _deny_roots() -> list[Path]:
    """只读区根清单：显式 env 优先，RESEARCH_OPS_DIR 兜底。"""
    import os
    roots: list[Path] = []
    deny_env = os.environ.get("VIRAL_EVO_READONLY_DENY", "").strip()
    if deny_env:
        for part in deny_env.split(":"):
            p = part.strip()
            if p:
                roots.append(Path(p).expanduser().resolve())
    rops = os.environ.get("RESEARCH_OPS_DIR", "").strip()
    if rops:
        roots.append(Path(rops).expanduser().resolve())
    return roots


def check_write_target(path: str | Path) -> tuple[bool, str]:
    """写盘前调用：目标命中只读区 → (False, 原因)；安全 → (True, "")。

    判定规则：目标路径（或其尚未存在的父目录链）解析后位于任一只读根之下
    → 拦截。用字符串前缀比对（resolve 后），不要求目标已存在。
    """
    import os
    if os.environ.get("VIRAL_EVO_ALLOW_READONLY", "").strip() in ("1", "true", "yes"):
        return True, ""
    roots = _deny_roots()
    if not roots:
        return True, ""
    p = Path(path).expanduser()
    # mkdir 类目标可能尚不存在：向上找最近的已存在祖先做 resolve，再拼回
    anchor = p
    try:
        while not anchor.exists():
            parent = anchor.parent
            if parent == anchor:
                break
            anchor = parent
        resolved = (anchor.resolve() / p.relative_to(anchor)) if anchor != p else anchor.resolve()
    except (ValueError, OSError):
        resolved = p
    rp = str(resolved)
    for root in roots:
        rs = str(root)
        if rp == rs or rp.startswith(rs + "/"):
            return False, (f"写目标命中只读区: {rp} 位于 {rs} 之下"
                           f"（双环隔离：research-ops/Loop B 只读；"
                           f"确需写入时先 cp 到工作区副本操作，或显式设置 "
                           f"VIRAL_EVO_ALLOW_READONLY=1 逃生）")
    return True, ""


def guard_or_exit(path: str | Path) -> None:
    """写盘前一行式：命中只读区直接向 stderr 报错并 EXIT=7。"""
    ok, reason = check_write_target(path)
    if not ok:
        print(f"⛔ [guard_readonly] {reason}", file=sys.stderr)
        raise SystemExit(EXIT_READONLY_VIOLATION)


def main() -> int:
    """独立运行：对传入路径做只读区检查（供人工/CI 预检）。"""
    import argparse
    ap = argparse.ArgumentParser(description="只写目标路径守卫：路径命中只读区 → EXIT=7")
    ap.add_argument("paths", nargs="+", help="待检查的写目标路径（可多个）")
    args = ap.parse_args()
    bad = []
    for p in args.paths:
        ok, reason = check_write_target(p)
        print(("  ✅ " if ok else "  ⛔ ") + (p if ok else reason))
        if not ok:
            bad.append(p)
    if bad:
        print(f"\n{len(bad)} 个路径命中只读区 → 拒绝写入（EXIT=7）", file=sys.stderr)
        return EXIT_READONLY_VIOLATION
    return 0


if __name__ == "__main__":
    sys.exit(main())
