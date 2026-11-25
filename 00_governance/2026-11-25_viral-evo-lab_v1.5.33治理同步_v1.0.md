# viral-evo-lab v1.5.33 治理同步（R4.16）

- 日期：2026-11-25
- 专家包 commit：`69cdafa`（= tag `v1.5.33` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.32` / `d2089d9`

## 1. 本轮触发

v1.5.32 盲检 A（前台同步，报告送达）报 3🔴+2🟠。主代理逐条独立复现 3🔴 全部坐实后修复；2🟠 评估为不放行恶意输入且修之会误拒存量产出，披露不修。

## 2. 修复清单（3🔴）

| 编号 | fail-open 形态 | 实测 | 根因修复 |
|---|---|---|---|
| A1 | `ɲ=888`/`ŋ`/`ϕ` 同形声明零提取 | checked=0/PASS（G2 传导 PASS）→ EXIT=3 | Unicode 名称语义判定 `has_homoglyph_declaration`（LATIN/ARMENIAN/GREEK N/P/PHI 同形），预组合 ń 经 NFD 转 ASCII 者跳过 |
| A2 | `n=94` 被池 `94e5`/`94%`/`94kg` 洗白 | found=1/PASS → EXIT=5 | 整数右边界追加禁 `\w`/`%` 后缀；CSV 字段正常溯源 |
| A3 | `轮ɲ次耗尽` 撞限字母隔断 | READY/EXIT=0 → EXIT=5 | `normalize_for_matching` 剥非 ASCII Ll/Lu/Lt/Lm，保留 Lo(CJK) |

## 3. 🟠 已知限制（不阻塞）

- G4 `artifact_mtimes` 缺条目不判篡改（攻击者尚需其他门禁全绿；强制条目会误拒存量）。
- `check_baseline_anchors` `bytes:true`（bool 是 int 子类）当合法整数（sha256 仍匹配，不影响防篡改）。

## 4. 验证与纪律

- 全链：manifest 80 / pytest 19 / fuzz 61/61 / 守卫 11/11 / compileall / 四处 version=1.5.33 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（3 项回归断言复用既有两函数，零新增函数）。
- 合法对照（预组合 ń / CSV 双字段 / 中文撞限 / 普通 n=94）全过无误伤。

## 5. 冻结状态

**未冻结**。v1.5.33 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。
