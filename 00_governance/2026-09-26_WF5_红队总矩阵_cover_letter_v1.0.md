# H5Nx Cover Letter（EID→EMI v5.1）· WF5 红队总矩阵
> 日期：2026-09-26 | 执行方式：**慢通道首跑——真实 spawn 4 攻击员并行**（团队史上首次真实多 agent 运行）
> 攻击员：redteam-hypothesis（贾思远规范）/ redteam-citation（文溯源规范）/ redteam-method（舒建树规范）/ redteam-extrap（喻高瞻规范）
> 攻击对象：`04_H5/paper/cover_letter_EID.md`
> 本报告由主会话汇编（真实 spawn 数=4，回传完整率=4/4）

---

## 〇、运行基线（三方量指标首次实测）

| 指标 | 本次实测 | 备注 |
|---|---|---|
| 真实 spawn 数 | 4（并行） | 团队 16 天来首次真实组队 |
| 回传完整率 | 4/4（100%） | 全部按模板字段交付 |
| 攻击总条数 | 38（假说8 + 引用14 + 方法10 + 外推6） | 单人格模拟时代从未达到的覆盖密度 |
| P0 闭环率 | 待修复后复验 | 本报告即 P0 闭环起点 |
| 运行时长 | 最长一路 5m49s，其余并行完成 | 并行收益实测有效 |

**与单人格代写的质量对比（定性）**：方法路的 GLMM 伪重复攻击、假说路的 clade 判定循环依赖攻击——两个最锋利单点在之前所有"模拟红队"输出中均未出现。多视角真并行的价值有实据。

---

## 一、致命发现汇总（P0——学术诚信级，投稿前必须修复）

### P0-A【最高优先】审稿人名单 3/5 幻觉人名 + 1 幻觉文献（引用路 #7/#10/#11/#12）
- "Meng-Jie Salvador"：Yang 2025 作者列表无此人（通讯=Jie Wu / Hui-Ling Yen / Vijaykrishna Dhanasekaran）
- "Shi 2024 Nature 哺乳适应综述"：不存在；实为 Peacock et al. 2024（DOI 10.1038/s41586-024-08054-z）
- "Vijaykrishna Duan"：拼接式幻觉，真名 Vijaykrishna Dhanasekaran（且是 Yang 2025 共同作者→COI）
- "Thao-Quyen Nguyen"：Burrough/Caserta 作者列表均无任何 Nguyen
- **处置**：审稿人名单重做（真实学者+COI声明）；这是"直接投出即学术诚信事故"级

### P0-B Sun 2022 PNAS Nexus 内容张冠李戴（引用路 #8 + 外推路 #1/#5 联动）
- 论文真实（DOI 10.1093/pnasnexus/pgac085）但内容是 HA Δ131→site 129 糖基化，**不是 Site 158/T160A**；第一作者 Honglei Sun 非 Hai-Long Sun
- **连锁杀伤**：Site 158 "98.7% 固定"叙事的唯一支撑引用是错的；且 Sun 恰是"first"声明最可能否定者
- **处置**：换真实 T160A 文献（候选 PMID 33436086，需人工核验后替换）

### P0-C Vrancken 2014 描述错配（引用路 #5）
- 原文=HIV-1 C 亚型 within/between-host 速率研究；信中称"subtype-structured transmission reconstruction"——**诚实声明 #1 里的引用不诚实**，风险加倍
- **处置**：替换或改写描述（疑与 Faria 2014 Science Kinshasa 研究混淆，需人工确认）

### P0-D 奶牛场监测工具三跳外推（外推路 #2，严重级）
- P2 末句是全文唯一越过标题数据范围的句子：中国→北美 × 2019-23→2024-26 × 4h 标记对→纯 4b 牛群（4h 对在 4b 群预期近单态，零数据检验）
- **处置**：降级为框架级声明，marker 级适用列入 Future work

---

## 二、重要发现汇总（P1——统计与逻辑，大修必答）

