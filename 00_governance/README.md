# 00_governance/

团队章程、协议、审查记录。

## 文件清单
> ⚠️ **活跃治理存档**：本目录随每次治理/审查动态新增文件，当前共 **20** 个（含本 README）。下方按类型归类，**不逐文件硬编码**以免再次漂移；新增即在「索引维护」段追加一行。

- 团队章程：`team_charter.md`
- 治理同步文档（v1.5.8–v1.5.12，共 5 份）：`2026-11-09`_v1.5.8、`2026-11-10`_v1.5.9 / v1.5.10 / v1.5.11、`2026-11-11`_v1.5.12
- 工程化 / 红队报告（共 4 份）：`2026-09-18_团队工程化优化报告`、`2026-09-26_WF5_红队总矩阵_cover_letter`、`2026-09-26_WF5_P0闭环报告_cover_letter修复`、`2026-09-30_WF1_unified_report`
- 决策 / 台账（共 4 份）：`decision_log.csv`、`anchor_refresh_log.jsonl`、`redteam_ledger.csv`、`redteam_stats_latest.txt`
- 脚本与摘要（共 5 份）：`memory_roll.py`、`redteam_tools.py`、`changes_summary.py`、`changes_summary_20261014.json`、`changes_summary_20261014.md`
- 本文件：`README.md`

## 索引维护
archivist 在每条章程修订或审查记录新增后追加一行：路径 | 类型 | 状态
## 台账字段语义（R2-6 · 2026-10-15）
- `closed_date` **仅在 `status=closed` 时允许填写**；partial/failed 行禁止填（否则闭环率统计与 hypothesis_watch 判定被污染）
- 修复完成但未复核 = `partial` + `fix_commit`（可填）+ `closed_date` 留空；复核通过（verified_by/verified_date，backlog）后才置 `closed`
