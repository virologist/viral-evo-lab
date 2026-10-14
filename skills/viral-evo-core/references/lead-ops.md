# 主理人低频运维细则（自 team-lead.md 下沉 · 2026-10-15）

> 主理人 MD 只保留每轮必用的读取行；本文件承载低频细则，按需 Read。

## CONTEXT_STACK JSON 真源细则

- **JSON 真源优先级（Anthropic feature_list.json 模式，P0-1 2026-09-18 落盘）**：
  - **机器读取**：必须从 `.json` 读取（严格 schema 防 model 改坏）
  - **人类视图**：`.md` 是渲染输出，可读可编辑但需走 archivist 同步 JSON
  - **已 JSON 化的真源**：`confirmed_hypotheses.json` / `method_library.json` / `research_anchor.json`
  - **未 JSON 化（保留 .md）**：`user_constraints.md` / `quality_gates.md`（按权威源唯一性原则保留在 skills/ 中）
- **写入规则（增量）**：
  - **仅在有新增/变更条目时**由 archivist 写入对应 JSON + 渲染 .md
  - **纯检索轮**（WF3 简报型任务，零新发现）：不动 context_stack，避免写放大
  - 用户明确修正某项 → 立即覆盖写入 JSON
  - **修改纪律**：禁止"先改 .md 再让 archivist 同步 JSON"——直接编辑 JSON，archivist 重新渲染 .md
- **权威源唯一性**：阈值/前沿锚点/检索源优先级以 `skills/viral-evo-core/references/` 内文件为权威源；`context_stack/` 仅记录项目级快照/锚点/确认假说
- **压缩（P1-6 2026-09-18，详见 skills/viral-evo-core/references/context-compaction.md）**：
  - 单轮 context > 85% → 触发压缩：清旧工具结果，保留结论+指针，日志先落盘
  - 单 JSON 条目 > 15 条 → archivist 语义摘要压缩 + schema_version bump
  - **永久保留清单（禁压缩）**：可证伪条件 / 质量门控阈值 / 用户约束 / 假说核心主张
  - 冲突事实必须显式记录，禁止静默替换
- **失败模式监控**：若 JSON 与 .md 出现不一致，archivist 必须立即报警并以 JSON 为准修复 .md

## 同步器
改任一 JSON 后必须跑：`python3 <专家包>/scripts/render_context_stack.py`（4 份 md 视图一键重渲染，禁手改 md）
