{"agent_id":"research-diagnostician","task_id":"T-20261015-M2","phase":1,"status":"success","confidence":88,"deliverable_summary":"两脚本各含真实缺陷：H1时间戳洗白旁路与C1留痕失配最重，建议修复后上线"}

# T-20261015-M2 门禁脚本审计报告（research-diagnostician）

## 一、缺陷清单（按严重度排序）

**【高】H1 时间戳洗白旁路** hypothesis_watch.py:83,98-99
报警条件仅为 `closed_date > last_updated`，不比对 finding_id 是否已处置。任何一次池更新（哪怕未复查任何发现）都会把此前全部 late_fatal 洗成"不晚于"；:107 的处置指引"复跑至 exit 0"反而鼓励先 bump 时间戳再复跑。复现：修改 last_updated 后重跑 → exit 0，26 天失效问题可经此复发。修法：按 finding_id 建已处置清单而非纯时间差。

**【高】C1 留痕失配** check_gates.py:132-133
G4 仅查 output-check.json **存在性**，无内容/时间绑定。实证：T-20261021-D artifact 于 10-21 被 T1 处置编辑（literature-scout.md:28），晚于 output-check 生成（10-14 22:37），G4 仍 PASS。核验后改动 artifact 可绕过核验留痕。

**【中】C2 400B 名实不符** check_gates.py:43,49
`ENVELOPE_SKIP_BYTES=400` 实为 400 **字符**截断（先 read_text 再切片）。信封 summary 无长度上限，约 135 个汉字即超限截断 → json 解析失败 → 合法信封误判 FAIL。实测现信封 67 字符/248 字节，余量有限。

**【中】H2 日期粒度与时区缺陷** hypothesis_watch.py:39,42-44,82-83
真实台账 closed_date 为纯日期（如 "2026-10-14"，解析为当日 00:00）：若同日**晚于**池更新时刻闭环，`cd > hyp_updated` 判 False → 静默漏报。另 :44 用 replace(tzinfo=None) 不换算，UTC("Z") 时间戳与 +08:00 混比偏 8 小时。

**【低】C3 退出码违约** check_gates.py:35-37,97-98,109
verify_member_output.py 缺失时 exec_module 异常未捕获 → exit 1，违反声明契约（0/3/5）；G3 失败路径 return 3 也不落盘 gates.json，下游自动化断档。

**【低】H4 池结构脆弱** hypothesis_watch.py:68-69
池若为 list 或字段漂移，hyp.get 抛 AttributeError → exit 1；closed_date 格式漂移时静默跳过，永不报警。

## 二、真实数据交叉验证

T-20261021-D 运行数据行为正确：G1 信封验真（agent_id/status/confidence 与 artifact 一致）、G2 精确复现 output-check 的 pct:79 未溯源、verdict FAIL→exit 5 符合声明。C2/H2 的触发条件在当前数据中尚未命中，属边界漏洞。

## 三、总评

**修后可上线**：两脚本判定逻辑与真实数据吻合，但 H1（时间戳洗白）与 C1（留痕失配）是治理闭环的两个真实旁路，建议修复后再作为唯一门禁依赖。
