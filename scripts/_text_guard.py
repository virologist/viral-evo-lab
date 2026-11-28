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
# R4.14：右侧数字改正向前瞻（不消耗），否则 `0.9⬰4` 中 `0.9` 先匹配消耗掉
# 数字 9，`9⬰4` 无法再匹配 → 前缀劈开洗白漏检。前瞻使每次匹配从下一位数字
# 重新开始，覆盖连续小数点后的符号劈开形态。
# R4.15（盲检 A🔴3）：{1,8} 上限导致 9+ 分隔符时正则零匹配 → 前缀被池洗白。
# R4.21（盲检 A🔴2）：{1,64} 仍有界——65 个 Sm 隔断即零匹配、前缀洗白 PASS。
# 根因修：去掉数量上限；`\d` 起点 + `[^\d\s]+` 贪婪 + `(?=\d)` 前瞻的组合
# 无灾难性回溯（每起点至多一次线性扫描到下一数字/空白），故无界安全。
_SPLIT_NUM = re.compile(r"\d(?P<x>[^\d\s]+)(?=\d)")
# R4.15（盲检 A🔴5）：原声称「全 S*/P*/M*/C*」实际漏 Co(私有区)/Cs(代理)/
# Mc(间距组合符)/Me(封闭组合符)——U+E000/U+20DD 隔断数字仍 PASS。补全。
# R4.21（盲检 A🔴1）：补 Cn（Unassigned）——U+0378 等未分配码点属 C 类但
# 不在原枚举，NFKC/同形映射都不收敛，插进数字后 p_val 右边界也放行 →
# 前缀 0.9 被权威池洗白 PASS。Cn 与 Cf/Co/Cs 同属「不可见格式类」，补齐。
_SPLIT_BAD_CATS = ("So", "Sk", "Mn", "Mc", "Me", "Cf", "Sc", "Cs", "Co", "Cn",
                   "Sm", "Pd", "Po", "Ps", "Pe", "Pi", "Pf")
# 合法的数字内部分隔符：ASCII 标点/符号放行（1-2-3 / 10:30 / 1,234 / 10~20 /
# 0.94-1.0 / D′）。非 ASCII 的同类字符（⬰ U+2B30 Sm / ～ U+FF5E Sm /
# ！ U+FF01 Po / — U+2014 Pd）才判劈开污染。
_SPLIT_ASCII_OK = frozenset(".,:-~′'()")


def has_split_number(text: str) -> bool:
    """文本中是否存在被符号/修饰/格式类字符劈开的数字串。

    命中即意味着数字正则可能静默失配（checked=0 → PASS），调用方须 fail-closed。
    R4.14（盲检 A🔴1）：原白名单只有 So/Sk/Mn/Cf/Sc，Sm(⬰ ～ ±)/Pd(—)/Po(！)
    劈开数字（88⬰88 / 94～500 / 0.9⬰4）时 core 不命中 → 前缀被池中洗白 PASS。
    扩展类别到全 S*/P*/M*/C*，但显式放行 ASCII 合法分隔符与常见排版符号，
    防误伤 1-2-3 / 10:30 / 1,234.5 / 10~20 / 20°C。
    """
    def is_legal_sep(ch: str) -> bool:
        if ch in _SPLIT_ASCII_OK:
            return True
        # 全角/多语分隔符（，U+FF0C／．U+FF0E／·U+00B7）NFKC/映射后是
        # ASCII 合法分隔符，放行——CI ［0.1，0.2］ / p = 0·94 不误判。
        mapped = unicodedata.normalize("NFKC", ch).translate(_EQUIV_TRANS)
        return mapped in _SPLIT_ASCII_OK and unicodedata.category(ch) == "Po"

    for m in _SPLIT_NUM.finditer(text):
        # R4.15（盲检 A🔴4）：原 rstrip(".,") 只剥尾部；前置合法分隔符
        # （94,⬰7 的逗号）留在 core 使 all() 判据整体失效 → 洗白 PASS。
        # 剔除 core 中所有合法分隔符后再判定剩余是否全为劈开类字符。
        core = "".join(ch for ch in m.group("x") if not is_legal_sep(ch))
        if not core:
            continue
        # 剩余字符中若含非劈开类（如字母 e/'°'），整体不判（防 1e-3/20°C 误伤）
        if all(unicodedata.category(ch) in _SPLIT_BAD_CATS for ch in core):
            return True
    return False


