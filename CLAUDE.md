# CLAUDE.md — 病毒演化研究院团队级运行指南
> 与 README 区分：README = 团队介绍与安装；本文件 = 团队运行机制与上下文接力协议
> 维护者：archivist（史治文）；更新触发：每轮结构变更后
> **Changelog 规范（Anthropic claude-progress.txt 模式）**：每次结构变更追加一条，必含"变更/理由/影响/下一步"四字段；禁止改写历史

## §1 子代理证据纪律（2026-10-21 增补，T-A1 · fix #8 LRN-006）

> 跨层护栏·优先级独立于双轨制与角色映射；本节为 R3（v1.5.0）准入门槛首条，无此纪律其余 R3 修复效果皆不可审计。

**强制要求（强制门）**：所有子代理 / 成员产出，主理人在采信前必须抽查 **≥2 条要害证据**，每条同时含：

1. **`文件:行号` 定位** —— 精确指向被声称的源文件与行号
2. **原文 1-2 行摘录** —— **主理人须自行 Read 该行号**与子代理摘录对照；不一致即视同抽查未通过

**反向 fixture（教训来源：`.learnings/LEARNINGS.md` LRN-006）**：5 条 spot-check 中 2 条被证伪的根因——

- 子代理常把"反面示例中出现的关键词"误报为"正文污染"（黑名单 ≠ 正例）
- 子代理常把 `find` 命令失败误报为"文件失踪"（命令失败 ≠ 文件不存在）
- **共同模式**：子代理写"证据"时只给 `file:行号` 不给原文摘录，主理人无从证伪——这正是"证据幻觉"（MAST Superficial Verification 失败模式）的最高发形态

**契约**：

- 抽查通过的证据**方可**采信入报告 / `decision_log.csv` / `context_stack/*.json`
- 抽查未通过的子代理产出视为**未交付**（与现有"文件缺失 = 未交付"同等待遇）
- 单任务内同类证伪 ≥2 处 → 触发主理人升级：重发任务或换 agent 来源；完整证据链入 `decision_log.csv`

**与 T-A2 决策日志的关系**：证据纪律是决策日志可信度的前提（无原文摘录的决策不可审计）。决策日志首次触发（T-A2 / fix #10 AUTH-M）依赖本节建立——**未立证据纪律不准动决策日志**。

## 双轨运行制（v1.3 起生效，2026-09-26 诊断 D1/D2/D6 的修正）

**快通道（默认）**：日常科研任务由**主会话单人格**执行——方法论沿袭自已退役的单 agent 版 `virus-evolution-researcher` v1.3.0 的假说/检索/迁移/pipeline 四模块与 ACP 编排契约（该包 **deprecated 2026-10-14、已归档 2026-11-04**；规范已内联于本包角色 MD，**此处不是包路径依赖，不读取、不 spawn 该包**），viral-evo-core 作为共享方法库按路径引用。产出**按对应角色 MD 的输出规范**交付（保结构化质量），署名如实标注"单人格执行，参照 XX 角色规范"。**禁止虚构成员署名**。

**慢通道（显式触发）**：用户说"全团审查 / 红队总攻 / 多角色会诊"时，主会话用 Agent 工具**真实 spawn** 3-4 个子代理（各注入对应角色 MD 作为 prompt），并行执行后汇编。仅限两类：WF5 投稿前红队（4 攻击员）+ WF6 重大诊断（勘探/诊断/假说三角）。其余场景禁止 spawn（防 15× token 失败模式）。

| 轨道 | 触发 | 执行者 | 署名 |
|---|---|---|---|
| 快 | 默认 | 主会话（师爷）单人格 | "单人格执行，参照 XX 规范" |
| 慢 | "全团审查/红队总攻/多角色会诊" | 真实 spawn 并行子代理 | 真实记录 spawn 数与回传质量 |

## 角色映射（10 角色，v1.3：medical-vet-bridge 并入 literature-scout）

