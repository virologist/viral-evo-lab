# 00_governance/

团队章程、协议、审查记录。

## 文件清单
- `team_charter.md` — 团队章程 v1.0（使命链、权重、底线）
- `README.md` — 本文件

## 索引维护
archivist 在每条章程修订或审查记录新增后追加一行：路径 | 类型 | 状态
## 台账字段语义（R2-6 · 2026-10-15）
- `closed_date` **仅在 `status=closed` 时允许填写**；partial/failed 行禁止填（否则闭环率统计与 hypothesis_watch 判定被污染）
- 修复完成但未复核 = `partial` + `fix_commit`（可填）+ `closed_date` 留空；复核通过（verified_by/verified_date，backlog）后才置 `closed`
