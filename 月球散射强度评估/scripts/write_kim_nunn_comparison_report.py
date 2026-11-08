from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
z=zipfile.ZipFile(root/'data/raw/published_waveform_sources/Nunn2024_impact_simulations_v1.0.0.zip')
n=next(n for n in z.namelist() if n.endswith('/postprocessing_util.py'))
lines=z.read(n).decode().splitlines()
evidence='\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines) if any(k in line for k in ['original_mask = linear_interpolation','output="VEL"','output="DISP"','np.square(tr_decay','water_level=None','Qc_after_tmax','Qc_length']))
(root/'figures/kim_nunn_comparison_20261103/nunn_archived_code_evidence.txt').write_text(n+'\n'+evidence,encoding='utf-8')
text='''# Kim 2026 与 Nunn 2024：波形对照和处理选择

日期：2026-11-03。范围限于目前已取得的 Apollo 人工撞击记录；不把结论推广到所有自然月震。

## 结论先行

**针对本项目的散射模拟和长尾波约束，Nunn 2024 的分析框架更合适；针对早到 P 波偏振与单台站定位，Kim 2026 的框架更合适。当前没有证据将 Kim 的公开数组评为更彻底的清洗成品，也不能把 Nunn 原始输入称为已经清洗好的波形。**

推荐以 Nunn 所用的可追溯归档数据和响应资料为主输入，以其物理量转换、长时段包络和衰减测量作为参考流程；Kim 数组用于交叉核对和早到偏振方法参考。最终仍需按事件、台站、分量分别检查缺样、仪器模式与异常，不能机械套用整条流程。

## 1. 这次图中比较的是什么

左列：Nunn 作者仓库 `input_files/local_MSEED` 中的归档数字计数；右列：Kim 发布的 `_uniform.mat` 中的 10 Hz 数组。两列均不是新运行论文全流程的结果。

- 不新增带通、去均值、去趋势、归一化、幅值拟合、极性翻转或重采样。
- Nunn 的 −1 是缺样码，绘图时以 NaN 断线显示；真正的数值 0 保留。此举只是正确显示缺样，不是插值或异常清洗。
- 同一分量的左右面板使用相同纵轴范围，不通过不同纵轴缩放制造“更干净”的视觉效果。
- Nunn 时间轴使用项目目录的地球接收撞击时间；Kim 使用作者存储的相对时间。没有为使曲线重合而人工平移；Kim 的 UTC 原点尚未独立解码。因此不报告逐点残差、时间精度或相似性评分。
- MH1/N、MH2/E 是名义对应，Kim 上游通道映射尚未全部核实。三分量共同出现不等于全部可用于偏振或能量计算。

[五页对比 PDF](../figures/kim_nunn_comparison_20261103/Kim2026_vs_Nunn2024_五组对比.pdf)；[窗口与缺样统计](../figures/kim_nunn_comparison_20261103/comparison_windows.csv)；[绘图处理声明](../figures/kim_nunn_comparison_20261103/provenance.json)。

## 2. 实际波形告诉我们什么

### A13 S-IVB—S12：近零平台并非 Kim 独有

两套输入的三分量都保留明显的近零平台和大幅振动。因此不能说 Kim 造成了这段异常，也不能说 Kim 已把它修复。平台具体成因需要独立仪器与遥测证据，不凭图判断为饱和、重置或缺样。

在 −60 至 600 s 的 Nunn 原输入中，MHZ/MH1/MH2 分别有 75/80/77 个 −1 缺样码，图中按断线显示。Kim 文件没有对应的原缺样掩码，不能把数组连续性当成有效观测完整性。

![A13 S-IVB S12 早段对比](../figures/kim_nunn_comparison_20261103/01_A13SIVB_S12_early.png)

![A13 S-IVB S12 平台局部对比](../figures/kim_nunn_comparison_20261103/02_A13SIVB_S12_plateau.png)

### A14 S-IVB—S12：长尾波整体形态对照

在共同时间范围直接比较两个版本的尾波与振幅变化。由于采样网格不同且未做精确时钟核验，只用于形态核对，不据此声称波形逐点等价或处理质量相同。

![A14 S-IVB S12 尾波对比](../figures/kim_nunn_comparison_20261103/03_A14SIVB_S12_coda.png)

### A14 LM—S14：检查复杂波形，不能仅看曲线平滑程度

保留三分量存储数值中的突变和振动，不人为删除。是否需要修复、修复到什么程度，要依据仪器异常记录和已发表的适用方法，不能仅凭带通后的外观决定。

![A14 LM S14 尾波对比](../figures/kim_nunn_comparison_20261103/04_A14LM_S14_coda.png)

### A17 LM—S14：数组存在不等于原通道已恢复

左侧缺 MHZ，右侧有 Z，但目前没有其原始通道身份和有效性证据。对比图明确留空左上面板，不以短周期、水平分量或模拟值补齐。不能把右侧文件的存在当成 Kim 修复了垂直通道的证据。

![A17 LM S14 通道覆盖对比](../figures/kim_nunn_comparison_20261103/05_A17LM_S14_missingZ.png)

## 3. 论文处理框架的差别

| 项目 | Nunn 2024 | Kim 2026 | 对本项目的意义 |
|---|---|---|---|
| 主要任务 | 三维传播、散射与较长时间包络比较 | 早到 P 波偏振及单台站定位 | Nunn 与尾波散射目标更接近 |
| 可追溯输入 | MiniSEED、通道编码、台站响应及处理函数 | 10 Hz 的 MAT 数组、偏振结果和示例脚本 | Nunn 更便于追踪仪器通道与缺样；Kim 上游处理链待补 |
| 物理量转换 | 公开处理代码按分支去响应为位移或速度 | 当前 MAT 与示例以 DU 表示，未提供完整去响应链 | 定量比较模拟与观测不能混用 DU 和 m/s |
| 频带 | 定量尾波采用 0.4–0.5 Hz，另有多频段比较 | 论文主分析 0.2–0.95 Hz | 频带不同服务于不同目标，不是越宽或越窄越合理 |
| 分析时段 | 长时段包络、峰值时刻及衰减窗 | 论文围绕 P 到达采用 30 s 分析窗 | 短 P 窗不能替代长尾波约束；Kim 存储数组本身多数更长 |
| 缺样处理 | 代码有有限插值；去响应时临时插值并恢复掩码 | MAT 数组没有显式原缺样掩码，生成细节待核实 | 保留缺样溯源更有利于避免把填补数据计入尾波能量 |
| 后续指标 | 包络上升与衰减；拟合分支使用平方包络 | 时频偏振、方位角、倾角、信噪比 | 散射反演主指标优先前者，偏振可作为补充 |
| 完整异常清洗 | 不等于系统修复所有跳变与削顶 | 也没有证据显示已系统修复全部异常 | 两者都不能整包无条件准入 |

Nunn 的主定量流程把速度波形限制到 0.4–0.5 Hz，平滑包络，测量相对源时刻的峰值时间，再从峰后 300 s 开始取 1500 s 衰减窗。Kim 论文 §2 的任务是在早到 P 波窗口内估计偏振方向。以上是方法适用性比较，本轮没有执行这些滤波与分析步骤。[Nunn 论文](https://doi.org/10.3847/PSJ/ad83d2)、[Kim 论文](https://doi.org/10.1029/2026GL122962)

## 4. Nunn 的流程也需要有条件采用

1. 去响应所需的临时长缺口插值可能影响邻近输出；恢复掩码不能自动保证缺口邻域无影响。
2. 展示用归一化会改变跨事件的绝对幅值关系，不能直接拿归一化曲线做绝对能量反演。
3. 平滑会改变包络细节，应检查对峰值时间和衰减的敏感性。论文周期数与代码平滑窗口定义也须统一。
4. 本项目不应只依赖一个窄频带约束相关长度、扰动强度和深度；多频带设计应在仪器响应和记录质量审核后确定。
5. 作者方法是可复现起点，不是无需检查即可应用的异常清洗保证。

## 5. 建议采用的分工

**主数据入口：Nunn 可追溯的归档输入。主分析框架：Nunn 的长尾波与物理量转换思路。辅助数据：Kim 原样保存的重采样数组。辅助指标：Kim 的早到偏振方法。异常处理：另按每条记录识别的问题选用已发表方法，保留原值、掩码和处理日志。**

这一建议基于本项目目标与当前公开文件证据，不是两篇论文总体质量的排名，也不是在已经统一频带、物理单位和时间基准后得出的数值性能评测。

## 参考与证据

- Nunn et al. (2024), Artificial Impacts on the Moon: Modeling 3D Seismic Propagation Effects with AxiSEM3D. [论文](https://doi.org/10.3847/PSJ/ad83d2)；[发表代码归档](https://doi.org/10.5281/zenodo.13821562)。
- Kim, Song & Schmerr (2026), Locating Moonquakes With Single-Station Seismology. [论文](https://doi.org/10.1029/2026GL122962)；[数据包](https://doi.org/10.6084/m9.figshare.32814290)。
- [Nunn 归档代码相关行摘录](../figures/kim_nunn_comparison_20261103/nunn_archived_code_evidence.txt)。
- [Kim 实际数组核验报告](18_Kim2026数据包实际核验_20261103.md)。
'''
p=root/'docs/20_Kim2026与Nunn2024波形及方法对比_20261103.md';p.write_text(text,encoding='utf-8');print(p)
