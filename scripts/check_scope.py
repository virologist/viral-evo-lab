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

# R4.2/R4.3：复用单一事实源的不可见字符检测（Cc/Cf/U+FFFD），避免内联判定与守卫漂移
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text_guard import has_forbidden, _EQUIV_TRANS  # noqa: E402

# R4.21（盲检 B🔴6）：紧凑投影的分隔符字符集此前硬编码 `。．｡` / `,，`，
# 漏掉 _text_guard._EQUIV_TRANS 中的多语小数点（U+066B/00B7/30FB/FF61/
# 2022/06D4/0387/2027/FF0E）与阿拉伯千分位（U+066C）。根因修：从单一事实源
# _EQUIV_TRANS **反向提取**所有映射为 '.' 或 ',' 的源字符，投影集自动随
# 单一事实源扩展，不再枚举（枚举补不完）。
_DOT_SEPS = "".join(sorted(
    chr(k) for k, v in _EQUIV_TRANS.items() if v == ".")) + "。．｡."
# ASCII 逗号是千分位投影的目标字符本身（_EQUIV_TRANS 的值而非键），须显式纳入。
_COMMA_SEPS = "".join(sorted(
    chr(k) for k, v in _EQUIV_TRANS.items() if v == ",")) + "，,"
_DOT_CLASS = "[" + re.escape(_DOT_SEPS) + "]"
_COMMA_CLASS = "[" + re.escape(_COMMA_SEPS) + "]"

# 项目特定叙事黑名单（关键词式；命中即疑似污染）
# 原则：禁"具体事件"（错案位点+具体数字+具体PMID+具体事故日）
# 不禁"领域通用"（糖基化、亚型名、位点符号本身）
# B5（2026-11-07）：移除单点事故的位点断言/短语模式（A156T*、编号映射错误、
# G140 mapping error 等具体事件记忆）——黑名单只保留「结构性污染信号」
# （具体 PMID/commit 片段/错误数值/草稿状态），位点级叙事防复发改由
# spawn 时的知识态注入（R11）+ T1 审判关卡承担。具体事件史归工作空间 ledger。
# R4.8（盲检 A🟠2/B🟠）：同名治理正本在任意目录均享受豁免 → 伪造目录绕过。
# 改为包内绝对路径精确匹配，仅真治理正本与本脚本自身豁免。
_PKG_ROOT = Path(__file__).resolve().parent.parent
_GOV_DOC = (_PKG_ROOT / "GOVERNANCE_BOUNDARIES.md").resolve()
_SELF_EXEMPT = frozenset((_GOV_DOC, (_PKG_ROOT / "scripts" / "check_scope.py").resolve()))

