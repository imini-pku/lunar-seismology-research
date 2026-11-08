# 原始波形与分阶段处理对照数据

本目录为独立的新版本，包含 60 个实际返回的分量文件；未改写 `impact_reference` 中的旧结果。21 个事件—台站配对共应有 63 个三分量位置，A16SIVB、A17SIVB、A17LM 的 S14 MHZ 在下载档案中未返回，同时处于已知故障时段；不制造空数组替代观测。

## 数组与单位

| 字段 | 含义 |
|---|---|
| `raw_counts` | 与 MiniSEED 逐样点相同的原始数字计数 DU；`-1` 是缺样标记，不是振幅 |
| `original_gap_mask` | 原始缺样位置，绘图时掩蔽为 NaN |
| `t_nominal_s` | MiniSEED 原始名义时间减去 NASA 地面接收源时，单位 s |
| `t_ATT_s`、`t` | ATT 仿射校正后的相对时间，单位 s；二者相同；没有重采样或改变原始幅值 |
| `velocity_response` | 去趋势、名义响应校正后的速度 m/s，预滤波转角 0.05/0.1/1.5/2.0 Hz |
| `velocity_03_09` | 上述速度再经 0.3–0.9 Hz 带通，单位 m/s |
| `velocity_03_05` | 上述速度再经 0.3–0.5 Hz 带通，单位 m/s |
| `displacement_03_05_m` | 独立位移处理分支：输出 DISP，预滤波 0.1/0.3/0.9/1.1 Hz，再经 0.3–0.5 Hz 带通，单位 m |
| `processing_edge_mask` | 每个处理段两端 `max(20 s, 3% 段长)` 的暂定处理影响区；标记不等于有效性认证，其外也不保证可靠 |
| `short_segment_mask` | 原始样点存在，但连续可处理段不足 60 s，因此没有处理输出 |
| `processing_failed_mask` | 速度处理支路失败位置；本轮为零 |
| `displacement_failed_mask` | 位移处理支路失败位置；本轮为零，与速度支路独立 |
| `temporary_interpolation_mask` | 仅在计算内临时插值的至多两个缺样；所有最终波形仍恢复原始缺口 |
| `metadataJSON` | 来源哈希、时钟、响应参数、每段处理状态、文献参照与限制 |

## 方法边界

仅封闭的至多两个缺样临时线性插值，较长缺口用于断段；至少 60 s 的段进行处理。恢复插值位置为 NaN，并不能消除插值对附近处理样点的影响。未自动去尖峰、去毛刺或重建长缺口。

速度与位移分支均使用名义 StationXML、`water_level=None` 和本项目沿用的 3% taper。滤波实现为 SciPy `butter(N=4, btype='bandpass', output='sos')` 后接 `sosfiltfilt`；N=4 表示原型阶数，不是组合后带通及双向滤波的总阶数。响应按名义 6.625 Hz 元数据计算，带通按 ATT 校正后的有效采样率计算。

位移分支参考 [官方入门示例](https://github.com/cerinunn/pdart/blob/master/getting_started.ipynb) 和 [Nunn et al. 2024](https://doi.org/10.3847/PSJ/ad83d2) 的图 1 频带，**不是完整复现**：缺口与分段政策不同，没有做 25 s 包络平滑，3% taper 不能称为文献的精确取值。

所有原始缺口在处理输出中保持 NaN；不足 60 s 的短段也不输出处理结果。计算得到的边缘样点保留，以橙线显示，不能把减少的显示空白解释成新增可靠观测。速度与位移的绝对物理幅值仍需增益履历核验，不能直接进入定量散射反演。

## 重现与检查

项目根目录运行 `python code/build_waveform_stage_comparison.py`；`--process-only` 仅重算新目录，`--plot-only` 仅重绘；`--event A15LM` 限制绘图事件。

完整检查结果见 `results/waveform_comparison/` 下的 `summary.json`、`trace_stage_comparison.csv`、`segment_processing_log.json`、`numerical_validation.json` 和 `artifact_validation.json`。本轮 221 个段成功处理，106 个短段不处理，速度和位移分支失败数均为 0。
