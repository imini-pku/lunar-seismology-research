# 低速层模型详细数据分析报告（REL3标准证据分级终审版）

M5/M6 与 M1-M4、Apollo A16S12 的统一证据链

本报告含24个结论-图件证据单元。

## 统一处理与证据规则

- 原采样率去趋势与四阶0.3-0.9 Hz零相位滤波；
- t05/t50/t95/T90使用三分量滤波速度平方累计能量；
- A16逐站旋转到R/T；正值指标用对数比，时间/占比用差值；
- 575主站、57个非重叠10站块；带区间/检验的推断量基于相同块中位数，指定的旧四模型T90与分量占比为575站描述性中位数；
- M5/M6缺少完整运行清单，绝对幅能量只作条件性运行级对比。

## 第一部分｜输入、设计与 S12 直接波形

先确定文件可比性、可识别设计和 S12 的直接三分量响应。

### LV01 六模型结构可比，但记录长度不同，必须采用双窗口

**正向确定性证据：** M5/M6 可以与 M1-M4 进行同名台站、同分量的配对比较；记录长度差异不能通过简单截断后被忽略。

**定量依据：** 六个文件均包含 r1-r606、seq_no 0-605 和有限 Vx/Vy/Vz；M1-M4 约 250 s，M5/M6 约 400 s。公共效应窗口为 50-245 s，低速层延长诊断窗口为 50-395 s。

![LV01 六模型结构可比，但记录长度不同，必须采用双窗口](../figures/low_velocity/Figure_LV01_input_audit.png)

**科学解释：** 双窗口把两个问题分开：公共窗回答模型之间的可比边际效应，延长窗回答低速层运行内部的晚期演化和删失风险。

**适用边界：** NetCDF 不编码完整运行条件；结构一致只证明输出格式和台站序列可比，不证明源、网格、Q、边界和随机实现完全相同。

**建议英文表述：** The six outputs share the same receiver sequence, but unequal record lengths require a common 50-245 s comparison window and a separate 50-395 s low-velocity diagnostic window.

*输入审计与 SHA-256：provenance/low_velocity_input_audit.csv。*

### LV02 当前只能识别含非均匀背景下的地形×低速层条件设计

**反向/排除性证据：** M2/M4/M5/M6 形成一个所有单元均含随机非均匀性的条件 2×2 设计，而不是完整的地形×散射×低速层三因素设计。

**定量依据：** 可识别对比为 M5/M2、M6/M4、M4/M2、M6/M5 以及 (M6-M5)-(M4-M2)；缺少“低速层+无散射”两单元。

![LV02 当前只能识别含非均匀背景下的地形×低速层条件设计](../figures/low_velocity/Figure_LV02_identifiable_design.png)

**科学解释：** 因此可以检验低速层在两种表面背景中的运行级差异，也可以检验条件交互；不能估计低速层×散射或完整三阶交互。

**适用边界：** 随机实现/种子未保存，图中“均含非均匀性”不能进一步提升为“使用同一随机实现”。

**建议英文表述：** The available models identify a heterogeneity-present topography-by-low-velocity contrast, not a complete three-factor design.

*设计边界由现有六个 station.nc 与缺失运行清单共同决定。*

### LV03 低速层改变 S12 三分量相位结构，而非统一振幅缩放

**正向确定性证据：** 在共享三分量尺度下，M5 相对 M2、M6 相对 M4 的 Z/R/T 都出现新的相位、脉冲和持续振荡。

**定量依据：** 图中同一对比使用共享 3C 尺度，没有逐分量归一化；变化同时存在于 Z、R 和 T。

![LV03 低速层改变 S12 三分量相位结构，而非统一振幅缩放](../figures/low_velocity/Figure_LV03_s12_common_waveforms.png)

**科学解释：** 低速层运行改变能量储存、转换和出射过程；单一静态时移或振幅系数不能把基准波形变成低速层波形。

**适用边界：** 这是波形形状证据，不反演具体层厚、速度或界面形态。

**建议英文表述：** Shared-scale S12 waveforms show that the low-velocity runs alter phase structure on all three components rather than applying a scalar amplitude correction.

*波形先逐站旋转到 Z/R/T；无逐分量归一化。*

### LV04 S12 的大量低速层能量位于原 245 s 截点之后

**正向确定性证据：** M5/M6 在 245 s 后仍持续出现能量峰和累计能量增长，旧的四模型窗口会截掉关键低速层响应。

