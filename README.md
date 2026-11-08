# 月震数值模拟与区域散射研究

本仓库保留两个原科研项目的代码、配置、分析表、图件、报告、论文及补充材料。网页可直接浏览主要文件；完整原文件按原目录结构存入 Release，包括原始与处理数据、历史成果包和大型二进制文件。这里没有用合成演示替换原项目。

## 两个项目

| 原项目 | 已有内容与状态 | 阅读入口 |
|---|---|---|
| **h：月震三维数值模拟与统计分析** | 使用课题组已有求解器，开展成组模型比较、三分量时序分析、特征提取、距离与空间差异检查，保留 6 种配置的分析与科研文稿。研究起于 2025-03，持续进行；论文已重新提交，二次审稿尚未完成。 | [原项目说明](h/jgr_planets_submission/README.md) · [分析代码](h/jgr_planets_submission/code) · [派生结果](h/jgr_planets_submission/data/derived) · [报告](h/jgr_planets_submission/reports) |
| **月球散射强度评估** | 保存 Apollo 事件与台站核对、公开波形筛选、LOLA 地形、参考模型、三区域结构设计及处理结果。已有 9 个事件、21 对事件与台站、60 个实际分量的检查记录；新 CGFD3D 波场模拟与最终区域反演尚未完成。 | [原项目说明](月球散射强度评估/README.md) · [代码](月球散射强度评估/code) · [完整研究设计](月球散射强度评估/docs/研究设计总册_20261029) · [结果](月球散射强度评估/results) |

原文件包含不同日期的历史方案与结果；保留原样以便追溯。判断当前状态时，先读各项目 README 顶部最新说明，不能把旧方案中的待执行清单当作已完成实验。

## 直接查看已有成果

- [月球地形、分层、散射与低速层综合分析报告（M1–M6 映射修订版）](h/jgr_planets_submission/reports/月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版_M1-M6映射修订版.pdf)
- [低速层专题分析报告（M1–M6 映射修订版）](h/jgr_planets_submission/reports/低速层模型详细数据分析报告_REL3标准_证据分级终审版_M1-M6映射修订版.pdf)
- [科研稿件与双语版本](h/jgr_planets_submission/manuscript) · [Supporting Information](h/jgr_planets_submission/supporting_information)
- [区域散射研究阅读指南](月球散射强度评估/docs/研究设计总册_20261029/00_阅读指南与总体方案.md)
- [公开作者波形与代码核查](月球散射强度评估/docs/16_作者公开波形筛选与代码复现_20261103.md)
- [作者基础预处理图册](月球散射强度评估/figures/published_waveforms_20261103/Apollo_作者基础预处理_13页.pdf)

## 下载完整原项目

前往 [完整文件 Release](https://github.com/imini-pku/lunar-seismology-research/releases/latest)。三个 ZIP 均为独立完整压缩包，**解压到同一个父目录**，即可合并为原有的 `h/` 与 `月球散射强度评估/` 结构，无需改名或手工搬动内部文件。

| 资产 | 内容 |
|---|---|
| [lunar-h-original-project.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-h-original-project.zip) | h 的完整研究文件：分析代码、模型配置、原始模拟数据、派生表、报告、图件、本人论文与补充材料、既有成果包。 |
| [lunar-scattering-original-project.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-scattering-original-project.zip) | 区域散射项目的完整工作文件：源码、配置、观测与处理数据、实际使用的原生 LOLA 条带/裁片、图件、研究设计、结果与原有成果包。 |
| [lunar-scattering-original-dem.zip](https://github.com/imini-pku/lunar-seismology-research/releases/latest/download/lunar-scattering-original-dem.zip) | 原 `data/raw/dem/` 的 5 个历史文件，单独保存以保持原目录全貌。详见下方历史 DEM 说明。 |

精确大小、文件数与 SHA-256 见 [发布资产清单](publication/release_assets_manifest.json) 和 [SHA256SUMS](publication/SHA256SUMS.txt)。每个 ZIP 内附自己的逐文件 SHA-256 清单。源文件内容未经改写；压缩与目录归档只改变承载方式。

**历史 DEM 说明：**原 `ldem_64_float.img` 的尺寸不符合其产品标签，原研究已明确停止用它绘制新结果。本次因完整保留原文件而将它单独归档，不把它标为有效分析输入。当前使用的原生条带与裁片在主包 `data/raw/lola_impact_64/` 内，来源和读取方法见[原始说明](月球散射强度评估/data/raw/lola_impact_64/README.md)。

## 使用与复现

先下载所需完整 ZIP，恢复目录后按各原项目说明安装依赖、选择对应脚本。部分历史脚本保留本地路径配置，需按自己的存放位置修改 `config` 或运行参数。仅克隆网页展示文件，不会得到大型 NetCDF、MiniSEED、NPZ 或 DEM。

这是既有科研资料的完整归档与展示，本次没有重新运行全部数值模拟，也没有把源项目尚未完成的步骤改写为完成。Git 中可浏览文件的逐文件校验见 [repository_file_manifest.json](publication/repository_file_manifest.json)。

## 整理范围与来源

仅排除本机工具/运行缓存、Office 锁文件、私密审稿往来及投稿联系信、第三方全文文献库。原始公开数据的来源说明、标签、下载记录和第三方作者声明随文件保留；不把 Apollo、LOLA 或他人公开代码写成本人原创。具体说明见 [归档排除说明](publication/排除与保留说明.md) 和 [来源与权利说明](NOTICE.md)。

科研数据处理、代码和材料整理使用过 AI 辅助工具；原始分析、历史版本与本次归档工作在文件中分别保留，不据此声称独立开发了底层波场求解器。
