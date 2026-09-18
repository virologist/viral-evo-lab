# context_stack/

跨轮记忆引擎，五文件每轮按需增量更新。

## 文件清单
- `research_anchor.md` — 活跃战线与数据资产锚点
- `confirmed_hypotheses.md` — **仅**用户明确认可的假说（写入受 gate 保护）
- `method_library.md` — 项目级核心管线快照（权威定义在 skills/viral-evo-core/）
- `user_constraints.md` — 资源约束 + 产出标准 + 交互纪律
- `quality_gates.md` — 项目级定制快照（权威定义在 skills/viral-evo-core/）

## 写入规则（增量）
- 仅在有新增/变更条目时更新；纯检索轮零写放大
- 权威源唯一性：阈值/前沿/检索源以 skills/viral-evo-core/references/ 为准
- 单文件超 15 条 → 语义摘要压缩，保留核心约束锚点