**定量依据：** S12 延长窗 t95 为 M5 368.22 s、M6 381.88 s；两者都接近 400 s 记录末端。

![LV04 S12 的大量低速层能量位于原 245 s 截点之后](../figures/low_velocity/Figure_LV04_s12_extended_energy.png)

**科学解释：** 延长记录使低速层能量滞留首次被直接看见，也解释了公共窗与延长窗持续时间指标的差异。

**适用边界：** 接近末端的 t95 仍可能被右删失；这些数值是当前记录内下限，不是完整尾波寿命。

**建议英文表述：** A substantial fraction of the S12 low-velocity response occurs after 245 s, and its t95 approaches the 400 s record limit.

*延长窗口仅用于 M5/M6 内部诊断。*

## 第二部分｜运行级能量、持续与三分量

量化低速层在两种表面背景中的总体与分射线效应。

### LV05 低速层运行的主效应是能量积累、持续时间增加和峰时延迟

**条件性运行级证据：** 两个表面背景中，低速层运行都显著增强累计能量并延迟包络演化；峰值放大较不均一。

**定量依据：** 平坦背景：空间块中位数 19.72 倍，95%区间 12.20-87.29 倍；站点级描述中位数 19.07 倍；空间块中位数 1.50 倍，95%区间 1.29-1.57 倍；站点级描述中位数 1.46 倍。地形背景：空间块中位数 12.04 倍，95%区间 6.72-65.61 倍；站点级描述中位数 11.59 倍；空间块中位数 1.41 倍，95%区间 1.25-1.57 倍；站点级描述中位数 1.39 倍。

![LV05 低速层运行的主效应是能量积累、持续时间增加和峰时延迟](../figures/low_velocity/Figure_LV05_low_effect_distributions.png)

**科学解释：** 能量因子远大于峰值因子，说明新增响应主要表现为长时间能量积累，而不是所有位置同步提高瞬时主峰。

**适用边界：** 绝对能量和振幅的因果归因以源与其余运行设置不变为前提；时间与分量占比结论更稳健。

**建议英文表述：** The low-velocity runs primarily enhance integrated energy and delay rather than producing a uniform peak-amplitude increase, conditional on unchanged run settings.

*小提琴为站点级分布；推断值与区间来自 57 个空间块中位数。*

### LV06 低速层响应具有显著射线路径差异

**正向确定性证据：** 三条剖面的能量、持续和峰时效应幅度明显不同，不能用一个全区常数概括低速层响应。

**定量依据：** 射线分组均去除首尾各 5 站后计算；每条射线的能量因子、T90 因子和 tmax 变化均呈不同中位值与四分位范围。

![LV06 低速层响应具有显著射线路径差异](../figures/low_velocity/Figure_LV06_low_effect_by_ray.png)

**科学解释：** 这说明低速层与传播方向、路径起伏、局部结构或边界几何耦合；路径差异是物理信号而非仅是总体离散。

**适用边界：** 现有三条单向剖面不足以把路径差异唯一归因于某一种界面或三维结构。

**建议英文表述：** Ray-specific effect distributions demonstrate that the low-velocity response is path dependent rather than a model-wide constant.

*分射线结果是描述性；跨全样本推断使用 57 个非重叠空间块。*

### LV07 低速层进一步把 Z 能量重新分配到 R/T

**正向确定性证据：** 从 M1 到 M6，复杂结构逐步降低 Z 占比并提高水平与横向能量，M5/M6 延续并强化这一趋势。

**定量依据：** M1-M4 的 Z/R/T 中位占比为 70.15/29.85/~0、54.58/24.69/20.45、56.37/27.63/16.13、48.92/27.28/23.43%；M5/M6 的当前值由统一脚本在相同公共窗重算。

![LV07 低速层进一步把 Z 能量重新分配到 R/T](../figures/low_velocity/Figure_LV07_component_fractions.png)

**科学解释：** 分量重分配是三维模式转换和多路径改变的重要证据；Z 下降不等价于能量吸收增强。

**适用边界：** Z/R/T 是台站坐标分量；严格 P/SV/SH 分离仍需要波场散度-旋度或阵列慢度。

**建议英文表述：** The low-velocity runs further redistribute energy from Z into horizontal and transverse motion, extending the three-dimensional conversion trend seen in M1-M4.

*占比按三分量平方速度能量计算，T 基准近零时不使用倍数。*

### LV08 T 分量转换依赖地表和低速背景

