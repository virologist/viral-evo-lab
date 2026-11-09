#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shared-core 分发与防漂移门禁（v3.4.2 P0-1 配套，2026-10-15 适配至本包）
=====================================================================
目的：修复「R9 联邦下沉后 git clone 直跑 shim 退出码 3」的可安装性回归，
      同时用哈希比对防止 vendor 兜底副本与联邦真源产生漂移。
适配：多包共用门禁模板（同源模板曾流经 smart-textbook-team / triz-invention-team）；
      本包改 _INSTALL_DIR / MEMBER_IDS / V6 临时目录名三处包耦合。
      [2026-11-07 A2 修正] _PKG_NAME 改本包名（原复制残留 triz-invention-team）；
      V6 断言改为符合本包现实——scripts/assemble_spawn_prompt.py 是独立实现
      （无 shim/vendor 回退机制），隔离目录冒烟只断言「退出码 0 + 全成员」；
      补 pytest 可收集入口 test_vendor_core()（原文件无 test_* 函数，
      pytest 收集 0 例，CI 静默零覆盖）。

检查项：
  V1  vendor/shared-core/assemble_spawn_prompt.py 存在
  V2  VENDOR.json 存在且可解析
  V3  vendor 副本 sha256 == VENDOR.json.sha256（清单自洽，任何场景都查）
  V4  联邦真源存在时 vendor == 联邦（防漂移；联邦缺失 → SKIP，git/CI 场景不误报）
  V5  冒烟：python3 scripts/assemble_spawn_prompt.py --list-members 退出码 0
      且输出含全部成员 ID（真执行，非静态断言）
  V6  冒烟：联邦缺失模拟（SHIM 隔离目录）——把包拷到临时目录跑，仍须退出码 0
      （证明 git clone 态开箱可用；这是 P0-1 的验收核心）

用法：
  python3 tests/test_vendor_core.py [--expert-dir 路径] [--json]
