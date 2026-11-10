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

## [LRN-20261109-013] 守卫无自锚 = 防线可被整体静默摘除
- **Category**: insight | **Severity**: critical | **Status**: resolved (v1.5.4 R-13b)
- **Context**: 任务 B 取证实测：test_contract_guard.py 的 7 项锚点无一锚定自身——空壳化守卫 + 重生成 integrity_manifest 后 EXIT=0 全静默、manifest --check 照样 OK、pytest 收集数表面不变。
- **Insight**: manifest 记录「当前是什么」而非「应该是什么」——以磁盘现状为基线的完整性校验无法检测「校验器本身被替换」；守卫与被守卫对象同文件时，覆盖守卫 = 摘除全部防线。历史事故「tests 被旧基线覆盖→CI 静默 0 覆盖」正是此模式的实发案例。
- **Fix**: 跨文件双向互锚（vendor_core V7 锚 guard 六锚点；guard 第 1 项锚 vendor_core）+ fuzz CASES ≥40 数量下限（拦语料抽稀）。残余：双文件同时覆盖需人工纪律兜底。
- **Prevention**: 任何「防线类」资产必须回答「谁防防线本身」；完整性清单类工具不得作为唯一锚点。

## [LRN-20261109-014] 状态标注的生产者-消费者断链（只写不读 / 只标不查）
- **Category**: insight | **Severity**: critical | **Status**: resolved (v1.5.4 R-13a/c)
- **Context**: 两个同构缺陷：①spawn_manifest.jsonl 只写不读（续跑第 1 步「读 manifest」无代码）；②「轮次耗尽」标注只标不查（poll 只看 mtime，带标注 artifact 判 READY）。
- **Insight**: 契约字段/状态标注必须有「生产者→传递→消费者→判定权威源」四段闭环（A-1 同律）；缺消费端的落盘是死数据，缺机械检查的标注是死文本——主理人「以落盘文件为准」的纪律在没有消费代码时退化为「以人工 cat 为准」。
- **Fix**: poll --from-manifest 打通读取；poll 读 artifact 头 3 行消费撞限标注 → NOT_READY。
- **Prevention**: 新增任何落盘字段/标注时，同步指定其消费者（脚本或门禁锚点）；无消费者的字段不进 schema。

## [LRN-20261109-015] 失效的 ✅：状态文档自述与实物脱钩
- **Category**: correction | **Severity**: medium | **Status**: resolved (v1.5.4 R-13e + 编号4/9 口径)
- **Context**: P4 B-3 标「✅ 已落地」但 T1 段实测无 poll 步骤；validate_contracts「工具索引全清单」实含 6/13；「信噪比 >70%」「3 次指数退避」均为无实现的死声明。
- **Insight**: 状态文档的 ✅ 会随时间脱钩（落地方被回退/部分落地被记全落地）；「全清单」类正则随代码增长漂移。检查状态声明的唯一可信方式 = 实测对应行为（grep 调用点 / 跑行为级用例）。
- **Fix**: B-3 真化（T1 首位真实写入）；白名单 6→13；死声明作废或落地（退避→poll 实装；信噪比→口径订正）。
- **Prevention**: 「✅ 已落地」条目须附可复验锚点（file:line 或测试名）；后续轮审计对每个 ✅ 抽查实测。

## [LRN-20261109-016] 字符串锚 ≠ 行为锚：守卫可被语义空壳化绕过
- **Category**: insight | **Severity**: critical | **Status**: resolved (v1.5.5 R1)
- **Context**: L3 盲检实测：V7 互锚的 6 个锚字符串全保留、`_checks` 改恒真 → V7 仍 PASS。这正是守卫第 7 项批评 fuzz「只锚函数名」的同构缺陷——互锚自身犯了同类错误。
- **Insight**: 存在性检查（字符串/函数名/项数）都是静态锚，可被「保留形态、替换语义」绕过；只有**行为锚**（真加载 + 畸形输入下断言真实 FAIL，即金丝雀）才能区分「守卫活着」与「守卫的尸体还摆着姿势」。
- **Fix**: V7 三层（项数下限静态计数 → 金丝雀行为验证）；`_checks_at(pkg)` 参数化入口使注入可行。
- **Prevention**: 互锚/存活守卫设计时必答「把函数体改成恒真后本守卫是否仍 FAIL」；答案为否 = 只有静态锚，需补金丝雀。