**正向确定性证据：** 低速层导致的 T 占比增量在平坦与地形背景中不同，地形的 T 边际效应也会因低速层背景而改变。

**定量依据：** M5/M2：空间块中位变化 10.43 个百分点，95%区间 7.47 至 15.43 个百分点；站点级描述中位数 10.89 个百分点；M6/M4：空间块中位变化 4.31 个百分点，95%区间 1.16 至 7.65 个百分点；站点级描述中位数 4.86 个百分点。

![LV08 T 分量转换依赖地表和低速背景](../figures/low_velocity/Figure_LV08_transverse_conversion.png)

**科学解释：** T 是对三维不对称、散射和地表转换最敏感的分量之一；背景依赖排除了固定转换率解释。

**适用边界：** T 只能作为 SH 代理，不能单凭单台站三分量唯一分解所有模式。

**建议英文表述：** Transverse-energy conversion depends on both the surface and low-velocity background, precluding a universal conversion factor.

*使用百分点差而非相对 M1 近零 T 能量的倍数。*

## 第三部分｜地形×低速层条件交互与路径控制

检验地形边际效应是否因低速背景改变。

### LV09 低速层运行使地形边际能量效应由放大转为近中性

**条件性运行级证据：** 无低速层时，地形在非均匀背景中总体提高能量；加入低速层后，点估计接近中性并略偏抑制，但区间跨越中性值。

**定量依据：** M4/M2：空间块中位数 1.78 倍，95%区间 1.23-2.12 倍；站点级描述中位数 1.66 倍；M6/M5：空间块中位数 0.99 倍，95%区间 0.76-1.19 倍；站点级描述中位数 0.94 倍。

![LV09 低速层运行使地形边际能量效应由放大转为近中性](../figures/low_velocity/Figure_LV09_conditional_factorial_cells.png)

**科学解释：** 地形不是可以从简单模型直接乘到复杂模型上的固定修正量；其边际效应取决于波场已经被散射和低速滞留改造的程度。

**适用边界：** M6/M5 的能量点估计为 0.985，但 95%区间 0.757-1.185 跨 1，因此只支持由显著放大转为近中性，不能声称抑制方向显著；唯一归因仍要求源、随机实现、Q、网格和边界完全一致。

**建议英文表述：** The marginal topographic energy effect changes from amplification without the low-velocity run to a statistically neutral estimate with it, conditional on run equivalence.

*绝对幅能量结论带运行清单限制。*

### LV10 地形×低速层交互是指标选择性的混合效应

**正向确定性证据：** 能量、峰值、t05、t50、晚期能量比例和 T 占比支持非零交互；T90、tmax、t95、Z/R 占比区间跨零。

**定量依据：** 交互项定义为 (M6-M5)-(M4-M2)，正值指标在对数比值域计算，时间和占比使用差值；图按单位分面，避免混合尺度。

![LV10 地形×低速层交互是指标选择性的混合效应](../figures/low_velocity/Figure_LV10_interaction_distributions.png)

**科学解释：** 结果支持“非加性集中在部分传播属性”，不支持“所有指标都存在同方向强交互”。

**适用边界：** 物理原因可能包括陷获、转换、聚焦/散焦和散射饱和，现有台站输出不能唯一拆分。

**建议英文表述：** Topography-by-low-velocity interaction is metric specific: selected energy, timing, late-energy, and transverse-partition measures are nonzero, whereas several duration and component intervals include zero.

*交互区间由相同 57 个空间块中位数估计。*

### LV11 峰值与能量地形空间指纹在低速背景中部分保留，T90 不显著

**正向确定性证据：** 同一位置的地形强弱格局在有无低速层之间并非完全消失，但保留程度取决于指标。

**定量依据：** 总能量地形效应的距离控制块相关 rho=0.53、q=0.00011；T90 为 rho=0.26、q=0.095。

![LV11 峰值与能量地形空间指纹在低速背景中部分保留，T90 不显著](../figures/low_velocity/Figure_LV11_topography_signature_persistence.png)

**科学解释：** 能量指纹的中等相关说明地形热点有一定跨背景稳定性；T90 不显著说明持续时间格局更容易被低速层重排。

**适用边界：** 这是空间格局相关，不是 M4 与 M2 或 M6 与 M5 原始波形相关。

**建议英文表述：** The spatial topographic fingerprint persists for energy more clearly than for T90, whose distance-controlled correlation is not significant.

*每条射线先去三次距离趋势，再标准化与分块。*

