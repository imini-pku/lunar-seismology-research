# 撞击—台站路径的 LOLA 地形图审计

## 图件索引

- `figures/impact_terrain/impact_station_terrain_overview.png` / `.pdf`：全部 9 个撞击位置、4 个接收台站、21 条记录路径，叠加全部记录框和近距候选框。
- `figures/impact_terrain/nine_event_terrain_domains.png` / `.pdf`：按撞击事件分开的九联图。
- `figures/impact_terrain/{event_id}_terrain_domain.png` / `.pdf`：9 张逐事件大图；在主报告中逐事件引用。
- `figures/impact_terrain/local_candidate_terrain_domains.png` / `.pdf`：8 个近距候选域、11 条文献清晰路径的八联放大图。
- `figures/impact_terrain/{event_id}_local_terrain_domain.png` / `.pdf`：8 张近距候选域大图。

共 20 组 PNG/PDF，PNG 用于 Markdown 阅读，PDF 用于放大或排版。

## 数据验证

1. 旧 float IMG 尺寸不符，拒绝使用。新数据从 NASA/PDS 的 `LDEM_64` 整数产品独立下载。
2. 21 个 HTTP 字节块均验证 `206 Partial Content`、精确 `Content-Range`、完整全球文件长度 530,841,600 字节及本块字节数。下载条带合并后验证长度，并记录每块及文件 SHA-256。
3. 官方标签规定小端 16-bit 有符号整数、0.5 m/DN、像元注册、东经正。裁片保留发布产品的 64 像元/度采样，没有地形上采样或跨缺口造值。
4. 提取 3712×4992 原生网格，范围西经 38°—东经 40°、南纬 18°—北纬 40°；高程 −4913.0～4441.5 m，所有像元均在共同 −5～+5 km 色标内。
5. S15 为 **+26.13406°N、+3.62991°E**。所有事件与台站位置读取现有审计 CSV；21 条大圆路径逐条检查，全部在对应蓝框内。
6. 对雨海内部、亚平宁区域及托勒密坑等位置抽取原生高程作地理方向的合理性检查。该步骤不代替独立测绘控制点精度评估。

完整记录见 `lola_data_provenance.json`、`terrain_figure_validation.json` 和 `site_height_checks.csv`。数据与绘图语义说明见 `data/raw/lola_impact_64/README.md`。

## 读图要点

高程颜色显示月海低地、盆地边缘和较高的崎岖地形；轻阴影只帮助识别坡面，不是散射强度。高地地质单元不能仅以“高于 0 km”划定。蓝框包括全部有记录台站，橙虚线框只含距离小于 400 km 且文献判定清晰的路径；400 km 是本项目初步计算分组阈值，不是文献普适界限。框线相同则重叠显示。路径虚线及台站名后 `*` 为该事件下低信噪比记录。

这些图用于决定传播路径和计算覆盖，**不能直接从地形起伏读取速度扰动强度、相关尺度或扰动深度**。它们仍须由波形比较与模型选择约束。
