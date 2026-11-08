# 月球地震上升时间、震中距与扩散时间关系：文献图件归档

本页归档三幅与“上升时间/能量峰值时间—震中距”直接相关的文献图件，供论文讨论、审稿回复和方法说明使用。图件仅用于科研引用和内部分析，正式投稿时应按期刊版权与图件许可要求处理。

## 图 1：Apollo 15 原始上升时间—距离曲线

文件：`figures/Apollo15_SP289_Fig8-12_rise-time_vs_distance.png`

来源：Apollo 15 Preliminary Science Report, NASA SP-289, Passive Seismic Experiment, Figure 8-12, printed page 8-15.

原始报告将 rise time 定义为从撞击时刻到信号强度近似峰值的时间。图中分别给出 0.45、1、2、4 和 8 Hz 窄带结果。近距离段上升时间随距离增加而增加，在约 100–150 km 达到较大值；更远距离总体趋于平台，并在约 180 km 附近出现与能量聚焦相关的局部凹陷。该图不是一个简单的全距离 (R^2) 拟合，而是显示散射层厚度、频率和路径聚焦共同影响上升过程。

原始来源：[Apollo 15 Preliminary Science Report PDF](https://www.apollojournals.org/alsj/a15/as15psr.pdf)。

## 图 2：2012 年论文中的 rise time 定义

文件：`figures/BlanchetteGuertin2012_Fig3_risetime_definition.png`

来源：Blanchette-Guertin, Johnson, and Lawrence (2012), *Investigation of scattering in lunar seismic coda*, Figure 3.

图中灰色区间表示 S-risetime，红线为平滑包络，蓝线为尾波指数衰减拟合。该论文的 rise time 是初始 P/S 到时至最大 P/S 振幅的时间，并报告 rise time 对震中距没有清晰、统一的经验依赖；距离效应在尾波衰减时间 \(\tau_d\) 和 \(Q_c\) 中更明显。因此不能把该论文的 rise time 直接等同于严格的 (R^2/D) 扩散时间。

原始来源：[Wiley article](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2011JE004042)。

## 图 3：2017 年扩散模型使用的 (t_{max})—震中距关系

文件：`figures/Gillet2017_Fig4_tmax_vs_epicentral_distance.png`

来源：Gillet et al. (2017), *Scattering attenuation profile of the Moon*, Figure 4.

图中给出 0.5 Hz 和 7 Hz 下的能量峰值时间 \(t_{max}\) 与震中距关系，并区分撞击、浅月震和深月震。该研究使用球对称、深度相关的扩散模型反演月球散射结构；实际模型包含球形几何、深度变化的扩散率和吸收，而不是简单地把每个点套入 \(t_{max}=R^2/(6D)\)。

原始来源：[ScienceDirect article](https://www.sciencedirect.com/science/article/pii/S0031920116301492)。

## 与本项目结果的对应关系

本项目检验的是能量峰值时间 \(t_{max}(R)\)，不是直接检验 rise time(R)。简单扩散理论给出特征时间 \(t_{diff}\sim R^2/D\)，而有限速度的直达或主能量包更接近 \(R/v\)。A16/S12 三条剖面、四个模型共 12 组拟合均由线性形式优于平方距离形式；半空间模型在多种平滑窗口下也得到相同排序。因此当前 250 s 模拟窗口中的主能量包仍以弹道/有限路径传播为主，不能据此否定月球在更长时间尺度上的扩散尾波。
