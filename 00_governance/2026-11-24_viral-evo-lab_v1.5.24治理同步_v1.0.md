# viral-evo-lab v1.5.24 治理同步 · 2026-11-24

## 轮次
R4.5 主代理对抗自验轮（v1.5.23 冻结声明前的独立压测）。

## 基线
- 专家包 commit `4ba69a9`（docs 补记）/ 版本 tag `v1.5.24`（打在代码 commit `01ff17f`）/ 已 push origin/main。
- 上一基线 v1.5.23 `292d6a7`。

## 本轮发现与修复（主代理独立复现）
v1.5.23 后主代理对抗压测发现**漏网 fail-open**：`n = 1 2 3`（数字被**空白**拆段）→ `n_eq` 正则 `\d{2,6}` 失配 → `checked=0 → PASS/EXIT=0`。

- **根因**：两道防线各留半扇门——`has_split_number` 正则 `[^\d\s]` 只管非空白隔断，放行空白；`has_broken_key_pattern` 只看「标记后首字符是否数字」，`n = 1 2 3` 首字符是 `1` 即判正常。
- **修复**：单一事实源 `has_broken_key_pattern` 增第二判据——标记后首个数字 token 紧跟「空白 + 数字」即判隔断（`^\d{1,6}(?:\.\d+)?\s+\d`）→ EXIT=3。三消费方（`verify_numbers` / `verify_member_output` / `check_gates` G2）经单一事实源自动生效。
- **精确对照不误伤**（全部实测）：`n = 5`（min_digits=2 有意跳过）→ EXIT=0；`n = 30 例`、`p = 0.05 vs 0.01` → 不误判隔断；`CI [0.1, 0.2]`（逗号非空白）→ 正常解析 EXIT=5（未溯源）；`-W error` 下攻击 EXIT=3 且无 SyntaxWarning（docstring 改 raw string 消除 `\d` 无效转义）。

## 修复纪律
- 回归断言复用既有 `test_require_tag_gate`（新增第 4 变体「空白拆段数字」），零新增函数 → 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` **零联动**。
- fail-closed 方向：隔断即拒（EXIT=3），不放行不完整证据。

## 终验
pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` EXIT=0（**80 文件**）/ 包外锚 **22/22 一致** / 四处 version=1.5.24 / py_compile 全过 / `-W error` 攻击与合法对照通过。

## 并行会话改动并入（如实标注）
本版本工作树同时带有 C19 跨包根治（Agent Harness 战线，`2026-11-22` A-2/N1 `resolve_skill_paths` 未知技能 fail-loud，5 包 vendor 逐字节同步），涉及 `scripts/assemble_spawn_prompt.py` 与 `vendor/shared-core/{assemble_spawn_prompt.py,VENDOR.json}`。经确认属用户并行会话有意工作：`test_vendor_core.py` 哈希守卫全链通过（声明 hash 与实际逐字节一致），合法技能解析结果不变。CHANGELOG 已补记说明，避免版本叙事漂移。

## 包外基线锚
按受控流程：刷前 **DRIFT/EXIT=5**（含 `assemble_spawn_prompt.py` 漂移——正因上述并行改动）→ `--refresh --i-acknowledge-refresh --reason` + `--git-log` 双位置追加 → 刷后 **22/22 OK/EXIT=0**，治理仓 `anchor_refresh_log.jsonl` 同步 +1 行。

## 已知口径限制（延续上轮记录）
锚 `source.tag` 字段在「HEAD 越过版本 tag 的 docs commit」时回退显示旧 tag（本轮显示 `v1.5.23`，实际版本 `v1.5.24`）。commit 溯源 `4ba69a9` 准确，`check_baseline_anchors.py` 不校验 tag 语义，机器锚有效性不受影响。根治方向：版本化时做到「代码 commit == tag commit == 最终 HEAD」，本轮因事后补记 docs 未能满足，记录待后续版本收敛。

## 冻结声明
本轮为 v1.5.23 冻结声明前的补漏轮。两路独立盲检（通用 + 对抗性）已随上轮会话中断丢失，须在 v1.5.24 基础上**重新派发**并取**连续两轮零🔴**方可恢复冻结（见 R4_SUMMARY.md §5）。
