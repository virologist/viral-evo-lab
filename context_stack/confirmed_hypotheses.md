# 已确认假说池
> **⚠️ 真源已迁移至 `confirmed_hypotheses.json`（Anthropic feature_list.json 模式，P0-1 2026-09-18 落盘）。本 .md 是人类可读视图，由 archivist 从 JSON 渲染。**
> **机器/程序读取：JSON。人工阅读/编辑：可改 .md 但需同步更新 JSON（否则 archivist 渲染会冲掉）。**
>
> 仅收录用户明确认可的假说。标准格式：主张 / 支持证据 / 关键预测 / 可证伪条件 / 置信度。
> 更新：2026-09-11（H-ANCHOR-1 按 v5.1 实际假说重写，废弃 v3.8 之前的"糖基化预适应 enabling"叙事）

## 活跃假说

### H-ANCHOR-1（H5Nx v5.1 重定位，2026-07-30 Gate-1 验证后）
- **主张**: H5Nx clade 2.3.4.4 中，G70（mature 54）与 G140（mature 124）构成 **4h clade 平级协同标记对**（D'=+0.94 共变），通过独立获得 + 遗传连锁共演化塑造 4h 谱系糖基化景观；G140 是 **4h clade 的定义性糖基化标记**（clade_delta=-0.916, freq_4h=91.7%）。
- **支持证据**:
  - M6 共演化 D'=+0.944（NetNGlyc n=2,476）/[+0.896（全集 n=2,497），95% CI 跨数据集一致 >0.85
  - M9_a GLMM Gate-1（控制 Clade + Subtype + Phase + Year + Province RE, n=2475）：G140 crude taxon_delta=+0.376 → conditional Mammal ΔP=+0.073, 95% CI [-0.067, +0.214], p=0.308（**不显著**）
  - M14 collapse（binomial GLM, n=77 tip）：G140 crude +0.368 → conditional +0.002，**崩塌 99.4%**
  - Clade 4h 效应 β=+0.806, p≈0（G140 变异绝大部分由 4h clade 解释）
- **关键预测**:
  - 若假说成立，未来 4h clade 内部 G140 频率维持 ≥90%；
  - 若 G140 真有独立 mammalian association 效应，在控制 clade confounding 的子样本中仍显著；当前 M9_a 不支持，故 G140 mammalian association **主要由 clade-founder confounding 驱动**
- **可证伪条件**:
  - 若 D' 重测（独立数据集）<0.85 → 推翻协同标记对叙事
  - 若 M9_a 类严格控制 clade 后 G140-Mammal 仍 p<0.05 → 推翻"clade confounding 主导"
  - 若 4h clade 不再定义 clade_delta 主导（freq_4h<80%）→ 推翻"定义性糖基化标记"
- **置信度**: 高（双源 GLMM + 双盲 PGLS 验证，Methods §2.5 已双源声明）
- **状态**: v5.1 重定位完成；manuscript v3.8c+5.1 已应用；投稿中（仅 P0=GISAID 致谢表）
- **配套叙事**: clade-host confounding 量化案例本身是核心方法学贡献（诚实讨论）

## 已弃用（v3.8c/v5.0 旧叙事，不可再引用）
1. ~~"S140 是唯一显著宿主关联位点"~~ → 被 G70 取代（M4 'cat' bug 修正）
2. ~~"sequon 三联体差异化选择"~~ → alignment 验证证伪（v3.6.1）
3. ~~"G70 是 4b 单次预适应"~~ → Card #2 排除大分支固定，修正为多重 gain+漂变
4. ~~"G140 双锁定 / 最强 mammalian marker"~~ → v5.1 Gate-1 验证证伪
5. ~~"糖基化获得是预适应事件，enabling 后续野生鸟溢出"（v3.8 之前的"叙事框架 A"）~~ → v5.1 重定位，已被 clade-confounding 框架取代
6. ~~"codon 140 = G140" 直接等号~~ → 2026-08-12 证伪（G140 mature 124 = m8_col 125）

## 归档（已发表 / 已弃用）
（无归档项——已弃用条目在上方"已弃用"小节保留可追溯）