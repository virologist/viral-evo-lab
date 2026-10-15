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

## 团队级契约要点

- **下行 task_payload 格式**：`{task_id, phase, instruction, input, output_contract, constraints, handoff_source}`，详见主理人 MD 接口契约段
- **纪律审判 checklist**（主理人 T0/T1 触发）：
  - T0（派 spawn 前）：引用事实须与 `confirmed_hypotheses.json` + `knowledge_index.md` 一致；输出落 git 跟踪目录；改稿前 git tag 快照
  - T1（收 envelope 时）：status 自评与实际一致；关键数字（n=/p=/D′/百分比/CI）须在权威源溯源（spawn prompt 已自动核验，未溯源会 stderr 警告）
- **数字核验关卡（V1/产出端）**：权威源 grep 不到的数字 = 标 `[待人工核验]` 或补证据后重传；外部引文数字由主理人核 URL 后走 waivers.json 放行
- **两仓分层纪律（P2）**：本成员 MD 不写项目特定事件/数字/PMID；仅通用机制/治理/版本（`scripts/check_scope.py` 机械兜底）

修改成员角色职责时，须同步检查以上契约是否仍适配；冲突时上报主理人裁决。