# R4.7（2026-11-24 · 盲检 B🔴4）：NFKC 不覆盖的**排版/同形字等价**——
# 弯引号 U+2019、中文方括号【】、希腊 rho 冒充 p 等，均可让 ASCII-only
# 声明正则静默失配 → checked=0 → PASS。按「语义等价类映射」（非码点区间枚举）
# 统一到 ASCII 正字，与 NFKC 同类思路；仅用于提取，不改动原文其他用途。
_EQUIV_TRANS = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u2032": "'", "\u02bc": "'", "\uff07": "'",
    # R4.14（盲检 A🔴3）：prime/acute 变体冒充 D′ 声明标记（d´ / dʹ / d‵）
    "\u00b4": "'", "\u02b9": "'", "\u2035": "'", "\u02ba": "'",
    "\u02cb": "'", "\u02c8": "'", "\u02b8": "'", "\u055a": "'",
    "\u201c": '"', "\u201d": '"', "\uff02": '"',
    "\u3010": "[", "\u3011": "]", "\u27e6": "[", "\u27e7": "]",
    "\u03c1": "p", "\u03f1": "p", "\u0440": "p",   # ρ/ϱ/р → p（同形声明）
    "\u03bd": "n", "\u03bf": "o",                   # ν/ο → n/o（希腊同形）
    "\u03a1": "P", "\u0420": "P",                   # Ρ/Р → P
    # R4.8（盲检 A🔴1）：西里尔同形字冒充声明标记（СІ [..] / р: 0.94）
    "\u0421": "C", "\u0441": "c", "\u0406": "I", "\u0456": "i",
    "\u0410": "A", "\u0430": "a", "\u0415": "E", "\u0435": "e",
    "\u041e": "O", "\u043e": "o", "\u0423": "Y", "\u0443": "y",
    "\u0425": "X", "\u0445": "x",
    # R4.9（盲检 B🔴2）：更多同形字与多语百分号（NFKC 不收敛）
    "\u043f": "n", "\u03a0": "N", "\u043d": "n", "\u0397": "H",
    "\u03b7": "n", "\u0435": "e", "\u0456": "i", "\u066a": "%",
    "\u00b5": "u", "\u039c": "M", "\u043c": "m", "\u043a": "k",
    "\u043e": "o", "\u0441": "c", "\u0442": "t", "\u0455": "s",
    "\u04bb": "h", "\u0454": "e", "\u0437": "3",
    # R4.12（盲检 A🔴2）：多语小数点/千分位——NFKC 不收敛，原被当普通隔断
    # → n = 30٫5 提取为 30 → 权威源含 30 即洗白（fail-open）。
    # U+066C 是阿拉伯千分位分隔符，必须映射为 ','（非 '.'）。
    "\u066b": ".", "\u066c": ",", "\u00b7": ".", "\u30fb": ".",
    "\uff61": ".", "\u2022": ".", "\u06d4": ".", "\u0387": ".",
    "\u2027": ".", "\uff0e": ".",
    # R4.13（盲检 A🔴4）：CI 括号用全角花括号 ｛｝ / 尖括号 〈〉 / 角括号 《》
    # 时，NFKC 不收敛且 CI 正则只认 []（）→ 声明隐身 checked=0/PASS。
    "\uff5b": "[", "\uff5d": "]", "\u3008": "[", "\u3009": "]",
    "\u00ab": "[", "\u00bb": "]", "\u300a": "[", "\u300b": "]"
})


def normalize_for_extraction(text: str) -> str:
    """NFKC + 排版/同形字等价映射——仅用于数字/声明提取，不改原文其他用途。

    R4.5（2026-11-24 · 两路盲检 + 主代理对抗实证）：NFKC 消解全角数字/等号/
    百分号、圈号数字、上标数字、０．９４ 等（①→1、８→8、²→2、％→%、＝→=、
    ［］→[]），不再靠枚举码点。

    R4.7（2026-11-24 · 盲检 B🔴4）：NFKC 不覆盖的排版等价（D’= U+2019、
    CI【】 U+3010/3011、ρ= 同形字）追加 str.translate 语义等价映射。
    对照组（ASCII 正字、纯文本、n=5）归一化后逐字不变。
    """
    # R4.13（盲检 A🔴1/A🔴3/A🔴5）：NFKC 不收敛的 Mn（组合符，如 U+1AB0/
    # U+0301 插进 p=/事故值/撞限词）会让声明正则与关键子串静默失配 →
    # checked=0 → PASS（fail-open）。合法组合重音已被 NFKC 预组合（e+U+0301
    # → é），残留 Mn 均为修饰性字符，删除不改变语义，统一剥离恢复 token。
    # 关键顺序：NFD 分解 → 剥 Mn → 语义映射 → NFKC——
    # ① 预组合同形字 ń(U+0144)/ṕ(U+1E55) 的 NFKC 不分解，须先 NFD 拆成
    #    n+Mn 再剥 Mn 才能复原 ASCII 标记（R4.14 盲检 A🔴2）；
    # ② 组合 Mn（如 U+1AB0）经 NFKC 会转成可见符号（U+2B30 ⬰），事后过滤
    #    挡不住，须在 NFKC 前剥除。
    # ③ prime 变体 U+00B4(´) 经 NFD 会拆成空格+Mn 再被剥掉，须在 NFD 前
    #    先做一次等价映射（´→'），NFKC 后再映射一次处理新生成形态。
    pre = text.translate(_EQUIV_TRANS)
    decomposed = unicodedata.normalize("NFD", pre)
    no_mn = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    nfkc = unicodedata.normalize("NFKC", no_mn).translate(_EQUIV_TRANS)
    # R4.18（盲检🔴4/6）：NFKC 不把**非 ASCII 的 Nd 十进制数字**（泰文 ๔
    # U+0E54 / 阿拉伯-印度 ١ U+0661 / 天城文 १ U+0967 等）转 ASCII，
    # 产出用这些同形数字写 `PP ๔๑...` / `轮١次耗尽` → 正则静默失配 →
    # clean/READY fail-open。类别判据（Nd + decimal）一次性覆盖所有语种
    # 十进制数字，不再逐码点枚举。圈号/上标（No）已由 NFKC 消解。
    return "".join(
        str(unicodedata.decimal(ch)) if unicodedata.category(ch) == "Nd" and ord(ch) > 127
        else ch for ch in nfkc)


