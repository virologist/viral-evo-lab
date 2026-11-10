# viral-evo-lab v1.5.12 治理同步（盲检 R7 · 收敛修复）

- **日期**：2026-11-11
- **专家包**：`main` = `deb1560`（tag `v1.5.12`，已 push，clean）
- **性质**：第三次独立盲检（R7）证伪 v1.5.11「零挂账」后的全部补齐轮

## 一、R7 盲检发现（实证）

| ID | 级别 | 差异 | 处置 |
|---|---|---|---|
| R7-1 | 🔴 | `_wording_counts()` 用跨版本宽正则取「当前基线」，实际命中 v1.5.10 历史段；自称「当前基线」的 v1.5.11 段被改成 14 仍全绿（同构第三次） | 机器锚 + 双向反验 |
| R7-2 | 🟡 | `AUDIT_STATE.md` §16/§17「research-ops commit 见本文件终验记录」悬空引用 | 改真实 hash |

## 二、v1.5.12 施工（9 files / +87 −28）

1. `test_gate_fuzz.py` docstring 落唯一机器锚 `CURRENT_BASELINE = 45 CASES + 15 行为级 = 60/60`；`_wording_counts()` 的 doc 数字只读该锚，废除跨版本宽正则。
2. 第 4 步补「仅改机器锚必被抓」反向断言；三态自检 `15/15`、改 main `14/15`、改机器锚 `15/16`。
3. 守卫 `WORDING_POSITIVE` 增 `CURRENT_BASELINE` 存活锚：正向锚 13→14、逐锚回退 17 次（单一事实源自动覆盖）。
4. §16/§17 悬空引用改真实 hash（`303c42e` / `49135e5`）；§17 施工第 3 条追加证伪标注（保留原文）。
5. 消除 docstring `SyntaxWarning`；CHANGELOG [1.5.12]、CLAUDE v1.5.12 节、LEARNINGS LRN-029。

## 三、终验基线（定版前实测）

pytest **18 passed** ｜ fuzz **60/60** ｜ 守卫 **11/11** ｜ V7 **7/7** ｜ contracts / scope / manifest（79 文件）全绿 ｜ 四处 version=1.5.12 ｜ 台账 **15 条** `HEALTHY/EXIT=0` ｜ 包外锚 21/21（`refresh_history=4`，`source.commit==deb1560`）；篡改演练改 sha→`5/DRIFT`、改 commit→`3/ANCHOR_SCHEMA_INVALID`，真锚字节未变。

## 四、发布链

- 专家包 `deb1560` + tag `v1.5.12` → `origin/main` / tag，`ls-remote` 同 hash，clean
- research-ops：本轮治理同步 commit → `origin/research-ops-track`；含 `decision_log.csv`（+1 条真实裁决，14→15）、`anchor_refresh_log.jsonl`（+1 行，共 4 行）、本治理同步文档

## 五、真实边界（不伪装）

同 §17/§18：G6 默认不强制（ADR-002）、crontab 零改动、包内脚本永不代写台账、语义逐条终裁人工 T2、`--require-tag` 默认关闭（ADR-001）、包外锚刷新为人工 ACK、联邦 shared-core / vendor 未改；守卫第 11 项只锚 5 个固定文件。

## 六、收敛判定

R7 仍有 1🔴，未达收敛。按判据（连续 2 轮无 🔴 独立盲检），需 **R8 零🔴** 后 R9 复核再宣布收敛冻结。下一轮动作已明确：R8 盲检 → 若零🔴 则再跑一轮全量基线 + 独立复核，两轮通过即冻结。
