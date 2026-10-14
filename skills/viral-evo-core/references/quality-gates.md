---
last_updated: 2026-10-14
---

# 质量门控阈值表（默认配置）
> **单一事实源**：任务中生效的阈值以工作空间 `research-ops/context_stack/quality_gates.md` 为准（用户可在任务对齐阶段调整）。本表是跨项目默认回退值，二者数值冲突时以 context_stack 版为权威。

| 门控项 | 阈值 | 诊断方法 | 未通过处置 |
|---|---|---|---|
| 时间树 | ESS≥200 | Tracer 全参数检查 | 延长 MCMC / 换先验 / 查时间信号（root-to-tip） |
| ML 树 | UFBoot≥95 + SH-aLRT≥80 | IQ-TREE 输出 | 查比对质量 / 模型选择 / 异常序列 |
| 正选择 | FDR p<0.05 + FUBAR 与 PAML M7M8 双显著 | 两法位点交集 | 单方法显著仅列候选，说明局限 |
| 数据质控 | 覆盖度报告 + 异常序列标注 | 长度/终止子/模糊碱基/重复检查 | 未过禁止进 pipeline |
| 时间信号 | root-to-tip R² 与斜率合理性 | TempEst | 信号不足禁推 BEAST，改距离法 |
| 引用 | 每条断言附 PMID/DOI | Crossref/PubMed 核验 | 无来源删除或降级标注 |
| 结构置信 | pLDDT≥70 区域方可做结构解读 | AlphaFold 输出 | <70 区域降级标注 |
| **复现校准**（R4 2026-09-26） | 复现类模块（M17+）关键统计量与论文锁定值差异 <预指定阈值（如 ΔP<0.005、freq<0.01），且 n 一致 | 对照原模块 notebook 数据准备段逐条校准 | **禁止进入下游计算**（与 ESS<200 同级暂停）——未校准建树/长跑 = 白烧算力 |
| **红队台账**（R2 2026-09-26） | 每次慢通道后 finding 全量登记 redteam_ledger.csv；P0 级闭环率脚本统计 | `python3 redteam_tools.py stats` | 未登记不汇编；未闭环 P0 不投出 |
| **完整性巡检**（R1 2026-09-26） | 慢通道启动前 manifest diff 无缺失 + validate 通过 | `python3 redteam_tools.py check` | 缺失文件先 git checkout 恢复再开跑 |
| 高危操作 | 警告 + 二次确认 | — | 无确认不执行 |

## 原则
- 门控在任务对齐阶段与用户确认；调整写入 quality_gates.md 覆盖本表
- 门控未通过 → 暂停 → 报告原因 → 给改进方案（不静默降级）

## 团队级脚本化门禁（D2 修复 · 2026-10-15）

上表为**领域分析门**（成员自查）；下表为**团队协作门**（主理人收产出时跑，已脚本化）：

| 门 | 检查内容 | 执行方式 |
|---|---|---|
| G1 信封完整 | artifact 头部 JSON 含 6 必填字段 + status 合法 | `scripts/check_gates.py <run-dir> <task-id>` |
| G2 数字溯源 | 关键数字在权威源 grep 得到（外部引文数字由主理人人工核 URL 后放行） | 同上（或 verify_member_output.py 单独跑） |
| G3 产出落盘 | `<task-id>__<member>.md` 存在 | 同上 |
| G4 核验留痕 | output-check.json 已生成 | 同上 |
| G5 审判留痕 | checklist.json 已生成（T0/T1 凭证） | 同上 |
| 假说治理 | 活跃假说无"晚于池更新的 fatal/severe 证伪"积压 | `scripts/hypothesis_watch.py`（T2 必跑） |
| 契约完整 | manifest 一致 + agents 9 + skills 1 契约条款在位 | `scripts/validate_contracts.py` |
| 叙事边界 | 包内无项目特定事件污染 | `scripts/check_scope.py` |

全部门禁 **EXIT=0 过 / 5 FAIL**，可串联 CI；报告落 `<run-dir>/<task-id>__gates.json`。
