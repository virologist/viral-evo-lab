# viral-evo-lab v1.5.21 治理同步 · 2026-11-20

## 轮次
R4.3 全面复测回补轮（用户授权「全面复测、持续迭代至全绿」）。

## 基线
- 专家包 commit `d69782b` / tag `v1.5.21` / 已 push origin/main（GitHub `virologist/viral-evo-lab`）。
- 上一基线 v1.5.20 `df852e2`。

## 本轮范围（用户要求：覆盖主要功能/关键流程/条件分支/边界/异常路径）
全面复测逐项独立复现 R4.2 两轮盲检报出的 7 项，全部坐实后修复：

| 编号 | 缺陷 | 实测 | 修复 |
|---|---|---|---|
| 🔴1 | `validate_contracts` version=list/dict → `set(values)` TypeError | EXIT=1 | 非字符串 version 记契约缺失 → EXIT=5 |
| 🔴2 | `hypothesis_watch` parse_dt 固定 strptime 不认小数秒 | severe 闭环漏报 EXIT=0 | 追加 fromisoformat 回退 → REVIEW_REQUIRED=5 |
| 🔴3 | `assemble_spawn_prompt` teamInfo 非对象 / members 元素非对象 | AttributeError EXIT=1 | 顶层+嵌套 isinstance 挡板 → EXIT=3/降级 |
| 🔴4 | `check_decision_records` cli_sites/tests 元素非字符串 | TypeError EXIT=1 | 记结构错误并跳过 → EXIT=3 |
| 🔴5 | `cron_watch.sh` `TASKS="$(python3 ...)"` 吞内联 py exit3 | 静默跳过 EXIT=0 | 捕获 $? 透传 → EXIT=3 |
| 🔴6 | `check_gates` 部分标注解除整段阻断 | G4 错误放行 | 标注须覆盖全部 unverified（对齐 waivers 纪律） |
| 🟠7 | Cf 一刀切误拒合法 emoji ZWJ 序列 | fail-close EXIT=3 | U+200D 两侧皆 emoji 精确放行，Cf 夹数字仍拒绝 |

## 修复纪律
- 回归断言全部复用既有测试函数（6 个），零新增函数；机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动。
- fail-closed 优先：所有畸形输入从「崩溃/静默放行」改为「契约内拒绝码」。
- 🟠7 白名单附安全论证：放行条件要求 ZWJ 两侧皆 emoji，数字/字母侧一律拒绝，无法用 ZWJ 分隔数字串造成 checked=0 fail-open。

## 终验
pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` EXIT=0（**80 文件**）/ 包外锚 **22/22 一致** / 四处 version=1.5.21 / py_compile 全过。

## 包外基线锚
按受控流程刷新：刷前正确报 DRIFT/EXIT=5（验证锚防护在真实流程生效）→ `--refresh --i-acknowledge-refresh --reason` 带 commit 溯源 → 刷后 22/22 OK。`BASELINE_ANCHORS.json` 落审计区（包外），refresh_history 记录本轮 commit `d69782b`。

## 冻结声明
本轮为冻结后改造轮，改动须连续两轮独立零🔴盲检方可恢复冻结（见 R4_SUMMARY.md §5）。
