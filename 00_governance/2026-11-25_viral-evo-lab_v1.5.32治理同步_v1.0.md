# viral-evo-lab v1.5.32 治理同步（R4.15）

- 日期：2026-11-25
- 专家包 commit：`d2089d9`（= tag `v1.5.32` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.31` / `f76d9fc`

## 1. 本轮触发

v1.5.31 盲检 A（前台同步，报告送达）报 6🔴+0🟠。主代理逐条独立复现全部坐实（PASS/CLEAN/READY 实证）后修复。6 项分两类根因：ZWJ(Cf) 隔断关键 token；上轮劈开检测修复引入/遗留的三缺陷。

## 2. 修复清单（6🔴）

| 编号 | fail-open 形态 | 实测 | 根因修复 |
|---|---|---|---|
| A1 | `轮‍次耗尽` → poll READY/EXIT=0 | READY → EXIT=5 | `has_forbidden` ZWJ span 左右 `isalnum()` 即拒；`normalize_for_matching` 全剥 Cf |
| A2 | `位‍置映射错` → check_scope clean | clean/EXIT=0 → EXIT=3 | 同上双防线 |
| A6 | `fatal‍` severity → fatal 证伪静默 CLEAN | CLEAN/EXIT=0 → EXIT=3 | 字母侧 ZWJ 严格读拒绝（证据源污染） |
| A3 | `94×9×7`（9 分隔符）→ 前缀洗白 | found=1/PASS → EXIT=3 | `_SPLIT_NUM` 上限 `{1,8}` → `{1,64}` |
| A4 | `94,⬰7` 前置分隔符破坏 `all()` | PASS → EXIT=3 | core 剔除所有合法分隔符后再判 |
| A5 | `94\ue0007`(Co)/`94\u20dd7`(Me) 洗白 | PASS → EXIT=3 | `_SPLIT_BAD_CATS` 补全 Co/Cs/Mc/Me |

## 3. 验证与纪律

- 全链：manifest 80 / pytest 19 / fuzz 61/61 / 守卫 11/11 / compileall / 四处 version=1.5.32 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（6 项回归断言复用既有三函数，零新增函数）。
- 合法对照（1,234.5 / 10:30 / 10~20 / 20°C / 1e-3 / 多语小数点 / 全角逗号 CI / D′）全过，无 fail-close 误伤。

## 4. 冻结状态

**未冻结**。v1.5.32 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。
