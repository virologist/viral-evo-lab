# viral-evo-lab v1.5.25 治理同步 · 2026-11-24

## 轮次
R4.6 全面复测回补轮（v1.5.24 冻结声明后重启两路独立盲检）。

## 基线
- 专家包 commit `45014b1` / 版本 tag `v1.5.25` / 已 push `origin main` 与 `origin v1.5.25`。
- 本轮**代码 commit == tag commit == HEAD**，解决 v1.5.24 同步文档记录的「HEAD 越过 tag 致锚 source.tag 回退旧版」口径限制；锚刷新确认 `tag v1.5.25`。
- 上一基线 v1.5.24 `4ba69a9`（docs）/ `01ff17f`（代码）。

## 本轮发现与修复（全部主代理独立复现后采信）
R4.5 后重启两路独立盲检：A=9🔴+1🟠、B=6🔴+2🟠。主代理逐条独立复现，确认 **13 个 Unicode/声明 fail-open 变体**全部 `rc=0 / checked=0 / PASS`；另复现 5 项结构性缺陷；证伪 1 项（`verify_member_output` 无权威源，实测 EXIT=5，不修）。

### 根因级（V 层）
- **码点枚举不可穷尽**：全角数字/等号/百分号、圈号数字（`①` 满足 `isdigit()` 但 `\d` 不匹配）、上标数字、不同语言小数点、全角方括号 CI，均使数字正则静默失配 → `checked=0 → PASS`。
- **治理**：`_text_guard.normalize_for_extraction()`（NFKC，仅用于提取前）；`DECL_HINT` / `_SMALL_N_DECL` / `has_declaration_without_number()` 判「有数字声明但零提取」→ EXIT=3；`prepare_numbers()` 收拢隔断检测→归一化→总闸→提取，三消费方（`verify_numbers` / `verify_member_output` / `check_gates` G2）同口径。
- 干净小 n（`n = 5` 后接空白/句读/行尾）保留豁免；组合攻击 `n = 1-2-3` / `n = 1©…©2` 仍拦。

### 结构性（逐项实证复现）
1. `assemble_spawn_prompt` 子串洗白（`0.94` 命中 `0.9441`）→ 复用 `verify_numbers.pool_has_number()` token 边界匹配，加载失败降级为等价边界正则（不回退子串）。
2. `check_scope` md 标题整行跳过 → 仅治理正本 `GOVERNANCE_BOUNDARIES.md` 注释行豁免，其余标题照常扫描。
3. `validate_contracts` 删除全部 agents 仍 PASS → `MIN_AGENTS = 9` 硬门，缺员 → EXIT=5。
4. `hypothesis_watch` 单元格尾空格（`fatal ` / ` closed`）漏判 + 空/不可解析 `closed_date` 静默跳过 → `_row_str()` strip；closed fatal/severe 空日期计入 `late_fatal`。
5. `poll_run_dir` 200k 截断致后段撞限标注漏检 → 移除 `max_chars=200000`，全文严格读。
6. `cron_watch.sh` bash 3.2 全角右括号紧贴 `$LOCK` → `unbound variable` EXIT=1（契约仅 0/3/5）→ 改 `${LOCK}`。

## 修复纪律
- 回归断言全部复用既有 `test_require_tag_gate()` / `test_poll_hitlimit_and_manifest()` / `test_decision_records_guard()`，零新增函数 → 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` **零联动**。
- fail-open 优先修：声明存在但零提取即拒，不放行不完整证据。

## 终验
pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` EXIT=0（**80 文件**）/ 包外锚 **22/22 一致** / 四处 version=1.5.25 / py_compile 全过。

## 包外基线锚
按受控流程：刷前 **DRIFT/EXIT=5**（10 项漂移）→ `--refresh --i-acknowledge-refresh --reason` + `--git-log` 双位置追加 → 刷后 **22/22 OK/EXIT=0**；治理仓 `anchor_refresh_log.jsonl` 同步 +1 行，锚 `source.tag=v1.5.25` 准确。

## 冻结声明
本轮尚未冻结。须在 v1.5.25 基础上重新派发两路独立盲检（A=通用无预设 / B=对抗性红队），每条🔴由主代理独立复现后采信，取得**连续两轮零🔴**方可恢复冻结并回填 `R4_SUMMARY.md` §5。
