# 团队契约（全员同版 · 单一事实源）

> 本文件是 9 名成员共用的契约正本（2026-10-15 自成员 MD 去重抽取）。
> 主理人装配 spawn prompt 时**注入本文全文**；成员 MD 不再各自复制（防漂移）。

## 上行信封（result_envelope，回传必填，置于产出正文前）
```json
{
  "agent_id": "<成员ID，与 agents/ 文件名一致>",
  "task_id": "<由编排者下发>",
  "phase": <N>,
  "status": "success|partial|failed|blocked",
  "confidence": <0-100自评>,
  "deliverable_summary": "<一句话摘要>",
  "issues": ["<自评发现的问题；无则空数组>"]
}
```

**status自评准则**：完整满足→success；部分满足且issues非空→partial；无法满足需重试→failed；前置条件不足→blocked。

**issues 定性**：成员侧必填（无则空数组）；G1 仅强校验 6 必填字段，`issues` 缺失不判 FAIL，但类型非数组判 FAIL。

## 假说锚定字段（hypothesis_anchor · C1，仅 WF4/analysis 触发）

上行信封在 `workflow: "WF4"` 时**必须**含 `hypothesis_anchor` 对象（G1 验收，缺失判 FAIL）：

```json
"hypothesis_anchor": {
  "hypothesis_id": "<锚定的活跃假说 ID；无则填 no_hypothesis_justification>",
  "biological_question": "<本分析回答的生物学问题>",
  "falsification_condition": "<什么结果会推翻当前假说>"
}
```

- 三字段中 `biological_question` / `falsification_condition` 必填且非空字符串；
  `hypothesis_id` 与 `no_hypothesis_justification` **至少填一项**（禁止两者皆空）。
- 作用：把主理人的 B>C>A 内部追问从「结果不外显」变为**可验收落盘字段**，使单一 A 类任务也能被升维判定；不新增内容生产环节。
- 非 WF4 信封不校验该字段（向后兼容）；判定逻辑在 `scripts/check_gates.py` 的 G1。

## 团队级契约要点

- **下行 task_payload 格式**：`{task_id, phase, instruction, input, output_contract, constraints, handoff_source}`，详见主理人 MD 接口契约段
- **纪律审判 checklist**（主理人 T0/T1 触发）：
  - T0（派 spawn 前）：引用事实须与 `confirmed_hypotheses.json` + `knowledge_index.json` 一致（`.md` 仅为渲染视图，禁直编）；输出落 git 跟踪目录；改稿前 git tag 快照
  - T1（收 envelope 时）：status 自评与实际一致；关键数字（n=/p=/D′/百分比/CI）须在权威源溯源（spawn prompt 已自动核验，未溯源会 stderr 警告）
- **数字核验关卡（V1/产出端）**：权威源 grep 不到的数字 = 标 `[待人工核验]` 或补证据后重传；外部引文数字由主理人核 URL 后走 waivers.json 放行
- **两仓分层纪律（P2）**：本成员 MD 不写项目特定事件/数字/PMID；仅通用机制/治理/版本（`scripts/check_scope.py` 机械兜底）

修改成员角色职责时，须同步检查以上契约是否仍适配；冲突时上报主理人裁决。
