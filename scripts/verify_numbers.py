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

退出码：0 = 通过；3 = 产出文件缺失/不可解码（证据源不可用）；5 = 存在未溯源数字（envelope 应降级 partial）

R4.1（2026-11-18 · backlog D）：全包禁用 errors="ignore" 静默吞字节——UTF-16/BOM
等畸形编码若被吞成空文本会让「未溯源数字」误放行（fail-open）。一律严格 utf-8-sig
解码 + 捕获 UnicodeError：产出解码失败→契约码 3；权威源解码失败→跳过该源（不进池）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# R4.2（2026-11-19 · 盲检🔴1）：统一严格读守卫——无 BOM UTF-16 的 NUL 交错在
# UTF-8 下是合法字节，单独捕获 UnicodeError 防不住，必须显式检测控制字符。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text_guard import read_text_checked, has_split_number  # noqa: E402

# 权威数字模式（保守：只抓最易造假/最关键的四类 + CI）
PATTERNS = [
    ("pct",   re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")),
    ("n_eq",  re.compile(r"\bn\s*=\s*(\d{2,6})\b", re.I)),
    ("p_val", re.compile(r"\bp\s*=\s*(0\.\d+|\d\.\d+e-?\d+|\d\.\d+)", re.I)),
    ("dprime",re.compile(r"D[′']\s*=\s*([+-]?\d\.\d+)")),
    ("ci",    re.compile(r"CI\s*[\[（(]\s*([+-]?\d\.\d+)\s*,\s*([+-]?\d\.\d+)\s*[\]）)]")),
]
# 排除：年份 / 版本号（须带 v 前缀或多级 x.y.z，纯小数如 0.9441 不是版本）/ 纯小数序号
# C6（2026-11-07）：年份 ^20[0-2]\d$ → ^20\d{2}$（原实现 2030+ 失效）
YEAR = re.compile(r"^20\d{2}$")
VERSION = re.compile(r"^[vV]\d+(\.\d+){1,2}$|^\d+\.\d+\.\d+$")

# R4.3（两路盲检交叉验证的 fail-open）：关键标记与数字之间被插入字符时，
# PATTERNS 全部失配 → checked=0 → 「无数字即 PASS」。实测变体：
#   p = 👨‍👩 0.9      （emoji 插在 = 与数字之间）
#   n = ⭐888         （符号插在 = 与数字之间）
# 判据：关键标记（n=/p=/D'/CI）之后的首个非空白字符不是数字 → 标记未接上数字。
# CI 括号形态（"CI [0.1, 0.2]"）不适用此判据（标记后是括号），单独排除。
KEY_MARKERS = re.compile(r"(?:\bn\s*=|\bp\s*=|D[′']\s*=|CI\s*[\[（(])", re.I)


def has_broken_key_pattern(text: str) -> bool:
    r"""文本中是否存在「关键标记与数字被隔开/数字被空白拆段」的结构（正则必然失配）。

    两类：① 标记后首个非空白字符不是数字（emoji/符号隔断）；
          ② 标记后数字被空白拆成多段（n = 1 2 3 → \d{2,6} 失配）。
    """
    for m in KEY_MARKERS.finditer(text):
        tail = text[m.end():m.end() + 12].lstrip()
        if not tail:
            continue
        if tail[0].isdigit():
            # R4.4（主代理对抗实证）：数字被**空白**拆成多段（n = 1 2 3）时，
            # \d{2,6} / 0\.\d+ 要求连续数字 → 全部失配 → checked=0 → PASS fail-open。
            # has_split_number 只管非空白隔断（[^\d\s]），放行空白，故此通道此前漏网。
            # 判据：标记后首个数字 token 紧跟「空白 + 数字」即判隔断。
            # 不误伤：n = 5（min_digits=2 有意跳过）、n = 30 例、p = 0.05 vs 0.01、
            # CI [0.1, 0.2]（逗号非空白，不匹配）。
            if re.match(r"^\d{1,6}(?:\.\d+)?\s+\d", tail):
                return True
            continue  # 标记后紧跟完整数字 → 正常
        if m.group(0).rstrip().endswith(("(", "[", "（", "[")):
            continue  # CI 括号形态：标记后是括号，不是数字
        return True
    return False

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

def float_candidates(val: str) -> set:
    """R2-8（2026-10-15）：浮点候选集公共实现（仅补零扩展，禁截断——截断会造假阳性）。
    三处消费方（verify_numbers/verify_member_output/check_gates）统一走这里，防精度规则漂移。
    """
    cands = {val}
    try:
        f = float(val)
        cands |= ({f"{f:.2f}", f"{f:.3f}", f"{f:.4f}"} if f >= 1
                  else {f"{f:.3f}", f"{f:.4f}", f"{f:.5f}"})
    except ValueError:
        pass
    return cands


def pool_has_number(pool: str, cand: str) -> bool:
    """候选数值是否作为**完整数字 token** 出现在权威池中（R4.3 单一事实源）。

    R4.3（盲检🟠4）：原实现用 `cand in pool` 子串匹配，导致编造数字可被
    权威源里的更长数字洗白——
      p = 0.94  命中池中 "0.9441"   → 假阳性 PASS
      p=0.98   命中池中 "10.980"   → 假阳性 PASS
    改为 token 边界匹配：候选值前后不得紧邻数字或小数点（. 与 , 视为数字延续），
    即池中必须是与候选值等值的独立数字 token。
    """
    if not cand:
        return False
    pat = re.compile(r"(?<![\d.])" + re.escape(cand) + r"(?![\d.])")
    return pat.search(pool) is not None


def load_sources(paths: list[str], exclude: list[str] | None = None, allow_md: bool = False,
                 require_tag: bool = False) -> str:
    """把权威源（csv/json/md/txt）读成一个大文本（grep 池）；exclude=**文件名**关键字黑名单。

    2026-10-14 修：exclude 曾匹配完整路径（str(f)），导致父目录名含关键字时
    整个目录被误杀（如 /tmp/vmo_test/ 被 --exclude "_" 清空）。现仅匹配 f.name。

    T-C4（2026-10-15，LRN-005 防线）：require_tag=True 时仅加载文件头部 3 行
    含 `source_tag: authoritative` 的源——杜绝 smoke 演练的假数据混入权威池
    （LRN-005 复发防线）。默认 False 向后兼容；生产环境建议开 True。
    """
    exclude = exclude or []
    chunks = []

    def tagged(f: Path) -> bool:
        txt, _ = read_text_checked(f, max_chars=400)
        # R4.1/R4.2：解码失败或控制字符污染视为无标记（fail-closed，该源不进权威池）
        return txt is not None and "source_tag: authoritative" in "".join(txt.splitlines()[:3])

    for sp in paths:
        p = Path(sp)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if any(x in f.name for x in exclude):
                    continue
                ok_suffix = (".csv", ".json", ".md", ".txt") if allow_md else (".csv", ".json")
                if f.suffix.lower() in ok_suffix and f.is_file():
                    if require_tag and not tagged(f):
                        continue
                    src_txt, _ = read_text_checked(f)
                    if src_txt is not None:
                        chunks.append(src_txt)
                    # R4.1/R4.2：畸形/控制字符污染源跳过，不静默吞字节进池
        else:
            ok_suffix2 = (".csv", ".json", ".md", ".txt") if allow_md else (".csv", ".json")
            if not (p.is_file() and p.suffix.lower() in ok_suffix2):
                continue
            if any(x in p.name for x in exclude):
                continue
            if require_tag and not tagged(p):
                continue
            src_txt, _ = read_text_checked(p)
            if src_txt is not None:
                chunks.append(src_txt)
            # R4.1/R4.2：畸形源跳过（单文件路径分支）
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
    ap.add_argument("--require-tag", action="store_true",
                    help="严审模式：权威源头部 3 行须含 source_tag: authoritative；未标记源一律拒收（默认关闭，向后兼容）")
    args = ap.parse_args()

    art = Path(args.artifact)
    if not art.is_file():
        print(f"[verify_numbers] 产出文件不存在: {art}", file=sys.stderr)
        return 3
    text, dec_err = read_text_checked(art)
    if text is None:
        # R4.1/R4.2：产出不可解码或含 NUL/U+FFFD = 证据源不可用（契约码 3），
        # 禁止吞字节后误判 PASS（无 BOM UTF-16 的 NUL 交错是合法 UTF-8，须显式检测）
        print(f"[verify_numbers] 产出文件不可解码: {dec_err}", file=sys.stderr)
        return 3
    # R4.3 复核（两路盲检交叉验证）：数字被符号/修饰/格式类字符劈开时，数字
    # 正则必然失配 → checked=0 → 「无数字即 PASS」fail-open。fail-closed。
    if has_split_number(text):
        print("[verify_numbers] 产出含被符号劈开的数字串（疑数字正则失配）——拒绝判 PASS",
              file=sys.stderr)
        return 3
    # R4.3：关键标记与数字之间被插入字符（p = 👨‍👩 0.9）同样导致正则失配。
    if has_broken_key_pattern(text):
        print("[verify_numbers] 产出含被隔开的关键数字模式（疑正则失配）——拒绝判 PASS",
              file=sys.stderr)
        return 3
    nums = extract_numbers(text, args.min_digits)
    pool = load_sources(args.sources, args.exclude, args.allow_md, require_tag=args.require_tag)

    found, not_found = [], []
    for kind, val, _ in nums:
        # 归一化 grep：原值 与 保留形式都试
        # R4.3（盲检🟠4）：原 `c in pool` 为子串匹配——p=0.94 会被权威源里的
        # 0.9441 洗白（假阳性），p=0.98 会被 10.980 洗白。改用数字 token
        # 边界匹配：候选值须作为完整数字 token 出现（前后不得紧邻数字/小数点）。
        cands = float_candidates(val)
        hit = any(pool_has_number(pool, c) for c in cands)
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
