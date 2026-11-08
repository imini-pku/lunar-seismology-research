"""Produce the reader-facing audit, tables and reversible transformation ledger."""
from pathlib import Path
import json,csv,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
import build_individual_cleaning_20261103 as b
import numpy as np
R=b.RES;F=b.FIG
recs=json.loads((R/'per_record_processing.json').read_text(encoding='utf-8'))
fits=json.loads((R/'glitch_fits.json').read_text(encoding='utf-8'))
dec=json.loads((R/'reviewed_glitch_decisions.json').read_text(encoding='utf-8'))
summary=json.loads((R/'summary.json').read_text(encoding='utf-8'))
bands=b.rows('results/individual_cleaning_20261103/per_record_band_screen.csv')
catalog_manifest=json.loads((ROOT/'data/raw/literature/Liu2025_ACC/acquisition_manifest.json').read_text())
intervals=[]
for r in recs:
 if r['status']=='missing_archive':continue
 d=np.load(b.OUT/f"{r['record']}.npz");t=d['t_ATT_s'];dt=float(np.median(np.diff(t)))
 for name in ['original_gap_mask','artifact_exclusion_mask','processing_edge_mask','short_segment_mask','temporary_gap_guard_mask','unresolved_transient_mask','glitch_subtraction_window']:
  for a,z in b.runs(d[name]):intervals.append(dict(record=r['record'],kind=name,start_index=int(a),stop_index_exclusive=int(z),start_ATT_s=float(t[a]),stop_ATT_exclusive_s=float(t[z-1]+dt),sample_count=int(z-a)))
b.writecsv(R/'processing_interval_ledger.csv',intervals)
smallfits=[{k:v for k,v in x.items() if k not in ['component','fit','catalogue_matches']} | {'catalogue_matches_count':len(x.get('catalogue_matches',[])),'decision':dec.get(x['fit_id'],{}).get('action','retain_flag')} for x in fits]
b.writecsv(R/'glitch_fit_audit.csv',smallfits)
good=[r for r in recs if r['status']!='missing_archive']
src=[ROOT/r['source_file'] for r in good]
old=b.rows('results/waveform_comparison/trace_stage_comparison.csv')
old_checks=[dict(path=r['npz'],sha256_unchanged=b.sha(ROOT/r['npz'])==r['npz_sha256']) for r in old if r.get('npz')]
b.dump(R/'previous_v2_preservation.json',old_checks)
assert all(r['sha256_unchanged'] for r in old_checks)
cal=ROOT/'data/raw/literature/Liu2025_ACC/event_window_calibration_commands.csv'
if not cal.read_text(encoding='utf-8-sig').strip():cal.write_text('event_id,station_code,date,command,MAP,date_error,data_error,relative_s\n',encoding='utf-8-sig')

