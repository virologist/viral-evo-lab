# _memory_archive/ 蒸馏归档索引（R8 产物）

## 蒸馏策略
- 触发：workbuddy memory_roll.py 30 天阈值
- 保留：标题段 + 涉及 commit hash + 原文绝对路径
- 删原文：30 天后（30 天蒸馏窗口 + R8 链可访问原文）
- 查询：`python3 find_knowledge.py "<关键词>"`（S1 跨仓入口）

## 蒸馏文件命名
- `ws_YYYY-MM-DD.md` — 来自 workbuddy 工作空间 memory/
- `B_YYYY-MM-DD.md` — 来自 04_H5/.workbuddy/memory/