| # | 来源 | 问题 | 一句话修复方向 |
|---|---|---|---|
| P1-1 | 方法#1+假说#3 | M9_a GLMM 伪重复：2,475 序列当独立观测，无系统发育/暴发簇 RE；77 哺乳类有效样本可能 <20 独立溢出事件 | phylo RE 或 cluster RE + robust SE + 功效敏感性 |
| P1-2 | 假说#1+#2 | 把 p=0.308 当"证伪"（absence of evidence）；且 Human p=0.022 显著与"塌缩"叙事自相矛盾 | TOST 等效检验 + 预指定判读规则 + p=0.022 标 exploratory |
| P1-3 | 假说#4 | **clade 判定与 G140 循环依赖**：clade call 来自 HA 树，G140 是 HA 位点参与建树→条件化是构造性必然 | 用 NA/内部基因定义 clade 重跑（零新数据） |
| P1-4 | 方法#6+假说#6 | M16 配对信号未做 clade-conditional 检验（与自身论点不自洽）；"非 driver-passenger"否定性断言无判别检验 | clade 内置换 + 删否定性断言或给区分性证据 |
| P1-5 | 假说#8 | LOSO 被推迟到 future work——纯重跑零新数据的最廉价证伪检验刻意不做 | 投稿前完成 LOSO 进 SI |
| P1-6 | 方法#3+#4 | Clade↔Subtype↔Phase↔Year 共线性无 VIF 报告；Province 单截距 RE 可能过度吸收宿主信号 | 报 VIF + leave-one-covariate-out + over-adjustment 对照 |
| P1-7 | 方法#8 | FUBAR 前提违反（无重组预筛 GARD）+ BF 表述 + 编号映射链不透明 | 先跑 GARD + aBSREL 验证 4h 特异 + 三列对照表 |
| P1-8 | 方法#5+假说#7 | D' ascertainment bias（n_joint=108 条件于多态）+ "defining marker" 无预指定判据 | clade 内分层 D' + 预指定 PPV/Youden 阈值 |
| P1-9 | 外推#1 | "first" 三处措辞不一致（现象级/方法级/监测级） | 统一单一规范措辞 + 与 Sun 2022 显式划界 |
| P1-10 | 方法#9 | 结构外推：0.6Å 未说明度量层级；全局 pLDDT≠位点局部；糖链未建模 | 限定 backbone 级 + 报位点 pLDDT + 注明糖链缺失 |
| P1-11 | 方法#10 | 多重检验校正总账不全（仅 M16 报 q_FDR） | 全研究检验家族清单 + 统一校正策略 |

## 三、次要发现（P2——措辞与格式，修改即可）

- 引用#1：致死病例（Louisiana D1.1）引文归组错位，仅 CDC 2025b 可能覆盖
- 引用#4：Wymant 2022 作"clade-conditional 先例"属引申解读，措辞收紧
- 引用#9：Dadonaite 2024 补期刊名 *PLOS Biol*
- 引用#14："CDC 2025b"的 b 后缀无对应 2025a，内部编号不一致；投稿前对照 CDC/USDA 当日数据
- 方法#7：Gate-2 置换方案（全局 vs clade 内）未说明，与 P1-4 联动
- 外推#3：G70-G140 未享受与 Human 信号同等的 "hypothesis-generating" 纪律
- 外推#5：全部审稿人需附 5 年无合作声明（与 P0-A 重做时一并解决）
- 外推#6：单一案例→"全 RNA 病毒报告标准"降格为 framework candidate
- 外推附注：n_avian 2,399 + n_mammal 77 = 2,476 vs M9_a n=2,475 差 1，核对分母口径

---

## 四、按 P0-4 反馈路由的分派表

| 缺陷 | 类型 | 路由 | 成本 |
|---|---|---|---|
| P0-A/B/C 幻觉引用与人名 | 引用/证据不足 | **WF3 重检索**（PMID 逐条人工核验）+ 审稿人名单重做 | 低（纯检索） |
| P0-D 外推越界 | 措辞 | 主会话直接改写 cover letter | 低 |
| P1-3 clade 循环依赖 | 方法设计错误 | **WF4 重跑**（NA/内部基因 clade call，零新数据） | 中 |
| P1-5 LOSO | 数据分析 | **WF4 重跑**（纯模型重跑） | 低 |
| P1-1/2/6/8 统计补救 | 方法 | WF4 重跑（PGLMM/VIF/TOST/分层 D'） | 中-高 |
| P1-7 GARD+aBSREL | 方法 | WF4 补跑 | 低 |
| P1-9/10/11 + 全部 P2 | 措辞/格式 | 主会话改写 | 低 |

**全局判断**：假说路总结论=「不能过审，但全部 8 条修复无需新数据，一轮大修可挽救」；引用路=「真实文献底座+局部幻觉点缀，修复面可控」；**本 cover letter 不可在当前状态投出**，但修复路径全部清晰且大部分零新数据。

---

## 五、本次运行的结构性沉淀

1. **双轨制首跑验证成功**：慢通道（真实 spawn）产出的攻击密度与单点锋利度显著优于此前全部单人格模拟输出——多 agent 火力集中在对抗性场景的决策被实测支持
2. **跨攻击员信息流转生效**：外推路发现的"Vijaykrishna Duan"姓名线索经主会话中转给引用路合并核验，确认为幻觉人名——中转铁律在实战中有效
3. **署名纪律**：本报告如实标注执行方式（真实 spawn 4 员 + 主会话汇编），无虚构署名