doc=r'''# Apollo 人工撞击记录：逐条清洗、处理与原始波形总图

版本：2026-11-03。对象为本项目已取得的 **9 次人工撞击、21 个事件—台站组合、60 条实际 MP 分量记录**，另保留 3 个缺失槽位。这里的“所有”指这一明确的数据集合，不是整个 Apollo 档案。

本次已实际运行逐条清洗和去响应，并重新计算频带筛查。每个事件、台站、分量保留独立结果与处理日志。**完成处理不等于数据已无异常，也不等于已经具备散射反演资格。** 未能可靠恢复的内容没有被补造成观测；未经确认的候选瞬变仍保留在波形中。

## 1. 先打开总图

- [一张包含全部记录的总图 PNG](../figures/individual_cleaning_20261103/Apollo_全部原始与独立处理波形_总图.png)
- [同一张总图 PDF：可放大阅读](../figures/individual_cleaning_20261103/Apollo_全部原始与独立处理波形_总图.pdf)
- [逐条处理清单 CSV](../results/individual_cleaning_20261103/per_record_processing.csv)
- [240 项逐分量频带筛查 CSV](../results/individual_cleaning_20261103/per_record_band_screen.csv)
- [每一段缺口、排除、边缘和瞬变的时间区间](../results/individual_cleaning_20261103/processing_interval_ledger.csv)

总图共 63 行槽位，每一行有四列：**原始 DU → 清洗后 DU → 去响应并滤波后的名义速度 → 本条处理说明**。前两列共用该行的纵轴范围，能直接看到清洗究竟改了什么；第三列的单位是 nm/s，不能与 DU 直接比较幅值。各行使用自己的纵轴，未做峰值归一化。横轴统一使用 ATT 校正后的时标，原始计数的数值和顺序未改变，没有为了对齐而重新采样。

选择三个波形阶段是为了区分两件事：第二列显示对数据异常的实际处理；第三列显示去仪器响应和频带限制的结果。如果第二列与第一列一样，说明本条没有足够依据改变该处计数，不是漏做处理。

MH1、MH2 保留仪器原始水平分量方向，没有伪标为南北／东西或径向／横向；MHZ 为垂直分量。

图中灰色顶部条为原始缺样；红色条为量程端点或疑似内部削顶附近的排除区；紫色条为未决瞬变区（波形保留）；绿色条为接受的模型减除窗口。清洗计数上的橙色圈为改动的尖峰样点。速度曲线的橙色部分为处理边缘，保留显示但不用于本轮频带初筛。

**没有通过筛查的记录仍画出 0.3–0.5 Hz 诊断曲线。这个频段不是替该条记录认定的“有效频段”。** 图旁会写“仅诊断，未通过初筛”。“通过初筛”也仅针对下述时间窗与判据，不能推广为全部尾波、全时段或绝对幅值已经可靠。

## 2. 本次实际做了什么

{STATS}

处理前后均核对了现代 MiniSEED 的 SHA-256，并逐样点比较原始计数；原始 21 个文件及旧版 60 个 NPZ 未被改写。所有修改均可由尖峰日志与保存的瞬变模型重建。不存在整条记录替换、缺口补零或用别的分量代替 MHZ 的操作。

三个缺失槽位是 A16SIVB–S14–MHZ、A17SIVB–S14–MHZ、A17LM–S14–MHZ。档案未返回这些分量，与既有 S14 MHZ 故障时段一致。它们继续以明确的无数据面板表示。

## 3. 文献更新与本项目采用的证据

| 文献／数据源 | 与本次任务有关的内容 | 本次实际使用和边界 |
|---|---|---|
| [Zhang 等（2025），Methods for Cleaning Apollo Passive Seismic Data](https://doi.org/10.1029/2025EA004710) | 区分尖峰、响应形状的 glitch、S14 幅值偏移与内部削顶；提出阶跃响应拟合 | 用于异常类型、位翻转约束和阶跃响应模型；本项目检测与接受阈值另外明确列出，不冒充论文原值 |
| [Zhang 作者代码与数据集](https://doi.org/10.18715/IPGP.2024.lsc22f10) | 发布单个 glitch 的 MATLAB 代码、传递函数和部分已处理撞击数据 | 已下载代码和说明；没有把作者的 116 个撞击子集称为我们的 9 次人工撞击的现成清洗结果，也没有下载并替换整包波形 |
| [Liu、Xiao、Li（2025），Acceleration-Related Glitch Patterns…](https://doi.org/10.1029/2025JE009277) | 识别台站相关的加速度型异常并发布目录 | 下载并核对作者的 36 个目录文件，提取与本项目时间窗相关的目录行，辅助候选判定；目录命中仍不保证逐样点无误 |
| [Liu 等公开目录、校准命令和代码](https://github.com/liuxinigg/lunar_ACC) | 异常类别、分量、时间及校准命令表 | 锁定仓库版本，保存 URL、文件哈希、时间窗子集；本次没有训练或运行作者的深度学习模型 |
| [Liu、Xiao、Li（2026），Refined characterization of prevalent short-period (5–15 s) signals…](https://doi.org/10.1016/j.asr.2026.05.084) | 出版社摘要描述了用深度学习辅助处理 glitch 污染，并研究 S12 的 5–15 s 周期信号 | 本次新增背景依据：简单滤波不能保证去除 glitch；周期信号也不能仅因像“噪声”就全部删除。已核对出版社摘要，未完整复现该工作流 |
| [Nunn 等（2022），Apollo 档案重建](https://doi.org/10.3847/PSJ/ac87af)及[官方处理示例](https://github.com/cerinunn/pdart/blob/master/getting_started.ipynb) | 档案时标、缺失数据和仪器响应处理 | 从现代 MiniSEED 与 StationXML 出发，保留缺样标记。档案修复与逐事件异常清洗是两个层次 |
| [Nunn 等（2024），人工撞击波形研究](https://doi.org/10.3847/PSJ/ad83d2) | 事件—台站覆盖及文献窄带波形比较 | 0.3–0.5 Hz 用作文献对照和未通过初筛时的诊断展示；这里画的是速度，并非其位移图的严格复现 |

检索与读取日期为 2026-11-03。“最新研究”在这里意味着纳入上述 2025–2026 年证据；不声称已经完成对全部 2026 年文献的系统综述。

### 3.1 独立目录交叉核对

作者目录提取窗为每次撞击的地球接收时刻前 650 s 至后 3650 s，略宽于本项目约前 600 s 至后 3600 s 的实际波形，用于检查靠近边界的异常。共取得 **187 条邻窗目录记录**；同一物理异常可以在多个分量或类别中重复出现，所以 187 不是独立 glitch 个数。图中的“目录命中”也是邻窗目录行数，不能当作需要减除的次数。

本地候选峰落在目录起止时间向两侧各扩展 10 s 的范围内，记为时间关联。10 s 是项目关联容差，用于容纳目录定义及其时标与本地 ATT 时标尚未完全核对的差别，**不是新的台钟修正**。原始目录、类别和时间均保留。目录未命中的候选不会仅凭高拟合度自动减除。

目录文件名中的 `ACC-Spike` 是作者定义的加速度型异常形态标签，不能直接等同于本报告按位翻转识别的“单点尖峰”。两者没有混作同一种清洗规则。

校准命令表中的 command 4 为 LP 校准开关。本次在同样的扩展窗内没有发现对应台站的校准命令。这个结果是“公开表中没有命中”，不能证明原始观测期间绝不可能存在未被记录的校准操作。也没有将外形类似校准的所有信号直接认定为校准信号。

### 3.2 为什么不能把全网波形都当作已经被论文清洗过

Zhang 数据说明明确限定了其子集和处理分量；作者单个 glitch 代码仍要求给定候选索引与仪器工作模式。它不是一个无需检查、对所有事件所有分量都可靠的黑箱。本次的每条输出都是从本项目原始记录重新处理得到，保存了自己的改动、排除和未决项。

## 4. 每条记录的清洗规则

### 4.1 单点尖峰：只修正有强约束的位翻转

尖峰是在一个或少数采样点突然偏离邻近数据的异常；不能把振幅大的地震峰直接叫作尖峰。根据 Zhang 对位翻转的说明，本次只接受能够通过**唯一一个二进制位反转**回到邻近波形的单点候选，而不直接用平滑值替换所有大峰。

项目判据：点相对于两侧邻点均值至少偏离 16 DU，并达到局部一阶差分典型尺度的 16 倍；前后邻点彼此接近；前后约 5 s 内无缺样；在第 4–9 位（从 0 开始计数）的反转中只有一种满足邻域限制。修正值还需与第二邻点相容。阈值均为保守项目设置，未从论文借用为“标准值”。多点突变、低幅位错误及不唯一的候选不自动改动。

实际只修正 **A14SIVB–S12–MH2，ATT 相对时刻 3091.820881 s，样点索引 24466：790 DU → 534 DU**，对应翻转值 256 DU。完整邻域和规则见尖峰日志。该修正是满足模型约束的估计，不能声称恢复了独立已知的真实值。

合成检验采用量化背景叠加单点位翻转：123 个注入点恢复 122 个，未注入位置无修改；另一个连续振荡波包对照未被修改。这只是算法的合成健全性检查，不是本批真实数据上已测得的查准率和召回率，也不说明漏检率只有 1/123。

### 4.2 glitch：先拟合，结合目录和残差，再决定是否减除

模型写为：

\[
d(t)=c_a g_a(t-t_g)+c_v g_v(t-t_g)+c_u g_u(t-t_g)+b_0+b_1t+r(t).
\]

三个 \(g\) 是仪器对加速度、速度、位移阶跃的响应；\(b_0+b_1t\) 是局部背景基线，\(r\) 是剩余波形。仅减去三个阶跃响应之和，**不把拟合的背景常数和趋势一并当成异常删除**。减除发生在原始数字计数域，之后才进行去响应。

传递函数表达式来自 Zhang 公开的 `Transfer_Function.m`。按作者列出的平坦模式时段核对，本批记录均采用 peaked 模式。参数搜索边界为 \(f_0=0.045–0.085\) Hz、阻尼参数 \(h=0.6–1.1\)、\(K_2=1.3\times10^{-5}–1.9\times10^{-5}\)，来自公开代码的搜索范围。这里拟合的是仪器异常响应，不是地下速度扰动；这些数值不能转作散射模型参数。

本项目实现与作者 MATLAB **并非逐行复制或严格复现**：使用标准 FFT 频率格点产生 53 Hz 模板，再在原采样时刻评估；以粗网格和有界非线性最小二乘优化仪器参数及起始时间，线性求解三个阶跃幅度与背景趋势。没有采用作者完全相同的端点拉格朗日约束和加权目标。模板 53 Hz 不代表 Apollo 观测获得了更高分辨率。

本地候选由相对中值背景的突出孤立瞬变识别；拟合窗为候选峰前 8 s 至后 100 s。含缺口或削顶排除区的窗口不拟合。212 个本地候选中，137 个窗口实际完成拟合；其余保留“窗口内有缺口／排除区”等原因。候选一词不等于已经确定的仪器异常，特别是振荡波包也可能触发检测。

接受减除要求：目录时间关联、拟合相对去线性趋势基线的方差减少率至少 0.95、窗口完整且未削顶、检查原始／拟合／残差形态、减除窗口之间不重叠。本轮完成候选图的初步图件检查；独立研究复核待完成。13 个接受结果的方差减少率约 0.953–0.991，完整残差和模型均保存。这一阈值为本项目决定，不是文献保证真实信号不受损的界限。

不满足条件的候选保留在曲线上并着色标记。没有用“拟合后好看”作为理由删掉它们。目录内但未被本地检测器选中的异常也进入待核标记；其标记覆盖起点前 10 s 到至少起点后 100 s，以提示可能的响应尾部。自动检测和目录都可能漏检，未标记区并不等于已证明干净。

### 4.3 饱和与内部削顶：排除而不是重建

修正单点尖峰之后，记录中仍为 0 或 1023 DU 的样点被记作“量程端点”，向前后各扩大约 1 s 作为排除区。到达端点也可能包含其他传输问题，故不把每一点都无条件认定为物理饱和。这里的处理目标是避免把无法确定的受限幅值用于去响应和频谱估计。

对 S14 额外检查文献报道的 319、383、447、511、575、639 DU：至少连续 3 点构成平顶／平底，且左右约 2 s 的波形同侧离开该值至少数个 DU，才作为疑似内部削顶。不能仅凭 511 DU 样点较多就认定削顶，因为安静或量化背景本身可能大量落在这一值。此规则只识别一种保守形态，也可能漏掉更短或更复杂的削顶。

**疑似内部削顶是项目筛查标志，不是已经查明的硬件失真。** 原始波形保留；清洗分支保守排除这些窗口以便后续复核。总图红条同时包含量程端点和疑似内部削顶，逐条清单分别给数。

Zhang 表 2 的幅值空码段校正规则起于 1973 年，而本批人工撞击记录来自 1969–1972 年，因此本次没有机械套用这张表。这个决定不意味着早期 S14 没有失真；内部削顶和未解释异常仍须单独处理。

## 5. 清洗之后如何去响应和选频

| 步骤 | 实际设置 | 来源与限制 |
|---|---|---|
| 时间 | 延用已审计的 ATT 局部仿射校时，保留名义时标副本 | 基于已有 ATT；未重新插值振幅，图零时刻仍为地球接收撞击时刻 |
| 缺样 | 大缺口分段；原始封闭缺口不超过 2 个样点时仅作计算用线性桥接 | 项目设置。处理后恢复全部原始缺样为 NaN；排除区不桥接 |
| 短段 | 连续段不足 60 s 不做去响应 | 项目保守显示规则，原始 DU 仍显示，不能称作观测缺失 |
| 趋势 | 每个连续计算段去线性趋势、去均值 | 为响应反卷积作准备；与第二列清洗计数的保留基线不同 |
| 响应 | StationXML 名义响应，输出 VEL；预滤波 0.05/0.1/1.5/2.0 Hz；`water_level=None`；taper_fraction=0.03 | 流程参照 Nunn，具体速度分支预滤波和边缘参数为项目设置。未完全重建增益命令历史 |
| 采样 | 响应计算采用 StationXML 名义 6.625 Hz；带通采用 ATT 推算的实际采样率 | 两者明确记录，不把微小时钟漂移隐去 |
| 带通 | SciPy `butter(N=4)` 带通加双向 `sosfiltfilt` | N=4 为原型阶数；复合带通及双向操作不能简单称作“总共四阶” |
| 边缘 | 每段前后各 max(20 s, 段长的 3%) 标记为边缘 | 项目保守掩膜；不是证明滤波影响绝不超出此范围 |
| 短缺口影响 | 临时桥接点前后各 10 s 另外不参与频带筛查 | 插值点恢复缺失并不消除邻近影响；10 s 是待敏感性检验的项目保护范围 |
| 待核瞬变 | 保留波形，相关窗口不进入噪声／信号频带筛查 | 不用未知异常帮信号“抬高”SNR |

四个候选频带为 **0.3–0.5、0.5–0.9、0.3–0.9、0.9–1.5 Hz**。每条都重新计算，没有沿用旧版“30 个频带通过”的计数。

噪声窗为撞击前 −450 至 −50 s；从 −450 s 开始是为了避开约 4200 s 长记录最前端的 taper 保护区，不根据某条曲线是否好看挑选噪声。信号窗为 \(\max(50\ \mathrm{s},\frac{R}{8\ \mathrm{km\,s^{-1}}})\) 至 1800 s，其中 \(R\) 为文献距离。这个 8 km/s 仅用于粗略定义信号统计起点，**不是 P 波到时拾取，也不是对该路径速度的反演结果**。

初筛同时要求：噪声和信号统计窗各有至少 95% 的安全有效样点；带内信号 RMS／噪声 RMS 不低于 3；最长可用连续段至少 120 s，并用 Welch 谱判断至少 60% 的带内频率满足信号／噪声功率比不低于 9；噪声未被判为量化限制；ATT 校时通过既有检查。这些都是项目准入初筛标准，不是论文普遍适用阈值。

噪声的有效 DU 取值少于 5 种或 95–5 百分位跨度不超过 1 DU 时标记为量化限制。这种记录往往仍能清楚看到撞击波包，但不能把几乎不动的数字噪声底机械换算成极高而可靠的 SNR。**未过这一筛查不等于没有可用月震信号。** 同样，因某处缺口而未满足整个统计窗 95% 覆盖率，也不否定其中其他连续时间段可供研究。

通过频带中预先优先选择 0.3–0.9 Hz，再选择 0.3–0.5 Hz，再选择 0.5–0.9 Hz；0.9–1.5 Hz 仅保留诊断结果，暂不因 SNR 高就优先选入。没有通过时回退到 0.3–0.5 Hz **仅供展示**。因此各条处理方式独立，但不需要为了显示差异而强迫每条用不同频带。

{PASS}

所有物理量仍是名义响应校准值。未完成历史增益、全部异常、源时标及稳定尾波窗验证之前，本报告不新增“最终可反演”记录。不存在为了得到更多合格曲线而删去质控限制的操作。

## 6. 逐事件、台站、分量处理清单

表中 G 为本轮接受的阶跃响应减除数，U 为合并后的待核时间区间数，R 为单点尖峰修正数。U 会把相邻候选合并，也可能包含目录候选，因此不能与本地检测的 199 个未决候选直接相加。量程与内部削顶是原始疑点样点数，不等于加保护区后的排除样点数。

{TABLES}

## 7. 已减除瞬变的具体证据

[13 处瞬变的原始／模型／减除后局部图](../figures/individual_cleaning_20261103/已减除13处瞬变_局部复核.png)｜[局部复核 PDF](../figures/individual_cleaning_20261103/已减除13处瞬变_局部复核.pdf)｜[唯一单点尖峰修正的放大图](../figures/individual_cleaning_20261103/单点尖峰修正_局部复核.png)。

{GLITCHTABLE}

每一项保存了完整拟合分量、残差检查图、起止索引、参数与接受理由。参数触及搜索边界并不少见，说明这些仪器参数不宜作为唯一解解释；本次仅用它们构造局部异常模板。原始记录随时可恢复，后续应把“不减除”分支与本分支的尾波包络结果一起比较。

## 8. 如何理解仍然出现的空白和相似曲线

1. 第一列空白：原始档案缺样，或某分量整个未返回。
2. 第二列新增空白：触及量程端点／疑似内部削顶附近被保守排除，绝非补零后的静止地面。
3. 第三列新增空白：排除和缺样使连续段不足 60 s，未进行去响应。其原因可查区间账本。
4. 紫色区域仍有曲线：这部分尚未确认如何安全去除，故保留；不能当作已无污染的信号。
5. 第一、二列相同：该处未接受额外振幅修正。去响应、滤波主要体现在第三列，不能因此推断“未处理”。

总图比较完整约 70 min 记录，不代表每一段都能服务于同一种科学问题。早期到时研究、长尾包络、幅值谱和绝对能量反演的准入条件不同。下一轮应按目标时间窗逐项判断，不能用一个全局“通过／失败”代替全部用途。

## 9. 文件、复核与复现

- [处理和检查总统计](../results/individual_cleaning_20261103/summary.json)
- [逐条来源与改动一致性检查](../results/individual_cleaning_20261103/integrity_checks.json)
- [旧版 NPZ 未改写检查](../results/individual_cleaning_20261103/previous_v2_preservation.json)
- [单点尖峰修改表](../results/individual_cleaning_20261103/spike_corrections.csv)
- [疑似内部削顶表](../results/individual_cleaning_20261103/internal_clip_candidates.csv)
- [212 个本地瞬变候选及拟合摘要](../results/individual_cleaning_20261103/glitch_fit_audit.csv)
- [13 项模型减除决定](../results/individual_cleaning_20261103/reviewed_glitch_decisions.json)
- [合成尖峰检查](../results/individual_cleaning_20261103/synthetic_spike_checks.json)
- [作者目录的事件邻窗子集](../data/raw/literature/Liu2025_ACC/event_window_glitch_catalogue.csv)
- [作者目录版本、文件 URL 与哈希](../data/raw/literature/Liu2025_ACC/acquisition_manifest.json)
- [本次校准命令匹配表（0 行数据）](../data/raw/literature/Liu2025_ACC/event_window_calibration_commands.csv)

每条处理结果位于 `data/processed/individual_cleaning_20261103/事件_台站_分量.npz`，包含原始计数、清洗计数、四个频带速度、未滤波速度、原始／校正时标、原始缺口、改动／排除／边缘／待核掩膜与元数据。`glitch_subtracted_counts` 保存实际减去的波形，而非仅保存一句“已清洗”。未替换现有原始数据和历史交付包。

若要复现现有交付，使用项目已有 Python 环境运行 `code/build_individual_cleaning_20261103.py process`，再运行 `plot`；这会读取已归档的拟合结果和接受决定。若重新运行候选检测和拟合，则需要重新核对接受清单，不能把原清单无条件用于变化后的候选编号。作者目录提取由独立脚本完成，并锁定仓库版本。

## 10. 后续用于散射反演前最需要补的事项

- 对待核瞬变按研究目标窗继续逐段复核；可拟合的重叠异常应使用联合或迭代模型，并用不减除分支评估结果敏感性。
- 对 S14 的疑似内部削顶检查原始码值分布和相邻分量，不把“未套用表 2”当作失真已经解决。
- 重建或约束每条记录的仪器增益与响应状态；当前绝对幅值不可直接跨站当成散射强弱。
- 在真正需要拟合的早期窗、包络峰后窗和晚期尾波窗分别选择连续有效数据，检验频段和保护宽度敏感性。
- 以处理差异作为观测不确定性的一部分，保留原始、保守清洗和进一步清洗分支；不要让清洗模型预先决定所要反演的尾波衰减。

本次交付满足“所有已取得记录的原始／处理后同图比较及独立处理说明”；尚未解决的异常以可追溯标记交付，而不是宣称已恢复为真实、完整、无失真的月震记录。
'''
stats=(f"- 实际处理：{summary['actual_records']} 条，缺失槽位 {len(summary['missing_records'])} 条。\n"
       f"- 单点尖峰：{summary['corrected_spike_samples']} 点，位于 {summary['records_with_spike_correction']} 条记录。\n"
       f"- 目录支持且通过拟合、视觉检查后减除：{summary['subtracted_glitches']} 处，涉及 {sum(r['glitch_subtracted_count']>0 for r in good)} 条记录。\n"
       f"- 出现量程端点：{summary['records_with_rails']} 条记录；发现疑似内部削顶：{summary['records_with_internal_clip_suspects']} 条。两类可重叠。\n"
       f"- 当前所选频带通过保守初筛：{summary['selected_band_screen_pass_records']} 条；其余 {summary['diagnostic_only_records']} 条仍输出诊断波形及失败原因。\n"
       '- 最终获准用于散射反演：0 条；这不是没有信号，而是增益和目标尾波窗等验证尚未完成。')
