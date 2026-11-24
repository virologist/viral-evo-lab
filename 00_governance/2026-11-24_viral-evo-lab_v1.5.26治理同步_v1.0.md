# viral-evo-lab v1.5.26 治理同步 · 2026-11-24

## 轮次
R4.7 双路盲检回补轮（v1.5.25 冻结声明被独立盲检推翻后的再回补）。

## 基线
- 专家包 commit `37a3990` / 版本 tag `v1.5.26` / 已 push `origin main` 与 tag。
- **代码 commit == tag commit == HEAD == 包外锚 source.commit**，v1.5.25 已达成的三点一致继续保持。
- 上一基线 v1.5.25 `45014b1`。

## 本轮发现与修复（全部主代理独立复现后采信）
v1.5.25 基础上两路独立盲检：A=1🔴+2🟠、B=5🔴+3🟠（交叉印证）。主代理逐条独立复现，**6🔴 全部坐实、零证伪**，另闭合 1🟠。

| 缺陷 | 复现实测 | 根因级修复 |
|---|---|---|
| A🔴 CJK 紧邻空白拆段 | `样本n = 1 2 3` → checked=0/PASS/EXIT=0；ASCII 对照 EXIT=3 | `KEY_MARKERS` 的 `\b` → `(?<![A-Za-z])`，与 PATTERNS 同口径 |
| B🔴1 诱饵短路总闸 | `n = 30（源有）, p = 0,94（伪造）` → PASS | 总闸从「nums 全空才查」改**逐声明判定** `_DECL_SPEC`，每条声明须有可解析数字形态 |
| B🔴2 G2 消费口径漂移 | 全角 `ｎ＝９９` 守卫过、G2 原始文本提取零命中 → PASS | `nums_by_art` 复用 `prepare_numbers` 归一化结果，守卫与消费同一口径 |
| B🔴3 逗号边界洗白 | `n = 94` 被池中 `0,94` 洗白 → PASS | `pool_has_number` 边界扩为「非数字/`.`/`,`」 |
| B🔴4 排版/同形字漏检 | `D’=0.94` / `CI【0.10, 0.20】` / `ρ=0.94` → checked=0 PASS | `_EQUIV_TRANS` 语义等价映射（弯引号/中文方括号/同形字 → ASCII） |
| B🔴5 小 n 豁免滥用 | `n = 5、94` → PASS | 收紧豁免：顿号/逗号后接数字不豁免，接字母声明仍合法 |
| B🟠 check_scope 双重子串豁免 | 目录 `GOVERNANCE_BOUNDARIES.md_evil/` 被整目录跳过 | `check_file` 与 `main.EXCLUDE` 均改文件名/路径段精确匹配 |

A🟠1（诱饵工艺）随逐声明总闸闭合；A🟠2（`n = 1 2` 等）随边界统一闭合；B🟠1（V1 逗号口径）随 pool 边界闭合。

## 修复纪律
- 回归断言全部复用既有 `test_require_tag_gate()` / `test_decision_records_guard()`，零新增函数 → 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` **零联动**。
- 6🔴 均经「复现 → 修复 → 反向对照三态」；合法对照（`n = 5，p = 0.111` / `n = 30 例` / `CI [0.1, 0.2]`）不误拒。

## 终验
pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` EXIT=0（**80 文件**）/ 包外锚 **22/22 一致** / 四处 version=1.5.26 / py_compile 全过 / 盲检一键复现脚本全项退出码回归。

## 包外基线锚
按受控流程：刷前 **DRIFT/EXIT=5** → `--refresh --i-acknowledge-refresh --reason` + `--git-log` 双位置追加 → 刷后 **22/22 OK/EXIT=0**，治理仓 `anchor_refresh_log.jsonl` 同步 +1 行，锚 `source.tag=v1.5.26` 准确。

## 冻结声明
本轮尚未冻结。须在 v1.5.26 基础上派两路独立盲检，每条🔴由主代理独立复现后采信，取得**连续两轮零🔴**方可恢复冻结并回填 `R4_SUMMARY.md` §5。
