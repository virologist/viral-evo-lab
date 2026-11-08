# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20261014-001] correction

**Logged**: 2026-10-14T21:08:00+08:00
**Priority**: critical
**Status**: resolved
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

### Resolution
- **Resolved**: 2026-11-07（B5 执行）
- **Commit/PR**: 待本轮 A 组 commit hash（assemble_spawn_prompt.py :407 注释与 check_scope.py 黑名单位点模式已泛化/移除，check_scope 全仓 clean）
- **Notes**: 包内最后一处项目叙事（装配器注释 + check_scope 位点断言）已清除；防复发机制 = check_scope.py 结构性黑名单 + spawn 时 R11 知识态注入

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
**Status**: resolved
**Area**: infra

### Summary
专家包成员 ID（如 literature-scout）**不可直接作为 Agent 工具 subagent_type**——spawn 返回 "Spawned successfully" 但底层执行时报 "agent literature-scout is not available"（duration 0s）

### Details
register_expert.py 注册的是专家包可见性（WorkBuddy 专家选择器），不等于把成员注册为可 spawn 的 agent 类型。信封契约/装配脚本假设"成员可被主理人 spawn"这一前提在本平台不成立。实测回退：`subagent_type=general-purpose` + 装配 prompt 全文作为任务 = 完全可行（prompt 即人设，与装配哲学一致），name 仍传成员 ID 保 traceability。

### Suggested Action
- 主理人 MD「调度成员」节补一行：subagent_type 用 `general-purpose`，name 用成员 ID，prompt=assemble 输出全文
- 长期：向平台反馈成员注册为 agent 类型的需求；或在 assemble_spawn_prompt.py docstring 记录此回退模式

### Resolution
- **Resolved**: 2026-10-15（v1.3.0 M1 落实）
- **Commit/PR**: db9bb02（LRN-003 回退模式写入装配 docstring + 主理人 MD 协作规则 5）
- **Notes**: 回退模式已机制化——主理人 MD 协作规则 5 明文 + 装配器 docstring 记录；本次 A2 复查确认在位

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

## [LRN-20261015-005] correction

**Logged**: 2026-10-15T06:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: tests

### Summary
R12 冒烟测试时在权威源池（research-ops/outputs/）放置了手编常量 CSV（M18.csv），直到 A→D 收官审计才发现——假数据在池里会被 V1/产出端核验当真源匹配，等于核验关卡失效

### Details
冒烟测试的产物与真实权威源混居同一目录，无隔离标记。D 演练时 verify_member_output 用该池匹配成员产出中的真值数字（0.9441 等），"found" 是假象——匹配到的是我自己编的冒烟常量。

### Suggested Action
- ✅ 已删 M18.csv + outputs/README.md（"本目录不放示例/冒烟数据"）
- 规则固化：**冒烟测试的权威源必须用 /tmp 或独立 smoke 目录，禁止入项目权威源池**；verify 类脚本加 `--sources` 显式指向时，主理人须确认路径非 smoke
- LRN-004（外部引文数字边界）的完整链条：关卡边界 = 本地池真伪 × 外部引文人判，两端都要人管

### Resolution
- **Resolved**: 2026-10-15（当日已删 + 3dbcbae 登记）
- **Commit/PR**: 3dbcbae
- **Notes**: 防复发规则固化入 outputs/README.md；2026-11-07 A6 复查确认无同类污染

### Metadata
- Source: conversation
- Tags: smoke-test, authoritative-pool, contamination
- Recurrence-Count: 1
- See Also: LRN-20261014-004

---

## [LRN-20261015-006] insight

**Logged**: 2026-10-15T06:50:00+08:00
**Priority**: high
**Status**: resolved
**Area**: tests

### Summary
五维度并行诊断中，诊断子代理自身出现证据幻觉（5 条 spot-check 里 2 条被证伪：声称"20.58% 幻觉值在 frontier-2025-2026.md:12"实为 GOVERNANCE_BOUNDARIES.md 的反面示例；声称"_trash_20261014 58M 失踪"实为存在）——子代理的"证据"同样需要验证层

