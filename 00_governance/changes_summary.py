#!/usr/bin/env python3
"""
R7: 变更影响分析卡片（archivist 启动时跑 git diff --stat 自动列 3 仓变更）
- 输入：3 仓 path
- 输出：00_governance/changes_summary_<date>.md（人读）
        + changes_summary_<date>.json（机器读）
- 触发：4 仓任一有未提交/未推送时，或每周一次手动
"""
import json, subprocess, sys
from pathlib import Path
from datetime import datetime

REPOS = {
    "expert": "/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab",
    "research-ops": "/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32",
    "04_H5": "/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5",
}

def git_c(repo, args):
    r = subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def analyze(repo_name, repo_path):
    out = {"name": repo_name, "path": repo_path, "status": {}, "warnings": []}
    # status --short
    s, _, _ = git_c(repo_path, ["status", "--short"])
    out["status"]["uncommitted"] = len(s.splitlines()) if s else 0
    out["status"]["details"] = s
    # ahead/behind
    a, _, _ = git_c(repo_path, ["log", "--oneline", "@{u}..HEAD"])
    out["status"]["unpushed"] = len(a.splitlines()) if a else 0
    out["status"]["unpushed_details"] = a
    # 最新 commit
    h, _, _ = git_c(repo_path, ["log", "-1", "--format=%h %s"])
    out["status"]["latest"] = h
    # CLAUDE.md 是否含 §7 模块链（如有，检查是否含 M* 模块号）
    claude = Path(repo_path) / "CLAUDE.md"
    if claude.exists():
        t = claude.read_text(encoding="utf-8")
        # 简易检查：M17 之后的 M 编号是否在 §7 出现
        from re import findall
        in_section_7 = "## §7" in t
        mods = sorted(set(findall(r"M(\d+[a-z]?)", t)))
        out["warnings"].append({
            "type": "CLAUDE_M_check",
            "section_7_found": in_section_7,
            "modules_in_file": mods,
            "m19_m20_m21_present": all(f"M{n}" in mods for n in ["19","20","21"])
        })
    return out

def main():
    today = datetime.now().strftime("%Y%m%d")
    out_dir = Path(REPOS["research-ops"]) / "research-ops/00_governance"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [analyze(n, p) for n, p in REPOS.items()]
    # 写 JSON
    (out_dir / f"changes_summary_{today}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    # 写 MD
    md = [f"# 变更影响分析卡片 {today}\n",
          "> 自动生成 by R7 archivist tools\n"]
    for r in results:
        s = r["status"]
        md.append(f"## {r['name']} ({r['path']})")
        md.append(f"- 未提交文件: **{s['uncommitted']}**")
        md.append(f"- 未推送 commit: **{s['unpushed']}**")
        md.append(f"- 最新 commit: `{s['latest']}`")
        if s.get('uncommitted'):
            md.append("**未提交明细**:\n```\n" + s['details'][:500] + "\n```")
        if s.get('unpushed'):
            md.append("**未推送明细**:\n```\n" + s['unpushed_details'][:300] + "\n```")
        for w in r['warnings']:
            if w['type'] == "CLAUDE_M_check":
                md.append(f"- §7 含 M19/M20/M21? **{w['m19_m20_m21_present']}**")
        md.append("")
    out = out_dir / f"changes_summary_{today}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    # 终端简报
    print(f"=== 变更影响分析 {today} ===")
    for r in results:
        s = r["status"]
        flag = "⚠" if s["uncommitted"] or s["unpushed"] else "✓"
        print(f"  {flag} {r['name']:12s} 未提交={s['uncommitted']:3d} 未推送={s['unpushed']:3d} | {s['latest'][:50]}")
    print(f"\n→ {out}")

if __name__ == "__main__":
    main()
