# viral-evo-lab v1.5.34 治理同步（R4.17）

- 日期：2026-11-27
- 专家包 commit：`af57943`（= tag `v1.5.34` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.33` / `69cdafa`

## 1. 本轮触发

v1.5.33 新一轮盲检报告正文随会话压缩丢失，仅摘要残留 3 条具体变体。按「每条🔴主代理独立复现才采信」铁律，不凭丢失的计数，直接对 3 条变体逐条独立复现——全部坐实 fail-open 后根因级修复。报告未记全的第 4 项按纪律不凭空编造，留待下一轮盲检重新暴露。

## 2. 修复清单（3🔴，全部主代理独立复现）

| 编号 | fail-open 形态 | 实测（修复前→后） | 根因修复 |
|---|---|---|---|
| 1 | `ɣ=888`/`ס=888`/`ɲ\u0301=888` 同形声明零提取 | checked=0/PASS、EXIT=0 → EXIT=3 | `_is_np_homoglyph` 从名称枚举 N/P/ENG/PHI 改为「任意非 ASCII 字母（L*），排除 CJK/假名/韩文」；`prepare_numbers` 归一化后再判一次同形（Mn 隔断双向覆盖） |
| 2 | `n=94` 被池 `94·5`/`94٫5` 洗白 | found=1/PASS、EXIT=0 → EXIT=5 | `pool_has_number` 对权威池统一走 `normalize_for_extraction`（`94·5`→`94.5` 后整数右边界遇 `.` 即拒），四处调用方同口径单一事实源 |
| 3 | `轮\u0903次耗尽`（Mc）/`轮\u20dd次耗尽`（Me）撞限隔断 | READY/EXIT=0 → EXIT=5 | `normalize_for_matching` drop_cats 补全全 M*（Mn/Mc/Me） |

合法对照全过无误伤：ASCII `n=888`、预组合 `ń=94`（NFD→ASCII 豁免）、纯池中整数 `94`、CSV 浮点字段 `30,0.9441`、中文撞限词。

## 3. 🟠 已知限制（沿用，不阻塞）

- G4 `artifact_mtimes` 缺条目不判篡改（攻击者尚需其他门禁全绿；强制条目会误拒存量）。
- `check_baseline_anchors` `bytes:true`（bool 是 int 子类）当合法整数（sha256 仍匹配，不影响防篡改）。

## 4. 验证与纪律

- 全链：manifest 80 / pytest 19 / fuzz 61/61 / 守卫 11/11 / compileall / 四处 version=1.5.34 / 包外锚刷前 DRIFT EXIT=5（5 漂移）、受控刷新、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（3 项回归断言复用既有 `test_require_tag_gate` / `test_poll_hitlimit_and_manifest` 两函数，零新增函数）。
- commit==tag==HEAD=`af57943`，main + tag 均已 push。
- 锚刷新日志：`anchor_refresh_log.jsonl` 追加 v1.5.34 条目（commit af57943 / tag v1.5.34 / 变更 5 文件）。

## 5. 冻结状态

**未冻结**。v1.5.34 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。已连续多轮每轮盲检均报新🔴（攻击面持续暴露），收敛判据不变。
