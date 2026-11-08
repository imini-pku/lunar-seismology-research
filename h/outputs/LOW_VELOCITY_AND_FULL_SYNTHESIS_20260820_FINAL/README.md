# 低速层与全模型综合分析最终交付包

生成日期：2026-08-20  
正式项目：`h/jgr_planets_submission/`

## 交付内容

- `documents/`：低速层专题报告和全模型综合报告的 DOCX、PDF、Markdown 正式版本。
- `figures/`：24 幅低速层证据图、1 幅独立 S12 三分量对比图、4 幅综合直接证据图，以及综合报告引用的半空间、A16 主图和补充图。
- `figures/low_velocity/Figure_S12_M1_M6_observed_three_component.png`：M1-M6 与 Apollo S12 观测的 Z/R/T 独立对比图。
- `figures/low_velocity/Figure_S12_M1_M6_observed_envelope_comparison.png`：20 s 平滑三分量包络线对比图。
- `figures/low_velocity/Figure_S12_M1_M6_observed_energy_comparison.png`：绝对累计能量和逐记录归一化累计能量对比图。
- `figures/low_velocity/Figure_S12_M1_M6_observed_component_envelopes.png`：分别展示 Z、R、T 三个分量的 20 s 平滑解析振幅包络。
- `figures/low_velocity/Figure_S12_M1_M6_observed_component_envelope_correlations.png`：Z/R/T 包络的零时滞和 ±10 s 最佳时滞相关系数图。
- `data_derived/`：报告所用的全部派生 CSV/JSON 结果。
- `data_derived/s12_m1_m6_observed_scaling.csv`：该独立图使用的 50–245 s 三分量 RMS 缩放因子。
- `data_derived/s12_m1_m6_observed_envelope_energy_summary.csv`：包络峰值和累计能量摘要指标。
- `data_derived/s12_m1_m6_observed_component_envelope_summary.csv`：Z/R/T 分量包络峰值时间摘要。
- `data_derived/s12_m1_m6_observed_component_envelope_correlations.csv`：Z/R/T 包络相关系数及最佳时滞记录。
- `code/`：半空间、低速层、图件和报告生成脚本；不含 Python 缓存文件。
- `provenance/`：输入审计、校验和、结论—证据索引和运行信息边界。
- `config/`：统一数据路径目录和路径配置示例。
- `project_records/`：h 项目的归档索引和项目说明。
- `MANIFEST_SHA256.csv`：本交付包内全部正式文件的字节数与 SHA-256。

## 规模与证据覆盖

- 低速层专题报告：33 页，24 个结论—图片证据单元，24 幅独立图。
- 全模型综合报告：91 页，76 个结论—图片证据单元，46 幅独立图；同一综合图仅在直接支持相互关联的结论时复用。
- 合计：100 个结论—图片证据单元，内容规模超过旧 REL3 29 个证据卡的三倍。

## 原始数据位置

为避免重复收录大体积数据，本包不复制原始 NetCDF。M5/M6 正式原始副本仍保存在：

- `h/jgr_planets_submission/data/raw/M5_flat_heterogeneity_low_velocity_station.nc`
- `h/jgr_planets_submission/data/raw/M6_topography_heterogeneity_low_velocity_station.nc`

其源路径、文件大小和 SHA-256 见 `config/data_catalog.json`、`provenance/LOW_VELOCITY_DATA_AUDIT.md` 和 `provenance/low_velocity_input_audit.csv`。

## 解释边界

1. M5/M6 缺少完整运行清单，因此不能从 `station.nc` 反推或宣称低速层厚度、速度、密度、Q、网格、震源或随机种子。
2. 低速层记录约 400 s，尾端仍存在右删失；报告把 50–245 s 公共窗与 50–395 s 延长窗严格分开。
3. 当前没有“低速层 + 无散射”单元，不能估计完整的地形 × 散射 × 低速层三因素交互。
4. 绝对峰值和能量比值以震源及其他运行条件一致为前提；时间、分量占比和波形形状结论更稳健。
