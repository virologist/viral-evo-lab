# 两仓分层纪律（P2 · 2026-10-21 · 防控 LRN-20261014-001 复发）

> 背景：本 thread 已发生 2 次"项目特定叙事污染专家团"事件（划界后我又反复把某项目编号映射错误作机制论据）。本纪律是该模式的根治契约。

## 三类位置 × 三类内容

| 位置 \ 内容 | 通用机制/治理/版本（✅） | 项目特定事件/数字/PMID/位点（❌） |
|---|---|---|
| 专家包 `*.md` / `scripts/*.py` / `CHANGELOG.md` | ✅ 机制描述、版本号、commit hash | ❌ 任何项目名/位点/具体值 |
| 团队 `CLAUDE.md` Changelog | ✅ 机制+版本+commit hash | ❌ |
| `.learnings/LEARNINGS.md` | ✅ 抽象模式（LLM 数字幻觉拦截/项目叙事污染） | ❌ 任何具体值（记 `Correction: <机制>+<频率>，不引具体项目） |

## 落盘前自检（每个持久化文件 5 秒）

```bash
# 任何专家包落盘前跑：检查是否含"项目特定关键词"
grep -E "<项目名>|<具体位点>|【具体PMID】|<具体仓库路径>" \
  $P/<新文件> 2>/dev/null && echo "❌ 污染——回退到通用语言" || echo "✅ clean"
```

## 经验边界升级
- LRN-20261014-001 Recurrence-Count: 2（critical）→ 下次复发即升 Status 为 wont_fix（本人不可被纠正，放弃治疗）
- Promote to CLAUDE.md：本纪律在 R13 当晚生效，应同时写入 `viral-evo-lab/CLAUDE.md` 顶部

## 正确示范 vs 错误示范

❌ 错误：`"用 GENERAL_LLM_HALLUCINATION 案例的 LRN-20261014-001 拦截"——在 verify_numbers.py docstring 写"A156T=20.58% 事故根治"`
✅ 正确：`"LLM 成员可能编造关键数字，结构化校验属确定性工程"——docstring 用通用设计动机`