| ID | 花名 | 触发场景关键词 |
|---|---|---|
| viral-evo-lab-team-lead | 路问渠 | 任何病毒遗传进化/系统发育/分子演化研究请求 |
| hypothesis-officer | 贾思远 | 假说/机制/为什么/创新/演化驱动/预测 |
| phylo-analyst | 舒建树 | 建树/时间树/重配/分子钟 |
| popgen-modeler | 权衍生 | dN/dS/选择压/重组/Ne 动态/群体动态 |
| predictive-virologist | 喻高瞻 | 免疫逃逸/突变适应/变异风险预测/疫苗靶点 |
| structural-virologist | 付尔德 | 蛋白结构/突变功能/糖基化/表位 |
| literature-scout | 文溯源 | 文献检索/前沿/方法借鉴/引用核验/**跨域方法借鉴（坍缩态，原柳通人职责）** |
| pipeline-engineer | 柯力行 | 代码/pipeline/质控/报错/Debug |
| research-diagnostician | 裴慎思 | 审视/诊断/审计/方案改进/合理性 |
| archivist | 史治文 | 勘探/整理/CLAUDE.md/落盘/素材汇编 |

## 工作流触发表

| WF | 触发 | Phase 数 |
|---|---|---|
| WF1 | 假说/机制/为什么/演化驱动/预测 | 4 |
| WF2 | 附件/借鉴/参考某方法 | 3 |
| WF3 | 最新/前沿/数据库版本 | 1 |
| WF4 | 序列/代码/pipeline/数据 | 3 |
| WF5 | 审查/critique/投稿前 | 2 |
| WF6 | 勘探/诊断/审视/审计/改进方案 | 3 |
| WF7 | 跨域方法借鉴/医学流感经验 | 3 |

## 上下文接力协议（接棒规则）
1. **接收方第一步**：读 `research-ops/CLAUDE.md`（项目快照/战线/方法栈/待办/接手建议/Changelog）
2. **接收方第二步**：按相关度读 `context_stack/` **四 JSON 真源**（research_anchor / confirmed_hypotheses / method_library / knowledge_index，以 `render_context_stack.py` 的 RENDERERS 为准）+ 四 .md 渲染视图 + 三协议 .md（user_constraints / quality_gates / diagnostic_findings）
3. **接收方第三步**：执行用户原任务；落盘走 archivist（JSON 编辑 → .md 渲染）
4. **handoff 失败处理**：若发现链路有断层，立即回主理人由主理人调度修复

## 全局重试预算
≤5 次（追问/4R 重入/Gödel 重入/成员返工共享）

## 高危操作
删除/批量覆写/不可逆 → 红色警告 + 二次确认

## 权威源唯一性
- 阈值/前沿/检索源 → `skills/viral-evo-core/references/` 权威
- 项目级快照/锚点/确认假说 → `research-ops/context_stack/` **四 .json 为真源**（research_anchor / confirmed_hypotheses / method_library / knowledge_index；.md 是渲染视图。v1.5.8 订正：原「三 .json」为历史残留，与下方 v1.5.2 订正节及 `render_context_stack.py` RENDERERS 冲突）
- 工作流触发表/角色映射 → 本文件权威

## Changelog
<!-- 规范：每次结构变更追加一条，禁止删除/改写历史；四字段：变更/理由/影响/下一步 -->
<!-- B6 2026-11-07 注：本区为追加式记录、非严格时间序（历史保留不重排，rc 追加批次见各自注释，P3-R2 订正）；包版本叙事权威源 = CHANGELOG.md（Keep a Changelog 格式，最新在上） -->
- **v1.1.1（2026-10-14，B6 2026-11-07 订正：原误标 v1.2.0——此条实际内容为 5 治理约束融入，对应 git tag v1.1.1 / commit 9e49faf；CHANGELOG.md 为版本叙事权威源）**
  - 变更：全天两轮实战（上午 7 步迭代+审计修复 / 下午 M20+M21 统计闭环+v6.5 改稿）；**团队规范零改动**（v1.1.1 已覆盖本轮全部需求——治理 5 约束经实战检验充分）
  - 理由：间隔 14 天回来，专家包 v1.1.0（信封契约/装配脚本/白名单/编号纪律）经受住真实任务检验：2 员实测信封合规 100%、审计抓出 M18 错版 CSV（诚实性红线首例）、一图一 ipynb 首秀成功
  - 影响：**无破坏性**——但确认两点：①M19 编号已被外部模块占用（模块命名需查重）②审计型任务（REVIEWER 工具白名单只读）价值极高，建议保留为常驻角色用法
  - 下一步：PGLMM（R 环境）为 M-01 终裁；v5.1→v6.5 改稿链证明“红队→模块→改稿”流水线成型，可复制到 H10/H1N1
- **v1.2（2026-09-18，P0-3~P1-6 任务）**
  - 变更：①11/11 agent MD 加 stable-prefix 速查卡（身份/触发/输出/回传/纪律五行）②主理人加 Evaluator 反馈路由（WF5/WF6 审查结论→按严重度回 WF4/WF2/WF7/WF3，计入 ≤5 预算）③主理人加动态资源分配表（7 WF 粒度 + 简单查询降级规则）④新增 `references/context-compaction.md` + 主理人/archivist 压缩职责
  - 理由：借鉴 Anthropic prompt-cache stable prefix（省 token）+ LangGraph Evaluator-Optimizer 边（loop 闭环）+ Anthropic 按复杂度分配投入（防过度投入）+ Managed Agents compaction（防 context rot）
  - 影响：所有 agent MD 头部新增统一速查卡（cache 锚点，修改需 bump 注释日期）；WF5/WF6 审查结果不再是终点而是路由起点；长会话需按压缩协议执行
  - 下一步：实测验证（首次实战任务观察路由准确率 + token 消耗 + P0 闭环率）
- **v1.1（2026-09-18，P0-1/P0-2 任务）**
  - 变更：CONTEXT_STACK 三文件 JSON 化（confirmed_hypotheses/method_library/research_anchor，schema 1.0.0）；本文件加 Changelog 规范；上下文接力协议改指 JSON 真源
  - 理由：借鉴 Anthropic feature_list.json 模式（JSON 严格 schema 防 model 改坏 + 跨 session 持久状态）；claude-progress.txt 模式（Changelog 四字段）
  - 影响：所有成员读取 context_stack 必须走 JSON；.md 变为渲染视图，禁止单独编辑；主理人/archivist MD 已同步协议
  - 下一步：P0-3 stable prefix 重排（11 agent MD 顶部前置角色+能力+输出规范，提升 prompt cache 命中）
- **v1.0（2026-09-10，建档）**
  - 变更：初始团队级运行指南（11 角色映射 + WF1-7 触发表 + 接力协议）
  - 理由：与 README 职责分离（介绍 vs 运行机制）
  - 影响：新会话 onboarding 按"项目级 CLAUDE.md → context_stack → 本文件"三步接力
  - 下一步：首次实战任务验证协议
- **v1.5.0-rc1-tA1（2026-10-21，R3 准入门槛首条 · T-A1 / fix #8 LRN-006；B6 2026-11-07 注：此为 v1.5.0 正式版后的 rc 追加批次，tag 日期 2026-10-15，非早于正式版）**
  - 变更：CLAUDE.md 顶部新增 §1「子代理证据纪律」——主理人采信子代理/成员产出前必须抽查 ≥2 条证据，每条含 `file:行号` + 原文 1-2 行摘录；未通过 = 视为未交付
  - 理由：5 spot-check 2 证伪（LRN-006 根因：子代理常"给行号但不给原文摘录"，等同证据幻觉）；R3 不可一日不立白纸纪律
  - 影响：所有慢通道（真实 spawn）/ 任意子代理产出 → 主理人 VERIFY 阶段抽查成为强制门；T-A2 决策日志触发条件同步生效（其依赖本节作为审计前提）
  - 下一步：T-A2 决策日志首次触发（≥5 行真实条目 + 至少 1 个任务压三类升级路径）；B/C/D 路线图 T-B*/T-C*/T-D* 在本纪律立定后启动

