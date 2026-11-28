# viral-evo-lab v1.5.40 治理同步（R4.23）

- 日期：2026-11-28
- 专家包 commit：`992fc4b`（= tag `v1.5.40` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.39` / `2821460`

## 1. 本轮触发

v1.5.39 两路独立盲检（前台同步，报告均送达）：A 通用无预设 4🔴+3🟠，B 对抗红队 3🔴+4🟠，去重后 5 组。主代理逐条自建 fixture + 真实 CLI 独立复现并设正字对照，**5/5 全部坐实、零证伪**。核心教训：**R4.22 的根因级修复本身留下邻界遗漏**——时间证据链只修基准字段（last_updated）未修复核字段（reviewed_at）、守卫正则词边界（\b）与提取正则（(?<![A-Za-z])）口径漂移、真值别名值解析仍是字面枚举、双实现各取一次 JSON、兼容区剥离放在 NFKC 之后成死代码。根治统一收敛为**同一事实源 + 语义求值 + 前置剥离 + 括号配平**。

## 2. 修复清单

| 项 | fail-open 形态 | 修复前 → 后 | 根因修复 |
|---|---|---|---|
| A-1 | `reviewed_at=2099` 未来复核使超期验收恒真 | OK/0 → 6 | 复核是已发生事实，未来时刻不可信，与 future_pool 同口径 fail-closed |
| A-2 | `样本n = 30′5`（CJK 紧邻）正则 \b 失配提取取 30 洗白 | PASS/0 → 3 | 守卫词边界统一为 `(?<![A-Za-z])`，与提取侧单一口径 |
| A-3/B-1 | `default=0.5`/`-1`/`"1"`/`[1]`/超长 help 挤出 default 绕过形态锚 | OK/0 → 5 | 参数块括号配平（无长度上限）+ `ast.literal_eval` 语义求值，求不出保守判真 |
| A-4/B-3 | V5 围栏+前置散文使预检与 vendor 各取一次 JSON 口径漂移 | OK/0 → 4 | 加载器返回 vendor 整个模块，预检复用 `_extract_task_json` 单一事实源，解析失败 fail-closed |
| B-2 | CJK 兼容字 U+F900 隔断 check_scope 黑名单（R4.22 后置排除是死代码） | clean/0 → 3 | 抽 `strip_cjk_compatibility()` 在 NFKC 前剥除，matching/cjk_keyword 两通道共用 |

## 3. 🟠 披露不修（沿用既有边界）

- tag-only 锚（source 无 commit 键）、gate_mode 键缺失、audit 台账 NUL 污染、G4 远期过去 ts —— 均为 R4.22 已披露的既有豁免边界，本轮复核仍成立，不重复计入新发现。

## 4. 验证与治理闭环

- pytest **19 passed** / fuzz 行为级 **61/61**（机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级` 不变）/ manifest `--check` EXIT=0（**80 文件**）/ compileall OK。
- 回归断言复用既有 `test_gate_fuzz` / `test_decision_records_guard` 函数，零新增 `def test_*`。
- 正字对照全过：近期 reviewed_at→OK/0、行首 prime 复合→3、纯污染 PP41034380→3、default=False→OK/0、裸 JSON 类型混淆→4。
- 包外锚：刷前正确报 DRIFT（2 文件 + commit 断裂），受控刷新后 **22/22 OK/EXIT=0**。
- 两仓终态：专家包 `992fc4b`=origin/main=tag v1.5.40；治理仓本轮同步后=origin/research-ops-track。
- 冻结状态：⏳ 未冻结——待 v1.5.40 基础上连续两轮独立盲检零🔴。
