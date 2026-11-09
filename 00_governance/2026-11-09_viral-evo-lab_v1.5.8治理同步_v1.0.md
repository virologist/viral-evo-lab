# viral-evo-lab v1.5.8 治理同步记录（2026-11-09）

> 性质：`viral-evo-lab-audit/AUDIT_STATE.md` §13「遗留 backlog 清理轮」的**治理侧同步**。v1.5.7 已按「连续 2 轮无 🔴」宣布循环审计闭环，本轮**不重开审计循环**，只清理实证清单，不改写任何历史结论。
> 命名遵循 research-ops 约定：`{日期}_{主题}_{版本}.md`。

## 1. 对治理层的直接影响：`decision_log.csv` 终于有消费端

- 此前 `docs/authorization_matrix.md` §四 规定「无 decision_log 记录的裁决 = 未发生」，但专家包全量检索的脚本消费端 = **0**，属「只规定写、没人读」的治理空转（LRN-021）。
- v1.5.8 新增 `scripts/audit_decision_log.py`（专家包内，**不在本仓**）：只读四查（结构 / 必填字段 / tier 白名单 / 陈旧阈值），退出码 `0 健康 / 3 结构失败 / 5 内容违规 / 6 陈旧提醒`，`--json` 供机器消费。
- archivist 在 T2 处置闭环前可跑：

  ```bash
  python3 ~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/scripts/audit_decision_log.py \
      "<工作区>/research-ops/00_governance/decision_log.csv" [--max-age-days 30] [--json]
  ```

- **2026-11-09 实测**：本仓台账 6 条、最新 `2026-10-15T08:36:56+08:00`、距今 25 天 → 默认 30 天阈值下 `HEALTHY/EXIT=0`；收紧到 `--max-age-days 1` 才 `STALE/EXIT=6`。
- ⚠️ **治理提醒（真实、非脚本故障）**：台账已 25 天无新条目。按 §四 纪律，若期间有 Block/决策档裁决行使，应由 archivist 补落条目。**本轮明确不代写台账**，脚本只读、不创建、不修复任何文件。语义级「某次裁决是否有对应条目」仍由主理人 T2 人工核对（自由文本机械匹配不可靠）。

## 2. 双位置一致性判据（用户要求的「两处均为最新版本」）

| 位置 | 分支 / 远端 | 版本锚 | 状态 |
|---|---|---|---|
| 专家包真源（本机 + GitHub） | `main` / `origin/main` | `b5033ed` · tag `v1.5.8` | local = origin（`git ls-remote` 实测同 hash）；工作区 clean |
| research-ops 治理仓（本仓） | `main` / `origin/research-ops-track` | 本文件所属提交 | 本记录随提交推送 |
| 审计区（本地工作区，无 git） | — | `AUDIT_STATE.md` §14 + `BASELINE_ANCHORS.json` | §13 八项清单闭合状态、包外基线锚 14 文件 |

- 包外基线锚：`viral-evo-lab-audit/BASELINE_ANCHORS.json`（`source.tag=v1.5.8` / `source.commit=b5033ed…`），由 `scripts/check_baseline_anchors.py --anchors <锚>` 只读对账。实测一致态 `EXIT=0`，篡改一个 sha256 → `EXIT=5 / DRIFT` 且真锚未动。**正常改动后须人工重生成基线，禁止改锚刷绿**。

## 3. 本轮闭合项摘要（详见 AUDIT_STATE §14）

- 🔴 P0-1 `decision_log` 零消费端 → 只读审计脚本 + 行为级测试 + guard 第 9 项锚 + 授权矩阵 §四/§五 文档真化。
- 🔴 P0-2 G3 FAIL 不落 `gates.json` → `check_gates.py` 所有退出路径共用 `write_report()`，`EXIT=3` 不变。
- 🟠 P1 `--require-tag` 默认值**裁决保持关闭**（向后兼容 + fuzz 锁定）；`CLAUDE.md` 三/四 JSON 冲突订正；审计区文档漂移销项。
- 🟡 P2 D2 质量判据扩展到追问/4R/Gödel（文档级，人工判定 + checklist，不虚构机器计数）；双文件同覆残余补包外基线锚（**mitigated，非 fixed**）。
- 终验：pytest **12 passed** ｜ fuzz **54/54** ｜ 守卫 **9/9** ｜ V7 **7/7** ｜ contracts / scope / manifest `--check` 全绿 ｜ 16 脚本编译 + `--help` 全过 ｜ 四处 version = `1.5.8`。

## 4. 真实未完成（不伪装，不阻塞）

| 项 | 状态 | 理由 |
|---|---|---|
| agent-harness-sop T-D1「G6 抽查门」 | ⚪ 实测不存在 | 属另一战线，需 `check_gates.py` 改造 + 红线评估（估 4h）；已在 `04-test/00_交付报告.md` 标注真实状态 |
| V2 联邦真源仓库归属核实 | ⚪ 外部依赖 | 需人工核实仓库归属，脚本无法判定 |
| P4 B-5 cron 巡检 | ⚪ 未排期 | 跨会话场景，非当前痛点 |
| 语义级裁决 ↔ 台账对账 | 🟡 人工纪律 | 自由文本不可靠，属主理人 T2 |
| 包外基线锚刷新 | 🟡 需人工 | 每次正常改动后重生成，`mitigated` 不是 `fixed` |
