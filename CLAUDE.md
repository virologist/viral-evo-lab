# CLAUDE.md — 病毒演化研究院团队级运行指南
> 与 README 区分：README = 团队介绍与安装；本文件 = 团队运行机制与上下文接力协议
> 维护者：archivist（史治文）；更新触发：每轮结构变更后

## 角色映射（11 角色）

| ID | 花名 | 触发场景关键词 |
|---|---|---|
| viral-evo-lab-team-lead | 路问渠 | 任何病毒遗传进化/系统发育/分子演化研究请求 |
| hypothesis-officer | 贾思远 | 假说/机制/为什么/创新/演化驱动/预测 |
| phylo-analyst | 舒建树 | 建树/时间树/重配/分子钟 |
| popgen-modeler | 权衍生 | dN/dS/选择压/重组/Ne 动态/群体动态 |
| predictive-virologist | 喻高瞻 | 免疫逃逸/突变适应/变异风险预测/疫苗靶点 |
| structural-virologist | 付尔德 | 蛋白结构/突变功能/糖基化/表位 |
| literature-scout | 文溯源 | 文献检索/前沿/方法借鉴/引用核验 |
| pipeline-engineer | 柯力行 | 代码/pipeline/质控/报错/Debug |
| research-diagnostician | 裴慎思 | 审视/诊断/审计/方案改进/合理性 |
| medical-vet-bridge | 柳通人 | 跨域方法借鉴/医学流感经验/类比 |
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
1. **接收方第一步**：读 `research-ops/CLAUDE.md`（项目快照/战线/方法栈/待办/接手建议）
2. **接收方第二步**：按相关度读 `context_stack/` 六文件
3. **接收方第三步**：执行用户原任务；落盘回 archivist 接力
4. **handoff 失败处理**：若发现链路有断层，立即回主理人由主理人调度修复

## 全局重试预算
≤5 次（追问/4R 重入/Gödel 重入/成员返工共享）

## 高危操作
删除/批量覆写/不可逆 → 红色警告 + 二次确认

## 权威源唯一性
- 阈值/前沿/检索源 → `skills/viral-evo-core/references/` 权威
- 项目级快照/锚点/确认假说 → `research-ops/context_stack/` 权威
- 工作流触发表/角色映射 → 本文件权威