passes='本次通过所选频带初筛的是：'+ '；'.join(r['record']+'（'+r['selected_band_hz']+' Hz）' for r in good if r['selected_band_screen_pass'])+'。'
tables=[]
for eid in dict.fromkeys(r['event_id'] for r in recs):
 rr=[r for r in recs if r['event_id']==eid]
 tables.append(f"### {eid}\n\n[分事件高清图](../figures/individual_cleaning_20261103/{eid}_原始与独立处理.png)\n\n| 台站／分量 | 距离 km | R / G / U | 量程点／内部疑点 | 原始缺样 % | 展示频带 Hz | 初筛 |\n|---|---:|---:|---:|---:|---|---|\n")
 for r in rr:
  if r['status']=='missing_archive':tables.append(f"| {r['station']} {r['channel']} | {r['distance_km']:g} | — | — | — | — | 档案未返回 |\n");continue
  tables.append(f"| {r['station']} {r['channel']} | {r['distance_km']:g} | {r['spike_corrected_samples']} / {r['glitch_subtracted_count']} / {r['unresolved_transient_intervals']} | {r['rail_samples']} / {r['suspected_internal_clip_samples']} | {r['raw_gap_pct']:.2f} | {r['selected_band_hz']} | {'通过；非最终准入' if r['selected_band_screen_pass'] else '未过；诊断展示'} |\n")
 tables.append('\n')
