# research-ops — 病毒演化研究文档系统

> 归属：病毒演化研究院（viral-evo-lab 专家团）| 建档：2026-09-10
> 用途：方法、过程、结果全程留痕；40_manuscript_assets 直接供论文撰写专家团消费。

## 目录协议

| 目录 | 写入内容 | 写入者 |
|---|---|---|
| `00_governance/` | 团队章程、质量门控、SOP 快照、版本治理同步记录 | 主理人 |
| `01_diagnostics/` | 专家团/项目独立诊断与对齐方案（历史 v1/v2 已归档至 `_archive/diagnostics_legacy/`） | 诊断方 |
| `10_hypotheses/` | 假说卡（H[n] 标准格式：主张/证据/预测/可证伪条件/置信度） | 假说引擎官 |
| `20_methods/` | 方法迁移记录（三步迁移：提取→适配→迁移）、pipeline 索引 | 文献侦察员、生信工程师 |
| `30_results/` | 分析结果、质控报告、图表源文件 | 各分析师 |
| `40_manuscript_assets/` | 论文级图、表、方法段落、结果段落（投稿格式） | 档案官汇编 |
| `50_cross_domain/` | 跨域方法迁移卡归档（只迁方法不迁结论；占位 README 说明命名与防复发约束） | archivist |
| `outputs/` | 权威源池（`verify_numbers.py` 的 grep 目标）；**禁止放示例/冒烟数据**，仓内仅留 README | 项目侧 |
| `scripts/` | 运维脚本（`push_all.sh`：三仓一站式 push） | 主理人 |
| `context_stack/` | 跨轮记忆五主题（逻辑）：锚点/假说池/方法库/约束/门控；**json 为真源、md 为渲染视图**，另含扩展索引 | 主理人每轮按需增量更新 |
| `_archive/` | 历史留痕归档区（`harness_runs_legacy/` / `memory_archive_legacy/` / `diagnostics_legacy/`），只读证据链，不删 | archivist |

> 归档去向：`_harness_runs/` 原为 harness 运行产物目录，2026-11-08 已整体 `git mv` 入 `_archive/harness_runs_legacy/`（见 `agent-harness-sop/REORG_MANIFEST.md`），残留空壳已清理。历史报告里 `_harness_runs/...` 路径引用保留为证据链原文，实际文件在归档区。

## 读写铁律
1. 每轮任务结束自动更新 context_stack/ 对应文件；用户明确修正 → 立即覆盖写入
2. 所有产出先落盘本系统，再回传对话——保证其他专家团可接力
3. 文件命名：`{日期}_{主题}_{版本}.md`，如 `2026-09-10_H5Nx-glycan-hypotheses_v1.md`
4. 论文撰写专家团只读 `40_manuscript_assets/` 与 `context_stack/`，不读过程文件
