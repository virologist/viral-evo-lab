# viral-evo-lab v1.5.36 治理同步（R4.19）

- 日期：2026-11-27
- 专家包 commit：`b06e81e`（= tag `v1.5.36` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.35` / `c616f53`

## 1. 本轮触发

v1.5.35 两路独立盲检（前台同步，报告均送达）：A 通用无预设 3🔴，B 对抗红队 8🔴+1🟠，中文句号项重复，去重后 10 项候选。主代理对 10 项逐条构造 fixture 真实 CLI 独立复现并设正字对照，**10/10 全部坐实、零证伪**。核心教训：**合法豁免本身成为新攻击面**——CSV 逗号特例、prime 豁免、CJK 白名单、被检对象自报的 cli_sites，均被反用为缩水检查范围的手段；故豁免必须收敛为固定真源白名单或语义判据。

## 2. 修复清单（10 项，全部主代理独立复现）

| 项 | fail-open 形态 | 修复前 → 后 | 根因修复 |
|---|---|---|---|
| A1/B4 | `20。58%` / `v6。6` / `file。pre-backup` 中文句号使黑名单永假 | clean → EXIT=3 | `check_scope` 在**原始文本**上做局部「数字/字母间句号→`.`」紧凑投影后二次扫描；不动全局归一化，保住 `n = 94。结论` 合法句号 |
| B3 | `PP 41,034,380` / commit 千分位逗号字面量失配 | clean → EXIT=3 | 同一紧凑投影只在数字间剥逗号，CSV 字段边界保留 |
| A2 | cli_sites 指向无锚 dummy 使形态锚检查被跳过 | OK → EXIT=3 | 有非空 `RULE_ANCHORS` 声明的 rule 强制 cli_sites 属于声明键集合；`require_tag_default_off` 走专用「三处 CLI 覆盖」校验 |
| A3 | spawn_manifest 混入非法 member 静默跳过 | READY → EXIT=5 | 非 spawn 事件（如 evidence_check）仍跳过；spawn 事件畸形 member 一律 fail-closed |
| B1 | `dɲ=0.94` / `dα=0.94` 滥用 prime 豁免 | checked=0/PASS → EXIT=3 | prime 豁免改为「归一化后确为撇号变体」，非撇号 mark 判同形 |
| B2 | `p量=0.94` / `n量=0.94` 用 CJK 隔断伪造声明 | checked=0/PASS → EXIT=3 | `=数字` 结构下 Lo 隔断纳入同形判据；`p值=0.94` 同构写法按脚本契约判 fail-closed，要求 `p=0.94` |
| B5 | 池 `id94` / `x0.94` 左边界洗白 | found=1/PASS → EXIT=5 | `pool_has_number` 左边界补 `\w` 对称约束 |
| B6 | 池 `0.94_5` / `0.94‿5` Pc 连接符洗白 | found=1/PASS → EXIT=5 | 右邻数值延续语义补 `Pc` 类别 |
| B7 | severity `fatαl` / `fataл` 同形漏报 | CLEAN → EXIT=5 | `hypothesis_watch` 归一化后仅接受纯 ASCII `fatal`/`severe`，其他字母视为同形 |
| B8 | G6 Hangul filler U+115F 视觉空白空壳 | PASS → EXIT=5 | `_is_nonempty` 拒绝 Unicode 名字含 `FILLER` 的字符，与 Cf/Cc/U+FFFD 并轨 |

**边界说明**：A2 修复后 EXIT=3 是脚本契约的结构错误码（非裁决违反的 EXIT=5），回归断言明确要求 3，属正确 fail-closed，非回退。

**🟠 披露不修 1 项**：`check_baseline_anchors` `bytes:true` 被当合法整数——改变 bytes 但 sha256 仍匹配才可触发，且属 fail-close 方向误判；沿用既有披露，不修。

## 3. 验证与纪律

- 全链：manifest 80 文件 / pytest 19 passed / fuzz（机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61`）/ 守卫 11 项 / compileall / 四处 version=1.5.36 全过。
- 10 项复现 driver 含正字对照全部转绿；`p值=0.94` 的 fail-closed 边界已在 CHANGELOG 如实披露。
- 回归断言复用既有 `test_require_tag_gate` / `test_poll_hitlimit_and_manifest` / `test_decision_records_guard` / `test_g6_evidence_gate` / `test_disposition_gate` 五函数，零新增 → 机器锚 61/61 不变。
- 包外锚：刷前 DRIFT EXIT=5，受控刷新 EXIT=0（reason 已写），刷后 `expected=22 matched=22 verdict=OK`，锚 source.commit=`b06e81e`、tag=`v1.5.36`。
- commit==tag==HEAD=`b06e81e`，main 与 tag 均已 push（HTTP/1.1 规避 HTTP2 framing 瞬断）。
- `anchor_refresh_log.jsonl` 已追加 v1.5.36 条目。

## 4. 冻结状态

**未冻结**。v1.5.36 须连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明；已连续多轮每轮盲检都能报出新🔴，收敛判据不变。
