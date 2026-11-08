# 月震数值模拟与区域散射研究

研究月表起伏、浅层结构与介质非均匀性对月震三分量波形、能量分布和持续时间的影响，并整理区域散射评估所需的观测数据、地形与参考模型。

## 研究问题

- 成组模型之间的波形差异，能否与地形、浅层结构及非均匀介质设置相对应？
- 峰值、包络和累计能量等指标如何随传播距离与路径变化？
- 公开 Apollo 记录中的缺样、仪器状态和噪声，如何影响后续比较与反演的准入？

## 数据与方法

| 项目 | 数据与分析 |
|---|---|
| [月震三维模拟与统计分析](h/jgr_planets_submission/README.md) | 6 种模型配置、575 个模拟接收点的三分量时序；使用已有求解器输出，进行滤波、包络与累计能量计算、成组比较、距离控制与敏感性分析。 |
| [月球散射强度评估](月球散射强度评估/README.md) | 9 次人工撞击、21 对事件与台站、60 个实际观测分量；核对原始记录、仪器与处理状态，结合 LOLA 地形和文献参考模型开展区域结构设计。 |

代码、参数口径、来源记录和结果表分别位于各项目的 `code/`、`config/`、`data/`、`results/` 与 `provenance/` 中。模拟接收点与真实观测台站分别统计。

## 研究成果

- [全模型综合分析报告（M1–M6 映射修订版）](h/jgr_planets_submission/reports/月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版_M1-M6映射修订版.pdf)
- [低速层专题分析报告（M1–M6 映射修订版）](h/jgr_planets_submission/reports/低速层模型详细数据分析报告_REL3标准_证据分级终审版_M1-M6映射修订版.pdf)
- [分析代码](h/jgr_planets_submission/code) · [派生结果表](h/jgr_planets_submission/data/derived) · [科研稿件](h/jgr_planets_submission/manuscript) · [Supporting Information](h/jgr_planets_submission/supporting_information)
- [区域散射研究设计](月球散射强度评估/docs/研究设计总册_20261029/00_阅读指南与总体方案.md)
- [公开波形与处理方法核查](月球散射强度评估/docs/16_作者公开波形筛选与代码复现_20261103.md) · [基础预处理图册](月球散射强度评估/figures/published_waveforms_20261103/Apollo_作者基础预处理_13页.pdf)

## 当前阶段

三维模拟分析项目始于 2025-03，持续进行；论文已重新提交，二次审稿尚未完成。区域评估已有数据检查、处理结果与结构设计，新 CGFD3D 波场模拟和最终区域反演尚未完成。逐条清洗中的图件检查属于初步检查，独立研究复核待完成。

不同日期的研究材料保留在各自目录。当前方案以各项目 README 顶部及对应文件日期为准，历史待执行清单不代表已经运行。

## 下载与复现

完整资料见 [最新 Release](https://github.com/imini-pku/lunar-seismology-research/releases/latest)。将三个 ZIP **解压到同一个父目录**，合并得到 `h/` 与 `月球散射强度评估/` 两个目录。

| 完整包 | 内容 |
|---|---|
| [lunar-h-original-project.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-h-original-project.zip) | 三维模拟分析代码、配置、原始与派生数据、图件、完整报告、论文与补充材料。 |
| [lunar-scattering-original-project.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-scattering-original-project.zip) | 区域评估代码、观测与处理数据、当前使用的原生 LOLA 条带/裁片、图件、结果与研究设计。 |
| [lunar-scattering-original-dem.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-scattering-original-dem.zip) | `data/raw/dem/` 的历史数据文件。 |

**历史 DEM：**`ldem_64_float.img` 的文件尺寸与产品标签不符，已停止用于新地图。当前有效输入在主包的 `data/raw/lola_impact_64/` 中，参见[来源与读取说明](月球散射强度评估/data/raw/lola_impact_64/README.md)。

恢复目录后，按原项目说明安装依赖并调整本机路径配置，再运行对应脚本。仅克隆仓库中的可浏览文件，不包含大型 NetCDF、MiniSEED、NPZ 和 DEM。

完整包的大小与校验值见 [资产清单](publication/release_assets_manifest.json) 和 [SHA256SUMS](publication/SHA256SUMS.txt)；每包内另有逐文件校验清单。[来源与权利说明](NOTICE.md)记录外部数据和代码的归属。