## Changelog v1.5.0（2026-10-15 · R3 收官正式版）
- **变更**：R3 全部 10 项落地（T-A1/A2 准入 + T-B1/B2/B3 巡检三件套 + T-C1/C2/C3/C4 高危修补 + T-D1/D2 补丁）；poll_run_dir.py / hypothesis 漂移告警 / require_tag 闸 / decision_log 6 条真实条目
- **理由**：R2 诊断 10 短板清算 + 巡检范式跃迁（轮询→事件驱动）
- **影响**：主理人上下文占用降级；LRN-005/006 双防线机制化；waiver/授权矩阵/契约正本三层治理闭环
- **下一步**：v1.5.1 backlog = T-E1（--require-tag CLI 化）+ decision_log 审计例行化；回滚锚点 v1.4.0-r2-anchor


## 当前口径订正（v1.5.2 · 2026-11-08 · 元层审计第 1 轮）

> 本节为**追加订正**，不改写上方任何历史 Changelog 条目（守本文件第 4 行「禁止改写历史」）。历史叙述仅作差异与证据，当前执行以本节为准。

- **`require_tag` 闸**：v1.5.0 条目所载「闸」在本版才完成三点接线（`verify_numbers.py` / `verify_member_output.py` / `check_gates.py`），且**默认关闭**以保持向后兼容；严审任务须显式传 `--require-tag`。未标记权威源在默认态仍可入池，属已知残余风险（见 CHANGELOG Known Issues）。
- **`--gate`**：不再是未串联的死参数。`verify_member_output.py --gate` 把 `gate_mode=block` 写入 `output-check.json`，`check_gates.py` 的 G4 读到 DEGRADE 未处置即判 FAIL；处置路径仅「补 [待人工核验] 重传」或「waivers.json 放行」两条。
- **契约正本**：`skills/viral-evo-core/references/team-contract.md` 现为 8 条款（新增 `hypothesis_anchor`，分析类 workflow 触发）；`validate_contracts.py` 的条款数文案已动态化。
- **CONTEXT_STACK 口径**：四份 JSON 为机器真源（confirmed_hypotheses / knowledge_index / method_library / research_anchor），`.md` 仅为人类可读渲染视图，禁直编；历史条目中的「三 JSON」表述以本节为准。
- **P4 监控**：B-1/B-2/B-3 已随 v1.5.0 落地；B-4/B-5 未排期。`docs/P4_monitoring_design.md` 末尾过期排期句已订正。
- **假说治理触发器**：新增 `--check-disposition` 纯只读验收（EXIT=6 = 处置台账缺失或不完整）；处置台账由项目侧 archivist 落盘，专家包脚本不代写。

