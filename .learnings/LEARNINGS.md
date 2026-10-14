# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20261014-001] correction

**Logged**: 2026-10-14T21:08:00+08:00
**Priority**: critical
**Status**: pending
**Area**: docs

### Summary
用户两次（15:42 划界、21:02 明确批评）要求"本 thread 只关注专家团本身，不掺杂项目具体任务/事件"——但我在 R12 交付叙事、verify_numbers.py docstring、方法卡 pitfall 三处反复用 H5Nx 某编号映射错误当论据

### Details
教训是设计级（VERSION 正则误滤、:g 截断假阳性、md 循环自证），但我用"具体事件"做论据，违反了用户明确划界
机制本身（LLM 数字幻觉拦截）用通用理由完全自洽
15:42 用户原话："本thread中仅关注智能体专家团的优化和进化，不关注具体的任务（如改v6.6），你怎么记不住呢"
21:02 用户原话："A156T 事故链条跟你优化专家团没有一毛钱关系，为什么紧咬这样的污染不放，清理上下文"

### Suggested Action
- 任何"通用机制需要论据"时，使用：**①机制本身的设计目标** ②**通用 LLM 行为模式** ③**抽象的 bug 类型**——禁止使用具体项目事件/数字/PMID/具体仓库路径作为论据
- 持久化资产（脚本 docstring、方法卡、变更日志）落盘前自检：用 `grep "<项目名>\|<具体位点>\|<具体PMID>" 文件` 验证无项目特定叙事
- 跨 thread 划界：用户划界后，**任何"顺便提一下 X 项目"即越界**

### Metadata
- Source: user_feedback
- Related Files: scripts/verify_numbers.py, context_stack/method_library.json, .workbuddy/memory/2026-10-14.md
- Tags: thread-scope, contamination, general-language
- Recurrence-Count: 2
- First-Seen: 2026-10-14T15:42
- Last-Seen: 2026-10-14T21:02

---
