{"agent_id":"literature-scout","task_id":"T-20261021-D","phase":1,"status":"success","confidence":85,"deliverable_summary":"3条多智能体编排可观测性代表实践（均核验arXiv原文）+落盘契约巡检方案一句评价+待核验区"}

# T-20261021-D：Multi-Agent Orchestration 可观测性调研简报（2024–2026）

检索方式：WebSearch 4 轮 + arXiv 原始页面核验；日期 2026-10-14。

## ① 三条代表实践/文献

1. **LumiMAS**（arXiv:2508.12412，2025，cs.CR）：三层架构——结构化事件日志层、LSTM 自编码器实时异常检测层、LLM 异常解释/RCA 层；核心机制是把"廉价常开监控"与"昂贵根因分析"解耦，宣称较 LLM-as-judge 提速约 148×。来源：https://arxiv.org/abs/2508.12412
2. **AgentOps 综述**（arXiv:2508.02121，2025，cs.AI/cs.MA，35 页）：将智能体系统异常分为智能体内/智能体间两类，提出"监控→异常检测→根因分析→处置"四阶段运维框架；"智能体间异常"即跨成员协作契约违背的理论位置。来源：https://arxiv.org/abs/2508.02121
3. **Beyond Black-Box Benchmarking**（arXiv:2503.06745，2025，IBM Research）：扩展 OpenTelemetry 语义约定以刻画 Workflows/Tools/Agents 等智能体级实体，从运行时日志重建执行图、用图编辑距离量化执行流变异性；证明"基于落盘痕迹的行为分析"可行且必要（用户研究中约 79% 从业者认为非确定性执行流是主要挑战）。来源：https://arxiv.org/abs/2503.06745

工业侧参照：LangSmith 为 LangGraph 等框架提供原生 tracing 及 OTel SDK（Python/TS/Go/Java），代表"平台内嵌式"路线，可作为巡检数据上游格式兼容目标。来源：https://www.langchain.com/

## ② 对"落盘契约+确定性巡检"方案的评价

方向与外部实践一致且更轻量：以磁盘状态为唯一事实源（工程实践概括为"state is truth, events are rumors"，拉取式扫描对不主动上报的组件依然自愈可见），用确定性脚本替代 LLM 轮询判官，恰对应 LumiMAS"廉价常开层 + 昂贵解释层"的分层思想；建议巡检结果写成结构化事件日志，为后续接入 OTel/LangSmith 管道留接口。

来源（pull-based 实践，个人工程博客）：https://www.worldprogramming.org/posts/why-i-rejected-an-event-bus-for-my-solo-agent-fleet-state-is-truth-events-are-rumors-iz8ak0

## ③ [待人工核验]

- LumiMAS 的 148× 提速与 F1≈0.733 为论文自评实验数据，未经独立复现。
- 上条 worldprogramming.org 博文为个人博客、非同行评审；其"拉取优于推送"结论依赖特定场景（小规模、含不可修改的第三方组件的机群），外推到团队编排需谨慎。
- LangSmith 描述来自官网营销页，SLA/成本数据未核。
- 未检索到与"契约+巡检"完全同构的已发表系统；②中"方向一致"判断为 [推断]。
- 三条 arXiv 文献仅核验摘要页，正文细节（实验设置）未逐条读全文。
- 【主理人 T1 处置 2026-10-21】"约 79% 从业者"被产出端核验关卡标红（本地权威源池未含）——已核：数字转述自 arXiv:2503.06745 摘要页（URL 在正文同句），属外部引文而非本地计算产物，**人工核后放行**；建议正文保留"约"字明示为转述。此为关卡边界案例：本地权威源管不到外部文献数字，须人判。