PATTERNS = [
    re.compile(r"PP\s*41034380"),                                # 具体 PMID
    re.compile(r"\.pre-[A-Za-z0-9_-]+"),                          # 特定事故的 backup 命名
    re.compile(r"1094(?![0-9A-Za-z])"),                                        # commit hash 片段
    re.compile(r"20\.58%"),                                      # 事故具体错误值
    re.compile(r"0\.2058(?![0-9A-Za-z])"),                                    # 事故具体错误值（裸数字）
    re.compile(r"\[39,40\]|\[40,39\]"),                          # 事故草稿引用号冲突
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
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        # R4.2（盲检🔴6）：R4.1 把不可解码当"无命中"实为 fail-open——UTF-16
        # 污染文件被整体跳过 → 误判 clean EXIT=0。改为记一条"无法核验"命中，
        # 由 main 判 EXIT=3（与 validate_contracts/check_gates 的 fail-closed 同口径）。
        return [(-1, "UNREADABLE", f"{type(e).__name__}: 文件不可解码，无法核验是否含项目特定叙事")]
    if has_forbidden(text):
        # 无 BOM UTF-16 的 NUL/Cf 零宽字符交错是合法 UTF-8，解码不抛异常——显式检测
        return [(-1, "UNREADABLE", "含 Cc/Cf 不可见字符或 U+FFFD（疑二进制污染），无法核验")]
    # R4.14（盲检 A🔴5）：非 Mn 的 Sm/Po/Pd 符号插进事故值（10⬰94/10！94）
    # 同样让黑名单正则静默失配 → clean。用匹配用途归一化剥除非 ASCII 符号。
    from _text_guard import normalize_for_matching  # R4.10: 事故值全角归一化
    # R4.18（盲检🔴6）：原逐行匹配使「位置映射\n错误」跨行拆段后每行都
    # 不含完整黑名单词 → clean fail-open。黑名单词义完整即可，行边界无
    # 语义——追加**全文归一化扫描**（换行被 normalize_for_matching 剥除，
    # 跨行叙事自动接续）。逐行扫描保留用于精确行号报告与治理正本注释豁免。
    full_norm = normalize_for_matching(text)
    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = normalize_for_matching(raw_line)
        # R4.6（盲检🔴 B3）：原实现把整行 `#`/`//` 开头的行全部跳过——md 标题
        # （`# 事故复盘：PP 41034380`）同样以 `#` 开头 → 事故叙事藏在标题里即可
        # 绕过 scope 检查 → 误判 clean EXIT=0（fail-open）。
        # 收窄豁免：仅当黑名单命中位于「注释标记之后紧邻的注释正文」且该行本身
        # 是代码注释（`# ` / `// `）时跳过——但 md 的 `# ` 标题无法仅凭前缀区分。
        # 正确处理：不再按前缀整行跳过，而是**照常扫描所有行**；脚本自检误报问题
        # 由 GOVERNANCE_BOUNDARIES.md 白名单处理（维持原特例），其余文件一视同仁。
        stripped = line.strip()
        # R4.7（盲检 B🟠2）：原用 `str(p)` 子串匹配 → 目录名
        # `GOVERNANCE_BOUNDARIES.md_evil/evil.md` 也命中豁免，事故的标题叙事
        # 再次被放行。改为文件名精确相等（治理正本只有一个）。
        is_governance_doc = p.resolve() == _GOV_DOC
        for pat in PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            # 仅豁免：治理正文本身，且命中在行首注释标记之后（自描述黑名单词场景）
            if is_governance_doc and stripped.startswith(("#", "//")):
                continue
            hits.append((lineno, pat.pattern, line.strip()[:80]))
            break
    # R4.18（盲检🔴6）：全文扫描补跨行拆段。仅收黑名单命中且尚未被逐行
    # 捕获的 pattern（用 pattern 去重，避免同一污染重复计数）。
    seen_pats = {h[1] for h in hits}
    for pat in PATTERNS:
        if pat.pattern in seen_pats:
            continue
        if pat.search(full_norm):
            hits.append((-1, pat.pattern, full_norm.strip()[:80]))
    # R4.19（盲检 A🔴1/B🔴3/B🔴4）：匹配用途归一化剥离中文句号 U+3002
    # （`20。58%`→`2058%`）与保留千分位逗号（`PP 41,034,380` 字面量失配）
    # 使事故值/PMID/commit 黑名单永假。根因修在匹配侧再加**数字紧凑投影**：
    # 在**原文**上只把「数字与数字之间」的句号型小数点归一为 `.`、千分位
    # 逗号剥离，再走同一 normalize_for_matching（否则 U+3002 已被上一步
    # 剥掉无法恢复）。不改原文、不影响句尾句号（非数字间）与合法字段边界
    # （逗号后非数字）。此投影局部于 check_scope——不动 normalize_for_matching
    # 本身（verify_numbers 侧 `n = 94。结论` 的合法中文句号须保持）。
    # R4.20（盲检 B🔴1/B🔴2）：原投影要求分隔符两侧**紧邻**目标字符，
    # `20。 58%` / `41, 034,380` / 全角逗号 `41，034` 均因空白或非 ASCII
    # 逗号漏投影 → 后续 normalize_for_matching 剥掉句号、保留逗号 →
    # 黑名单字面量永假。根因修：投影本身按「分隔点 + 两侧空白」语义匹配，
    # 并纳入全角逗号 U+FF0C；仍只作用于数字/字母之间，不动句尾标点。
    compact_src = re.sub(r"(?<=\d)\s*" + _DOT_CLASS + r"\s*(?=\d)", ".", text)
    # `.pre-backup-...` 黑名单前置可为字母（`file。pre-...`），句号同样
    # 充当分隔点；字母侧同样归一。
    compact_src = re.sub(r"(?<=[A-Za-z0-9])\s*" + _DOT_CLASS + r"\s*(?=[A-Za-z0-9])",
                         ".", compact_src)
    compact_src = re.sub(r"(?<=\d)\s*" + _COMMA_CLASS + r"\s*(?=\d)", "", compact_src)
    seen_pats = {h[1] for h in hits}
    if compact_src != text:
        compact_norm = normalize_for_matching(compact_src)
        for pat in PATTERNS:
            if pat.pattern in seen_pats:
                continue
            if pat.search(compact_norm):
                hits.append((-1, pat.pattern, compact_norm.strip()[:80]))
                seen_pats.add(pat.pattern)
    # R4.21（盲检 B🔴6）：多语小数点（U+066B/30FB/00B7…）可能是千分位语义
    # （`41٫034380` 即 41034380），上一步投影成 `41.034380` 后点被保留，
    # 黑名单字面量仍失配。根因修：再做一次「数字间任何分隔符一律剥离」的
    # 紧凑投影（千分位语义），两种投影都扫——点型保小数点、剥离型保分组，
    # 覆盖同一字符的两种语境，不误伤合法文本（只匹配数字间的分隔符）。
    all_seps = "[" + re.escape(_DOT_SEPS + _COMMA_SEPS) + "]"
    stripped = re.sub(r"(?<=\d)\s*" + all_seps + r"\s*(?=\d)", "", text)
    if stripped != text:
        strip_norm = normalize_for_matching(stripped)
        for pat in PATTERNS:
            if pat.pattern in seen_pats:
                continue
            if pat.search(strip_norm):
                hits.append((-1, pat.pattern, strip_norm.strip()[:80]))
                seen_pats.add(pat.pattern)
    return hits


def main() -> int:
    # C5（2026-11-07）：--help 支持（argparse 接管路径参数，默认全仓）
    import argparse
    ap = argparse.ArgumentParser(
        description="专家包落盘前自检：检查 .md/.py 是否含项目特定叙事（两仓分层纪律，详见 GOVERNANCE_BOUNDARIES.md）")
    ap.add_argument("paths", nargs="*", help="待检路径（默认全仓 .md/.py）")
    args = ap.parse_args()
    base = Path(__file__).resolve().parent.parent
    if args.paths:
        # R4.21（盲检 A🔴4）：原实现把显式参数逐字当文件路径，传目录时
        # check_file 对无 .md/.py 后缀的目录直接返回 []，检查 0 个文件却
        # 输出「全部干净」 EXIT=0——空工作量被当成功。根因修：显式路径
        # 同样展开为文件集（目录 rglob 收 .md/.py），展开后为空即结构错误。
        targets = []
        for raw in args.paths:
            p = Path(raw)
            if p.is_dir():
                targets.extend(f for f in p.rglob("*")
                               if f.is_file() and f.suffix.lower() in (".md", ".py"))
            else:
                targets.append(p)
        if not targets:
            print("❌ 待检路径展开后无 .md/.py 文件（拒绝以零检查量报 clean）",
                  file=sys.stderr)
            return 3
    else:
        targets = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".py")]
    # 自检豁免：本脚本自身 + 纪律契约 + .learnings/（本身记录具体事件）
    # R4.7（盲检 B🟠2）：原用 `x in str(t)` 子串匹配 → 任何路径里含
    # `GOVERNANCE_BOUNDARIES.md` 字样的目录（如 ..._evil/）整目录被跳过，
    # 标题叙事二次绕过。改为文件名精确相等 + 路径段精确相等。
    total = 0
    for t in targets:
        # R4.20（盲检 A🟠7）：`.learnings` 豁免只适用于包内路径；显式传入的
        # 外部文件仅因路径里出现该目录名就被判 clean，是 fail-open 面。
        if t.resolve() in _SELF_EXEMPT or (
                ".learnings" in t.parts and t.resolve().is_relative_to(base)):
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
