#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红队台账统计 + 专家包完整性清单（R1+R2 合并脚本）
用法：
  python3 redteam_tools.py stats           # ledger 闭环率统计
  python3 redteam_tools.py manifest        # 生成/校验专家包 integrity_manifest.json
  python3 redteam_tools.py check           # 完整性巡检（manifest diff + validate 提示）
"""
import csv, json, os, subprocess, sys, hashlib
from pathlib import Path
from datetime import datetime

BASE_WS = Path("/Users/biodog/Library/CloudStorage/OneDrive-Personal/GPT/WorkBuddy/2026-09-10-11-38-32")
LEDGER  = BASE_WS / "research-ops/00_governance/redteam_ledger.csv"
PKG     = Path("/Users/biodog/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab")
MANIFEST = PKG / "integrity_manifest.json"
VALIDATE = "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts/validate_expert.py"

TRACKED = ["plugin.json", "settings.json", "CLAUDE.md", "README.md"]  # 根级关键文件
TRACKED_DIRS = ["agents", "skills", "avatars"]


def sha256(path, limit=64_000):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(limit))
    return h.hexdigest()[:16]


def build_manifest():
    files = {}
    for rel in TRACKED:
        p = PKG / rel
        if p.exists():
            files[rel] = {"sha16": sha256(p), "bytes": p.stat().st_size}
    for d in TRACKED_DIRS:
        dp = PKG / d
        if not dp.is_dir():
            continue
        for p in sorted(dp.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and p.suffix in (".md", ".json", ".jpg", ".png"):
                rel = str(p.relative_to(PKG))
                files[rel] = {"sha16": sha256(p), "bytes": p.stat().st_size}
    manifest = {"generated": datetime.now().isoformat(timespec="seconds"),
                "file_count": len(files), "files": files}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ manifest 生成: {MANIFEST}（{len(files)} 文件）")
    return manifest


def check():
    if not MANIFEST.exists():
        print("⚠ 无 manifest，先生成基线：python3 redteam_tools.py manifest")
        return 1
    old = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed, added, missing = [], [], []
    for rel, meta in old["files"].items():
        p = PKG / rel
        if not p.exists():
            missing.append(rel)
        elif sha256(p) != meta["sha16"]:
            changed.append(rel)
    for d in TRACKED_DIRS:
        for p in sorted((PKG / d).rglob("*")):
            if p.is_file() and p.suffix in (".md", ".json"):
                rel = str(p.relative_to(PKG))
                if rel not in old["files"] and "archive" not in rel:
                    added.append(rel)
    print(f"基线: {old['generated']}（{old['file_count']} 文件）")
    print(f"变更 {len(changed)} | 新增 {len(added)} | 缺失 {len(missing)}")
    for x in changed: print(f"  ~ {x}")
    for x in added:   print(f"  + {x}")
    for x in missing: print(f"  ✗ {x}  ← 需立即排查（如 settings.json 事件）")
    r = subprocess.run([sys.executable, VALIDATE, str(PKG)], capture_output=True, text=True)
    print(f"validate: {'✅ 通过' if 'valid' in r.stdout else '❌ ' + r.stdout[-200:]}")
    return 0 if not missing else 2


def stats():
    if not LEDGER.exists():
        print("⚠ ledger 不存在"); return 1
    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8-sig")))
    by_sev, by_status, by_route = {}, {}, {}
    for r in rows:
        s, st = r["severity"], r["status"]
        by_sev[s] = by_sev.get(s, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
        rt = r["route"] or "unrouted"
        by_route[rt] = by_route.get(rt, 0) + 1
    n = len(rows)
    closed = by_status.get("closed", 0)
    print(f"═ redteam_ledger 统计 ═")
    print(f"总 finding: {n}（trace: {sorted({r['trace_id'] for r in rows})}）")
    print(f"严重度: " + " | ".join(f"{k}={v}" for k, v in sorted(by_sev.items())))
    print(f"状态:   " + " | ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    print(f"路由:   " + " | ".join(f"{k}={v}" for k, v in sorted(by_route.items())))
    fatal = [r for r in rows if r["severity"] in ("fatal", "severe", "high")]
    fatal_closed = sum(1 for r in fatal if r["status"] == "closed")
    print(f"\nP0 级（fatal/severe/high）闭环率: {fatal_closed}/{len(fatal)} = {fatal_closed/len(fatal)*100:.0f}%")
    print(f"全量闭环率: {closed}/{n} = {closed/n*100:.0f}%")
    out = BASE_WS / "research-ops/00_governance/redteam_stats_latest.txt"
    out.write_text("\n".join([f"generated: {datetime.now().isoformat(timespec='seconds')}",
        f"total={n} closed={closed} rate={closed/n*100:.0f}%",
        f"fatal_high_closed={fatal_closed}/{len(fatal)}"]), encoding="utf-8")
    print(f"→ {out.name}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"stats": stats, "manifest": build_manifest, "check": check}.get(cmd, lambda: print(__doc__))()