# Method Library（人类可读视图）
> 更新：2026-10-14T20:55:00+08:00

## METH-DPRIME-PROB-SCALE — D′ Lewontin 概率标度计算（格子数标度陷阱）
- **核心**：D = p11·p00 − p10·p01（全部除 N² 后的概率），D_max = min(pA·pb, pB·pa)；❌禁用格子数当 D 配概率分母（会得百万级）
- **陷阱**：两次实战错误：格子数/概率混标度=D′ 百万级；分子记错=D′=0。分层 D′=±1 是空单元算术后果禁读作强协同
- **验证**：M20 §3：全样本 D′=0.9441 bootstrap CI[0.893,0.988]；4h 内分层 D′=0.081
- **复用**：H10/H1N1 任何 LD 分析直接套用
- **源码**：`09_Supplementary/M_statistical/M20_robustness_suite/M20_robustness_computation.py`

## METH-FOUR-CALIBER — 多口径并列 GLMM（caliber panel）
- **核心**：C0(仅EPI)/C1(+Province)/C2(去Other宿主)/C3(+仅Top4clade) 四档口径同规格拟合，并列报告点估计与显著性——不选'对的口径'，报告'口径敏感性'
- **陷阱**：n 差异源于宿主分类函数关键词边界；任何引用必须声明口径与分类函数版本
- **验证**：M18: C0-C2 一致(n=1892)，C3 剔混合 clade 后 Human p=0.022→0.92
- **复用**：所有'过滤口径分歧'型争议的解决方案
- **源码**：`09_Supplementary/M_statistical/M18_mammal_caliber_uniform/M18_caliber_computation.ipynb`

## METH-LOSO-PRECRITERIA — LOSO 预指定判据
- **核心**：运行前锁定：留一子样本系数符号一致 且极差<0.10 → 稳健；否则降级。两维度跑：subtype + province（70 次）
- **陷阱**：事后改判据=证据偷跑；只跑一个维度会漏 subtype 敏感性（H5N6 依赖即此发现）
- **验证**：M21: province 极差0.053稳定；subtype LOO-H5N6 符号翻转→Human 降级
- **复用**：任何'结论是否被单一子集驱动'的检验
- **源码**：`09_Supplementary/M_statistical/M21_pglmm_loso/M21_computation.py`

## METH-CLUSTER-ROBUST-PSEUDOREP — 伪重复三路检验（cluster-robust/crossed RE/PGLMM）
- **核心**：①OLS cluster-robust SE ratio（阈值1.5）②MixedLM crossed vc_formula ③phylolm PGLMM 终裁；三路并列而非单点
- **陷阱**：Province RE 已吸收大部分省内相关时 naive SE 只低估 6-8%——'伪重复'指控需实证而非默认成立
- **验证**：M21: ratio=1.06-1.08 轻度；crossed 差 0.019 未确证
- **复用**：红队'伪重复'攻击的标准回应模板
- **源码**：`09_Supplementary/M_statistical/M21_pglmm_loso/M21_computation.py`

## METH-NUMBER-VERIFY-GATE — 关键数字核验关卡（幻觉拦截）
- **核心**：产出中 n=/p=/D′/百分比/CI 提取 → 在权威源（仅 csv/json 计算产物，禁 md 循环自证）grep 同值 → 未命中=DEGRADE_TO_PARTIAL
- **陷阱**：A156T=20.58% 事故：幻觉数字流入 sentinel CSV+日志+汇报 16 天才被真源核查推翻。归一化禁截断（:g 制造假阳性 20.58→20.6 误命中）
- **验证**：R12 冒烟：幻觉被 EXIT=5 拦截，真值 EXIT=0 放行
- **复用**：所有成员产出的 envelope 前置关卡
- **源码**：`viral-evo-lab/scripts/verify_numbers.py`
