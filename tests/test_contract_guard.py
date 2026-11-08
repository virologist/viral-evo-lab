#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
契约与分发守卫（P3.2 · 2026-11-07）
=====================================================================
背景：本日联邦 shared-core 分发两次（10:14 / 17:43）以旧基线模板覆盖
      tests/test_vendor_core.py，把 A2 修复回退成 triz 残留版、pytest 入口
      消失（CI 静默 0 覆盖）；同时刷新 vendor 副本与 VENDOR.json。
      手工救火两次后，本守卫把「分发后的包是否仍处于正确状态」变成常态
      自动判定：任一不符即 FAIL，并给出恢复命令。

校验五项（每项独立异常兜底，守卫自身不得因畸形输入崩溃）：
  1. test_vendor_core.py 的包名与 pytest 入口  → 抓 A2 回退
  2. 四处 version 一致性                        → 抓版本叙事漂移
  3. integrity_manifest.json 与磁盘 + git ls-files 一致
                                               → 抓内容漂移与新增文件漏收
  4. 联邦真源 / vendor 副本 / VENDOR.json 三方 sha256 一致
                                               → 抓分发不同步
  5. require_tag 闸三点接线存活                → 抓产出端核验被静默摘除

运行：python3 tests/test_contract_guard.py  或  pytest tests/ -q
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FED = PKG.parent / "shared-core" / "assemble_spawn_prompt.py"
VENDOR_PY = PKG / "vendor" / "shared-core" / "assemble_spawn_prompt.py"
VENDOR_JSON = PKG / "vendor" / "shared-core" / "VENDOR.json"
TVC = PKG / "tests" / "test_vendor_core.py"
MANIFEST = PKG / "integrity_manifest.json"
VERSION_FILES = (
    ".claude-plugin/plugin.json",
    ".codebuddy-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
)
RECOVER = ("git checkout <本包最新 commit> -- tests/test_vendor_core.py && "
           "git add -A && python3 scripts/gen_integrity_manifest.py")


