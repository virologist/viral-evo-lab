# viral-evo-lab v1.5.35 治理同步（R4.18）

- 日期：2026-11-27
- 专家包 commit：`c616f53`（= tag `v1.5.35` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.34` / `af57943`

## 1. 本轮触发

v1.5.34 两路独立盲检（前台同步，报告均送达）：A 通用无预设报 10🔴+1🟠，B 对抗红队报 7 组🔴+1🟠，大量交叉印证。主代理逐条独立复现、去重后坐实 8 类 fail-open，证伪 2 项。核心教训复现历史：**「按类别/码点枚举」永远补不完**——本轮从 Mc/Me 扩展到 Nd/No/Zs/Lm/Co/非 ASCII `!`，且 `%`(Po) 被误剥使黑名单字面量 `20\.58%` 永假（纯 ASCII 输入即 clean）。

## 2. 修复清单（8 类，全部主代理独立复现）

| 类 | fail-open 形态 | 实测 | 根因修复（语义判据/白名单，不再枚举） |
|---|---|---|---|
| 1 | 浮点 `0.94e5` / 整数 `94$€°` 后缀洗白 | PASS→EXIT=5 | `pool_has_number` 命中后检查右邻 Unicode 语义（L*/N*/S*/M*/Cf/Cs/Co 延续即拒） |
| 2 | 同形声明假名 `ん`/`ニ`、非字母 `★`/Co mark | checked=0/PASS→EXIT=3 | `_is_np_homoglyph` 改「`=数字` 结构下除 CJK 表意外任何非 ASCII mark 一律拦」；D′ prime 豁免 |
| 3 | 撞限词 Nd/No/Zs/Lm/Co/`!` 隔断 | READY→EXIT=5 | `normalize_for_matching` 白名单（ASCII 可见+CJK）；撞限专用 `normalize_for_cjk_keyword` 纯 CJK 投影 |
| 4 | check_scope `%` 黑名单永假 + 跨行叙事 + 泰文 PMID | clean→EXIT=3 | 保留 `%`；追加全文归一化扫描；`normalize_for_extraction` 增 Nd→ASCII 映射 |
| 5 | severity 全角/西里尔/Mn 同形 → fatal 漏报 | CLEAN→EXIT=5 | `hypothesis_watch` severity/status 比较前走 `normalize_for_extraction` |
| 6 | 形态锚全角等号 `default＝True` | OK→EXIT=5 | `check_decision_records` 归一化源码后匹配形态锚 |
| 7 | G6 reason/excerpt Cf 空壳 + line -1/0 | PASS→EXIT=5 | `verify_evidence_check` `_is_nonempty` 加 `has_forbidden`；line 值域 `>=1` |

**证伪 2 项**：evidence `line="１"`（U+FF11）归一化后为合法行号 1（非 fail-open）；泰文 PMID 原 payload 混入元音符 U+0E38（Mn 非数字），正确数字 U+0E58 已被 Nd 映射覆盖。

## 3. 🟠 已知限制（沿用）

- G4 `artifact_mtimes` 缺条目不判篡改；`check_baseline_anchors` `bytes:true` 当合法整数（sha256 仍匹配）。

## 4. 验证与纪律

- 全链：manifest 80 / pytest 19 / fuzz 61/61 / 守卫 11/11 / compileall / 四处 version=1.5.35 / 包外锚刷前 DRIFT EXIT=5、受控刷新、刷后 22/22 OK。
- 机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级 = 61/61` 零联动（回归断言复用既有 `test_require_tag_gate` / `test_poll_hitlimit_and_manifest` / `test_decision_records_guard` / `test_g6_evidence_gate` 四函数，零新增函数）。
- 8 类 25 变体 CLI 三态实测全过，合法对照（CSV 双字段 / prime 变体 / 中文正文 n / 治理正本精确豁免 / 合法 PMID 嵌入正文）无误伤。
- commit==tag==HEAD=`c616f53`，main + tag 均已 push（tag 因 HTTP2 framing 瞬断改用 `-c http.version=HTTP/1.1` 成功）。
- 锚刷新日志追加 v1.5.35 条目。

## 5. 冻结状态

**未冻结**。v1.5.35 需连续两轮独立盲检零🔴才可回填 `R4_SUMMARY.md` §5 冻结声明。已连续多轮每轮盲检均报新🔴（攻击面持续暴露），收敛判据不变。