## [LRN-20261109-017] 守卫根选择必须对照真实工作流沙盘推演
- **Category**: correction | **Severity**: high | **Status**: resolved (v1.5.5 R2)
- **Context**: 只读守卫默认根设整个 research-ops，但 run_dir（_harness_runs）、context_stack 渲染、台账维护流的文档工作流全在 research-ops 下——按文档操作 = 被自家守卫阻断（盲检实测）。
- **Insight**: 防线范围（granosity）是安全性与可用性的权衡：整根拦截「安全」但把正常工作流逼向 --allow-readonly 逃生（逃生常态化 = 防线失效）；收窄到事故现场（_archive）才实现「拦该拦的、放该放的」。
- **Fix**: 默认根 = RESEARCH_OPS_DIR/_archive；扩根走显式 DENY（人工决策留痕）。
- **Prevention**: 新守卫上线前跑一遍「按文档工作流走一遍」的沙盘（盲检 R2 的实验路径），确认零误拦。

## [LRN-20261109-018] 守卫「降级不阻断」的兑现需捕获 Exception 而非窄清单
- **Category**: correction | **Severity**: medium | **Status**: resolved (v1.5.5 Y6)
- **Context**: _load_guard 只捕 (OSError, SyntaxError)；guard 文件半损坏（NameError/AttributeError）或 spec=None 时直接 traceback，退出码 1 不在任何脚本契约内。
- **Insight**: 「失败降级」承诺的捕获面必须覆盖「任何加载路径异常」——动态加载的失败模式清单不可枚举（文件损坏方式无限），except Exception 是动态加载边界的正确形态（业务逻辑处仍窄捕）。
- **Fix**: 六脚本 _load_guard 统一 except Exception + type 名入警告。
- **Prevention**: 动态 import/spec_from_file_location 处的降级承诺 → except Exception；窄捕只用于可枚举失败的业务调用。

## [LRN-20261109-019] 接线替换 ≠ 接线插入：守卫接线必须保全既有语句
- **Category**: correction | **Severity**: critical | **Status**: resolved (v1.5.6)
- **Context**: Y4 给 assemble 接守卫时，把 run_dir 的幂等 `mkdir` 当作「写盘点」**替换**成了守卫调用——守卫本应插在写盘**之前**而非替代原语句。新任务 run_dir 不存在 → sidecar FileNotFoundError + 主产物丢失，P0 派工链路崩溃（三轮盲检实测复现）。
- **Insight**: 「写盘点接入守卫」的正确动作是 **插入守卫调用 + 保留原写盘语句**；把原语句当锚点做 replace 时极易滑成「替换」。接线类改动必须跑「按文档工作流全链路」验证（v1.5.5 只测了归档区拦截与已有目录，没测**新目录创建**这条最常见路径）。
- **Fix**: 恢复 mkdir（守卫在前）；退出码表同步补 7。
- **Prevention**: 守卫接线 PR 的验收清单固定含「新对象创建路径」「既有对象更新路径」「只读区拒绝路径」三态实测。

## [LRN-20261109-020] 黑名单校验不如白名单：成员 ID 类标识符一剑封喉
- **Category**: insight | **Severity**: medium | **Status**: resolved (v1.5.6)
- **Context**: Y7 的 member 校验用黑名单（拦 `/`、`..`、前导点等），实测 `a b`/`UPPER`/`$VAR` 全通过——`UPPER` 在 APFS 大小写不敏感卷还能匹配 `upper.md`，跨平台行为分裂；而 9 名成员 ID 实测全为 `[a-z0-9-]+`。
- **Insight**: 标识符类输入（成员 ID/任务 ID/文件名成分）几乎总有严格形态约定——白名单 `fullmatch` 一次表达全部约束，黑名单永远漏「没想到的那一种」；且校验规则的「声称保护对象」要核实（本例「防 G3/G4 读路径探测」中 check_gates 根本不消费 manifest）。
- **Fix**: `[a-z0-9][a-z0-9-]*` 白名单 + 注释如实标注保护范围（仅 poll 自身）。
- **Prevention**: 写校验前先 grep 声称要保护的那个消费者是否真的存在；标识符校验默认白名单。