---

## 当前口径订正（v1.5.3 · 2026-11-09 · L3 盲检回补）

> 本节为**追加订正**，不改写上方任何历史条目（守本文件第 4 行「禁止改写历史」）。

- **`workflow` 归一化**：`hypothesis_anchor` 的触发判定不再只认精确 `WF4`/`ANALYSIS`。`check_gates.py` 新增 `normalize_workflow()`——按 `/ - _ · | 空格` 及中文标点切 token，任一 token 命中 `WF4`/`ANALYSIS`/`分析`/`分析执行` 即触发校验。故 `wf4`、`WF4/analysis`、`WF4 分析执行`、`analysis` 等变体**不得绕过**；`no_hypothesis_justification` 允许并列写在信封顶层（与契约正本一致）。
- **G4 waiver 放行路径已接线**：此前 G4 的提示与文档均声称「主理人核 URL 后写 waivers.json 放行」，但实现**完全不读 waiver**——实测写好 waivers.json 后 G4 仍判 FAIL，文档承诺与代码行为背离，主理人只剩违反诚实性红线的「人工裁量跳过」。现 G4 消费同一 `<task-id>__waivers.json`：须 `value`+`reason`+`authorized_by` 三项齐全，且**覆盖全部未溯源数字**才放行（部分覆盖不解除阻断）。G2 同口径补授权校验。
- **`hypothesis_watch.py` 退出码契约修复**：三处 JSON 消费点此前直接 `.get()`/构造 `set`，畸形输入（顶层 list/str/null、非字符串元素、不可哈希元素）抛未捕获异常 → EXIT=1（契约只允许 0/3/5/6）、门禁静默失效。现统一走 `load_json_obj()`/`extract_handled_ids()`/`_row_str()` 安全入口，畸形一律转契约退出码 3；台账畸形按「未处置」保守计（宁可多提醒，不可漏提醒）。
- **`--check-disposition` 不再误阻断存量项目**：此前无任何待处置项的干净项目也因「台账文件不存在」返回 EXIT=6。现区分「无待处置项 + 池未超期 = 无需台账」（EXIT=0）与「确有未处置项/例行复核缺失」（EXIT=6）。
- **WF4 数据质控不再错误绑定数字溯源**：Phase 1 数据质控的门控依据是 `quality-gates.md`「数据质控」行（覆盖度报告 + 异常序列标注），此前 team-lead 误将其绑到 `verify_member_output.py --gate`（数字溯源，属 T1 收产出环节）——两环节不同，已订正。
- **回归基线升级**：fuzz 用例 27 → 34（含 workflow 归一化族 5 例 + 顶层 justification 1 例），另增 3 个**行为级**用例（G4 waiver 放行五路径 / gate_mode 阻断传导 / 处置门禁畸形与误阻断）；`test_contract_guard.py` 增第 6 项「L3 修复存活守卫」（6 个锚点），防本轮修复被静默回退。

