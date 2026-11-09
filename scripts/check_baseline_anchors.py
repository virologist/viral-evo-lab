#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_baseline_anchors.py —— 关键防线文件的包外基线对账（v1.5.8 · P2-7）
==========================================================================
背景：历史事故「联邦分发用旧基线覆盖 tests/」发生过两次，导致 CI 静默 0 覆盖。
      现有防御是包内跨文件互锚（guard ↔ test_vendor_core V7），但两个文件
      **同时**被旧基线覆盖时，包内没有任何参照能证明「防线被换了」。
      `AUDIT_STATE.md` §12 / Known Issues 一直把此列为「人工 diff 兜底」。

本脚本补上**包外独立参照**：基线 JSON 存放在审计区（不在专家包 git 仓内），
记录关键防线文件的 sha256 与字节数；本脚本只读对账，不改任何文件。

v1.5.9（ADR-003）：补**受控刷新**，把 v1.5.8 的「需人工手算 sha、mitigated」
      升级为可审计刷新：`--refresh` 须同时给 `--i-acknowledge-refresh` 与
      `--reason`，且工作区干净、锚在包外、被锚文件全部存在；刷新写
      `refresh_history` 并可追加治理仓 JSONL 日志。check 侧校验
      `source.commit == git HEAD` 与 history 末条一致，防「改锚刷绿」。

边界（诚实声明，防过度设计）：
  - **默认只读**：不带 --refresh 时不生成、不修复、不改写锚文件；漂移只报告并 EXIT=5
  - **刷新是人工动作**：脚本不自动刷新、不按时间刷新、不在 CI 里刷新
  - **不硬编码路径**：`--anchors` 必填、`--pkg-root` 可覆盖（默认本包根）
  - 只比 sha256 + bytes，**不判断漂移是否合理**：正常改动后应走 --refresh
    而不是改锚来「刷绿」
  - 路径安全：锚内相对路径拒绝绝对路径 / `..` 逃逸 / `.git` 目录

锚 JSON 格式：
    {
      "schema_version": 1,
      "generated": "2026-11-09T...",
      "source": {"tag": "v1.5.8", "commit": "<hash>", "note": "..."},
      "files": {"tests/test_contract_guard.py": {"sha256": "...", "bytes": 12345}}
    }

用法：
    python3 scripts/check_baseline_anchors.py --anchors <包外基线.json>
        [--pkg-root <包根>] [--json]
    python3 scripts/check_baseline_anchors.py --anchors <包外基线.json> --refresh \
        --i-acknowledge-refresh --reason "v1.5.9 定版：新增三脚本" \
        [--git-log <治理仓/anchor_refresh_log.jsonl>]

退出码契约：
    0 = 全部一致 / 刷新成功
    3 = 结构失败（锚缺失/畸形 / files 非法 / 路径不安全 / 刷新前置不满足）
    5 = 漂移（文件缺失 / 哈希或字节数不符 / commit 与 history 不一致 / 刷新被拒）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

EXIT_OK = 0
EXIT_STRUCT = 3
EXIT_DRIFT = 5


