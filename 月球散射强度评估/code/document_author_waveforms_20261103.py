from pathlib import Path
import csv,json,hashlib,zipfile,re
import fitz
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results/published_waveforms_20261103';F=ROOT/'figures/published_waveforms_20261103';S=ROOT/'data/raw/published_waveform_sources'
summary=json.loads((R/'execution_summary.json').read_text());idx=json.loads((R/'split_figure_index.json').read_text());xiao=json.loads((R/'xiao_author_window_audit.json').read_text())
rows=list(csv.DictReader((R/'逐记录作者处理与频段状态.csv').open(encoding='utf-8-sig')))
events=list(csv.DictReader((ROOT/'results/impact_audit/events_and_domains.csv').open(encoding='utf-8-sig')))
pairs=list(csv.DictReader((ROOT/'results/impact_pairs_literature.csv').open(encoding='utf-8-sig')))
ntree=json.loads((S/'cerinunn_impact_simulations_tree.json').read_text());xtree=json.loads((S/'MrXiaoXiao_Apollo_Disturbance_Detection_tree.json').read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
release=json.loads((S/'release_verification.json').read_text()) if (S/'release_verification.json').exists() else None
release_note=('已下载论文归档版本，`util.py` 与本次调用文件逐字节一致。' if release and release['current_matches_published_release'] else '本次固定 GitHub 提交；Zenodo 论文版本的逐字节核对尚未完成。')
refs={
'N20':('Nunn et al. (2020). Lunar Seismology: A Data and Instrumentation Review. Space Science Reviews, 216, 89.','https://doi.org/10.1007/s11214-020-00709-3'),
'N22':('Nunn et al. (2022). A New Archive of Apollo’s Lunar Seismic Data. The Planetary Science Journal, 3, 219.','https://doi.org/10.3847/PSJ/ac87af'),
'N24':('Nunn, Fernando & Panning (2024). Artificial Impacts on the Moon: Modeling 3D Seismic Propagation Effects with AxiSEM3D. The Planetary Science Journal, 5, 246.','https://doi.org/10.3847/PSJ/ad83d2'),
'Z25':('Zhang et al. (2025). Methods for Cleaning Apollo Passive Seismic Data. Earth and Space Science, e2025EA004710.','https://doi.org/10.1029/2025EA004710'),
'X25':('Xiao, Li, Shi, Liu & Nakamura (2025). Detection and Removal of Strong Transient Disturbances for Uncovering Weak Long-Period Signals in Apollo Lunar Seismic Data. BSSA, 115(4), 1435–1448.','https://doi.org/10.1785/0120250012'),
'K26':('Kim, Song & Schmerr (2026). Locating Moonquakes With Single-Station Seismology. Geophysical Research Letters, 53, e2026GL122962.','https://doi.org/10.1029/2026GL122962'),
'O21':('Onodera et al. (2021). Numerical Simulation of Lunar Seismic Wave Propagation: Investigation of Subsurface Scattering Properties Near Apollo 12 Landing Site. JGR: Planets, e2020JE006406.','https://doi.org/10.1029/2020JE006406'),
'O22':('Onodera et al. (2022). Quantitative Evaluation of the Lunar Seismic Scattering and Comparison Between the Earth, Mars, and the Moon. JGR: Planets, e2022JE007558.','https://doi.org/10.1029/2022JE007558'),
'K25':('Kim et al. (2025). A New Lunar Crustal Thickness Model Constrained by Converted Seismic Waves Detected Beneath the Apollo Seismic Network. GRL, e2024GL114506.','https://doi.org/10.1029/2024GL114506'),
'T25':('Turner et al. (2025). Statistical Methods to Distinguish Shallow Moonquakes From Impacts. JGR: Planets, e2024JE008739.','https://doi.org/10.1029/2024JE008739'),
}
report=f'''# Apollo 撞击波形：已发表成果筛选、作者代码复现与分图说明

更新：2026-11-03。范围：既定 9 次人工撞击、21 个事件—台站配对、60 条实际 MP 分量记录与 3 个缺失槽位。

## 1. 本轮结论与交付边界

本轮依照新的要求，查找论文配套仓库，并只复现作者已公开的明确步骤。**没有使用上一轮自编的 glitch 检测、拟合或清洗结果；没有新增任何带通滤波，也没有执行 0.3–0.5 Hz 滤波。**

当前不能诚实地给每条记录贴上“已找到最优完整清洗波形”的标签。实际得到的结果是：

1. **完整覆盖的可复现基础入口：Nunn 2024。** 作者仓库直接提供全部 21 个配对的 MiniSEED 输入。本轮对 60 条 MP 分量调用原封不动的 `util.linear_interpolation(interpolation_limit=1)`，生成未滤波的基础预处理对照。它处理缺样，不负责去 glitch、幅值偏移、内部削顶或仪器响应恢复，不能当成全面清洗结果。
2. **明确不选作撞击尾波输入：Xiao 2025 的现成排除窗。** 已取得作者的 5 个 S-IVB 数据包和配套代码；文件中的 `Before/After` 是撞击前后各 10 天。按作者排除窗复现后，撞击后首小时的存储采样点被排除约 95.7%–100%。这是研究目标不匹配，不是作者方法无效。
3. **优先核验的处理后成品候选：Kim 2026。** 论文与 DOI 注册元数据明确列出人工撞击三分量 `.mat`、偏振结果及代码。不过本次 Figshare 页面返回空的 202 响应，API 和下载入口返回 403，尚未取得 `dataset.zip`。因此只能列为“最值得优先检查的候选”，不能声称下载成功、逐条覆盖已验证或已选为最优。
4. **Zhang 2025 的现成数据不匹配本批人工撞击。** 已逐行读取其 116 事件 Excel 目录，9 个目标日期均没有匹配；不因论文引用了数据集就假定存在这些人工撞击的清洗后文件。其 MATLAB 方法仍有价值，但缺少本批事件的作者确认异常位置，不能直接套用示例的索引和参数。

建议现阶段用 **Nunn 原始档案＋缺样掩码** 保留证据，用作者有限插值版本作对照；正式散射反演暂不把任何一套称为“已完成全异常清洗的最优数据”。这一选择以保留撞击尾波和可追溯性为依据，属于本项目的适用性判断，并非文献宣称的数据排名。

直接查看：[分图图册](17_作者来源波形分图图册_20261103.md)｜[13 页对照图 PDF](../figures/published_waveforms_20261103/Apollo_作者基础预处理_13页.pdf)｜[逐记录处理与频段表](../results/published_waveforms_20261103/逐记录作者处理与频段状态.csv)。

## 2. 怎样判断“最优”

这里的目标是估计散射强度，而不是把曲线画得更平滑。候选数据至少需要满足：事件和台站分量确实匹配；保留足够长的上升段与衰减尾波；说明幅值单位、时轴、仪器响应和已经施加的滤波；可区分真实测量、插值与删除；处理方法来自公开论文或作者代码。

因此，下载了原始输入不等于取得清洗成品；下载了模拟波形不等于取得处理后观测；发表了处理方法也不等于每个台站的每条记录都已处理。删去强信号以研究长周期弱信号，或为了识别直达波而抑制非相干成分，均不能自动视为适合本项目的清洗。

## 3. 数据源逐项核验

| 来源 | 实际公开内容与本次证据 | 与目标记录的关系 | 本轮选择 |
|---|---|---|---|
| [Nunn 2024](https://doi.org/10.3847/PSJ/ad83d2)；[GitHub](https://github.com/cerinunn/impact_simulations)；[论文代码归档](https://doi.org/10.5281/zenodo.13821562) | 已下载 21 个 `local_MSEED` 输入、响应文件、处理代码；`write_local_data.helper.py` 证明文件来自 FDSN 下载后直接写盘 | 9 事件、21 配对、60 MP 分量，3 个 S14/MHZ 槽位缺失 | 原始参照与作者基础步骤复现；不是作者清洗成品 |
| [Zhang 2025](https://doi.org/10.1029/2025EA004710)；[IPGP 数据集](https://doi.org/10.18715/IPGP.2024.lsc22f10) | 已核验 `Impact_catalog_116.xlsx`、README、MATLAB 代码；未为无匹配事件盲目下载整个 2.11 GB 波形包 | 116 目录事件与本次 9 次人工撞击日期交集为 0 | 现成成品不纳入；方法保留，未迁移示例异常索引 |
| [Xiao 2025](https://doi.org/10.1785/0120250012)；[GitHub](https://github.com/MrXiaoXiao/Apollo_Disturbance_Detection)；[归档](https://doi.org/10.5281/zenodo.15166531) | 5 个真实 Git LFS NPY 数据下载完成，每个约 91.6 MB，校验通过；内含 trace＋windows，而非去噪前后两个波形数组 | A13/A14/A15/A16/A17 S-IVB 的 S12/MHZ；其他台站、分量不据此外推 | 作者时间窗仅作适用性反例，不采用为散射尾波清洗 |
| [Kim 2026](https://doi.org/10.1029/2026GL122962)；[Figshare](https://doi.org/10.6084/m9.figshare.32814290) | 已核验论文和 DataCite 元数据，后者明确列出处理波形 `.mat`、偏振结果、目录、MATLAB 脚本；文件访问受阻 | 元数据列出 LM-12/14/15/17、S4B-13/14/15/16/17 及 lp12/14/15/16 目录组织；不代表所有笛卡尔组合都有文件 | 处理后成品优先核验候选，尚未取得数值数组 |
| [Onodera 2021](https://doi.org/10.1029/2020JE006406)、[2022](https://doi.org/10.1029/2022JE007558) | 方法说明包含去响应、滤波、包络与分量转换；2022 可用性声明把观测指向 DARTS，把独立输出指向模拟结果 | A14/A16 S-IVB→S12 是高度相关的参考路径 | 可靠的方法与频段依据；本轮未取得作者处理后观测数组，不能拿模拟输出替代 |
| [Kim 2025](https://doi.org/10.1029/2024GL114506)；[Zenodo](https://doi.org/10.5281/zenodo.15632211) | Zenodo API 清单为月壳厚度网格文件 | 模型公开不等于观测波形公开 | 不作为清洗后观测来源 |
| [Liu 2025](https://doi.org/10.1029/2025JE009277)；[lunar_ACC](https://github.com/liuxinigg/lunar_ACC) | 项目已取得 ACC/标定相关目录，含事件窗目录摘录；它们是异常辅助信息 | 可辅助确定异常时间，不能等同于已完成校正的波形 | 作为参考，不把目录标记直接当作作者已接受的清洗结果 |
| [Turner 2025](https://doi.org/10.1029/2024JE008739)；[代码归档](https://doi.org/10.5281/zenodo.13786113) | 研究重点是 SP 数据的自然撞击/浅月震分类与统计分析 | 本轮目标是 9 次人工撞击的 MP 三分量；不以 SP 分类数据充当同一记录 | 背景方法，不作为本批 MP 成品替代 |

负面结论仅限定为本次已核验的仓库和文件，**不是断言互联网中绝无其他处理成品**。

### 3.1 Nunn 作者原始文件为什么不是处理成品

`write_local_data.helper.py` 请求撞击前 1800 s 至撞击后 5400 s 的波形，随后直接 `st.write(..., format="MSEED")`。文件能作为作者实际使用的可追溯输入，但没有证据支持称其为去 glitch 后的输出。

作者绘图 notebook 后续另有插值、去响应及频带设置。这次没有执行那些完整绘图处理，也没有把作者用于展示的窄带结果当作未滤波波形。

### 3.2 Zhang 116 事件匹配的具体证据

本次读取 Excel 的事件日期、小时、分钟字段，而不是依靠论文摘要推测。其首个条目为 1971-10-18；本批较晚的 A16/A17 人工撞击日期也没有匹配。完整目录摘录见 [JSON](../results/published_waveforms_20261103/zhang116_catalogue_extracted.json)。

发布代码 `Apollo_deglitch_single.m` 使用具体示例文件、指定 `index_list_2_deglitch`、仪器模式与三类预计算响应。它是有明确输入条件的单条去 glitch 示例，不是对任意记录调用即能完成所有异常清洗的通用程序。本轮没有使用上轮自拟合的索引去冒充作者给出的异常位置。

### 3.3 Kim 2026 仍需核验的内容

[DOI 注册元数据原文](../data/raw/published_waveform_sources/kim_request_4.txt) 明确说明 `dataset.zip` 含处理后的 Z/N/E 三分量 `.mat` 和独立的偏振结果文件。它还说处理脚本会载入预处理片段后执行带通与截窗。因此，**不能仅凭论文的分析频带就断定每个存储数组已经施加了相同滤波**；这必须在取得文件和脚本后核对。

需要核对：每个事件实际有哪些台站；数组的 UTC、单位和长度；时轴与本项目撞击时间是否一致；是否已去响应、旋转、归一化、删窗或重采样；存储的是未偏振筛选的输入波形，还是筛选后的结果。30 s 的 P 波分析窗与完整存储波形长度也不能画等号。当前访问失败的原因只能记为服务响应，不能推断作者未公开数据。

## 4. 本轮真正运行了什么

### 4.1 Nunn 2024：直接调用作者函数，未改算法

代码位置：[作者 util.py](../data/raw/published_waveform_sources/cerinunn_impact_simulations/util.py)。GitHub 固定树提交：`{ntree['sha']}`。{release_note}

调用：`linear_interpolation(trace, interpolation_limit=1)`。这是作者公开流程的基础步骤子集，不是完整论文流水线。输出仍为 DU，仍含直流电平和仪器响应；未减均值、未去趋势、未加窗、未去响应、未旋转、未重采样、未使用 ATT 重新校时、未滤波、未拟合 glitch、未恢复削顶。

作者函数先把 `−1` 识别为缺样，调用 pandas 线性插值，再转换为整数并恢复剩余缺样掩码。**`limit=1` 并非“只填长度恰为 1 的缺口”：在多点缺口内，它也可能填入起始的一个点。** 本轮逐点审计明确记录这一行为，没有私自修改作者函数。

| 执行审计 | 数量 |
|---|---:|
| 处理的实际 MP 分量 | {summary['actual_components']} |
| 源文件内缺样码总数（全 2 小时，不仅图中窗口） | {summary['total_source_missing_samples']:,} |
| 作者函数补入点数 | {summary['total_author_filled_samples']:,} |
| 其中位于多点缺口的补入点 | {summary['filled_samples_in_long_gaps']:,} |
| 原有有效测量值被改变 | 0 |
| 新增带通 / 去响应 / 自编去 glitch | 0 / 0 / 0 |
| 已被认定全面清洗并可直接做散射反演 | 0 |

逐条 NPZ 同时保存原始值、原始缺样掩码、作者基础预处理值、剩余缺样掩码和补入点标记。这样可以独立保留测量证据，也能看到作者步骤实际做了什么。**插值点是估计，不是找回的实测值。** 后续使用时，保留掩码的原始版本是基准；不能因曲线更连续就丢弃原始缺样信息。

### 4.2 Xiao 2025：复现作者删窗函数，评估是否适合本目标

已下载论文归档 notebook 并与本次 GitHub notebook 核对，逐字节一致。调用的 `remove_detected_windows` 函数从 notebook 原样提取，连同作者对首个负索引的边界处理一起执行。输入是作者公开 `trace` 和 `windows`；没有重新训练模型，没有自行检测异常，没有新增阈值。我们只复现删窗步骤，没有执行其后续减均值、FFT、置零频谱或 Lomb–Scargle 分析。

输出保留不规则的剩余时间点；画图时在被删除区间断线，不能把剩余两端连接为虚假的连续信号。这里的空白是作者排除窗造成的，和原始档案缺样是不同的原因。

| 人工撞击 | 台站/分量 | 作者删窗排除的撞击后 0–60 min 存储采样点 | 对散射尾波的选择 |
|---|---|---:|---|
'''
for r in xiao:report+=f"| {r['event']} | S12/MHZ | {r['removed_sample_percent_0_60min']:.2f}% | 排除该方案作为反演输入；保留诊断图 |\n"
report+='''
上述比例包括输入中的缺样码，是采样点保留审计，不是能量损失估计。结果表明这套现成排除窗会去掉主要撞击记录，不能依据“发表于期刊且可以运行”就采用。5 张独立诊断图见图册。

## 5. 每个事件、台站和分量的覆盖

同一仪器型号不意味着每条记录质量相同。本轮分别保存每条记录的缺样和插值数量；不会把 S12 的方法和可信程度自动赋给 S14/S15/S16。

| 事件 | 日期 UTC | 作者原始缓存覆盖台站 | MP 实际分量数 / 计划槽位 | 已取得的其他作者输入＋处理信息 |
|---|---|---|---:|---|
'''
for e in events:
    rr=[r for r in rows if r['event']==e['event_id']];npresent=sum(r['author_raw_exists']=='True' for r in rr)
    xs='Xiao：仅 S12/MHZ＋作者排除窗（不适用散射尾波）' if e['event_id'].endswith('SIVB') else '本轮未取得额外匹配清洗成品'
    stas='、'.join(p['station'] for p in pairs if p['event_id']==e['event_id'])
    report+=f"| {e['event_id']} | {e['time_earth_received'][:10]} | {stas} | {npresent}/{len(rr)} | {xs} |\n"
report+='''
三个缺失槽位是 A16SIVB–S14–MHZ、A17SIVB–S14–MHZ、A17LM–S14–MHZ；没有用水平分量、另一台站或模拟数据去填充。Kim 数据集的实际逐条覆盖仍待文件核验，未在表中计为“已下载”。

## 6. 频段：能给参考范围，不能把参考范围当作逐条保证

需要区别三个层次：

- **仪器响应范围**：说明传感器对不同频率有多敏感，不保证某次事件信号强于噪声。
- **作者实际分析频带**：说明某研究用了什么范围，不表示该范围内任意台站记录都可靠。
- **本条记录的可信频段**：还需该条记录的信噪比、缺样、削顶、响应校正与时轴证据。本轮没有重新计算频谱或自行选择频带，因此不编造逐条上下限。

Nunn 2020 的仪器综述指出，MP peaked 模式位移响应峰值约 0.45 Hz，flat 模式位移响应约在 0.1–1 Hz 较平坦。两种模式不能混用；名义采样率 6.625 Hz 对应的 3.3125 Hz 奈奎斯特频率也不等于可信上限。[仪器依据](https://doi.org/10.1007/s11214-020-00709-3)

| 台站/记录 | 可参考的频段 | 证据与适用界限 | 本轮是否滤波 |
|---|---|---|---|
| S12 的 MP 三分量 | 0.2–0.95 Hz：优先核验范围 | Kim 2026 §2 的三分量分析频带；是文献参照，不是本批全部记录的逐条 SNR 保证 | 否 |
| A14SIVB→S12、A16SIVB→S12 | 扩展参考：0.2–1.5 Hz（2021）或 0.3–1.5 Hz（2022） | Onodera 同两条人工撞击路径的速度波形/散射建模频带；两篇设置分别列出，不能合写成同一参数 | 否 |
| S14 的现有 MP 分量 | 0.2–0.95 Hz：待核验范围 | 相同 MP 仪器类和 Kim 2026 分析范围；仍需分量可用性及幅值偏移、削顶等核验；缺失 MHZ 无可信带 | 否 |
| S15 的 MP 三分量 | 0.2–0.95 Hz：待核验范围 | 同上；弱事件不能因仪器有响应就判为可用 | 否 |
| S16 的 MP 三分量 | 0.2–0.95 Hz：待核验范围 | 同上；不能把 S12 的单条结果平移到 S16 | 否 |

文献依据：[Kim 2026 §2](https://doi.org/10.1029/2026GL122962)、[Onodera 2021 §2.4](https://doi.org/10.1029/2020JE006406)、[Onodera 2022 §2.6.1](https://doi.org/10.1029/2022JE007558)。Kim 的 SNR 阈值用于其 P 波定位任务，不能直接当作本项目长尾波准入阈值。

**本轮每条 CSV 中 `individual_trust_band` 为 `not established`，缺失分量为 `N/A`。** 这是对证据状态的记录，不是说所有这些频率都不可用。0.2–0.95 Hz 在图上的标记也仅为参考范围，绘出的波形仍未滤波。

SP 通道属于不同传感器，不能套用以上 MP 频段，也不能用其处理后记录补齐 MP 分量；本轮未扩展成 SP 清洗任务。

## 7. 为什么暂不运行所有“清洗代码”

Nunn 基础函数可直接用于其原始档案格式，并且实测样本保持不变，因此适合先建立可追溯对照。Xiao 的现成时间窗适合其长周期研究，但会删掉目标尾波，已经用作者数据和代码实证排除。

Zhang 单条脚本所需的异常位置与模式必须先有对应证据；使用 116 自然撞击目录中的索引去处理不同日期的人工撞击会作用于错误样本。其方法的移植还涉及响应库、采样时轴与拟合窗，不能隐瞒为“直接使用作者成品”。本轮没有另造异常检测器以凑齐 60 条清洗输出。

Kim 2026 成品是下一步最有价值的核验对象，但本次访问限制尚未解决。需要先拿到公开 ZIP，检查存储波形与偏振结果的差别，再决定能否保留完整尾波。当前不把“去偏振筛选”当作“去仪器干扰”，也不凭论文图反向猜测数值数据。

## 8. 后续接入 CGFD3D 的选择规则

1. 先固定事件—台站—分量—来源版本及原始掩码，保持未滤波数据作基准。
2. 优先核验 Kim 2026 成品的处理历史和尾波长度；如已带通，按作者的原频带评价，不再次套 0.3–0.5 Hz。
3. 若需应用 Zhang 等清洗方法，必须逐条记录异常证据、作者函数、输入索引、实际改动点和拒绝原因；“程序运行成功”不能替代“物理信号未被误删”的验证。
4. 仅当观测单位、响应处理、可靠频带及有效时间窗明确后，再与 CGFD3D 合成波形作一致比较。缺失或被删的段不补成零后计算尾波能量。
5. 当前尚未开展新的散射参数反演，也未据此改动参考介质模型。

## 9. 文件、复现和验证

- [分图图册](17_作者来源波形分图图册_20261103.md)：13 张基础对照，每张最多 2 台站、6 行；另有 5 张 Xiao 适用性诊断。
- [逐记录 CSV](../results/published_waveforms_20261103/逐记录作者处理与频段状态.csv)：63 槽位均有独立状态、距离、处理及频段说明。
- [执行统计](../results/published_waveforms_20261103/execution_summary.json)、[输入前后哈希](../results/published_waveforms_20261103/raw_hashes_before_after.json)、[Xiao 逐窗审计](../results/published_waveforms_20261103/xiao_author_window_audit.json)。
- [作者源文件清单](../results/published_waveforms_20261103/acquisition_manifest.json)：固定提交、下载路径、文件尺寸与 SHA-256。
- 原始下载保存在 `data/raw/published_waveform_sources/`；复现输出在 `data/processed/author_code_reproduction_20261103/`，与上一轮自编清洗结果隔离。

运行时只直接调用 Nunn 原始 `util.py` 和从 Xiao 原 notebook 提取的函数；项目脚本负责文件路由、保存、计数和画图，不实现新的清洗算法。所有原始 MiniSEED 校验未变；60 条记录的有效原测量值逐点相同；没有把参考频带应用到绘图数据。

上一轮 `docs/15_Apollo逐条清洗与全波形总图_20261103.md` 和 `individual_cleaning_20261103` 目录保留为历史试验，**不作为本次“作者成品/作者代码复现”的处理证据**。

## 10. 参考文献与公开仓库

'''
for code,(title,url) in refs.items():report+=f'- **{code}**：[{title}]({url})\n'
report+='''
数据仓库：

- Nunn 2024：[GitHub](https://github.com/cerinunn/impact_simulations)，[代码归档 DOI](https://doi.org/10.5281/zenodo.13821562)。其另一 Zenodo 条目 [10631693](https://doi.org/10.5281/zenodo.10631693) 主要是模型参数与模拟输出，不与处理后观测混淆。
- Zhang 清洗数据：[IPGP Dataverse DOI](https://doi.org/10.18715/IPGP.2024.lsc22f10)。
- Xiao 2025：[GitHub](https://github.com/MrXiaoXiao/Apollo_Disturbance_Detection)，[Zenodo 版本归档](https://doi.org/10.5281/zenodo.15166532)。
- Kim 2026：[Figshare 数据 DOI](https://doi.org/10.6084/m9.figshare.32814290)，[DataCite 可核验元数据](https://api.datacite.org/dois/10.6084/m9.figshare.32814290)。

检索截止 2026-11-03。下载失败、无匹配记录和方法不适用分别记录，不相互替代。
'''
(ROOT/'docs/16_作者公开波形筛选与代码复现_20261103.md').write_text(report,encoding='utf-8')

atlas='''# 作者来源波形分图图册

2026-11-03。每张主图最多两个台站、六个分量槽位，按事件独立分组。没有重新带通滤波；没有使用上一轮自编清洗结果。

主图左列为 Nunn 作者缓存的原始 DU，右列为其公开缺样处理函数的复现结果。**右列只完成基础预处理，不表示已去 glitch、幅值偏移或削顶。** 两列保持同一纵轴，橙点为插值值。图旁计数针对完整源文件约两小时，图中显示撞击前 10 min 至后 90 min。

[完整选型与方法说明](16_作者公开波形筛选与代码复现_20261103.md)｜[13 页主图 PDF](../figures/published_waveforms_20261103/Apollo_作者基础预处理_13页.pdf)｜[5 页排除方案诊断 PDF](../figures/published_waveforms_20261103/Xiao_作者排除窗适用性_5页.pdf)

## 快速索引

| 事件 | 独立图 |
|---|---|
'''
for e in events:
    entries=[r for r in idx if r['event']==e['event_id']]
    atlas+=f"| {e['event_id']} | "+' · '.join(f"[{'、'.join(r['stations'])}](../figures/published_waveforms_20261103/{r['png']})" for r in entries)+' |\n'
for i,r in enumerate(idx,1):
    atlas+=f"\n## {i:02d} · {r['event']} · {'、'.join(r['stations'])}\n\n![{r['event']} 原始与作者基础处理](../figures/published_waveforms_20261103/{r['png']})\n\n[单页 PDF](../figures/published_waveforms_20261103/{r['png'].replace('.png','.pdf')})\n"
atlas+='''
## 附：为什么不采用 Xiao 的现成排除窗

以下各图依次展示作者 NPY 中的输入、作者排除窗、原样调用作者删窗函数后的剩余记录。`Before/After` 是事件前后各十天，不是清洗前后。它们用于长周期弱信号分析，删去了本研究关心的大部分撞击尾波。第三行空白表示作者删窗造成的排除，不能视为无震动。
'''
for r in xiao:atlas+=f"\n### {r['event']} · S12/MHZ\n\n首小时存储采样点排除 {r['removed_sample_percent_0_60min']:.2f}%。\n\n![作者排除窗复现](../figures/published_waveforms_20261103/{r['figure']})\n"
(ROOT/'docs/17_作者来源波形分图图册_20261103.md').write_text(atlas,encoding='utf-8')

# Combine scientific figure exports into page-by-page viewers; no image resampling.
for name,files in [('Apollo_作者基础预处理_13页.pdf',[r['png'].replace('.png','.pdf') for r in idx]),
                   ('Xiao_作者排除窗适用性_5页.pdf',[r['figure'].replace('.png','.pdf') for r in xiao])]:
    doc=fitz.open()
    for f in files:
        with fitz.open(F/f) as p:doc.insert_pdf(p)
    doc.save(F/name);doc.close()

manifest=[]
for repo,tree in [('cerinunn_impact_simulations',ntree),('MrXiaoXiao_Apollo_Disturbance_Detection',xtree)]:
    urlrepo=repo.replace('_','/',1) if repo.startswith('cerinunn_') else 'MrXiaoXiao/Apollo_Disturbance_Detection'
    for p in sorted((S/repo).rglob('*')):
        if not p.is_file() or p.name.endswith('.source.txt'):continue
        rel=p.relative_to(S/repo).as_posix()
        if p.name.endswith('.lfs_pointer.txt'):continue
        lfs=p.with_suffix('.lfs_pointer.txt').exists()
        url=f'https://media.githubusercontent.com/media/{urlrepo}/{tree["sha"]}/{rel}' if lfs else f'https://raw.githubusercontent.com/{urlrepo}/{tree["sha"]}/{rel}'
        manifest.append({'source':repo,'fixed_tree_sha':tree['sha'],'url':url,'path':p.relative_to(ROOT).as_posix(),'size':p.stat().st_size,'sha256':h(p),'git_lfs_object':lfs})
(R/'acquisition_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

readme=ROOT/'README.md';old=readme.read_text(encoding='utf-8')
heading='# 当前波形交付：作者来源审计与分图（2026-11-03）'
if not old.startswith(heading):
    old=old.replace('# 最新波形交付：逐条清洗与原始／处理后总图（2026-11-03）','# 历史试验：自编逐条清洗（已被本轮要求取代）',1)
    old=old.replace('本次波形处理状态以第15号报告为准；','以下第15号报告仅记录历史自编处理状态，不作为作者成品证据；',1)
    top=heading+'''

[作者公开波形筛选与代码复现报告](docs/16_作者公开波形筛选与代码复现_20261103.md)｜[分图图册](docs/17_作者来源波形分图图册_20261103.md)｜[13 页主图 PDF](figures/published_waveforms_20261103/Apollo_作者基础预处理_13页.pdf)｜[逐记录表](results/published_waveforms_20261103/逐记录作者处理与频段状态.csv)。

根据最新要求，本轮仅查找作者公开结果并复现作者代码，不使用上一轮自编清洗。Nunn 2024 的 21 个原始配对文件和基础函数覆盖 60 条分量，主图分为 13 张；未滤波、未去响应，基础缺样处理不等于全面清洗。Xiao 2025 的 5 套 S12/MHZ 现成排除窗会删除大部分撞击尾波，已用作者代码验证并排除为散射输入。Zhang 116 事件与本批人工撞击无日期交集。Kim 2026 公开处理成品是优先核验候选，但本次文件访问受阻，未计为已取得。

**当前没有声称取得或完成 60 条最优全面清洗波形。** 文献频段与逐条可信频段分开标注；不再施加 0.3–0.5 Hz 滤波。旧版图表保留供追溯，本轮状态以第16、17号报告为准。

'''
    readme.write_text(top+old,encoding='utf-8')
historical=ROOT/'docs/15_Apollo逐条清洗与全波形总图_20261103.md'
if historical.exists():
    old=historical.read_text(encoding='utf-8');banner='> 历史试验说明：'
    if not old.startswith(banner):historical.write_text(banner+'本文件记录上轮自编清洗，已不符合当前“作者公开成品或作者代码复现”的交付口径。当前请阅读[作者来源筛选报告](16_作者公开波形筛选与代码复现_20261103.md)，不将此处结果归为作者发布成果。\n\n'+old,encoding='utf-8')
print('Written reports, figure atlas, PDFs, manifest and updated README.')
