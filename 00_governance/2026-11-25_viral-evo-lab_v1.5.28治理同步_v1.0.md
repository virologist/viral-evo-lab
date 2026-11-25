# viral-evo-lab v1.5.28 治理同步（R4.9 + R4.10）

- 日期：2026-11-25
- 专家包 commit：`aed27ed`（= tag `v1.5.28` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.27` / `88fe487`

## 1. 本轮触发：v1.5.27 冻结前双路独立盲检非零🔴

| 路线 | 结论 | 主代理独立复现 |
|---|---|---|
| A（通用无预设） | 5🔴 + 4🟠 | 4 项坐实（🔴1 超大整数与主代理自查合并） |
| B（对抗性红队） | 2🔴 + 3🟠 | 2🔴 + 3🟠 全部坐实 |

## 2. 修复清单（7🔴 + 4🟠）

### 🔴
1. **B🔴1 不可见字符隔断声明**：ZWJ(U+200D)/VS16(U+FE0F) 插在 `p/n` 与 `=` 之间 → `checked=0/PASS`。新增 `_MARKER_GAP` 判「标记与 =/: 之间夹 Cf/Mn」→ fail-closed EXIT=3；合法 emoji ZWJ 不误伤。
2. **B🔴2 同形字/多语百分号**：`п=94`/`η=94`/`95٪` → `checked=0/PASS`。`_EQUIV_TRANS` 扩同形字 + 多语 `%`。
3. **A🔴2 min-digits 关闭守卫**：`--min-digits 1` + `p = 0,94` → PASS。守卫改为独立于 min_digits。
4. **A🔴3 n_eq 截断洗白**：`n = 1234567` + 池中 `123456` → PASS。`\d{2,6}` 加右边界。
5. **A🔴4 pct 截断洗白**：`1234%` + 池中 `234` → PASS。`\d{1,3}` 加左边界。
6. **A🔴5 V1 装配零告警**：`_v1_extract` 自带正则副本无守卫 → `p = 0,94` 静默跳过。改走 `prepare_numbers` 单一入口 + 哨兵告警；修三元组解包。
7. **A🔴1/B🟠3 超大整数契约外 EXIT=1**（主代理自查合并）：8 处 `json.loads` 漏捕获 `ValueError` → 统一扩捕获面。

### 🟠
- **B🟠4** CSV 双数字字段 `30,0.9441` 误降级 → pool 逗号边界精细化（仅整数候选前逗号紧邻数字才算延续）。
- **A🟠6** `check_scope` 事故值全角 → 扫描前 `normalize_for_extraction`。
- **A🟠7** cron manifest 含非法 task_id → 静默 exit 0 改为 EXIT=3；空 manifest 仍 exit 0。
- **A🟠8** CI/dprime 个位整数部分误拒 → `\d\.\d+` 扩为 `\d{1,3}\.\d+`。
- A🟠9（机器锚口径）：既有守卫 + manifest 双重覆盖，本轮不额外放宽。

## 3. 验证与纪律

- 全链：manifest 80 文件 `--check` EXIT=0 / pytest 19 passed（含 `-W error`）/ fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version = 1.5.28 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（回归断言复用既有两函数，零新增函数）。
- 变异测试：回退 min-digits 守卫短路后断言即失败，真包通过 → 新断言非空转。
- 包外锚 `source.tag=v1.5.28`，`anchor_refresh_log.jsonl` 已留痕（commit==tag==HEAD 先刷新）。

## 4. 冻结状态

**未冻结**。按纪律，v1.5.28 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。