def normalize_for_matching(text: str) -> str:
    """匹配用途归一化：在 normalize_for_extraction 基础上再剥非 ASCII 的
    符号/标点类字符（S*/P*），供关键子串匹配（撞限标注/事故叙事）使用。

    R4.14（盲检 A🔴5/🔴6）：Mn 之外的 Sm(⬰)/So(★)/Po(！)/Pd(—) 插进
    「轮次耗尽」/事故值同样让子串失配 → READY/clean fail-open。此类字符
    在匹配用途下无语义，剥离后恢复原 token；ASCII 标点（.,:-~）保留以
    维持合法数字格式。仅用于匹配，不改原文其它用途。
    """
    import unicodedata as _ud
    base = normalize_for_extraction(text)
    # R4.18（盲检🔴4/6，根因级重构）：原按类别枚举剥离（S*/P*/Cf/M*/非ASCII
    # L{l,u,t,m}），但类别永远补不完——Nd(阿拉伯数字插进撞限词)/No(½)/Zs(空格
    # NBSP)/Co(私用区)/Lm(ʰ) 逐个绕过；更糟的是 `%`(Po) 被误剥导致 check_scope
    # 黑名单 `20\.58%` **字面量自身**永假（纯 ASCII 输入即 clean fail-open）。
    # 弃用「剥坏类别」的黑名单，改**白名单**：只保留
    #   ① ASCII 可见字符（0x21~0x7E，含 % 数字 . , : - ( ) [ ] 等合法 token/分隔符）
    #   ② CJK 表意文字（汉字本身，撞限词「轮次耗尽」/事故叙事「位置映射错」）
    # 其余（非 ASCII 字母/各语种符号/组合符/私用区/各类空白）一律剥离——
    # 匹配用途下这些字符均无语义，剥除后关键子串恢复，白名单不再有遗漏类别。
    # 注意：ASCII 空白(0x20)/换行也剥（撞限词/事故叙事不含空白；黑名单里的
    # \s* 本就容忍空白），全角空格经 NFKC 已是 0x20 同样剥除。
    def is_cjk(ch: str) -> bool:
        o = ord(ch)
        # R4.22（盲检 A🔴4，根因级）：CJK 兼容表意文字区（F900–FAFF）
        # 不保留——兼容字 NFKC 后折叠成**另一个**统一汉字（如 U+F900→
        # 「豈」U+8C48），插进「轮次耗尽」仍隔断关键词子串匹配 → READY
        # fail-open。撞限词/事故叙事用字均为常用统一汉字，兼容区无合法
        # 用途、纯属隔断攻击面，白名单中排除。扩展区 A/B（3400–4DBF、
        # 20000–2FA1F）是真正的造字扩展，保留。
        return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
                or 0x20000 <= o <= 0x2FA1F)

    def keep(ch: str) -> bool:
        o = ord(ch)
        if 0x21 <= o <= 0x7E:  # ASCII 可见（含 %，修复黑名单字面量永假）
            return True
        return is_cjk(ch)
    # R4.18 设计纪律（分离关注点）：此处**不再剥「CJK 之间的 ASCII」**——
    # check_scope 的合法黑名单 token（PP41034380 PMID / d211094 commit）
    # 本就嵌在中文正文里（「说明：PP 41034380 是事故编号」），一刀切剥离
    # 会误放真污染（fail-open）。撞限词「轮次耗尽」的隔断问题改用专用
    # normalize_for_cjk_keyword（纯 CJK 投影）在 poll 侧解决，互不干扰。
    kept = [ch for ch in base if keep(ch)]
    # 数字间 ASCII 标点（10!94 / 10—94 / 10⬰94 中的隔断符）须剥以还原事故值
    # token（1094 commit），但**不得剥字母/数字本身**（PMID PP41034380），
    # 也须保留合法数字字面量分隔符 `.` `,` `:` `-` `%`（黑名单 20\.58% /
    # 0\.2058 / 千分位 1,234 依赖）。仅当 ASCII 可见字符左右均为数字、
    # 且不是这些合法分隔符时剥离。
    numeric_seps = frozenset(".,:-%")
    out = []
    for i, ch in enumerate(kept):
        if (0x21 <= ord(ch) <= 0x7E and not ch.isalnum() and ch not in numeric_seps
                and i > 0 and i + 1 < len(kept)
                and kept[i - 1].isdigit() and kept[i + 1].isdigit()):
            continue
        out.append(ch)
    return "".join(out)


