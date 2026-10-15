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

**快通道（默认）**：日常科研任务由**主会话单人格**执行——能力承载 `virus-evolution-researcher`（v1.3.0，含假说/检索/迁移/pipeline 四模块 + ACP 编排契约），viral-evo-core 作为共享方法库按路径引用。产出**按对应角色 MD 的输出规范**交付（保结构化质量），署名如实标注"单人格执行，参照 XX 角色规范"。**禁止虚构成员署名**。

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
2. **接收方第二步**：按相关度读 `context_stack/` **三 JSON 真源**（research_anchor / confirmed_hypotheses / method_library）+ 三 .md 渲染视图 + 三协议 .md（user_constraints / quality_gates / diagnostic_findings）
3. **接收方第三步**：执行用户原任务；落盘走 archivist（JSON 编辑 → .md 渲染）
4. **handoff 失败处理**：若发现链路有断层，立即回主理人由主理人调度修复

## 全局重试预算
≤5 次（追问/4R 重入/Gödel 重入/成员返工共享）

## 高危操作
删除/批量覆写/不可逆 → 红色警告 + 二次确认

## 权威源唯一性
- 阈值/前沿/检索源 → `skills/viral-evo-core/references/` 权威
- 项目级快照/锚点/确认假说 → `research-ops/context_stack/` **三 .json 为真源**（.md 是渲染视图）
- 工作流触发表/角色映射 → 本文件权威

## Changelog
<!-- 规范：每次结构变更追加一条，禁止删除/改写历史；四字段：变更/理由/影响/下一步 -->
- **v1.2.0（2026-10-14，实战验证轮）**
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
- **v1.5.0-rc1-tA1（2026-10-21，R3 准入门槛首条 · T-A1 / fix #8 LRN-006）**
  - 变更：CLAUDE.md 顶部新增 §1「子代理证据纪律」——主理人采信子代理/成员产出前必须抽查 ≥2 条证据，每条含 `file:行号` + 原文 1-2 行摘录；未通过 = 视为未交付
  - 理由：5 spot-check 2 证伪（LRN-006 根因：子代理常"给行号但不给原文摘录"，等同证据幻觉）；R3 不可一日不立白纸纪律
  - 影响：所有慢通道（真实 spawn）/ 任意子代理产出 → 主理人 VERIFY 阶段抽查成为强制门；T-A2 决策日志触发条件同步生效（其依赖本节作为审计前提）
  - 下一步：T-A2 决策日志首次触发（≥5 行真实条目 + 至少 1 个任务压三类升级路径）；B/C/D 路线图 T-B*/T-C*/T-D* 在本纪律立定后启动
