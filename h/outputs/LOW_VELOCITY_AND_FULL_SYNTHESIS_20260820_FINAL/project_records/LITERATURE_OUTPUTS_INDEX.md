# h 项目文献与报告输出索引

本项目的文稿、审稿材料、分析报告及其可复用附件，统一归档在：

`h/jgr_planets_submission/`

不得把临时渲染目录、外部盘符或聊天附件作为唯一保存位置。新生成或更新的文献类产物必须在 `h` 项目内保留正式副本；Word/PDF 交付件同时保留可编辑源文件或生成脚本。

## 当前正式文献产物

### 当前稿件

- `jgr_planets_submission/manuscript/manuscript.md`
- `jgr_planets_submission/manuscript/Wu_et_al_JGR_Planets_manuscript.docx`
- `jgr_planets_submission/manuscript/Wu_et_al_JGR_Planets_manuscript.pdf`

### Supporting Information

- `jgr_planets_submission/supporting_information/supporting_information.md`
- `jgr_planets_submission/supporting_information/Wu_et_al_JGR_Planets_supporting_information.docx`
- `jgr_planets_submission/supporting_information/Wu_et_al_JGR_Planets_supporting_information.pdf`

### 半空间数据分析与交叉核对

- `jgr_planets_submission/reports/半空间区域数据分析与交叉核对报告.md`
- `jgr_planets_submission/reports/半空间区域数据分析与交叉核对报告_真实800台站几何修订.docx`（当前正式版）
- `jgr_planets_submission/reports/半空间区域数据分析与交叉核对报告_真实800台站几何修订.pdf`（当前正式版）
- 无“真实800台站几何修订”后缀的 DOCX/PDF 为几何修正前的历史版本，不再用于正文结论。
- `jgr_planets_submission/reports/论文结构与结论_真实800台站几何修订.md`
- 数据图：`jgr_planets_submission/figures/halfspace/Figure_HS1` 至 `Figure_HS9`
- 派生表：`jgr_planets_submission/data/derived/halfspace_*`
- 输入审计：`jgr_planets_submission/provenance/halfspace_input_audit.csv`
- 路径目录：`jgr_planets_submission/config/data_catalog.json`

### 低速层与全模型综合分析（2026-08-20 终审版）

- `jgr_planets_submission/reports/低速层模型详细数据分析报告_REL3标准_证据分级终审版.md`
- `jgr_planets_submission/reports/低速层模型详细数据分析报告_REL3标准_证据分级终审版.docx`（33 页）
- `jgr_planets_submission/reports/低速层模型详细数据分析报告_REL3标准_证据分级终审版.pdf`（33 页）
- `jgr_planets_submission/reports/月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版.md`
- `jgr_planets_submission/reports/月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版.docx`（91 页）
- `jgr_planets_submission/reports/月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版.pdf`（91 页）
- 低速层图件：`jgr_planets_submission/figures/low_velocity/Figure_LV01` 至 `Figure_LV24`
- 综合直接证据图：`jgr_planets_submission/figures/synthesis/`
- 派生结果：`jgr_planets_submission/data/derived/low_velocity_*` 及 `direct_evidence_*`
- 输入审计：`jgr_planets_submission/provenance/LOW_VELOCITY_DATA_AUDIT.md`、`low_velocity_input_audit.csv`
- 可复现脚本：`jgr_planets_submission/code/analyze_low_velocity_models.py`、`build_low_velocity_and_integrated_reports.py`、`generate_direct_evidence_figures.py`
- 独立 S12 三分量对比图：`jgr_planets_submission/figures/low_velocity/Figure_S12_M1_M6_observed_three_component.png`
- 独立 S12 包络线对比图：`jgr_planets_submission/figures/low_velocity/Figure_S12_M1_M6_observed_envelope_comparison.png`
- 独立 S12 累计能量对比图：`jgr_planets_submission/figures/low_velocity/Figure_S12_M1_M6_observed_energy_comparison.png`
- 独立 S12 各分量包络线对比图：`jgr_planets_submission/figures/low_velocity/Figure_S12_M1_M6_observed_component_envelopes.png`
- S12 各分量包络相关系数图：`jgr_planets_submission/figures/low_velocity/Figure_S12_M1_M6_observed_component_envelope_correlations.png`
- 对比图缩放记录：`jgr_planets_submission/data/derived/s12_m1_m6_observed_scaling.csv`
- 包络线与能量摘要：`jgr_planets_submission/data/derived/s12_m1_m6_observed_envelope_energy_summary.csv`
- 各分量包络线摘要：`jgr_planets_submission/data/derived/s12_m1_m6_observed_component_envelope_summary.csv`
- 各分量包络相关系数：`jgr_planets_submission/data/derived/s12_m1_m6_observed_component_envelope_correlations.csv`
- 完整交付包：`outputs/LOW_VELOCITY_AND_FULL_SYNTHESIS_20260820_FINAL/`
- M5/M6 原始 NetCDF 正式副本保留在 `jgr_planets_submission/data/raw/`，交付包通过目录和 SHA-256 清单引用，不重复收录大体积原始文件。

### 投稿材料

- `jgr_planets_submission/submission_materials/cover_letter.md`
- `jgr_planets_submission/submission_materials/cover_letter.docx`
- `jgr_planets_submission/submission_materials/cover_letter.pdf`
- 其余作者问询、投稿检查和仓储说明均位于 `submission_materials/`。

### 原稿和审稿记录

- 原稿及第一轮审稿回复的原始文件均位于 `jgr_planets_submission/source_archive/`。

## 后续归档规则

1. 文稿正文放入 `manuscript/`。
2. 补充材料放入 `supporting_information/`。
3. 专题分析、文献核对和数据解释报告放入 `reports/`。
4. 审稿回复和投稿信放入 `submission_materials/`；未经修改的历史原件放入 `source_archive/`。
5. 图件、派生数据、脚本和输入来源分别放入 `figures/`、`data/derived/`、`code/` 和 `provenance/`。
6. PDF、DOCX 等最终输出生成后，应从临时渲染目录复制到上述正式目录，并更新本索引。
