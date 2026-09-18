# 方法示例库（项目级）
> **⚠️ 真源已迁移至 `method_library.json`（Anthropic feature_list.json 模式，P0-1 2026-09-18 落盘）。本 .md 是人类可读视图。**
> **权威定义**：skills/viral-evo-core/references/frontier-2025-2026.md
> **本文件**：项目级核心管线快照 + 迁移记录；前沿锚点以权威定义为准。
> 更新：2026-09-10（建档）

## 项目级核心管线（已验证默认配置）
```
序列检索（NCBI/GISAID）→ MAFFT 比对（--auto ≤1000seq / --thread >1000；蛋白序列 MUSCLE5）
→ IQ-TREE 3.x（MFP 自动模型选择）ML 树 → HyPhy FUBAR 选择压
→ PAML M7/M8 交叉确认 → AlphaFold3 结构验证（批量用 ESMFold）
```
- 时间树：BEAST2（精度）/ TreeTime（探索）；分歧时间配 Tracer 诊断
- 可视化：ggtree+ggplot2（发表级）/ FigTree（探索级）
- 流程化：样本 >20 自动建议 Snakemake 模块化
- 8 基因节段分别建树，目录 03_ML_tree/

## 迁移记录
（空——每次方法迁移成功后按三步模板追加：原方法→适配差异→参数调整依据）