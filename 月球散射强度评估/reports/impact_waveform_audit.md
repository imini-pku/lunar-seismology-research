# 人工撞击 SAC 实际下载与组件审计

审计日期：2026-10-29。数据来自 JAXA DARTS 的 UT Austin 人工撞击事件 SAC 镜像。

已下载 **81 个压缩文件**并解压核验为 81 个 SAC；包含 **9 个事件、21 个事件—台站组合、63 条 LP 和 18 条 SP**。这里只认实际文件，台站运行日期未被当作记录存在的证明。

## 下载覆盖

| 撞击事件 | 有档案记录的台站 | LP 文件数 | SP 文件数 |
|---|---|---:|---:|
| A12LM | S12 | 3 | 1 |
| A13SIVB | S12 | 3 | 1 |
| A14SIVB | S12 | 3 | 1 |
| A14LM | S12, S14 | 6 | 2 |
| A15SIVB | S12, S14 | 6 | 2 |
| A15LM | S12, S14, S15 | 9 | 3 |
| A16SIVB | S12, S14, S15 | 9 | 2 |
| A17SIVB | S12, S14, S15, S16 | 12 | 3 |
| A17LM | S12, S14, S15, S16 | 12 | 3 |

## 事件—台站具体记录

| 事件 | 台站 | 实际分量 | LP 时长/min | 分量级频谱初筛前置条件通过数 |
|---|---|---|---:|---:|
| A12LM | S12 | LPX;LPY;LPZ;SPZ | 198.3–198.3 | 0/3 |
| A13SIVB | S12 | LPX;LPY;LPZ;SPZ | 195.6–195.6 | 0/3 |
| A14SIVB | S12 | LPX;LPY;LPZ;SPZ | 198.3–198.3 | 0/3 |
| A14LM | S12 | LPX;LPY;LPZ;SPZ | 198.3–198.3 | 0/3 |
| A14LM | S14 | LPX;LPY;LPZ;SPZ | 195.6–195.6 | 0/3 |
| A15SIVB | S12 | LPX;LPY;LPZ;SPZ | 195.6–195.6 | 0/3 |
| A15SIVB | S14 | LPX;LPY;LPZ;SPZ | 198.3–198.3 | 0/3 |
| A15LM | S12 | LPX;LPY;LPZ;SPZ | 198.3–198.3 | 0/3 |
| A15LM | S14 | LPX;LPY;LPZ;SPZ | 195.6–195.6 | 0/3 |
| A15LM | S15 | LPX;LPY;LPZ;SPZ | 195.6–195.6 | 1/3 |
| A16SIVB | S12 | LPX;LPY;LPZ | 190.2–190.2 | 0/3 |
| A16SIVB | S14 | LPX;LPY;LPZ;SPZ | 187.5–187.5 | 1/3 |
| A16SIVB | S15 | LPX;LPY;LPZ;SPZ | 187.5–187.5 | 0/3 |
| A17SIVB | S12 | LPX;LPY;LPZ | 130.4–130.4 | 0/3 |
| A17SIVB | S14 | LPX;LPY;LPZ;SPZ | 127.7–127.7 | 0/3 |
| A17SIVB | S15 | LPX;LPY;LPZ;SPZ | 127.7–127.7 | 0/3 |
| A17SIVB | S16 | LPX;LPY;LPZ;SPZ | 127.7–127.7 | 0/3 |
| A17LM | S12 | LPX;LPY;LPZ | 266.3–266.3 | 0/3 |
| A17LM | S14 | LPX;LPY;LPZ;SPZ | 269.0–269.0 | 0/3 |
| A17LM | S15 | LPX;LPY;LPZ;SPZ | 269.0–269.0 | 0/3 |
| A17LM | S16 | LPX;LPY;LPZ;SPZ | 269.0–269.0 | 0/3 |

## 文件级检查和限制

- 压缩原件、解压 SAC 均保留；每个文件 URL、大小、SHA256、起止时刻、SAC 震源标记、台站与分量、采样率、点数、头坐标及质量指标写入 `results/impact_waveform_inventory.csv`。
- 全部文件满足 632 字节 SAC 头 + 4×NPTS 的长度关系；全部使用大端格式。非有限值总数：0。无 NaN 不代表无丢失：档案可能采用恒值、保持上一数值或其他填补方式。
- 实测 DELTA 对应 LP 约 6.625259 Hz、SP 约 53.002061 Hz；与标称 6.625/53 Hz 略有区别，原头字段照录，未擅自重采样。
- SAC IDEP 在本集内有 42 条值为 6、39 条值为 7，分别指 IDISP/IVEL。由于完整处理历史、校准增益与单位未核实，图中统一称“档案振幅”，不将其视为已验证的位移/速度，也不直接用新 StationXML 再次去响应。
- 时间零点使用各文件 SAC 的 O 字段；推得 A13SIVB 为 1970-04-15，与 JAXA 说明表中的 April 5 不一致。该表存在日期冲突，应由 NASA 主目录核定。原时间字段没有改写，也未擅自实施约 1.3 s 的 Earth-received / Moon-origin 校正。
- SAC 头的事件坐标只作为原档案证据保留。新版地图与震中距应使用经 NASA 校核的坐标，尤其 A16SIVB，不应覆盖旧 SAC 的原头。

## 明确的质量问题

