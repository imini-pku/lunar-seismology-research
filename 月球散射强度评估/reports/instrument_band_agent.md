# Apollo 人工撞击记录：仪器、响应和有效频带审计
核验日期：2026-10-29。范围：S12、S14、S15、S16 PSE；本报告不把名义响应、档案存在和可用于反演混为一谈。

## 1. 频带结论
- **0.3–0.5 Hz：跨事件的首轮公共比较带。** Nunn、Fernando 与 Panning (2024) §2 / Fig.1 对人工撞击观测去除响应后使用该带；上限 0.5 Hz 主要为了与其模拟频率上限一致。
- **0.3–0.9 Hz：人工撞击 MP 记录的文献支持候选带。** 同文报告其所考察事件通常在该带信噪比较好，带外一般较吵。这是数据集经验，不是每台站、每个事件和每段晚时尾波都通过的认证。
- **0.3–1.5 Hz：S12 两条已研究近距路径的扩展比较带。** Onodera 等 (2022) §2.2、§2.6.1：A14 S-IVB→S12、A16 S-IVB→S12；去趋势、0.05–3 Hz 四阶 Butterworth 预滤波、3% Tukey 窗、peaked 响应校正得到速度，最后后滤波至 0.3–1.5 Hz。不能自动推广到所有 S14/S15/S16 远距记录。
- **0.1–3 Hz 不应再写成全部台站人工撞击的“有效频带”。** 它可能是其他分析使用范围，但不等于这些事件可校正且有足够 SNR 的共同频带。Nyquist 也不是有效通带。