---

## 当前口径订正（v1.5.3 追加 · 2026-11-09 · A-1 链路闭合 + 文档口径统一）

> 本节为**追加订正**，不改写上方任何历史条目（守本文件第 4 行「禁止改写历史」）。

- **`workflow` 字段有了生产者与强制力（A-1 闭合）**：`workflow` 此前**全包无任何生产者**（装配脚本 0 处、9 份成员 MD 0 处、信封 schema 无此字段）→ G1 的假说锚定校验在真实链路上是**死代码**。且更深一层：即便成员愿意写，成员也可自报 `WF1` 规避锚定校验（**自报 = 自证清白**）。现按四段链路闭合：
  1. **生产者**：`assemble_spawn_prompt.py --workflow <值>` 新增参数 → 注入 spawn prompt「【工作流声明】」段 + 落 sidecar `<run-dir>/<task_id>__workflow.json`；
  2. **传递**：契约正本要求成员回传时把 `workflow` **原样**写入信封顶层；
  3. **判定权威源**：门禁 G1 以 sidecar 类别（`analysis`/`other`）为准，信封自报仅用于**比对**；
  4. **交叉核验**：下发与回传类别不符（缺失 / 降级 / 升级）即 G1 FAIL；表述差异（`WF4 分析执行` vs `WF4` vs `analysis`）属同一类别不拦；**无 sidecar 的存量链路退回「只信信封」旧行为，不误阻断存量产出**。
  主理人侧强制：**派 spawn 必须带 `--workflow`**，否则 sidecar 不落、强制失效。
