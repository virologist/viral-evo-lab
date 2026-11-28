# viral-evo-lab v1.5.38 治理同步（R4.21）

- 日期：2026-11-28
- 专家包 commit：`a3178e9`（= tag `v1.5.38` = origin/main = HEAD，工作树 clean）
- 治理基线：`v1.5.37` / `0cc40b9`

## 1. 本轮触发

v1.5.37 两路独立盲检（前台同步，报告均送达）：A 通用无预设 4🔴+5🟠，B 对抗红队 9🔴+2🟠，U+3002 类项重复，去重后 11 项候选。主代理对 11 项逐条自建 fixture 真实 CLI 独立复现并设正字对照，**11/11 全部坐实、零证伪**。核心教训：**「上限补丁」和「类别枚举」都留邻界空间**——`{1,64}` 有界正则被 65 符绕过、`len(mid)<=2` 被 3 字符绕过、`_SPLIT_BAD_CATS` 漏 `Cn`、`severity 守卫只认 L 类字母` 被 Nd/Po/Zs 绕过。根治统一收敛为**无界语义判据 + 固定真源白名单 + 单一事实源反向提取**。

## 2. 修复清单

| 项 | fail-open 形态 | 修复前 → 后 | 根因修复 |
|---|---|---|---|
| A1 | `p = 0.9<U+0378>4`（Cn 未分配码点劈开数字）前缀被池洗白 | PASS/0 → 3 | `_SPLIT_BAD_CATS` 补 Cn（与 Cf/Co/Cs 同属不可见格式类） |
| A2 | `{1,64}` 有界正则被 65×Sm 隔断绕过 | PASS/0 → 3 | 去掉数量上限改无界（`\d` 起点+贪婪+前瞻，无灾难性回溯） |
| A3/B3/B9 | severity/status 插 Cn/Nd/Po/Zs 使 fatal 闭环整行隐身 | CLEAN/0 → 5 | 判据从「非 ASCII 字母(L)」改为「任意非 ASCII 字符」——合法枚举恒为纯 ASCII 窄集 |
| A4 | `check_scope` 传目录检查 0 文件仍报 clean | clean/0 → 3 | 显式目录递归展开 .md/.py，展开为空即结构错误 |
| B1 | `pABC=0.94` 3 字符隔断绕过 `len<=2` | PASS/0 → 3 | 去上限，改语义判据（ASCII mid + marker 前不邻引号 + `=`/`:` + 数字） |
| B2 | `default=(True)` 括号包裹绕过形态锚 | OK/0 → 5 | `RE_DEFAULT_TRUE` 容忍 `True` 前包裹括号 `\(*\s*` |
| B4 | `type:"spawn"` + `event:"evidence_check"` 伪装被跳过 | READY/0 → 5 | 显式已知非 spawn 事件白名单，event/type 任一键含 spawn 语义即 fail-closed |
| B5 | 锚 `source:{}` / `commit:null` 借假值跳过溯源 | OK/0 → 3 | source 须含 commit/tag 非空字符串溯源字段 |
| B6 | 多语分隔符 U+066C/066B/30FB 千分位投影遗漏 | clean/0 → 3 | 从 `_EQUIV_TRANS` 反向提取所有映射为 `.`/`,` 的字符；叠加「数字间分隔符一律剥离」投影 |
| B7 | checklist `1 总/0 通过/99 幻觉/PASS` 过 G5 | PASS/0 → 5 | 消费侧补 `items_passed==items_total` 且 `hallucinated==0`（与生产者单一事实源一致） |
| B8 | 篡改 artifact 后 touch oc 抹 mtime 时序 | PASS/0 → 5（真实产物） | oc 内容 `ts` 与文件 mtime 互证，差 >2s 且 ts 在近 2 天内即判 G4 FAIL |

## 3. 🟠 披露不修（1 项）

- **空指纹手写 oc 的信任边界**：`artifact_mtimes:{}` 且无 `ts`/`checked_artifacts` 的手写 output-check.json，调用方可完全伪造其全部元数据（mtime/内容），文件元数据无法做不可伪造的时序仲裁。真实 `verify_member_output --gate` 产物（带指纹+ts）已验证：篡改后 touch 仍 EXIT=5（指纹比对 + ts 互证双拦）。该残留属信任边界固有限制，不伪造根治补丁。

## 4. 验证与治理闭环

- pytest **19 passed** / fuzz 行为级 **61/61**（机器锚 `CURRENT_BASELINE = 45 CASES + 16 行为级` 不变）/ manifest `--check` EXIT=0（**80 文件**）/ compileall OK。
- 回归断言复用既有 6 个测试函数（test_require_tag_gate / test_g6_evidence_gate / test_decision_records_guard / test_poll_hitlimit_and_manifest / test_baseline_anchor_roundtrip / test_disposition_gate），**零新增 `def test_*`**，测试函数数保持 17。
- 包外锚：刷前正确报 DRIFT/EXIT=5（10 文件漂移），受控刷新后 **22/22 OK/EXIT=0**。
- 两仓终态：专家包 `a3178e9`=origin/main=tag v1.5.38；治理仓本轮同步后=origin/research-ops-track。
- 冻结状态：⏳ 未冻结——待 v1.5.38 基础上连续两轮独立盲检零🔴。
