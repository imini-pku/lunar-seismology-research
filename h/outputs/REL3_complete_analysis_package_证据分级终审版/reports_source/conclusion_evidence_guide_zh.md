# 29项主结果与证据图册

所有条目均改用原始/滤波波形、Hilbert-RMS包络、累积能量或距离波形剖面呈现，不再使用柱状图。主结果按确定性正向结果、反向/排除性结果和证据不足/待验证事项分开，第三类不作为论文结论。

## 正向的确定性结果

### C01 随机散射稳定推迟能量峰值，但延迟依赖平滑尺度

![C01](cards/C01_scatter-tmax-smoothing.png)

**波形判据：** 同一代表台站在5、10、20周期平滑下都显示M2峰值晚于M1，但峰值位置会随平滑窗移动。

**代表记录：** r39 · 射线1 · 38.0 km

**证据来源：** `station.nc + tmax_smoothing_sensitivity.csv`

### C02 随机散射最稳定的表现是波列全面展宽

![C02](cards/C02_scatter-broadening.png)

**波形判据：** 代表台站中M2主脉冲变宽、上升变慢且尾波更长，展宽不是单一数值造成的视觉假象。

**代表记录：** r437 · 射线2 · 223.0 km

**证据来源：** `station.nc + station_metrics.csv`

### C03 随机散射降低主波幅、总能量和脉冲性

![C03](cards/C03_scatter-amplitude-energy-snr.png)

**波形判据：** 共享振幅尺度下，M2主脉冲和累计能量均低于M1，同时晚到能量比例增加。

**代表记录：** r431 · 射线2 · 217.0 km

**证据来源：** `station.nc + station_metrics.csv`

### C05 射线2、3存在稳定的路径高差—波形关系

![C05](cards/C05_path-relief-control.png)

**波形判据：** 去除震中距后，射线2、3的路径高差与M3−M1振幅、能量和持续时间均呈强相关；该确定性结果限定于射线2、3。

**代表记录：** r324 · 射线2 · 110.0 km；r543 · 射线3 · 89.0 km

**证据来源：** `station.nc + terrain station metrics`

### C06 平均坡度补充累计高差未包含的起伏分布信息

![C06](cards/C06_mean-slope-waveform.png)

**波形判据：** 累计高差只记录路径最高与最低点之差；平均绝对坡度还区分缓慢单次起伏与反复陡坡。近似同距离、同高差台站的波形差异说明两者不能互相替代。

**代表记录：** r532 · 射线3 · 78.0 km；r537 · 射线3 · 83.0 km

**证据来源：** `station.nc + terrain station metrics`

### C07 地形与散射存在显著饱和型非加性耦合

![C07](cards/C07_nonlinear-saturation.png)

**波形判据：** 同一台站的增量波形显示，地形在无散射背景中的影响明显大于其在散射背景中的附加影响。

**代表记录：** r322 · 射线2 · 108.0 km

**证据来源：** `station.nc + factorial station metrics`

### C08 代表波形支持M1最尖锐、M4比M2更弥散

![C08](cards/C08_model-snr-separation.png)

**波形判据：** r59满足SNR依次降低且M4持续时间显著长于M2；图中M4主峰可辨识度最低、尾波宽于M2。

**代表记录：** r59 · 射线1 · 58.0 km

**证据来源：** `station.nc + station_metrics.csv`

### C10 地形幅度—能量—宽度空间效应在散射背景中部分保留

![C10](cards/C10_terrain-signature-persistence.png)

**波形判据：** M4−M2表示散射背景中的地形边际效应；它与M3−M1在峰值、能量和T90上的空间块相关均约0.53–0.55，说明这些强弱位置存在中等一致性。

**代表记录：** r324 · 射线2 · 110.0 km

**证据来源：** `station.nc + signature_persistence.csv`

### C11 同震中距下射线2的散射延迟和展宽最大

