# viral-evo-lab v1.5.23 治理同步 · 2026-11-20

## 轮次
R4.4 复核回补轮（R4.3 冻结后重启两路独立盲检 → 采信项全修）。

## 基线
- 专家包 commit `292d6a7` / tag `v1.5.23` / 已 push origin/main（GitHub `virologist/viral-evo-lab`）。
- 上一基线 v1.5.22 `bdae771`；再上 v1.5.21 `d69782b`；v1.5.20 `df852e2`。

## 本轮范围（用户要求：覆盖主要功能/关键流程/条件分支/边界/异常路径）
R4.3 冻结后重启两路独立盲检（通用 A + 对抗性 B）。通用盲检报 0🔴/2🟠 后在 v1.5.22 复核追加 1🔴；对抗性盲检报 3🔴 + 4🟠。主代理**逐条独立复现**后采信 6 项（3🔴 + 3🟠）、**证伪 1 项**，另有 1🟠 由两路交叉印证：

| 编号 | 缺陷 | 实测 | 修复 |
|---|---|---|---|
| 🔴1 | 数字被符号类字符劈开 → 数字正则静默失配 → `checked=0 → PASS`（3 变体：emoji 隔开标记 / `⭐`U+2B50 夹数字 / 组合音标 U+0301） | EXIT=0 误放行 | `_text_guard.has_split_number()` 类别化劈开检测（So/Sk/Mn/Cf/Sc）→ EXIT=3 / 记 unverified 哨兵 |
| 🔴2 | 邻近 `[待人工核验]` 标注洗白邻数字（`n=111 及 n=222 [待人工核验]`） | 111 未溯源却 PASS | 标注间隔 `[^\n]{0,40}?` → `[^\d\n]{0,40}?`（只归属紧邻且间隔内无他数字）；G4 须覆盖**全部** unverified |
| 🔴3 | `hypothesis_watch` `active_hypotheses` 元素非 dict | `AttributeError` EXIT=1 | 改漂移检测（缺 `KEY_FIELDS` 任一即判漂移），无 Traceback，退出码 ∈ {0,3,5,6} |
| 🟠4 | 数字子串匹配假阳性（`0.94` 命中 `0.9441`；`0.98` 命中 `10.980`） | 误判溯源成功 | 边界匹配 `(?<![\d.])cand(?![\d.])`（`pool_has_number`），三处复用 |
| 🟠5 | `validate_contracts` 正本/`SKILL.md`/`team-contract.md` 缺失 → 虚假「全员契约完整」 | 删除文件反而 EXIT=0 | 按缺失条目数记契约缺失 → EXIT=5 |
| 🟠6 | `cron_watch.sh` task_id 全被白名单过滤 → 静默「无巡检对象」 | 监控失效 EXIT=0 | stderr 明示 + EXIT=3 |
| 🟠7 | `poll_run_dir` 撞限标注限前 8 行 → 第 9 行即漏检 | 不完整产出判 READY | 改全文扫描（`max_chars=200000`），docstring「头部带」→「正文带」 |

**证伪不修 1 项**：盲检 B 报「`verify_member_output` 无权威源时 EXIT=0 静默放行」→ 主代理复现实为 **EXIT=5** 且落盘 unverified 哨兵，属误报，不修。

## 根因级治理（不再枚举码点区间）
字符码点区间枚举永远补不完（U+2B50 在既有区间外、U+203C‼ 是 Po、U+3030 是 Pd）。本轮改为**类别化 + 消费侧一致性**双保险：
- `_text_guard.has_split_number()` 按 Unicode 类别（So/Sk/Mn/Cf/Sc）识别「数字 + 隔断字符 + 数字」结构 → 命中即 fail-closed。常规排版（`1,234.5` / `10:30` / `20°C` / `10~20`）不误判。
- `has_forbidden()` 改 span 判定：连续 emoji/Cf 为一段；非 ZWJ 的 Cf 一律拒绝；emoji/ZWJ 段紧贴 ASCII 数字即拒绝；合法 ZWJ emoji 序列放行。

## 修复纪律
- 回归断言**全部复用既有测试函数**（`test_require_tag_gate` / `test_gate_mode_blocks` / `test_disposition_gate` / `test_decision_records_guard` / `test_cron_b5_assets` / `test_poll_hitlimit_and_manifest`），零新增函数 → 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` **零联动**。
- fail-open 优先于 fail-close 修复；每条 🔴 均「复现 → 修复 → 反向对照三态」后才采信。
- 文档口径同步：`poll_run_dir` 的「头部带」→「正文带」文案随实现同步修正，避免口径漂移。

## 终验
pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` EXIT=0（**80 文件**）/ 包外锚 **22/22 一致** / 四处 version=1.5.23 / py_compile 全过。

## 包外基线锚
按受控流程刷新：刷前正确报 **DRIFT / EXIT=5**（9 条漂移）→ `--refresh --i-acknowledge-refresh --reason` 带 commit 溯源（commit `292d6a7` / tag `v1.5.23` / 9 文件变更）→ 刷后 **22/22 OK / EXIT=0**。`BASELINE_ANCHORS.json` 落审计区（包外），`refresh_history` 记本轮 commit。

## 遗留（本轮发现，未擅改 · 记录待裁决）
1. **治理仓锚刷新日志断档**：`research-ops/00_governance/anchor_refresh_log.jsonl` 自 v1.5.20 起未再追加（git 历史：v1.5.9→v1.5.20 连续 7 行，此后无），而包外锚 `refresh_history` 已有 14 条。v1.5.13–v1.5.17 与 v1.5.21/v1.5.22 的刷新事件在治理仓侧缺留痕 → 双位置对账口径不一致。本轮已补记 v1.5.23 一行；历史缺口不回填（改写既有审计台账风险高于收益）。
2. **锚历史 tag 记录陈旧**：v1.5.21 / v1.5.22 两轮刷新在打 tag **之前**执行 → `refresh_history` 记为上一版 tag `v1.5.20`（实际对应 v1.5.21 / v1.5.22）。属操作顺序问题，commit 溯源正确。本轮改为**先 commit+tag 再刷新**，`source.tag` 正确记为 `v1.5.23`。

## 冻结声明
本轮为冻结后改造轮，改动须**连续两轮独立零🔴盲检**方可恢复冻结（见 R4_SUMMARY.md §5）。盲检 A/B 已重启，结果待回填。