## [LRN-20261109-021] 治理断言必须配对消费端：「无记录=未发生」没有读的一方就是空话
- **Category**: insight | **Severity**: high | **Status**: resolved (v1.5.8 P0-1)
- **Context**: `authorization_matrix.md` §四 规定「无 decision_log 记录的裁决 = 未发生」，但全包 grep 脚本消费端 = **0**（仅 check_gates.py 一句注释），台账最后更新停在 2026-10-15（25 天）而无人察觉；`CLAUDE.md` 的「审计例行化」待办挂了多个版本。与 LRN-014「只写不读」同构，这次发生在治理层而非数据层。
- **Insight**: 台账/留痕类机制的效力 = 生产者纪律 × **消费者存在性**。只规定「必须写」而没有可机器执行的读方，等于把合规退化为自觉；且写方停摆不会触发任何信号。消费端最低成本形态是**只读审计脚本 + 陈旧阈值**，不必做语义对账。
- **Fix**: `scripts/audit_decision_log.py`（结构/必填/档位/陈旧四查，退出码 0/3/5/6，`--json`），`test_decision_log_audit` 锁退出码与「台账字节不变」；明确不代写台账、不做自由文本语义匹配。
- **Prevention**: 每写下一条「无 X 即视为未发生」的规则，立刻 grep 是否有脚本读 X；没有就把消费端列入同批次交付，不许只留 TODO。

## [LRN-20261109-022] 早退路径是留痕的隐形缺口：报告落盘必须覆盖所有 return
- **Category**: correction | **Severity**: high | **Status**: resolved (v1.5.8 P0-2)
- **Context**: `check_gates.py` 的 `if not g3: return 3` 位于报告落盘代码之前，G3（artifact 缺失）失败时 `gates.json` 完全不生成——恰恰是「最需要留痕判定为何失败」的路径零留痕。AUDIT_STATE §9 早已标为高优先级，因属边界分支被多轮忽略。
- **Insight**: 单一事实源原则不只管正常流程；**每个提前 return 都是一次「落盘是否被跳过」的独立审计点**。把落盘抽成闭包并让所有退出路径共用，比在每个早退处复制写盘更抗回退（守卫第 9 项用 `write_report()` 出现次数 ≥3 直接锚定）。
- **Fix**: 抽出 `write_report()`，G3 早退与正常路径共用；EXIT=3 契约不变；行为级测试断言报告存在、verdict=FAIL、G3=false 与补产出后的覆盖语义。
- **Prevention**: 新增门禁/审计类脚本时，逐个列出所有 `return`/`sys.exit` 点，逐一回答「此处报告是否已落盘」。

## [LRN-20261109-023] 包内互锚挡不住双文件同覆：防线需要包外参照
- **Category**: insight | **Severity**: medium | **Status**: mitigated (v1.5.8 P2-7)
- **Context**: guard ↔ test_vendor_core V7 双向互锚把「旧基线覆盖」攻击面收窄到「两文件同时被覆」，但历史事故正是**整包 tests/ 被覆盖**；包内任何参照都会随覆盖一起消失，只剩人工 diff。
- **Insight**: 自校验系统的根信任锚必须在被校对象之外。包外 sha256 基线不能自动阻止覆盖，但能把「是否被换过」变成一次确定性对账；代价是基线需随正常改动刷新，因此必须标注 `source.tag/commit` 且禁止改锚刷绿。
- **Fix**: `scripts/check_baseline_anchors.py --anchors <包外 JSON>`（0/3/5）+ 审计区 `BASELINE_ANCHORS.json`；路径不硬编码，脚本只读、不生成锚。
- **Prevention**: 设计互锚/自校验时必答「如果这组文件全部被一次性替换，还剩什么能证明」；答案为无 → 补包外锚。状态仅 **mitigated**，须人工刷新基线。

## [LRN-20261110-024] 裁决不配机器消费端，等于允许「文档还在、实现已翻」
- **Category**: correction | **Severity**: high | **Status**: resolved (v1.5.9 ADR-001)
- **Context**: v1.5.8 把 `--require-tag` 默认值裁决写成一句「保持关闭，不改代码」，当时看是诚实收敛；但没有任何机制能发现后续有人把 `default=True` 悄悄加回去——与 LRN-021「治理断言须配消费端」同构，只是这次被断言的是**裁决本身**。
- **Insight**: 「不改代码」不能作为裁决的终点。裁决必须同时具备 ①机器可读真源 ②只读校验脚本 ③违反时的确定性退出码 ④启用前置与迁移路径；否则它只是一段会过期的话。防翻转守卫的价值不在阻止合法变更，而在**让非法变更必然留痕**。
- **Fix**: `docs/decision_records.json`（4 条裁决含 verification）+ `scripts/check_decision_records.py`（`EXIT=5/VIOLATION`）+ `test_decision_records_guard` 用 /tmp fixture 实测「加 default=True → 5」「删裁决文件 → 3」。
- **Prevention**: 写「保持 X 不变」类结论时，立即追问「谁会在 X 被改时报警」；答不出就补消费端，不要只写文档。