### LV12 低速背景下路径高差仍对应峰值/能量降低和 T90 延长

**正向确定性证据：** 路径累计高差必须在新背景中重新检验；结果表明它仍与地形边际效应具有系统关系。

**定量依据：** 能量效应与路径高差的距离控制相关 rho=-0.47、q=0.00072；T90 为 rho=0.52、q=0.00014。

![LV12 低速背景下路径高差仍对应峰值/能量降低和 T90 延长](../figures/low_velocity/Figure_LV12_path_relief_low_velocity.png)

**科学解释：** 更大路径起伏仍倾向于削弱相干幅能量并延长持续，但相关强度与无低速层背景不同。

**适用边界：** 路径使用地表投影直线，尚未包含有限频率 Fresnel 走廊、三维射线弯曲或波场通量。

**建议英文表述：** Path relief remains associated with reduced coherent energy and prolonged duration in the low-velocity background, but the relationship must be re-estimated rather than transferred from the baseline models.

*路径指标来自当前 A16/S12 几何和既有路径派生表。*

## 第四部分｜距离迁移、相位与代表波形

判断传播状态并把统计分布对应到真实波形。

### LV13 低速层运行使能量峰迁移变慢且空间离散增大

**正向确定性证据：** M5/M6 的能量峰随距离迁移斜率显著高于 M1-M4，同时同距离散布明显变大。

**定量依据：** M5/M2：空间块中位变化 111.74 s，95%区间 91.23 至 123.39 s；站点级描述中位数 108.43 s；M6/M4：空间块中位变化 100.99 s，95%区间 83.66 至 119.35 s；站点级描述中位数 99.64 s。删失安全斜率覆盖 0.84-1.90 s/km。

![LV13 低速层运行使能量峰迁移变慢且空间离散增大](../figures/low_velocity/Figure_LV13_low_velocity_tmax_distance.png)

**科学解释：** 低速结构显著减慢峰能量迁移并提高路径敏感性，但仍保留清晰距离结构。

**适用边界：** 斜率来自 50-395 s 记录内 tmax；边界受限点以 x 标出并从敏感性斜率中剔除。

**建议英文表述：** The low-velocity runs slow and disorder peak-energy migration, with larger distance slopes and substantially greater path-dependent scatter.

*边界受影响点单独标识；拟合为 400 s 窗内描述。*

### LV14 低速层仍未使主能量迁移进入简单 R² 扩散状态

**反向/排除性证据：** 全部主样本和删失安全敏感性样本中，线性距离形式均优于简单 R² 形式。

**定量依据：** 删失安全六组拟合的最小 Delta AIC(R²-线性) 为 12.79，所有 preferred_form 均为 linear。

![LV14 低速层仍未使主能量迁移进入简单 R² 扩散状态](../figures/low_velocity/Figure_LV14_linear_vs_diffusion.png)

**科学解释：** 低速层使传播更慢、更离散，但主能量脊仍更接近弹道/准弹道距离标度，而非简单强扩散峰时标度。

**适用边界：** 该检验只比较两个简化经验形式，不能排除更复杂的非高斯扩散、频散或多阶段输运。

**建议英文表述：** Even after censor-safe filtering, the main energy ridge remains better described by linear distance than by a simple R-squared diffusion form.

*仅作当前 400 s 记录窗内传播状态诊断。*

### LV15 包络相似性提高并不意味着相位波形拟合成功

**正向确定性证据：** 低速层运行可以保持或改善缓慢能量包络演化，同时零时滞三分量波形相关仍集中在零附近。

**定量依据：** 图同时给出零时滞 3C 波形相关与允许 ±10 s 的 5 s 包络最佳相关；两者的经验分布和散点关系明显分离。

![LV15 包络相似性提高并不意味着相位波形拟合成功](../figures/low_velocity/Figure_LV15_waveform_envelope_similarity.png)

**科学解释：** 包络比较检验能量迁移，波形相关检验相位与脉冲结构；论文必须并列报告，不能用前者替代后者。

**适用边界：** 允许时移会提高包络相关，不能据此声称走时、相位和源机制均已匹配。

**建议英文表述：** Improved envelope similarity does not imply phase agreement; the two diagnostics capture distinct aspects of the waveform.

*相关性不做逐台站自由振幅拟合。*

### LV16 数据选取的代表台站验证总体分布不是单迹异常

**正向确定性证据：** 代表波形依据效应分位数、同距离和交互强度规则自动选取，而非根据视觉效果挑选。

