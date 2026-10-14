#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_scope.py —— 专家包落盘前自检（P2 · 2026-10-14）
执行：检查修改/新增的 .md/.py 是否含"项目特定叙事"（违反两仓分层纪律）
用法：python3 scripts/check_scope.py [paths...（默认全仓 .md/.py）]
退出码：0=clean；3=含项目特定叙事
边界：仅做"机械关键词检查"（确定性），判断"该不该"留给 LLM 审阅
纪律契约：GOVERNANCE_BOUNDARIES.md

注：只禁"具体事件级污染"（具体 PMID/事故位点/具体错误值/事故日）；
不禁"领域共享知识"（H5Nx 通用知识、糖基化常识、位点列表）——后者是
专家包存在的根本理由（包就是为某领域服务，共享领域知识不等于污染）。
"""
import re
import sys
from pathlib import Path

# 项目特定叙事黑名单（关键词式；命中即疑似污染）
# 原则：禁"具体事件"（错案位点+具体数字+具体PMID+具体事故日）
# 不禁"领域通用"（糖基化、亚型名、位点符号本身）
PATTERNS = [
    re.compile(r"PP\s*41034380"),                                # 具体 PMID
    re.compile(r"\.pre-[A-Za-z0-9_-]+"),                          # 特定事故的 backup 命名
    re.compile(r"1094\b"),                                        # commit hash 片段
    re.compile(r"\bA156T?\s*=\s*"),                               # 事故位点的具体断言
    re.compile(r"20\.58%"),                                      # 事故具体错误值
    re.compile(r"0\.2058\b"),                                    # 事故具体错误值（裸数字）
    re.compile(r"\[39,40\]|\[40,39\]"),                          # 事故草稿引用号冲突
    re.compile(r"A156[A-Z]?\b\s+幻觉"),                          # "A156X 幻觉"短语
    re.compile(r"编号映射错误"),                                  # 事故根因描述
    re.compile(r"v6\.6\s*草稿"),                                 # 事故草稿状态
    re.compile(r"d211094"),                                      # 事故 commit
    re.compile(r"位置_?映射.*错"),                                # 事故类别
    re.compile(r"mapping.*error.*G140"),                        # 事故类别（英文）
    re.compile(r"NetNglyc.*错|NG.*错误"),                        # 工具结果错
]


def check_file(p: Path) -> list:
    """返回该文件中疑似项目特定叙事的行号+内容列表。"""
    hits = []
    if p.suffix.lower() not in (".md", ".py"):
        return hits
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        # 排除纯注释行（脚本自身含 PPMID 等黑名单词会自检）
        stripped = line.strip()
        if stripped.startswith(("#", "//")) and "GOVERNANCE_BOUNDARIES.md" not in str(p):
            continue
        for pat in PATTERNS:
            if pat.search(line):
                hits.append((lineno, pat.pattern, line.strip()[:80]))
                break
    return hits


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    if len(sys.argv) > 1:
        targets = [Path(a) for a in sys.argv[1:]]
    else:
        targets = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".py")]
    # 自检豁免：本脚本自身 + 纪律契约 + .learnings/（本身记录具体事件）
    EXCLUDE = ("check_scope.py", "GOVERNANCE_BOUNDARIES.md", ".learnings/")
    total = 0
    for t in targets:
        if any(x in str(t) for x in EXCLUDE):
            continue
        hits = check_file(t)
        if hits:
            total += len(hits)
            try:
                rel = t.relative_to(base)
            except ValueError:
                rel = t  # 外部路径
            print(f"❌ {rel}: {len(hits)} 处疑似项目特定事件污染")
            for lineno, pat, snippet in hits[:3]:
                print(f"   L{lineno} ({pat!r}): {snippet}")
    if total:
        print(f"\n总计 {total} 处——违反 P2 两仓分层纪律（参见 GOVERNANCE_BOUNDARIES.md）")
        print("  处置：删具体事件/数字/PMID；用通用机制描述代替")
        return 3
    print("✅ clean: 专家包内容均为通用机制/治理/版本，无项目特定事件污染")
    return 0


if __name__ == "__main__":
    sys.exit(main())
