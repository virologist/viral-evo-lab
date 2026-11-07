# 病毒演化研究院（viral-evo-lab）

病毒遗传进化研究 Team 型专家团：前沿检索、方法迁移、假说生成与演化预测，指导生信分析，驱动高水平论文产出。

## 类型
Team 型（多角色协作团队，主理人调度 9 名专业团员）

## 团队阵容

| 成员 ID | 花名 | 职责 |
|---|---|---|
| viral-evo-lab-team-lead | 路问渠 | 主理人：任务路由/苏格拉底追问/质量门控/CONTEXT_STACK |
| hypothesis-officer | 贾思远 | 假说引擎（β核心）：分层假说/可证伪设计/排序 |
| phylo-analyst | 舒建树 | 系统发育：IQ-TREE/BEAST2+CoalRe/TreeTime |
| popgen-modeler | 权衍生 | 群体遗传：FUBAR/PAML M7M8/重组/Ne 动态 |
| predictive-virologist | 喻高瞻 | 升维节点：DMS 景观/蛋白 LM 抗原预测 |
| structural-virologist | 付尔德 | 结构：AlphaFold3/Foldseek/糖基化解读 |
| literature-scout | 文溯源 | 文献（γ核心）：4R 检索/PMID 核验/方法迁移/跨域迁移坍缩态 |
| pipeline-engineer | 柯力行 | 工程：可复现 Jupyter/质控/Debug |
| research-diagnostician | 裴慎思 | 研究诊断官：勘探审计/方法学诊断/纪律审判（discipline-sentinel） |
| archivist | 史治文 | 档案：research-ops 治理/CONTEXT_STACK/论文素材 |

## 标准工作流（7 条预设 Workflow）
- WF1 假说生成与验证（假说/机制/为什么/预测）
- WF2 方法迁移与硅基复现（附件/借鉴/参考某方法）
- WF3 前沿追踪（最新/前沿/数据库版本）
- WF4 分析执行（序列/代码/pipeline/数据）
- WF5 投稿前红队审查（审查/critique/投稿前）
- WF6 研究勘探与诊断（勘探/诊断/审视/审计/改进方案）
- WF7 跨域方法迁移（借鉴医学/HIV·SARS-CoV-2·流感经验/方法学类比）

## 文档系统（research-ops）
团队依赖工作空间内 `research-ops/` 六层目录（00_governance / 10_hypotheses / 20_methods / 30_results / 40_manuscript_assets / context_stack）。
**注意**：CONTEXT_STACK 锚点数据（H5Nx/H10/H1N1 战线）是项目级状态，**不随专家包跨工作空间迁移**；换工作空间时由 archivist 自动重建空结构，需手动复制旧 `context_stack/` 全部文件（现行 = 4 JSON 真源 + 4 .md 渲染 + 3 协议 .md）以延续锚点。

## 使用示例
- 基于这组病毒序列的变异模式，生成可证伪的演化假说并给出验证路径
- 检索目标方法的国际前沿并评估迁移到我当前禽流感数据集的可行性
- 审查我的系统发育分析流程，指出方法缺陷并给出改进方案

## 头像
自动生成于 `avatars/`（512×512，≤500KB）。可手动替换（PNG/JPG，512×512，≤500KB，同风格 cyan-teal）。

## 安装
将本目录放到专家目录：
```
~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/
```
然后通过专家中心「我的专家」确认可见（B1 2026-11-07 订正：原引用的
`scripts/register_expert.py` 不在本包——注册走平台专家管理器或
expert-manager skill 的 register_expert.py，见其 SKILL.md §一·第六步）。

## 打包分享
```bash
zip -r viral-evo-lab.zip viral-evo-lab/
```
