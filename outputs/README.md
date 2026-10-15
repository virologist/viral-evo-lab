# outputs/ — 权威源池（V1/产出端核验的 grep 目标）

**本目录不放示例/冒烟数据。** 各项目的计算产物（csv/json）由项目自行放入或由
RESEARCH_OPS_DIR 指向真实项目目录。仓内仅保留本说明。

历史教训：2026-10-14 R12 冒烟曾在此放置手编常量 CSV（M18.csv），被 D 演练的
产出端核验当真源匹配——假数据入池 = 核验失效。已删，立此 README 防复发。

生产权威源建议在文件头部 3 行内加 `source_tag: authoritative` 标记，配合
verify_numbers.py `load_sources(..., require_tag=True)` 使用，未带 tag 的文件
不进 grep 池（T-C4 · LRN-005 防线机制闸）。
