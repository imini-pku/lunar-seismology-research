# REL3完整分析交付包

## 直接阅读

- `document/REL3月震四模型_完整综合报告_证据分级终审版.docx`：包含全部方法、29条保留图证条目、证据分级、路径分析、地形/散射三分量变化、低速层、td/Qc、文献方法应用和审稿修改。
- `document/REL3月震四模型_完整综合报告_证据分级终审版.md`：按正向、反向/排除和证据不足三类组织的图文索引。
- `document/REL3月震四模型_完整综合报告_证据分级终审版.pdf`：已渲染并逐页验收的PDF预览版。


## 一键复现

```powershell
python run_complete_analysis.py --check-only
python run_complete_analysis.py
```

安装依赖：`pip install -r requirements-complete-analysis.txt`。

脚本保留原始数据绝对路径；如数据移动，请修改 `plot_releasy_waveform_comparison.py` 顶部的 `MODELS`、`OBSERVED_COMPONENT_FILES` 和 `TOPOGRAPHY_FILE`。

## 目录

- `figures/conclusion_cards`：29条保留波形证据图。
- `figures/key`：S12、三条路径、因子差分/交互项、时变偏振、时频对比、P-SV-SH和低速层等主图。
- `tables`：全部关键CSV结果，包括606台站指标。
- `reports_source`：29项证据图册中文索引。历史阶段报告未纳入终审包，避免其旧编号和候选机制与本版证据分级冲突。