## [LRN-20261110-025] SKIP 记成 PASS 是语义空壳化的另一副面孔
- **Category**: insight | **Severity**: high | **Status**: resolved (v1.5.9 ADR-002)
- **Context**: 给 `check_gates.py` 加 G6 时最省事的做法是「默认不评估、gates 列表里不放 G6」，报告照样 `verdict=PASS`。但读报告的人无法区分「检查通过」与「根本没检查」——与之前抓到的「恒真守卫」「撞限标注不消费」是同一类失效。
- **Insight**: 可选门禁必须有三态：`PASS / FAIL / SKIPPED`，且 SKIP 要写进报告的**独立字段**（不是 gates 里的 `ok=true`）。把未评估项混进「全绿」会制造比没有门禁更危险的虚假安全感。
- **Fix**: `gates.json` 增 `skipped_gates`；G3 早退也记「G6 未评估」；`test_g6_evidence_gate` 断言 SKIP 不在 gates 内、启用后必须出现 G6 记录、策略文件也能触发。
- **Prevention**: 新增可选检查时，先写「关闭时报告长什么样」的断言，再写检查逻辑。

## [LRN-20261110-026] 依赖人工兜底的防线，必须把「人工动作」也机制化
- **Category**: correction | **Severity**: medium | **Status**: resolved (v1.5.9 ADR-003 / B-5)
- **Context**: 两个同构实例：①v1.5.8 包外锚标 mitigated，理由「正常改动后人工重生成」，但人工手算 sha 既易错又可被用来改锚刷绿；②cron 目录锁用 `trap rmdir` 清理，实测 macOS 沙箱返回 `Operation not permitted`，锁永久残留、后续巡检全跳过——两者都把可靠性押在「人会正确处理」上，且都没测过失败路径。
- **Insight**: 人工环节不是免责声明。至少要机制化三件事：**显式确认**（ACK+reason）、**前置校验**（干净工作区 / 资源可释放）、**事后可验证**（commit 溯源 / 锁不残留的断言）。
- **Fix**: `--refresh` 须 ACK+reason+干净 git 仓并写 `refresh_history` 与 `source.commit=HEAD`，check 侧校验防刷绿；cron 改 `noclobber`（O_EXCL）文件锁 + `rm -f`，行为级用例明确断言「锁未清理」即 FAIL；两处均配 fixture 实测（含临时 git 仓）。
- **Prevention**: 文档里出现「由人工…」时，立刻补一列「人工做错时谁报警」；清理类逻辑必须实测环境是否真允许该删除操作。

## [LRN-20261110-027] 「脚本存在」不等于「口径已同步」：存活锚必须覆盖消费端文档
- **Category**: correction | **Severity**: high | **Status**: resolved (v1.5.10 R5)
- **Context**: v1.5.9 用守卫第 10 项锁住 7 个新脚本的存活并宣告零挂账；独立只读盲检却抓到 4 个 🔴——CLI argparse description、被 SKILL.md 引为权威的门表、主理人活跃 T1 checkbox 全写 G1-G5 五门，cron 头部注释仍写已被实测废弃的 mkdir 目录锁。全量 pytest/fuzz/守卫/V7 全绿，因为守卫只检查「新脚本在不在」，不检查「当前口径对不对」。另外 §15 已自认 docstring 未同步，却当作「历史文本保留（非漂移缺陷）」豁免——追加说明并不等于修复。
- **Insight**: 「资产存活」与「口径一致」是两个独立断言。升级门禁数量、锁实现、用例数这类**会被人读到并执行**的契约时，消费端文档 / CLI / help 就是防线的一部分；只锚生产端会让「文档停在旧版」成为可静默通过的假陈述。收轮节里写下的每一条「真实未完成」，下一轮都必须按施工项处理，不能靠标注降级为边界。
- **Fix**: 守卫第 11 项正/负双向锚（必须出现的当前口径 + 禁止出现的旧口径）；行为级用例真跑 `--help`、真加载守卫、用整包旧口径副本反向断言第 11 项 FAIL（防恒真）、正则比对 docstring 与 `main()` 用例数；V7 项数下限同步 10 → 11；5 处口径订正 + SOP 历史行销项索引。
- **Prevention**: 每次「新增/升级门禁」收尾加一问：「哪些文档 / CLI 会向操作者描述它？它们也被锚住了吗？」；宣布零挂账前必须跑一次独立只读盲检，不能只信自己写的收轮节。