def _sha(path: Path) -> str:
    """文件 sha256；读取失败抛 OSError 由各检查项捕获。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_obj(path: Path) -> dict:
    """统一 JSON 消费入口：非对象顶层一律判为畸形（P3.1 同类崩溃防线）。"""
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path.name} 顶层非对象")
    return obj


def _checks() -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []

    # 1. A2 回退检测 -------------------------------------------------------
    try:
        t = TVC.read_text(encoding="utf-8")
        m = re.search(r'_PKG_NAME\s*=\s*"([^"]+)"', t)
        name = m.group(1) if m else "缺失"
        entry = "def test_vendor_core" in t
        ok = name == "viral-evo-lab" and entry
        msg = (f"A2 存活（_PKG_NAME=viral-evo-lab + pytest 入口）"
               f" [name={name}, entry={entry}]")
        out.append((ok, msg if ok else f"{msg} → 恢复命令: {RECOVER}"))
    except (OSError, UnicodeError, ValueError) as e:
        out.append((False, f"A2 存活：读取失败 {type(e).__name__}: {e} → {RECOVER}"))

    # 2. 四处 version ------------------------------------------------------
    try:
        vers: list[str] = []
        for rel in VERSION_FILES:
            d = _load_obj(PKG / rel)
            vers.append(str(d.get("version", d.get("metadata", {}).get("version"))))
            if rel.endswith("marketplace.json"):
                plugs = d.get("plugins")
                if not isinstance(plugs, list) or not plugs or not isinstance(plugs[0], dict):
                    raise ValueError("marketplace.json plugins 结构异常")
                vers.append(str(plugs[0].get("version")))
        ok = len(vers) == 4 and len(set(vers)) == 1
        out.append((ok, f"四处 version 一致 {vers}"))
    except (OSError, UnicodeError, ValueError, KeyError, AttributeError) as e:
        out.append((False, f"四处 version：校验失败 {type(e).__name__}: {e}"))

    # 3. manifest 与磁盘 + git ls-files 一致 --------------------------------
    try:
        man = _load_obj(MANIFEST)
        files = man.get("files")
        if not isinstance(files, dict):
            raise ValueError("manifest.files 非对象")
        bad: list[str] = []
        for rel, meta in files.items():
            p = PKG / rel
            if not isinstance(meta, dict) or not isinstance(meta.get("sha16"), str):
                bad.append(f"条目畸形:{rel}")
                continue
            if not p.is_file():
                bad.append(f"缺失:{rel}")
                continue
            try:
                if p.stat().st_size != meta.get("bytes") or _sha(p)[:16] != meta["sha16"]:
                    bad.append(f"变化:{rel}")
            except OSError:
                bad.append(f"不可读:{rel}")
        # 新增已跟踪文件是否漏收（gen_integrity_manifest.py 以 git ls-files 为源）
        try:
            tracked = set(subprocess.run(
                ["git", "-C", str(PKG), "ls-files"],
                capture_output=True, text=True, check=True, timeout=30,
            ).stdout.splitlines()) - {"integrity_manifest.json", ""}
            missing = sorted(tracked - set(files))
            extra = sorted(set(files) - tracked)
            set_bad = bool(missing or extra)
        except (subprocess.SubprocessError, OSError) as e:
            missing, extra, set_bad = [], [], False
            bad.append(f"git ls-files 不可用: {type(e).__name__}")
        count_ok = man.get("file_count") == len(files)
        ok = not bad and not set_bad and count_ok
        detail = f" 不一致 {bad[:5]}" if bad else ""
        if set_bad:
            detail += f" 漏收={missing[:5]} 多收={extra[:5]}"
        if not count_ok:
            detail += f" file_count={man.get('file_count')}≠{len(files)}"
        out.append((ok, f"manifest 一致（{len(files)} 文件）{detail}"))
    except (OSError, UnicodeError, ValueError, KeyError, AttributeError) as e:
        out.append((False, f"manifest：校验失败 {type(e).__name__}: {e}"))

    # 4. vendor 三方哈希 ----------------------------------------------------
    try:
        vj = _load_obj(VENDOR_JSON)
        declared = vj.get("sha256")
        if not isinstance(declared, str):
            raise ValueError("VENDOR.json sha256 非字符串")
        a = _sha(FED) if FED.is_file() else ""
        b = _sha(VENDOR_PY)
        ok = bool(a) and a == b == declared
        out.append((ok, "vendor 三方哈希一致 "
                        f"[fed={a[:12]} vendor={b[:12]} 清单={declared[:12]}]"))
    except (OSError, UnicodeError, ValueError, KeyError, AttributeError) as e:
        out.append((False, f"vendor 三方哈希：校验失败 {type(e).__name__}: {e}"))

    # 5. require_tag 闸三点接线存活（C3 · 2026-11-08）----------------------
    try:
        targets = ("verify_numbers.py", "verify_member_output.py", "check_gates.py")
        bad = []
        for fn in targets:
            t = (PKG / "scripts" / fn).read_text(encoding="utf-8")
            for needle in ("--require-tag", "require_tag=args.require_tag"):
                if needle not in t:
                    bad.append(f"{fn} 缺 {needle}")
        out.append((not bad, "require_tag 闸三点接线存活" if not bad else "; ".join(bad)))
    except (OSError, UnicodeError) as e:
        out.append((False, f"require_tag 闸：校验失败 {type(e).__name__}: {e}"))

    return out


def test_contract_guard() -> None:
    """pytest 入口：任一守卫项失败即 FAIL。"""
    results = _checks()
    failures = [msg for ok, msg in results if not ok]
    assert not failures, "契约/分发守卫失败:\n  " + "\n  ".join(failures)


def main() -> int:
    results = _checks()
    for ok, msg in results:
        print(("  ✅ " if ok else "  ❌ ") + msg)
    n_ok = sum(ok for ok, _ in results)
    print(f"\n守卫项 {len(results)} | 通过 {n_ok} | 失败 {len(results) - n_ok}")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
