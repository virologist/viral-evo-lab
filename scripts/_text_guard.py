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
    2) 解码后扫描控制字符：NUL(U+0000) / U+FFFD 替换符 → 判不可解码
    3) 统一返回 (text | None, reason)；调用方按各自契约码 fail-closed

使用（同目录 import，脚本运行时 scripts/ 在 sys.path[0]）：
    from _text_guard import read_text_checked
    text, err = read_text_checked(path)
    if text is None:
        return <契约码>   # 绝不把 err 当空文本继续跑核验

设计纪律：
    - fail-closed：宁可拒绝/降级，也不把不可解码内容当空/当干净放行
    - 不放宽：errors 参数固定 strict，禁止 ignore/replace 静默吞字节
"""
from pathlib import Path

# 不可解码控制字符：NUL（UTF-16 交错的铁证）、U+FFFD（非法字节被替换的痕迹）
_FORBIDDEN = ("\x00", "\ufffd")


def has_forbidden(text: str) -> bool:
    """文本是否含 NUL / U+FFFD——命中即视为 UTF-16 或非法字节污染。"""
    return any(ch in text for ch in _FORBIDDEN)


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
        return None, "含 NUL/U+FFFD 控制字符（疑无 BOM UTF-16 或非法字节序列）"
    if max_chars is not None:
        text = text[:max_chars]
    return text, ""