### Details
今天让 5 个 general-purpose 子代理并行诊断专家团，回传质量总体高（每条带文件:行号），但抽查发现 2/5 条要害证据不实。模式：子代理把"黑名单/反面示例中出现的关键词"误报为"正文污染"；把 find 命令失败误报为"文件失踪"。这与 MAST 分类学的 Superficial Verification 失败模式同构——**验证者本身也会表面验证**。

### Suggested Action
- 诊断/审计类子代理回传后，**主理人必须抽查 ≥2 条要害证据**（grep 原文）才可采信进报告——本次已执行并当场纠正
- 子代理 prompt 应要求："证据须给可复核的定位（文件:行号+原文摘录），不得只给结论"——本次 prompt 已含此要求但仍出现幻觉，说明要求不够，需加"摘录原文片段"
- 团队 V 层哲学（确定性关卡+人判）对子代理产出同样适用

### Resolution
- **Resolved**: 2026-10-21（v1.5.0-rc1-tA1 机制化）
- **Commit/PR**: 87db1c8（CLAUDE.md §1 子代理证据纪律 + 主理人 MD T-A1 门）
- **Notes**: 抽查 ≥2 条含原文摘录已是强制门；2026-11-07 独立诊断中主审对 3 路子代理执行 10 项抽查（纠正 1 处 grep 假阴性），纪律有效

### Metadata
- Source: conversation
- Tags: subagent-hallucination, verification, MAST
- Recurrence-Count: 1
- See Also: LRN-20261014-004, LRN-20261015-005

---


## [LRN-20261108-007] bug

**Logged**: 2026-11-08T17:50:00+08:00
**Priority**: high
**Status**: resolved
**Area**: scripts

### Summary
「文档声称已落地、代码却无消费点」再次出现两例：`require_tag` 闸在 4 个调用点全部不传 True（`CLAUDE.md` 却记为已落地），`--gate` 定义后 `args.gate` 零消费且无条件 `return 5`。二者都属「防线存在但未接线」，静态文档检查无法发现。

### Details
- `verify_numbers.py:95` `require_tag: bool = False`，4 个调用点（自身 main、`verify_member_output.py`、`check_gates.py`）均不传 True → LRN-005 假数据防线虚设。
- `verify_member_output.py` 的 `--gate` 是死参数 → DEGRADE 无机制阻断，返工纯靠主理人裁量。
- 共同模式：**开关/参数已定义 ≠ 已接线**；验收必须看到「消费点」而非「定义点」。

### Suggested Action
- 凡新增布尔开关，必须同时给出「三点接线清单」（定义点 + 全部消费点 + 透传点）并用自动守卫守住。
- 行为级测试优先于文本存在性检查：同一输入在开/关两态下 EXIT 码必须不同。

### Resolution
- **Resolved**: 2026-11-08（v1.5.2）
- **Commit/PR**: 本轮提交
- **Notes**: 三点 `--require-tag` 全部接线；`test_gate_fuzz.py::test_require_tag_gate` 两态行为断言；`test_contract_guard.py` 第 5 项守「三点接线存活」。`--gate` 改为写 `gate_mode=block` 并由 G4 消费，L2 实测 warn→EXIT 0 / block→EXIT 5。

### Metadata
- Source: conversation
- Tags: dead-parameter, unwired-gate, behavioral-test
- Recurrence-Count: 2
- See Also: LRN-20261015-005

---

## [LRN-20261108-008] insight

**Logged**: 2026-11-08T17:55:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: tests

### Summary
验收脚本自身再次踩到「zsh 不做 word splitting」：用 `spec="tagged.csv --require-tag"; set -- $spec` 拼参数，zsh 把整串当单个词，导致 `--sources` 路径混进 flag，三态演练全部输出假结果（EXIT 全 5）。

### Details
- 该坑在本仓 CHANGELOG/LEARNINGS 已有记录，但**只约束了生产脚本，没有约束审计者自己的临时验证脚本**。
- 同类先例：BSD grep `\|` 假阴性（上一轮诊断中主审亲踩）。两者同属「验证工具本身的缺陷被误读为被测对象缺陷」。

