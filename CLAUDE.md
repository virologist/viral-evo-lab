# CLAUDE.md — 项目级 AI 助手交接文档
> 最后更新：2026-09-18 by P0-2 优化任务（v0.3）
> 维护者：archivist（史治文）
> 触发更新：每 WF 完成 + 每轮任务结束有变更时增量更新
> **Changelog 规范（Anthropic claude-progress.txt 模式）**：每 session 追加一条，必含"完成/发现修复/下一步/决策"四字段；禁止整段重写历史

## 项目快照
- **病毒/对象**：H5Nx clade 2.3.4.4（主线，G70/G140 协同标记对 + clade-founder confounding 方法学贡献）+ H10 禽流感（重构，10 主图+7 附图）+ H1N1/H3N8 猪流感（PB2-M631L/PA-T97I）
- **数据规模**：H5Nx 2543 条 HA + 2365 条 NA 中国序列（GISAID 2019-2023）；cd995 子集 640 HA + 582 NA
- **核心叙事（v5.1 重定位）**：clade-host confounding 量化案例为核心方法学贡献；G140 = 4h clade 定义性糖基化标记；无湿实验，纯干实验
- **当前阶段**：H5Nx v7.0 终稿已存在（v5.1 是过程稿）；EMI 投稿三件套就绪；**唯一 P0 = GISAID 致谢表（用户行为）**；H10 稿件重构；H1N1 投稿准备
- **下一动作**：GISAID 致谢表导出（用户）→ 清 8 项 P0 全 ✅ → 投稿
- **关键约束**：无实验室 / 无研究生 / 经费极紧 / 干实验优先 / 算力 Ubuntu24 (A5000 24G)

## 活跃战线与状态
- H5Nx：[v7.0 终稿 + EMI 投稿三件套就绪] / 目标 EMI (Original Article)，VE 备
- H10：[稿件重构 10+7 图] / 目标 CAS 1区 virology / 锚点待补
- H1N1：[投稿准备] / 致病性证据链汇总 / 锚点待补

**详细锚点（真源）** → `context_stack/research_anchor.json`（.md 是渲染视图）

## 已确认假说（活跃）
- H-ANCHOR-1（高置信）：G70/G140 构成 4h clade 平级协同标记对（D'=+0.94 共变）；G140 是 4h clade 定义性糖基化标记（clade_delta=-0.916, freq_4h=91.7%）；crude mammalian association 已被 M9_a GLMM Gate-1 证伪为 clade confounding

**完整列表（真源）** → `context_stack/confirmed_hypotheses.json`（.md 是渲染视图）

## 方法栈（活跃管线 + 备选）
- **管线 A（生产）**：序列检索(NCBI/GISAID) → MAFFT → IQ-TREE 3.x (MFP) ML 树 → HyPhy FUBAR + PAML M7M8 → AlphaFold3
- **时间树**：BEAST2 + CoalRe（重配）/ TreeTime（探索）
- **可视化**：ggtree + ggplot2（发表级）/ FigTree（探索级）
- **前沿增量**：DMS 适应度景观（Bloom 组 Nat Ecol Evol 2025）/ 蛋白 LM 抗原预测（Sci Rep 2025）

**详细定义（真源）** → `context_stack/method_library.json`；前沿权威 → `skills/viral-evo-core/references/frontier-2025-2026.md`

## 已完成分析 & 关键发现
- M1-M16 统计模块链 16/16 ✅（在 04_H5/09_Supplementary/M_statistical/，CSV 落盘）
- 关键发现：M6 共演化 D' / M9_a GLMM Gate-1 / M16 HA-NA 协同 / M8 codon 211/530 正选择

## 待办（按优先级）
1. **P0**：GISAID 致谢表导出（用户操作 30min，清 8 项 P0 全 ✅）
2. **P1**：H10 数据路径补 DATA_PATHS.md（用户告知后 archivist 补）
3. **P1**：H1N1 数据路径补 DATA_PATHS.md（同上）
4. **P2**：CoalRe 适配评估（WF7 迁移卡，视方案 B 启动与否）

