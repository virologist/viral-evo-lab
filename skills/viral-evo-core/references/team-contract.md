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
  "workflow": "<主理人下发的 workflow 值·原样回传>",
  "issues": ["<自评发现的问题；无则空数组>"],
  "next_action": "<可选·建议主理人下一步动作（≤120字）；描述动作本身，不含成员名——非路由指令，无则省略>"
}
```

**status自评准则**：完整满足→success；部分满足且issues非空→partial；无法满足需重试→failed；前置条件不足→blocked。

**next_action 定性（编号5 · 2026-11-09）**：**可选字段**——区别于 E1 已删的 `next_agent_hint`（成员自创路由指令，防越权）：本字段只描述动作（如「建议对 NA 段补 dN/dS」），不含成员名、不构成路由权；G1 不校验该字段（缺省不拦）；主理人 T1 汇编须采纳或在 checklist note 说明不采纳理由。

**issues 定性**：成员侧必填（无则空数组）；G1 仅强校验 6 必填字段，`issues` 缺失不判 FAIL，但类型非数组判 FAIL。

**workflow 回传规则（L3 2026-11-09 · A-1 修复）**：主理人在装配时用
`assemble_spawn_prompt.py --workflow <值>` 声明任务工作流，该值会
① 注入 spawn prompt 的「【工作流声明】」段；
② 落 sidecar `<run-dir>/<task_id>__workflow.json`（**门禁交叉核验的权威源**）。
成员回传时**必须**把 `workflow` 值原样写入信封顶层，不得改写、不得省略。

门禁 G1 做**类别级双向比对**（`analysis` / `other`）：
- 下发 analysis + 回传缺 `workflow` → **FAIL**（未回传工作流）
- 下发 analysis + 回传 other → **FAIL**（擅自降级，规避假说锚定校验）
- 下发 other + 回传 analysis → **FAIL**（擅自升级，伪造分析约束）
- 表述差异（`WF4 分析执行` vs `WF4` vs `analysis`）→ 同一类别，**PASS**
- 无 sidecar（存量链路）→ 退回「只信信封」旧行为，不误阻断存量产出

**为什么必须交叉核验**：成员自报 = 自证清白。若只信信封，成员写 `workflow:"WF1"`
即可合法绕过 WF4 的假说锚定强制（本次审计的 A-1 高危实为该问题，
而非单纯的「字段缺失」）。权威源必须是主理人的下发声明。


## 假说锚定字段（hypothesis_anchor · C1，分析类任务触发）

上行信封在 `workflow` 属**分析类**时**必须**含 `hypothesis_anchor` 对象（G1 验收，缺失判 FAIL）：

```json
"hypothesis_anchor": {
  "hypothesis_id": "<锚定的活跃假说 ID>",
  "biological_question": "<本分析回答的生物学问题>",
  "falsification_condition": "<什么结果会推翻当前假说>"
}
```

- 三字段中 `biological_question` / `falsification_condition` 必填且非空字符串；
  `hypothesis_id` 与 `no_hypothesis_justification` **至少填一项**（禁止两者皆空）。
- `no_hypothesis_justification` 可写在 `hypothesis_anchor` 内，**或并列写在信封顶层**（两种写法等效，G1 均接受）。
- **分析类 workflow 判定（归一化 · L3 2026-11-09）**：`workflow` 字段按分隔符（`/ - _ · | 空格` 及中文标点）切 token，
  任一 token 命中 `WF4` / `ANALYSIS` / `分析` / `分析执行` 即视为分析类，强制校验本字段。
  故 `WF4`、`wf4`、`WF4/analysis`、`WF4 分析执行`、`analysis` **全部触发**校验——变体写法不得绕过。
  非分析类（如 `WF1`）不校验本字段（向后兼容）。
- **判定依据以主理人下发声明为准（A-1 · L3 2026-11-09）**：本字段是否强制，**以 sidecar
  `<run-dir>/<task_id>__workflow.json` 的类别为准**（`analysis` / `other`），而非信封自报值。
  信封自报仅用于**比对**（与下发声明不一致即判 FAIL），不作判定依据——
  理由：成员自报 = 自证清白，只信自报则 `workflow:"WF1"` 可合法绕过本字段的强制。
- 作用：把主理人的 B>C>A 内部追问从「结果不外显」变为**可验收落盘字段**，使单一 A 类任务也能被升维判定；不新增内容生产环节。
- 判定逻辑在 `scripts/check_gates.py` 的 G1（`normalize_workflow` + `workflow_class` + `check_envelope`）。


## 团队级契约要点

- **下行 task_payload 格式**：`{task_id, phase, instruction, input, output_contract, constraints, handoff_source}`，详见主理人 MD 接口契约段
- **纪律审判 checklist**（主理人 T0/T1 触发）：
  - T0（派 spawn 前）：引用事实须与 `confirmed_hypotheses.json` + `knowledge_index.json` 一致（`.md` 仅为渲染视图，禁直编）；输出落 git 跟踪目录；改稿前 git tag 快照
  - T1（收 envelope 时）：status 自评与实际一致；关键数字（n=/p=/D′/百分比/CI）须在权威源溯源（spawn prompt 已自动核验，未溯源会 stderr 警告）
- **数字核验关卡（V1/产出端）**：权威源 grep 不到的数字 = 标 `[待人工核验]` 或补证据后重传；外部引文数字由主理人核 URL 后走 waivers.json 放行
- **waiver 放行规则（G2 + G4 同口径 · L3 2026-11-09）**：`<task-id>__waivers.json` 每条放行须含 `value` + `reason`（出处/URL）+ `authorized_by`（主理人署名）三项齐全；缺任一项**不放行**（防自我授权与空口放行）。G4 阻断态（`gate_mode=block` + verdict≠PASS）消费同一台账：**须 waiver 覆盖全部未溯源数字才放行，部分覆盖不解除阻断**。waiver 行使须按 `docs/authorization_matrix.md` §四落 `decision_log.csv`；同任务 ≥3 处 → 上报管家节点。
- **假说治理处置门禁**：`scripts/hypothesis_watch.py --check-disposition` 为只读验收（EXIT=0 = 无需处置/处置完整；EXIT=6 = 确有未处置项或例行复核缺失）。**无待处置项且假说池未超期时判 PASS**，不因台账文件缺失而误阻断存量项目；台账畸形按「未处置」保守计（宁可多提醒，不可漏提醒）。
  **退出码 3 与 6 的判别原则**：区别不是「哪个文件坏了」，而是**坏掉后还能不能算出裁决**——
  证据源（假说池 / redteam_ledger.csv）畸形 → 无法算出 late_fatal → **EXIT=3（无法裁决）**；
  处置记录（hypothesis_watch_state.json）畸形 → 证据源完好、裁决可算，保守按未处置 → **EXIT=6（可裁决但不合规）**。

- **两仓分层纪律（P2）**：本成员 MD 不写项目特定事件/数字/PMID；仅通用机制/治理/版本（`scripts/check_scope.py` 机械兜底）

修改成员角色职责时，须同步检查以上契约是否仍适配；冲突时上报主理人裁决。
