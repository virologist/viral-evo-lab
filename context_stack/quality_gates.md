# 质量门控配置（项目级快照）
> **权威定义**：skills/viral-evo-core/references/quality-gates.md
> **本文件**：项目级定制/补充快照；如空则沿用权威定义。
> **同步规则**：团队成员一律以 skills/viral-evo-core 内文件为准；本文件仅记录差异。
> 更新：2026-09-26（R1/R2/R4 三门随 v2.0 诊断落地，权威源已更新，此处登记差异）

## 项目级定制

### 复现校准门（R4）——当前活跃用例
- 适用：M17_clade_independence（进行中）
- 预指定阈值：V1 复现 Mammal ΔP 与论文锁定 `+0.073` 差异 **<0.005**；n 达 **2475**；freq_4h(G140) 与 **0.917** 差异 <0.01
- 校准依据：`M09_glyco_host_association/M9_glyco_host_association.ipynb` 数据准备段
- 状态：**未通过**（实测 freq_4h=0.9697、G70=0.2914 → 过滤口径待对齐）→ M17 §3 之后的建树步骤被此门拦截

### 红队台账门（R2）
- 台账路径：`00_governance/redteam_ledger.csv`；工具：`00_governance/redteam_tools.py`
- 当前基线（2026-09-26 首跑回填）：37 findings，全量闭环率 51%，P0 级闭环率 62%
- 待办：H-04（clade 循环依赖）状态 partial——M17 模块已建，校准+跑通后回填 closed

### 完整性巡检门（R1）
- 命令：`python3 00_governance/redteam_tools.py check`（manifest 基线 2026-09-26T20:54，33 文件）
- 已拦截实战：settings.json 二次缺失（20:55 git checkout 恢复）——外部进程会反复删它，每次慢通道前必查