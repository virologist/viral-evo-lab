---
last_updated: 2026-11-10
---

# 质量门控阈值表（默认配置）
> **两层权威结构**（B4 2026-11-07 统一措辞，与 lead-ops.md 对齐）：本表 = 跨项目默认权威；工作空间 `research-ops/context_stack/quality_gates.md` = 项目级覆盖层（用户在任务对齐阶段调整后任务内生效）。任务中生效值：有项目级覆盖用覆盖值，无则用本表。

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
| **完整性巡检**（R1 2026-09-26） | 慢通道启动前 manifest diff 无缺失 + validate 通过 | `python3 redteam_tools.py check` | 缺失文件先判类型：宿主管理的 `settings.json` 禁止 `git checkout --` 恢复（见主理人 MD「完整性巡检」），其余文件才按 git 恢复 |
| 高危操作 | 警告 + 二次确认 | — | 无确认不执行 |

## 原则
- 门控在任务对齐阶段与用户确认；调整写入 quality_gates.md 覆盖本表
- 门控未通过 → 暂停 → 报告原因 → 给改进方案（不静默降级）

## 团队级脚本化门禁（D2 修复 · 2026-10-15）

上表为**领域分析门**（成员自查）；下表为**团队协作门**（主理人收产出时跑，已脚本化）：

| 门 | 检查内容 | 执行方式 |
|---|---|---|
| G1 信封完整 | artifact 头部 JSON 含 6 必填字段 + status 合法；分析类任务（`workflow` 归一为 WF4）另须含 `hypothesis_anchor` 三要素 | `scripts/check_gates.py <run-dir> <task-id>` |
| G2 数字溯源 | 关键数字在权威源 grep 得到（外部引文数字由主理人人工核 URL 后放行） | 同上（或 verify_member_output.py 单独跑） |
| G3 产出落盘 | `<task-id>__<member>.md` 存在 | 同上 |
| G4 核验留痕 | output-check.json 已生成；`gate_mode=block` 且 verdict≠PASS 时判 FAIL，须由 waivers.json 人工放行 | 同上 |
| G5 审判留痕 | checklist.json 已生成（T0/T1 凭证） | 同上 |
| G6 抽查留痕 | `spawn_manifest.jsonl` ≥2 条 `evidence_check`（actor=lead，含 `file:行号` + 原文摘录 + reason） | 同上；**默认 SKIP** 并写入 `skipped_gates`（不伪装 PASS），`--require-evidence-check` 或 `evidence_check_policy.json` 启用后形式要件不合格判 FAIL |
| 假说治理 | 活跃假说无"晚于池更新的 fatal/severe 证伪"积压 | `scripts/hypothesis_watch.py`（T2 必跑） |
| 契约完整 | manifest 一致 + agents 9 + skills 1 契约条款在位 | `scripts/validate_contracts.py` |
| 叙事边界 | 包内无项目特定事件污染 | `scripts/check_scope.py` |

全部门禁 **EXIT=0 全过 / 3 artifact 缺失 / 5 门禁 FAIL**，可串联 CI；报告落 `<run-dir>/<task-id>__gates.json`。**G6 默认不强制**（ADR-002）：未启用时以 `SKIP` 记入 `skipped_gates`，不得伪装成 PASS；启用后形式要件不合格统一 `EXIT=5`。脚本只验形式要件，抽查语义真伪归主理人 T1 人工。

**waiver 放行口径（L3 · 2026-11-09）**：G2 与 G4 共用 `<task-id>__waivers.json`；每条须 `value` + `reason` + `authorized_by` 三项齐全，缺任一项不放行（防自我授权/空口放行）。G4 阻断态须 waiver 覆盖**全部**未溯源数字才放行，部分覆盖不解除阻断。行使须落 `decision_log.csv`。

**workflow 交叉核验（A-1 · 2026-11-09）**：G1 的分析类判定**以主理人下发声明为权威源**——`assemble_spawn_prompt.py --workflow <值>` 落 sidecar `<run-dir>/<task-id>__workflow.json`；成员信封的 `workflow` 只用于**类别级比对**（`analysis` / `other`）。不一致即 G1 FAIL（回传缺失 / 擅自降级 / 擅自升级均拦）。表述差异（`WF4 分析执行` vs `WF4` vs `analysis`）属同一类别，不拦。无 sidecar 的存量链路退回「只信信封」旧行为，不误阻断存量产出。

**假说治理处置门禁**：`hypothesis_watch.py --check-disposition` 为只读验收，EXIT=0（无需处置/处置完整）/ 6（可裁决但处置不合规）/ 3（无法裁决）。判别原则：区别不是「哪个文件坏了」，而是**坏掉后还能不能算出裁决**——证据源（假说池 / redteam_ledger.csv）畸形 → 无法算出 late_fatal → EXIT=3；处置记录（hypothesis_watch_state.json）畸形 → 证据源完好，保守按未处置 → EXIT=6。无待处置项且池未超期时判 PASS，不误阻断存量项目。