- **退出码 3 与 6 的判别原则（A-8 口径统一）**：`hypothesis_watch.py` 的 `3 = 文件缺失或结构畸形` 过于笼统，与「台账畸形按未处置计 → EXIT=6」相矛盾。统一为**「坏掉后还能不能算出裁决」**：
  - **EXIT=3（无法裁决）**：证据源（假说池 / `redteam_ledger.csv`）畸形或缺失 → late_fatal 根本算不出来，无任何可交付判定；
  - **EXIT=6（可裁决但不合规）**：处置记录（`hypothesis_watch_state.json`）畸形 → 证据源完好、裁决可算，保守按「未处置」计。
  已同步 `hypothesis_watch.py` docstring、team-contract、quality-gates、team-lead T2 条目。
- **两类门控分开（A-10 口径统一）**：team-lead「质量门控」段此前把**领域分析门**（数据质控/时间树/ML 树/正选择/引用）与**团队协作门**（G1–G5 脚本化）并列于同一清单，读者会误以为数据质控 = 数字溯源。现拆为 ① 领域分析门（任务内成员自查）/ ② 团队协作门（回传后主理人跑脚本），并明确数字溯源属 T1 收产出环节、**不是** WF4 Phase 1 的数据质控，两者互不替代。
- **退出码勿跨脚本套用（A-11 口径统一）**：team-lead T1 段列的是 `check_gates.py` 退出码（0/3/5），T2 段列的是 `hypothesis_watch.py` 退出码（0/5/6/3），相邻两段并列易被误读为同一套契约。现显式声明两套退出码**不可互换、不可合并解读**，并在 T1/T2 两处各补本脚本的完整退出码表。
- **回归基线再升级**：fuzz 用例 34 → **45**（新增 A-1 交叉核验族 11 例：谎报规避 / 漏回传 / 漏 anchor / 表述差异 / 存量链路 / 伪造升级 / sidecar 畸形），另加 3 个行为级用例，合计 **48/48 全绿**；`test_contract_guard.py` 增第 **7** 项「A-1 修复存活守卫」（生产链路 9 个锚点：装配参数 / sidecar 落盘 / 门禁读取 / 交叉比对 / 契约同步 / 主理人 MD 同步 / 回归用例）；L2 沙箱新增**真实链路**演练 8/8 全绿（装配 → spawn 产物 → 成员产出 → 门禁）。

---

## 当前口径订正（v1.5.8 · 2026-11-09 · 遗留 backlog 清理轮）

> 本节为**追加订正**，不改写上方任何历史条目（守本文件第 4 行「禁止改写历史」）。历史 Changelog 的「下一步」「未推送」等表述仅作历史证据，当前执行以本节为准。

- **decision_log 审计例行化已落地（v1.5.0 条目「下一步」销项）**：新增 `scripts/audit_decision_log.py`，是 `decision_log.csv` 的**首个脚本消费端**（此前全包 grep 消费端 = 0）。只读四查：结构 / 必填字段 / tier 白名单 / 陈旧阈值；退出码 `0 健康 / 3 结构失败 / 5 内容违规 / 6 陈旧提醒`，`--json` 供机器消费。用法：`python3 scripts/audit_decision_log.py <台账.csv> [--max-age-days 30] [--min-entries 1] [--json]`。
- **消费端边界（诚实声明）**：脚本**不代写台账**（与 `check_gates.py`「只校验落盘台账」同口径），也不做「某次具体裁决是否有对应条目」的语义对账——台账 `decision` 为自由文本，机械匹配不可靠，该对账仍属主理人 T2 人工纪律（`docs/authorization_matrix.md` §四）。真实台账最后更新 2026-10-15（6 条），2026-11-09 实测默认 30 天阈值下为 `HEALTHY/EXIT=0`（25 天未超阈值）；收紧到 `--max-age-days 1` 才报 `STALE/EXIT=6`。**台账确已 25 天未更新**，属治理事实，应由 archivist 落盘新条目，不是脚本故障；阈值可按战线节奏调严，但脚本不改数据。
- **`--require-tag` 默认值裁决（CHANGELOG v1.5.2 Known Issues「下一轮评估」销项）**：**保持默认关闭，不改代码**。依据：① `test_require_tag_gate` 已锁定默认关闭的向后兼容契约，翻转即破坏已发布行为；② 存量任务的多数权威源未打 `source_tag: authoritative`，翻转会误杀；③ 严审任务显式传 `--require-tag` 即可，收益不抵回归成本。
- **CONTEXT_STACK 数量口径**：上方「权威源唯一性」节历史残留的「三 .json」已订正为**四 .json**，与 v1.5.2 订正节及 `render_context_stack.py` 的 RENDERERS 一致。
- **G3 失败留痕**：`check_gates.py` 的 `EXIT=3`（artifact 缺失）现在也落 `<task_id>__gates.json`（verdict=FAIL / G3 ok=false）；退出码表不变，仅补报告，失败不再零留痕。
- **包外基线锚（双文件同覆残余的兜底）**：`scripts/check_baseline_anchors.py --anchors <包外 JSON>` 对关键防线文件做 sha256 只读对账；锚文件落在审计区（包外），路径不硬编码。锚文件生成于 v1.5.8 定版后，若此后有正常改动需重新生成基线，勿直接改锚来「刷绿」。

