# T-20261015-M2 简报：LLM 多智能体"升级/授权机制"代表实践（2025-2026）

```json
{"agent_id":"literature-scout","task_id":"T-20261015-M2","phase":1,"status":"success","confidence":88,"deliverable_summary":"检索到3条分级授权代表实践：TAO分级升级、框架工具审批默认化、三级审批门控模型，支撑分级授权表设计。"}
```

## ① 代表实践

**1. Tiered Agentic Oversight（TAO，2025，MIT/Google 等）**
按"护士→医生→专家"式分层组织智能体，各层用布尔升级旗（escalation flag）投票决定自办或上抛；下层智能体分歧自动触发升级。人作为最高层参与验证时，医疗分诊准确率从 40% 升至 60%。
来源：https://arxiv.org/abs/2506.12482

**2. 主流框架"工具调用默认先问人"（2026）**
Microsoft Agent Framework（skills 引入的工具默认需审批）、LangChain（HumanInTheLoopMiddleware，按工具配置 interrupt）、OpenAI Agents SDK（require_approval 按工具设 always/never）三殊途同归：拦截工具调用→交人决策→批准后恢复。核心不是"暂停"而是"谓词"——按影响半径决定哪些调用值得人审，且警告全量门控会导致审批疲劳。
来源：https://dreaming.press/posts/agent-tool-approval-becomes-a-framework-default.html

**3. 三级门控模型：Auto-approve / Notify / Block（2026，业界通行模式）**
低风险只读操作自动放行；中风险执行但通知（软门）；高风险（付款、删除、对外发布、合规相关）硬门停下等人签核，配合审计日志归因每次动作。
来源：https://www.airtable.com/articles/human-in-the-loop-ai-agents

## ② 对分级授权表的一句话建议

授权表应按"影响半径×可逆性"而非按任务类型划级：低风险/可逆→自动+事后抽检，中风险→AI 审查+通知，高风险/不可逆（外部发送、删除、花钱、改架构）→强制人签；并以"智能体分歧/置信度低于阈值"作为升级触发器，避免管家节点缺席时无人兜底。

## ③ [待人工核验]

- 来源 2（dreaming.press）为独立博客，对三家框架行为的描述建议对照官方 release notes 核验。
- 来源 3（Airtable）为厂商文章，三级模型属业界通行归纳但非标准文档。
- 来源 1 已对照 arXiv 原文核验（arXiv:2506.12482，v2 2025-09-28），数据（40%→60%、24% 错误吸收）出自摘要，可靠。
