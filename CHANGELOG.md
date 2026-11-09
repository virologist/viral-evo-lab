# Changelog

All notable changes to **viral-evo-lab** are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/spec/v2.0.0.html).

> **2026-11-07 补记说明**：v1.1.1~v1.5.0 区间曾长期缺条目（版本记录断层，已按治理约束⑤索引同步修复）。以下补记条目均从 git tag 链与提交信息反推，逐条附 commit hash 溯源；措辞可能较当时实况简略，以 git 历史为准。

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