---

## 当前口径订正（v1.5.9 · 2026-11-10 · 「裁决与真实未完成」清理轮）

> 本节为**追加订正**，不改写上方任何历史条目。v1.5.8 §14 把 1 项裁决 + 6 项真实未完成列为「不施工 / 不代写 / mitigated」；本轮按用户「直至全部任务完成」的显式授权全部施工闭合，以下口径覆盖 v1.5.8 的「明确不做」四条。

- **`--require-tag` 裁决已工程化**：保持默认关闭**不变**，但新增 `docs/ADR-001_require_tag_default_off.md` + `docs/decision_records.json`（机器真源）+ `scripts/check_decision_records.py`（防翻转守卫，`EXIT=5/VIOLATION`）。变更后须跑 `python3 scripts/check_decision_records.py`；翻转默认值须先满足 ADR-001 的 `enable_when` 三条并升主版本。
- **门禁从 G1-G5 变为 G1-G6**：G6 抽查留痕默认 SKIP，但 `gates.json` 必写 `skipped_gates`（**不把没检查写成 PASS**）；`--require-evidence-check` 或 run_dir 下 `evidence_check_policy.json {"enabled": true}` 启用后不合格 `EXIT=5`。只验形式要件（≥2 条 lead / file:行号 / 原文摘录 / reason），语义真伪仍归 T1。
- **决策台账口径更新**：`reconcile_decisions.py` 只出候选与 `[DRAFT·待人工终裁]` CSV，**拒写台账**（ADR-004）；台账本身已于 2026-11-10 由主理人授权补落 5 条真实裁决（6 → 11 条，实测 `HEALTHY/EXIT=0`）。v1.5.8 订正节「台账 25 天未更新、应由 archivist 补落，本轮不代写」为历史文本，**已销项**。
- **包外锚从 mitigated 升为 fixed**：`check_baseline_anchors.py --refresh --i-acknowledge-refresh --reason "<理由>" [--git-log <JSONL>]` 受控刷新（干净工作区 + 包外锚 + 文件齐全），写 `refresh_history` 与 commit 溯源；check 校验 `source.commit == git HEAD`，改锚刷绿会被抓（EXIT=3）。刷新仍是**人工动作**，默认只读不变。
- **P4 B-5 / V2 销项**：`cron_watch.sh` + `install_cron_watch.sh` 资产就绪，安装器 **dry-run 默认**，未执行 `--install`、系统 crontab 零改动；V2 联邦真源归属实证为 `https://github.com/virologist/my-experts-plugins.git`（`shared-core/`），结论见审计区 `VENDOR_PROVENANCE.md`，`VENDOR.json` 的 `upstream_repo` 口径偏差按联邦红线不擅改。
- **回归基线**：fuzz 45 CASES + 14 行为级 = **59/59**；守卫 **10/10**；V7 下限 10；pytest 全绿；四处 version = **1.5.9**。

