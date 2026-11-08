# 处理后数据

将通过 QC 的事件–台站–频带–时间窗指标保存为 `metrics_long.csv`。字段规范见 [`../../config/metrics_long_schema.csv`](../../config/metrics_long_schema.csv)。

当前没有真实输入文件，因此不预置任何反演数字。请先运行 `python ../../code/validate_inputs.py`，确认字段和参考能量完整，再运行首轮拟合。
