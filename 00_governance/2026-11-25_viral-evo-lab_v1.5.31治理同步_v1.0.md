# viral-evo-lab v1.5.31 治理同步（R4.14）

- 日期：2026-11-25
- 专家包 commit：`f76d9fc`（= tag `v1.5.31` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.30` / `43a0af3`

## 1. 本轮触发

v1.5.30 盲检 A 改用**前台同步调用**，报告正文实际送达（规避 v1.5.29 轮后台 agent 报告丢失）。报 7🔴 + 若干🟠。主代理逐条独立复现 7🔴 全部坐实（checked=0/PASS、found=1/PASS、valid=2/PASS 实证）后修复。

## 2. 修复清单（7🔴）

| 编号 | fail-open 形态 | 实测 | 根因修复 |
|---|---|---|---|
| A1 | Sm/Pd/Po 劈开数字前缀被池洗白（`88⬰88`/`0.9⬰4`/`94～500`） | found=1/PASS → EXIT=3 | `_SPLIT_BAD_CATS` 扩全 S*/P*/M*/C* + ASCII 合法分隔符放行；`_SPLIT_NUM` 右侧改正向前瞻修贪心消耗 |
| A2 | 预组合 ń/ṕ、希腊 ν 声明隐身 | checked=0/PASS → EXIT=5 | NFD 分解→剥 Mn→映射→NFKC + ν/ο 同形映射 |
| A3 | prime 变体 d´/dʹ/d‵ 声明隐身 | checked=0/PASS → EXIT=5 | `_EQUIV_TRANS` 扩 8 个 prime/acute 变体，NFD 前先映射 |
| A4 | `n=94` 被池 `94,5000` 洗白 | found=1/PASS → EXIT=5 | 右边界 `(?!,\d+(?!\.))` 任意位数千分位拦，CSV 浮点字段放行 |
| A5/A6 | check_scope `10⬰94` / poll `轮⬰次耗尽` 隔断 | clean/READY → EXIT=3/5 | `normalize_for_matching()` 剥 S*/P*，两处共用 |
| A7 | G6 `line=true` 被当合法行号 | valid=2/PASS → EXIT=5 | 显式排除 bool（int 子类） |

## 3. 🟠 fail-close 已知限制（不阻塞冻结）

`CI [+0.1,+0.2]` / `d′=+0.94` / `p=1.2e-3`(池 0.0012) / `0.9441` vs `0.944100000` / `n=1234` vs 池 `1,234` 均误拒合法输入（EXIT=3/5），但不放行恶意输入；按 fail-open 优先不修，披露为限制。

## 4. 验证与纪律

- 全链：manifest 80 / pytest 19 / fuzz 61/61 / 守卫 11/11 / compileall / 四处 version=1.5.31 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（7 项回归断言复用既有三函数，零新增函数）。
- 中途三次 fail-close 误伤（全角逗号 CI / 多语小数点 `·` / 全角波浪 `～`）均加等价分隔符放行判据消除，合法对照全过。

## 5. 冻结状态

**未冻结**。v1.5.31 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。下一轮继续前台同步盲检确保报告送达。
