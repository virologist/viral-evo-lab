# viral-evo-lab v1.5.37 治理同步（R4.20）

- 日期：2026-11-27
- 专家包 commit：`0cc40b9`（= tag `v1.5.37` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.36` / `b06e81e`

## 1. 本轮触发

v1.5.36 两路独立盲检（前台同步，报告均送达）：A 通用无预设 6🔴+5🟠，B 对抗红队 7🔴+3🟠，U+2800 视觉空白项重复，去重后 12 项候选。主代理对 12 项逐条自建 fixture 真实 CLI 独立复现并设正字对照，**12/12 全部坐实、零证伪**（其中 3 项因盲检 fixture 字段口径有误，重建最小用例后复核坐实）。核心教训：**「检查范围由被检对象自报」与「空工作量即 PASS」是两类新的语义空壳化**，修复不能只补形态锚，须固定检查范围与工作量下限。

## 2. 修复清单

| 项 | fail-open 形态 | 修复前 → 后 | 根因修复 |
|---|---|---|---|
| A1 | `render_context_stack` 4/4 真源全丢仍 EXIT=0 | 0 → 3 | docstring 契约「3=真源缺失」落地，missing 非空即 rc=3 |
| A2 | 零项审判 `items=0/sources=0/PASS` 让 G5 放行 | PASS/0 → DEGRADE/5 | 生产侧 PASS 须正数量检查项+源核验；G5 消费侧同步拒绝零工作量 |
| A3 | `ap.set_defaults(require_tag=True)` 绕过形态锚 | OK → 5 | `RE_DEFAULT_TRUE` 补 set_defaults 关键字/字典写法 |
| A4/B4 | G6 用 U+2800 / 私用区空壳凑满 2 条 | PASS → 5 | 单一事实源 `has_visible_content()` 白名单判据（须含 L/N），保留 Hangul filler 具名排除 |
| A5 | waiver `reason="\u200b"` 空口放行 G2+G4 | 0 → 5 | waiver 署名/理由复用同一白名单判据 |
| A6 | `artifact_mtimes={}` + 核验后篡改且谎称指纹一致 | 0 → 5 | 时序语义判据：artifact mtime 晚于核验记录写出即 G4 FAIL；按实际比对条数如实披露（保住空映射存量基线） |
| B1/B2 | `20。 58%` / `41, 034` / 全角逗号漏投影 | clean → 3 | 投影按「分隔点+两侧空白」语义匹配，纳入 U+FF0C |
| B3 | cli_sites 白名单内子集删掉翻转站点 | OK → 3 | ADR-001 三处 CLI 固定真源不可缩水 |
| B5 | status `cloաed` 亚美尼亚同形使 fatal 闭环隐身 | CLEAN → 5 | 含非 ASCII 字母即视为不可信 closed 声明，保守计入 |
| B6 | `pA=0.94` / `n_=94` 五道守卫全灭 checked=0 | PASS → 3 | 短 ASCII 隔断（1~2 字符）+ 分隔符 + 数字专用判据；不把 L/N/Pc 入全局 gap_cats（保住 `"phase": 1`） |
| B7 | `type:"spawn"` + 非字符串 member 静默跳过 | READY → 5 | 仅已知非 spawn 事件可跳过，畸形行 fail-closed |

**4 项🟠低风险根治**：外部 `.learnings` 路径豁免收敛为包内；池左符号前缀 `€0.94` 补对称语义判据；`schema_version: true` 排除 bool；锚删 `source` 字段即结构错误（保持 schema verdict 契约）。

**3 项🟠披露不修**：`verify_member_output` 无权威源零核验返回 0（设计取舍，G4 兜底）；繁体撞限「輪次耗盡」（语义等价非 Unicode 等价，不引简繁词表）；severity `fat4l` ASCII 拼写变体（非同形，属输入拼写错误）。

## 3. 验证与纪律

- 全链：pytest 19 passed / fuzz 61/61 / 守卫 11/11 / manifest 80 文件 / compileall / 四处 version=1.5.37 全过。
- 回归断言复用既有 8 个测试函数（含 `test_contract_guard`），零新增 `def test_*`，机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 不变。
- 修复过程中修正 4 次自身误伤：`Lu` 双字母码未命中、长 JSON mid 误判、U+115F 属 Lo 被新白名单误放行、锚 verdict 抢先改写既有 schema 契约。
- 包外锚：刷前 DRIFT EXIT=5（12 文件漂移），受控刷新 EXIT=0，刷后 `expected=22 matched=22 verdict=OK`，锚 source.commit=`0cc40b9` / tag=`v1.5.37`。
- commit==tag==HEAD=`0cc40b9`，main 与 tag 均已 push。
- `anchor_refresh_log.jsonl` 已追加 v1.5.37 条目。

## 4. 冻结状态

**未冻结**。v1.5.37 须连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明；已连续多轮每轮盲检都能报出新🔴，收敛判据不变。
