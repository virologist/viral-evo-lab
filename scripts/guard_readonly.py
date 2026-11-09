#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_readonly.py —— 只写目标路径守卫（R-10a · 2026-11-09；L3 盲检 R2 收窄 · 2026-11-09）
=============================================================
背景：LEARNINGS 已记录实证事故——在 Loop B 只读区（research-ops/_archive）原地跑
check_gates.py，门禁报告被硬编码写回 run_dir，覆写历史快照。此前处置全靠
"人记住先 cp 到 /tmp"，无代码拦截。

本守卫 = 写盘前的最后一道机械闸：供各写盘脚本在 write/mkdir 前调用
check_write_target(path)，目标命中只读区即拒绝（EXIT=7）。

只读区判定（v1.5.5 R2 收窄；按优先级）：
  1. 显式清单：环境变量 VIRAL_EVO_READONLY_DENY（冒号分隔的绝对路径前缀）
  2. 默认兜底：RESEARCH_OPS_DIR 下的**只读子目录**——_archive/
     （历史快照/归档区 = LRN-012 事故现场，覆写 = 篡改证据）
     注意：**不再**默认拦截整个 research-ops——run_dir（_harness_runs）、
     context_stack 渲染、hypothesis_watch 台账等维护流本就位于 research-ops
     下，整根拦截会使文档工作流自相阻断（L3 盲检 R2 实验证实）。
     台账/真源子目录（00_governance 等）如需纳管，用显式 DENY 追加。

边界：
  - 只拦「写目标位于只读区」，不拦正常工作区写入
  - 未设任何只读根时打印一次性 stderr 警告（守卫空转不静默）
  - 不做内容审查、不做递归扫描；逃生开关 = env VIRAL_EVO_ALLOW_READONLY=1
    （确需写入的受控场景人工显式设置）

退出码：7 = 写目标命中只读区（本脚本独立运行时输出诊断后返回）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

EXIT_READONLY_VIOLATION = 7

# R2：RESEARCH_OPS_DIR 下默认只读的子目录（相对 research-ops 根）
DEFAULT_READONLY_SUBDIRS = ("_archive",)


def _deny_roots() -> list[Path]:
    """只读区根清单：显式 env 优先；RESEARCH_OPS_DIR 下只读子目录兜底。"""
    roots: list[Path] = []
    deny_env = os.environ.get("VIRAL_EVO_READONLY_DENY", "").strip()
    if deny_env:
        for part in deny_env.split(":"):
            p = part.strip()
            if p:
                roots.append(Path(p).expanduser().resolve())
    rops = os.environ.get("RESEARCH_OPS_DIR", "").strip()
    if rops:
        rp = Path(rops).expanduser().resolve()
        for sub in DEFAULT_READONLY_SUBDIRS:
            roots.append(rp / sub)
    if not roots:
        # 四轮🟢2：一次性警告改为「进程内一次」——函数属性会随 _load_guard 的
        # 每次 exec_module 重置（六脚本各自加载新实例，同进程可重复打印）。
        # 标记挂到 sys 模块（跨 exec_module 实例存活，进程退出即失效）。
        if not getattr(sys, "_guard_readonly_warned", False):
            print("⚠ [guard_readonly] 未设置 VIRAL_EVO_READONLY_DENY / RESEARCH_OPS_DIR——守卫空转（全部放行）；"
                  "建议显式设置只读根", file=sys.stderr)
            sys._guard_readonly_warned = True
    return roots


def check_write_target(path: str | Path) -> tuple[bool, str]:
    """写盘前调用：目标命中只读区 → (False, 原因)；安全 → (True, "")。

    判定规则：目标路径（或其尚未存在的父目录链）解析后位于任一只读根之下
    → 拦截。前缀比对统一 .lower() 折叠大小写（L3 盲检 Y2：macOS APFS 大小写
    不敏感，纯字符串前缀可被大小写变体绕过并实写成功——os.path.normcase 在
    darwin 上不折叠大小写（与 Windows 不同），故用 lower() 显式折叠；对
    Linux 纯大小写敏感文件系统，lower() 只会造成极端罕见的误拦（同目录下
    大小写孪生子目录），安全方向正确）。
    """
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
    rp = str(resolved).lower()
    for root in roots:
        rs = str(root).lower()
        if rp == rs or rp.startswith(rs + "/"):
            return False, (f"写目标命中只读区: {resolved} 位于 {root} 之下"
                           f"（归档/快照区只读——覆写即篡改证据；"
                           f"验证行为先 cp 到工作区副本操作，或显式设置 "
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
    ap.add_argument("--allow-readonly", action="store_true",
                    help="本次检查放行只读区（等价 env VIRAL_EVO_ALLOW_READONLY=1）")
    args = ap.parse_args()
    if args.allow_readonly:
        os.environ["VIRAL_EVO_ALLOW_READONLY"] = "1"
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
