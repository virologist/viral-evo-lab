# context_stack/

跨轮记忆引擎，**五个逻辑主题**每轮按需增量更新（锚点 / 假说池 / 方法库 / 约束 / 门控）。

> 口径说明：治理协议里的「五文件」指五个**逻辑主题**，不是物理文件数。物理层 json 为机器可读真源、md 为渲染视图，另有扩展索引文件。2026-11-13 体检据此补齐清单，不改变协议本身。

## 逻辑五文件（md 渲染视图）
- `research_anchor.md` — 活跃战线与数据资产锚点
- `confirmed_hypotheses.md` — **仅**用户明确认可的假说（写入受 gate 保护）
- `method_library.md` — 项目级核心管线快照（权威定义在 skills/viral-evo-core/）
- `user_constraints.md` — 资源约束 + 产出标准 + 交互纪律
- `quality_gates.md` — 项目级定制快照（权威定义在 skills/viral-evo-core/）

## 结构化真源（json · 4 个）
- `research_anchor.json` / `confirmed_hypotheses.json` / `method_library.json` — 对应前三个主题的机器可读真源（`CLAUDE.md` 与核验脚本读 json）
- `knowledge_index.json` — 扩展主题「知识索引」的真源
- `user_constraints` / `quality_gates` 当前仅 md、无 json 镜像（是当前实现，不是遗漏）

## 扩展文件（非协议项）
- `knowledge_index.md` — 知识索引渲染视图
- `diagnostic_findings.md` — 诊断发现留痕
- `README.md` — 本说明

## 写入规则（增量）
- 仅在有新增/变更条目时更新；纯检索轮零写放大
- 权威源唯一性：阈值/前沿/检索源以 skills/viral-evo-core/references/ 为准
- 单文件超 15 条 → 语义摘要压缩，保留核心约束锚点