### Suggested Action
- 多参数 CLI 演练一律**显式写出每个参数**，或用 Python `subprocess` 传 list；禁止用 shell 变量拼接后靠分词展开。
- 演练结果出现「全部与预期相反」时，先怀疑验证脚本，不要先改被测代码。

### Resolution
- **Resolved**: 2026-11-08（本轮 L2 重跑）
- **Notes**: 显式参数重跑后三态为 5/0/0，与 pytest 行为级守卫一致；假结果未写入任何结论。

### Metadata
- Source: conversation
- Tags: verification-tool-bug, zsh-word-splitting, false-negative
- Recurrence-Count: 1
- See Also: LRN-20261015-006

---

## [LRN-20261109-009] insight

**Logged**: 2026-11-09T00:00:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: contract

### Summary
「分支遮蔽」（branch shadowing）是本轮 L3 盲检反复抓到的系统性根因模式：`if/elif` 组织使新加的路径**短路**旧防线，缺陷单点看不出口、组合起来才致命。

### Details
- 实例一：`check_gates.py` G4 用 `if/elif` 组织，「阻断态 DEGRADE 未处置」分支**短路**了 mtime 篡改检测。实测「篡改 artifact + 写 waiver」可让全门禁 EXIT=0——击穿诚实性红线。
- 实例二：`waivers` 变量原本定义在 G2 分支内，G4 段取不到 → 文档承诺的 waiver 放行路径是死路（成员/主理人只剩违反红线的「人工裁量跳过」）。
- 实例三：`workflow` 字段全包无生产者，G1 锚定校验是死代码；且成员自报可降级规避（**自报 = 自证清白**）。
- 共性：单条测试都能过，**只有组合场景的对抗性测试才暴露**。这解释了为何前几轮自测全绿仍留此多缺陷。

### Suggested Action
- 写分支时先问「这条新路径会不会让另一条防线失效」；**判定彼此独立**的检查项，一律用两个独立 `if` + 独立的结果容器（阻断原因 / 解除说明分离），禁止 `elif`。
- 变量作用域按「最宽需求」定义，不按「当前分支需要」定义。
- 契约字段必须同时具备：**生产者 → 传递 → 消费者 → 判定权威源**四要素，缺一即死代码；且权威源不得是被审计方自报。
- 新增断言必须含**组合场景**（篡改+放行、谎报+缺失），不能只测单变量。

### Resolution
- **Resolved**: 2026-11-09（v1.5.3）
- **Notes**: G4 拆为两个独立判定（`problems` / `resolved`）；`waivers` 提到外层；A-1 按「生产者 → 传递 → 判定权威源 → 交叉核验」四段链路闭合；新增 fuzz 11 例 + L2 沙箱 8 场景（真实链路）全绿。

### Metadata
- Source: conversation
- Tags: branch-shadowing, dead-code, contract-gap, independent-checks
- Recurrence-Count: 3
- See Also: LRN-20261108-007

---

## [LRN-20261109-010] insight

**Logged**: 2026-11-09T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: testing

### Summary
断言「不崩溃」的回归套件抓不到**静默失效**——门禁恒判 PASS 或恒判 FAIL 都过得去。本轮 fuzz 套件从「只断言不崩溃」升级为「断言期望行为」才暴露 A-1/A-3/A-6/A-7。

### Details
- 原套件断言：退出码 ∈ {0,3,5}、无 Traceback、gates.json 已落盘。这三条对「G1 恒判 FAIL」同样成立。
- 本轮增「行为断言层」：CASES 可声明期望门禁结果（G1/G2/G4 ok 布尔）+ 期望退出码，逐项断言。
- 配套增 `_read_gates()`：gates.json 里 gate 名是展示文案（如 `G1 信封完整`），按 `name.split()[0]` 归一——**原实现假设键名为 `G1`，导致 11 个用例假失败**（验证工具缺陷被误读为被测对象缺陷，同 LRN-20261108-008）。

### Suggested Action
- 门禁类回归必须断言**期望裁决**，不只断言「没崩」。
- 断言依赖被测对象的具体存储格式时，先读实现确认真实键名，不要按直觉假设。
- 出现「大批用例同时失败」时，先怀疑验证脚本自身，再改被测代码。