def normalize_for_cjk_keyword(text: str) -> str:
    """撞限关键词专用归一化：只保留 CJK 表意文字，其余一律剥离。

    R4.18（盲检🔴4，根因级）：撞限词「轮次耗尽」是**纯 CJK**，插入任何
    非 CJK 字符（Nd 阿拉伯数字 ١ / No ½ / Lm ʰ / Co 私用区 / Zs 空格 /
    ASCII ! 等）都是隔断攻击。通用的 normalize_for_matching 必须保留
    ASCII 数字字母（供 PMID/commit 黑名单匹配），无法一刀切剥离；故撞限
    检测单独走此「纯 CJK 投影」：任意非 CJK 隔断自动消失，类别永不遗漏。
    """
    # R4.22（盲检 A🔴4，根因级）：CJK 兼容表意文字（F900–FAFF、2F800–2FA1F）
    # 必须在 NFKC **之前**剥除——NFKC 把 U+F900 折成「豈」(U+8C48，统一区)，
    # 事后投影无法区分，兼容字便作为隔断字符混进「轮次耗尽」使子串失配 →
    # READY/0 fail-open。撞限词用字均为常用统一汉字，兼容区无合法用途。
    raw = "".join(ch for ch in text
                  if not (0xF900 <= ord(ch) <= 0xFAFF
                          or 0x2F800 <= ord(ch) <= 0x2FA1F))
    base = normalize_for_extraction(raw)
    return "".join(ch for ch in base
                   if (0x4E00 <= ord(ch) <= 0x9FFF or 0x3400 <= ord(ch) <= 0x4DBF
                       or 0x20000 <= ord(ch) <= 0x2FA1F))


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
            # R4.15（盲检 A🔴1/2/6）：emoji/ZWJ span 紧贴数字**或字母/汉字**
            # 均可能是隔断 fail-open——`轮‍次耗尽` / `位置‍映射错` /
            # `fatal‍` 的 ZWJ 两侧是 CJK/字母，原只拒数字侧故放行 →
            # 撞限/事故叙事/severity 静默失配。合法 emoji ZWJ 序列两侧均为
            # emoji（非 alnum），继续放行。
            if left.isalnum() or right.isalnum():
                return True
            i = j
            continue
        i += 1
    return False


def has_visible_content(text: str) -> bool:
    """文本是否含至少一个「可见语义字符」（字母 L 或数字 N）。

    R4.20（盲检 A🔴4/B🔴4/A🔴5）：按 Unicode 名称枚举 FILLER 是死路——
    U+2800 BRAILLE PATTERN BLANK(So)、私用区(Co)、未分配(Cn) 均不含 FILLER，
    `strip()` 也不剥；靠 `reason.strip()` 判非空同样放过了 ZWSP。
    根因改白名单语义判据：G6 的 reason/excerpt 与 waiver 的 reason/署名
    都是「人类可读文字」，必须含字母或数字；纯符号、视觉空白、格式/控制
    字符一律视为空壳。中文/英文/数字正文均含 L/N，不受误伤。
    """
    if not isinstance(text, str):
        return False
    for ch in normalize_for_extraction(text):
        if unicodedata.category(ch)[0] not in ("L", "N"):
            continue
        # R4.22（盲检 B🔴5，根因级）：R4.20 按名称子串 FILLER 具名排除仍是枚举——
        # U+13441 EGYPTIAN HIEROGLYPH FULL BLANK / U+13442 HALF BLANK 是 Lo
        # （字母类别）但视觉完全空白，名称含 BLANK 不含 FILLER → 被误判为可见
        # 正文，击穿 G2/G4 waiver 署名与 G6 抽查留痕。语义判据：可见内容必须是
        # 人类可读文字；Unicode 名称含 FILLER 或 BLANK 的 Lo 字符是占位空白，
        # 一律排除（埃及象形文字 BLANK、Hangul filler 等同类一并覆盖）。
        name = unicodedata.name(ch, "").upper()
        if "FILLER" in name or "BLANK" in name:
            continue
        return True
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