- S12 SP 通道在任务期间低增益/失效；虽然 6 个事件各有 SP 文件，不能用作有效短周期记录。
- A16SIVB→S14 LPZ 仅 6 个离散振幅值，A17SIVB→S14 LPZ 仅 3 个，A17LM→S14 LPZ 仅 20 个；与已知 S14 MHZ 故障时期一致，排除物理拟合。某故障记录仍可能产生很高频谱比值，故障判定优先。
- A15SIVB→S14 LPY 在事件后约 143–157 s 出现同一全局极值持续约 13.6 s；A17SIVB→S14 LPY 在约 222–242 s 持续约 20.1 s。需排查饱和/阶跃，不可直接拿此段标定包络峰值。
- 多数记录末端有数十至数百秒恒值段。已分别统计全记录和 -600～3600 s 分析窗，避免末端填补自动导致整条早期记录被判无效。
- 事件前噪声常处于粗量化状态。例：A14SIVB→S12 LPZ 的 -600～-60 s 前窗仅 4 个值，众数比例约 82.9%，MAD=0，并有大尖峰；A16SIVB→S12 LPZ 前窗仅 3 个值、众数约 78.3%、MAD=0。这些窗不能自动认证有效频带。

## 频带初筛方法与解释

预备显示滤波统一采用四阶 Butterworth 0.3–0.9 Hz，前后向零相位滤波，先线性去趋势。每条图迹按自己的峰值归一化；因此图用于记录形态与异常检查，不可比较台站间绝对振幅。完整未滤波图另存。

频谱初筛使用 Welch PSD：噪声窗 -600～-60 s，信号窗 +60～+1800 s；比较 PSD(signal+noise)/PSD(noise)，对子带 0.1–0.3、0.3–0.5、0.5–0.9、0.9–1.5、1.5–2.0 Hz 保存中位频谱比和比值≥3 的频点比例。原始阈值为中位比≥3且至少60%频点≥3。

另设保守的本项目自动筛查前置条件：前窗至少 8 个独特值、众数比例<50%、MAD>0、无≥5 s完全恒值段、峰值偏离≤20×1.4826 MAD；且非已知故障/低增益通道，分析窗无≥1 s重复全局极值。它们是本轮质量警报规则，不是公认的物理有效带判据，也不证明所有被警报记录都毫无科学价值。

81 条档案中，5 条满足本轮自动频谱初筛前置条件。未满足者保留比值但 `screen_usable=false`、`spectral_screen_pass=false`；`raw_threshold_pass` 只记录数值阈值，不能当通过。所有 `physical_band_validated=false`，因为本轮未完成事件时期响应校正及新档案交叉验证。

## 文件清单

- `data/raw/impact_waveforms_darts/`：81 个压缩原件、81 个解压 SAC 和官方目录页面。
- `results/impact_waveform_inventory.csv`：81 行文件级详细审计。
- `results/impact_event_station_download_summary.csv`：21 行事件—台站覆盖摘要。
- `results/impact_waveform_spectral_screen.csv`：405 行分量×子带初筛结果。
- `figures/impact_audit/*_record_overview.png`：9 张事件全分量原始归一化概览。
- `figures/impact_audit/*_LP_filtered_0p3_0p9Hz.png`：9 张事件 LP 滤波概览，含全部 63 条 LP，故障分量仍显示并标注。
- `figures/impact_audit/downloaded_record_coverage.png`：按实际文件统计的 9×4 台站覆盖。
- 复现：系统需 numpy/scipy/matplotlib/requests；仅 Unix compress 解压依赖 unlzw3 安装到项目 `.build/waveform_dependencies`，没有改变系统包。运行 `python code/audit_impact_waveforms_darts.py` 可重算本地审计。

## 主要资料

- [JAXA DARTS Artificial Impact Event Data](https://darts.isas.jaxa.jp/en/datasets/darts:apollo-ai-data/)
- [JAXA 原始 SAC 分发目录](https://data.darts.isas.jaxa.jp/pub/apollo/ai/sacs/)
- [Yamada: The Description of Apollo Seismic Experiments](https://darts.isas.jaxa.jp/missions/apollo/The_Description_of_Apollo_Seismic_Experiments.pdf)
- [Yamada: The Apollo Seismometer Responses](https://darts.isas.jaxa.jp/missions/apollo/The_Apollo_Seismometer_Responses.pdf)
- [SAC 官方格式说明](https://ds.iris.edu/files/sac-manual/manual/file_format.html)
- [Nunn et al. (2022): 新 Apollo PSE 档案与通道故障处理](https://doi.org/10.3847/PSJ/ac87af)

## PPT 代表记录图补充

另生成 9 张 `figures/impact_audit/{event_id}_representative_records.png`，每事件含全部有档案记录的台站，共 21 道代表记录。优先显示 LPZ；1972 年 S14 坏 Z 改为 LPX。按 `results/impact_pairs_literature.csv` 标注 Nunn et al. (2024) 的 5 条低 SNR 路径，并未按本轮保守自动频谱条件删除路径。时间窗 -300～3600 s，四阶 0.3–0.9 Hz 前后向滤波，逐道峰值归一化。图中醒目标明旧档案、未去响应与非认证有效频带。9 张均已逐张视觉检查。复现入口为 `code/plot_impact_representative_records.py`。

本报告完成实际记录下载与初步审计；未将文件存在、频谱阈值通过或统一显示滤波等同于正式可反演记录。
