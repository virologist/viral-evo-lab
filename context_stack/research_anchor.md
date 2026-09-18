# 研究对象锚点（Research Anchors）
> **⚠️ 真源已迁移至 `research_anchor.json`（Anthropic feature_list.json 模式，P0-1 2026-09-18 落盘）。本 .md 是人类可读视图。**
> 主理人每轮任务前自动检索本文件，相关条目前缀注入；战线变化时立即覆盖写入。
> 数据资产指针见 `../DATA_PATHS.md`（不重复路径常量）。
> 更新：2026-09-11（H5 锚点从 v5.1 实际内容回填，不再是占位符）

## 活跃战线

| 战线 | 病毒/对象 | 关键基因/蛋白 | 宿主与区域 | 当前阶段 | 目标 | 锚点详情 |
|---|---|---|---|---|---|---|
| **H5Nx 主线** | H5Nx clade 2.3.4.4 | HA（G70/G140/G170 糖基化）+ NA（N1/N6/N8） | 中国，野生鸟-家禽-哺乳动物界面 | **v7.0 终稿已存在；v5.1 是过程稿；EMI 投稿三件套就绪；唯一 P0=GISAID 致谢表** | EMI（Original Article）| 见下方 §H5Nx-详细 |
| H10 重构 | H10 禽流感 | 全基因组（10 主图+7 附图） | 中国 | 稿件重构 | CAS 1区 virology | 待补 |
| H1N1 猪流感 | H1N1 / H3N8 | PB2-M631L / PA-T97I | 猪-人界面 | 投稿准备 | 致病性证据链汇总 | 待补 |

## §H5Nx-详细（基于 v5.1 真本回填，2026-09-11）

### 核心假说（v5.1 重定位，2026-07-30 Gate-1 验证后）
**G70 (mature 54) 与 G140 (mature 124) 构成 4h clade 平级协同标记对**（D'=+0.94 共变），通过独立获得 + 遗传连锁共演化塑造 4h 谱系糖基化景观；**G140 是 4h clade 的定义性糖基化标记**（clade_delta=-0.916, freq_4h=91.7%），其 crude mammalian association（taxon_delta=+0.376）已被 M9_a GLMM Gate-1 验证证伪（控制 Clade 后 Mammal ΔP=+0.073, p=0.308）——clade-host confounding 量化案例本身是核心方法学贡献。

### 已弃用结论（不可再引用，见 04_H5/CLAUDE.md §E.5）
- "S140 是唯一显著宿主关联位点" → 被 G70 取代
- "sequon 三联体差异化选择" → alignment 验证证伪（v3.6.1）
- "G70 是 4b 单次预适应" → 修正为多重 gain+漂变
- v3.8c/v5.0 旧 "G140 双锁定/最强 mammalian marker" 叙事 → v5.1 已撤
- "codon 140 = G140" 直接等号 → 2026-08-12 证伪（G140 mature 124 = m8_col 125）

### 数据规模与设计
- GISAID 2019–2023 中国 H5Nx：2543 HA + 2365 NA；cd995 子集：640 HA + 582 NA
- 两层样本设计：M1 用 Data_clean 中国子集 (2475)；M2-M9 用 HA-re 精选 (639/622)
- D' 数据集：n=2,476（NetNGlyc 过滤后）或 n=2,497（过滤前）——投稿稿双报

### 投稿硬门槛（8 项 P0，§H.4 Q19 验证）
- 7/8 已完成 ✅（含 docx 图编号统一 v5.1 8+14、GLMM VIF、共线性诊断、Human p=0.022 定位句）
- **唯一未完成 ⏳：GISAID 致谢表**（需用户登录 GISAID 导出 accession ID 列表，AI 无法绕过）

### 稿件版本演进
- v3.8c（锚定数字版）+ v5.1（过程修订版）+ v6.0/v7.0（终稿，已有中英双版）
- 稿件真本 = `$BASE/paper/current/H5Nx_v5.1_final_EID_ready.docx`
- 靶期刊：EMI 主（cover_letter_EID.md）/ VE 备

### M1-M16 统计模块链（09_Supplementary/M_statistical/）
- 16 模块全部 ✅ 状态，CSV 落盘可引用
- 关键发现：M6 共演化 / M9_a GLMM Gate-1 / M16 HA-NA 协同 / M8 codon 211/530 正选择

### 数据资产指针
**完整路径常量见 `../DATA_PATHS.md`**（BASE/DATA/GLYC/BEAST/SUP/MSTAT/MANUS/FIGMAIN/FIGSUPP/FIGARC/CONDA_BIO 等）

## 数据资产（通用）
- H5Nx：2543 条 HA + 2365 条 NA 中国序列（2021 截止）
- 8 基因节段 ML 树（HA,NA,PB2,PB1,PA,NP,M,NS）位于 `$BASE/03_ML_tree/`
- BEAST 分析资产：`$BASE/06_Beast/H5Nx_HA_cd995_jump-reward.xml` + `_com.tree`（MCC）
- Figures 三层：`$BASE/Figures/main/` (Fig1-8) + `supp/` (S01-S14) + `archive/`

## 环境锚点
- 算力：Ubuntu 24 服务器（24 核 / 126G / A5000 24G）+ Mac M1 Pro + ThinkPad P51
- 本机 conda：`/Users/biodog/miniconda3/envs/bio/bin/python`
- 约束：无实验室、无研究生、经费极紧 → 纯生信干实验，轻实验优先