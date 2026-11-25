# Changelog

All notable changes to **viral-evo-lab** are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/spec/v2.0.0.html).

> **2026-11-07 补记说明**：v1.1.1~v1.5.0 区间曾长期缺条目（版本记录断层，已按治理约束⑤索引同步修复）。以下补记条目均从 git tag 链与提交信息反推，逐条附 commit hash 溯源；措辞可能较当时实况简略，以 git 历史为准。

## [1.5.32] - 2026-11-25（R4.15 v1.5.31 盲检 A 回补 · 6🔴 fail-open：ZWJ 隔断三处 + 劈开检测三缺陷）

v1.5.31 盲检 A（前台同步，报告送达）报 6🔴+0🟠，主代理**逐条独立复现全部坐实**（checked=0/found=1/PASS、CLEAN 等实证）后修复。6 项分两类根因：①ZWJ(Cf) 隔断关键 token（撞限词/事故叙事/severity），②上轮修复引入/遗留的劈开检测三缺陷。

### Fixed（6🔴，全部主代理独立复现）
- **A1 ZWJ 隔断撞限词**：`轮‍次耗尽` → poll READY/EXIT=0。`has_forbidden` 原只拒 ZWJ span 紧贴**数字**，CJK 侧放行；`normalize_for_matching` 不剥 Cf → 子串失配。改：`has_forbidden` span 左右任一 `isalnum()`（数字/字母/CJK）即拒（合法 emoji ZWJ 两侧均 emoji 仍放行）；`normalize_for_matching` 匹配用途全剥 Cf。
- **A2 ZWJ 隔断事故叙事**：`位‍置映射错` → check_scope clean/EXIT=0。同上根因，双防线修复后 EXIT=3。
- **A6 ZWJ 附 severity**：`fatal‍` → `_row_str` 只 strip（ZWJ 非空白）→ 精确比较失配 → fatal 证伪静默 CLEAN/EXIT=0。`has_forbidden` 拒字母侧 ZWJ → 严格读 EXIT=3（证据源污染，不可放行）。
- **A3 劈开上限 `{1,8}`**：`94×9×7`（9 个分隔符）→ 正则零匹配，前缀 94 被池洗白 PASS。上限放宽 `{1,64}`（有界防 ReDoS）。
- **A4 前置分隔符破坏 `all()`**：`94,⬰7` 的 `,⬰` 中逗号留在 core 使 `all(is_split_char)` 整体 False → 洗白 PASS。改：剔除 core 中所有合法分隔符后再判剩余是否全劈开类。
- **A5 Co/Me 类漏检**：`94\ue0007`(Co 私有区)/`94\u20dd7`(Me 封闭组合环) → PASS。`_SPLIT_BAD_CATS` 补全 Co/Cs/Mc/Me（原注释声称「全 S*/P*/M*/C*」实际漏四类）。

### Verified
- 6🔴 修复前后三态实测（PASS/CLEAN/READY → EXIT 3/5），合法对照（1,234.5 / 10:30 / 10~20 / 20°C / 1e-3 / 多语小数点 / 全角逗号 CI / D′）不误拒。
- 回归断言复用既有 `test_require_tag_gate()` / `test_poll_hitlimit_and_manifest()` / `test_disposition_gate()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version 一致（1.5.32）。

## [1.5.31] - 2026-11-25（R4.14 v1.5.30 盲检 A 回补 · 7🔴 fail-open：Sm/Pd 劈开 + 同形/prime 声明 + 池逗号 4+ 位 + 符号隔断匹配 + G6 bool）

v1.5.30 盲检 A 前台同步调用成功（报告正文实际送达，规避上轮后台 agent 报告丢失）。报 7🔴 + 若干🟠。主代理**逐条独立复现全部 7🔴**（含 checked=0/PASS、found=1/PASS、valid=2/PASS 实证）后修复；🟠 均为 fail-close 误拒合法输入（CI `+0.1` / d′=`+0.94` / 科学计数 `1.2e-3` / 超长补零 `0.944100000` / 千分位池 `1,234`），按「fail-open 优先」不阻塞冻结，作已知限制披露。

### Fixed（7🔴，全部主代理独立复现）
- **A1 Sm/Pd/Po 劈开数字前缀洗白**：`n=88⬰88`、`p=0.9⬰4`、`n=94～500`、`10！94` → 前缀 `88/0.9/94` 被池中洗白 PASS。`_text_guard._SPLIT_BAD_CATS` 扩到全 S*/P*/M*/C* 类（ASCII 合法分隔符 `.,:-~′'`、`·` 多语小数点、全角 `，．` 显式放行）；`_SPLIT_NUM` 右侧数字改正向前瞻（不消耗），修 `0.9⬰4` 因 `0.9` 先匹配消耗数字致 `9⬰4` 漏检的正则贪心 bug。
- **A2 预组合同形/希腊同形声明标记**：`ń=94`/`ṕ=0.94`/`ν=94` → checked=0/PASS。`normalize_for_extraction` 改 NFD 分解 → 剥 Mn → 语义映射 → NFKC，复原预组合字母的 ASCII 基底；`_EQUIV_TRANS` 加 ν/ο 同形映射。
- **A3 prime 变体声明隐身**：`d´`/`dʹ`/`d‵` → checked=0/PASS。`_EQUIV_TRANS` 扩 prime/acute 变体（U+00B4/02B9/2035/02BA/02CB/02C8/02B8/055A），NFD 前先映射一次防 U+00B4 被拆成空格+Mn。
- **A4 池逗号 4+ 位回溯绕过**：`n=94` 被池中 `94,5000` 洗白（`\d{1,3}` 回溯耗尽）。右边界改 `(?!,\d+(?!\.))`——任意位数千分位/字段延续均拦，CSV 浮点字段 `30,0.9441` 因后随小数点放行。
- **A5/A6 非 Mn 符号隔断匹配**：`10⬰94`/`10！94` check_scope clean、`轮⬰次耗尽` poll READY。新增 `normalize_for_matching()`（剥 Mn + 非 ASCII S*/P*，保留合法数字分隔符），check_scope/poll 共用；全角 `！` 经 NFKC→ASCII `!` 后按类别剥离。
- **A7 G6 `line=true`**：bool 是 int 子类，两条 `line=true` 抽查判 valid=2/PASS。`verify_evidence_check` 显式排除 bool。

### Known Issues（🟠 fail-close，不阻塞）
- `CI [+0.1, +0.2]`（池 0.1/0.2）、`d′=+0.94`、科学计数 `p=1.2e-3`（池 0.0012）、超长补零 `0.9441` vs `0.944100000`、`n=1234` vs 池 `1,234` 会误拒（EXIT=3/5）。均为拒绝合法输入，不放行恶意输入；为避免新 fail-open 面，本轮不修。

### Verified
- 7🔴 修复前后三态实测（PASS → EXIT 3/5；valid=2/PASS → EXIT=5/valid=0），合法对照（多语小数点 / 全角逗号 CI / 千分位 / 时间 / 20°C / emoji ZWJ）不误拒；中途两次 fail-close 误伤（`CI ［0.1，0.2］` 全角逗号、`p=0·94` 多语小数点、`～` 全角波浪）均已加等价分隔符放行判据消除。
- 回归断言复用既有 `test_require_tag_gate()` / `test_poll_hitlimit_and_manifest()` / `test_g6_evidence_gate()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version 一致（1.5.31）。

## [1.5.30] - 2026-11-25（R4.13 v1.5.29 双路盲检回补 · 8🔴 fail-open 根因级封堵）

v1.5.29 双路盲检报 A=5🔴2🟠 / B=3🔴1🟠（报告正文因 agent 结束未送达主代理上下文，按纪律不凭计数采信）。主代理以对抗 payload 逐条独立复现，**8 项 fail-open 全部坐实**（含 checked=0/PASS、found=1/PASS、EXIT=1/崩溃实证），逐项修复；B2（未来日期）经精确 fixture 二次复现后亦坐实。核心根因三类：**Mn/Sm 符号插进关键 token 致正则/子串静默失配**、**token 边界与精度候选不完备致编造数字被池中洗白**、**容器类型未校验致契约外崩溃**。

### Fixed（8🔴，全部主代理独立复现）
- **A1 Sm/区间外 Mn 隔断声明**：`p⬰ = 0.94`（U+2B30 Sm）、`p\u1AB0 = 0.94`（区间外 Mn）→ `checked=0/PASS`。`normalize_for_extraction()` 改为**先剥 Mn 再 NFKC**（防 U+1AB0→U+2B30 转换绕过），`has_invisible_marker_gap()` 改 Unicode 类别动态判据（S*/C*/M*），不再靠码点区间枚举。合法 `p＝0.94`（全角等号 NFKC→`=`）经归一化文本扫描不误伤。
- **A2 池中逗号延续洗白**：R4.11 修 CSV 三列字段时误删 v1.5.28 的右边界 `(?!,[0-9])` → `n = 94` 被池中 `94,500` 洗白 `PASS`。恢复整数候选右边界 `(?!,\d{1,3}(?![\d.,]))`：禁千分位/字段延续，放行 CSV 浮点字段 `30,0.9441`。
- **A4 CI 花括号**：`CI ｛0.1, 0.2｝` → NFKC 转 `{}` 而 CI 正则只认 `[]（）` → 声明隐身。PATTERNS.ci / KEY_MARKERS / _DECL_SPEC / DECL_HINT / has_broken_key_pattern 五处统一加 `{}` 括号形态。
- **A3 check_scope Mn 隔断**：`10\u030194` → 事故值正则失配 → clean/EXIT=0。归一化剥 Mn 后命中 EXIT=3。
- **A5 poll 撞限标注 Mn 隔断**：`轮\u0301次耗尽` → 子串失配 → 不完整产出判 READY/EXIT=0。撞限判定改走 `normalize_for_extraction()` 后匹配 → EXIT=5。
- **B1 float 截断候选洗白**：`float_candidates()` 无条件 `f"{f:.3f}"` 产生**截断候选**——产出 `0.94412` → 候选 `0.944` → 被池中 `0.944` 洗白，违反函数 docstring「禁截断」。改为仅补零（目标精度 ≥ 原值实际小数位且数值相等），绝不降精度。
- **B2 未来同日 fatal 静默吞**：带毫秒 `last_updated == closed_date`（未来时刻）走 `cd > hyp_updated` 严格比较相等判「不晚于」→ CLEAN/EXIT=0。统一「同日即算晚于」判据（与纯日期口径一致，保守 fail-closed）→ EXIT=5 REVIEW_REQUIRED。
- **B3 verification.rule 容器崩溃**：`rule=list/dict` → `rule not in RULE_ANCHORS` 抛 `TypeError: unhashable` → EXIT=1（契约仅 0/3/5）。先做字符串类型校验 → 结构错误 EXIT=3。

### Verified
- 8🔴 修复前后三态实测（PASS/EXIT=1 → EXIT 3/5），合法对照（CSV 双字段 / CI 方括号 / 全角等号 / emoji ZWJ / 普通 p）不误拒。
- 回归断言复用既有 `test_require_tag_gate()` / `test_disposition_gate()` / `test_poll_hitlimit_and_manifest()` / `test_decision_records_guard()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件重生成 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version 一致（1.5.30）。

## [1.5.29] - 2026-11-25（R4.11+R4.12 v1.5.28 双路盲检回补 · 不可见隔断扩展 + 多语小数点语义归一 + 台账严格读 + JSONL 巡检）

v1.5.28 冻结前双路盲检：A=2🔴+2🟠、B=3🔴+3🟠。主代理**逐条独立复现**（含 fixture 原样复验）后确认：A🔴1（UTF-16BE 台账 fail-open）、A🔴2（多语小数点洗白）、B🔴1（`_MARKER_GAP` 漏检）、B🔴3（cron JSONL）、B🟠5/6（CSV 三列字段、合法小 n/千分位）坐实；另主代理自查发现 V1 降级路径 fail-open，一并修复。核心根因：**NFKC 不收敛的多语小数点被当普通隔断 → 数字截断后取片段被池中洗白**、**裸 open(utf-8-sig) 吞入 UTF-16BE 无 BOM 的 NUL → 列名污染 → fatal 证伪静默忽略**。

### Fixed（🔴）
- **A🔴1 台账 UTF-16BE 静默放行**：`redteam_ledger.csv` 以 UTF-16BE 无 BOM 编码时，NUL 在 UTF-8 下合法，裸 `open(utf-8-sig)` 吞入 → 列名含 NUL → `finding_id` 取不到 → fatal 闭环被当 CLEAN（EXIT=0，fail-open）。改用 `_text_guard.read_text_checked()` 严格读 + 控制字符检测，污染即 EXIT=3。
- **A🔴2 多语小数点被截断洗白**：`p = 0٫94`（U+066B 阿文小数点）等经 NFKC 不收敛，提取为 `0` → 池中 `0` 洗白 PASS。`_EQUIV_TRANS` 补语义等价映射：U+066B/00B7/30FB/FF61/2022/06D4/0387/2027/FF0E → `.`，U+066C（阿文千分位）→ `,`；对 NFKC 将 `｡`→`。` 致 `30。5` 被截断者，`prepare_numbers()` 加 `\d。\d` 定点 fail-closed（不动句尾句号），合法中文句读 `n = 30。结果…` 不误伤。
- **B🔴1 `_MARKER_GAP` 漏检**：Cf/Mn 隔断区间有限且未覆盖 CI 括号形态 → 某些不可见隔断仍零提取 PASS。扩展为全区间 Cf/Mn + CI `（` 形态检测。
- **B🔴3 cron JSONL 被吞**：`json.load()` 只能读单行 JSON，多行 JSONL 报 Extra data 被 except 吞掉 → 非法 `task_id` 静默跳过。改为逐行 `json.loads()`，含 `task_id` 字段却全非法 → EXIT=3；空 manifest 仍 EXIT=0。
- **主代理自查 V1 降级 fail-open**：`_load_verify_numbers()` 返回 None 时降级路径无守卫，`p = 0,94` / `n = 1 2 3` 静默跳过。补本地守卫 + `split_number` 哨兵进 unverified。

### Fixed（🟠）
- **B🟠5 CSV 三列字段**：`1,0.94,2` 中数字被逗号边界误当延续 → 合法字段无法溯源。精确化 pool 边界：仅整数候选且前逗号紧邻数字才算延续。
- **B🟠6 合法小 n / 千分位**：`n = 5，结果 p = …` / `n = 1,234` 曾被声明总闸误拒。扩豁免（中文句读后接字母）+ `n_eq` 千分位分支去逗号，仍拦 `n = 5，94` 滥用。
- **A🟠 `--all` 文档**：确认口径与 CLI 一致，本轮不额外改码。

