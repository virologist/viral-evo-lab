# WF1 假说生成·实测报告（unified）
> 日期：2026-09-30 | 任务：基于 H5Nx clade 2.3.4.4 G70(m54)/G140(m124) 的演化机制生成可证伪假说
> 执行：慢通道 3 员真实 spawn（wf1-scout / wf1-hypothesis / wf1-predictive）
> 执行方式标注：3 员报告均已独立产出（**完整内容见证据简报/假说卡 v1.2/升维评估报告**），本 unified 仅汇编关键决策与落地清单

## 一、任务路由（trace）

```
07:39 wf1-scout spawned       [证据锚定/Phase 1]
07:39 wf1-hypothesis spawned  [分层假说/Phase 2]
07:39 wf1-predictive spawned  [DMS 升维/Phase 3]
07:49 wf1-predictive 报告回传
07:54 wf1-hypothesis v1 报告回传
07:55 wf1-hypothesis v1.1 自组织修订（回查 scout 证据，机制叙事重定位）
07:56 wf1-hypothesis v1.2 自组织修订（采用 DMS 不测糖基化的边界声明）
07:58 wf1-scout 报告回传
07:59 wf1-scout 追加核验（核验假说官 D′ 分层判据是否成立；推翻机理表述+给出 r² 替代）
```

## 二、产出汇总（已记入 ledger 5 条）

| 员 | 产出 | 关键发现 |
|---|---|---|
| scout | 证据简报（8+4+5 条） | G140 位于抗原位点 A 区，宿主嗜性开关在 RBS 经典位点（不在 140/70）；G70 无位点级文献 |
| hypothesis | 假说卡 v1.2（5 条） | H-S1 标记属性 高 / 机制侧 抗原选择（不再是 mammalian marker）；H-B1 判据阈值已预注册 |
| predictive | DMS 升维评估（14 条候选突变） | H5 DMS 图谱已存在（Dadonaite 2024），不测糖基化；G70/G140 sequon 后验提取为唯一原创方向 |
| scout 追加 | D′ 退化红线 + r² 替代 + 谱系分布判据 | 同 D'=0.944 对应 r² 0.012~0.513（PMID 18572214）；clade 内相关→第三候选解释（PMID 20525617） |

## 三、跨员共识点

1. **机制叙事必须从“哺乳动物适应”重定位为“抗原位点 A 免疫/抗原选择候选”**（三员独立收敛，依据：scout E1/O2/O3/O4 + hypothesis v1.1 + predictive 边界声明）
2. **DMS 已存在不应建议做新 DMS**（predictive v1.2 + hypothesis v1.2 全员对齐；正确姿势是“索引+二次挖掘”）
3. **编号映射未解前挂 P0 阻塞**（hypothesis v1.2 + main sequon 核验解除：G140=N124-H125-T126 / G70=N54-C55-S56 均自洽，不依赖 H3↔H5 映射）
4. **D′ 在近乎单态位点退化**（scout 第二次回传 + M17_V1b 校正结果共同指向同一红线）

## 四、跨员冲突点（待裁决）

| # | 冲突 | 来源 | 待决方 |
|---|---|---|---|
| C1 | **D′ 三值口径**（0.9681 / 0.9441 / 0.8958）投稿稿应锁哪个？ | scout 推荐“统一改报 r² + CI，D′ 进 SI” | **TZUVet**（涉及投稿稿数字呈现） |
| C2 | **是否插入谱系分布检验到本轮排期**（唯一能判决 founder vs 功能耦合） | scout vs hypothesis 均提，但 V2 树未跑 | **TZUVet**（算力/时间预算） |
| C3 | **Mammal 三源不一致是否需要回头修订 v5.1/v7.0 投稿稿**（V1b -0.032 vs M9_a +0.073 vs 论文 CSV +0.065） | hypothesis H-09 | **TZUVet**（影响投稿稿一致性） |

## 五、可立即执行的低算力下一步（不依赖 429 重置）

1. **中国 4h 哨兵位点状态查询**（predictive 推荐 #2，零成本）：
   - Q226L/R、E190Q/A、N224K/Y、G228A（受体）
   - R81G（稳定性）
   - R90K、P128S、E255K（逃逸）
   - 工具：纯 DataFrame 操作，n=2475/639，≤ 半天
2. **sequon 后验提取启动脚本**（predictive 推荐 #3）：
   - 用 DMS 参考序列定位 G70/G140 sequon 三元组
   - 从 10,773 突变矩阵抽出“破坏该 sequon 的所有单点突变”
   - 读 cell entry / stability / escape 三项效应
   - 依赖：DMS 原始数据（确认可访问性后启动）

## 六、诚实声明

- **本报告是三员报告的汇编索引，不是原创内容**——三员独立产出见各自完整文档（已归档到 RESEARCH 上下文）
- **未做的事**：跑通三个真实产出对应的物理结果（4h 哨兵位点查询、sequon 后验、V2 建树）—— 算力依赖型工作留给服务器与频率重置后
- **诚实标注**：本次三员**真实运行了**（证据/结论与频率重置前完成的报告一致），不是单人格代写。但统一综合由主会话完成（快通道），签名如实标注

## 七、回填 ledger

- H-09（fatal, open）：Mammal 三源不一致
- M-12（major, open）：D′ 退化 + r² 替代
- M-13（major, open）：第三候选解释（PMID 20525617）
- N-01（fatal, closed）：编号碰撞 P0（sequon 解除）
- N-02（minor, closed）：比对列索引≠残基编号

## 八、收尾状态

- 5 条 findings 已入 ledger（43/43 总数）
- P0 闭环率：fatal/severe/high = 9/16 = **56%**
- 全量闭环率：21/43 = **49%**
- 落盘：04_H5 main `3c2ffe6`（V2/V3 设计）+ `01cb45f`（sequon/D′）+ research-ops-track `b0a0e3d`
- 频率限制：3 subagent 429（08:00 重置）；本报告及全部产出在限流前完成