gtable='| 记录 | 候选编号 | 相对峰时 s | 方差减少率 | 目录关联行数 |\n|---|---|---:|---:|---:|\n'
for f in fits:
 if f['fit_id'] in dec:gtable+=f"| {f['record']} | {f['fit_id'].split('_')[-1]} | {f['peak_time_s']:.3f} | {f['variance_reduction']:.4f} | {len(f.get('catalogue_matches',[]))} |\n"
doc=doc.replace('{STATS}',stats).replace('{PASS}',passes).replace('{TABLES}',''.join(tables)).replace('{GLITCHTABLE}',gtable)
path=ROOT/'docs/15_Apollo逐条清洗与全波形总图_20261103.md';path.write_text(doc,encoding='utf-8')
# Human-facing decision reasons, one per record, not only codes.
translated={'quantization_limited_noise':'噪声底受数字量化限制','safe_window_coverage_below_95pct':'噪声或信号窗安全覆盖不足95%',
 'RMS_SNR_below_3_or_unavailable':'RMS信噪比不足3或无法计算','PSD_support_below_60pct_or_unavailable':'谱支持比例不足60%或连续谱窗不足',
 'unresolved_clock':'ATT时钟未解决'}
report=[]
for r in good:
 br=next(x for x in bands if x['record']==r['record'] and x['band_hz']==r['selected_band_hz'])
 report.append(dict(记录=r['record'],频段Hz=r['selected_band_hz'],频带用途='通过初筛但未最终准入' if r['selected_band_screen_pass'] else '仅用于诊断展示',
  尖峰修正点数=r['spike_corrected_samples'],瞬变模型减除数=r['glitch_subtracted_count'],待核合并时段数=r['unresolved_transient_intervals'],
  原始缺样百分比=r['raw_gap_pct'],排除百分比=r['excluded_pct'],短段未处理百分比=r['short_segment_pct'],
  原因='；'.join(translated.get(k,k) for k in br['reason'].split(';') if k) or '通过本项目频带初筛；仍需增益和目标窗复核'))
b.writecsv(R/'逐条处理说明_中文.csv',report)
print(path, len(doc),'characters')
