# viral-evo-lab v1.5.39 治理同步（R4.22）

- 日期：2026-11-28
- 专家包 commit：`2821460`（= tag `v1.5.39` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.38` / `a3178e9`

## 1. 本轮触发

v1.5.38 两路独立盲检（前台同步，报告均送达）：A 通用无预设 10🔴+3🟠，B 对抗红队 5🔴+4🟠，去重后 13 项候选。主代理对 13 项逐条自建 fixture + 真实 CLI 独立复现并设正字对照，**13/13 全部坐实、零证伪**（A2=B4、A6=B2 重复项合并计）。核心教训：**时间基准无上界**（未来 ts/未来 mtime/未来 last_updated 使超时/陈旧/证伪告警恒假）、**形态锚枚举字面与名称子串**（true 字面、FILLER 子串都是补不完的枚举）、**同一文件语义只判路径不判 inode**（硬链接绕过台账保护）、**肯定式类型判据跳过非字符串**（V5 结构门禁被类型混淆糊弄）、**合法豁免边界过宽**（引号豁免、合法分隔符使伪造声明洗白）。根治统一收敛为**无界语义判据 + 单一事实源白名单 + inode/类型前置校验**。

## 2. 修复清单

| 项 | fail-open 形态 | 修复前 → 后 | 根因修复 |
|---|---|---|---|
| A1 | 台账 ts=2099（未来）使陈旧告警永久失效 | HEALTHY/0 → 5 | 任何 ts > now(+08 canonical) 即内容违规 |
| A2/B4 | 假说池 last_updated=2099 吞掉真实 closed fatal；`--check-disposition` 同判 OK | CLEAN/0 → 5 | 未来基准下所有 closed fatal/severe 保守计入 late_fatal，disposition 不得判 OK |
| A3 | 产出 mtime=2099 使红/黄超时恒假 | READY/0 → 5 | mtime 超出 60s 容差落未来即计入红超时 |
| A4 | `轮豈次耗尽`（U+F900 CJK 兼容字）隔断撞限词 | READY/0 → 5 | NFKC 前剥除兼容表意文字区（兼容字折成另一汉字仍隔断） |
| A5 | `gate_mode="BLOCK"` 大小写变体使 DEGRADE 阻断态消失 | PASS/0 → 5 | 归一化比较，合法枚举 {block,warn,pass}，未知/非字符串 fail-closed |
| A6/B2 | `default=1` / 变量别名翻转 ADR-001 默认值 | OK/0 → 5 | `--require-tag` 参数块内非假 default= 即翻转（set_defaults 同口径） |
| A7 | 锚 `tag + commit=""` 改锚刷绿 | OK/0 → 3 | source 声明 commit 字段即须非空且与 HEAD 相符 |
| A8 | DRAFT 硬链接穿透「绝不写台账」守卫并覆写 | PASS/0 → 3 | 加 `os.path.samefile` inode 判据 |
| A9 | `n = 30′5` prime 复合 token 提取 30 被池洗白 | PASS/0 → 3 | 声明 marker 后「数字+合法分隔符+数字」复合 token fail-closed |
| A10 | V5 任务包 `judge_mode=0`/`threshold=0` 类型混淆过结构门禁 | OK/0 → 4 | 本包调用层 `_v5_type_precheck` 复核五要素/三件套类型 |
| B1 | `"pABC=0.94"` 借前邻引号豁免绕过隔断检测 | PASS/0 → 3 | 收窄为完整 JSON-key 形态（前邻引号且 marker 后冒号） |
| B3 | G4 ts 未来/非字符串值使 mtime 互证失效 | PASS/0 → 5（阻断态） | ts 字段存在即须合法 ISO 且不晚于当前（+60s），否则内容锚不可信 |
| B5 | U+13441 EGYPTIAN BLANK（Lo 视觉空白）凑满 waiver/G6 署名 | PASS/0 → 5 | 可见内容语义判据：名称含 FILLER 或 BLANK 的 Lo 视为占位空白 |

## 3. 🟠 披露不修（1 项）

- **B3 远期过去 ts**：ts=2026-01-01（drift>2 天）仍在 mtime 互证窗口外。与合法存量 fixture（ts=固定旧值 2026-11-09）结构同类，一刀切按时间窗口必误伤存量 G4 用例，只能靠枚举具体日期（脆弱补丁，违反根因纪律）。已修同族最危险的「未来/非字符串/空」三态；剩余远端过去态列为残留。

## 4. 联邦件处理

A10 的 V5 类型混淆根因在联邦共享真源 `plugins/shared-core/assemble_spawn_prompt.py`（6 个包 vendored）。本轮不在本包改 vendor 副本（避免污染 6 副本 sha 一致性与其它战线的未提交变更），改为在 viral-evo-lab 调用层 `scripts/assemble_spawn_prompt.py` 加 `_v5_type_precheck` 叠加校验，联邦件修下沉待单独治理轮次处理。

## 5. 验证与治理闭环

- pytest **19 passed** / fuzz 行为级 **61/61**（机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级` 不变）/ manifest `--check` EXIT=0（**80 文件**）/ compileall OK。
- 回归断言复用既有 2 个测试函数（test_gate_fuzz / test_decision_records_guard），**零新增 `def test_*`**。
- 包外锚：刷前正确报 DRIFT（13 文件漂移 + commit 断裂），受控刷新后 **22/22 OK/EXIT=0**。
- 两仓终态：专家包 `2821460`=origin/main=tag v1.5.39；治理仓本轮同步后=origin/research-ops-track。
- 冻结状态：⏳ 未冻结——待 v1.5.39 基础上连续两轮独立盲检零🔴。
