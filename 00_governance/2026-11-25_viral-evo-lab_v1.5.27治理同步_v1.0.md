# viral-evo-lab v1.5.27 治理同步（R4.8）

- 日期：2026-11-25
- 专家包 commit：`88fe487`（= tag `v1.5.27` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.26` / `37a3990`

## 1. 本轮触发：v1.5.26 冻结前双路独立盲检非零🔴

| 路线 | 结论 | 主代理独立复现 |
|---|---|---|
| A（通用无预设） | 3🔴 + 4🟠 | 3/3 全部坐实，0 证伪 |
| B（对抗性红队） | 2🔴 + 2🟠（基于 `git show 37a3990` 纯净基线） | B🔴1 与 A🔴1 同源并修；B🔴2 独立坐实；2🟠 坐实 |

## 2. 修复清单（4🔴 + 4🟠）

### 🔴
1. **A🔴1 守卫/提取正则口径漂移**：`_DECL_SPEC.full_re` 与 `PATTERNS` 双份正则（大小写、`[=:]`、CI 可选分隔符）不一致，11 变体（小写 `d'`/`ci`、`CI:`、`p:`、西里尔 `СІ`）`checked=0 → PASS`。根治：`_DECL_SPEC.full_re` 直接复用 `_PAT_BY_KIND` 同一对象；`_EQUIV_TRANS` 补西里尔同形字映射。
2. **A🔴2 超大整数 JSON → 契约外 EXIT=1**：>4300 位整数抛 `ValueError`（非 `JSONDecodeError`），6 处 except 漏捕获，`e.msg` 二次 `AttributeError`。统一扩捕获面 + `str(e)`，退化为 EXIT=3 结构失败。
3. **A🔴3 `check_scope` `\b` CJK 漂移**：`1094\b` / `0\.2058\b` 在 CJK 紧邻处不成立，事故值误判 clean。改 `(?![0-9A-Za-z])`。
4. **B🔴2 冒号隔断未同步**：`n: 1 2 3` → `checked=0/PASS`（等号形式 rc=3）。`KEY_MARKERS` 同步 `[=:]`，与提取/小 n 判定第三处口径对齐。

### 🟠
- **B🟠3 逗号边界过严 fail-close**：v1.5.26 把 CSV 字段分隔符逗号当数字延续，`p,0.11` 合法值误降级。改为「仅前后紧邻数字时逗号才算延续」，欧洲小数/千分位洗白仍拦。
- **A🟠1** `cron_watch.sh` 参数缺值在 `set -u` 下 unbound → EXIT=1；改先判 `$# >= 2` → EXIT=3。
- **A🟠2** `check_scope` 治理正本豁免从 basename 相等改为包内规范路径精确匹配。
- **A🟠3** `assemble_spawn_prompt._V1_PATTERNS` 与 `verify_numbers.PATTERNS` 逐条同源。

## 3. 验证与纪律

- 全链：manifest 80 文件 `--check` EXIT=0 / pytest 19 passed（含 `-W error`）/ fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version = 1.5.27 / 包外锚刷前 DRIFT EXIT=5、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（回归断言复用既有 `test_require_tag_gate()` / `test_decision_records_guard()`，零新增函数）。
- 变异测试：回退 CSV 逗号边界 / 冒号隔断后对应断言即失败，真包通过 → 新断言非空转。
- 包外锚 `source.tag=v1.5.27`，`anchor_refresh_log.jsonl` 已留痕（commit==tag==HEAD 先刷新）。

## 4. 冻结状态

**未冻结**。按纪律，v1.5.27 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。冻结前任何改动必须重新版本化并刷新包外锚。
