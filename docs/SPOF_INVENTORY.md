# SPOF_INVENTORY.md — 单点故障与降级链清单（R-12b · 2026-11-09）

> 来源：任务 B 编号 12（工具动态编排冗余/单点故障规避）取证。
> 维护纪律：scripts/ 增删外部依赖时**必须同步更新本表**；「硬依赖」新增须经 GATE 确认。
> 判定口径：**硬依赖** = 失效即当前功能终止（有退出码契约）；**软依赖** = 失效有降级路径继续工作。

## scripts/ 外部依赖清单

| 依赖 | 消费位置 | 类型 | 降级路径 | 状态 |
|---|---|---|---|---|
| vendor/shared-core（联邦真源 + 兜底副本） | assemble_spawn_prompt.py V5 校验器加载 | 软 | 缺失 → `--legacy-package-check` 旧子串校验 + 显式告警（可被散文糊弄） | ✅ 已接线（R-12a 补测试锁定） |
| `git` 可执行 | gen_integrity_manifest.py tracked_files | 硬 | ~~无（check=True 裸抛）~~ → v1.5.4 R-12b：明确报错 EXIT=2 | ✅ 有退出码契约 |
| `git` 可执行 | assemble_spawn_prompt.py 版本探测 | 软 | except OSError/Timeout → return None | ✅ |
| `rg` 可执行 | find_knowledge.py | 软 | shutil.which 探测 + 纯 grep 回退分支 | ✅ |
| `grep` 可执行 | find_knowledge.py grep 回退分支 | 硬（该分支内） | 无（POSIX 系统必有）；执行失败 → v1.5.4 R-10b：重试后本仓跳过 | ✅ |
| `research-ops` 目录（RESEARCH_OPS_DIR） | assemble_spawn_prompt.py 知识态注入 | 软 | 未设置 → 静默跳过注入 | ✅ |
| `research-ops` 目录 | hypothesis_watch.py | 硬 | ❌ 缺失 → EXIT=3（无法裁决）——契约性行为，按退出码判别原则处理 | ✅（有意硬） |
| confirmed_hypotheses.json + redteam_ledger.csv | hypothesis_watch.py | 硬 | ❌ 缺失 → EXIT=3 | ✅（有意硬） |
| `research-ops` 目录 | render_context_stack.py | 硬 | ❌ 缺失 → 非零退出 | ✅（有意硬） |
| 权威源（数字溯源池） | check_gates.py G2 | 硬（门禁层） | 无权威源 → 判 FAIL（fail-closed） | ✅（方向安全） |
| guard_readonly.py 只读根 | RESEARCH_OPS_DIR/_archive（v1.5.5 收窄） | 软 | 根缺失 → 不拦截（一次性 stderr 警告）；显式 DENY 优先 | ✅ |
| `research-ops` 目录 | verify_member_output.py | 软 | env→CWD→本仓 outputs/ 逐级回退；无源 → fail-open 跳过 + 人工确认 | ✅ |
| 本地知识库（context_stack 四 JSON） | render_context_stack.py | 软 | 单 JSON 缺失 → 静默 skip 并继续渲染其余 | ⚠️ 缺失不落痕（backlog：加 stderr 汇总） |
| 联网（MCP/WebSearch） | 成员侧（literature-scout 等） | 软 | 降级三通道（search-sources.md）；**v1.5.4 R-10b 新增**：全失败 → find_knowledge.py 本地三仓降级检索 + 信封标注 `[本地知识库降级检索]` | ✅ 已接线 |
| PyYAML | vendor 动态层（仅 vendor 副本） | 软 | 缺失 → 拒收动态层 | ✅（scripts/ 版不触发） |

## 冗余编排现状

- **信封双通道**：成员落盘 artifact（主）+ SendMessage 摘要（辅）——产出回传域的冗余。
- **检索三通道**：MCP → WebSearch/WebFetch → 本地三仓（R-10b 后完整）。
- **vendor 双源**：联邦真源优先 + 包内兜底副本 + legacy 子串校验终极回退。
- **测试互锚**（R-13b 新增）：test_vendor_core V7 ↔ test_contract_guard 跨文件双向锚定，防守卫被单文件覆盖静默摘除。

## 已知残余单点（不施工，记录归属）

| 残余 | 归属 | 说明 |
|---|---|---|
| 两测试文件同时被旧基线覆盖 | 人工纪律 | 互锚同时失效场景；缓解 = 施工前后必跑守卫 + 轮报时 `git diff <tag> -- tests/` |
| vendor 模板死引用（progress.py/record_trace.py 不存在） | 联邦层 | vendor 只读，按 Known Issues 先例标「待联邦层修复」 |
| 平台 Agent spawn 不暴露 token/turn 数 | 平台侧 | 脚本级预算校验客观不可行（任务 B 编号 4 已诚实声明） |
