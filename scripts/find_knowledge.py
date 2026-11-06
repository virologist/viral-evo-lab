#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_knowledge.py —— 跨三仓知识入口（S1 · 2026-10-14）
执行：在 04_H5 / research-ops / 专家包三仓统一 grep 查询关键词
用法：python3 scripts/find_knowledge.py <query> [--limit 20] [--type md|py|json]
返回：<仓库>::<相对路径>:<行号>:<内容>  排序按相关度
边界：仅做"机械跨仓 grep"（确定性），不判断"这是什么含义"（语义，LLM 范畴）
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# C4（2026-11-07）：默认值保留本机布局，但全部可被环境变量覆盖（换机/换用户不失效）
#   FIND_KNOWLEDGE_H5 / FIND_KNOWLEDGE_ROPS / FIND_KNOWLEDGE_PKG
_REPOS_DEFAULT = {
    "04_H5": "/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5",
    "research-ops": "/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32/research-ops",
    "expert": "/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab",
}
_ENV_MAP = {
    "04_H5": "FIND_KNOWLEDGE_H5",
    "research-ops": "FIND_KNOWLEDGE_ROPS",
    "expert": "FIND_KNOWLEDGE_PKG",
}


def get_repos() -> dict[str, str]:
    return {k: os.environ.get(v, d) for k, (d, v) in
            ((k, (_REPOS_DEFAULT[k], _ENV_MAP[k])) for k in _REPOS_DEFAULT)}


# rg 路径：PATH 探测优先，最后回退 homebrew 常见位置
RG = shutil.which("rg") or "/opt/homebrew/bin/rg"


def grep_repo(name: str, root: str, query: str, type_filter: str | None, limit: int) -> list[dict]:
    out = []
    if not Path(root).is_dir():
        return out
    if Path(RG).is_file():
        cmd = [RG, "-n", "--no-heading", "-i", "--max-columns", "200", "--max-count", str(limit)]
        if type_filter:
            cmd += ["-t", type_filter]
        cmd += [query, root]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        lines = r.stdout.splitlines()[:limit]
    else:
        # 纯 grep 回退（macOS BSD grep -E 支持基础正则；不解释 | ，退化为字面）
        cmd = ["grep", "-rni", "-E", query, root, "-l"]  # 先列文件
        r1 = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        files = r1.stdout.splitlines()[:limit]
        lines = []
        for f in files:
            r2 = subprocess.run(["grep", "-ni", "-E", query, f], capture_output=True, text=True, timeout=10)
            for line in r2.stdout.splitlines()[:3]:
                lines.append(line)
                if len(lines) >= limit:
                    break
    for line in lines:
        # 形如 /abs/path:lineno:content（BSD grep 输出 path:lineno:content）
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        abs_p, lineno, content = parts
        rel = abs_p.replace(root + "/", "") if abs_p.startswith(root) else abs_p
        out.append({"repo": name, "path": rel, "line": lineno, "content": content.strip()[:200]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="跨三仓知识入口：rg/grep 跨 04_H5/research-ops/专家包 查关键词")
    ap.add_argument("query", help="查询关键词（支持正则，rg 时 -E）")
    ap.add_argument("--limit", type=int, default=15, help="每仓最多返回行数（默认 15）")
    ap.add_argument("--type", choices=("md", "py", "json"), help="文件类型过滤（仅 rg 模式）")
    args = ap.parse_args()

    all_hits: list[dict] = []
    for name, root in get_repos().items():
        all_hits.extend(grep_repo(name, root, args.query, args.type, args.limit))

    if not all_hits:
        print(f"❌ 三仓均无命中: '{args.query}'")
        return 0
    print(f"🔍 '{args.query}' → {len(all_hits)} 命中（{args.limit} cap/仓）\n")
    for h in all_hits:
        print(f"[{h['repo']}] {h['path']}:{h['line']}")
        print(f"  {h['content']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