### Verified
- 三条🔴主代理独立复现：A🔴1 用盲检原 fixture（真包 EXIT=0 → 副本 EXIT=3）；A🔴2 多语小数点矩阵（7 变体修复前 rc=0 → 修复后归一化正确提取 rc=5 或句号型定点 rc=3）；B🔴1/3 复验通过。
- 回归断言复用既有 `test_require_tag_gate()` / `test_disposition_gate()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件重生成 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / compileall 全过 / 四处 version 一致（1.5.29）。

## [1.5.28] - 2026-11-25（R4.9+R4.10 v1.5.27 双路盲检回补 · 不可见隔断/同形字 + 提取 token 边界 + 契约外崩溃全入口）

v1.5.27 冻结前双路盲检：A=5🔴+4🟠、B=2🔴+3🟠。主代理**逐条独立复现**（含在当前工作树复验），确认 A🔴2/3/4/5、B🔴1/2 及两路🟠全部坐实；A🔴1（超大整数）与 B🟠3（ValueError 捕获遗漏）经主代理自查合并修复。核心根因两类：**不可见字符/同形字让声明正则静默失配**、**提取正则无 token 边界导致截断片段被池中无 token 洗白**。

### Fixed（🔴）
- **B🔴1 不可见字符隔断声明**：ZWJ(U+200D)/VS16(U+FE0F) 插在 `p/n` 与 `=` 之间 → `checked=0/PASS`。`has_forbidden` 对非数字邻 ZWJ 放行、`KEY_MARKERS` 漏检。新增 `_MARKER_GAP` 判「标记与 =/: 之间夹 Cf/Mn」→ fail-closed EXIT=3；合法 emoji ZWJ（`家族 👨‍👩‍👧 n=888`）不误伤。
- **B🔴2 同形字/多语百分号**：`п=94`（西里尔）、`η=94`（希腊）、`95٪`（阿文百分号）→ `checked=0/PASS`。`_EQUIV_TRANS` 扩同形字等价类 + 多语 `%` → EXIT=5。
- **A🔴2 min-digits 关闭守卫**：`--min-digits 1` + `p = 0,94` → PASS。守卫原 `if min_digits < 2: return False`，与提取阈值耦合。改为逐声明判定独立于 min_digits → EXIT=3。
- **A🔴3 n_eq 截断洗白**：`n = 1234567` + 池中 `123456` → `checked=1/PASS`（只核前 6 位）。`\d{2,6}` 加右边界 `(?![A-Za-z\d.])`，超长声明正则失配 → EXIT=3。
- **A🔴4 pct 截断洗白**：`1234%` + 池中 `234` → PASS。`\d{1,3}` 加左边界 `(?<![\d.])` → EXIT=3。
- **A🔴5 V1 装配零告警**：`assemble_spawn_prompt._v1_extract` 自带正则副本无 NFKC/隔断/声明守卫，`p = 0,94` / `n = 1 2 3` 静默跳过。改走 `verify_numbers.prepare_numbers` 单一入口；守卫 fail 时写 `split_number` 哨兵进 unverified → 装配告警可见；三元组归一化修复下游解包。
- **A🔴1/B🟠3 超大整数契约外 EXIT=1**（主代理自查合并）：>4300 位整数抛 `ValueError`（非 `JSONDecodeError`），`check_baseline_anchors`(×2) / `render_context_stack` / `check_gates` policy+sidecar / `assemble_spawn_prompt` plugin.json / `reconcile_decisions` 共 8 处漏捕获 → 统一扩捕获面，落契约码 3/5。

### Fixed（🟠）
- **B🟠4 CSV 双数字字段误降级**：v1.5.27 的 pool 逗号边界把 `30,0.9441` 的字段分隔符当数字延续 → 合法值 EXIT=5。改为「仅整数候选且前逗号紧邻数字才算延续」；欧洲小数 `0,94` 洗白、千分位 `1,234` 洗白仍拦。
- **A🟠6 check_scope 全角**：事故值 `１０９４号` / `０．２０５８` → clean(0)。扫描前经 `normalize_for_extraction` 归一化 → EXIT=3。
- **A🟠7 cron 非法 task_id 静默跳过**：manifest 含 `task_id: 12345`（非字符串）被白名单过滤后 exit 0。改为含 task_id 字段却全非法 → EXIT=3；无字段仍 exit 0（空 list 对照通过）。
- **A🟠8 CI/dprime 个位整数误拒**：`CI [12.3, 45.6]` → EXIT=3。正则 `\d\.\d+` 扩为 `\d{1,3}\.\d+` → 正常溯源 EXIT=0。
- A🟠9（机器锚口径）：已由既有守卫第 6/9/10 项 + manifest 双重覆盖，本轮不额外放宽。

### Verified
- 双路盲检 7🔴 全部主代理独立复现（复现 → 修复 → 反向对照三态），零证伪；变异测试确认 min-digits 守卫断言有效（回退即失败，真包通过）。
- 回归断言复用既有 `test_require_tag_gate()` / `test_decision_records_guard()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 `--check` EXIT=0 / pytest 19 passed（含 `-W error`）/ fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version 一致。

## [1.5.27] - 2026-11-25（R4.8 v1.5.26 双路盲检回补 · 口径漂移二次收敛 + 契约外崩溃封堵）

v1.5.26 冻结前双路盲检：A=3🔴+4🟠、B=2🔴+2🟠。主代理**逐条独立复现**（含 B 用 `git show 37a3990` 钉纯净基线复核），确认 A3🔴 + B 残留 1🔴（B🔴1 小写 d'/ci 与 A🔴1 同源已并修）全部坐实，零证伪。核心根因仍是**同一语义在多处各写正则导致口径漂移**（这次是 v1.5.26 新引入的 `_DECL_SPEC` 与 `PATTERNS`、`KEY_MARKERS` 之间）。

### Fixed（🔴，全部主代理独立复现后修复）
- **A🔴1 守卫/提取正则口径漂移**：`d'=0.94`（小写 d）、`ci [0.10,0.20]`（小写）、`CI: [...]`、`p: 0.94`、西里尔 `СІ [...]` 共 11 变体 → `checked=0/PASS`（大写 `D'=0.94` 正确 EXIT=5）。根因：`_DECL_SPEC.full_re` 大小写不敏感 `[dD]`、`PATTERNS.dprime` 仅大写 `D`；`ci` 一侧 `re.I` 一侧无。根治：`PATTERNS` 统一 `[dD]`/大小写不敏感/分隔符 `[=:]`/CI 可选分隔符，`_DECL_SPEC.full_re` **直接复用 `_PAT_BY_KIND` 同一对象**（单一事实源，杜绝双份正则漂移）；`_text_guard._EQUIV_TRANS` 补西里尔同形字映射（С/І/р 等）。
- **A🔴2 超大整数 JSON → 契约外 EXIT=1**：>4300 位整数使 `json.loads` 抛 `ValueError`（非 `JSONDecodeError` 子类），5 处 except 漏捕获；且 `e.msg` 在普通 `ValueError` 上不存在引发二次 `AttributeError`。修复：`verify_evidence_check` / `check_gates` / `hypothesis_watch` / `poll_run_dir` / `check_decision_records` / `reconcile_decisions` 六处捕获面扩至 `(json.JSONDecodeError, ValueError)`，错误文案统一 `str(e)` → 统一 EXIT=3 结构失败，`gates.json` 正常落盘。
- **A🔴3 check_scope `\b` CJK 漂移**：`事故编号1094号与错误值0.2058的复盘` → clean(0)（`1094\b`、`0\.2058\b` 在 CJK 紧邻处不成立）。改为 `(?![0-9A-Za-z])`，v1.5.26 在 `verify_numbers` 的同类修复同步到 `check_scope`。
- **B🔴2（R4.8 后残留）冒号声明隔断漂移**：`n: 1 2 3` → `checked=0/PASS`（等号形式正确 EXIT=3）。根因：`KEY_MARKERS` 仍只认 `=`，而 `_DECL_SPEC`/`_SMALL_N_DECL` 已支持 `:`。`KEY_MARKERS` 同步 `[=:]`，与提取/小 n 判定第三处口径对齐。

### Fixed（🟠）
- **B🟠3 逗号边界过严 fail-close**：v1.5.26 把 pool 边界一律扩到 `[\d.,]`，把 CSV 字段分隔符逗号当数字延续 → `metric,value\np,0.11` 中合法 `p = 0.11` 被误降级 EXIT=5。改为「仅当前后**紧邻数字**的逗号才视为延续」：`(?<![\d.])(?<![0-9],)…(?![\d.])(?!,[0-9])`；欧洲小数 `0,94` 洗白、千分位 `1,234` 洗白、`0.9441` 子串洗白全部保持拦截，`p,0.11` / `v,0.11,` 正常溯源。
- **A🟠1 cron 参数缺值**：`bash cron_watch.sh --run-dir` 在 `set -u` 下 `$2` unbound → EXIT=1（契约 3）。参数分支先判 `$# >= 2`，缺值统一 EXIT=3。
- **A🟠2 check_scope 同名文件豁免**：治理正本豁免从 basename 相等改为包内规范路径精确匹配 `_GOV_DOC`，任意目录同名 `GOVERNANCE_BOUNDARIES.md`/`check_scope.py` 不再骗取豁免。
- **A🟠3 V1 装配口径**：`assemble_spawn_prompt._V1_PATTERNS` 与 `verify_numbers.PATTERNS` 逐条同源（大小写/[=:]/CI 可选分隔符），CJK 紧邻 `实验p=0.8` 正常告警。