---

## 当前口径补正（v1.5.10 · 2026-11-10 · L3 盲检 R5）

> 本节为**追加订正**，不改写上方任何历史条目。v1.5.9 §15 的「零挂账」结论经独立只读盲检实证**不成立**；下列口径覆盖上节的「回归基线 59/59、守卫 10/10、version 1.5.9」。

- **「零挂账」为何失真**：v1.5.9 守卫第 10 项只锚「新脚本存在」，没有锚「权威文档 / CLI 的当前口径」。代码升到 G1-G6 后，`check_gates.py --help`、`skills/viral-evo-core/references/quality-gates.md` 门表、`agents/viral-evo-lab-team-lead.md` 活跃 T1 条款仍写 G1-G5 五门；`cron_watch.sh` 头部仍写已废弃的 mkdir 目录锁；`test_gate_fuzz.py` docstring 停在 v1.5.8——而全部测试仍全绿。**4 个 🔴 + 1 个自认残留已全部订正**。
- **防复发机制**：`tests/test_contract_guard.py` 新增第 11 项「当前口径一致性守卫」（正/负双向锚）；`tests/test_gate_fuzz.py` 新增 `test_current_wording_guard`（真跑 `--help` + 真加载守卫 + 旧口径整包 fixture 反向断言 FAIL + docstring/total 数字一致性）；`test_vendor_core.py` V7 下限 10 → 11。今后「代码升级但文档留在旧版」不再能全绿通过。
- **当前基线**：fuzz 45 CASES + 15 行为级 = **60/60**；守卫 **11/11**；V7 7/7；pytest **18 passed**；四处 version = **1.5.10**。
- **历史文本纪律不变**：CHANGELOG / CLAUDE 中带版本标题的历史条目仍保留原样；本次只订正**无版本标注的活跃条款**，SOP 历史行以「追加销项索引」处理。

---

## 当前口径补正（v1.5.11 · 2026-11-10 · 终验盲检 R6）

> 本节为**追加订正**。v1.5.10 的独立终验盲检再次证伪「零挂账」，抓到的是**新防线自身的自审漏洞**；上节关于 `test_current_wording_guard` ③④ 的描述为 v1.5.10 时点声称，实际实现有落差，以下口径覆盖之。

- **三处实证漏洞（均已修）**：①守卫第 11 项只禁 `last_updated: 2026-10-14`，把日期换成任意其它旧值仍全绿 → 补 `last_updated: 2026-11-10` **正向锚**；②`_wording_counts()` 的 `re.search` 命中 docstring 自己（自证），实测把 `main()` 的 total 改成 `+14` 断言仍通过 → 改为只在 `main()` 函数体内取 total，并加「仅改 main() 必被抓」反向断言；③反向 fixture 只改 1 文件 1 锚，其余 12 个正向锚从未被反验 → 扩为**逐锚回退**（13 正向锚摘除 + 3 旧口径串注入，共 16 次逐项断言 FAIL）。
- **单一事实源**：锚清单提为 `test_contract_guard.py` 模块级 `WORDING_POSITIVE` / `WORDING_NEGATIVE`，守卫与反向用例共用；第 11 项逻辑抽为 `check_current_wording(pkg_root)`，`_checks_at` 直接 append 其返回值并由行为级用例断言接线。反向用例只调该函数并只复制被检 5 文件，实测 157s → 约 10s（`pytest --durations` 单次实测；全套 18 passed）。
- **当前基线**：fuzz 45 CASES + 15 行为级 = **60/60**；守卫 **11/11**；V7 7/7；pytest **18 passed**；四处 version = **1.5.11**。
- **纪律更新（LRN-028）**：写「校验 X 与 Y 一致」前先确认正则第一个命中的位置；写「全部 / 整包」前先数代码循环覆盖几个；自审防线必须配「改动目标后断言 FAIL」的反向用例；宣布零挂账前必跑独立只读盲检。