**定量依据：** 图包含平坦/地形背景的中位能量效应、高延迟、强正/负地形交互和约 100 km 同距台站。

![LV16 数据选取的代表台站验证总体分布不是单迹异常](../figures/low_velocity/Figure_LV16_representative_station_atlas.png)

**科学解释：** 这些波形把统计量对应到真实相位、尾波和分量变化，防止只用中位数隐藏空间异质性。

**适用边界：** 代表台站用于解释，不替代 575 站和 57 空间块的总体统计。

**建议英文表述：** Data-selected representative traces confirm that the reported distributions correspond to reproducible waveform changes rather than a single visually chosen station.

*选择规则与台站编号保存在 low_velocity_representative_stations.json。*

## 第五部分｜Apollo 对比、删失和空间异质性

同时报告改善、仍然存在的失配与记录窗限制。

### LV17 低速层把 S12 早期包络推向 Apollo，但仍远短于观测长尾

**正向确定性证据：** M5/M6 的包络能量峰和累积能量明显晚于 M1-M4，方向上改善了观测对比。

**定量依据：** M5/M6 tmax 为 213.22/272.45 s，观测为 658.29 s；t95 为 368.22/381.88 s，观测为 2804.62 s。

![LV17 低速层把 S12 早期包络推向 Apollo，但仍远短于观测长尾](../figures/low_velocity/Figure_LV17_observed_six_model_envelopes.png)

**科学解释：** 低速层是现有试验中最强的延迟机制，但仍只覆盖 Apollo 长尾的早期部分。

**适用边界：** 模型和观测终止时间不同；累计曲线明确使用各自可用记录，不能把模型终点解释为完整 100% 物理能量。

**建议英文表述：** The low-velocity runs move the early S12 envelope toward Apollo, but their peak and t95 times remain far earlier than the observed long coda.

*每个模型只使用一个共享 3C RMS 源尺度。*

### LV18 时间改善没有解决相位和完整持续时间失配

**反向/排除性证据：** M5/M6 的 tmax 和包络相关改善，但早期三分量相位相关仍很低，完整 t95 差距仍接近一个数量级。

**定量依据：** 早期 3C 相关为 M5 -0.058、M6 0.080；观测 t95=2804.6 s。

![LV18 时间改善没有解决相位和完整持续时间失配](../figures/low_velocity/Figure_LV18_observed_metric_comparison.png)

**科学解释：** 新增低速机制改善了“何时积累能量”，却没有同时修复“每个脉冲的相位”和“数千秒持续时间”。

**适用边界：** 单台站观测不能建立距离幂律，但足以排除当前模型已经再现该站长尾的说法。

**建议英文表述：** Improved envelope timing does not resolve the near-zero phase correlation or the order-of-magnitude duration gap to Apollo.

*观测值来自 A16S12；模型按共享源尺度比较。*

### LV19 低速层时频能量仍远短于 Apollo

**反向/排除性证据：** M5/M6 把 0.3-0.9 Hz 能量延长到 400 s 左右，但观测在更长时间保持宽频带能量。

**定量依据：** 图使用统一 0.2-1.2 Hz 展示范围和每面板相对功率标度，M4、M5、M6 与观测的持续时间和频带演化可直接比较。

![LV19 低速层时频能量仍远短于 Apollo](../figures/low_velocity/Figure_LV19_time_frequency.png)

**科学解释：** 失配同时存在于时间和频率：不仅尾波太短，能量中心与频带演化也不同。

**适用边界：** 面板采用相对功率，不能用于绝对谱幅比较；它支持的是时频形态与持续范围判断。

**建议英文表述：** The low-velocity synthetics prolong band-limited energy but still fail to reproduce the observed time-frequency extent of the Apollo coda.

*颜色为各面板相对最大功率 dB。*

### LV20 400 s 记录仍右删失一部分低速层台站

**待验证/受限证据：** 延长到 400 s 显著提高覆盖，但一部分台站的 t95 仍落在记录最后 20 s，尾部能量尚未稳定结束。

**定量依据：** 575 个主样本中，t95 位于最后 20 s 的台站为 M5 118 个、M6 132 个。

![LV20 400 s 记录仍右删失一部分低速层台站](../figures/low_velocity/Figure_LV20_tail_censoring.png)

**科学解释：** 这些台站的 t95/T90 是下限或窗口依赖估计；应在论文图表和统计中明确标记。

