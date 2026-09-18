# DATA_PATHS — H5Nx 数据资产软指针
> 避免移动大文件 / 跨工作空间漂移；这里只记路径，不复制内容。
> 维护者：archivist；更新触发：路径变更 / 新增数据资产。
> 建档：2026-09-11（首次建立，指针从空骨架接上真实实验台）

## H5Nx 主项目（v3.8c 锁，8+14 图，EMI 投稿中）

### 根路径
```
BASE=/Users/biodog/Library/CloudStorage/OneDrive-Personal/Research/04_H5
```

### 关键路径常量（来自 04_H5/CLAUDE.md v4.4 §C）
```
DATA=$BASE/01_data_clean
GLYC=$BASE/05_Glycosylation
BEAST=$BASE/06_Beast
SUP=$BASE/09_Supplementary
MSTAT=$SUP/M_statistical        # M01-M16 统计模块链
DDRY=$SUP/D_drylab              # D01-D13 结构-功能干实验
SSUP=$SUP/S_supplement          # S01-S07 投稿增补材料
TREE=$BASE/04_Treetime/HA_cd995_align.newick
MANUS=$BASE/paper/current/H5Nx_v5.1_final_EID_ready.docx
PPATCH=$BASE/paper/patches
PAUDIT=$BASE/docs/audits
FIGMAIN=$BASE/Figures/main       # 正文定稿图 Fig1-8（投稿唯一正式出口）
FIGSUPP=$BASE/Figures/supp       # 附图定稿 S01-S14
FIGARC=$BASE/Figures/archive     # 版本归档
CONDA_BIO=/Users/biodog/miniconda3/envs/bio/bin/python
```

### onboarding 必读顺序
1. `$BASE/CLAUDE.md`（项目总控入口，495 行 v4.4）
2. `$BASE/.claude/CLAUDE_GLOBAL_v1.0.md`（通用规则，C1-C9 + 5 源核验 + 双盲 SOP）
3. `$BASE/docs/PROJECT_ASSETS_MAP.md`（单一文档地图）
4. `$BASE/docs/CURRENT_TRUTH.md`（当前真相 + 弃用声明）
5. `$BASE/docs/WRITING_ROADMAP.md` + `REVIEWER_PREP.md` + `DATA_AVAILABILITY.md`（投稿三件套）
6. `$BASE/CLAUDE.md §J`（8 项 P0 状态报告）

### 锚点数字（与 manuscript v3.8c 锁定）
- ANCHOR_N = "n=2,543 curated clade 2.3.4.4 HA dataset (manuscript P36)"
- ANCHOR_STAT = "G70 (mature 54) PGLS β=+2.006, p_bonf=0.0056 (R phyloglm)"
- ANCHOR_GISAID_N = "n=2,763 中国 clade 2.3.4 全集 (Figure 1 数据源)"
- ANCHOR_CD995 = "n=622 cd995 子集 (BEAST/HyPhy 数据源)"

### 投稿硬门槛状态（CLAUDE.md §H.4, Q19 验证）
| # | 项 | 状态 |
|---|----|------|
| 1 | 数字一致性总表 | ✅ |
| 2 | Data availability 段插入 docx | ✅ |
| 3 | **GISAID 致谢表** | ⏳ **需用户登录 GISAID 导出** |
| 4 | docx 图编号统一 v5.1 8+14 | ✅ |
| 5 | GLMM 共线性诊断 VIF | ✅ |
| 6 | G140-Human p=0.022 定位句 | ✅ |
| 7 | 9NRR 撤下 | ✅ |
| 8 | 核验新增 P0 已执行 | ✅ |

**真需用户执行**：仅 #3 GISAID 致谢表。

## 其他战线（H10 / H1N1）
（空——用户未告知数据位置，待补充）

## 跨工作空间纪律
- 本文件只记路径指针；不复制大文件（Git LFS/OneDrive 已承载）
- 路径变更 → archivist 同步更新本文件 + research_anchor.md
- 数据路径漂移检测：每轮主理人任务对齐时核对一次