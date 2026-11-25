# viral-evo-lab v1.5.30 治理同步（R4.13）

- 日期：2026-11-25
- 专家包 commit：`43a0af3`（= tag `v1.5.30` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.29` / `794c876`

## 1. 本轮触发与采信纪律

v1.5.29 双路盲检报 A=5🔴2🟠 / B=3🔴1🟠，但**报告正文因后台 agent 结束未送达主代理上下文**。按 LRN-028（自审须真读被校验对象）与「每条🔴须主代理独立复现才采信」铁律，**不凭计数采信**：主代理以对抗 payload 逐条独立复现，8 项 fail-open 全部坐实（含 checked=0/PASS、found=1/PASS、EXIT=1 崩溃、未来日期 CLEAN 等实证）；B2 经精确 fixture 二次复现后坐实。盲检计数仅作线索，不作为结论依据。

## 2. 修复清单（8🔴，全部独立复现）

| 编号 | fail-open 形态 | 实测（修前→修后） | 根因修复 |
|---|---|---|---|
| A1 | `p⬰=0.94`(U+2B30 Sm) / `p\u1AB0=` 区间外 Mn 隔断声明 | checked=0/PASS → EXIT=3 | `normalize_for_extraction` 先剥 Mn 再 NFKC；`has_invisible_marker_gap` 改 Unicode 类别动态判据（S*/C*/M*），弃码点区间枚举 |
| A2 | `n=94` 被池中 `94,500` 洗白 | found=1/PASS → EXIT=5 | 恢复整数候选右边界 `(?!,\d{1,3}(?![\d.,]))`，放行 CSV 浮点字段 `30,0.9441` |
| A3 | check_scope `10\u030194` 事故值漏检 | clean/EXIT=0 → EXIT=3 | 归一化剥 Mn 后匹配 |
| A4 | `CI ｛0.1,0.2｝` 声明隐身 | checked=0/PASS → EXIT=5 | PATTERNS/KEY_MARKERS/_DECL_SPEC/DECL_HINT/broken_key 五处加 `{}` |
| A5 | poll `轮\u0301次耗尽` 撞限标注漏检 | READY/EXIT=0 → EXIT=5 | 撞限判定走 `normalize_for_extraction()` |
| B1 | `p=0.94412` 被池中 `0.944` 洗白 | found=1/PASS → EXIT=5 | `float_candidates` 去截断候选，仅补零（精度不降） |
| B2 | 未来同日带毫秒 fatal 闭环静默吞 | CLEAN/EXIT=0 → EXIT=5 | 统一「同日即算晚于」判据 |
| B3 | `verification.rule=list/dict` 崩溃 | EXIT=1 Traceback → EXIT=3 | 字符串类型校验前置 |

## 3. 验证与纪律

- 全链：manifest 80 文件 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version=1.5.30 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（8 项回归断言复用既有四函数，零新增函数）。
- 合法对照（CSV 双字段 / CI 方括号 / 全角等号 / emoji ZWJ / 普通 p）不误拒；A1 修复中全角等号一度误伤，已改归一化文本扫描消除。
- 包外锚 `source.tag=v1.5.30`，刷前 commit==tag==HEAD 先验证 DRIFT 再受控刷新。

## 4. 冻结状态

**未冻结**。v1.5.30 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。上一轮盲检报告丢失已暴露「后台 agent 结论送达不可靠」风险，本轮盲检须确保报告正文实际送达后再据以判定，否则按主代理独立复现为准。