退出码：0 全通过 | 1 有失败项
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_PKG_NAME = "viral-evo-lab"
_INSTALL_DIR = os.path.expanduser(
    "~/.workbuddy/plugins/marketplaces/my-experts/plugins/" + _PKG_NAME
)
_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 与包内主测试同策略：CI/纯 clone 态回落到仓库自身
DEFAULT_EXPERT_DIR = (
    _REPO_DIR
    if os.path.exists(os.path.join(_REPO_DIR, ".codebuddy-plugin", "plugin.json"))
    else _INSTALL_DIR
)
CORE_REL = os.path.join("vendor", "shared-core", "assemble_spawn_prompt.py")
MANIFEST_REL = os.path.join("vendor", "shared-core", "VENDOR.json")
MEMBER_IDS = [
    "hypothesis-officer",
    "phylo-analyst",
    "popgen-modeler",
    "predictive-virologist",
    "structural-virologist",
    "literature-scout",
    "pipeline-engineer",
    "research-diagnostician",
    "archivist",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_federal(pkg_root, max_up=4):
    """与 shim 同逻辑：从包根父目录起向上找联邦 shared-core/。"""
    d = os.path.dirname(pkg_root)
    for _ in range(max_up):
        cand = os.path.join(d, "shared-core", "assemble_spawn_prompt.py")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


class Result:
    def __init__(self):
        self.items = []          # (id, desc, status, detail) status: PASS/FAIL/SKIP

    def add(self, cid, desc, status, detail=""):
        self.items.append((cid, desc, status, detail))

    @property
    def failed(self):
        return [i for i in self.items if i[2] == "FAIL"]


def run_checks(expert_dir):
    r = Result()
    core_path = os.path.join(expert_dir, CORE_REL)
    manifest_path = os.path.join(expert_dir, MANIFEST_REL)

    # V1 vendor 副本存在
    if not os.path.isfile(core_path):
        r.add("V1", "vendor/shared-core/assemble_spawn_prompt.py 存在", "FAIL", core_path)
        r.add("V2", "VENDOR.json 存在且可解析", "SKIP", "V1 失败，跳过")
        r.add("V3", "vendor sha256 == VENDOR.json.sha256", "SKIP", "V1 失败，跳过")
        r.add("V4", "vendor == 联邦真源（防漂移）", "SKIP", "V1 失败，跳过")
    else:
        r.add("V1", "vendor/shared-core/assemble_spawn_prompt.py 存在", "PASS")
        vendor_sha = sha256(core_path)

        # V2 清单可解析
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            r.add("V2", "VENDOR.json 存在且可解析", "PASS")
        except (OSError, json.JSONDecodeError) as e:
            manifest = {}
            r.add("V2", "VENDOR.json 存在且可解析", "FAIL", str(e))

        # V3 清单自洽
        want = manifest.get("sha256", "")
        r.add("V3", "vendor sha256 == VENDOR.json.sha256",
              "PASS" if want == vendor_sha else "FAIL",
              "" if want == vendor_sha else f"清单 {want[:12]}… vs 实际 {vendor_sha[:12]}…")

        # V4 防漂移（联邦存在才比对）
        fed = find_federal(expert_dir)
        if fed is None:
            r.add("V4", "vendor == 联邦真源（防漂移）", "SKIP",
                  "联邦 core 缺失（git/CI 态），按设计跳过")
        else:
            fed_sha = sha256(fed)
            r.add("V4", "vendor == 联邦真源（防漂移）",
                  "PASS" if fed_sha == vendor_sha else "FAIL",
                  "" if fed_sha == vendor_sha else
                  f"漂移！联邦 {fed_sha[:12]}… vs vendor {vendor_sha[:12]}…；"
                  f"同步: cp {fed} {core_path} 并更新 VENDOR.json")

    # V5 安装态冒烟（走联邦真源）
    script = os.path.join(expert_dir, "scripts", "assemble_spawn_prompt.py")
    try:
        p = subprocess.run([sys.executable, script, "--list-members"],
                           capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        missing = [m for m in MEMBER_IDS if m not in out]
        ok = p.returncode == 0 and not missing
        r.add("V5", "安装态冒烟 --list-members 退出码 0 且含全部成员",
              "PASS" if ok else "FAIL",
              "" if ok else f"exit={p.returncode} 缺失成员={missing} out={out[:200]}")
    except (OSError, subprocess.SubprocessError) as e:
        r.add("V5", "安装态冒烟 --list-members 退出码 0 且含全部成员", "FAIL", str(e))

    # V6 git-clone 态冒烟：拷到临时目录（其父目录无 shared-core）→ 必须走 vendor 兜底
    tmp_root = tempfile.mkdtemp(prefix="trot-clone-sim-")
    try:
        tmp_pkg = os.path.join(tmp_root, _PKG_NAME)
        shutil.copytree(expert_dir, tmp_pkg,
                        ignore=shutil.ignore_patterns(".git"))
        if find_federal(tmp_pkg) is not None:
            r.add("V6", "git-clone 态冒烟（隔离目录独立实现可用）", "SKIP",
                  "临时目录意外命中联邦 core，无法隔离")
        else:
            env = dict(os.environ, SHIM_DEBUG="1")
            p = subprocess.run(
                [sys.executable, os.path.join(tmp_pkg, "scripts", "assemble_spawn_prompt.py"),
                 "--list-members"],
                capture_output=True, text=True, timeout=60, env=env)
            out = p.stdout + p.stderr
            missing = [m for m in MEMBER_IDS if m not in out]
            # 本包 scripts/ 版是独立实现（无 shim/vendor 回退）：
            # 隔离态验收 = 退出码 0 + 全部成员 ID 可列出
            ok = p.returncode == 0 and not missing
            r.add("V6", "git-clone 态冒烟（隔离目录退出码 0 且全成员）",
                  "PASS" if ok else "FAIL",
                  "" if ok else f"exit={p.returncode} 缺失={missing} out={out[:250]}")
    except (OSError, subprocess.SubprocessError) as e:
        r.add("V6", "git-clone 态冒烟（隔离目录走 vendor 兜底）", "FAIL", str(e))
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    # V7 守卫互锚（R-13b · 2026-11-09；L3 盲检 R1 加固 · 2026-11-09）--------
    # 背景：历史事故「tests 被旧基线覆盖 → CI 静默 0 覆盖」发生过两次。实测
    # 发现 test_contract_guard.py 自身无任何守卫锚定——空壳化 + 重生成
    # integrity_manifest 后 EXIT=0 全静默（manifest 记录"当前是什么"而非
    # "应该是什么"）。本项从另一文件反向锚定守卫的存在性，形成跨文件互锚：
    #   删/空壳化 test_contract_guard.py → 本项 FAIL
    #   删/空壳化 test_vendor_core.py   → guard 第 1 项（A2 锚定本文件）FAIL
    # 【L3 盲检 R1 加固】字符串锚可被「语义空壳化」绕过（_checks 改恒真但
    # 保留锚字符串 → V7 仍 PASS，已实验证实）。现加两层行为锚：
    #   ① 金丝雀：importlib 真加载 guard 模块，动态注入畸形 manifest 后
    #     调 _checks()，断言第 3 项真实 FAIL（行为≠恒真）；
    #   ② 守卫项数下限：len(results) ≥ 8（空壳 return 1 条即被抓）。
    import importlib.util
    guard_rel = os.path.join("tests", "test_contract_guard.py")
    guard_path = os.path.join(expert_dir, guard_rel)
    try:
        with open(guard_path, encoding="utf-8") as f:
            gsrc = f.read()
        needles = [
            "def _checks",                # 守卫主体函数
            "def test_contract_guard",    # pytest 可收集入口（防收集数静默归零）
            "def main",                   # 直跑入口
            "sys.exit(main())",           # 退出码契约（失败≠0）
            "A2 存活",                    # 第 1 项标题（守卫内容未被整体替换）
            "A-1 修复存活守卫",            # 第 7 项标题（守卫版本未回退）
        ]
        missing = [n for n in needles if n not in gsrc]
        # ② 项数下限（R1）：恒真空壳通常 return 1 条；真实守卫 ≥8 项
        # 三轮🟢7：删除死变量 m_cnt（原 re.search 结果从未使用）
        cnt_anchors = sum(gsrc.count(p) for p in ('out.append((True', 'out.append((False', "out.append((not bad"))
        if cnt_anchors < 8:
            missing.append(f"守卫项断言数仅 {cnt_anchors}（<8）——疑语义空壳化")
        # ① 金丝雀（R1）：真加载 + 畸形输入下第 3 项必须真实 FAIL
        if not missing:
            try:
                spec = importlib.util.spec_from_file_location("_guard_canary", guard_path)
                gmod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(gmod)
                with tempfile.TemporaryDirectory(prefix="v7canary_") as td:
                    bad_pkg = os.path.join(td, "pkg")
                    shutil.copytree(expert_dir, bad_pkg,
                                    ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__"))
                    with open(os.path.join(bad_pkg, "integrity_manifest.json"), "w", encoding="utf-8") as fm:
                        fm.write('{"files": "not-a-dict", "file_count": -1}')
                    res = gmod._checks_at(Path(bad_pkg))
                # 第 3 项（manifest 一致性）在畸形 manifest 下必须 FAIL
                item3 = res[2] if len(res) > 2 else (True, "缺失")
                if item3[0]:
                    missing.append("金丝雀失败：畸形 manifest 下守卫第 3 项仍 PASS（恒真嫌疑）")
            except Exception as e:  # noqa: BLE001 —— 金丝雀自身任何异常 = 锚定失败
                missing.append(f"金丝雀加载/执行失败: {type(e).__name__}: {e}")
        r.add("V7", "守卫互锚：test_contract_guard.py 存活 + 项数下限 + 行为金丝雀",
              "PASS" if not missing else "FAIL",
              "" if not missing else f"缺失锚点={missing}（守卫可能被空壳化/语义改写）"
                                     f"→ 恢复: git checkout <最新commit> -- {guard_rel}")
    except OSError as e:
        r.add("V7", "守卫互锚：test_contract_guard.py 存活 + 项数下限 + 行为金丝雀", "FAIL",
              f"读取失败 {e}（守卫文件缺失？）")

    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expert-dir", default=DEFAULT_EXPERT_DIR)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    r = run_checks(args.expert_dir)
    failed = r.failed

    if args.json:
        print(json.dumps({"passed": len(r.items) - len(failed),
                          "total": len(r.items),
                          "items": [{"id": i[0], "desc": i[1], "status": i[2],
                                     "detail": i[3]} for i in r.items]},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 62)
        print("shared-core 分发与防漂移门禁（viral-evo-lab）")
        print("=" * 62)
        for cid, desc, status, detail in r.items:
            mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "-"}[status]
            print(f"  {mark} [{cid}] {status:<4} {desc}")
            if detail:
                print(f"          → {detail}")
        n_pass = sum(1 for i in r.items if i[2] == "PASS")
        print("-" * 62)
        print(f"检查项 {len(r.items)} | 通过 {n_pass} | 失败 {len(failed)}")
        print("=" * 62)
    return 0 if not failed else 1


def test_vendor_core():
    """pytest 可收集入口：断言全部检查项无 FAIL（SKIP 不算失败）。"""
    r = run_checks(DEFAULT_EXPERT_DIR)
    assert not r.failed, "防漂移门禁失败项: " + "; ".join(
        f"[{cid}] {detail}" for cid, _, _, detail in r.failed
    )


if __name__ == "__main__":
    sys.exit(main())
