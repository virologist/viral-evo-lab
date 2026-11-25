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
from _text_guard import (read_text_checked, has_split_number,  # noqa: E402
                         normalize_for_extraction)

# 权威数字模式（保守：只抓最易造假/最关键的四类 + CI）
# R4.5：\b → (?<![A-Za-z])——CJK 紧邻（"实验p=0.8" / "样本n=888"）时 \b 不成立
# （CJK 属 \w），导致声明被静默漏掉 → checked=0 → PASS。改用「左侧非 ASCII 字母」
# 判据：CJK/数字紧邻放行提取，ASCII 单词（如 exp=0.8）仍不误抓成 p 值。
# 配合 NFKC 归一化（消费侧 main 中），全角/圈号/上标等价形态一并收敛。
# R4.8（盲检 A🔴1）：守卫层与提取层原各写一套正则（大小写 / 分隔符 / 冒号），
# 11 个声明变体（d'= / ci / CI: / p: / 西里尔 СІ 等）在守卫层判「声明合法」、
# 提取层却零命中 → checked=0 → PASS。根治：提取 PATTERNS 统一大小写不敏感、
# 分隔符 [=:]、CI 可选分隔符，且下方 _DECL_SPEC 的 full_re **直接复用同一对象**。
PATTERNS = [
    ("pct",   re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*%")),
    ("n_eq",  re.compile(r"(?<![A-Za-z])n\s*[=:]\s*(\d{1,3}(?:,\d{3})+|\d{2,6})(?![A-Za-z\d.])", re.I)),
    ("p_val", re.compile(r"(?<![A-Za-z])p\s*[=:]\s*(0\.\d+|\d\.\d+e-?\d+|\d\.\d+)(?![A-Za-z\d.])", re.I)),
    ("dprime",re.compile(r"[dD][′']\s*[=:]\s*([+-]?\d{1,3}(?:\.\d+)?)")),
    ("ci",    re.compile(r"CI\s*(?:[=:]\s*)?[\[（({]\s*([+-]?\d{1,3}(?:\.\d+)?)\s*,\s*([+-]?\d{1,3}(?:\.\d+)?)\s*[\]）)}]", re.I)),
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
# R4.7（盲检 A🔴）：\b 在「样本n=」这类 CJK 紧邻处不成立（CJK 属 \w），
# 与 PATTERNS 的 (?<![A-Za-z]) 口径漂移 → CJK 紧邻的空白拆段绕过隔断检测。
# 统一为「仅禁 ASCII 字母紧邻」，与 PATTERNS / DECL_HINT 同口径。
KEY_MARKERS = re.compile(
    r"(?:(?<![A-Za-z])n\s*[=:]|(?<![A-Za-z])p\s*[=:]|D[′']\s*[=:]|CI\s*(?:[=:]\s*)?[\[（({])", re.I)


# R4.9（盲检 B🔴1）：ZWJ(U+200D)/VS16(U+FE0F) 等 Cf/Mn 插在 p/n 与 = 之间，
# has_forbidden 放行（span 左右非数字）、KEY_MARKERS 漏检 → 声明隐身 → PASS。
# 判据：关键标记后紧跟 Cf/Mn 不可见字符再接 =/: → 视为声明被隔断，fail-closed。
_MARKER_GAP = re.compile(
    r"(?<![A-Za-z])[npDdCI]\s*[\u200b-\u200f\u2060-\u206f\ufeff\u200c\u200d\uFE0F\u0300-\u036F\u20d0-\u20ff]{1,}\s*[=:]",
    re.I)


# B🔴1：CI 后直接接括号（CI\u200d[0.1,0.2]）不经过 =/:，单列判据
_MARKER_GAP_CI = re.compile(
    r"(?<![A-Za-z])CI[\u200b-\u200f\u2060-\u206f\ufeff\u200c\u200d\uFE0F\u0300-\u036F\u20d0-\u20ff]{1,}\s*[\[（(]",
    re.I)


def has_invisible_marker_gap(text: str) -> bool:
    """声明标记与 =/: 之间夹符号/格式/修饰符 → 正则会静默失配，须 fail-closed。

    R4.13（主代理对抗实证）：原只覆盖 Cf/Mn 码点区间，U+2B30（Sm 方块符）
    插在 `p` 与 `=` 之间（p⬰ = 0.94）仍 checked=0 → PASS。码点区间枚举补不
    完，改用 Unicode 类别动态判定：标记（n/p/D'/CI）之后、首个 `=:`/括号之前
    若出现 S*/C*/M* 类字符（符号/格式/修饰，排除空白），即判隔断。合法
    `p = 0.94` / `CI [0.1,0.2]` / `家族 👨‍👩‍👧 n=888`（emoji 在标记前）不受影响。
    """
    if _MARKER_GAP.search(text) is not None or _MARKER_GAP_CI.search(text) is not None:
        return True
    import unicodedata as _ud
    gap_cats = {"Sm", "Sk", "So", "Sc", "Cf", "Cs", "Co", "Mn", "Mc", "Me"}
    # 在归一化文本上跑类别判据：全角等号 ＝(Sm) 经 NFKC 变 '=' 属合法终止符，
    # 若用原始 text 会把 p＝0.94 误判为隔断（fail-close，既有测试断言 EXIT=5）。
    scan = normalize_for_extraction(text)
    markers = re.compile(r"(?<![A-Za-z])(?:[np]|D[′']|CI)", re.I)
    for m in markers.finditer(scan):
        j = m.end()
        while j < len(scan) and scan[j].isspace():
            j += 1
        # 收集到首个 `=:` 或 CI 括号为止的中间字符
        k = j
        while k < len(scan) and scan[k] not in "=:[(":
            k += 1
        mid = scan[j:k]
        if any(_ud.category(ch) in gap_cats for ch in mid):
            return True
    return False


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
        if m.group(0).rstrip().endswith(("(", "[", "（", "[", "{")):  # R4.13: CI 花括号
            continue  # CI 括号形态：标记后是括号，不是数字
        return True
    return False

# R4.5（2026-11-24 · 两路盲检 + 主代理对抗实证）：声明意图总闸。
# 根因：13 个 fail-open 变体（逗号/中点/阿拉伯小数点 0,94 / 0·94 / ٠٫٩٤、
# 连字符拆段 1-2-3、9 符号劈开、CJK 紧邻等）共性是「文本含关键数字声明，但
# ASCII-only 正则一个都没提取 → checked=0 → PASS」。逐变体补区间补不完，
# 改为根因判定：**声明标记存在，却零数字被提取 → fail-closed**。
# 判据复用 PATTERNS 的 key marker 语义，仅追加「文本确含数字声明」检测；
# 合法对照不误伤：纯文字（无声明）、n = 5（min_digits 有意跳过的小 n，
# 但声明存在——需在调用侧按 checked==0 且无其它声明时才放行，见 main）。
DECL_HINT = re.compile(
    r"(?:[np]\s*[=:＝]|[dD][′']\s*[=:]|CI\s*(?:[=:]\s*)?[\[（({［]|"
    r"(?:\d{1,3}(?:\.\d+)?)\s*[%％])",
    re.I)
# 合法的小 n 声明（n = 5）——min_digits=2 有意跳过的 1 位样本量。此类声明后
# 紧跟**单个 ASCII 数字**，数字是可解析的，只是低于阈值，不是正则失配。
# 豁免须整段声明干净：单数字后只允许行尾/空白/句读终止符，禁止紧接另一数字
# 或隔断符（- © · 等）——否则 n = 1-2-3 / n = 1©…©2 会被误当作小 n 放行。
# 顿号/逗号后仍接数字（`n = 5、94`）属列表隔断，不得豁免；但中文/英文
# 逗号后接字母声明（`n = 5，p = 0.111`）是合法多声明句，须豁免。
_SMALL_N_DECL = re.compile(
    r"(?<![A-Za-z])n\s*[=:]\s*\d(?=\s|$|[。；;）\]]|[,，、](?=\s*[^0-9\s，,、；;]))", re.I)

# R4.7（盲检 B🔴1/B🔴5）：原总闸只看「nums 是否全空」→ 诱饵声明（n = 30
# 在权威源中）可洗白同段另一条静默失配的声明（p = 0,94 / D’=0.94）；
# 原小 n 豁免把「、」「，」当句读 → `n = 5、94` 被当干净小 n 放行。
# 根治：改为**逐声明判定**——每个声明标记都须有可解析的对应数字形态，
# 否则 fail-closed。小 n 豁免收紧为「单数字后只接空白/句末/句号/右括号」，
# 顿号/逗号后仍接数字即视为列表隔断，不得豁免。
_PAT_BY_KIND = {kind: pat for kind, pat in PATTERNS}
_DECL_SPEC = (
    ("n", re.compile(r"(?<![A-Za-z])n\s*[=:]", re.I), _PAT_BY_KIND["n_eq"]),
    ("p", re.compile(r"(?<![A-Za-z])p\s*[=:]", re.I), _PAT_BY_KIND["p_val"]),
    ("dprime", re.compile(r"[dD][′']\s*[=:]"), _PAT_BY_KIND["dprime"]),
    ("ci", re.compile(r"CI\s*(?:[=:]\s*)?[\[（({]", re.I), _PAT_BY_KIND["ci"]),
    ("pct", re.compile(r"\d{1,3}(?:\.\d+)?\s*%"), _PAT_BY_KIND["pct"]),
)


def has_declaration_without_number(text: str, nums: list, min_digits: int = 2) -> bool:
    """逐声明判定：任一数字声明标记无对应可解析数字形态 → fail-closed。

    替代原「nums 全空才检查」的全有/全无口径（诱饵短路）。`nums` 保留签名
    兼容，不参与判定——判定只依据文本自身的声明结构与可解析形态。
    """
    # R4.10（盲检 A🔴2）：守卫是「声明存在但无法解析」的结构判定，
    # 与提取阈值 min_digits 无关；原 min_digits<2 直接 return False 会
    # 让 --min-digits 1 关闭守卫 → p = 0,94 静默 PASS。
    for kind, hint_re, full_re in _DECL_SPEC:
        for m in hint_re.finditer(text):
            if full_re.match(text, m.start()):
                continue
            if kind == "n" and _SMALL_N_DECL.match(text, m.start()):
                continue
            return True
    return False


# R4.16（盲检 A🔴1）：NFKC 不分解、_EQUIV_TRANS 未枚举的同形声明标记
# （ɲ U+0272 / ŋ U+014B / ϕ U+03D5 / ն U+0576 等）让声明正则零命中 →
# checked=0 → PASS。码点枚举补不完，改为 Unicode 名称语义判定：名称含
# 'LATIN ... LETTER N/P' / 'ARMENIAN ... NOW' / 'GREEK ... PHI' 的非 ASCII
# 字母若紧跟 =/: + 数字，视为 n/p 声明被同形字冒充 → fail-closed。
_HOMOGLYPH_DECL = re.compile(
    r"(?P<mark>[^\x00-\x7f\s])\s*[=:]\s*(?:\d{2,}|0\.\d+)", re.I)


def _is_np_homoglyph(ch: str) -> bool:
    import unicodedata as _ud
    name = _ud.name(ch, "").upper()
    if not name:
        return False
    return (("LATIN" in name and "LETTER" in name
             and ("LETTER N" in name or "LETTER P" in name
                  or "LETTER ENG" in name or "LETTER PHI" in name))
            or ("ARMENIAN" in name and ("NOW" in name or "PEH" in name))
            or ("GREEK" in name and "PHI" in name))


def has_homoglyph_declaration(text: str) -> bool:
    for m in _HOMOGLYPH_DECL.finditer(text):
        mark = m.group("mark")
        if not _is_np_homoglyph(mark):
            continue
        # 预组合 ń(U+0144)/ṕ(U+1E55) 等 NFD 剥 Mn 后已转成 ASCII n/p，
        # 声明正则可正常提取（EXIT=5），无需 fail-closed。仅当归一化后
        # 仍是非 ASCII 同形字（ɲ/ŋ/ϕ 等）才拦。
        if normalize_for_extraction(mark) in ("n", "p", "N", "P"):
            continue
        return True
    return False


def prepare_numbers(text: str, min_digits: int = 2):
    """消费方共用的「归一化 → 提取 → 隔断/声明守卫」单一入口。

    返回 (ok: bool, nums: list, reason: str)。ok=False 表示检出一个或多个
    fail-open 结构（符号劈开 / 标记隔断 / 声明无数字），消费方须按自身契约
    fail-closed（verify_numbers → EXIT=3；vmo → unverified 哨兵 → DEGRADE；
    check_gates → G2 FAIL）。R4.5 新增 NFKC 归一化与声明总闸。
    """
    # 污染检测必须在归一化前（原始 text）——归一化不该掩盖 NUL/Cf 污染
    if has_split_number(text):
        return False, [], "数字被符号劈开"
    if has_broken_key_pattern(text):
        return False, [], "关键数字模式被隔开"
    if has_invisible_marker_gap(text):
        return False, [], "声明标记被不可见字符隔断"
    if has_homoglyph_declaration(text):
        return False, [], "数字声明标记被同形字冒充"
    norm = normalize_for_extraction(text)
    # R4.12（盲检 A🔴2）：数字+中文句号+数字（含 NFKC(｡)→。）是小数点变体，
    # 定点检测（不动句尾句号），否则 30。5 被提取为 30 被池中 30 洗白。
    # 必须在 norm 生成后同时查原始 text 与归一化 norm（｡ NFKC→。）。
    if re.search(r"\d[。]\d", text) or re.search(r"\d[。]\d", norm):
        return False, [], "数字被句号型小数点隔断"
    # 归一化后再查一次劈开（全角→ASCII 后可能出现新的相邻数字-符号结构）
    if has_split_number(norm) or has_broken_key_pattern(norm):
        return False, [], "归一化后数字被隔断"
    nums = extract_numbers(norm, min_digits)
    if has_declaration_without_number(norm, nums, min_digits):
        return False, [], "含数字声明但零提取（正则失配）"
    return True, nums, ""


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
                if kind == "n_eq":
                    v_norm = v.replace(",", "")  # R4.11: 千分位 1,234 → 1234
                    if len(v_norm.lstrip("0")) < min_digits:
                        continue
                    out.append((kind, v_norm, v_norm))
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
        # R4.13（盲检 B🔴1）：原实现无条件 f"{f:.3f}" 等会产生**截断候选**——
        # 产出 0.94412 → 候选 0.944 → 被池中 0.944 洗白 → 假阳性 PASS，正违反
        # 本函数 docstring「禁截断」承诺。改为仅补零：目标精度须 ≥ 原值实际
        # 小数位，且格式化后与原值数值相等（去尾零后逐字相同），绝不降精度。
        if "." in val and "e" not in val.lower():
            frac_digits = len(val.split(".", 1)[1].rstrip("0"))
            base = val.rstrip("0").rstrip(".")
            for nd in (2, 3, 4, 5, 6):
                if nd < frac_digits:
                    continue
                formatted = f"{f:.{nd}f}"
                if formatted.rstrip("0").rstrip(".") == base:
                    cands.add(formatted)
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
    # R4.7（盲检 B🔴3）：逗号亦为数字延续符（欧洲小数 0,94 / 千分位 1,234），
    # 原边界只禁 \d 与 . → 产出 `n = 94` 被权威池 `0,94` 洗白 → PASS。
    # 边界统一为「前后不得紧邻数字 / . / ,」。
    # R4.13（盲检 A🔴2）：v1.5.28 右边界曾为 `(?![\d.])(?!,[0-9])`，R4.11 修 CSV
    # 三列字段时误删 `(?!,[0-9])` → 产出 `n = 94` 被权威池 `94,500` 洗白 PASS。
    # 恢复：整数候选（无 `.`）右边界禁 `,\d`（千分位延续），浮点候选（含 `.`）
    # 不禁逗号（合法 CSV 字段 `1,0.94,2` / `30,0.9441` 正常溯源）。
    left = r"(?<![\d.])(?<![0-9],)" if "." not in cand else r"(?<![\d.])"
    # 整数候选右边界只禁「逗号 + 1~3 位数字 + 非数字/点/逗号结尾」——命中
    # 千分位/字段延续（94,500 / 1,94,2）；CSV 浮点字段 30,0.9441 的 `,0.`
    # 因后随小数点不满足末项，合法放行（v1.5.28 CSV 双字段回归保住）。
    # R4.14（盲检 A🔴4）：\d{1,3} 在 4+ 位逗号组（94,5000）回溯耗尽 →
    # lookahead 误通过。改 \d+ 并只排除「后随小数点」的 CSV 浮点字段
    # （30,0.9441 的 ,0.9441 合法放行），千分位/字段延续任意位数均拦。
    # R4.16（盲检 A🔴2）：原右边界只禁数字/点/逗号，产出 `n = 94` 被池中
    # `94e5`（数值 9400000）/ `94%` / `94kg` / `94_5` 洗白 PASS。整数候选
    # 追加禁字母/数字/下划线/百分号后缀（\w 含字母数字下划线，% 单列）。
    right = (r"(?![\d.\w%])(?!,\d+(?!\.))" if "." not in cand
             else r"(?![\d.])")
    pat = re.compile(left + re.escape(cand) + right)
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
    # R4.3/R4.5（两路盲检 + 主代理对抗）：符号/空白劈开、标记隔断、Unicode 等价
    # 形态、声明存在却零提取 → 数字正则静默失配 → checked=0 → PASS fail-open。
    # 统一走 prepare_numbers 单一入口（NFKC + 隔断 + 声明总闸），与另两个消费方
    # （verify_member_output / check_gates）同口径，杜绝三处判定漂移。
    ok_nums, nums, why_nums = prepare_numbers(text, args.min_digits)
    if not ok_nums:
        print(f"[verify_numbers] 产出含{why_nums}（疑数字正则失配）——拒绝判 PASS",
              file=sys.stderr)
        return 3
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
