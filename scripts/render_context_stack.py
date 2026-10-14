#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_context_stack.py —— 双轨同步器（R2 修复 · 2026-10-15）
============================================================
背景：context_stack 的 4 对 JSON+md 双轨靠 archivist 手工双写，实测 4/4 漂移
（knowledge_index 差 5.5h / method_library 差 50min / research_anchor 与
confirmed_hypotheses 各 26 天）。本脚本 = 一条命令从 JSON 真源重渲染全部 md。

用法：
    python3 scripts/render_context_stack.py [--research-ops <路径>] [--which all|hyp|ki|ml|ra]

纪律：
    - JSON 是唯一真源；md 一律由本脚本生成，**禁止手改 md**（写 JSON → 跑本脚本）
    - 渲染是确定性变换，不新增/删除信息
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def render_hyp(d: dict) -> str:
    out = ["# Confirmed Hypotheses（人类可读视图）",
           f"> JSON 机器真源 → 渲染版｜更新：{d['last_updated']}\n", "## 活跃"]
    for h in d.get("active_hypotheses", []):
        if h.get("status") == "deprecated":
            continue
        out.append(f"### {h['id']}\n**Claim**: {h['claim']}\n")
        ev = h.get("supporting_evidence", [])
        if ev:
            out.append("**证据**: " + "; ".join(
                e.get("value", str(e.get("source", ""))) for e in ev[:3]))
        if h.get("confidence"):
            out.append(f"**置信**: {h['confidence']}")
        out.append("")
    out.append("## Deprecated（保留溯源）")
    for h in d.get("active_hypotheses", []):
        if h.get("status") != "deprecated":
            continue
        out.append(f"### {h['id']} (deprecated)\n**原 claim**: {h['claim'][:200]}")
        out.append(f"**deprecation_reason**: {h.get('deprecation_reason', '')}\n")
    if d.get("v65_manuscript_link"):
        out.append(f"## 关联稿件\n{d['v65_manuscript_link']}")
    return "\n".join(out) + "\n"


def render_ki(d: dict) -> str:
    ts = d.get("last_updated", "")
    out = [f"# Knowledge Index（人类可读视图）\n> JSON 机器真源 → 渲染版｜更新：{ts}\n",
           f"**总览**: {d.get('index_meta', {})}\n", "## 主题索引\n"]
    for t in d.get("topics", []):
        out.append(f"### {t['id']} — {t['title']}")
        out.append(f"**Claim**: {t.get('claim', '')}\n")
        if t.get("causal_chain"):
            out.append("**因果链**：")
            out.extend(f"- {c}" for c in t["causal_chain"])
        if t.get("linked_findings"):
            out.append(f"\n**关联发现**: {', '.join(t['linked_findings'])}")
        if t.get("file_paths"):
            out.append("\n**文件路径**：")
            out.extend(f"- `{f}`" for f in t["file_paths"])
        out.append(f"\n**关键词**: {' / '.join(t.get('keywords', []))}\n\n---\n")
    return "\n".join(out) + "\n"


def render_ml(d: dict) -> str:
    out = ["# Method Library（人类可读视图）",
           f"> 更新：{d.get('last_updated', '')}｜schema: {d.get('schema_version', '')}\n"]
    for m in d.get("methods", []):
        out.append(f"## {m['id']} — {m.get('name', '')}")
        out.append(f"- **模块**: {m.get('module', '')}")
        out.append(f"- **核心**: {m.get('core', '')}")
        out.append(f"- **陷阱**: {m.get('pitfall', '')}")
        out.append(f"- **验证**: {m.get('verify', '')}")
        out.append(f"- **复用**: {m.get('reusable', '')}")
        out.append(f"- **源码**: `{m.get('source', '')}`")
        lr, ro = m.get("last_reused"), m.get("reuse_outcome")
        if lr or ro:
            out.append(f"- **复用记录**: {lr or '—'} / {ro or '—'}")
        out.append("")
    return "\n".join(out) + "\n"


def render_ra(d: dict) -> str:
    out = ["# Research Anchor（人类可读视图）",
           f"> JSON 机器真源 → 渲染版｜更新：{d.get('last_updated', '')}\n"]
    for fr in d.get("active_fronts", []):
        out.append(f"## {fr.get('id', '?')} — {fr.get('front_name', '')}")
        for k, v in fr.items():
            if k in ("id", "front_name") or not v:
                continue
            out.append(f"- **{k}**: {v}")
        out.append("")
    for k, v in d.items():
        if k.startswith(("$", "last_updated")) or k == "active_fronts" or not isinstance(v, (str, int, float)):
            continue
        out.append(f"- **{k}**: {v}")
    return "\n".join(out) + "\n"


RENDERERS = {"hyp": ("confirmed_hypotheses", render_hyp),
             "ki": ("knowledge_index", render_ki),
             "ml": ("method_library", render_ml),
             "ra": ("research_anchor", render_ra)}


def main() -> int:
    ap = argparse.ArgumentParser(description="context_stack 双轨同步器：JSON 真源 → 重渲染 md 视图")
    ap.add_argument("--research-ops", default=None)
    ap.add_argument("--which", choices=("all",) + tuple(RENDERERS), default="all")
    args = ap.parse_args()

    ro = args.research_ops or os.environ.get("RESEARCH_OPS_DIR", "")
    if not ro:
        cwd = Path.cwd() / "research-ops"
        ro = str(cwd) if cwd.is_dir() else ""
    if not ro:
        print("❌ 未找到 research-ops", file=sys.stderr)
        return 3
    ctx = Path(ro) / "context_stack"

    targets = RENDERERS.keys() if args.which == "all" else [args.which]
    rc = 0
    for key in targets:
        stem, fn = RENDERERS[key]
        jp = ctx / f"{stem}.json"
        mp = ctx / f"{stem}.md"
        if not jp.is_file():
            print(f"  ⏭ {stem}: JSON 缺失")
            continue
        try:
            d = json.loads(jp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ❌ {stem}: JSON 解析失败 {e}")
            rc = 3
            continue
        mp.write_text(fn(d), encoding="utf-8")
        print(f"  ✅ {stem}.md ← {stem}.json（{mp.stat().st_size}B）")
    print("\n纪律：md 由本脚本生成，禁手改；改 JSON → 重跑本脚本。")
    return rc


if __name__ == "__main__":
    import os
    sys.exit(main())