## 接手建议（给下一个 AI）
- **不要先做**：不要在没有 WF6 勘探/诊断前直接动数据；H5Nx 数据规模大，重跑管道代价高
- **优先做**：
  1. 先读本文件（项目快照）→ `context_stack/` 三 JSON 真源 + 三 .md 视图理解战线全貌
  2. **H5x 实际资产在 `DATA_PATHS.md` 指向的 04_H5/ 项目**（不是本工作空间）；按 04_H5/CLAUDE.md §M 七步 onboarding 流程接力
  3. 必须读 `04_H5/CLAUDE.md` v4.4（495 行）+ `04_H5/docs/PROJECT_ASSETS_MAP.md` + `04_H5/docs/CURRENT_TRUTH.md`
- **慎用**：BEAST2 全长跑（接受过夜但不接受重跑）；AlphaFold3 全蛋白预测（算力吃紧）
- **必走流程**：任何重计算 → WF6 勘探/诊断 → WF4 任务对齐 + ACK → 人工审核执行
- **质量门控**：ML 树 UFBoot≥95 + SH-aLRT≥80；时间树 ESS≥200；正选择 FDR<0.05 双方法显著
- **H5x 投稿硬门槛（04_H5/CLAUDE.md §H.4 Q19 验证）**：7/8 已 ✅，**唯一 P0=GISAID 致谢表**
- **陈旧叙事红线**：user memory / auto-injected memory 中的"糖基化预适应 enabling 框架 A"已被 v5.1 撤下，**以 04_H5/CLAUDE.md 真本为准**

## Changelog
<!-- 规范：每 session 追加一条，禁止删除/改写历史条目；格式含四字段 -->
- **v0.4（2026-09-18，P0-3~P1-6 任务）**
  - 完成：stable prefix 速查卡 11/11 覆盖；Evaluator 反馈路由（审查结论→修复路由）；动态资源分配表（7 WF 粒度+降级规则）；context-compaction 协议上线
  - 发现修复：P0-3 首轮脚本漏了 archivist 速查卡（覆盖 10/11），已补齐并复验 11/11；team-lead MD 的 old_string 锚点因 WF6/WF7 段落位置误判失败一次，改用精确锚点重试成功
  - 下一步：实测验证（路由准确率 / token 消耗 / P0 闭环率 三方量）
  - 决策：maxTurns 因平台字段静态，改用「任务粒度控制」实现等效动态分配；简单查询强制降级直调（防 50 子智能体失败模式）
- **v0.3（2026-09-18，P0-2 任务）**
  - 完成：CLAUDE.md Changelog 规范化（Anthropic claude-progress.txt 模式）+ 修正顶部快照陈旧漂移
  - 发现修复：项目快照仍含 v0.1 陈旧叙事（"Site 140 预适应框架 A"/"H-ANCHOR-1 中置信"）——v0.2 只改了底部历史没改顶部，文档漂移活案例；本次按 v5.1 真本全量修正
  - 下一步：P0-3 stable prefix 重排（11 agent MD 顶部前置角色+能力+输出规范）
  - 决策：Changelog 四字段（完成/发现修复/下一步/决策）强制；快照段与 context_stack JSON 真源对齐（指向 .json 而非 .md）
- **v0.2（2026-09-11，WF6 实战）**
  - 完成：对接 04_H5/ 项目真本；DATA_PATHS.md 新建；research_anchor/confirmed_hypotheses 按 v5.1 重定位
  - 发现修复：user memory 陈旧锚点污染 CONTEXT_STACK（"叙事框架 A"是 v3.8 之前化石）；H-ANCHOR-1 从占位符重写为 v5.1 实际假说
  - 下一步：GISAID 致谢表 / H10·H1N1 路径补全
  - 决策：接手项目第一动作必须读项目真本 CLAUDE.md 并与 user memory 比对，不一致以真本为准
- **v0.1（2026-09-10，建档）**
  - 完成：初始战线锚点建档（基于 user memory 旧信息——后被证明部分陈旧）
  - 发现修复：无
  - 下一步：首个实战任务锚定
  - 决策：六层目录协议 + CONTEXT_STACK 五文件结构
