# CLAUDE.md — 病毒演化研究院团队级运行指南
> 与 README 区分：README = 团队介绍与安装；本文件 = 团队运行机制与上下文接力协议
> 维护者：archivist（史治文）；更新触发：每轮结构变更后
> **Changelog 规范（Anthropic claude-progress.txt 模式）**：每次结构变更追加一条，必含"变更/理由/影响/下一步"四字段；禁止改写历史

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
