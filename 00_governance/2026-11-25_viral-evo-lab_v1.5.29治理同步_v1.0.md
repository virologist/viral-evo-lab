# viral-evo-lab v1.5.29 治理同步（R4.11 + R4.12）

- 日期：2026-11-25
- 专家包 commit：`794c876`（= tag `v1.5.29` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.28` / `aed27ed`

## 1. 本轮触发：v1.5.28 冻结前双路独立盲检非零🔴

| 路线 | 结论 | 主代理独立复现 |
|---|---|---|
| A（通用无预设） | 2🔴 + 2🟠 | 2🔴 全部坐实（🔴1 用盲检原 fixture 真包 EXIT=0 → 副本 EXIT=3） |
| B（对抗性红队） | 3🔴 + 3🟠 | 🔴1/🔴3 + 🟠5/🟠6 坐实；另主代理自查补 V1 降级 fail-open |

## 2. 修复清单（5🔴 + 3🟠）

### 🔴
1. **A🔴1 台账 UTF-16BE 静默放行**：`redteam_ledger.csv` 以 UTF-16BE 无 BOM 编码时，NUL 在 UTF-8 下合法 → 裸 `open(utf-8-sig)` 吞入 → 列名污染 → fatal 证伪被当 CLEAN（EXIT=0，fail-open）。改用 `_text_guard.read_text_checked()` 严格读 → 污染 EXIT=3。
2. **A🔴2 多语小数点截断洗白**：`p = 0٫94`（U+066B）等 NFKC 不收敛 → 提取为 `0` 被池中 `0` 洗白 PASS。`_EQUIV_TRANS` 补语义等价映射（U+066B/00B7/30FB/FF61/2022/06D4/0387/2027/FF0E → `.`；U+066C 阿文千分位 → `,`）；NFKC 将 `｡`→`。` 致 `30。5` 截断者，`prepare_numbers()` 加 `\d。\d` 定点 fail-closed，合法中文句读不误伤。
3. **B🔴1 `_MARKER_GAP` 漏检**：Cf/Mn 隔断区间有限、未覆盖 CI 括号形态 → 扩展为全区间 Cf/Mn + CI `（` 检测。
4. **B🔴3 cron JSONL 被吞**：`json.load()` 只能读单行，多行 JSONL 报 Extra data 被 except 吞掉 → 非法 task_id 静默跳过。改逐行 `json.loads()`，含 task_id 字段却全非法 → EXIT=3；空 manifest 仍 EXIT=0。
5. **主代理自查 V1 降级 fail-open**：`_load_verify_numbers()` 返回 None 时降级路径无守卫，`p = 0,94` / `n = 1 2 3` 静默跳过。补本地守卫 + `split_number` 哨兵进 unverified。

### 🟠
- **B🟠5** CSV 三列字段 `1,0.94,2` 被逗号边界误当延续 → pool 边界精确化（仅整数候选前逗号紧邻数字才算延续）。
- **B🟠6** 合法小 n `n = 5，结果 p = …` / 千分位 `n = 1,234` 被误拒 → 扩豁免 + `n_eq` 千分位去逗号，仍拦 `n = 5，94` 滥用。
- **A🟠 `--all` 文档**：口径与 CLI 一致，本轮不额外改码。

## 3. 验证与纪律

- 全链：manifest 80 文件 `--check` EXIT=0 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version = 1.5.29 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（回归断言复用 `test_require_tag_gate()` / `test_disposition_gate()` 两既有函数，零新增函数）。
- 多语小数点矩阵实测：修复前 7 变体 rc=0（fail-open）→ 修复后中点/阿文小数点 rc=5（正确提取未溯源）、中文/半角句点 rc=3（定点 fail-closed）、合法中文句读不误拒。
- 包外锚 `source.tag=v1.5.29`，`anchor_refresh_log.jsonl` 已留痕（commit==tag==HEAD 先刷新）。

## 4. 冻结状态

**未冻结**。按纪律，v1.5.29 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。
