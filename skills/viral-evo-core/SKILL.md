---
name: viral-evo-core
description: 病毒演化研究院共享方法库。当执行病毒遗传进化研究的检索、假说生成、系统发育/选择压/结构分析、代码产出、文档落盘时加载，获取检索源优先级、质量门控阈值、代码规范、方法迁移模板与 2025-2026 前沿对齐摘要。
---

# viral-evo-core — 团队共享方法库

病毒演化研究院全员共享的核心参考。按任务类型查阅对应 reference，不必全文加载。

## 索引

| 场景 | 查阅文件 |
|---|---|
| 文献检索、引用核验、前沿追踪 | `references/search-sources.md` |
| 任何分析的质量门控阈值与未通过处置 | `references/quality-gates.md` |
| 代码/Notebook 产出前 | `references/code-standards.md` |
| 从论文/附件迁移方法 | `references/method-transfer-template.md` |
| 需要 2025-2026 前沿锚点（DMS/LM/CoalRe/结构系统发育） | `references/frontier-2025-2026.md` |
| 跨域方法迁移（医学/植物/昆虫病毒）| `references/medical-vet-bridge.md` |
| 研究诊断审视（方法/数据/管线协同） | `references/diagnostic-protocol.md` |
| 上下文接近阈值/长会话/需要压缩时 | `references/context-compaction.md` |
| 需要跨编号系统换算/从比对取残基 | `references/coordinate-mapping.md` |

## 团队工具与契约（v1.2.3+ · 2026-10-14 补）

本包 `scripts/` 目录提供团队级确定性工具（路径由主理人装配时统一下发，成员按需 Read/Bash）：

| 工具 | 用途 | 调用方 |
|---|---|---|
| `scripts/assemble_spawn_prompt.py` | 成员 spawn 人设装配（含团队版本号/知识态注入/任务前数字核验） | 主理人 |
| `scripts/verify_numbers.py` | 数字核验底层库（5 类模式提取 + 权威源 grep） | 主理人/成员自检 |
| `scripts/verify_member_output.py` | **产出端**数字核验（run-dir artifact 一键核，`--gate` 阻断） | 主理人收 envelope 时 |
| `scripts/check_scope.py` | 落盘前项目特定叙事自检（事故黑名单） | 主理人/成员 |
| `scripts/write_checklist.py` | 纪律审判 checklist 落盘（JSON schema） | 主理人 T0/T1 |
| `scripts/find_knowledge.py` | 跨仓知识查询入口 | 全员 |
| `scripts/validate_contracts.py` | 契约完整性检查（agents+skills 层） | 主理人/CI |

**成员须知**（完整契约以 `agents/viral-evo-lab-team-lead.md` 为准，本表仅索引）：
- 上行 `result_envelope` 6 必填字段（agent_id/task_id/phase/status/confidence/deliverable_summary）
- 产出中关键数字（n=/p=/D′/百分比/CI）必须可溯源至权威源（仅 csv/json 计算产物），否则标 `[待人工核验]`
- 本 MD/references 只写通用机制与领域知识，**不写项目特定事件/数字/PMID**（见 `GOVERNANCE_BOUNDARIES.md`，`check_scope.py` 机械兜底）

## 铁律速查
1. 断言必附 PMID/DOI，无来源不输出
2. 推断必标 [推断|待核查→方向]
3. 质控未过禁止进 pipeline
4. 数据不足宁可降级结论
5. 高危操作（删除/覆写）→ 警告 + 二次确认
6. 科学真实性 > 方法严谨性 > 结果美观性 > 分析效率
7. **数字必溯源**：任何关键数字须在权威源中 grep 得到，找不到 = `[待人工核验]`（V1/产出端关卡机械兜底）
8. **包内禁项目叙事**：本包只承载通用机制/治理/版本与领域共享知识；项目特定事件归各项目仓