### Resolution
- **Resolved**: 2026-11-09（v1.5.3）
- **Notes**: fuzz 用例 27 → 45，行为用例 3 个，合计 48/48；guard 增第 7 项存活守卫防修复被静默回退。

### Metadata
- Source: conversation
- Tags: behavioral-test, silent-failure, regression
- Recurrence-Count: 2
- See Also: LRN-20261108-008

---

## [LRN-20261109-011] correction

**Logged**: 2026-11-09T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: docs

### Summary
文档写「3 = 结构畸形」而代码对台账畸形返回 6——**行为与承诺背离**，且这类矛盾不会被任何自动化测试抓到（测试只断言行为，从不读 docstring）。

### Details
- 根因不是「代码错」而是**判别原则没写清**：`3` 与 `6` 的区别不是「哪个文件坏了」，而是**坏掉后还能不能算出裁决**。
  - 证据源（假说池 / redteam_ledger.csv）畸形 → late_fatal 算不出来 → 无法裁决 → 3。
  - 处置记录（state）畸形 → 证据源完好、裁决可算，保守按未处置 → 6。
- 同类：A-10（领域分析门 vs 团队协作门混列）、A-11（两套脚本退出码相邻并列易误读）。

### Suggested Action
- 退出码契约**按脚本分节**，每节显式声明「本脚本的退出码表」并加「勿跨脚本套用」警示。
- 文档改动后须**回读 docstring 与实现**，做一次「承诺 vs 行为」逐条对照（本轮靠人工交叉审阅发现，A 级自动化难覆盖）。
- 分类判别原则写进文档本身，不要只存在于实现者脑子里。

### Resolution
- **Resolved**: 2026-11-09（v1.5.3）
- **Notes**: 已同步 hypothesis_watch.py docstring / team-contract / quality-gates / team-lead T1+T2 四处。

### Metadata
- Source: conversation
- Tags: doc-code-drift, exit-code-contract, taxonomy
- Recurrence-Count: 2
- See Also: LRN-20261109-009

---

## [LRN-20261109-012] correction

**Logged**: 2026-11-09T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: tooling

### Summary
为验证存量兼容性，直接在 `research-ops/_archive/` 原地跑 `check_gates.py`——该脚本会把门禁报告**写回 run_dir**，覆写了历史快照文件 `T-20261021-D__gates.json`。**Loop B 只读区被写入**，违反双环隔离纪律。

### Details
- `check_gates.py` 无 `--dry-run` / `--no-write`，报告落盘是硬编码行为（`<run-dir>/<task-id>__gates.json`）——这是**设计如此**（门禁报告须落盘供审计），但调用方极易忽略。
- 归档目录里的 `gates.json` 是**历史快照**（ts=2026-10-15），被新一轮运行覆写即丢失历史证据。
- 已用 `git checkout --` 回退单文件，`research-ops` 恢复干净（`git status` 无输出）；复验改用 `/tmp` 副本，G1 PASS 确认存量不误阻断。

### Suggested Action
- **在只读区/归档区跑任何会写盘的脚本，一律先 `cp -r` 到 `/tmp` 再跑**；验证兼容性必须用副本。
- 对只读区的写操作，事后立即 `git status` 核对（research-ops 是 git 仓，回退成本低）。
- 脚本「会落盘」这一行为须在调用方视角显式记账——门禁/核验类脚本的报告落盘是设计意图，不是副作用。
- 归档快照类文件（`*__gates.json` / `*__output-check.json`）视为**证据**，不可被重跑覆盖。

### Resolution
- **Resolved**: 2026-11-09（已回退 + 改副本复验）
- **Notes**: 单文件回退完成；复验结论 G1 PASS（存量 6 字段信封 + 无 sidecar → 不误阻断）。

### Metadata
- Source: conversation
- Tags: read-only-violation, side-effect, evidence-overwrite, dual-loop-isolation
- Recurrence-Count: 1
- See Also: LRN-20261109-009

---
