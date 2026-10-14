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

## [LRN-20261014-002] best_practice

**Logged**: 2026-10-14T22:40:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
本会话 4 次因 Bash heredoc 内嵌 Python 源码导致转义损坏（f-string 反斜杠、`def` 块错位、`Path` 未 import、sed 双引号失效）

### Details
模式：`python << 'PYEOF' ... PYEOF` 里含 `\'` / 嵌套引号 / `sed -i 's/"x"/"y"/'` 时，shell 与 Python 双层解析互相破坏；报错信息还常具有误导性（如 sed 的 "No such file or directory" 实为引号问题）

### Suggested Action
- **写 Python 文件一律用 Write 工具**（本次修复后全程零转义事故）
- Bash 内 `python -c` 仅限单行简单语句；多行逻辑先 Write 成文件再执行
- managed python 用绝对路径 `/Users/biodog/.workbuddy/binaries/python/envs/default/bin/python`（系统 python3 3.9 不支持 `list[str] | None` 注解）

### Metadata
- Source: error
- Tags: heredoc, escaping, tool-choice
- Recurrence-Count: 4

---

## [LRN-20261014-003] knowledge_gap

**Logged**: 2026-10-14T22:40:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
专家包成员 ID（如 literature-scout）**不可直接作为 Agent 工具 subagent_type**——spawn 返回 "Spawned successfully" 但底层执行时报 "agent literature-scout is not available"（duration 0s）

### Details
register_expert.py 注册的是专家包可见性（WorkBuddy 专家选择器），不等于把成员注册为可 spawn 的 agent 类型。信封契约/装配脚本假设"成员可被主理人 spawn"这一前提在本平台不成立。实测回退：`subagent_type=general-purpose` + 装配 prompt 全文作为任务 = 完全可行（prompt 即人设，与装配哲学一致），name 仍传成员 ID 保 traceability。

### Suggested Action
- 主理人 MD「调度成员」节补一行：subagent_type 用 `general-purpose`，name 用成员 ID，prompt=assemble 输出全文
- 长期：向平台反馈成员注册为 agent 类型的需求；或在 assemble_spawn_prompt.py docstring 记录此回退模式

### Metadata
- Source: error
- Tags: spawn, subagent_type, integration-gap
- Related Files: scripts/assemble_spawn_prompt.py

---

## [LRN-20261014-004] insight

**Logged**: 2026-10-14T22:40:00+08:00
**Priority**: medium
**Status**: pending
**Area**: tests

### Summary
产出端核验关卡的边界案例：外部引文数字（有 URL 在侧）会被本地权威源池标红——这是设计使然，处置靠人判

### Details
D 演练实录：成员简报中"约 79% 从业者"（转述 arXiv:2503.06745）被 verify_member_output 标红（本地池仅含计算产物 CSV/JSON，天然不含外部文献数字）。正确处置不是改关卡放水，而是：主理人核 URL 存在 → 人工放行 + 在 artifact [待人工核验] 区补处置记录。这验证了分工：**确定性关卡负责标红，LLM/人负责裁判**。

### Suggested Action
- 主理人 MD T1 节补一句：关卡标红的数字若来自外部引文（URL 在侧），主理人核 URL 后放行并补标注，不算幻觉
- 可选改进：verify_member_output 支持 `--allow-external-urls`（检测数字同句含 http 则降级为 warn 不阻断）——列入 backlog

### Metadata
- Source: conversation
- Tags: verify-gate, boundary, external-citation
- Related Files: scripts/verify_member_output.py

---