def _sha256(path: Path) -> str:
    """文件 sha256；读取失败由调用方按「漂移」处理。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_rel(rel: str) -> bool:
    """锚内相对路径合法性：非空 str、非绝对、无 .. 逃逸、不进 .git。"""
    if not isinstance(rel, str) or not rel.strip() or rel.startswith(("/", "\\")):
        return False
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or ".git" in p.parts:
        return False
    return True


def _git(root: Path, *args: str) -> str | None:
    """只读 git 查询；非 git 仓 / git 不可用时返回 None（不崩溃、不假装成功）。"""
    if not (root / ".git").exists():
        return None
    try:
        p = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True, timeout=20)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_head(root: Path) -> str | None:
    """当前 HEAD 完整 hash；拿不到返回 None。"""
    return _git(root, "rev-parse", "HEAD") or None


def check(anchors: Path, pkg_root: Path) -> tuple[int, dict]:
    """只读对账主逻辑：返回 (退出码, 报告字典)。所有失败路径有确定性退出码。"""
    rep: dict = {
        "anchors": str(anchors),
        "pkg_root": str(pkg_root),
        "expected": 0,
        "matched": 0,
        "missing": [],
        "mismatched": [],
        "structural_errors": [],
        "verdict": "",
    }

    try:
        obj = json.loads(anchors.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        rep["structural_errors"].append(
            f"锚文件不可读或非合法 JSON: {type(e).__name__}: {e}")
        rep["verdict"] = "ANCHOR_UNREADABLE"
        return EXIT_STRUCT, rep

    if not isinstance(obj, dict):
        rep["structural_errors"].append("锚文件顶层非对象")
        rep["verdict"] = "ANCHOR_NOT_OBJECT"
        return EXIT_STRUCT, rep

    # ADR-003 防「改锚刷绿」：锚的 commit 溯源必须与包内 git HEAD 一致，
    # 且刷新历史末条的 to_commit 不得与 HEAD 分叉。无 source / 非 git 仓跳过。
    src = obj.get("source")
    head = _git_head(pkg_root)
    if isinstance(src, dict) and head:
        if src.get("commit") and src["commit"] != head:
            rep["structural_errors"].append(
                f"锚 source.commit={str(src['commit'])[:7]}… 与 git HEAD={head[:7]}… 不符"
                "（疑改锚刷绿或忘记 --refresh）")
        hist = obj.get("refresh_history")
        if isinstance(hist, list) and hist:
            last = hist[-1] if isinstance(hist[-1], dict) else {}
            if last.get("to_commit") not in (None, head):
                rep["structural_errors"].append(
                    "refresh_history 末条 to_commit 与 HEAD 不一致（刷新链断裂）")

    if obj.get("schema_version") != 1:
        rep["structural_errors"].append(
            f"schema_version={obj.get('schema_version')!r} 非 1（未知锚格式，拒绝对账）")
    files = obj.get("files")
    if not isinstance(files, dict) or not files:
        rep["structural_errors"].append("files 缺失 / 非对象 / 为空")
    if rep["structural_errors"]:
        rep["verdict"] = "ANCHOR_SCHEMA_INVALID"
        return EXIT_STRUCT, rep

    rep["expected"] = len(files)
    for rel, meta in sorted(files.items()):
        if not _safe_rel(rel):
            rep["structural_errors"].append(f"非法锚路径: {rel!r}")
            continue
        if not isinstance(meta, dict) or not isinstance(meta.get("sha256"), str) \
                or len(meta["sha256"]) != 64 or not isinstance(meta.get("bytes"), int):
            rep["structural_errors"].append(f"{rel}: 条目缺合法 sha256/bytes")
            continue
        target = pkg_root / rel
        try:
            data = target.read_bytes()
        except OSError:
            rep["missing"].append(rel)
            continue
        got_sha = hashlib.sha256(data).hexdigest()
        if got_sha != meta["sha256"] or len(data) != meta["bytes"]:
            rep["mismatched"].append({
                "path": rel,
                "expected_sha256": meta["sha256"][:12],
                "actual_sha256": got_sha[:12],
                "expected_bytes": meta["bytes"],
                "actual_bytes": len(data),
            })
        else:
            rep["matched"] += 1

    if rep["structural_errors"]:
        rep["verdict"] = "ANCHOR_SCHEMA_INVALID"
        return EXIT_STRUCT, rep
    if rep["missing"] or rep["mismatched"]:
        rep["verdict"] = "DRIFT"
        return EXIT_DRIFT, rep
    rep["verdict"] = "OK"
    return EXIT_OK, rep


def refresh(anchors: Path, pkg_root: Path, reason: str, ack: bool,
            git_log: Path | None) -> tuple[int, dict]:
    """ADR-003 受控刷新：显式 ACK + 理由 + 干净工作区，缺一不写盘。

    唯一写盘动作是覆写包外锚（以及可选追加治理仓 JSONL）。
    拒绝「删掉漂移条目刷绿」：files 中被锚文件缺失即拒绝刷新。
    """
    rep: dict = {
        "anchors": str(anchors), "pkg_root": str(pkg_root), "reason": reason,
        "changed": [], "commit": "", "tag": "", "git_log": str(git_log) if git_log else "",
        "structural_errors": [], "verdict": "",
    }

    def fail(rc: int, msg: str) -> tuple[int, dict]:
        rep["structural_errors"].append(msg)
        rep["verdict"] = "REFRESH_REFUSED"
        return rc, rep

    if not ack:
        return fail(EXIT_STRUCT, "缺 --i-acknowledge-refresh（刷新是人工动作，必须显式确认）")
    if len(reason.strip()) < 8:
        return fail(EXIT_STRUCT, "--reason 须 ≥8 字符且说明改锚依据")
    try:
        a_res, r_res = anchors.expanduser().resolve(), pkg_root.expanduser().resolve()
        if a_res == r_res or r_res in a_res.parents:
            return fail(EXIT_STRUCT, "锚文件必须位于包外（包内锚无法独立证明防线未被覆盖）")
    except OSError as e:
        return fail(EXIT_STRUCT, f"路径解析失败: {type(e).__name__}: {e}")

    try:
        obj = json.loads(anchors.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        return fail(EXIT_STRUCT, f"锚不可读: {type(e).__name__}: {e}")
    files = obj.get("files") if isinstance(obj, dict) else None
    if not isinstance(files, dict) or not files:
        return fail(EXIT_STRUCT, "锚 files 缺失 / 为空")
    for rel in files:
        if not _safe_rel(rel):
            return fail(EXIT_STRUCT, f"非法锚路径: {rel!r}")
        if not (pkg_root / rel).is_file():
            return fail(EXIT_DRIFT, f"被锚文件缺失，拒绝刷新（防删条目刷绿）: {rel}")

    head = _git_head(pkg_root)
    if not head:
        return fail(EXIT_STRUCT, "包根非 git 仓 / git 不可用（无法留 commit 溯源）")
    status = _git(pkg_root, "status", "--porcelain")
    if status is None:
        return fail(EXIT_STRUCT, "git status 失败")
    if status.strip():
        return fail(EXIT_DRIFT, "工作区不干净；请先提交或清理，再从干净 commit 刷新锚")

    for rel, meta in sorted(files.items()):
        data = (pkg_root / rel).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if not isinstance(meta, dict) or meta.get("sha256") != sha or meta.get("bytes") != len(data):
            rep["changed"].append(rel)
        files[rel] = {"sha256": sha, "bytes": len(data)}

    tags = _git(pkg_root, "tag", "--points-at", "HEAD") or ""
    old_src = obj.get("source") if isinstance(obj.get("source"), dict) else {}
    tag = tags.splitlines()[-1].strip() if tags.strip() else str(old_src.get("tag", ""))
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    hist = obj.setdefault("refresh_history", [])
    if not isinstance(hist, list):
        hist = []
        obj["refresh_history"] = hist
    hist.append({
        "ts": ts, "from_commit": old_src.get("commit", ""), "to_commit": head,
        "tag": tag, "reason": reason, "changed_files": list(rep["changed"]),
    })
    obj["generated"] = ts
    obj["source"] = {
        "tag": tag, "commit": head,
        "note": str(old_src.get("note", "")) or "包外独立参照（ADR-003 受控刷新）",
    }
    try:
        anchors.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return fail(EXIT_STRUCT, f"锚写入失败: {type(e).__name__}: {e}")

    if git_log is not None:
        try:
            with git_log.expanduser().open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": ts, "commit": head, "tag": tag,
                                     "reason": reason, "changed_files": rep["changed"]},
                                    ensure_ascii=False) + "\n")
        except (OSError, UnicodeError) as e:
            # 锚已写成功，日志失败只降级警告（不回滚已完成的刷新）
            rep["structural_errors"].append(f"治理仓日志追加失败: {type(e).__name__}: {e}")

    rep["commit"], rep["tag"] = head, tag
    rep["verdict"] = "REFRESHED"
    return EXIT_OK, rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="关键防线文件包外基线对账（默认只读；--refresh 须显式 ACK）")
    ap.add_argument("--anchors", required=True,
                    help="包外基线 JSON 路径（必填；不硬编码，锚文件应不在专家包仓内）")
    ap.add_argument("--pkg-root", default=str(Path(__file__).resolve().parent.parent),
                    help="待对账的包根（默认本脚本所在专家包根）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告（供 CI 消费）")
    ap.add_argument("--refresh", action="store_true",
                    help="ADR-003 受控刷新：重算全部锚条目并写回（默认只读，不改任何文件）")
    ap.add_argument("--i-acknowledge-refresh", action="store_true",
                    help="刷新显式确认（缺此参数一律拒绝写盘）")
    ap.add_argument("--reason", default="", help="刷新理由（≥8 字符，写入 refresh_history 与治理仓日志）")
    ap.add_argument("--git-log", default=None, help="可选：治理仓锚刷新日志 JSONL（追加，供双位置对账）")
    args = ap.parse_args()

    anchors = Path(args.anchors).expanduser()
    root = Path(args.pkg_root).expanduser()
    if args.refresh:
        rc, rep = refresh(anchors, root, args.reason, args.i_acknowledge_refresh,
                          Path(args.git_log) if args.git_log else None)
        if args.json:
            print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
            return rc
        print(f"═══ 包外基线受控刷新 ═══\n锚: {rep['anchors']}\n理由: {rep['reason']}")
        print(f"commit {rep['commit'][:12] or '(未刷新)'} | tag {rep['tag'] or '(无)'}"
              f" | 变更文件 {len(rep['changed'])}")
        for rel in rep["changed"][:12]:
            print(f"  ↻ {rel}")
        for e in rep["structural_errors"]:
            print(f"  ❌ {e}")
        print(f"\n裁决: {rep['verdict']} → EXIT={rc}")
        return rc

    rc, rep = check(anchors, root)
    if args.json:
        print(json.dumps({"exit_code": rc, **rep}, ensure_ascii=False, indent=2))
        return rc

    print(f"═══ 包外基线对账 ═══\n锚: {rep['anchors']}\n包根: {rep['pkg_root']}")
    print(f"条目 {rep['expected']} | 一致 {rep['matched']} | 缺失 {len(rep['missing'])}"
          f" | 漂移 {len(rep['mismatched'])}")
    for rel in rep["missing"]:
        print(f"  ❌ 缺失: {rel}")
    for m in rep["mismatched"]:
        print(f"  ❌ 漂移: {m['path']} sha {m['expected_sha256']}… → {m['actual_sha256']}…"
              f" / bytes {m['expected_bytes']} → {m['actual_bytes']}")
    for e in rep["structural_errors"]:
        print(f"  ❌ 结构: {e}")
    label = {EXIT_OK: "✅ OK", EXIT_STRUCT: "❌ 锚结构失败", EXIT_DRIFT: "❌ 漂移"}
    print(f"\n裁决: {rep['verdict']} {label.get(rc, '')} → EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
