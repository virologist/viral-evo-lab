#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
_text_guard.py —— 统一严格文本读取守卫（R4.2 · 2026-11-19）
=======================================================================
背景（盲检实证 fail-open）：
    R4.1 把全包 errors="ignore" 改为「严格 utf-8-sig + 捕获 UnicodeError」，
    但**无 BOM 的 UTF-16**（如 'p = 0.999\n'.encode('utf-16-be')）解出的
    NUL 交错文本（p\x00 \x00=\x00 ...）在 UTF-8 下全部是**合法字节**——
    utf-8-sig 解码不抛异常，NUL 又不是 \s，导致数字正则全部失配 →
    checked=0 → 误判 PASS。这是比 traceback 更危险的 fail-open。

本模块提供单一事实源：read_text_checked()
    1) utf-8-sig 严格解码（剥 BOM，畸形多字节序列抛 UnicodeError）
    2) 解码后按 Unicode 类别扫描：Cc(除 \t\n\r\v\f) / Cf(零宽/格式字符) / U+FFFD → 判不可解码
    3) 统一返回 (text | None, reason)；调用方按各自契约码 fail-closed

R4.3 复核（2026-11-20 · 两路独立盲检交叉验证的 fail-open）：
    「数字被任意非数字字符隔断」会让数字正则静默失配 → checked=0 → PASS。
    变体：emoji(So，如 U+2B50 ⭐)、ZWJ emoji 序列、组合音标(Mn，如 U+0301)、
    符号(Sm/Po)。字符类别补区间永远补不完，故本模块再加一层**数字劈开检测**：
    has_split_number() 识别「数字 + 符号/修饰/格式类字符 + 数字」的结构，
    由调用方 fail-closed。

使用（同目录 import，脚本运行时 scripts/ 在 sys.path[0]）：
    from _text_guard import read_text_checked
    text, err = read_text_checked(path)
    if text is None:
        return <契约码>   # 绝不把 err 当空文本继续跑核验

设计纪律：
    - fail-closed：宁可拒绝/降级，也不把不可解码内容当空/当干净放行
    - 不放宽：errors 参数固定 strict，禁止 ignore/replace 静默吞字节