来源：[Nunn et al. 2024，§2/Fig.1](https://doi.org/10.3847/PSJ/ad83d2)；[Onodera et al. 2022，§2.6.1/Fig.5](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022JE007558)。

## 2. 采样与名义响应
下表取自本次实际下载的 PDS StationXML 和 PDS SIS §2.6。四台站的名义采样参数相同，真实采样率随时间变化。

| 仪器/通道 | 名义采样率 | 名义采样间隔 | Nyquist | 名义响应要点 |
|---|---:|---:|---:|---|
| MP：MH1/MH2/MHZ；旧名 LPX/LPY/LPZ | 6.625 Hz | 0.1509434 s | 3.3125 Hz | peaked 位移响应峰约 2.2 s（约 0.45 Hz）；location=00 |
| MP flat：MH1/MH2/MHZ | 6.625 Hz | 同上 | 3.3125 Hz | 位移响应约 0.1–1 Hz 平坦；自然周期 15 s；location=01 |
| SP：SHZ；旧名 SPZ | 53 Hz | 0.0188679 s | 26.5 Hz | 垂直速度换能器，位移响应峰约 8 Hz；不是“到26.5 Hz都有科学有效信号” |

Nominal response 的输入单位在此次 PDS StationXML 中为 M（位移）。可经响应运算输出位移、速度或加速度；不同研究的包络要先统一物理量。作者 getting_started 示例中 MP 去响应的四角预滤波为 [0.1,0.3,0.9,1.1] Hz，SP 为 [1,2,11,13] Hz。四角预滤波的中间两点与最终分析带相关，但**四个点不是四个分析通带**。该示例是参考处理，不可取代事件质控。

来源：[PDS SIS §2.6](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/document/apollo_pse_description.pdf)；[作者处理示例](https://github.com/cerinunn/pdart/blob/master/getting_started.ipynb)。

## 3. 台站、事件时期与组件
“候选组件”表示仪器/档案可考虑，实际文件存在与事件 SNR 仍需逐道审核。

| 台站 | 本批人工撞击所处观测时期 | MP 候选组件 | 固定或时期性缺失 | 首轮频带 |
|---|---|---|---|---|
| S12 | A12 LM (1969) 至 A17 LM (1972) | MH1/MH2/MHZ | **SHZ 全任务失效**，不得用于对比；水平朝向 MH1=180°、MH2=270° | 0.3–0.5 Hz；合格后 0.3–0.9 Hz；两条 S-IVB 参考路径再检验至1.5 Hz |
| S14 | A14 LM (1971) 至 A17 LM (1972) | 1971：三分量候选；1972-03-12之后：MH1/MH2候选 | **MHZ 在1972-03-12 00:00至1976-11-17 00:00被新档案排除**；A16/A17撞击不能按完整三分量使用；未取得MH2整段故障证据，不猜排除 | 0.3–0.5 Hz；合格后0.3–0.9 Hz |
| S15 | A15 LM (1971) 至 A17 LM (1972) | MH1/MH2/MHZ | A15 S-IVB撞击早于S15部署；不能凭任务号视作S15记录 | 同上 |
| S16 | A17 S-IVB和A17 LM (1972) | MH1/MH2/MHZ | A16 S-IVB撞击早于S16部署；MH1=334.5°、MH2=64.5°须正确旋转 | 同上 |

上述人工撞击日期均落在各站通常的 peaked 运行阶段。S15 首次较长 flat 时段为1971-10-24至11-08，S16为1972-05-13至05-14；其余较长 flat 时段主要始于1974/1975/1976。因此不能直接把 flat 通带当成本批撞击记录响应。但仪器曾有短时测试切换，作者提示location码也可能短时误标；最终以事件窗文件location、响应、命令日志三者交叉核对。

Nunn2024 明确 A16/S-IVB→S14 展示的是 MH1，因为 Z 不可用。该文低SNR标记包括 A15/LM→S12、S14，A17/LM→S14、S16，以及A17/S-IVB→S14；这些配对是“有记录但未进入其主图”，不是“无记录”。

来源：[Nunn et al. 2022，新档案故障说明](https://doi.org/10.3847/PSJ/ac87af)；[Nunn et al. 2020，Table2](https://doi.org/10.1007/s11214-020-00709-3)；[Nunn2024 Table1/Fig.1](https://doi.org/10.3847/PSJ/ad83d2)；站姿态来自此次本地StationXML。

## 4. 必须逐事件保留的质量字段
以下是本项目建议的准入检查，不是已完成的测量结果。
1. **时间**：ATT 与名义采样时间的偏差、重采样方式、事件UTC、窗口前600 s至后3600 s。地面接收时间和月面采样时间存在传播延迟，跨站精确到时需统一时间定义。不要重复修正新档案已含的分量时序偏移。
2. **缺测**：原始记录以 -1 储存缺失值；SHZ正常遥测结构也有每32样点缺3样点。先标缺失再处理响应。只允许可解释的短缺口修复；长缺口截窗或排除，不能整体填零后计算尾波。
3. **偏置与脉冲**：移除均值/趋势；保存偏置跳变、孤立spike、校准脉冲和增益切换标记。DU原始量化范围0–1023；接近端点的连续平台需检查饱和。**当前未以原始DU对本批每道完成饱和认证**，不能宣称无饱和。
4. **增益**：StationXML响应是名义值；命令1/2分别切换LP水平/LPZ增益，命令3/4是SP/LP校准，5为SP增益，13为feedback filter。日志须检查MAP和date_error/data_error。仅看到命令号不能单独确定绝对增益；需追溯初态与成功命令序列。
5. **频带SNR**：分别对事件前噪声、早期增长段、尾波段计算PSD/带内RMS比；候选子带0.1–0.3、0.3–0.5、0.5–0.9、0.9–1.5 Hz。建议先按功率比≥9（振幅RMS比≥3）作保守筛查，并报告阈值敏感性。该阈值是项目选择，不是Nunn原文给定。
6. **可用等级**：A=完整且响应/时钟/SNR通过；B=可比较部分组件或时窗；C=有记录但SNR不足；X=缺失或坏道。三分量能量目标函数只接受三道共同合格窗口；S14坏Z不得补零。
7. **旧DARTS与新档案分开**：旧SAC即使header写IVEL也必须核对处理历史；**不可直接给已校正速度再次套新StationXML去卷积**。新档案raw DU可从头统一处理；两种来源先比较波形/时间，不强行比较绝对幅值。

## 5. 本次已取得的元数据与限制
保存位置：`data/raw/impact_metadata/`。
- `stationxml.xa.0.sxml`：PDS原始StationXML，181458字节；`stationxml.xa.0.xml`为PDS4标签（不是第二份响应）。
- `channel_epochs.csv`：从StationXML提取的37个通道/响应条目，包括S11和四主站。
- `apollo_pse_description.pdf`：PDS SIS全文。
- `getting_started.ipynb`：作者公开处理示例。
- `cvtfp_12/14/15/16.csv`与`cvtfw_12/14/15/16.csv`及`cvtf.README`：PSE tapes/work tapes命令校准日志，已下载；逐事件绝对增益重建仍未完成。
- `instrument_metadata_download_log.json`及`instrument_calibration_download_log.json`：下载URL、字节数及SHA-256。

**特别提醒：StationXML中00/01两个模式均有覆盖整个任务的epoch，且还保留失效S12 SHZ、S14坏Z的名义响应条目。因此 metadata epoch 仅表示响应描述有效区间，不能当作运行日志或记录存在证据。**

原始StationXML：[PDS元数据](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/data/xa/metadata/stationxml.xa.0.sxml)。
本轮尚未由新档案每条事件波形推导一个“最终有效滤波频带”；应在波形审计表中将文献建议和实际SNR结果分列，避免把候选值伪装成实测结论。


## 6. 现代档案波形交叉核验（本轮新增，已执行）
在上述仪器审计后，进一步从 EarthScope FDSN 新档案下载了9次撞击的**全部21个文献记录配对**，每对请求 MH1、MH2、MHZ、ATT，窗口为NASA Earth-received撞击时刻前600 s至后3600 s。21个请求全部成功；63个候选MP分量中，3条S14坏Z明确排除，**60条分量生成了名义响应校正预览**。这不等于60条均通过反演质控。

原始endpoint为 `https://service.earthscope.org/fdsnws/dataselect/1/query`；精确参数、文件SHA-256见 `results/impact_modern_download_log.json`。可复现脚本：`code/audit_modern_impact_records.py`。原始miniSEED：`data/raw/impact_modern/`。处理后：`data/processed/impact_reference/`。

NPZ字段：
- `t`：相对于NASA Earth-received撞击起时的秒数；未擅自减1.3 s月地传播时间。
- `velocity_m_s`：PDS名义响应校正速度；**不是完整增益重建后的绝对幅值认证**。
- `raw_counts`、`original_gap_mask`：原始DU和原始缺测标记；缺口在速度数组中保留NaN。
- `metadataJSON`：location、仪器响应、时间处理、缺口、可能削顶及噪声量化限制。

时间处理用事件窗内ATT作稳健局部仿射拟合，保留原始各分量在头信息中的采样时序；60条均有可用ATT并通过残差99分位<0.05 s检查。1969年A12 LM的合法负Unix时间已保留，未再误判为缺失；缺失sentinel与时间不连续另行筛除。该局部方法不代替全天复杂时钟异常的完整恢复。两条参考MHZ：A14 SIVB的事件时刻ATT偏移约−1.147 s，残差99分位0.0241 s；A16 SIVB偏移约−0.0579 s，残差99分位0.0010 s。

响应处理：去趋势/均值，预滤波 [0.05,0.1,1.5,2.0] Hz，输出VEL、无water-level。≤2样点缺口只临时插值供处理，最终恢复NaN；更长缺口分段去响应，各有效段端部另去10 s以避免边缘影响。保留标称响应的采样参数，将ATT修正反映在时间轴；该近似需在精细相位拟合前进一步验证。

**初筛输出，绝不冒充最终通带：**
- `results/impact_modern_trace_audit.csv`：63行，含坏道排除、gap、possible_clipping、ATT状态、量化限制及预览路径。
- `results/impact_modern_band_screen.csv`：60道×4频带=240行；`published_supported_band`、`provisional_record_screen`、`qualified_band`三列分开。
- 分析子带0.1–0.3、0.3–0.5、0.5–0.9、0.9–1.5 Hz。前噪声窗−500至−50 s；事件窗max(50 s,震中距/8 km/s)至1800 s。本窗只检验增长段与较早尾波，不证明1800–3600 s仍有效。
- 暂定通过条件：RMS信号/噪声≥3且带内≥60% PSD频点的功率比≥9；噪声与信号有效样点比例≥95%；ATT校时通过；未触发粗量化或连续≥3样点触及量化轨顶/底的可疑削顶标记。
- 240个trace-band组合中30个满足这一保守初筛。**26条分量的前噪声粗量化**，并不据此判定原始前噪声是填充；只标记noise_quantization_limited，使SNR不被当成可靠认证。文献显示清晰的事件也可能因此不通过本次自动筛查。
- 当前 `qualified_band` 留空：名义增益和初筛不能代替人工检查、绝对增益序列复核及晚时信噪比审核。已完成的是“可追溯记录+候选频带量化初筛”。
- 参考波形QA图 `reports/impact_modern_reference_QA.png` 已检查。A14 SIVB→S12 MHZ有缺口及最长3样点触及量化边界的可疑削顶；A16 SIVB→S12 MHZ的窗内完整性更好。两条波形均清晰，但前噪声量化限制仍须保留。

