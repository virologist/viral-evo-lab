# Changelog

All notable changes to **viral-evo-lab** are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/spec/v2.0.0.html).

> **2026-11-07 补记说明**：v1.1.1~v1.5.0 区间曾长期缺条目（版本记录断层，已按治理约束⑤索引同步修复）。以下补记条目均从 git tag 链与提交信息反推，逐条附 commit hash 溯源；措辞可能较当时实况简略，以 git 历史为准。

## [Unreleased] - 2026-11-07（独立诊断 P1–P3 修复，尚未发版）

> **版本口径**：本轮为诊断驱动的结构修复，`plugin.json` / `marketplace.json` 的 `version` 仍为 **1.5.0**，未擅自升版。是否发版为 1.5.1 由管家节点裁决。

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
- `vendor/shared-core/assemble_spawn_prompt.py` 669 → 685 行，`VENDOR.json` sha256/lines 同步；联邦真源 / vendor 副本 / 清单三方哈希实测一致
- `integrity_manifest.json` 重建为 66 文件全量清单（此前 55 项漂移 + 25 文件未覆盖，防篡改能力失能）

### Fixed（P3 第 2 轮交叉验证，2026-11-07）
- **高**：`check_gates.py` `load_waivers` 对 `value` 为 list/dict 的非法 waiver 抛 `unhashable TypeError` → G1–G5 全体失效；改为仅接受可哈希标量 + 异常类型扩充
- **中**：C7 重写时遗失「非数值/带单位 waiver 精确匹配」→ G2 合法放行条目静默失效；恢复精确匹配、候选值匹配、浮点容差三路并存
- **中**：装配器 docstring 的 `669 行` / `1809085d` / `595 行` 未随 vendor v2.6.0 升级回改（实况 `685` / `f2ced4c2` / `654`）
- **中**：授权矩阵触发器计数 5 → 6（CHANGELOG 与主理人 MD 两处）；`quality-gates.md` 的 `git checkout` 指引与主理人 MD 的 settings.json 禁令互斥 → 补类型前置判定
- **低**：`verify_member_output` 元文件排除后缀补 `spawn_prompt`（对齐 LEAD_SUFFIXES 4 项）；tests 复制来源叙述自相矛盾；CLAUDE.md Changelog 区排列注释改为「非严格时间序」；A4 补记措辞订正

### Known Issues（残留，不阻塞）
- `VENDOR.json` 的 `synced_at=2026-10-15` / `synced_by=P0-S4-1 5包vendor分发v2` 为并发工作线回填的旧元数据，与 11-07 的 hash 不自洽；未擅改，交管家节点裁决
- 本轮未升 version；如需发版，须同步 4 处版本号并重跑 `gen_integrity_manifest.py`
- `vendor/shared-core/assemble_spawn_prompt.py:122` 命中首个 `vendor/shared-core` 段后 `break`（而非 `continue`），多层同名嵌套路径下会放弃扫描更内层真包根（隔离实测 EXIT 3）。该文件是联邦真源镜像，改包内副本会破坏 V3/V4 哈希门禁与「vendor 零改动」修改禁区，**须在联邦真源层修复后重新分发**；本轮未擅改

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
