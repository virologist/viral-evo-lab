# WF5 P0 闭环报告 · cover letter 修复 v1.0
> 2026-09-26 | 触发：红队总矩阵 P0-A~D | 执行：主会话（快通道单人格，参照 WF3 检索核验规范）
> 闭环依据：P0-4 反馈路由（引用/证据不足 → WF3 重检索）

## P0 闭环状态（4/4 全闭）

| P0 | 修复内容 | 核验依据 | 状态 |
|---|---|---|---|
| **P0-A** 审稿人 3/5 幻觉 | 名单重做：Meng-Jie Salvador→**Hui-Ling Yen**（Yang 2025 共同通讯，HKU）/ Hai-Long Sun→**Honglei Sun**（T160A site158 文献一作）/ Shi 2024→**Thomas Peacock**（2024 Nature panzootic 综述一作，Pirbright）/ Vijaykrishna Duan→**Dhanasekaran**（HKU-Pasteur）/ Nguyen→删除（4 人制） | WebSearch 核验：Yang 2025 通讯作者列表 + Peacock DOI 10.1038/s41586-024-08054-z + Sun 一作身份 | ✅ |
| **P0-B** Sun 引用张冠李戴 | 改引 **PMID 29615249**（T160A deglycosylation at site 158 in HA, clade 2.3.4.4 H5NX, dual receptor binding——内容与信中语境 100% 匹配） | PubMed 标题+摘要逐点核对 | ✅ |
| **P0-C** Vrancken 2014 描述错配 | "subtype-structured transmission reconstruction"→"Bayesian genealogical inference constrained by a known HIV-1 subtype C transmission chain"（忠实原文描述，PMID 24699231） | 三个独立源（AGRIS/KU Leuven/figshare）摘要一致核验 | ✅ |
| **P0-D** 奶牛场三跳外推 | 拆两句：框架级 "directly portable to the dairy-cattle 2.3.4.4b population"（合理）+ marker 级 "whether G70–G140 retains discriminant utility there is **untested and listed as Future work**"（诚实） | 红队外推路 #2 修复建议原文采纳 | ✅ |

## 联动措辞修复（红队 P1/P2 中零成本项顺手完成）

1. "collapses from +0.376 to +0.073" → "**is substantially reduced**...residual effects up to +0.21 cannot be excluded at the current mammalian sample size"（假说路#1：不显著≠无效应）
2. "first quantitative case study of clade-founder confounding **in** H5Nx" → "first systematic quantitative demonstration of clade-founder confounding **for an** H5Nx HA glycosylation marker"（外推路#1：三处 first 措辞统一）
3. "rather than a driver–passenger pair" → "a pattern consistent with a marker pair, whose driver–passenger structure (if any) remains an **open competing hypothesis**"（假说路#6：删无判别检验的否定性断言）
4. p=0.022 加标 "**uncorrected exploratory**"（方法路#10 部分）
5. "reusable reporting standard" → "for evaluation as a reporting standard"（外推路#6）
6. "provides a clade-conditional surveillance candidate" → "hypothesis-generating surveillance candidate...pending out-of-sample validation"（外推路#3：纪律对齐）
7. Dadonaite 补期刊名 *PLOS Biol*（引用路#9）
8. 审稿人全员附 "no collaboration within past 5 years" + Yang 2025 数据重叠主动披露（外推路#5）

## 三方量更新（P0 闭环率）

| 指标 | 值 |
|---|---|
| 红队发现 P0 | 4 |
| 已闭环 | **4（100%）** |
| 修复 commit | 04_H5 仓库 `19124c4`（已 push） |

## 未在本轮处理的 P1（需 WF4 重跑，零新数据但需算力时间）

- P1-3 clade 判定循环依赖（NA/内部基因 clade call 重跑 M9_a）——**影响最大，建议下一轮最优先**
- P1-5 LOSO（纯模型重跑）
- P1-1 GLMM 伪重复（phylo RE / cluster RE）
- P1-6 VIF + leave-one-covariate-out
- P1-7 GARD 重组预筛 + aBSREL
- P1-8 分层 D' + PPV 判据预指定

这些全部是**分析层重跑**，不动 cover letter 文本；完成后数字若有变化需同步回 letter 与 manuscript。

## 遗留风险声明

1. 新审稿人名单 4 人中 Yen 与 Dhanasekaran 同属 Yang 2025 作者网络——已在信中主动披露供编辑裁决，但若编辑视为过近可再换（备选：Peacock 组同事、或 Burrough/Caserta 网络的真实学者，需再核验）
2. 04_H5/CLAUDE.md §H.4 Q19"Cover Letter 已完整 v5.1"结论随红队发现**作废**，本报告为新的权威状态；建议下次进 04_H5 会话时同步更新其 CLAUDE.md
3. Louisiana 致死病例归组（引用路#1，中风险）：已把 CDC 2025b 提到疫情报告组首位，但"1 fatal case"的精确出处仍需投稿前对照 CDC 当日页面人工确认
