# ADR-001 · `--require-tag` 保持默认关闭

> 机器可读真源：`docs/decision_records.json`（`ADR-001` / `status: accepted`）。
> 本文是人读视图；两者冲突时以 JSON 为准，且 `check_decision_records.py` 会拒绝不一致的部署。

## 状态

**Accepted · 2026-11-10 · v1.5.9**（v1.5.8 只落一句结论，本版补齐裁决记录、机器校验与迁移路径）

## 背景

`--require-tag` 是 C3 严审闸：开启后 G2 权威源池只接受头部带 `source_tag: authoritative` 的文件。v1.5.0 起三点接线（`check_gates.py` / `verify_numbers.py` / `verify_member_output.py`）均为 `action="store_true"`，**默认关闭**。CHANGELOG v1.5.2 Known Issues 留了「下一轮评估是否翻转默认值」，v1.5.8 给出「保持关闭」的口头裁决但未落成可验证资产——这正是本 ADR 要补的缺口。

## 裁决

**保持默认关闭，不改代码。** 严审任务显式传 `--require-tag`。

## 依据

1. **已发布契约**：`test_require_tag_gate` 断言默认关闭为向后兼容契约；翻转即破坏 v1.5.0 以来所有已发布行为。
2. **存量现实**：多数权威源未打 `source_tag: authoritative`，默认翻转会误杀存量任务，且无自动迁移路径。
3. **成本收益**：显式传参即可获得同等校验强度，翻转收益不抵全量回归成本。

## 后果（诚实披露）

- 默认态下未标记权威源仍可入池 → **残余风险持续存在**，Known Issues 不得销项。
- 任何新增 CLI 接入 `require_tag` 必须同步 `decision_records.json` 的 `cli_sites` 与 guard 第 5 项，否则防翻转守卫 EXIT=5。

## 启用前置（`enable_when`，全部满足才允许翻转）

1. 存量权威源 **100% 打齐** `source_tag: authoritative`（须脚本全量盘点并出具报告）；
2. `test_require_tag_gate` 与三处 CLI 契约测试改写为默认开启版并通过全量 fuzz；
3. **主版本升级（≥2.0.0）**，CHANGELOG 明确列 Breaking Change 与迁移命令。

## 迁移路径

① 生成待打标源清单并逐条补标 → ② 过渡版本「默认 True + `--no-require-tag` 逃生开关」→ ③ 过渡期结束后移除逃生开关，本记录 `status` 改 `superseded` 并新增 ADR。

## 防翻转机制

`scripts/check_decision_records.py` 只读校验：三处 CLI 必须仍是 `action="store_true"` 且不含 `default=True`；`test_require_tag_gate` 与「require_tag 闸三点接线存活」两个测试锚必须存活。任一被改 → `EXIT=5 / VIOLATION`。**裁决不是写在文档里的一句话，而是有机器消费端的契约。**

复核日期：2027-01-31。