![C11](cards/C11_ray2-strongest.png)

**波形判据：** 三条射线统一选取约100 km台站后，M2−M1的tmax延迟与T90倍率均以射线2最大；射线3不再使用视觉上峰值近乎重合的原代表站。

**代表记录：** r101 · 射线1 · 100.0 km；r314 · 射线2 · 100.0 km；r554 · 射线3 · 100.0 km

**证据来源：** `station.nc + ray-wise effects`

### C12 射线1振幅损失弱，但包络仍受地形影响

![C12](cards/C12_ray1-envelope-change.png)

**波形判据：** 共享振幅尺度下M1/M3主脉冲接近，但M3包络更宽、尾波更持久。

**代表记录：** r142 · 射线1 · 141.0 km

**证据来源：** `station.nc + ray1 station metrics`

### C19 真实A16S12三分量主频稳定集中在约0.43 Hz

![C19](cards/C19_observed-dominant-frequency.png)

**波形判据：** 观测三分量时序和频谱峰彼此一致，而模型S12平均频谱峰整体偏高。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 three-component waveforms`

### C29 12组距离关系全部支持线性而非R²形式

![C29](cards/C29_linear-beats-diffusion.png)

**波形判据：** 波形剖面的能量脊随距离近似直线移动；线性轨迹沿脊通过，而R²轨迹系统弯离。

**代表记录：** 三条射线波形剖面；四模型拟合轨迹

**证据来源：** `station.nc + peak-time fits`

### C30 当前模拟仍由弹道传播主导

![C30](cards/C30_ballistic-dominance.png)

**波形判据：** 射线2波形剖面的主脉冲形成清晰直线到时脊，扩散型曲线不能沿主能量传播。

**代表记录：** 射线2 M1波形剖面

**证据来源：** `station.nc + peak-time fits`

## 反向或排除性的确定结果

### C04 起伏地形造成有限展宽，但没有形成明显弥散尾波

![C04](cards/C04_topography-scatter-like.png)

**波形判据：** M3相对M1的能量窗和拟合衰减时间增大，但差异主要位于低振幅尾部；该图支持弱地形多路径效应，不足以证明强随机散射。

**代表记录：** r159 · 射线1 · 158.0 km

**证据来源：** `station.nc + station_metrics.csv`

### C16 射线1、2的不同折点不支持共同单一折点解释

![C16](cards/C16_no-common-breakpoint.png)

**波形判据：** 射线1和2的平坦背景散射延迟分别在约128和68 km后明显转为随距离增加；折点位置和前后波形变化不同，不支持用共同单一折点或统一层厚直接解释。

**代表记录：** r109 · 射线1 · 108.0 km；r149 · 射线1 · 148.0 km；r262 · 射线2 · 48.0 km；r302 · 射线2 · 88.0 km

**证据来源：** `station.nc + breakpoints.csv`

### C20 初始能量时间大体相容，但包络演化完全不相容

![C20](cards/C20_onset-versus-envelope.png)

**波形判据：** 观测和模型都在约80-100秒起振；此后模型迅速衰减而观测包络继续增强。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 + modeled S12 waveforms`

### C21 观测三分量能量峰值远晚于所有模型

![C21](cards/C21_observed-tmax-gap.png)

**波形判据：** 归一化三分量能量包络显示，模型峰值都在百秒内，观测峰值延迟至约六百秒以后。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 + modeled S12 envelopes`

### C22 地形和随机散射只产生小幅峰值延迟

![C22](cards/C22_small-model-delays.png)

**波形判据：** 早期放大图中四模型峰值只相差数秒；完整时间轴上这一差异远小于观测峰值延迟。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 + modeled S12 envelopes`

### C23 观测上升过程比模型长一个至两个数量级

![C23](cards/C23_rise-duration-gap.png)

