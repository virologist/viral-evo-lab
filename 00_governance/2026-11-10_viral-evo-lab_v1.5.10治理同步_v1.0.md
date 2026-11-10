# viral-evo-lab v1.5.10 治理同步（2026-11-10）

## 定位

本文件是 research-ops 治理仓对 viral-evo-lab 专家包 v1.5.10 的事实同步记录。专家包真源在 `virologist/viral-evo-lab.git`；本仓只保存治理侧凭证、决策台账与锚刷新留痕，**不复制包内代码**。

## 接续与结论

- 起点：v1.5.9 `c075c70` = HEAD = `origin/main`，clean；`viral-evo-lab-audit/AUDIT_STATE.md` §15 宣布「七项全部闭合、零挂账」。
- 用户指令：继续完成此前中断的开发任务，核对已完成与未完成事项、逐一补齐剩余实现、确认所有原始任务完整完成。
- **独立只读盲检证伪「零挂账」**：抓到 4 个 🔴 新发现 + 1 个 §15 自认残留。根因 = v1.5.9 守卫第 10 项只锚「新脚本存在」，未锚「权威文档 / CLI 的当前口径」，导致代码升到 G1-G6 而 CLI help、门表、主理人 T1 条款仍写五门，cron 锁注释仍写已废弃实现，fuzz docstring 停在 v1.5.8——而全量测试仍全绿。**上一轮「零挂账」不成立，本轮全部补正。**

## 本轮闭合清单

| # | 级别 | 项 | 落点 |
|---|---|---|---|
| 1 | 🔴 | CLI help 仍称 G1-G5 | `scripts/check_gates.py` argparse description → G1-G6 + G6 默认 SKIP 说明 |
| 2 | 🔴 | 权威门表停在五门 / frontmatter 停在 2026-10-14 | `skills/viral-evo-core/references/quality-gates.md` 补 G6 行 + 「G6 默认不强制」与退出码口径 + `last_updated: 2026-11-10` |
| 3 | 🔴 | 主理人活跃 T1 条款仍「五门齐查」 | `agents/viral-evo-lab-team-lead.md` 三处 → G1–G6 / 六门齐查 + `--require-evidence-check` 启用条件（v1.5.9 文档真化清单漏掉的文件） |
| 4 | 🔴 | cron 头部注释仍写 mkdir 目录锁 | `scripts/cron_watch.sh` → noclobber（O_EXCL）文件锁 + 退出码补「锁冲突跳过 / poll 透传」 |
| 5 | 🔴 | fuzz docstring 停在 v1.5.8（§15 自认残留） | `tests/test_gate_fuzz.py` 补 v1.5.10 当前基线段（行为级 9→15，45+15=60/60，`total = len(CASES) + 15`） |
| 6 | 🟠 | 防线根因：口径漂移无人拦截 | 守卫第 11 项「当前口径一致性守卫」正/负双向锚 + `test_current_wording_guard` 行为级用例 + V7 互锚下限 10→11 |
| 7 | 🟡 | 文字残留 / SOP 历史行未索引 | `test_vendor_core.py` 头部补 V7 与数字订正、`gen_integrity_manifest.py` 补 `exit 2`、SOP 三文档（T-A1.1 测试/实施报告、T-A1 返工单）追加跨战线销项索引（不改写历史文本） |

## 防复发机制（本轮核心）

- **守卫第 11 项**：positive 锚（必须出现的当前口径：G1-G6 / G6 门表行 / 六门齐查 / noclobber / `len(CASES) + 15`）+ negative 锚（禁止出现的旧口径：`五门齐查` / `mkdir 原子锁` / `last_updated: 2026-10-14`）。
- **`test_current_wording_guard`**：①真跑 `check_gates.py --help` 断言含 G1-G6；②importlib 真加载守卫断言当前包第 11 项 PASS；③复制整包改回旧口径，**断言第 11 项真实 FAIL**（防恒真）；④正则比对 docstring 与 `main()` 用例数一致。
- **V7**：项数下限 10 → 11 + 第 11 项标题锚，头部检查项补 V7 行。
- 经验入库：`.learnings/LEARNINGS.md` LRN-20261110-027「『脚本存在』不等于『口径已同步』」。

## 终验基线

pytest **18 passed** ｜ fuzz **60/60**（45 CASES + 15 行为级）｜ 守卫 **11/11** ｜ V7 **7/7** ｜ contracts / scope / manifest `--check` 全绿（**79** 文件）｜ 21 脚本（19 py + 2 sh）编译/语法 + `--help` 全过 ｜ 四处 version = **1.5.10** ｜ `check_decision_records.py` `EXIT=0 / OK` ｜ 决策台账 `HEALTHY / EXIT=0`（**13** 条，0 天）。

包外锚：21/21 一致、`source.commit == HEAD`、`refresh_history=2`、本仓 `anchor_refresh_log.jsonl` 2 行；篡改演练：改一个 sha → `5/DRIFT`，改 `source.commit` → `3/ANCHOR_SCHEMA_INVALID`（提示「疑改锚刷绿」），真锚字节未变。

## 发布链

- 专家包：commit `3095ec4f3076fd892188e6ce5ae85b9e86ffe543` + 轻量 tag `v1.5.10` → `origin/main` / tag，`git ls-remote` 同 hash，工作区 clean。
- research-ops：本文件 + `decision_log.csv`（+2 条真实裁决，11 → 13）+ `anchor_refresh_log.jsonl`（+1 行）→ `origin/research-ops-track`。
- 审计区（无 git）：`AUDIT_STATE.md` §16、`BASELINE_ANCHORS.json`（21 文件，source.tag=v1.5.10）；`agent-harness-sop` 三文档销项索引；`.workbuddy/memory/` 日志与项目记忆已同步。

## 真实边界（非未完成缺陷）

- G6 **默认不强制**（ADR-002，存量 run_dir 免误杀）；未启用必写 `skipped_gates`，抽查语义真伪归主理人 T1 人工。
- 系统 crontab **零改动**；包内脚本**永不代写台账**，语义逐条终裁属人工 T2；`--require-tag` 保持默认关闭（ADR-001）。
- 包外锚刷新仍为人工 ACK 动作（ACK+reason+干净工作区+commit 溯源）；联邦 shared-core / vendor 副本未改。
- 带版本标题的历史条目（CHANGELOG v1.5.9 及更早、CLAUDE 历史节、SOP 历史表）按「禁止改写历史」保留原样；本轮只订正**无版本标注的活跃条款**，历史行以追加销项索引处理。

---

> ⚠️ **v1.5.11 订正（2026-11-10，追加不改写历史）**：上文「防复发机制」中 ③「复制整包改回旧口径」与 ④「正则比对 docstring 与 `main()` 用例数一致」两句是 v1.5.10 时点声称，独立只读终验盲检实证与实现不符——③只回退 1 个文件 1 个锚，④ `re.search` 命中 docstring 自己（改 `main()` 的 total 断言仍通过），且 `last_updated` 当前值缺正向锚。v1.5.11 已全部修复：锚清单提为守卫模块级 `WORDING_POSITIVE` / `WORDING_NEGATIVE` 单一事实源、第 11 项抽 `check_current_wording()`、新增 `_wording_counts()` 只从 `main()` 体内取 total、反向用例扩为逐锚回退（13 正向 + 3 负向共 16 次）。当前口径见 `2026-11-10_viral-evo-lab_v1.5.11治理同步_v1.0.md` 与 `viral-evo-lab-audit/AUDIT_STATE.md` §17。