"""
import re
import unicodedata
from pathlib import Path

# R4.3（2026-11-19 · 盲检①🔴6 + 主代理对抗实证）：从「枚举 C0 字符」升级为
# **Unicode 类别检测**——零宽/格式字符（Cf，如 U+200B/ZWSP、U+FEFF、U+2060、
# U+00AD 软连字符）交错在数字旁同样让正则静默失配 → checked=0 → PASS fail-open，
# 而它们不在 C0 范围，枚举法挡不住。改用类别：
#   - Cc（控制字符）：NUL/SOH/DEL 等；白名单 \t\n\r\v\f（Python re 的 \s，合法文本空白）
#   - Cf（格式字符）：零宽空格/连接符/BOM/软连字符等，一律拒绝
#   - U+FFFD（So 替换符）：非法字节被替换的痕迹，单独拒绝
# 放行：NBSP(U+00A0, Zs)——Python re 的 \s 可解析、合法文档会用；及一切可见字符。
_ALLOWED_WS = frozenset("\t\n\r\v\f")  # re \s 成员，放行不造成数字正则失配


def _is_emoji_cp(ch: str) -> bool:
    """ZWJ 序列两侧的 emoji 码点判定（常见 emoji 区 + dingbats）。"""
    cp = ord(ch)
    return (0x1F000 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF)


# R4.3 复核（2026-11-20 · 两路盲检交叉验证）：数字劈开检测。
# 「数字 + 符号/修饰/格式类字符 + 数字」→ 数字被劈开，数字正则必然失配 →
# checked=0 → PASS fail-open。已实测变体：emoji(So ⭐/U+2B50)、ZWJ emoji 序列、
# 组合音标(Mn U+0301)、符号。字符类别补区间补不完（U+203C‼ 是 Po），
# 故按「类别属于符号/修饰/格式/货币，且不含常规数字分隔符(. ,)」判劈开。
# 说明：常规排版（1,234.5 / 10:30 / 20°C / 10~20）不含此类字符，不误判。
_SPLIT_NUM = re.compile(r"\d(?P<x>[^\d\s]{1,8})\d")
_SPLIT_BAD_CATS = ("So", "Sk", "Mn", "Cf", "Sc")


def has_split_number(text: str) -> bool:
    """文本中是否存在被符号/修饰/格式类字符劈开的数字串。

    命中即意味着数字正则可能静默失配（checked=0 → PASS），调用方须 fail-closed。
    """
    for m in _SPLIT_NUM.finditer(text):
        core = m.group("x").rstrip(".,")
        if not core:
            continue
        if all(unicodedata.category(c) in _SPLIT_BAD_CATS for c in core):
            return True
    return False


def has_forbidden(text: str) -> bool:
    """文本是否含 Cc(除空白)/Cf/U+FFFD——命中即视为二进制或不可见字符污染。

    R4.3（2026-11-20 · 盲检🟠）：合法 emoji ZWJ 序列（👨‍👩‍👧，U+200D 连接两侧
    emoji）不得被一刀切误拒（fail-close 误伤合法产出）。精确白名单：仅当
    U+200D 两侧均为 emoji 码点时放行；其余 Cf（U+200B/ZWSP、U+FEFF、U+00AD
    软连字符、U+2060）仍拒绝。
    安全论证：放行条件要求两侧都是 emoji——数字/字母侧一律拒绝，故攻击者
    无法用 ZWJ 分隔数字串（如 0\\u200d7）造成正则失配 → checked=0 → PASS 的
    fail-open；emoji 序列也不会被数字正则当作数字的一部分。
    """
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch in _ALLOWED_WS:
            i += 1
            continue
        if ch == "\ufffd":
            return True
        cat = unicodedata.category(ch)
        if cat == "Cc":
            return True
        # R4.3 复核（主代理对抗实证）：emoji(So)/Cf 本身不是 fail-open，但把
        # 连续 emoji/Cf 当成一个 span 塞进数字串中间（n=8👨‍👩88）会让数字正则
        # 静默失配 → checked=0 → PASS。合法 emoji 序列不会紧贴 ASCII 数字，
        # 故：span 左右任一紧邻 ASCII 数字即判污染；否则（如「家族 👨‍👩‍👧
        # 样本量 n=888」）放行。同时保留 ZWSP/BOM/软连字符等非 ZWJ Cf 一律拒绝。
        if _is_emoji_cp(ch) or cat == "Cf":
            j = i
            has_non_zwj_cf = False
            while j < n and (_is_emoji_cp(text[j]) or text[j] == "\u200d"
                             or unicodedata.category(text[j]) == "Cf"):
                if (unicodedata.category(text[j]) == "Cf"
                        and text[j] != "\u200d"):
                    has_non_zwj_cf = True
                j += 1
            left = text[i - 1] if i > 0 else ""
            right = text[j] if j < n else ""
            # 非 ZWJ 的 Cf（ZWSP/BOM/软连字符/U+2060）夹在任意位置都拒绝
            if has_non_zwj_cf:
                return True
            # emoji/ZWJ span 紧贴数字 = 数字串被隔断 = fail-open，拒绝
            if (left.isdigit() or right.isdigit()):
                return True
            i = j
            continue
        i += 1
    return False


def read_text_checked(path, *, encoding: str = "utf-8-sig", max_chars: int | None = None):
    """严格读文本并检测控制字符污染。

    返回 (text, "") 成功；或 (None, reason) 失败（OSError / 解码异常 / 控制字符）。
    max_chars 用于只需文件头的场景（如撞限检测），截断在检测**之后**执行，
    确保 NUL 污染不会因为只看了干净的前几行而漏检。
    """
    try:
        text = Path(path).read_text(encoding=encoding)
    except (OSError, UnicodeError) as e:
        return None, f"{type(e).__name__}: {e}"
    if has_forbidden(text):
        return None, "含 Cc(控制)/Cf(零宽格式)字符或 U+FFFD（疑不可见字符/二进制污染）"
    if max_chars is not None:
        text = text[:max_chars]
    return text, ""
