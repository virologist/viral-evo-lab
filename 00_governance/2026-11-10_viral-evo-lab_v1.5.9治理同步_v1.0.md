# viral-evo-lab v1.5.9 治理侧同步（2026-11-10）

> 对应专家包 `c075c70` / tag `v1.5.9`（`https://github.com/virologist/viral-evo-lab.git`，已 push）。
> 依据：`viral-evo-lab-audit/AUDIT_STATE.md` §15、专家包 `CHANGELOG.md` [1.5.9]。

## 1. 本轮范围

用户要求「妥善完成 v1.5.8 收尾的『裁决与真实未完成』，直至全部任务完成」。
v1.5.8 §14 列的 1 项裁决 + 6 项真实未完成，本轮**全部转为施工项并闭合**，不再以「明确不施工 / 不代写 / mitigated」收尾。v1.5.7 已闭环的 L3 盲检循环未重开。

## 2. 决策台账变更（本仓）

- `decision_log.csv` 追加 **5 条真实裁决**（6 → **11** 条），`actor=lead` / `tier=通知档`，
  时间戳取本机真实时间：`process-decision`（ADR-001）、`gate-hardening`（G6）、
  `governance`（对账+锚刷新）、`external-dependency`（V2 归属）、`monitoring`（B-5）。
- 补落是**按用户授权由 archivist 代行的一次性治理动作**，不是包内脚本行为：
  `reconcile_decisions.py` 仍只读、**拒写台账或同名文件**（ADR-004）。
- 实测：`python3 scripts/audit_decision_log.py <台账> --json` → `EXIT=0 / HEALTHY / 11 条 / age_days=0`。
- 新增 `00_governance/anchor_refresh_log.jsonl`：包外基线锚的刷新事件留痕（本轮 1 行，
  `commit=c075c70…`、`tag=v1.5.9`、理由含新增 7 资产）。与审计区
  `BASELINE_ANCHORS.json` 的 `refresh_history` 互为双位置对账。

## 3. 七项闭合对照

| # | 项 | v1.5.8 | v1.5.9 落点 |
|---|---|---|---|
| 1 | `--require-tag` 裁决 | 只落一句结论 | `ADR-001_require_tag_default_off.md` + `docs/decision_records.json` + `scripts/check_decision_records.py`（防翻转 `EXIT=5`）；**默认值保持关闭** |
| 2 | G6 抽查门 | 明确不施工 | `verify_evidence_check.py` + `check_gates.py --require-evidence-check`；SKIP 写 `skipped_gates`；SOP T-D1 销项 |
| 3 | 语义级裁决对账 | 人工 T2 | `reconcile_decisions.py` 候选对账 + `[DRAFT·待人工终裁]`；逐条终裁仍人工 |
| 4 | 包外锚人工刷新 | mitigated | `--refresh` 受控刷新 + `refresh_history` + commit 防刷绿 → **fixed**（21/21 一致） |
| 5 | 台账 25 天未更新 | 本轮不代写 | 本仓已补落 5 条，`HEALTHY/EXIT=0` |
| 6 | V2 联邦归属 | 外部依赖 | `viral-evo-lab-audit/VENDOR_PROVENANCE.md` 实证核实销项 |
| 7 | P4 B-5 cron | 未排期 | `cron_watch.sh` + `install_cron_watch.sh`（dry-run 默认） |

## 4. V2 归属结论（摘要）

联邦真源 = `https://github.com/virologist/my-experts-plugins.git`（`master`）的
`shared-core/assemble_spawn_prompt.py`；专家包仓 `virologist/viral-evo-lab` 是**另一个独立仓**，
`vendor/shared-core/` 只是兜底副本。三方 sha256 一致（`3c3648f17cedf1df…`，694 行）。
`VENDOR.json` 的 `upstream_repo: my-experts/viral-evo-lab` 为口径偏差，按「联邦侧不擅改」红线
**本轮不修改**，已在 `VENDOR_PROVENANCE.md` 记录正确修复通道（改联邦仓后重分发）。

## 5. 运维速查（新脚本）

```bash
PKG=~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab
# 裁决一致性（防 --require-tag 默认值被翻转）
python3 $PKG/scripts/check_decision_records.py
# G6 抽查硬门（默认不强制；显式启用）
python3 $PKG/scripts/check_gates.py <run_dir> <task_id> --require-evidence-check
python3 $PKG/scripts/verify_evidence_check.py <run_dir> --json
# 决策候选对账（只读；DRAFT 须人工终裁）
python3 $PKG/scripts/reconcile_decisions.py --run-dirs <run_dir> --ledger research-ops/00_governance/decision_log.csv
# 包外锚对账 / 受控刷新
python3 $PKG/scripts/check_baseline_anchors.py --anchors viral-evo-lab-audit/BASELINE_ANCHORS.json
python3 $PKG/scripts/check_baseline_anchors.py --anchors <锚> --refresh \
    --i-acknowledge-refresh --reason "<理由>" --git-log research-ops/00_governance/anchor_refresh_log.jsonl
# P4 B-5（dry-run 默认，不自动装系统调度）
bash $PKG/scripts/install_cron_watch.sh --run-dir <dir> --state-dir <dir>
```

## 6. 真实边界（不伪装）

- G6 **默认不强制**（存量 run_dir 无 evidence_check，默认强制会误杀）；未启用必写 `skipped_gates`；脚本只验形式要件，语义真伪归主理人 T1。
- 系统 **crontab 零改动**：安装器默认 dry-run，须用户显式 `--install`；跨会话告警推送通道（IM/邮件）属新范围、未排期。
- 包内脚本**永不代写台账**；语义级逐条终裁仍属人工 T2。
- 联邦 shared-core / vendor 副本**均未改动**；`upstream_repo` 偏差只记录、不擅改。
- 包外锚刷新仍是人工动作（须 ACK+reason+干净工作区），只是不再需要手算 sha；默认只读不变。