### Verified
- 全部🔴/🟠主代理独立复现（复现 → 修复 → 反向对照三态），变异测试确认 CSV 字段/冒号隔断两项新断言均非空转（回退修复即断言失败，真包通过）。
- 回归断言全部复用既有 `test_require_tag_gate()` / `test_decision_records_guard()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 `--check` EXIT=0 / pytest 19 passed（含 `-W error`）/ fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version 一致。

## [1.5.26] - 2026-11-24（R4.7 双路盲检再回补 · 声明总闸逐条化 + 边界/字形/消费口径统一）

v1.5.25 基础上重启两路独立盲检：A=1🔴+2🟠、B=5🔴+3🟠（部分交叉印证）。主代理**逐条独立复现**后确认 6🔴 全部坐实，证伪 0 项；3🟠 中 2 项随根因修复自动闭合，1 项（`check_scope` 路径子串豁免）单独修复。

### Fixed（6🔴，全部主代理独立复现后修复）
- **A🔴 CJK 紧邻空白拆段**：`样本n = 1 2 3` → `checked=0/PASS/EXIT=0`（ASCII 对照 EXIT=3）。根因：`KEY_MARKERS` 用 `\b`，CJK 属 `\w` 使词边界不成立，与 `PATTERNS` 的 `(?<![A-Za-z])` 口径漂移。统一为「仅禁 ASCII 字母紧邻」。
- **B🔴1 诱饵短路声明总闸**：`样本 n = 30，结果 p = 0,94` → PASS（权威源含诱饵 30、不含伪造 0.94）。根因：总闸只看 `nums` 全空与否，一个可提取数字即关闭全部声明的检查。改为**逐声明判定** `_DECL_SPEC`：每条 `n=/p=/D′=/CI[/%` 声明都须有可解析的对应数字形态，否则 EXIT=3。
- **B🔴2 G2 消费口径漂移**：`check_gates` 守卫循环调 `prepare_numbers` 却丢弃归一化结果，第二循环对**原始文本** `extract_numbers` → 全角 `ｎ＝９９` 守卫通过、提取零命中 → G2 PASS。改为存 `nums_by_art` 复用同一入口结果 → EXIT=5。
- **B🔴3 逗号未作数字边界**：`pool_has_number` 边界只禁 `\d` 与 `.` → 产出 `n = 94` 被权威池 `0,94` 洗白。边界统一为「前后不得紧邻数字 / `.` / `,`」。
- **B🔴4 排版/同形字等价漏检**：`D’=0.94`（U+2019）、`CI【0.10, 0.20】`（U+3010/3011）、`ρ=0.94`（希腊 rho）→ `checked=0/PASS`。NFKC 不覆盖此类等价，新增 `_EQUIV_TRANS` 语义等价类映射（弯引号/中文方括号/同形字 → ASCII 正字），仅用于提取。
- **B🔴5 小 n 豁免滥用**：`n = 5、94` 中顿号被当句读 → 豁免总闸。收紧为「单数字后只接空白/句末/句号/右括号，或逗号后接字母声明」；`n = 5，p = 0.111` 合法多声明不误伤，`n = 5、94` / `n = 5, 94` 仍拦。

### Fixed（🟠）
- `check_scope` 双重子串豁免：`check_file` 的 `str(p)` 与 `main()` 的 `EXCLUDE` 均以子串匹配 → 目录 `GOVERNANCE_BOUNDARIES.md_evil/` 被整目录跳过，标题叙事绕过。改为文件名精确相等 + 路径段精确相等。
- A🟠1（诱饵工艺）随逐声明总闸闭合；A🟠2（`n = 1 2` 等数字后空白拆段）随边界统一闭合；B🟠1（V1 逗号口径）随 `pool_has_number` 边界闭合。

### Verified
- 6🔴 + 1🟠 全部主代理独立复现（复现 → 修复 → 反向对照三态），零证伪、零跳过。
- 回归断言全部复用既有 `test_require_tag_gate()` / `test_decision_records_guard()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 `--check` EXIT=0 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version 一致 / 盲检一键复现脚本全项退出码回归。

## [1.5.25] - 2026-11-24（R4.6 全面复测回补 · Unicode 等价形态 fail-open 根因级封堵 + 五项结构缺陷）

R4.5 冻结后重启两路独立盲检：A=9🔴+1🟠、B=6🔴+2🟠。主代理**逐条独立复现**后确认 13 个 Unicode/声明 fail-open 变体全部 `rc=0 / checked=0 / PASS`，另复现 5 项结构性缺陷；证伪 1 项（`verify_member_output` 无权威源，实测 EXIT=5）。根因与 v1.5.24 同源但面更广：**枚举字符码点永远补不完**——全角数字/等号/百分号、圈号数字（`①` 满足 `isdigit()` 但 `\d` 不匹配）、上标数字、不同语言小数点、数字声明零提取都会让正则静默失配 → `checked=0 → PASS`。本轮不再补码点，改走归一化 + 总闸的单一事实源。

### Fixed（根因级）
- **NFKC 归一化单一入口**：`_text_guard.normalize_for_extraction()` 仅用于数字/声明提取前归一化，根因收敛 `０．９４` / `p＝0.8` / `95％` / `①.⑧` / `8²8` / `CI ［0.1，0.2］`；原始文本其他用途不变。
- **数字声明意图总闸**：新增 `DECL_HINT` / `_SMALL_N_DECL` / `has_declaration_without_number()`——文本含 `p=` / `n=` / `D′=` / `CI [` / `%` 声明但一个数字都提取不出时，判正则静默失配 fail-closed（EXIT=3），杜绝「声明存在、checked=0、PASS」。干净小 n（`n = 5` 后接空白/句读/行尾）保留豁免，`n = 1-2-3` / `n = 1©…©2` 仍拦。
- **`prepare_numbers()` 单一事实源**：隔断检测 → 归一化 → 声明总闸 → 提取全链路收拢，`verify_numbers` / `verify_member_output` / `check_gates` G2 三消费方同口径，任一方不再自行拼接检测步骤。

### Fixed（结构性，全部实证复现后修复）
- **`assemble_spawn_prompt` 子串洗白**：V1 自动核验原 `cand in pool` 使 `0.94` 命中 `0.9441`。改为复用 `verify_numbers.pool_has_number()` / `float_candidates()` 做 token 边界匹配；模块加载失败时降级到等价边界正则（不再回退子串）。
- **`check_scope` md 标题绕过**：原 `stripped.startswith("#")` 整行跳过，标题内事故叙事不设防。改为仅治理正本 `GOVERNANCE_BOUNDARIES.md` 的注释行豁免，其余标题照常扫描。
- **`validate_contracts` 成员层缺失虚假 PASS**：删除全部 agents 后仍判契约完整。新增 `MIN_AGENTS = 9` 硬门，缺员计入契约缺失 → EXIT=5。
- **`hypothesis_watch` 尾空格/空日期漏报**：`_row_str()` 对字符串单元格 strip，`fatal ` / ` closed` 不再漏判；closed + fatal/severe + 空或不可解析 `closed_date` 不再静默跳过，计入 `late_fatal`。
- **`poll_run_dir` 200k 后撞限漏检**：移除 `max_chars=200000` 截断，全文严格读；撞限标注挪到第 200001 字符后仍判 NOT_READY/EXIT=5。
- **`cron_watch.sh` bash 3.2 陈旧锁崩溃**：全角右括号紧贴 `$LOCK` 被解析为 `$LOCK\xef`，`set -u` 下 unbound variable EXIT=1（契约仅 0/3/5）。改 `${LOCK}`。

### Verified
- 13 个 Unicode/声明 fail-open 变体 + 5 项结构缺陷全部主代理独立复现（复现 → 修复 → 反向对照三态）。
- 回归断言全部复用既有 `test_require_tag_gate()` / `test_poll_hitlimit_and_manifest()` / `test_decision_records_guard()`，零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- manifest 80 文件 `--check` EXIT=0 / pytest 19 passed / fuzz 61/61 / 守卫 11/11 / py_compile 全过 / 四处 version 一致。

## [1.5.24] - 2026-11-24（R4.5 主代理对抗自验 · 空白拆段 fail-open 封堵）

v1.5.23 后主代理对抗压测发现同类漏网 fail-open：`n = 1 2 3`（数字被**空白**拆成多段）→ `n_eq` 正则 `\d{2,6}` 失配 → `checked=0 → PASS`。此前 `has_split_number` 只管非空白隔断（`[^\d\s]`），放行空白；`has_broken_key_pattern` 只看「标记后首字符是否数字」，首字符是 `1` 即判正常——两道防线各留半扇门。

> **并行会话并入说明（v1.5.24 同 commit）**：本版本提交时工作树同时带有 C19 跨包根治（Agent Harness 战线 `2026-11-22` 的 A-2/N1 `resolve_skill_paths` 未知技能 fail-loud，5 包 vendor 逐字节同步），涉及 `scripts/assemble_spawn_prompt.py`、`vendor/shared-core/{assemble_spawn_prompt.py,VENDOR.json}`。该改动非本轮 fail-open 修复内容，经确认属用户并行会话有意工作：vendor 哈希守卫 `test_vendor_core.py` 全链通过（声明 hash 与实际逐字节一致），合法技能解析结果与顺序不变。此处如实标注，避免版本叙事漂移。

### Fixed
- **空白拆段 fail-open**：在单一事实源 `has_broken_key_pattern` 增加第二判据——标记后首个数字 token 紧跟「空白 + 数字」即判隔断（`^\d{1,6}(?:\.\d+)?\s+\d`），EXIT=3。三消费方（`verify_numbers` / `verify_member_output` / `check_gates` G2）经单一事实源自动生效。
- 精确对照不误伤：`n = 5`（min_digits=2 有意跳过）、`n = 30 例`、`p = 0.05 vs 0.01`、`CI [0.1, 0.2]`（逗号非空白）均保持原行为。
- docstring 改 raw string，消除 `SyntaxWarning: invalid escape sequence '\d'`（`-W error` 下可致失败）。

### Verified
- 回归断言复用既有 `test_require_tag_gate`（新增第 4 变体），零新增函数 → `CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**。
- pytest 19 passed / fuzz 61/61 / 守卫 11/11 / manifest 80 文件 / py_compile 全过 / `-W error` 下攻击 EXIT=3、合法对照不误拒。

## [1.5.23] - 2026-11-20（R4.4 复核回补轮 · 数字劈开/标注洗白/正本缺失/静默过滤）

R4.3 冻结后重启两路独立盲检（通用 + 对抗性）。通用盲检报 0🔴/2🟠 后在 v1.5.22 复核追加 1🔴；对抗性盲检报 3🔴 + 4🟠。主代理**逐条独立复现**后采信 6 项（3🔴 + 3🟠），证伪 1 项，另有 1🟠 由另一盲检交叉印证。本轮回补为 R4.4。

### Fixed（3🔴 + 3🟠，全部实证复现后修复）

- **🔴 数字劈开 fail-open（3 变体）**：`数字 + 符号类字符 + 数字` 使数字正则静默失配 → `checked=0 → PASS`（比 traceback 更危险）。实测变体：emoji 隔开标记（`p = 👨‍👩 0.9`）、`⭐`(U+2B50) 夹数字、组合音标(U+0301) 劈开。根因：字符码点区间枚举永远补不完（U+2B50 在既有区间外、U+203C‼ 是 Po、U+3030 是 Pd）。**根因级治理**：不再补码点区间，改为「Unicode 类别化劈开检测」——新增 `_text_guard.has_split_number()`，判定「数字 + So/Sk/Mn/Cf/Sc 类字符 + 数字」结构，命中即 fail-closed（EXIT=3 / 记 unverified 哨兵 → DEGRADE）。常规排版（`1,234.5` / `10:30` / `20°C` / `10~20`）不误判。
- **🔴 邻近标注洗白**：`[待人工核验]` 标注原按 `[^\n]{0,40}?` 采集，可跨过数字吸附到邻近数字 → `n=111 及 n=222 [待人工核验]` 洗白 111。改为 `[^\d\n]{0,40}?`——标注只归属紧邻其前、且间隔内无其他数字的数字；G4 放行须覆盖**全部** unverified（`marked >= marked_total`），部分标注进 problems 并阻断。
- **🔴 hypothesis_watch 非 dict 元素**：`active_hypotheses: [5]` → `AttributeError` EXIT=1（契约无 1）。改为漂移检测（缺 `KEY_FIELDS` 任一即判漂移），无 Traceback，退出码 ∈ {0,3,5,6}。
- **🟠 数字子串匹配假阳性**：原 `cand in pool` 子串匹配 → `0.94` 命中 `0.9441`、`0.98` 命中 `10.980`。改为边界匹配 `(?<![\d.])cand(?![\d.])`（`pool_has_number`），单一实现供 `verify_numbers` / `verify_member_output` / `check_gates` G2 复用。
- **🟠 validate_contracts 虚假「全员契约完整」**：正本 `SKILL.md` / `team-contract.md` 缺失时原判「契约完整」EXIT=0（删文件反而 PASS）。改为按缺失条目数记契约缺失 → EXIT=5。
- **🟠 cron_watch task_id 全被白名单过滤**：manifest 中 task_id 全部超长/非法 → 原静默丢弃 → 「本轮无巡检对象」EXIT=0，监控失效。改为 stderr 明示 + EXIT=3。

### Changed

- `poll_run_dir.head_hit_limit` 由「只扫前 8 行」改为**全文扫描**（`max_chars=200000`）：撞限标注是成员显式写入的产出内容，位置不应受限——原实现标注挪到第 9 行即漏检 → 不完整产出被判 READY/EXIT=0。docstring 与提示同步由「头部带」改为「正文带」。
- `validate_contracts` / `check_decision_records` / `assemble_spawn_prompt` 三处结构异常改记契约缺失/结构错误（EXIT=5 / 3 / 2-3），不再 AttributeError/TypeError 崩溃。

### Verified

- pytest 19 passed / fuzz **61/61** / 守卫 11/11 / manifest 80 文件 `--check` EXIT=0 / py_compile 全过 / 四处 version 一致。
- 6 项坐实缺陷全部**主代理独立复现**（复现 → 修复 → 反向对照三态）后才采信与闭合；1 项（`verify_member_output` 无权威源）经复现为 EXIT=5，**证伪不修**。

## [1.5.22] - 2026-11-20（R4.3 复核回补 · emoji/ZWJ 夹数字 fail-open 封堵）

R4.3 冻结后通用盲检复核追加 1🔴：连续 emoji/Cf span 紧贴 ASCII 数字时，`has_forbidden` 的类别判定放行 → 数字仍被隔断。改为 span 判定（连续 emoji/Cf 为一段；非 ZWJ 的 Cf 一律拒绝；emoji/ZWJ 段紧贴 ASCII 数字即拒绝；合法 ZWJ emoji 序列放行），修 `ord()` 双重取值的 TypeError。

## [1.5.21] - 2026-11-20（R4.3 全面复测回补 · 6🔴 + 1🟠）

R4.2 冻结后两路独立盲检各报真实缺陷，主代理逐条独立复现后全修：version 容器 TypeError（EXIT=1→5）、小数秒闭环漏报（EXIT=0→5）、assemble 嵌套畸形 AttributeError（1→2/3）、decision 元素 TypeError（1→3）、cron_watch 吞退出码（0→3）、G4 部分标注放行（放行→FAIL）、Cf 一刀切误拒合法 emoji（放行）。回归断言全部复用既有测试函数，`CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = 61/61。

## [1.5.20] - 2026-11-19（R4.2 全面复测回补轮 · 用户授权持续迭代至全绿）

两路独立盲检（R4.1 后）各报真实缺陷，主代理逐条独立复现后全修。核心根因：R4.1 的「严格 utf-8-sig + 捕获 UnicodeError」防不住**无 BOM UTF-16**——其 NUL 交错字节在 UTF-8 下合法，解码不抛异常却使数字正则全部失配 → `checked=0 → PASS`（比 traceback 更危险的 fail-open）。

### Fixed（6🔴 + 1🟠，全部实证复现后修复）
- **🔴 UTF-16 fail-open（3 入口）**：新增共享守卫 `scripts/_text_guard.py`（解码后检测 NUL/U+FFFD，单一事实源），接入 `verify_numbers`（产出+权威源）、`verify_member_output`、`check_gates`（G2 分桶扫描 + G4 标注 + G1 信封）。无 BOM UTF-16 产出从误判 PASS 改为契约码 3 / G2 FAIL / unverified 哨兵。
- **🔴 G4 标注后缀绕过**：`_pending_manual_marked` 原 `endswith(f"__{member}.md")` 被 `T__foo__alice.md` 命中，副产物标注洗白 `T__alice.md` 数字 → 误判 PASS/EXIT=0。改为精确匹配（文件名主体须恰好 `{task_id}__{member}`，仅一个 `__` 分隔符）+ member 白名单校验；修复中发现并修正 off-by-one（`.md` 3 字符误切 4）。
- **🔴 撞限标注 UTF-16 漏检**：`poll_run_dir.head_hit_limit` 原 `errors="replace"` 把 UTF-16 的「轮次耗尽」吞成 U+FFFD → 判 READY 放行不完整产出。改严格读 + 控制字符检测，失败/污染保守判撞限 True（NOT_READY/EXIT=5）。
- **🔴 assemble_spawn_prompt 结构崩溃**：`confirmed_hypotheses.json` 顶层非对象（`[]`）或元素非 dict → `AttributeError` EXIT=1（契约无 1）。加 isinstance 防护 + 捕获面扩展，降级跳过注入不炸装配。
- **🔴 validate_contracts 结构崩溃**：plugin.json 顶层非对象 → `AttributeError` EXIT=1（契约仅 0/5）。结构不符记契约缺失 → EXIT=5。
- **🔴 check_scope fail-open**：不可解码/控制字符污染文件原被当「无命中」→ 误判 clean/EXIT=0。改为记「无法核验」命中 → EXIT=3（与 validate_contracts/check_gates fail-closed 同口径）。
- **🟠 cron_watch.sh manifest 静默失效**：原 `errors="replace"` 使 UTF-16 manifest 全部 JSON 行解析失败 → TASKS 空 → 监控静默失效。改严格读 + 控制字符检测，不可解码时 stderr 明示 + 非零退出。

### Changed
- 新增 `scripts/_text_guard.py` 进入完整性清单（manifest 79 → **80 文件**）。
- 回归断言全部复用既有测试函数（不新增函数，`CURRENT_BASELINE` 机器锚保持 45 CASES + 16 行为级 = **61/61**）：🔴1/4/5/6 入 `test_require_tag_gate`，🔴2 入 `test_gate_mode_blocks`，🔴3 入 `test_poll_hitlimit_and_manifest`。

### Verified
- pytest 19 passed / fuzz 61/61 / 守卫 11/11 / manifest 80 文件 --check EXIT=0 / py_compile 全过。
- 6🔴 全部主代理独立复现（复现→修复→反向对照三态）后才采信与闭合。

## [1.5.19] - 2026-11-18（R4.1 盲检回补轮 · 用户裁决全修）

> R4 两轮独立盲检均报🔴（通用盲检 2🔴 / 对抗性盲检 6🔴），主代理逐条独立复现后坐实 4 类真缺陷、厘清误报与 fail-close 安全方向。用户裁决「全修 + 重开盲检」「UTF-16 全包统一改严格读」。R4 收敛计数归零，本轮回补后重启两轮零🔴盲检。

### Fixed
- **🔴 标注跨成员串味（门禁绕过）**：`check_gates.py` G2 的 `marked_vals`（全局 set）与 G4 的 `_pending_manual_marked`（遍历全部 artifact）均不记录标注来源，任一成员 `[待人工核验]` 可洗白另一成员引用同一未标注数字 → G2/G4 误判 PASS。改为标注按 artifact 分桶（`marked_by_art`）+ G4 按 `unverified[].member` 定位来源产出，缺 member 时 fail-closed 不放行。
- **🔴 包外锚退出码语义错配**：`check_baseline_anchors.py` 把 commit/history 与 HEAD 不一致塞进 `structural_errors` → EXIT=3 `ANCHOR_SCHEMA_INVALID`；契约表 `:46` 明定属「漂移」EXIT=5。新增 `drift_errors` 单列，走 EXIT=5 `DRIFT` 且继续 files 对账（不再提前 return 丢明细）。同步 `test_anchor_refresh_guard`「改锚刷绿」断言 3→5。
- **🔴 超长 task_id 崩溃**：`write_checklist.py` 等六脚本白名单只管字符不管长度，5000 字符 task_id 拼路径触发 `OSError: File name too long` → traceback EXIT=1。六脚本 task_id 正则 `{0,127}`、member `{0,63}` 加长度上限，非法统一走参数码 2。
- **🔴 UTF-16 fail-open（17 处）**：全包 `errors="ignore"` 静默吞字节使 UTF-16/BOM 畸形输入解码为空 → 数字核验 `PASS checked=0`、契约校验误放行。7 脚本 17 处统一改严格 `utf-8-sig` + 捕获 `UnicodeError` → 各自契约码/fail-closed（verify_numbers 产出不可解码=3；verify_member_output 记未溯源哨兵→DEGRADE；check_gates 不可解码产出并入 G2 FAIL；validate_contracts/check_decision_records/check_scope/assemble 走既有失败分支）。

### Changed
- 两处文档措辞同步：`verify_numbers` 契约码 3 扩为「产出缺失/不可解码」；`log_spawn`/六脚本错误文案补「长度 ≤128」。
- 四处 version = **1.5.19**；manifest 重生成；包外锚待受控刷新；全量验证 pytest **19** / fuzz **61/61** / 守卫 **11/11**。R4.1 计数归零 0/2，待两轮独立盲检。
- 澄清：R4 自身改动经主代理复现是干净的；上述 4 类🔴多为 v1.5.2/L3 历史遗留，其中 UTF-16 有 2 处系 R4 backlog④ 引入/放大，已一并根治。

## [1.5.18] - 2026-11-18（R4 backlog 清理轮 · 冻结后非阻塞项）

> R3 收敛冻结（v1.5.17 / 连续两轮零🔴）后按用户「接续」授权开 R4 收尾轮，清 R3_SUMMARY §4 backlog 中不改变行为契约的六项。全程机器锚复用既有 `test_tc3_timezone_canonicalize`，45 CASES + 16 行为级 = 61/61 零联动；R4 改动须重新走两轮独立盲检才恢复冻结。

### Fixed
- **🟠 组合死锁（task_id × LEAD_SUFFIXES）**：`check_gates.py` / `verify_member_output.py` 旧 `any(s in a.stem)` 子串包含，在 task_id 合法含元后缀子串（如 `x__gates`）时把成员文件 `x__gates__phylo-analyst.md` 误判为元 artifact 排除 → G3 恒空。改精确尾匹配 `a.stem == f"{task_id}{s}"`（元文件形态固定 `<task_id><suffix>.md`）。
- **🟡 `log_spawn.py` member 无白名单**：`parse_args()` 后补 `_re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.member)`，非法 → stderr + EXIT=2。与 6 脚本 task_id 白名单口径对齐。
- **🟡 `hypothesis_watch.extract_handled_ids` 防御硬化**：签名 `obj: dict | None`，函数体内移挡板 `if not isinstance(obj, dict): return set(), [漂移描述]`。实证 🟠「hw state AttributeError」路径不可达（`load_json_obj` 不变式 err 非空 ⇒ obj 为 None + state_err 挡板保护），故仅硬化不改行为。

### Changed
- **退出码契约表补齐**：`check_gates.py` / `verify_member_output.py` / `log_spawn.py` / `write_checklist.py` / `render_context_stack.py` 的 description/docstring 补当前真实退出码（0/2/3/5 按脚本实际口径）。`poll_run_dir` docstring 已声明 0/5，跳过。
- **解码口径统一**：`validate_contracts.py` 全部 `read_text(encoding="utf-8")` → `errors="ignore"`（对齐同文件既有宽松口径）；`check_decision_records.py` → `utf-8-sig + errors="ignore"`。
- **README 环境要求**：新增 Python ≥ 3.10（PEP 604 `str | None`）+ git 在 PATH（`git ls-files` 为完整性清单唯一真源）说明。
- 四处 version = **1.5.18**；manifest 重生成（79 文件）；全量验证 pytest **19** / fuzz **61/61** / 守卫 **11/11** / manifest EXIT=0。R4 收敛计数归零 0/2，待两轮独立盲检。

## [1.5.17] - 2026-11-17（R3 盲检回补 · R3.2）

> R3 重启第一轮盲检（v1.5.16）FAIL 3🔴——UnicodeDecodeError 捕获面同类残留 4 处裸读点（假说池/state/成员 MD/plugin.json+team-contract），主代理逐一独立复现。计数再归零，回补后重启。

### Fixed
- **🔴 hypothesis_watch `load_json_obj`**：捕获面补 `UnicodeDecodeError`（假说池+state 两消费点一处补齐全覆盖）→ 契约码 3。
- **🔴 assemble_spawn_prompt `load_member_md`**：非 UTF-8 成员 MD → 既有「MD 无效」码 3。
- **🔴 assemble_spawn_prompt `load_plugin`**：捕获面补 `UnicodeDecodeError` → 既有码 3。
- **🔴 assemble_spawn_prompt team-contract 裸读**：契约注入属增强项，解码失败降级为提示行（装配完整、EXIT=0），与「缺失时静默跳过」既有语义对齐。

### Added
- **⑪ 回归断言**：五场景非 UTF-8 fixture 逐一断言契约码/降级行为 + 零 traceback（机器锚 61/61 不变）。
- 如实登记：🟠 hypothesis_watch 畸形 state 两分支语义口径（主路径 6 / extract 分支 AttributeError）待统一；🟡 validate_contracts/check_decision_records 裸读双标——均未达 🔴 线，列入 backlog 不阻塞冻结。

### Changed
- 四处 version = **1.5.17**；manifest 重生成；包外锚受控刷新；全量验证 pytest **19** / fuzz **61/61** / 守卫 **11/11**。R3 计数再归零 0/2。

## [1.5.16] - 2026-11-17（R3 盲检回补 · R3.1）

> R3 第一轮独立盲检（v1.5.15）FAIL 3🔴——同一根因（UnicodeDecodeError 未入捕获面）三实例，均由盲检以独立 fixture 首次复现、主代理独立复现确认。R3 收敛计数归零，本轮回补后重启。另如实声明：🟡 log_spawn 的 member 参数仍未校验（下游消费端兜底，CHANGELOG 1.5.15 口径有落差，已在 F2 语义上收窄为「task_id 已校验、member 未校验」）。

### Fixed
- **🔴 check_gates.py `load_workflow_sidecar`**：非 UTF-8 sidecar → UnicodeDecodeError traceback → G1 起点即崩、gates.json 不落盘、六门全失效。补捕获转「sidecar 解析失败」同通道（G1 FAIL 语义），gates.json 照常落盘。
- **🔴 hypothesis_watch.py 台账读取**：非 UTF-8 台账 → traceback + EXIT=1，违反「证据源畸形 → EXIT=3」契约（CSV 路径漏网）。补 `UnicodeDecodeError` 入 `(OSError, csv.Error)` 捕获面 → EXIT=3。
- **🔴 assemble_spawn_prompt.py 两入口**：`--task-file` 裸读与假说池注入裸读 → traceback + EXIT=1。前者转「任务包无效」既有码 3；后者并入既有跳过注入通道（不炸装配）。

### Added
- **⑩ 回归断言**（复用既有函数，机器锚 61/61 不变）：三入口非 UTF-8 fixture 逐一断言契约码 + 零 traceback + gates.json 落盘（check_gates）。

### Changed
- 四处 version = **1.5.16**；manifest 重生成；包外锚受控刷新。
- 全量验证：pytest **19 passed** / fuzz **61/61** / 守卫 **11/11**。
- R3 收敛计数重启 0/2（连续两轮独立零🔴 才冻结）。

## [1.5.15] - 2026-11-17（R3 回补轮 · F1/F2/B-3 闭合）

> R2 重启第一轮盲检（v1.5.14）FAIL 2🔴 + 🟠1，按 R2_SUMMARY §5 建议开 R3 一次性闭合。B-2 字符集按呈报推荐 `[A-Za-z0-9][A-Za-z0-9_-]*` 落地（默认假设，与存量 T-20261015-M2/T-FUZZ 等完全兼容，可推翻）。

### Fixed
- **🔴 F1 audit_decision_log 跨 TZ 裁决翻转**：`parse_ts` naive 输入裸 `astimezone()` 按系统本地时区解释 + `datetime.now().astimezone()` → 同一台账 UTC 判 13 天 HEALTHY/EXIT=0、Asia/Shanghai 判 14 天 STALE/EXIT=6（PK-R2-001 同构复发）。复用 `now_canonical()` 范式：aware 输入显式 canonicalize 到 +08 naive、naive 按 +08 语境解释、比较侧统一基准；实测三 TZ 环境 EXIT/age/verdict 完全一致。
- **🔴 F2 task_id 路径穿越（6 脚本）**：`check_gates.py` / `verify_member_output.py` / `poll_run_dir.py` / `write_checklist.py` / `log_spawn.py` / `assemble_spawn_prompt.py(--task-id)` 在拼路径/落记录前统一白名单校验 `[A-Za-z0-9][A-Za-z0-9_-]*`；非法走各脚本参数错误码（2 或 5），实测 `../escape` 六连拒、零越界读写。log_spawn 虽只写 JSONL 记录不拼文件名，仍校验（防下游消费端把记录当路径）。
- **🟠 B-3 gen_integrity_manifest --check 损坏清单**：`json.loads` 无保护 → traceback + EXIT=1（与「1=清单过期」撞车）。加捕获 + 顶层结构校验，转独立契约码 **EXIT=3**（清单损坏 ≠ 过期）；docstring 用法行与 --help 同步。

### Added
- **R3 回归集合**：`test_tc3_timezone_canonicalize` 内追加 ⑦F1 跨 TZ 一致性（动态时间基准）⑧F2 六脚本 `../escape` 负例（断言拒收码 + 零越界文件）⑨B-3 损坏清单 EXIT=3（finally 恢复）。仍保持 `45 CASES + 16 行为级 = 61/61` 机器锚不变。

### Changed
- 四处 version = **1.5.15**；`integrity_manifest.json` 重生成；包外锚受控刷新。
- 全量验证：pytest **19 passed** / fuzz **61/61** / 守卫 **11/11** / manifest `--check` OK。
- R3 收敛计数：连续两轮独立零🔴 盲检后冻结（见 `viral-evo-lab-audit/R3_SUMMARY.md`）。

## [1.5.14] - 2026-11-15（R2 第二轮盲检证伪 · 回补轮）

> **收敛判定：v1.5.13 不收敛。** R2 第一轮独立盲检 ZERO 🔴（PASS），第二轮独立盲检（换 lite 模型突破 429）返回 **FAIL / 3🔴**；三条均已由主代理用独立 `/tmp` 夹具复现确认。按 R2 铁律「连续两轮独立零🔴 才冻结」，连续零🔴 计数归零，回补后重启盲检轮。1.5.13 段有关收敛预期的表述属历史原文，保留不改，以本段作证伪标注。

### Fixed
- **🔴-1 时区基准未闭环（T-C3 残留）**：v1.5.13 只修 `parse_dt()` 输入侧，`age_days`（`:269`）与 `reviewed_at` 复核（`:172`）仍用 `datetime.now()`（系统本地 naive），与 canonicalize 后的 +08 naive 混比。实测同一合法 UTC 输入在 `+0800` 下 15 天 / EXIT=5、`TZ=UTC` 下 14 天 / EXIT=0 裁决翻转。新增 `now_canonical()` 统一比较基准，并订正 `:71` 注释「不依赖系统本地时区」此前不实的声称。
- **🔴-2 naive ISO 静默吞掉证伪发现**：`parse_dt()` 仅认 3 种格式，`2026-11-10T12:00:00` 返回 None，台账 `:260` 直接 `continue` 且无 warning。实测仅差一个 `Z` 后缀即由 1 条 / EXIT=5 变 0 条 / EXIT=0。新增两种 naive 格式，并对「非空但无法解析」的 `closed_date` 输出 stderr warning。
- **🔴-3 render_context_stack 破坏 EXIT 契约**：`main()` 只捕 `JSONDecodeError`，渲染函数用 `d['last_updated']` / `h['id']` 直接索引，3 种畸形 JSON 全部 traceback + EXIT=1。改为顶层类型校验 + 扩面异常捕获，统一契约码 **EXIT=3**；`md.read_text()` 亦纳入保护；删除未使用的 `datetime` 导入。
- **🟠-1 gen_integrity_manifest `--help` 静默写盘**：`main()` 仅判断 `"--check" in sys.argv`，任何未知参数（含 `--help`、拼错的 `--chek`）都落入「重生成并覆盖」分支——第二轮盲检实测 `--help` 把 `generated` 从 `08:01:29` 刷成 `09:42:44` 并污染工作树，等于可静默洗白基线。改用 `argparse`：`--help` 只读、未知参数报错 EXIT=2。订正 docstring「幂等性：两次运行 diff 为空」的不实声称。
- **🟡-3 poll_run_dir `--expected` 缺白名单**：成员名直接拼入 `f"{task_id}__{member}.md"`，含 `/`/`..` 可指向包外。与 `--from-manifest` 对齐加 `[a-z0-9][a-z0-9-]*` 校验，非法 EXIT=5。
- **工作区 `changes_summary.py`（research-ops）**：`m19_m20_m21_present` 用 `f"M{n}" in mods`，而 `mods` 来自 `findall(r"M(\d+[a-z]?)")` 不含 M 前缀 → 恒 False，§7 模块检查形同虚设。改为 `n in mods`；删除未用 `sys` 导入。

### Added
- **R2 回补回归集合**：在既有 `test_tc3_timezone_canonicalize()` 内追加 ③④⑤⑥ 四组断言（跨 TZ 裁决一致性 / naive ISO 不吞发现 / 畸形 JSON EXIT=3 / `--help` 只读不写盘）。**刻意复用现有函数**：保持 `45 CASES + 16 行为级 = 61/61` 机器锚与守卫第 11 项计数不变，规避历史 v1.5.10–12 三次计数联动返工。跨 TZ 与 naive 场景均以 `now_canonical()` 动态构造时间基准，无时间炸弹。

### Changed
- 四处 version = **1.5.14**；`integrity_manifest.json` 重生成；包外锚受控刷新（22 文件，含本轮改动的 5 个已跟踪资产）。
- 全量验证：pytest **19 passed** / fuzz **45+61/61** / 守卫 **11/11** / manifest `--check` OK / 全量 `py_compile` 0 失败 / `--help` 只读 / 未知参数 EXIT=2 零写盘 / 白名单拦截 EXIT=5。
- **R2 收敛计数重启为 0/2**；冻结判定以后续连续两轮独立零🔴 盲检为准，见 `viral-evo-lab-audit/R2_SUMMARY.md`。

## [1.5.13] - 2026-11-15（R2 新轮 · T-C3 时区 canonicalize 修正）

> 用户授权开 R2 新轮：冻结包 v1.5.12（`deb1560`）经独立复核（2026-11-14，`independent-review-r2`）确认唯一实质性代码缺陷为 T-C3——`hypothesis_watch.py` 的 `parse_dt()` 对带偏移时间输入（Z/+0000/-05:00）静默丢弃偏移量，导致 late_fatal 漏报与 age_days 偏差。设计文档旧处方（裸 `astimezone()` / 字节切）经实证为回归源，已 superseded（见 `agent-harness-sop/02-design/架构设计文档.md` 处方消歧段，`c93e4ab`）。

### Fixed
- **T-C3 时区 canonicalize**：`scripts/hypothesis_watch.py` 的 `parse_dt()` 将 `dt.replace(tzinfo=None)` 改为 `dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)`——显式 canonicalize 到 +08:00 再转 naive，消除 Z/+0000/-05:00 输入静默丢偏移（实测 Z 04:00→12:00 naive、旧实现误为 04:00；-05:00 07:00→20:00 naive、旧实现误为 07:00）。全程仅在 `dt` 已带 tzinfo 时调用 `astimezone`，绝不对 naive dt 裸调用，避免与 `datetime.now()` naive 触发 naive/aware `TypeError` 打碎 EXIT 契约。同步补 `timezone` 导入与行内注释。

### Added
- **T-C3 回归测试**：`tests/test_gate_fuzz.py` 新增 `test_tc3_timezone_canonicalize()`，两层断言——①单元层 `parse_dt` 对四种时区输入产出确定 +08 naive；②端到端构造「`last_updated=+08 23:00` + `closed_date=Z 16:00`（=次日 00:00 +08）」场景，旧实现 EXIT=0（漏报），修复后必须 EXIT=5 报出。行为级用例 15 → **16**，CURRENT_BASELINE 机器锚同步 `45 CASES + 16 行为级 = 61/61`。

### Changed
- 四处 version = **1.5.13**；`integrity_manifest.json` 重生成（捕获 hypothesis_watch.py / test_gate_fuzz.py / 三处 version 文件哈希变化）；包外锚受控刷新；用例数：fuzz **61/61**、守卫 **11/11**、V7 **7/7**、pytest **19 passed**。
- R2 盲检重启计数：连续两轮独立零🔴 才宣布收敛冻结（待 R2_SUMMARY.md 收轮）。

---

## [1.5.12] - 2026-11-10（终验盲检 R7 · 收敛冻结）

> 第三次独立盲检又抓到 1🔴 + 1🟡：①`_wording_counts()` 的 doc 正则用跨版本宽匹配，实际命中 v1.5.10 **历史段**；自称「当前基线」的 v1.5.11 段数字改成 14 仍全绿（与前两轮同构的覆盖缺口），且 §17 / helper docstring 写「取当前基线声明」属不实声称；②`AUDIT_STATE.md` §16/§17 的「research-ops commit 见本文件终验记录」是悬空引用。本版全部补齐并再次终验。

### Fixed
- **机器锚**：`test_gate_fuzz.py` docstring 新增唯一被读取的 `CURRENT_BASELINE = 45 CASES + 15 行为级 = 60/60`；`_wording_counts()` 的 doc 数字改为只读该锚（`CURRENT_BASELINE\s*=\s*45 CASES \+ (\d+) 行为级`），不再用跨版本宽正则。
- **双向反验**：第 4 步补「仅改 `CURRENT_BASELINE` 数字必被抓」反向断言；实测三态 `('15','15')` / 改 main `('14','15')` / 改机器锚 `('15','16')`。
- **守卫锚同步**：`WORDING_POSITIVE` 的 fuzz 条目增 `CURRENT_BASELINE` 存活锚，正向锚 13 → **14**，逐锚回退 16 → **17** 次（单一事实源自动覆盖，fuzz 代码无需改）。
- **消除 SyntaxWarning**：docstring 内不再写含反斜杠的正则字面量。
- **悬空引用**：`AUDIT_STATE.md` §16 / §17 的 research-ops commit 指引改为真实历史 hash `303c42e` / `49135e5`；v1.5.12 治理同步文档发布链落最终 hash。

### Changed
- 四处 version = **1.5.12**；`integrity_manifest.json` 重生成；包外锚受控刷新；LEARNINGS +1（LRN-029）；决策台账 +1 条真实裁决。
- 用例数不变：fuzz **60/60**、守卫 **11/11**、V7 **7/7**、pytest **18 passed**。

---

## [1.5.11] - 2026-11-10（终验盲检 R6 · 防线自审漏洞补齐）

> 版本口径：v1.5.10 的独立终验盲检**再次证伪「零挂账」**——这次抓的不是旧口径残留，而是本轮新防线自身的 3 个洞。v1.5.10 [Added] 段 ③④ 的声称与实现不符（③只回退 1 个锚却写「整包改回旧口径」；④`re.search` 命中 docstring 自己却写「比对 `main()`」），属新写入的假陈述。本节为当前口径，[1.5.10] 段保留为历史记录。

### Fixed
- **正向锚补日期**：守卫第 11 项增加 `last_updated: 2026-11-10` 正向锚；实测把日期改成任意非 `2026-10-14` 的旧值不再能全绿通过。
- **自证假防线修复**：`tests/test_gate_fuzz.py` 新增 `_wording_counts(src)`，`total` 只在 `main()` 函数体内取（原全文 `re.search` 先命中 docstring 里的同一句话），并新增反向断言「仅改 `main()` 的 total 必被抓到」。实测改成 `+14` 立刻暴露。
- **反向覆盖补全**：`test_current_wording_guard` 第 3 步由「只改 1 个文件 1 个锚」扩为**逐锚回退**——5 文件 13 个正向锚逐个摘除 + 3 个旧口径串逐个注入，共 16 次，每次都断言第 11 项真实 FAIL。
- **单一事实源 + 提速**：`WORDING_POSITIVE` / `WORDING_NEGATIVE` 提为 `test_contract_guard.py` 模块级常量，守卫与反向用例共用；新增 `check_current_wording(pkg_root)` 独立函数，`_checks_at` 第 11 项直接 append 其返回值，**接线由行为级用例断言**（`res[10] == check_current_wording(PKG)`）。反向用例只调该函数并只复制被检 5 文件，实测 **157s → 约 10s**（`pytest --durations` 单次实测），不必 16 次跑完整守卫的 git / sha / 冒烟；全套 18 passed。

### Changed
- 四处 version = **1.5.11**；`integrity_manifest.json` 重生成；包外锚受控刷新；`.learnings/LEARNINGS.md` +1（LRN-028）。
- 用例数不变：fuzz **60/60**（45 CASES + 15 行为级）、守卫 **11/11**、V7 **7/7**、pytest **18 passed**。

### 终验
pytest **18 passed** ｜ fuzz **60/60** ｜ 守卫 **11/11** ｜ V7 **7/7** ｜ contracts / scope / manifest `--check` 全绿 ｜ 21 脚本编译+help ｜ 四处 version=1.5.11 ｜ 台账 HEALTHY ｜ 包外锚 21/21 且 `source.commit == HEAD`。

---

## [1.5.10] - 2026-11-10（L3 盲检 R5 · 当前口径一致性补正与防复发）

> 版本口径：v1.5.9 §15 宣布「零挂账」，但独立只读盲检实证**不成立**——代码已升到 G1-G6，而 CLI help、权威门表、主理人活跃 T1 条款仍写 G1-G5 五门，cron 锁注释仍写已废弃的 mkdir 目录锁，fuzz docstring 用例数停在 v1.5.8，且全量测试仍全绿。根因是 v1.5.9 守卫第 10 项只锚「脚本存在」，未锚「权威文档的当前口径」。本版补 5 项口径 + 1 项防复发守卫，不重开 v1.5.7 已闭环的 L3 收敛判据。

### Fixed
- **CLI help**：`scripts/check_gates.py` argparse description `G1-G5` → `G1-G6 一条命令全查（G6 抽查留痕默认 SKIP，--require-evidence-check 可启用）`。
- **权威门表**：`skills/viral-evo-core/references/quality-gates.md` 补 G6 行（≥2 条 lead evidence_check / 默认 SKIP 写 `skipped_gates` / 启用后 FAIL）、补「G6 默认不强制」与退出码口径、frontmatter `last_updated` 2026-10-14 → 2026-11-10。
- **主理人操作规程**：`agents/viral-evo-lab-team-lead.md` 三处活跃条款（质量门控 §2 定义、T1 清单、全门禁一条命令）由「G1–G5 五门齐查」统一为「G1–G6 六门齐查」并补 G6 启用条件——这是 v1.5.9 文档真化清单**漏掉**的文件。
- **cron 锁注释**：`scripts/cron_watch.sh` 头部「mkdir 原子锁」→「noclobber（O_EXCL）文件锁」，退出码契约补「锁冲突跳过 EXIT=0 / poll 其它退出码透传」，与同文件 :45 修复后实现一致。
- **fuzz docstring**：补 v1.5.10 当前基线段（行为级 9→15、45 CASES + 15 = 60/60、`total = len(CASES) + 15`），明确上方 v1.5.8 段为历史记录。
- **文字残留**：`test_vendor_core.py` 头部补 V7 检查项、注释「≥9 / 14」→「≥11 / ≈18」；`gen_integrity_manifest.py` 用法补 `exit 2 = git 不可用`。

### Added
- **守卫第 11 项「当前口径一致性守卫」**：正/负双向锚锁定 5 个文件的当前口径（G1-G6 / G6 门表行 / 六门齐查 / noclobber / `len(CASES) + 15`），并显式禁止旧口径字符串（`五门齐查` / `mkdir 原子锁` / `last_updated: 2026-10-14`）回潮。
- **`test_current_wording_guard` 行为级用例**：①真跑 `--help` 断言含 G1-G6；②真加载守卫断言当前包第 11 项 PASS；③复制整包改回旧口径，**断言第 11 项真实 FAIL**（防恒真）；④正则比对 docstring 与 `main()` 的用例数一致。
- **V7 互锚升级**：项数下限 10 → 11 + 第 11 项标题锚；守卫头部「校验十项」→「十一项」。

### Changed
- 四处 version = **1.5.10**；`integrity_manifest.json` 重生成；包外锚受控刷新；SOP 三处 T-D1 历史行追加销项索引（不改写历史文本）。

### 终验
pytest **18 passed** ｜ fuzz **60/60**（45+15）｜ 守卫 **11/11** ｜ V7 **7/7** ｜ contracts / scope / manifest / 21 脚本编译+help 全绿 ｜ CLI `--help` 含 G1-G6 ｜ 包外锚 21/21 且 `source.commit == HEAD`。

---

## [1.5.9] - 2026-11-10（「裁决与真实未完成」清理轮 · 七项全部闭合）

> 版本口径：v1.5.8 的 §14 收轮把 1 项裁决与 6 项真实未完成列为「不施工 / 不代写 / mitigated」。本版按用户「妥善完成裁决与真实未完成，直至全部任务完成」的显式授权，把**全部 7 项转为施工项并闭合**；不重开 v1.5.7 已闭环的 L3 盲检循环。v1.5.8 的「明确不做」三条理由在本版失效，已逐条给出实现与边界。

### Added
- **ADR-001 正式裁决 + 机器消费端**：`docs/ADR-001_require_tag_default_off.md`（人读）、`docs/decision_records.json`（机器真源，4 条裁决含 `enable_when` / `migration` / `verification`）、`scripts/check_decision_records.py`（只读校验，三处 CLI 必须仍为 `action="store_true"` 且无 `default=True`，测试锚必须存活；`0 一致 / 3 结构 / 5 VIOLATION`）。**裁决从「一句话」升级为可验证契约**，防未来悄悄翻转默认值。
- **G6 抽查留痕硬门（SOP T-D1 销项）**：`scripts/verify_evidence_check.py`（`≥2` 条 `evidence_check`、`actor=lead`、`file:行号 + excerpt + reason`；`0/3/5`），接入 `check_gates.py --require-evidence-check` 与 `evidence_check_policy.json`。ADR-002 裁决**默认不强制**，但 SKIP 写入 `gates.json` 的 `skipped_gates`——不把「没检查」伪装成 PASS。只验形式要件，语义真伪仍归主理人 T1。
- **语义对账半自动化（ADR-004）**：`scripts/reconcile_decisions.py` 只读扫描 waivers/gates/checklist/manifest/策略文件，输出 `matched` / `unmatched` 候选与 `[DRAFT·待人工终裁]` CSV；**拒绝写入台账或同名文件**（EXIT=3）。机器缩小人工核对面，逐条终裁仍属 T2。
- **包外锚受控刷新（ADR-003，mitigated → fixed）**：`check_baseline_anchors.py --refresh` 须 `--i-acknowledge-refresh` + `--reason` + 干净 git 工作区 + 锚在包外 + 被锚文件齐全；写 `refresh_history` 与可选治理仓 `--git-log`；check 侧校验 `source.commit == git HEAD` 与 history 末条，防「改锚刷绿」。默认仍只读。
- **P4 B-5 cron 巡检资产**：`scripts/cron_watch.sh`（manifest 汇总 task_id → 逐个 `poll_run_dir.py --from-manifest` → `cron_watch.jsonl` 留痕 + 原子锁）、`scripts/install_cron_watch.sh`（**dry-run 默认**，`--install/--uninstall` 幂等标记块，`CRONTAB_BIN` 可替身）。未执行 `--install`，**系统 crontab 零改动**（权限红线）。
- **`VENDOR_PROVENANCE.md`（审计区）**：V2 联邦真源归属实证核实销项。

### Changed
- `check_gates.py`：门禁清单 G1-G5 → **G1-G6**；`write_report()` 增 `skipped_gates`；G3 早退也记「G6 未评估」。既有 45 个 fuzz 用例与 `EXIT=0/3/5` 契约不变。
- 回归基线：行为级用例 9 → **14**（+裁决防翻转 / G6 硬门 / 语义对账 / 锚刷新 / cron 资产），独立跑合计 **59/59**；守卫 9 → **10**（第 10 项「ADR/G6/B-5 修复存活守卫」）；V7 金丝雀项数下限 9 → **10** + 新标题锚。
- 文档真化：`CLAUDE.md` 追加 v1.5.9 订正节；`docs/P4_monitoring_design.md` B-5 销项；`skills/viral-evo-core/SKILL.md` 工具表补 6 个脚本；`docs/authorization_matrix.md` 补 ADR-004 口径；SOP `T-A1_测试报告.md` / `00_交付报告.md` T-D1 追加销项标注（保留历史文本）；审计区 `ROUND2_SUMMARY.md` §4 追加 V2/B-5 销项。
- **决策台账补落**：按本轮授权以 archivist 代行，向 `research-ops/00_governance/decision_log.csv` 追加 **5 条真实裁决**（6 → 11 条），审计 `HEALTHY/EXIT=0`、`age_days=0`。包内脚本仍**不代写台账**（ADR-004 不变），这是一次性治理落盘。
- 四处 version → **1.5.9**；`integrity_manifest.json` 重生成；包外 `BASELINE_ANCHORS.json` 用 `--refresh` 更新并留 `refresh_history` + 治理仓 `anchor_refresh_log.jsonl`。

### Fixed
- **cron 锁死锁**：首轮测试实测 macOS 沙箱下 `rmdir` 返回 `Operation not permitted`，`mkdir` 目录锁清理失败会永久跳过后续巡检 → 改 `noclobber`（O_EXCL）文件锁 + `rm -f`，并用行为级用例锁定「锁必须清理」。
- **VENDOR.json 口径偏差**：实证 `upstream_repo: my-experts/viral-evo-lab` 与真源所属仓不符；按联邦红线**不改 vendor**，在 `VENDOR_PROVENANCE.md` 记录偏差与正确修复通道。

### 闭合对照（v1.5.8 §14「裁决与真实未完成」7 项）
| 项 | v1.5.8 状态 | v1.5.9 处置 |
|---|---|---|
| `--require-tag` 裁决只落结论 | 不改代码 | ADR-001 + 防翻转守卫（**保持默认关闭**） |
| G6 抽查门 | 明确不施工 | 硬门落地 + G6 接线 + SOP T-D1 销项 |
| 语义对账纯人工 | 人工 T2 | `reconcile_decisions.py` 机器候选 + 人工终裁 |
| 包外锚 mitigated | 人工手算刷新 | 受控刷新 + 防刷绿校验 → **fixed** |
| 台账 25 天未更新 | 本轮不代写 | 授权补落 5 条真实裁决，HEALTHY |
| V2 联邦归属 | 外部依赖 | 实证核实 → `VENDOR_PROVENANCE.md` |
| P4 B-5 cron | 未排期 | 资产落地 + 显式安装器（不自动装） |

---

## [1.5.8] - 2026-11-09（遗留 backlog 清理轮 · 生产者-消费者闭环 + 门禁失败留痕）

> 版本口径：v1.5.7 已按「连续 2 轮无 🔴」宣布循环审计闭环。本版**不重开审计循环**，仅清理 `AUDIT_STATE.md` §13 实证清单里的 2 项 🔴 P0 + 3 项 🟠 P1 + 2 项 🟡 P2；⚪ P3 三项**列明真实未完成，不施工、不伪装**。

### Added
- **P0-1 · `scripts/audit_decision_log.py`**：补齐 `decision_log.csv` 的**零消费端**断链（LRN-014「只写不读」同构）。只读审计四查（结构 / 必填字段 / tier 白名单 / 陈旧阈值），退出码 `0 健康 / 3 结构失败 / 5 内容违规 / 6 陈旧提醒`，`--json` 供机器消费。**不代写台账、不做语义级裁决对账**（自由文本机械匹配不可靠，仍属主理人 T2 人工纪律）。实测：真实台账 `HEALTHY/EXIT=0`；`--max-age-days 1` → `STALE/EXIT=6`；缺文件 / 缺列 / 条目不足 / 空值 / 坏 ts / 坏档位 六形态退出码全按契约。
- **P2-7 · `scripts/check_baseline_anchors.py` + 包外锚文件**：以 `--anchors <包外 JSON>` 对关键防线文件做 sha256 只读对账（`0 一致 / 3 结构 / 5 漂移`），路径不硬编码。锚文件落在审计区 `viral-evo-lab-audit/BASELINE_ANCHORS.json`，使「双测试文件同时被旧基线覆盖」有**包外独立参照**可查，不再只靠包内互锚 + 人工 diff。

### Fixed
- **P0-2 · G3 FAIL 零留痕**：`check_gates.py` 原 `if not g3: return 3` 在报告落盘前早退，门禁失败无报告。抽出 `write_report()` 供早退与正常路径共用（单一事实源），**`EXIT=3` 契约不变**，失败也落 `<task_id>__gates.json`。守卫仍在写盘前调用，只读区 `EXIT=7` 不变。补行为级回归：断言报告落盘、verdict=FAIL、G3=false，以及补产出后重跑的报告覆盖语义。
- **P1-4 · `CLAUDE.md` 三/四 JSON 硬冲突**：L69「四 JSON 真源」与 L81「三 .json 为真源」并存；L81 订正为四 .json，与 v1.5.2 订正节及 `render_context_stack.py` RENDERERS 一致。
- **P0-1 配套 · 文档真化**：`docs/authorization_matrix.md` §四 补消费端脚本；§五 记录义务里 v1.5.4 编号3 的「当前无脚本审计 / 脚本化列入 backlog」订正为准确口径（脚本只验台账健康，语义级裁决对账仍属人工）。`CLAUDE.md` 追加 v1.5.8 订正节，销掉 v1.5.0「decision_log 审计例行化」待办与 v1.5.2「下一轮评估」；历史条目本身**保留不改**。
- **P1-5 · 审计区文档漂移**：`ROUND2_SUMMARY.md` §4 已销项仍列 backlog、`agent-harness-sop/CLEANUP_CHECKLIST.md` §五「未推送」与实测 `0 0` 不符 → **保留历史文本 + 追加销项/订正标注**，不改写历史。

### Changed
- **P1-3 · `--require-tag` 默认值裁决（只落结论，不改代码）**：**保持默认关闭**。① `test_require_tag_gate` 已断言默认关闭的向后兼容契约，翻转即破坏已发布行为；② 存量权威源多数未打 `source_tag: authoritative`，翻转会误杀；③ 严审场景显式传参即可。CHANGELOG v1.5.2 Known Issues「下一轮评估是否翻转默认值」**销项**。
- **P2-6 · D2 质量维度扩展**：team-lead MD 的 D2 适用面从「仅 WF5/WF6」扩展到追问 / 4R / Gödel 三分支的**轻量级质量终止判据**（连续 2 轮无新增实质问题 + 关键质疑已闭环 + checklist 留痕），与「全局重试 ≤5」并行而非替代。仍为文档级判据，不虚构机器计数。
- **回归基线升级**：fuzz 行为级 6 → **9**（新增 G3 早退落盘 / decision_log 退出码 / 基线锚对账），守卫 8 → **9** 项（新增第 9 项「P0 修复存活守卫」：锚脚本、统一落盘、三处行为级用例名），V7 金丝雀项数下限 8 → **9** 同步。

### Known Issues（本轮真实未完成，不阻塞）
- ⚪ P3 · **agent-harness-sop T-D1「G6 抽查门」实测不存在**，属另一战线（需 `check_gates.py` 改造 + 红线评估，估 4h），本版不实现、不伪装已完成；已在 `04-test/00_交付报告.md` 标注真实状态。
- ⚪ P3 · V2 联邦真源仓库归属核实（外部依赖，需人工）、P4 B-5 cron 巡检（跨会话场景，未排期）——均不施工，理由见 `AUDIT_STATE.md` §13。
- 🟡 语义级「某裁决是否有对应 `decision_log` 条目」仍无机械对账（诚实声明，同 P0-1 边界）。

### Verification
- pytest **12 passed** | fuzz **54/54** | 守卫 **9/9** | contracts / scope / manifest `--check` 全绿 | 四处 version=1.5.8
- 新增行为级用例全绿：G3 FAIL 落盘 + 覆盖语义 / decision_log 八形态退出码 + 台账字节不变 / 基线锚一致与篡改双态

## [1.5.7] - 2026-11-09（第四轮盲检收敛计数 · 零🔴零🟡 + 低危清理）

> 版本口径：第四轮 L3 独立盲检对 v1.5.6 复核——**零 🔴 零 🟡**（收敛计 1 轮），3 项 🟢 观察项随本版清理。v1.5.6 的 mkdir 回归修复经新 run-dir 全链路实测确认；前两轮成果（守卫三态/白名单/金丝雀/render 可见性）无一被破坏；退出码契约经五个破坏性场景实测无击穿。

### Changed
- 🟢 SPOF_INVENTORY：render 缺失不落痕条目销项（v1.5.6 已落地，四轮盲检 B-d 实测确认）。
- 🟢 guard 空转警告改「进程内一次」：函数属性标记会随 `_load_guard` 每次 `exec_module` 重置（六脚本各自加载新实例，同进程重复打印）——标记挂 `sys` 模块，跨实例存活，实测 3 次调用仅 1 条。
- 🟢 poll member 白名单增 64 字符长度上限（防超长标识符进文件名；超长判畸形，fail-safe 方向）。

### Verification
- pytest **9 passed** | fuzz **51/51** | 守卫 **8/8** | 四处 version=1.5.7
- 四轮盲检 B-a~B-e 五场景全过：mkdir 全链路 EXIT=0 双落盘 / 白名单 3 过 8 拦 / 金丝雀 cnt=12≥8 / render 缺失汇总 / 归档区 EXIT=7 零残留

## [1.5.6] - 2026-11-09（第三轮再诊断回补 · 守卫接线回归修复）

> 版本口径：第三轮 L3 独立盲检（对 v1.5.5）发现 **1 🔴（施工自引入回归）+ 3 🟡 + 4 项低成本 backlog**，本版全部闭环。收敛计数：本轮 🔴 仍为接线施工自引入（mkdir 被误当写盘点替换），修复后进入第 4 轮收敛计数。

### Fixed
- **🔴 · assemble `--run-dir` mkdir 被守卫接线误删（施工自引入回归，实测复现）**：v1.5.5 Y4 接线时把幂等建目录 `rd.mkdir(...)` **替换**为守卫调用——新任务 run_dir 不存在 → sidecar 落盘 `FileNotFoundError`（EXIT=1 未在退出码契约）+ spawn 主产物丢失，主理人 P0 强制派工链路（`--run-dir ... --out ...`）在新任务上必崩。现恢复 mkdir（守卫通过后幂等建目录，两者本不冲突）。实测：新 run-dir 全链路 EXIT=0，sidecar + 主产物双落盘。
- **🟡 · poll manifest member 校验过宽（「防路径探测」名不符实）**：黑名单拦不住空格/大写/`$VAR`（`UPPER` 在 APFS 还能匹配 `upper.md`，跨平台行为分裂）。收紧为白名单 `[a-z0-9][a-z0-9-]*`（与 9 名成员 ID 形态精确对齐）。实测：`literature-scout`/`a-1` 通过；`a b`/`UPPER`/`../x`/`.h`/`a:b` 全判畸形。
- **🟡 · `_read_manifest_with_retry` 不捕 UnicodeDecodeError**：非 UTF-8 manifest 直接 traceback（退出码契约 0/5 被击穿）。现归入重试失败路径。实测 UTF-16 manifest → 3 次退避日志 + EXIT=5。
- **🟡 · assemble 退出码表缺 7**：v1.5.5 三处守卫接线后 EXIT=7 未声明，主理人按表误判。退出码表补 `7 = 写目标命中只读区`。
- **🟢 · 四项**：poll docstring「头 3 行」→「头 8 行」（修 Y3 时漏改模块头）；V7 死变量 `m_cnt` 删除；render_context_stack 缺失 JSON 结束前 stderr 汇总（SPOF_INVENTORY backlog 清项，实测 2 缺失 → `⚠ 2 个 JSON 缺失（未渲染）…`）；主理人 MD `.harness-runs`→`_harness_runs` 命名统一（遗留分裂）。
- **文档销项**：v1.5.4 Known Issues「RESEARCH_OPS_DIR 未设守卫根为空」已被 v1.5.5 Y5 空转警告覆盖，标注销项。

### Verification
- pytest **9 passed** | fuzz **51/51** | 守卫 **8/8** | contracts/scope 全绿 | 四处 version=1.5.6
- 关键实测：新 run-dir 全链路 EXIT=0 双落盘 / UTF-16 manifest 退避+EXIT=5 / 白名单 2 过 5 拦 / render 缺失汇总 2 场景

## [1.5.5] - 2026-11-09（第二轮再诊断盲检回补 · L3 九项发现闭环）

> 版本口径：v1.5.4 经 L3 独立盲检**不收敛**（2 🔴 + 7 🟡 + 4 低危），本版为盲检回补发版。全部改动为「修复 / 加固 / 口径同步」，v1.5.4 引入的新机制（互锚/撞限消费/manifest 读取/只读守卫）全部保留并加固。

### Fixed
- **🔴 R1 · V7 互锚语义空壳化绕过（已实验证实并修复）**：盲检实测——把守卫 `_checks` 改恒真但保留全部锚字符串，V7 仍 PASS（字符串锚与守卫第 7 项自己批评的「只锚函数名」缺陷同构）。现 V7 三层加固：① **项数下限**（守卫断言数 <8 即 FAIL，静态计数）；② **行为金丝雀**（`_checks_at(pkg)` 参数化新入口，V7 真加载守卫模块 + 拷贝包到临时目录 + 注入畸形 manifest → 断言第 3 项真实 FAIL）；③ 锚字符串保留。实测四级攻击（恒真 1 条 / 恒真 8 条 / 伪造真实形态 append / 8×`out.append((True`）全部被 V7 = FAIL 拦截。
- **🔴 R2 · 只读守卫根与文档工作流冲突（已实验证实并收窄）**：盲检实测——设 `RESEARCH_OPS_DIR` 后按文档维护 context_stack、按 poll 示例跑 run_dir 全被自家守卫 EXIT=7 阻断（守卫拦整根 vs 工作流就在根下）。现默认只读根**收窄为 `research-ops/_archive/`**（归档/历史快照区 = LRN-012 事故现场，覆写即篡改证据）；`_harness_runs/`（演练区）与 `context_stack/`（维护流）放行；真源子目录可 `VIRAL_EVO_READONLY_DENY` 显式追加。实测：_archive → EXIT=7，_harness_runs/context_stack → EXIT=0。
- **🟡 Y1 · poll manifest 重试被二次裸读架空**：重试取回全文后 86 行又 `mf.read_text()` 重新读盘（TOCTOU + 二次 OSError 会 traceback 违反退出码契约）。改为消费已取回的 `txt`。
- **🟡 Y2 · macOS 大小写不敏感绕过（已实写证实）**：纯字符串前缀比对可被大小写变体绕过并在 APFS 实写成功。前缀比对统一 `.lower()` 折叠（normcase 在 darwin 不折叠大小写，不可用）。实测四态：正写拦 / `_ARCHIVE` 拦 / 全路径变体拦 / `_archive_new` 放。
- **🟡 Y3 · 撞限标注位置规避 + 读失败偏放行**：窗口 3→8 行（标注落第 5 行已可检出，实测）；`head_hit_limit` 读失败从「无标注=完成」改「保守=撞限嫌疑交人工」（目录冒充文件实测 EXIT=5）。
- **🟡 Y4 · assemble_spawn_prompt 三处写盘未接守卫（双口径打架）**：workflow sidecar / run_dir mkdir / --out 三写盘点全部接线（现 6 脚本 8 调用点，SKILL.md 口径同步）。
- **🟡 Y5 · 守卫空转静默**：未设任何只读根时打一次性 stderr 警告（不静默放行）。
- **🟡 Y6 · _load_guard 捕获面过窄**：五脚本 `except (OSError, SyntaxError)` → `except Exception`（半损坏/None loader 也降级不崩溃，兑现「加载失败不阻断」）。
- **🟡 Y7 · manifest member 路径注入 + BOM 静默吞行**：member 含 `/` `\` `..` 前导点等路径成分 → 判畸形（防 G3/G4 读路径探测）；manifest 读取剥 UTF-8 BOM（实测 BOM 首条记录不再被静默跳过）。
- **🟢 O1/O2/O3/O4/O5**：退避日志显示真实等待秒数（原打印墙钟秒针值）+ 文档「最多等 6s」口径；`--expected`+`--from-manifest` 同传打警告；主理人 MD 两处「。，/。。」双标点；guard CLI 补 `--allow-readonly` 旗标（docstring 已承诺）；CHANGELOG 守卫项数「7→9 vs 8/8」矛盾统一为 7→8。

### Changed
- `test_contract_guard.py`：`_checks()` 拆为 `_checks_at(pkg_root)` 参数化入口（金丝雀注入用），`_checks()` 保持向后兼容转调。
- 文档同步：team-lead 只读区条款收窄口径、SKILL.md guard 行、SPOF_INVENTORY 补守卫根行、guard docstring 判定规则重写。

### Verification
- pytest **9 passed** | fuzz **51/51** | 守卫 **8/8** | contracts/scope 全绿 | 四处 version=1.5.5
- R1 攻击矩阵 4/4 被 V7 拦截；R2 三态（拦/放/放）实测；Y1-Y7 逐项复现→修复→复测通过

## [1.5.4] - 2026-11-09（任务 B 十编号对齐施工 · 断链接线与防复发）

> 版本口径：任务 B（编号 1/2/3/4/5/6/9/10/12/13）第一阶段对齐方案经用户 GATE 2 放行后的施工发版。三批次（B1 断链接线 / B2 只读守卫与重试 / B3 文档增补）一次交付；全部改动为「接线 / 补测试 / 口径订正 / 维度增补」，**零重新设计已闭合机制**。

### Added
- **R-13b 🔴 守卫互锚（决定性新发现修复）**：实测发现 `test_contract_guard.py` 自身无任何锚定——空壳化 + 重生成 manifest 后 EXIT=0 全静默（历史事故「tests 被旧基线覆盖 → CI 静默 0 覆盖」的同构复发路径，当前零防御）。现 `test_vendor_core.py` 新增 **V7 守卫互锚**：反向锚定守卫文件的 `_checks`/`test_contract_guard`/`sys.exit(main())`/守卫标题等 6 锚点；删守卫 → V7 FAIL，删 vendor_core → 守卫第 1 项 FAIL，**双向互锚**（残余风险：双文件同时覆盖 → Known Issues，缓解 = 施工前后必跑守卫）。
- **R-13b fuzz 语料下限**：实测 fuzz CASES 可抽稀 45→1 而守卫全过（只锚函数名不锚数量）。现守卫第 7 项增 CASES ≥40 下限断言（拦删减不拦扩展），实测抽稀至 35 条 → `❌ CASES 仅 35 条（<40 下限）——疑遭抽稀` EXIT=1。
- **R-13a 🔴 撞限标注消费（决定性新发现修复）**：实测带 `<!-- 轮次耗尽 -->` 头部标注的 artifact 被 `poll_run_dir.py` 判 READY/EXIT=0（主理人「无标注 = Phase 完成」的续跑判据在代码侧落空）。现 poll 读每个 artifact 头 3 行，命中「轮次耗尽」→ 新增「撞限」分类 + NOT_READY/EXIT=5 + 明确提示「不得收 envelope」。实测：撞限 1 → `NOT_READY（撞限 1）`。
- **R-13c spawn_manifest 读取接线**：manifest 此前**只写不读**（穷举 grep 仅 log_spawn.py 自身 2 处；续跑三步判定的第 1 步「读 spawn_manifest」无代码实现）。现 `poll_run_dir.py` 新增 `--from-manifest`：从 manifest 自动生成期望清单（`--expected` 保留为显式覆盖项）；manifest 缺失 → EXIT=5 不静默放行。
- **R-10a 只读区写盘守卫**：新增 `scripts/guard_readonly.py`——`check_write_target(path)` 按 `VIRAL_EVO_READONLY_DENY` 显式清单 + `RESEARCH_OPS_DIR` 兜底判定只读区，命中即 EXIT=7；逃生开关 `VIRAL_EVO_ALLOW_READONLY=1`。**接线 5 个写盘脚本**（check_gates / verify_member_output / write_checklist / log_spawn / render_context_stack）写盘前调用；加载失败降级为无守卫（不阻断）。实测复现 LEARNINGS-012 事故场景（只读区跑 check_gates）：修复前 gates.json 落入只读区，修复后 **EXIT=7 且零落盘**；正常工作区行为逐字节不变。
- **R-10b 重试与降级接线**：① poll manifest 读取加 3 次指数退避（2s/4s/8s，失败原因写 stderr——P4 B-4 从「未排期」转「部分落地」）；② find_knowledge 三处 subprocess 补 `run_cmd` 封装（returncode 检查 + 单次重试，rg/grep 无命中 returncode=1 不误重试）；③ 主理人 MD 增「本地降级检索」条款：联网检索全失败 → `find_knowledge.py` 扫本地三仓 + 信封标注 `[本地知识库降级检索]`（「联网失败→本地库」从文档声明变流程接线）。
- **R-12a legacy 回退测试锁定**：`--legacy-package-check` 回退链此前**零测试覆盖**（实测可放行 V5 拒收的散文包 = 真实退化通道，可能被静默改动）。新增行为级测试：V5 拒收散文包（EXIT=4）→ `--legacy-package-check` 放行（EXIT=0, mode=legacy-forced）。
- **R-12b 单点故障清单**：新增 `docs/SPOF_INVENTORY.md`（14 项依赖逐条「类型/降级/状态」+ 冗余编排现状 + 残余单点归属）；`gen_integrity_manifest.py` 的 git `check=True` 裸抛改为明确报错 EXIT=2。
- **编号1 坍缩三维扩展**：坍缩路由表增「三维度」（分析主题/数据集·基因段/领域匹配度——成员 frontmatter 新增 `domain:` 字段，9 员全配）+「坍缩确认」行（无坍缩行 = 任务对齐不完整）。
- **编号3 分歧协议补全**：authorization_matrix §五 从两步扩为四步（数据仲裁 → **多数共识**（≥3 非当事成员评审，票型落 decision_log）→ **用户终裁** → 记录义务）；仲裁输入接 literature-scout 4R R2 证据对比表；补 decision_log 对账诚实声明（无脚本审计，不虚构自动化）。
- **编号5 信封可选 next_action**：schema 增可选字段（≤120 字、描述动作不含成员名、非路由指令、G1 不校验）——与 E1 已删的 `next_agent_hint` 明确切割。
- **编号6 元审计触发条款**：主理人 MD 新增「每轮元审计收轮必须写 ≥1 条 LRN（含漏检维度）」+「修复后 1 轮内用守卫锚点回查改进落地」+ 空模板（ERRORS/FEATURE_REQUESTS）使用说明。
- **编号9 白名单真化**：validate_contracts 工具索引正则 6→13 脚本（原「全清单」名不符实）；SKILL.md 工具索引表 7→13 行（补 check_gates/hypothesis_watch/render_context_stack/log_spawn/poll_run_dir/guard_readonly/gen_integrity_manifest）。
- **SPOF/任务B状态**：见 docs/SPOF_INVENTORY.md 与工作空间 `viral-evo-lab-audit/MISSION_B_ALIGNMENT.md`。

### Fixed
- **P4 B-3 失效声明真化**：P4 文档曾标 B-3「✅ 已落地（v1.5.0）」，实测 T1 段无任何 poll 步骤。现已真实写入 T1 首位（收 envelope 前先 `poll_run_dir --from-manifest`，NOT_READY 不收），P4 条目订正并注明失效史。
- **信噪比 >70% 死声明作废**：主理人 MD 声明的「相关度 >70% 注入」全包唯一命中、无任何计算实现（render_context_stack 仅做 JSON→md 渲染）。订正为「全量注入固定清单 + 诚实声明作废死阈值」。
- **两仓分层污染泛化**：`predictive-virologist.md:54` 与 `frontier-2025-2026.md:16` 含项目特定位点叙事（HA Site 140 / H5Nx 框架 A），泛化为领域通用表述（复扫 + check_scope EXIT=0 clean）。

### Changed
- 主理人 MD：T1 增 poll 前置与 R-10a/R-10b 条款；坍缩路由表三维扩展；元审计触发条款；D2 适用面声明；maxTurns/全局重试预算口径诚实化（声明式定档无脚本校验 / 计数靠 checklist note，不虚构机器计数）。
- `P4_monitoring_design.md`：B-3 真化、B-4 部分落地订正。
- fuzz main() 行为级清单 3→6（+require_tag/poll_hitlimit/legacy_fallback），独立跑合计 **51/51**。
- 守卫校验项 7→**8**（第 7 项内嵌语料 ≥40 下限；新增第 8 项撞限巡检接线锚点）；vendor_core 检查项 V1-V6→**V1-V7**。

### Verification
- pytest **9 passed**（7 原有 + test_poll_hitlimit_and_manifest + test_legacy_package_check_fallback）
- fuzz **51/51**（45 用例 + 6 行为级）；守卫 **8/8**；contracts EXIT=0（白名单 13 脚本）；check_scope EXIT=0 clean；14 脚本编译 + `--help` 全过
- 沙箱实测：撞限标注 NOT_READY / --from-manifest 三态 / 守卫空壳化被 V7 抓获 / CASES 抽稀被下限抓获 / 只读区写盘 EXIT=7 零落盘 / 正常区行为不变 / legacy 回退两分支

### Known Issues（本轮新增/更新，不阻塞）
- 守卫互锚残余风险：两测试文件**同时**被旧基线覆盖时双向锚同时失效——缓解：施工前后必跑守卫（工程纪律）+ 轮报人工 `git diff <tag> -- tests/`（零成本人工锚）；完全防御需包外 CI 锚（backlog）。
- ~~`RESEARCH_OPS_DIR` 未设置时只读守卫兜底根为空~~（**v1.5.5 销项**：未设根时打一次性 stderr 警告，不再静默；三轮盲检确认）
- vendor 模板 `record_trace.py`/`progress.py` 死引用**不在本包 vendor 副本**（实测 grep=0，审计取证误报已订正）；如联邦层出现按 Known Issues 先例标「待联邦层修复」。

## [1.5.3] - 2026-11-09（L3 独立盲检回补 · 门禁诚实性收敛）

> 版本口径：v1.5.2 已提交推送（tag `v1.5.2`），但 L3 独立盲检发现 **2 个严重代码缺陷** + 3 项高危契约缺口，故 v1.5.2 **不视为真正收敛**。本版为**补丁级**回补发版，不新增内容生产环节，全部改动为「修复 / 接线 / 口径统一」。

### Fixed
- **严重 1 · `hypothesis_watch.py` 畸形输入崩溃**：三处 JSON 消费点直接 `.get()`/构造 `set`，畸形输入（顶层 list/str/null、非字符串元素、不可哈希元素）抛未捕获异常 → EXIT=1（契约只允许 0/3/5/6）、门禁静默失效。统一走 `load_json_obj()` / `extract_handled_ids()` / `_row_str()` 安全入口。
- **严重 2 · G4 声称可 waiver 放行但实际不读 waiver**：此前 G4 的提示与文档均声称「主理人核 URL 后写 waivers.json 放行」，实现**完全不读 waiver**——实测写好 waivers.json 后 G4 仍判 FAIL，文档承诺与代码行为背离，主理人只剩违反诚实性红线的「人工裁量跳过」。现 G4 消费同一 `<task-id>__waivers.json`：须 `value`+`reason`+`authorized_by` 三项齐全，且**覆盖全部未溯源数字**才放行（部分覆盖不解除阻断）。G2 同口径补授权校验。
- **高危 A-3 · G4 阻断态遮蔽 mtime 篡改检测**：原实现以 `if/elif` 组织，阻断态分支**短路**了 mtime 检测——实测「篡改 artifact + 写 waiver」可让全门禁 EXIT=0（击穿诚实性红线）。改为**两个独立判定**（篡改 / 阻断态），互不遮蔽。
- **高危 A-1 · `workflow` 字段无生产者 + 成员可自报规避**：`workflow` 全包无任何生产者 → G1 假说锚定校验在真实链路上是**死代码**；更深一层，成员自报 `WF1` 即可合法绕过 WF4 锚定强制（自报 = 自证清白）。按四段链路闭合：① `assemble_spawn_prompt.py --workflow` 新增参数（注入 spawn prompt + 落 sidecar `<run-dir>/<task_id>__workflow.json`）② 契约正本要求成员原样回传 ③ 门禁以 sidecar 类别（`analysis`/`other`）为判定权威源 ④ 双向交叉核验（缺失 / 降级 / 升级均 FAIL，表述差异不拦，**无 sidecar 的存量链路不误阻断**）。
- **高危 A-2 · workflow 归一化漏 11+ 变体**：`normalize_workflow()` 改为子串包含 + 正则判定，`wf4` / `WF4/analysis` / `WF4 分析执行` / `analysis` / `数据WF4` / `WF_4` 等全部触发；`no_hypothesis_justification` 允许并列写在信封顶层（与契约正本一致）。
- **中危 A-4 · 浮点候选集 G2/G4 分歧**：`verify_numbers.float_candidates` 提为单一事实源，两侧同口径。
- **中危 A-5 · `[待人工核验]` 处置路径只有文案无解析逻辑**：此前标注了也照样判 FAIL，主理人只剩文档明令禁止的「人工裁量跳过」。现逐数字解析放行（未标注的数字照常 FAIL，不整份免检）。
- **中危 A-6 · verdict 缺失在 block 态静默 PASS**：截断 output-check.json 即可绕过阻断。现 verdict 缺失视为未通过。
- **中危 A-7 · G5 只判文件存在不看判罚状态**：空壳 checklist（`{}` 或 `hallucinated>0`）与合规 checklist 等价。现须 `verdict=PASS`（缺失视为未通过）。
- **误阻断 · `--check-disposition` 拦死存量项目**：无任何待处置项的干净项目也因「台账文件不存在」返回 EXIT=6。现区分「无待处置项 + 池未超期 = 无需台账」（EXIT=0）与「确有未处置项/例行复核缺失」（EXIT=6）。
- **口径 A-8 · 退出码 3 与 6 的判别原则**：原「3 = 文件缺失或结构畸形」过于笼统，与「台账畸形按未处置计 → EXIT=6」矛盾。统一为**「坏掉后还能不能算出裁决」**：证据源（假说池 / ledger）畸形 → 无法算 late_fatal → EXIT=3；处置记录（state）畸形 → 证据源完好、保守按未处置 → EXIT=6。
- **口径 A-10 · 两类门控混列**：team-lead「质量门控」段把领域分析门与团队协作门并列，读者会误以为数据质控 = 数字溯源。拆为 ① 领域分析门（任务内成员自查）/ ② 团队协作门（回传后主理人跑脚本），并明确数字溯源属 T1 收产出环节、**不是** WF4 Phase 1 数据质控。
- **口径 A-11 · 退出码跨脚本套用风险**：team-lead T1 段（`check_gates.py` 0/3/5）与 T2 段（`hypothesis_watch.py` 0/5/6/3）相邻并列易被误读为同一套契约。显式声明不可互换、不可合并解读，两处各补本脚本完整退出码表。

### Changed
- `CLAUDE.md` 追加两节「当前口径订正」（v1.5.3 · L3 盲检回补 + A-1 链路闭合与文档口径统一），不改写任何历史条目。
- `team-contract.md` 信封 schema 增 `workflow` 字段 + 「workflow 回传规则」与「交叉核验为何必须以主理人下发声明为准」；`quality-gates.md` G1 行与文末增 workflow 交叉核验口径。
- 主理人 MD：装配命令增 `--workflow`、下行 task_payload 增 `workflow`、上行信封增 `workflow`、WF4 Phase 0 增 A-1 强制条款、T1 增 workflow 交叉核验条目、quality-gates 段拆两类门控、T1/T2 退出码表分列。
- `validate_contracts.py` 的 `--help` 文案改为动态读取条款数（原写死「7 条款」实为 8）。
- 四处 version 1.5.2 → 1.5.3；`integrity_manifest.json` 重生成（68 文件）。

### Verification
- pytest **7 passed**｜fuzz **48/48**（45 用例 + 3 行为级）｜guard **7/7**（新增第 7 项 A-1 存活守卫 9 锚点）｜contracts / scope / compileall / 13 脚本 `--help` 全绿
- L2 沙箱 **8/8** 全绿（真实链路：装配 → spawn 产物 → 成员产出 → 门禁）；新增 `sandbox/l2_a1_workflow.py`
- 实测复现并验证：A-3（篡改 + waiver → G4 FAIL）、A-6（verdict 缺失 + block → FAIL）、A-2（13 变体全触发 / 5 非分析类不误触发）、A-5（标注场景解除 / 未标注仍 FAIL）、A-1（10 场景矩阵全对）

### Known Issues（本轮新增，不阻塞）
- `--workflow` 未传时 sidecar 不落，G1 退回「只信信封」旧行为（成员自报可规避）——**依赖主理人执行纪律**，脚本无法从技术上强制「必须声明」。已写入主理人 MD 与 team-contract 强制条款。
- 存量 run_dir 无 sidecar，一律走旧行为（向后兼容优先）；如需回溯加固，须对存量 artifact 重跑装配流程。
- `hypothesis_watch.py --check-disposition` 对真实项目侧实测 EXIT=6（处置台账缺失）——**属 Loop B 项目数据侧，专家包不可代写**，需 archivist 落盘后复验。

## [1.5.2] - 2026-11-08（元层审计第 1 轮 · 洞察引擎闭环补丁）


> 版本口径：以 `purpose_charter`（假说优先 B>C>A / 科学真实性优先 / 诚实性红线 / 使命链完整 / 单一用户）重排施工优先级后的**补丁级**发版。施工前补 `v1.5.1` tag 锚点；A 桶 18 项已闭合机制一律未重新设计，全部改动为「接线 / 字段 / 前置条款 / 只读验收」。

### Added
- **C2 处置闭环只读验收**：`scripts/hypothesis_watch.py` 新增 `--check-disposition` 与 `check_disposition()`，纯只读判定处置台账存在性、结构、`handled_finding_ids` 覆盖全部 late_fatal、`reviewed_at` 有效性；退出码 6 = 处置缺失或不完整。主理人 MD T2 增「EXIT=6 禁止派发下一批 WF1/WF3/WF5」前置条款，T0 一并复核。
- **C3 严审闸三点接线**：`verify_numbers.py` / `verify_member_output.py` / `check_gates.py` 新增 `--require-tag` 并透传 `load_sources(..., require_tag=...)`；新增行为级测试 `test_require_tag_gate()` 与 guard 第 5 项「三点接线存活」，防接线被并发分发静默摘除。
- **C1 假说锚定字段**：`team-contract.md` 定义 `hypothesis_anchor`（`hypothesis_id` 或 `no_hypothesis_justification` + `biological_question` + `falsification_condition`）；`check_gates.py` G1 在 `workflow ∈ {WF4, ANALYSIS}` 时条件校验；`validate_contracts.py` 同步第 8 条契约；fuzz 24→27 例。主理人 MD 增「追问落盘」「A 类升维判定」「WF4 Phase 0」三处条款，使 B>C>A 从明文铁律变为可验收字段。

### Fixed
- **C4 返工阻断**：`--gate` 从死参数变为可传导信号——写入 `output-check.json` 的 `gate_mode=block`，G4 读到 DEGRADE 未处置即判 FAIL；主理人 MD 的「由主理人决定是否返工」订正为依 EXIT 码裁决 + 两条合法处置路径，不得仅凭人工裁量跳过。
- **B3 文档时态**：`docs/P4_monitoring_design.md` 末尾「建议排期：下一迭代执行 B-1/B-2/B-3」为过期文本（提交史 `0b3bed1` + tag `bc89fa1`/`6d3fad3` 已证落地），改为标注剩余 B-4/B-5 未排期。

### Changed
- `CLAUDE.md` 追加「当前口径订正」节（不改写历史条目）；四处 version 1.5.1 → 1.5.2；`integrity_manifest.json` 重生成（68 文件）。
- 验证：pytest **4 passed**（新增 1 个测试函数）｜fuzz **27/27**｜guard **5/5**｜contracts / scope / 13 脚本编译全绿｜L2 沙箱 12 组命令行演练全对。

### Known Issues（本轮新增，不阻塞）
- `--require-tag` 默认关闭（向后兼容）；严审任务须显式开启。默认态下未标记权威源仍可入池，属已知残余风险，下一轮评估是否翻转默认值。
- `hypothesis_watch.py --check-disposition` 对真实项目侧实测 EXIT=6（处置台账缺失）——**属 Loop B 项目数据侧，专家包不可代写**，需 archivist 落盘后复验。
- B 桶候补池未动：`dependency_artifacts` 假边、spawn_manifest 只写不读、三源零接入、P4 B-4/B-5、VG1–VG4 编号统一、vendor 两处联邦层已知问题。

## [1.5.1] - 2026-11-08（独立诊断 P1–P3 修复发版）

> **版本口径**：本轮为诊断驱动的结构修复，原记录于 `[Unreleased]`（2026-11-07），经 P3 三轮交叉验证 + 两轮收敛重测（重要级新 finding=0，D2 判据收敛）后由管家节点裁决定版 **1.5.1**。4 处 `plugin.json` / `marketplace.json` version 已同步升级。

### Added
- **A1**：`scripts/assemble_spawn_prompt.py` 经 importlib 消费 vendor 版 `check_task_package_v5`（JSON 五要素 + 验收三件套 + 占位值拒收）；新增 `--legacy-package-check` 回退开关；vendor 缺失时回退旧子串校验并输出显式告警
- **A3**：`scripts/gen_integrity_manifest.py`（`git ls-files` 全量清单，sha16 + bytes，`--check` 幂等校验）
- **A5**：主理人 MD「撞限与断点续跑协议」（成员落盘标注 partial / 主理人三步判定 / 续跑 2 轮仍撞限上报管家节点）
- **D2/D3**：Evaluator 收敛判据（连续 2 轮无重要级新 finding 即止）+ `docs/authorization_matrix.md` §五 分歧解决协议（数据仲裁 → 管家节点裁决 → decision_log 记录）
- **C2/C5**：`render_context_stack.py` import 前置修复；`validate_contracts.py` / `check_scope.py` 补 `--help`

### Fixed
- **A2**：`tests/test_vendor_core.py` 从 triz 复制残留订正（`_PKG_NAME`）、V6 恒假断言改为符合本包独立实现现实、补 pytest 可收集入口（此前收集 0 例 = CI 静默零覆盖）
- **A4**：CHANGELOG 补记 v1.1.1 / v1.2.6（该段合并收录 v1.2.1–v1.2.5 变更，未逐版本单列）/ v1.3.0–v1.3.2 / v1.4.0 / v1.5.0，逐条附 commit hash 溯源，排列改为最新在上
- **A6**：`.learnings/LEARNINGS.md` LRN-001/003/005/006 置 resolved（附 Resolution + commit）
- **B1–B10**：README 8→9 团员 + WF 5→7 条 + 悬空 `register_expert.py` 引用订正；`confirmed_hypotheses` 真源口径统一；maxTurns 唯一口径；权威源两层结构；CLAUDE.md 时间线订正；元数据三件套 version 统一 1.5.0；SKILL.md 索引 11 份 references 全覆盖；悬空引用与 P4 backlog 状态刷新；装配器 D′ 正则同源化；项目特定叙事从黑名单泛化为结构性信号
- **C1/C3/C4/C6/C7**：`hypothesis_watch` JSON 异常处理；`verify_member_output` artifact glob 排除元文件；`find_knowledge` 三仓路径环境变量可覆盖；年份正则 `20[0-2]\d` → `20\d{2}`；`check_gates` waiver 浮点容差匹配
- **P3-R1 fatal**：C7 引入的 `NameError`（未溯源数字 + 权威源存在时 G2 分支崩溃）已根治；装配器硬编码「9 份参考 / 8 个工具」计数漂移订正；旧 `check_task_package` 死代码清除
- **并发冲突处置**：10:13–10:14 另一工作线以旧基线覆盖 `tests/test_vendor_core.py` 致 A2 回退，本轮从已推送 commit `0b3bed1` 恢复；其 vendor v2.6.0（685 行，修 vendor 兜底态包根反推）升级**予以保留**

### Changed
- `vendor/shared-core/assemble_spawn_prompt.py` 随联邦真源两轮升级（最终状态以 `VENDOR.json` 的 `lines` / `sha256` 为准，本文档不再硬编码行数）；联邦真源 / vendor 副本 / 清单三方哈希实测一致
- `integrity_manifest.json` 重建为全量清单（覆盖 `git ls-files` 全部文件，条目数见 `file_count`；此前 55 项漂移 + 25 文件未覆盖，防篡改能力失能）

### Fixed（P3 第 2 轮交叉验证，2026-11-07）
- **高**：`check_gates.py` `load_waivers` 对 `value` 为 list/dict 的非法 waiver 抛 `unhashable TypeError` → G1–G5 全体失效；改为仅接受可哈希标量 + 异常类型扩充
- **中**：C7 重写时遗失「原始串/候选值精确匹配」→ 不可 float 化的合法放行条目静默失效；恢复精确匹配、候选值匹配、浮点容差三路并存（带单位值仍不放行，属设计边界）
- **中**：装配器 docstring 的 `669 行` / `1809085d` / `595 行` 未随 vendor v2.6.0 升级回改（实况 vendor `685` / `f2ced4c2`；本文件行数改由实测，不再硬编码）
- **中**：授权矩阵触发器计数 5 → 6（CHANGELOG 与主理人 MD 两处）；`quality-gates.md` 的 `git checkout` 指引与主理人 MD 的 settings.json 禁令互斥 → 补类型前置判定
- **低**：`verify_member_output` 元文件排除后缀补 `spawn_prompt`（对齐 LEAD_SUFFIXES 4 项）；tests 复制来源叙述自相矛盾；CLAUDE.md Changelog 区排列注释改为「非严格时间序」；A4 补记措辞订正

### Fixed（P3 第 3 轮交叉验证，2026-11-07）
- **中**：`check_gates.py` G4 消费 `output-check.json` 未做类型判定，顶层为数组/标量/null 时 `AttributeError` → EXIT=1、G5 与 gates.json 均不落盘（与 R2 修复的 load_waivers 崩溃同构，实测 4/4 崩）；补顶层/字段双重 isinstance + 异常类型扩充
- **中 F1**：主理人 MD 上行信封示例仍含 E1 已删的 `evidence` / `next_agent_hint` / `metrics`，与契约正本 6 必填 + `issues` 冲突（`validate_contracts.py` 对主理人 MD 有豁免，门禁抓不到）；示例与 VERIFY 说明对齐正本，装配器侧注释同步
- **中 F2**：CONTEXT_STACK 的 `knowledge_index` 真源口径在 lead-ops / CLAUDE.md / 主理人 MD / team-contract 四处不统一（三/四/五/六 混用，T2 仍指令手改 `.md`）；统一为「四 JSON 真源（以 `render_context_stack.py` RENDERERS 为权威源）+ 四 .md 渲染视图 + 三协议 .md」，T2 改写入 `.json` 后重渲染
- **低**：装配器 docstring 取消「本文件 N 行」硬编码（每改一次必漂移，R2→R3 连漂两次，改为指向 `wc -l` 实测）；`vendor B21` 代号刷新；`quality-gates.md` 与主理人 MD 补 `EXIT=3`；P3-R2 的 waiver 措辞订正（带单位值属设计边界，非回归）

### Fixed（P3.1 收敛重测，2026-11-07）
- **中**：`check_envelope()` 消费信封 `issues` 无类型判定，dict/int/bool 值 → 未捕获 TypeError、EXIT=1、gates.json 不落盘（同构模式第三次：R2 waivers → R3 output-check → P3.1 issues）；补类型判定，畸形值明确判 G1 FAIL
- **根治**：`check_gates.py` 增信封顶层 isinstance 防御 + main 调用处异常兜底（门禁脚本永不因单个畸形输入崩溃）；新增 `tests/test_gate_fuzz.py`（覆盖信封/waivers/output-check 全畸形形态，断言退出码 ∈ {0,3,5}、无 Traceback、gates.json 必落盘），纳入 pytest 自动回归——把逐点打补丁升级为同类缺陷自动拦截
- **中**：F2 CONTEXT_STACK 口径残留 6 处（主理人 MD 的 WF 读取步骤/迁移说明/T0 核验、research-diagnostician、README、archivist）全清；VG2 停用 E1 废弃的 `evidence` 字段名；`issues` 必填/可选口径在契约正本统一
- **低**：取消 CHANGELOG 中 manifest 文件数的硬编码（新增 fuzz 测试后条目数会变）
- **流程约束**：`gen_integrity_manifest.py` 以 `git ls-files` 为清单源，新增文件须先 `git add` 再重生成，否则静默漏收（本轮新增 fuzz 测试时实测命中）

### Fixed（P3.2 收敛终检与第二次并发处置，2026-11-07）
- **P3.2 收敛终检**：全新只读子代理 + 主理人独立静态复核双路并行，**重要级（高/中）新 finding = 0**，按 D2 判据收敛；P3 共 3 轮交叉验证 + 2 轮收敛重测（P3.1 / P3.2），逐轮产出并修复 R1 fatal、R2 高 1 中 3、R3 中 3、P3.1 中 2
- **第二次并发写入（17:43）**：联邦分发再次以旧基线 `e651ded` 覆盖 `tests/test_vendor_core.py`（A2 二次回退：包名变回 `triz-invention-team`、pytest 入口消失、CI 静默 0 覆盖），同时把 vendor 升到 694 行（注入「路由落盘提醒」，修 D2-1）并修正 `VENDOR.json` 的 `synced_at`。处置：从已推送 `d0bbf1e` 恢复 A2、保留合法升级（三方 sha256 实测一致）、不删除任何并发成果
- **防复发守卫**：新增 `tests/test_contract_guard.py`，把「每次手工救火」升级为常态自动判定——四项校验（A2 存活 / 四处 version / manifest 与磁盘及 `git ls-files` 一致 / vendor 三方哈希），每项独立异常兜底（守卫自身不因畸形输入崩溃），污染态实测正确报 2 FAIL，修复态全 PASS；纳入 pytest 自动回归
- **中**：`### Changed` 段硬编码的 `669 → 685 行` 随第二次升级再度漂移，改为指向 `VENDOR.json` 权威字段（与装配器行数硬编码同构的根治）
- **Known Issues 收敛**：`VENDOR.json` 的 `synced_at` 已由并发工作线回填为 `2026-11-07T17:43:24`，与 hash 自洽，原残留项销项

### Known Issues（残留，不阻塞）
- ~~本轮未升 version~~ → **已销项**：1.5.1 定版时同步升级 4 处 version 并重跑 `gen_integrity_manifest.py`
- `vendor/shared-core/assemble_spawn_prompt.py:544` 仍向 spawn prompt 注入 E1 已废弃的 `next_agent_hint` 字段规范（包内 `scripts/` 版已订正）。同属联邦真源镜像，**须在联邦真源层修复后重新分发**，本轮未擅改。**2026-11-08 复核**：vendor 副本与联邦真源 sha256 完全一致（`3c3648f1…`，694 行），确认为上游既有设计，维持「联邦真源层修复后分发」结论
- `vendor/shared-core/assemble_spawn_prompt.py:122` 命中首个 `vendor/shared-core` 段后 `break`（而非 `continue`），多层同名嵌套路径下会放弃扫描更内层真包根（隔离实测 EXIT 3）。**2026-11-08 复核**：同上，vendor=上游一致（`3c3648f1…`），属上游层既有设计，不在包内擅改

## [1.5.0] - 2026-10-15

### Added（补记，溯源 bc89fa1 / d03b08b / 431aca7）
- **R3 收官批 T-B1**：`scripts/poll_run_dir.py` 落盘巡检三件套（黄/红超时分级 + 缺失检测，轮询→事件驱动范式跃迁）
- **T-B2**：check_gates G1 信封类型校验强化（phase:int + confidence:0-100）
- **T-B3**：hypothesis_watch 假说池 KEY_FIELDS 漂移告警
- **T-C2**：decision_log.csv 首批 6 条真实条目（带来源溯源）
- **T-C4**：`--require-tag` 闸门（高危操作 git tag 锚点）
- **T-A1 准入门槛**：CLAUDE.md §1 子代理证据纪律（≥2 条 file:行号+原文摘录抽查，未过=未交付；87db1c8）
- **T-A1.1**：tester 返工闭环（267e749）
- vendor 联邦共享件兜底 + 防漂移门禁（9b61455）

### Fixed（补记）
- settings.json 补齐（Team 型 validate 强制项，agent=主理人 ID；07da845）
  - ⚠️ 2026-11-04 订正详见 1.2.0 条目内说明

## [1.4.0] - 2026-10-15

### Added（补记，溯源 6d3fad3）
- **R2-1 分级授权矩阵**：`docs/authorization_matrix.md`（影响半径×可逆性 7 类 + 6 条强制升级触发器 + 防自我授权落盘纪律）
- **R2-2 G2 waiver 态**：`<task-id>__waivers.json` 人工放行台账 → check_gates 扣减后 PASS
- **R2-3 spawn manifest**：`scripts/log_spawn.py` → spawn_manifest.jsonl（task_id↔agent_task_id↔装配产物）
- **R2-5 契约正本化**：`references/team-contract.md` 单一事实源（信封 schema+status 准则+团队要点）；9 成员 MD 去重 −10.8KB；assemble 注入契约全文
- **R2-4**：串行 handoff 首测（hypothesis-officer 消费 scout 产出，handoff 溯源 + 信息缺口自标）

### Fixed（补记）
- R2-6 ledger 非 closed 行清 closed_date；R2-7 render diff 跳过写放大；R2-8 float_candidates 抽公共；R2-10 issues 字段消费
- 修复者也被审计：本轮 R2 子代理抓出主理人侧 4 错误（zombie 指令/字符字节混淆/路由越权/16 文件日期笔误）全部当场修正

## [1.3.2] - 2026-10-15

### Fixed（补记，溯源 45e4eb2 / 1831028 / e80329e）
- phylo 路由表越权修复（选择压归 popgen-modeler，诊断子代理抓获）+ 16 文件日期笔误（2026-10-21→2026-10-14）补齐

## [1.3.1] - 2026-10-15

### Fixed（补记，溯源 2b32731）
- research-diagnostician 首测审计抓出的 6 缺陷修复

## [1.3.0] - 2026-10-15

### Added（补记，溯源 db9bb02，五维诊断修复 10 项）
- **D1 假说治理**：`scripts/hypothesis_watch.py`（假说池 last_updated vs ledger closed fatal/severe 时间差触发器）
- **D2 门禁数字化**：`scripts/check_gates.py` G1-G5 一条命令（信封解析/数字溯源/落盘/双留痕）
- **M1 spawn 现实化**：LRN-003 回退模式写入装配 docstring（平台 gap 文档化）
- **R1 lead MD 下沉**：CONTEXT_STACK 细则 → `references/lead-ops.md`
- **R2 双轨同步**：`scripts/render_context_stack.py` 4 份 md 一键重渲染
- **E1 信封瘦身**：9/9 成员删 next_agent_hint+metrics → 6 必填+issues
- **C2 路由判定表**：9/9 成员加"我接/我不接→谁接"表
- **E2/R4 路径注入瘦身**：spawn 载荷 −33~45%
- **M2 多员首测**：双员并行 spawn 实测
- maxTurns 推导规则入主理人 MD；quality-gates.md 增"团队级脚本化门禁"节

## [1.2.6] - 2026-10-14

### Added（补记，溯源 6920731 / c71f36c / bd97d17 / bee97d2 / 32364aa）
- **A 产出端核验**：`scripts/verify_member_output.py`（5 类数字模式产出端 grep 溯源 + `--gate`）
- **B skills 契约**：成员 MD 声明 skills 引用白名单
- **C P4 设计**：`docs/P4_monitoring_design.md` 慢通道监控预研
- **D spawn 演练**：单员/双员/串行 handoff 三轮真实 spawn 演练（T-DIAG-TEST 等）
- **T-B1/B2/B3 前身**：tag 快照锚点 + 知识态注入 + 数字核验关卡 + checklist 落盘（5f6362a）
- **V1 自动 verify + 装配版本注入 + check_scope 边界守卫**（f101da0）
- **C1 自动探测 + checklist schema + 跨仓知识入口**（f29d53c）
- **P3 六项轻改收尾**（9b99388）
- discipline-sentinel 融合：主理人 3 时点 8 项纪律审判 + research-diagnostician 职责扩展（4cce5ec，v1.2.1）
- LRN-005 登记：冒烟假数据曾入权威源池（已删 + README 防复发，3dbcbae）

## [1.2.0] - 2026-10-14

### Changed
- 角色数 11→10：medical-vet-bridge（柳通人）并入 literature-scout 坍缩协议（Anthropic 备份红线回归）
- 主理人编排规格升级：TeamCreate 强制流程 / 成员人设注入协议（装配脚本）/ Evaluator 反馈路由 / 动态资源分配表 / 慢通道启动前置门
- CLAUDE.md 双轨运行制落地（快=主会话单人格 / 慢=真实 spawn，仅限 WF5 红队+WF6 重大诊断）

### Added
- **信封契约**：9 成员 result_envelope 上行（6 必填字段）+ task_payload 下行 + VG1-VG4 门禁（v1.1.0）
- **工具权限最小化**：9 成员速查卡白名单（ANALYZER 禁 Write / 落盘归 archivist / 删除须二次确认）
- **编号纪律**：references/coordinate-mapping.md（比对列≠残基编号 / 跨亚型映射三铁律）
- **稳定性资产**：references/quality-gates 三门（复现校准/红队台账/完整性巡检）+ integrity_manifest.json（34 文件基线）

### Fixed
- settings.json 外部删除二度复发（巡检拦截+git 恢复）
  - ⚠️ **2026-11-04 订正**：上述「git 恢复」是**错误处置**。根因已定位到宿主 `app.asar` 的 `ExpertPluginService`：单键 agent 型 `settings.json` 被判为宿主私有 override 缓存，激活时 + 启动时主动 `unlink`；恢复只会被再删一次。宿主解析 agent 名走 `plugin.json`，从不读该文件。现行本包保留的是**多键**版本（不命中删除判据），仅为兼容旧校验器；不得恢复成单键格式
- M18 错版 CSV 落盘（审计 G-01 fatal：计算后未覆盖产物=虚报完成首例）→ 重算覆盖（D′=0.9441 断言验收）

### Security
- 双 manifest（.codebuddy-plugin + .claude-plugin）同步机制（防 Claude Code 侧引用失效）

## [1.1.1] - 2026-10-14

### Added（补记，溯源 9e49faf / f62b8d7）
- **治理 5 约束**：诚实性红线（虚报=整单退回+记 ledger）/ 一图一 ipynb / pdf 定稿 / 路径显式 / 文件治理与索引同步

## [1.1.0] - 2026-09-30

### Added
- 成员契约闭环：result_envelope 信封 + 预加载 skills + maxTurns 差异化（60/80/50/40）
- 主理人接口契约段（task_payload 下行 + VERIFY 门禁）

### Changed
- 角色分类：7 ANALYZER + 2 EXECUTOR + 1 REVIEWER

### 实战验证记录（非结构变更，2026-10-14 补记）
- 两轮真实任务：WF5 红队（4 员 spawn，38 findings，ledger 77% 闭环）/ WF1 假说生成（3 员并行，信封合规 100%，v1→v1.2 三次自组织迭代）
- 审计型 REVIEWER 角色实测抓出 fatal 级落盘矛盾（G-01）——工具白名单"只读"纪律的价值实证
- 一图一 ipynb 纪律首秀成功（M18 四口径森林图，300DPI pdf + 同名 notebook）

## [1.0.0] - 2026-09-11

### Added
- 9-role expert team: team-lead (路问渠) + 8 specialists (假说/系统发育/群体遗传/预测/结构/文献/工程/档案)
- 5 standard workflows (WF1假说验证 / WF2方法迁移 / WF3前沿追踪 / WF4分析执行 / WF5投稿前红队)
- research-ops 文档系统（00_governance / 10_hypotheses / 20_methods / 30_results / 40_manuscript_assets / context_stack）
- 跨域病毒演化研究：H5/H7/H9/H10、糖基化-宿主适应、抗原漂移、DMS预测、MAFFT/IQ-TREE/HyPhy/AlphaFold3管线规划
- 硬约束：禁幻觉引用（无PMID/DOI删）/ 禁推断伪装事实（显式标注）/ 禁跳过质控乐观交付

### License
- Apache-2.0（保留专利授权，允许商用）