**波形判据：** 从5%累计能量到包络峰值的阴影区间显示，观测跨越数百秒，模型仅跨越数秒到十余秒。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 cumulative energy + envelopes`

### C24 随机散射延长合成尾波，但强度仍不足

![C24](cards/C24_scatter-extends-t95.png)

**波形判据：** 累积能量曲线中M2/M4晚于M1到达95%，但仍在约160秒结束，远早于观测。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 cumulative energy`

### C25 地形单独作用的尾波延长弱于当前随机散射

![C25](cards/C25_topography-weaker-than-scatter.png)

**波形判据：** 合成记录累积能量曲线显示M3最接近M1，M2和M4的尾部延长更明显。

**代表记录：** 四模型S12

**证据来源：** `modeled S12 cumulative energy`

### C26 真实记录前250 s仅包含约3.98%的总能量

![C26](cards/C26_observed-energy-fraction.png)

**波形判据：** 观测波形、包络和累积能量共同显示，250秒截点只覆盖初始波列，主要能量仍在其后。

**代表记录：** 真实A16S12

**证据来源：** `A16S12 waveform and cumulative energy`

### C27 统一源能量后，早期相位波形相似性仍很低

![C27](cards/C27_low-waveform-similarity.png)

**波形判据：** 三个分量逐一叠加后，四模型都无法跟随观测的相位和振幅起伏，差异不是单一分量造成。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `source-matched A16S12 waveforms`

### C28 早期三分量包络甚至呈负相关

![C28](cards/C28_negative-envelope-correlation.png)

**波形判据：** 观测包络在模型主脉冲衰减时仍继续增强，峰谷关系相反；小幅时移不能改变整体趋势。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `source-matched A16S12 envelopes`

## 证据不足、无法确定与待验证事项（不作为结论）

### C09 坑缘聚焦/散焦机制尚需波场证据

![C09](cards/C09_topography-neutral-median.png)

**波形判据：** r578/r580的M4−M2幅能量效应反号是确定观测，但是否由坑缘曲率导致聚焦/散焦仍无法仅凭台站波形确定。

**代表记录：** r578 · 射线3 · 124.0 km；r580 · 射线3 · 126.0 km

**证据来源：** `station.nc + terrain path profiles`

### C17 当前数据无法给出唯一地形影响“泄漏距离”

![C17](cards/C17_no-unique-spatial-lag.png)

**波形判据：** 三条射线按各自最佳距离偏移后，地形扰动波形仍不能稳定对齐，且所需偏移方向不一致。

**代表记录：** r108 · 射线1 · 107.0 km；r131 · 射线1 · 130.0 km；r335 · 射线2 · 121.0 km；r353 · 射线2 · 139.0 km；r531 · 射线3 · 77.0 km；r512 · 射线3 · 58.0 km

**证据来源：** `station.nc + spatial_lags.csv`

### C18 最可靠判据是包络展宽 + 脉冲性 + 路径地形

![C18](cards/C18_combined-diagnostic.png)

**波形判据：** 同一台站的四模型波形与路径地形放在一起后，可同时判断波列展宽、脉冲性和地形背景。

**代表记录：** r347 · 射线2 · 133.0 km

**证据来源：** `station.nc + topography profile`

### C31 真实S12单点不能建立观测距离幂律

![C31](cards/C31_single-observed-anchor.png)

**波形判据：** 合成波形提供完整距离剖面，而真实数据仅在约152千米处提供一条长尾记录，无法拟合距离趋势。

**代表记录：** 射线2合成剖面；真实S12单点

**证据来源：** `synthetic waveform section + A16S12`

### C32 下一步应延长记录并重构散射层，而非只调源振幅

![C32](cards/C32_extend-synthetics.png)

**波形判据：** 同一时间轴上，四模型在250秒终止而观测持续至3000秒以上，延长记录是检验长尾机制的前提。

**代表记录：** 真实A16S12；四模型S12

**证据来源：** `A16S12 + modeled S12 envelopes`
