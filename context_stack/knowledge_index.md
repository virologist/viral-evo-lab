# Knowledge Index（人类可读视图）
> JSON 机器真源 → 渲染版｜更新：2026-10-14T15:30:00+08:00
**总览**: {'topic_count': 5, 'file_path_count': 22, 'ledger_total_findings': 48, 'ledger_closed_pct': 0.77}
## 主题索引
### K-G140-CLADE-DIAGNOSTIC — G140 是 clade 诊断标记（co-occurrence）而非功能共变（co-varying）**Claim**: G140 是 4h clade 跨结构谱系诊断标记——4h 内 D'=0.081（近独立），全样本 D'=0.9441（强 LD）；强 LD 主要由 4h vs 4b 分化驱动（Simpson 型）
**因果链**：- redteam: WF5 红队首跑（2026-09-26）→ ledger H-04 H-08 C-01等 38 findings- module: M17 V1b 反推（n=2476，clade 独立性）→ M20 §3 分层 D'- evidence: 4h 内 D'=0.0811（n=374, 108 join 中仅 11 例非 G140）- manuscript: v6.5 P3 改稿（commit 98f845a）— co-varying → clade-diagnostic co-occurrence- registry: H-ANCHOR-1 deprecated + H-ANCHOR-2 active（context_stack/confirmed_hypotheses.json）
**文件路径**：- `09_Supplementary/M_statistical/M17_clade_independence/output/M17_V1b_wide_clade_result.csv`- `09_Supplementary/M_statistical/M20_robustness_suite/output/M20_dprime_bootstrap_stratified.csv`- `paper/current/H5Nx_v6.5.docx`- `research-ops/context_stack/confirmed_hypotheses.json`
**关键词**: G140 / clade-diagnostic / D' / co-varying / co-occurrence / 4h / 4b / Simpson / H-ANCHOR-1 / H-ANCHOR-2 / M17 / M20 / v6.5

---
### K-HUMAN-SIGNAL-FRAGILITY — Human clade-conditional ΔP 是 H5N6-dependent exploratory signal**Claim**: 论文 p=0.022 的 Human 残余信号经三重检验不稳健——M18 C3（去混合 clade）p=0.92 + M21 LOO-H5N6 p=0.774 + M20 F3 家族校正将不显著
**因果链**：- redteam: H-02（2026-09-26）/M-02 功效不足 / M-10 多重检验- module: M18 C3（去混合 clade）p=0.92 → M21 §1 LOO-subtype H5N6 p=0.774 → M20 §5 F3 家族 n=568- manuscript: v6.5 P3 改稿——hypothesis-generating → H5N6-dependent exploratory- registry: H-ANCHOR-3 active（context_stack/confirmed_hypotheses.json）
**文件路径**：- `09_Supplementary/M_statistical/M18_mammal_caliber_uniform/output/M18_four_cabin_forest.pdf`- `09_Supplementary/M_statistical/M20_robustness_suite/output/M20_multipletest_families.csv`- `09_Supplementary/M_statistical/M21_pglmm_loso/output/M21_loso_subtype.csv`- `paper/current/H5Nx_v6.5.docx`
**关键词**: Human / H5N6 / exploratory / M18 / M20 / M21 / C3 / LOO / family / H-ANCHOR-3

---
### K-M9A-SOURCE-ABSENT — M9_a MixedLM 源码缺失（fatal）**Claim**: M9_a 论文核心模型（MixedLM n=2475，REML，Province RE）的实现代码全史 git -S 无记录——支撑 v5.1/v6.5 叙事的模型本身不可独立复现；已用 M17 V1b 反推替代
**因果链**：- redteam: M-11（2026-09-26）— git -S 全史无 'S140_bin' / 'C(Clade_top)' 任何实现- module: M17 V1b 反推（n=2476）作为唯一可复现代码（dirichlet n=2476 vs 2475 差 1 行）- ledger: M-11 partial 闭合（commit 01cb45f）- registry: 接受 M17 反推为官方可复现代码（用户裁决 ④）
**文件路径**：- `09_Supplementary/M_statistical/M17_clade_independence/output/M17_V1b_full_coefficients.csv`- `09_Supplementary/M_statistical/M17_clade_independence/output/V1_calibration_notes.md`
**关键词**: M9_a / 源码 / M-11 / MixedLM / REML / 2475 / 2476 / V1b / 反推

---
### K-COORDINATE-DISCIPLINE — 编号与坐标映射纪律（coordinate-mapping.md）**Claim**: 从比对文件取残基必须去 gap 后按残基位置索引（不是列索引）；跨亚型外推（H3↔H5）未经校验收验禁止；sequon 基序 N-X-S/T 自检绕过映射
**因果链**：- incident: 2026-09-30 sequon 核验首次犯错（列索引 0.92% vs 去 gap 残基索引 20.26%）- discipline: 新增 references/coordinate-mapping.md（实测事故原型+三条铁律+SOP+已核验映射表）- module: G140=G70 sequon 核验通过（N124-H125-T126 / N54-C55-S56），不依赖 H3↔H5 映射- manuscript: v6.5 P3 改稿不涉及 H3 映射（避雷）
**文件路径**：- `~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/skills/viral-evo-core/references/coordinate-mapping.md`- `09_Supplementary/M_statistical/M17_clade_independence/output/V1_calibration_notes.md`
**关键词**: 编号 / 坐标 / sequon / 去 gap / H3↔H5 / coordinate-mapping / G140 / G70

---
### K-EXPERT-TEAM-GOVERNANCE — viral-evo-lab 团队治理（v1.1.0 契约 + v1.1.1 治理 + v1.2.0 实战验证）**Claim**: 10 角色 Team 型专家团；信封契约（6 必填 JSON 字段）+ 装配脚本 + 工具白名单 + 编号纪律 + 5 条治理约束（2026-10-14）经两轮实战零缺陷验证
**因果链**：- team: 9 角色创团（2026-09-10）→ 双轨制（v1.0）→ 信封契约（v1.1.0）→ 5 治理约束（v1.1.1）→ 实战验证 v1.2.0- evidence: 2 员实测 100% 信封合规；审计抓 M18 错版 CSV（诚实性红线首例）；一图一 ipynb 首秀成功- lessons: M19 编号冲突 → 命名需查重；REVIEWER 只读审计价值极高- registry: Changelog v1.2.0（2026-10-14）+ 双 manifest version 同步
**文件路径**：- `~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/CLAUDE.md`- `~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/.codebuddy-plugin/plugin.json`- `~/.workbuddy/plugins/marketplaces/my-experts/plugins/viral-evo-lab/.claude-plugin/plugin.json`- `research-ops/00_governance/redteam_ledger.csv`
**关键词**: viral-evo-lab / v1.1.0 / v1.1.1 / v1.2.0 / 信封契约 / 装配脚本 / 治理约束 / discipline-sentinel / M-11 / M19

---