**适用边界：** 右删失不否定早期延迟和三分量转换，但限制对完整尾波寿命、距离斜率和长时能量比例的推断。

**建议英文表述：** The 400 s records still right-censor a substantial subset, so late t95 and T90 values are lower bounds for those stations.

*375 s 被用作距 395 s 分析终点 20 s 的删失阈值。*

### LV21 低速层延迟具有距离结构、非单调性和路径差异

**正向确定性证据：** tmax 差值随距离先增长，随后在不同射线上饱和或回落，不能表示为常数静态时移。

**定量依据：** 三条剖面分别用 11 站平滑显示 M5-M2 与 M6-M4 的局部距离结构；站点散点保留真实离散。

![LV21 低速层延迟具有距离结构、非单调性和路径差异](../figures/low_velocity/Figure_LV21_low_velocity_delay_distance.png)

**科学解释：** 距离结构说明低速层效应随传播路径累积和重分配，可能包含多次波、模式转换及出射位置变化。

**适用边界：** 非单调曲线不应被拟合为单一全区线性延迟定律；它是机制诊断而非层厚反演。

**建议英文表述：** Low-velocity delay is distance structured and nonmonotonic, ruling out representation by a single static time correction.

*曲线为局部平滑，不用于声明全程单调。*

### LV22 一致的空间块估计确认能量、持续与延迟效应稳健

**正向确定性证据：** 点估计、bootstrap 区间和 Wilcoxon 检验均使用相同的 57 个非重叠 10 站块中位数。

**定量依据：** M5/M2 能量：空间块中位数 19.72 倍，95%区间 12.20-87.29 倍；站点级描述中位数 19.07 倍；M6/M4 能量：空间块中位数 12.04 倍，95%区间 6.72-65.61 倍；站点级描述中位数 11.59 倍。

![LV22 一致的空间块估计确认能量、持续与延迟效应稳健](../figures/low_velocity/Figure_LV22_effect_forest.png)

**科学解释：** 空间块避免把相邻台站错误当作 575 个独立重复，区间宽度也揭示了路径异质性。

**适用边界：** 块区间仍依赖三条剖面代表性；不能替代新的方位覆盖或随机实现重复。

**建议英文表述：** Consistent spatial-block estimators confirm robust energy, duration, and delay contrasts without treating neighboring receivers as independent replicates.

*同一块中位数用于点估计、区间和符号秩检验。*

### LV23 低速模型的 T 转换沿三条剖面系统变化

**正向确定性证据：** M5/M6 的 T 占比并非固定百分比，而是随距离与射线呈连续起伏和局部峰谷。

**定量依据：** 图在每条剖面同时展示 M2、M4、M5、M6 的 11 站平滑 T 占比，便于识别背景和低速层的条件差异。

![LV23 低速模型的 T 转换沿三条剖面系统变化](../figures/low_velocity/Figure_LV23_transverse_fraction_profiles.png)

**科学解释：** 空间结构支持路径控制的三维转换；低速层和地形共同改变转换发生的位置与强度。

**适用边界：** 平滑曲线不提供独立自由度；统计显著性仍来自分块推断。

**建议英文表述：** Transverse-energy conversion varies systematically along all three profiles, indicating spatially structured three-dimensional coupling rather than a model-wide fraction.

*T 占比使用能量分数，避免近零基准倍数发散。*

### LV24 峰时和持续时间估计强烈依赖可用记录窗

**反向/排除性证据：** M5/M6 的 tmax 在公共窗与延长窗相对稳定程度不同，而 t95/T90 在延长窗显著增加。

**定量依据：** 图直接连接 50-245 s 和 50-395 s 的主样本中位值，分开显示 tmax、t95 与 T90。

![LV24 峰时和持续时间估计强烈依赖可用记录窗](../figures/low_velocity/Figure_LV24_common_vs_extended.png)

**科学解释：** 公共窗适合模型间效应比较；延长窗适合低速层内部尾波诊断，两者不能混成同一结论。

**适用边界：** 延长窗仍可能右删失，因此更长记录是下一轮验证所必需的，而不是可选的版式改动。

**建议英文表述：** Peak and duration estimates are strongly window dependent, so common-window contrasts and extended-window tail diagnostics must be reported separately.

*t05/t50/t95/T90 均按三分量滤波速度平方累计能量定义。*

## 可复现性

输入审计、派生CSV、24幅低速层图及分析脚本均保存在 h/jgr_planets_submission 内。
