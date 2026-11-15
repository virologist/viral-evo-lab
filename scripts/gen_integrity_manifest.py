#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_integrity_manifest.py — 完整性清单重生成（A3 · 2026-11-07）

背景：integrity_manifest.json 生成于 2026-10-14（34 文件），此后 docs/、scripts/ 全部
脚本、tests/、vendor/、lead-ops.md、team-contract.md 等大量结构变更未入清单——
完整性基线与实际文件脱节（抽查 5 项仅 1 项吻合）。

功能：遍历 git ls-files（唯一真源：跟踪文件即资产），生成 {sha16, bytes} 清单。
排除：清单文件自身（避免自引用死锁）与 .pytest_cache（非 git 跟踪时自动排除）。

用法：
    python3 scripts/gen_integrity_manifest.py            # 生成并覆盖 integrity_manifest.json
    python3 scripts/gen_integrity_manifest.py --check    # 只校验不写（exit 1 = 清单过期；2 = git 不可用）
    python3 scripts/gen_integrity_manifest.py --help     # 打印帮助（只读）

R2 回补（2026-11-15）：原 main() 仅判断 "--check" in sys.argv，任何未知参数
（含 --help、拼错的 --chek）都被静默忽略并落入「重生成并覆盖」分支——
实测 --help 会刷新 generated 时间戳并写盘，等于可静默洗白基线。改用 argparse：
--help 只读、未知参数直接报错（EXIT=2），不再误触写分支。

幂等性：--check 为只读且状态不变时结果恒为 0；重生成每次刷新 generated 时间戳
（故重生成本身不是「diff 为空」的幂等写，旧 docstring 该声称不实，已订正）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PKG_ROOT / "integrity_manifest.json"


def tracked_files() -> list[str]:
    # R-12b（2026-11-09）：git 缺失/仓库损坏不再裸抛——明确报错 EXIT=2
    # （此前的 check=True 无兜底会直接 traceback，无退出码契约）
    try:
        out = subprocess.run(
            ["git", "-C", str(PKG_ROOT), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
        print(f"❌ git ls-files 失败（{type(e).__name__}: {e}）——"
              f"manifest 以 git 跟踪清单为源，git 不可用即无法生成。"
              f"请确认本目录是 git 仓库且 git 在 PATH。", file=sys.stderr)
        raise SystemExit(2)
    return sorted(ln for ln in out.splitlines() if ln.strip())


def file_digest(p: Path) -> dict:
    data = p.read_bytes()
    return {
        "sha16": hashlib.sha256(data).hexdigest()[:16],
        "bytes": len(data),
    }


def build() -> dict:
    files: dict[str, dict] = {}
    for rel in tracked_files():
        if rel == "integrity_manifest.json":
            continue  # 自引用排除
        p = PKG_ROOT / rel
        if not p.is_file():
            continue
        files[rel] = file_digest(p)
    return {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "file_count": len(files),
        "files": files,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="完整性清单：以 git ls-files 为唯一真源生成/校验 integrity_manifest.json")
    ap.add_argument("--check", action="store_true",
                    help="只校验不写（EXIT 1 = 清单过期；2 = git 不可用）")
    args = ap.parse_args()
    if args.check:
        old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        new = build()
        # 只比对文件字典内容，忽略 generated 时间戳
        if old.get("files") != new["files"]:
            stale = [k for k in new["files"] if k not in old.get("files", {})]
            gone = [k for k in old.get("files", {}) if k not in new["files"]]
            print(f"[STALE] 缺失条目 {len(stale)}: {stale[:5]}")
            print(f"[STALE] 已删条目 {len(gone)}: {gone[:5]}")
            changed = [
                k for k in set(old.get("files", {})) & set(new["files"])
                if old["files"][k] != new["files"][k]
            ]
            print(f"[STALE] 内容变化 {len(changed)}: {changed[:8]}")
            return 1
        print("[OK] integrity_manifest 与实际文件一致")
        return 0

    manifest = build()
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 重生成 {MANIFEST.name}: {manifest['file_count']} 文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
