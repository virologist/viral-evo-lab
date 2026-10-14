#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
verify_numbers.py —— 成员产出关键数字核验关卡（V 层 · R12 2026-10-14）
=======================================================================
设计动机：LLM 成员可能编造或错引关键数字（n=/p=/D′/百分比/CI）。
思路：**结构化校验属确定性工程**——对成员产出中的关键数字，自动在
权威源 CSV/JSON（计算产物）中 grep 同值；找不到 = 降级信号。

边界（严格守）：
    本脚本只做「数字存在性核对」这种确定性匹配；
    「这个数字在科学上对不对 / 该不该用」仍是 LLM 与人的判断。

用法：
    # 核验一份成员产出（默认权威源目录 = 04_H5 M 统计链输出）
    python3 verify_numbers.py <产出文件.md> \
        --sources <权威源目录或文件...> [--min-digits 3] [--json]

    # 与装配脚本联动：task_payload 已注入本脚本的成员，可在自检段调用

规则：
    1. 从产出中提取"关键数字模式"：
       - 百分比  (\d+\.?\d*\s*%)
       - n= / n = / (n = xxx)
       - p = 0.xxx / p=xxx
       - D′ / D' = 0.xxx
       - CI [...] 区间两端
    2. 过滤：纯年份(1990-2030)、版本号(v1.2)、表内序号(1. 2. 3.)、行号
    3. 每个数字在权威源集合（*.csv/*.json/*.md 的文本拼接）中做精确 grep
    4. 输出：found / not_found 两清单 + 退出码（0=全found或无数字；5=有not_found）

退出码：0 = 通过；3 = 产出文件缺失；5 = 存在未溯源数字（envelope 应降级 partial）
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 权威数字模式（保守：只抓最易造假/最关键的四类 + CI）
PATTERNS = [
    ("pct",   re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")),
    ("n_eq",  re.compile(r"\bn\s*=\s*(\d{2,6})\b", re.I)),
    ("p_val", re.compile(r"\bp\s*=\s*(0\.\d+|\d\.\d+e-?\d+|\d\.\d+)", re.I)),
    ("dprime",re.compile(r"D[′']\s*=\s*([+-]?\d\.\d+)")),
    ("ci",    re.compile(r"CI\s*[\[（(]\s*([+-]?\d\.\d+)\s*,\s*([+-]?\d\.\d+)\s*[\]）)]")),
]
# 排除：年份 / 版本号（须带 v 前缀或多级 x.y.z，纯小数如 0.9441 不是版本）/ 纯小数序号
YEAR = re.compile(r"^20[0-2]\d$")
VERSION = re.compile(r"^[vV]\d+(\.\d+){1,2}$|^\d+\.\d+\.\d+$")

def extract_numbers(text: str, min_digits: int):
    """返回 [(kind, value_str, norm_str)]，norm 用于 grep。"""
    out = []
    for kind, pat in PATTERNS:
        for m in pat.finditer(text):
            if kind == "ci":
                for g in (1, 2):
                    v = m.group(g)
                    if YEAR.match(v):
                        continue
                    out.append((kind, v, v))
            else:
                v = m.group(1)
                if YEAR.match(v) or VERSION.match(v):
                    continue
                # n= 太小（如 n=5）多为示意，跳过；min_digits 默认 2 位以上
                if kind == "n_eq" and len(v.lstrip("0")) < min_digits:
                    continue
                out.append((kind, v, v))
    # 去重
    seen, uniq = set(), []
    for k, v, n_ in out:
        key = (k, v)
        if key not in seen:
            seen.add(key); uniq.append((k, v, n_))
    return uniq

def load_sources(paths: list[str], exclude: list[str] | None = None, allow_md: bool = False) -> str:
    """把权威源（csv/json/md/txt）读成一个大文本（grep 池）；exclude=**文件名**关键字黑名单。

    2026-10-21 修：exclude 曾匹配完整路径（str(f)），导致父目录名含关键字时
    整个目录被误杀（如 /tmp/vmo_test/ 被 --exclude "_" 清空）。现仅匹配 f.name。
    """
    exclude = exclude or []
    chunks = []
    for sp in paths:
        p = Path(sp)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if any(x in f.name for x in exclude):
                    continue
                ok_suffix = (".csv", ".json", ".md", ".txt") if allow_md else (".csv", ".json")
                if f.suffix.lower() in ok_suffix and f.is_file():
                    try:
                        chunks.append(f.read_text(encoding="utf-8", errors="ignore"))
                    except OSError:
                        pass
        else:
            ok_suffix2 = (".csv", ".json", ".md", ".txt") if allow_md else (".csv", ".json")
            if not (p.is_file() and p.suffix.lower() in ok_suffix2):
                continue
            if any(x in p.name for x in exclude):
                continue
            chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)

def main() -> int:
    ap = argparse.ArgumentParser(description="成员产出关键数字核验关卡")
    ap.add_argument("artifact", help="成员产出文件（md/txt）")
    ap.add_argument("--sources", nargs="+", required=True,
                    help="权威源目录/文件（可多个）")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="排除的路径关键字（已被证伪/幻觉载体文件）")
    ap.add_argument("--allow-md", action="store_true",
                    help="允许 md/txt 作权威源（默认排除：叙述层不可为数字权威，防循环自证）")
    ap.add_argument("--min-digits", type=int, default=2,
                    help="n= 值最小位数（默认2，即 n>=10 才核）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    art = Path(args.artifact)
    if not art.is_file():
        print(f"[verify_numbers] 产出文件不存在: {art}", file=sys.stderr)
        return 3
    text = art.read_text(encoding="utf-8", errors="ignore")
    nums = extract_numbers(text, args.min_digits)
    pool = load_sources(args.sources, args.exclude, args.allow_md)

    found, not_found = [], []
    for kind, val, _ in nums:
        # 归一化 grep：原值 与 保留形式都试
        cands = {val}
        try:
            f = float(val)
            # 只补零扩展精度（20.58 → 20.580/20.5800），禁止截断（:g/:1f 会造假阳性）
            cands |= {f"{f:.2f}", f"{f:.3f}", f"{f:.4f}"} if f >= 1 else {f"{f:.3f}", f"{f:.4f}", f"{f:.5f}"}
        except ValueError:
            pass
        hit = any(c in pool for c in cands)
        (found if hit else not_found).append({"kind": kind, "value": val})

    result = {
        "artifact": str(art),
        "checked": len(nums),
        "found": len(found),
        "not_found": len(not_found),
        "not_found_list": not_found,
        "verdict": "PASS" if not not_found else "DEGRADE_TO_PARTIAL",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[verify_numbers] {result['verdict']}  "
              f"checked={result['checked']} found={result['found']} "
              f"not_found={result['not_found']}")
        for x in not_found:
            print(f"  🔴 {x['kind']}: {x['value']}  ← 权威源中未溯源")
        if not_found:
            print("  → envelope.status 应降级 partial，或补 [待人工核验] 标注")
    return 5 if not_found else 0

if __name__ == "__main__":
    sys.exit(main())
