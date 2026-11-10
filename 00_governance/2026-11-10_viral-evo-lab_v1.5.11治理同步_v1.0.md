# viral-evo-lab v1.5.11 治理同步（2026-11-10）

## 定位

research-ops 治理仓对 viral-evo-lab 专家包 v1.5.11 的事实同步记录。专家包真源在 `virologist/viral-evo-lab.git`；本仓只保存治理侧凭证、决策台账与锚刷新留痕，不复制包内代码。

## 接续与证伪

- 起点：v1.5.10 `3095ec4` = HEAD = `origin/main`，clean；research-ops `303c42e` = `origin/research-ops-track`，clean；`AUDIT_STATE.md` §16 宣布零挂账。
- **独立只读终验盲检再次证伪「零挂账」**：A 类声称数字全部核实无误（pytest 18 / fuzz 60 / 守卫 11 / V7 7 / 21 脚本 / 79 文件 / 四处 version / 台账 13 条 / 锚 21/21 / commit 15 files +204 −51），5 项口径订正真实落地、无活跃旧口径残留、SOP 与记忆资产齐备；但**本轮核心交付「防复发」自身有洞**。

| ID | 级别 | 差异 |
|---|---|---|
| R6-1 | 🟡 | 守卫第 11 项只把 `last_updated: 2026-10-14` 列为负锚，当前值 `2026-11-10` 无正向锚；实测改成任意其它旧日期仍全绿 |
| R6-2 | 🔴 | `test_current_wording_guard` 第 4 步声称「比对 docstring 与 `main()`」，但 `re.search` 第一个命中在 **docstring 自己**；实测只把 `main()` 改成 `+14` 断言仍通过（校验器自证） |
| R6-3 | 🟡 | 第 3 步声称「复制整包改回旧口径」，实际只改 1 文件 1 锚；另外 4 文件 12 个正向锚与 3 个负锚从未被反验 |

R6-2 使 CHANGELOG / CLAUDE / AUDIT_STATE / 本仓 v1.5.10 治理同步文档四处都写入了不实声称，是本轮必须修的实质缺陷。

## 施工闭合

1. `WORDING_POSITIVE` / `WORDING_NEGATIVE` 提为 `tests/test_contract_guard.py` **模块级常量**（单一事实源），守卫第 11 项与反向用例共用；正向锚补 `last_updated: 2026-11-10`。
2. 第 11 项逻辑抽为 `check_current_wording(pkg_root)`，`_checks_at` 直接 append 其返回值，**接线由 `res[10] == check_current_wording(PKG)` 断言**；反向用例只调该函数并只复制被检 5 文件，耗时 157s → 约 10s。
3. `tests/test_gate_fuzz.py` 新增 `_wording_counts(src)`：`total` 只在 `main()` 体内取（避开 docstring 自证），并加「仅改 `main()` total 必被抓」反向断言；实测 `('15','15')` → 改 main 后 `('14','15')`。
4. 反向金丝雀扩为**逐锚回退**：13 个正向锚逐个摘除 + 3 个旧口径串逐个注入，共 16 次，每次断言第 11 项真实 FAIL。
5. 文档订正：CHANGELOG [1.5.11]（明确 [1.5.10] 段 ③④ 为历史声称）、CLAUDE v1.5.11 订正节、LEARNINGS LRN-028、守卫/fuzz docstring；本仓 v1.5.10 治理同步文档末尾追加订正标注（保留原文）；删除已无用的 `shutil` import。

## 循环轨迹

1. 第 1 轮：终验盲检 3 项 → 施工 → 新增用例真跑 157s，性能不可接受。
2. 第 2 轮：抽独立函数 + fixture 收窄为被检 5 文件 → 约 10s；`pytest --durations` 定位显示大头是既有的 `test_gate_fuzz`(28s) / `test_vendor_core`(16s)，全套耗时随环境负载浮动（75~93s）。未放宽任何断言。
3. 第 3 轮：文档里写死的全套秒数会随负载失效 → 改为「约 10s / 全套 18 passed」不写死；manifest 漂移重生成 → 全量复验 → 定版。

## 终验基线

pytest **18 passed** ｜ fuzz **60/60**（45 CASES + 15 行为级）｜ 守卫 **11/11** ｜ V7 **7/7** ｜ contracts / scope / manifest `--check` 全绿（79 文件）｜ 21 脚本（19 py + 2 sh）编译/语法 + `--help` 全过 ｜ 四处 version = **1.5.11** ｜ `check_decision_records.py` `EXIT=0/OK` ｜ 决策台账 `HEALTHY/EXIT=0`（**14** 条，0 天）。

包外锚：21/21 一致、`source.commit == HEAD`、`refresh_history=3`、本仓 `anchor_refresh_log.jsonl` 3 行；篡改演练：改一个 sha → `5/DRIFT`，改 `source.commit` → `3/ANCHOR_SCHEMA_INVALID`（提示「疑改锚刷绿」），真锚字节未变。系统 crontab 中 B-5 行数 = 0。

## 发布链

- 专家包：commit `9d27e63ccda29d44e737a222fec3898ed0123a2a`（9 files / +188 −82）+ 轻量 tag `v1.5.11` → `origin/main` / tag，`git ls-remote` 同 hash，clean。
- research-ops：本文件 + `decision_log.csv`（+1 条真实裁决，13 → 14）+ `anchor_refresh_log.jsonl`（+1 行）+ v1.5.10 治理同步文档末尾订正标注 → `origin/research-ops-track`。
- 审计区（无 git）：`AUDIT_STATE.md` §17（§15/§16 原文保留 + 证伪标注）、`BASELINE_ANCHORS.json`（21 文件 / v1.5.11）；`.workbuddy/memory/2026-11-10.md` 与 `MEMORY.md` 已同步。

## 真实边界（非未完成缺陷）

- 同 v1.5.9 / v1.5.10：G6 默认不强制（ADR-002）、系统 crontab 零改动、包内脚本永不代写台账、语义逐条终裁属人工 T2、`--require-tag` 保持默认关闭（ADR-001）、包外锚刷新仍为人工 ACK 动作、联邦 shared-core / vendor 未改。
- ⚪ 负锚只禁精确串 `mkdir 原子锁`，`mkdir 目录锁` 变体理论上可绕过该负锚；但同文件正向锚 `noclobber（O_EXCL）文件锁` 会同时消失 → 第 11 项仍 FAIL，构成双保险。
- ⚪ 守卫第 11 项只锚 5 个固定文件，不覆盖 `CLAUDE.md` 历史节与代码注释中的旧口径字样；按「只订正无版本标注的活跃条款」纪律保留，不构成当前状态声明。
- 历史文本纪律：§15 / §16 的「零挂账」原文保留 + 证伪标注；CHANGELOG [1.5.10] 段 ③④ 保留为历史声称，由 [1.5.11] 节明确订正。

## 结论

v1.5.10 的三处自审漏洞全部施工闭合，防线不再依赖收轮节自述；循环 3 轮至全绿，两处 GitHub 分支与本地工作区均为最新版本。**零挂账。**
