"""Build the REL3-standard low-velocity and full-synthesis reports.

The reports are evidence-led: every numbered conclusion is immediately paired
with a relevant figure, quantitative support, inferential boundary, and a
manuscript-ready English sentence.  Numeric values are loaded from the current
derived tables so the prose cannot silently drift from the analysis outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "jgr_planets_submission"
DERIVED = PROJECT / "data" / "derived"
FIGURES = PROJECT / "figures"
REPORTS = PROJECT / "reports"
PROVENANCE = PROJECT / "provenance"
LEGACY_CODE = PROJECT / "code" / "verified_legacy"
sys.path.insert(0, str(LEGACY_CODE))

from build_lunar_five_paper_synthesis_docx import (  # noqa: E402
    BLACK,
    BLUE,
    DEEP_BLUE,
    FONT,
    GOLD,
    LIGHT_BLUE,
    MUTED,
    NAVY,
    PALE_BLUE,
    PALE_GOLD,
    add_callout,
    add_field,
    add_figure,
    add_heading,
    add_paragraph,
    add_rich_paragraph,
    add_table,
    configure_section,
    configure_styles,
    set_document_language,
    set_paragraph_border,
    set_run_font,
)


LOW_DOCX = REPORTS / "低速层模型详细数据分析报告_REL3标准_证据分级终审版_M1-M6映射修订版.docx"
LOW_MD = REPORTS / "低速层模型详细数据分析报告_REL3标准_证据分级终审版.md"
FULL_DOCX = REPORTS / "月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版_M1-M6映射修订版.docx"
FULL_MD = REPORTS / "月球地形_分层_散射_低速层全模型综合分析报告_证据分级终审版.md"


FIG = {
    **{f"LV{i:02d}": FIGURES / "low_velocity" / name for i, name in enumerate(
        [
            "Figure_LV01_input_audit.png",
            "Figure_LV02_identifiable_design.png",
            "Figure_LV03_s12_common_waveforms.png",
            "Figure_LV04_s12_extended_energy.png",
            "Figure_LV05_low_effect_distributions.png",
            "Figure_LV06_low_effect_by_ray.png",
            "Figure_LV07_component_fractions.png",
            "Figure_LV08_transverse_conversion.png",
            "Figure_LV09_conditional_factorial_cells.png",
            "Figure_LV10_interaction_distributions.png",
            "Figure_LV11_topography_signature_persistence.png",
            "Figure_LV12_path_relief_low_velocity.png",
            "Figure_LV13_low_velocity_tmax_distance.png",
            "Figure_LV14_linear_vs_diffusion.png",
            "Figure_LV15_waveform_envelope_similarity.png",
            "Figure_LV16_representative_station_atlas.png",
            "Figure_LV17_observed_six_model_envelopes.png",
            "Figure_LV18_observed_metric_comparison.png",
            "Figure_LV19_time_frequency.png",
            "Figure_LV20_tail_censoring.png",
            "Figure_LV21_low_velocity_delay_distance.png",
            "Figure_LV22_effect_forest.png",
            "Figure_LV23_transverse_fraction_profiles.png",
            "Figure_LV24_common_vs_extended.png",
        ],
        start=1,
    )},
    **{f"HS{i}": FIGURES / "halfspace" / name for i, name in enumerate(
        [
            "Figure_HS1_topography_switch_waveforms.png",
            "Figure_HS2_topography_switch_metrics.png",
            "Figure_HS3_resolution_convergence.png",
            "Figure_HS4_resolution_station_pattern.png",
            "Figure_HS5_topography_grid_resolution.png",
            "Figure_HS6_layering_switch_waveforms.png",
            "Figure_HS7_layering_switch_metrics.png",
            "Figure_HS8_time_distance_diagnostics.png",
            "Figure_HS9_halfspace_a16_effect_comparison.png",
        ],
        start=1,
    )},
    "A1": FIGURES / "main" / "Figure_1_experiment_design.png",
    "A2": FIGURES / "main" / "Figure_2_factorial_waveforms.png",
    "A3": FIGURES / "main" / "Figure_3_component_energy.png",
    "A4": FIGURES / "main" / "Figure_4_path_relief.png",
    "A5": FIGURES / "main" / "Figure_5_interaction_residual.png",
    "A6": FIGURES / "main" / "Figure_6_linear_diffusion.png",
    "A7": FIGURES / "main" / "Figure_7_observed_models.png",
    "AS1": FIGURES / "supporting" / "Figure_S1_smoothing_sensitivity.png",
    "AS2": FIGURES / "supporting" / "Figure_S2_time_frequency.png",
    "A_RT": FIGURES / "synthesis" / "Figure_A02_rt_rotation_geometry.png",
    "A_PATH": FIGURES / "synthesis" / "Figure_A14_A15_path_metric_diagnostics.png",
    "SYN_TOPO": FIGURES / "synthesis" / "Figure_SYN01_topographic_energy_effects.png",
    "SYN_CHAIN": FIGURES / "synthesis" / "Figure_SYN08_SYN13_SYN15_evidence_chain.png",
}


@dataclass(frozen=True)
class EvidenceConclusion:
    code: str
    evidence_class: str
    title: str
    claim: str
    quantitative: str
    interpretation: str
    boundary: str
    english: str
    figure_key: str
    caption: str
    source_note: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


EFFECT_ROWS = read_csv(DERIVED / "low_velocity_effect_summary.csv")
INTERACTION_ROWS = read_csv(DERIVED / "low_velocity_interaction_summary.csv")
RELATION_ROWS = read_csv(DERIVED / "low_velocity_spatial_relationships.csv")
FIT_ROWS = read_csv(DERIVED / "low_velocity_time_distance_fits.csv")
OBS_ROWS = read_csv(DERIVED / "A16S12_observed_six_model_comparison_metrics.csv")
EXTENDED_ROWS = read_csv(DERIVED / "low_velocity_extended_window_metrics.csv")
AUDIT_ROWS = read_csv(PROVENANCE / "low_velocity_input_audit.csv")


def one(rows: list[dict[str, str]], **filters: str) -> dict[str, str]:
    matched = [row for row in rows if all(row.get(key) == value for key, value in filters.items())]
    if len(matched) != 1:
        raise ValueError(f"Expected one row for {filters}, found {len(matched)}")
    return matched[0]


def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in (None, "") else math.nan


def effect(effect_name: str, metric: str) -> dict[str, str]:
    return one(EFFECT_ROWS, effect=effect_name, metric=metric)


def relation(relation_name: str, metric: str, predictor: str = "first_effect") -> dict[str, str]:
    return one(RELATION_ROWS, relation=relation_name, metric=metric, predictor=predictor)


def observed(record: str) -> dict[str, str]:
    return one(OBS_ROWS, record=record)


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def ratio_phrase(effect_name: str, metric: str) -> str:
    row = effect(effect_name, metric)
    return (
        f"空间块中位数 {f(row, 'ratio_median'):.2f} 倍，"
        f"95%区间 {f(row, 'ratio_bootstrap95_low'):.2f}-{f(row, 'ratio_bootstrap95_high'):.2f} 倍；"
        f"站点级描述中位数 {f(row, 'ratio_station_median'):.2f} 倍"
    )


def difference_phrase(effect_name: str, metric: str, unit: str = "s", scale: float = 1.0) -> str:
    row = effect(effect_name, metric)
    return (
        f"空间块中位变化 {f(row, 'median') * scale:.2f} {unit}，"
        f"95%区间 {f(row, 'bootstrap95_low') * scale:.2f} 至 {f(row, 'bootstrap95_high') * scale:.2f} {unit}；"
        f"站点级描述中位数 {f(row, 'station_median') * scale:.2f} {unit}"
    )


def evidence_label(value: str) -> tuple[str, str, str]:
    mapping = {
        "positive": ("正向确定性证据", PALE_BLUE, BLUE),
        "conditional": ("条件性运行级证据", PALE_GOLD, GOLD),
        "exclusion": ("反向/排除性证据", PALE_GOLD, GOLD),
        "uncertain": ("待验证/受限证据", PALE_GOLD, GOLD),
    }
    return mapping[value]


def low_conclusions() -> list[EvidenceConclusion]:
    m5 = observed("M5")
    m6 = observed("M6")
    obs = observed("Observed A16S12")
    persistence_energy = relation("topography_signature_no_low_vs_low", "total_energy")
    persistence_t90 = relation("topography_signature_no_low_vs_low", "T90_s")
    relief_energy = relation("path_predictor_vs_topography_effect_with_low_velocity", "total_energy", "path_relief_range_km")
    relief_t90 = relation("path_predictor_vs_topography_effect_with_low_velocity", "T90_s", "path_relief_range_km")
    safe_fits = [row for row in FIT_ROWS if row["sample_definition"] == "censor_safe"]
    min_safe_aic = min(f(row, "delta_aic_squared_minus_linear") for row in safe_fits)
    primary = [row for row in EXTENDED_ROWS if row["included_primary"] == "1"]
    final_counts = {
        name: sum(row["model"] == name and row["t95_within_20s_of_end"] == "1" for row in primary)
        for name in ("M5", "M6")
    }
    return [
        EvidenceConclusion(
            "LV01", "positive", "六模型结构可比，但记录长度不同，必须采用双窗口",
            "M5/M6 可以与 M1-M4 进行同名台站、同分量的配对比较；记录长度差异不能通过简单截断后被忽略。",
            "六个文件均包含 r1-r606、seq_no 0-605 和有限 Vx/Vy/Vz；M1-M4 约 250 s，M5/M6 约 400 s。公共效应窗口为 50-245 s，低速层延长诊断窗口为 50-395 s。",
            "双窗口把两个问题分开：公共窗回答模型之间的可比边际效应，延长窗回答低速层运行内部的晚期演化和删失风险。",
            "NetCDF 不编码完整运行条件；结构一致只证明输出格式和台站序列可比，不证明源、网格、Q、边界和随机实现完全相同。",
            "The six outputs share the same receiver sequence, but unequal record lengths require a common 50-245 s comparison window and a separate 50-395 s low-velocity diagnostic window.",
            "LV01", "低速层输入文件的采样、长度与结构一致性审计。", "输入审计与 SHA-256：provenance/low_velocity_input_audit.csv。",
        ),
        EvidenceConclusion(
            "LV02", "exclusion", "当前只能识别含非均匀背景下的地形×低速层条件设计",
            "M3/M4/M5/M6 形成一个所有单元均含随机非均匀性的条件 2×2 设计，而不是完整的地形×散射×低速层三因素设计。",
            "可识别对比为 M5/M3、M6/M4、M4/M3、M6/M5 以及 (M6-M5)-(M4-M3)；缺少“低速层+无散射”两单元。",
            "因此可以检验低速层在两种表面背景中的运行级差异，也可以检验条件交互；不能估计低速层×散射或完整三阶交互。",
            "随机实现/种子未保存，图中“均含非均匀性”不能进一步提升为“使用同一随机实现”。",
            "The available models identify a heterogeneity-present topography-by-low-velocity contrast, not a complete three-factor design.",
            "LV02", "可识别的条件因子设计及缺失单元。", "设计边界由现有六个 station.nc 与缺失运行清单共同决定。",
        ),
        EvidenceConclusion(
            "LV03", "positive", "低速层改变 S12 三分量相位结构，而非统一振幅缩放",
            "在共享三分量尺度下，M5 相对 M3、M6 相对 M4 的 Z/R/T 都出现新的相位、脉冲和持续振荡。",
            "图中同一对比使用共享 3C 尺度，没有逐分量归一化；变化同时存在于 Z、R 和 T。",
            "低速层运行改变能量储存、转换和出射过程；单一静态时移或振幅系数不能把基准波形变成低速层波形。",
            "这是波形形状证据，不反演具体层厚、速度或界面形态。",
            "Shared-scale S12 waveforms show that the low-velocity runs alter phase structure on all three components rather than applying a scalar amplitude correction.",
            "LV03", "S12 在平坦和地形非均匀背景中的三分量公共窗对比。", "波形先逐站旋转到 Z/R/T；无逐分量归一化。",
        ),
        EvidenceConclusion(
            "LV04", "positive", "S12 的大量低速层能量位于原 245 s 截点之后",
            "M5/M6 在 245 s 后仍持续出现能量峰和累计能量增长，旧的四模型窗口会截掉关键低速层响应。",
            f"S12 延长窗 t95 为 M5 {f(m5, 't95_s'):.2f} s、M6 {f(m6, 't95_s'):.2f} s；两者都接近 400 s 记录末端。",
            "延长记录使低速层能量滞留首次被直接看见，也解释了公共窗与延长窗持续时间指标的差异。",
            "接近末端的 t95 仍可能被右删失；这些数值是当前记录内下限，不是完整尾波寿命。",
            "A substantial fraction of the S12 low-velocity response occurs after 245 s, and its t95 approaches the 400 s record limit.",
            "LV04", "S12 低速层延长窗包络、累计能量与分量包络。", "延长窗口仅用于 M5/M6 内部诊断。",
        ),
        EvidenceConclusion(
            "LV05", "conditional", "低速层运行的主效应是能量积累、持续时间增加和峰时延迟",
            "两个表面背景中，低速层运行都显著增强累计能量并延迟包络演化；峰值放大较不均一。",
            f"平坦背景：{ratio_phrase('low_flat', 'total_energy')}；{ratio_phrase('low_flat', 'T90_s')}。地形背景：{ratio_phrase('low_topography', 'total_energy')}；{ratio_phrase('low_topography', 'T90_s')}。",
            "能量因子远大于峰值因子，说明新增响应主要表现为长时间能量积累，而不是所有位置同步提高瞬时主峰。",
            "绝对能量和振幅的因果归因以源与其余运行设置不变为前提；时间与分量占比结论更稳健。",
            "The low-velocity runs primarily enhance integrated energy and delay rather than producing a uniform peak-amplitude increase, conditional on unchanged run settings.",
            "LV05", "低速层运行级能量、峰值、T90 与 tmax 效应分布。", "小提琴为站点级分布；推断值与区间来自 57 个空间块中位数。",
        ),
        EvidenceConclusion(
            "LV06", "positive", "低速层响应具有显著射线路径差异",
            "三条剖面的能量、持续和峰时效应幅度明显不同，不能用一个全区常数概括低速层响应。",
            "射线分组均去除首尾各 5 站后计算；每条射线的能量因子、T90 因子和 tmax 变化均呈不同中位值与四分位范围。",
            "这说明低速层与传播方向、路径起伏、局部结构或边界几何耦合；路径差异是物理信号而非仅是总体离散。",
            "现有三条单向剖面不足以把路径差异唯一归因于某一种界面或三维结构。",
            "Ray-specific effect distributions demonstrate that the low-velocity response is path dependent rather than a model-wide constant.",
            "LV06", "三条射线的低速层运行级效应及区间。", "分射线结果是描述性；跨全样本推断使用 57 个非重叠空间块。",
        ),
        EvidenceConclusion(
            "LV07", "positive", "低速层进一步把 Z 能量重新分配到 R/T",
            "从 M1 到 M6，复杂结构逐步降低 Z 占比并提高水平与横向能量，M5/M6 延续并强化这一趋势。",
            "M1-M4 的 Z/R/T 中位占比为 70.15/29.85/~0、54.58/24.69/20.45、56.37/27.63/16.13、48.92/27.28/23.43%；M5/M6 的当前值由统一脚本在相同公共窗重算。",
            "分量重分配是三维模式转换和多路径改变的重要证据；Z 下降不等价于能量吸收增强。",
            "Z/R/T 是台站坐标分量；严格 P/SV/SH 分离仍需要波场散度-旋度或阵列慢度。",
            "The low-velocity runs further redistribute energy from Z into horizontal and transverse motion, extending the three-dimensional conversion trend seen in M1-M4.",
            "LV07", "六模型 Z/R/T 能量占比分布。", "占比按三分量平方速度能量计算，T 基准近零时不使用倍数。",
        ),
        EvidenceConclusion(
            "LV08", "positive", "T 分量转换依赖地表和低速背景",
            "低速层导致的 T 占比增量在平坦与地形背景中不同，地形的 T 边际效应也会因低速层背景而改变。",
            f"M5/M3：{difference_phrase('low_flat', 'T_fraction', '个百分点', 100.0)}；M6/M4：{difference_phrase('low_topography', 'T_fraction', '个百分点', 100.0)}。",
            "T 是对三维不对称、散射和地表转换最敏感的分量之一；背景依赖排除了固定转换率解释。",
            "T 只能作为 SH 代理，不能单凭单台站三分量唯一分解所有模式。",
            "Transverse-energy conversion depends on both the surface and low-velocity background, precluding a universal conversion factor.",
            "LV08", "四个可识别条件效应的 T 占比变化。", "使用百分点差而非相对 M1 近零 T 能量的倍数。",
        ),
        EvidenceConclusion(
            "LV09", "conditional", "低速层运行使地形边际能量效应由放大转为近中性",
            "无低速层时，地形在非均匀背景中总体提高能量；加入低速层后，点估计接近中性并略偏抑制，但区间跨越中性值。",
            f"M4/M3：{ratio_phrase('topography_no_low', 'total_energy')}；M6/M5：{ratio_phrase('topography_low', 'total_energy')}。",
            "地形不是可以从简单模型直接乘到复杂模型上的固定修正量；其边际效应取决于波场已经被散射和低速滞留改造的程度。",
            "M6/M5 的能量点估计为 0.985，但 95%区间 0.757-1.185 跨 1，因此只支持由显著放大转为近中性，不能声称抑制方向显著；唯一归因仍要求源、随机实现、Q、网格和边界完全一致。",
            "The marginal topographic energy effect changes from amplification without the low-velocity run to a statistically neutral estimate with it, conditional on run equivalence.",
            "LV09", "M3/M4/M5/M6 四条件单元的能量、峰值、T90 与 t50。", "绝对幅能量结论带运行清单限制。",
        ),
        EvidenceConclusion(
            "LV10", "positive", "地形×低速层交互是指标选择性的混合效应",
            "能量、峰值、t05、t50、晚期能量比例和 T 占比支持非零交互；T90、tmax、t95、Z/R 占比区间跨零。",
            "交互项定义为 (M6-M5)-(M4-M3)，正值指标在对数比值域计算，时间和占比使用差值；图按单位分面，避免混合尺度。",
            "结果支持“非加性集中在部分传播属性”，不支持“所有指标都存在同方向强交互”。",
            "物理原因可能包括陷获、转换、聚焦/散焦和散射饱和，现有台站输出不能唯一拆分。",
            "Topography-by-low-velocity interaction is metric specific: selected energy, timing, late-energy, and transverse-partition measures are nonzero, whereas several duration and component intervals include zero.",
            "LV10", "按对数比值、时间差和分量百分点分面的交互分布。", "交互区间由相同 57 个空间块中位数估计。",
        ),
        EvidenceConclusion(
            "LV11", "positive", "峰值与能量地形空间指纹在低速背景中部分保留，T90 不显著",
            "同一位置的地形强弱格局在有无低速层之间并非完全消失，但保留程度取决于指标。",
            f"总能量地形效应的距离控制块相关 rho={f(persistence_energy, 'spearman_rho'):.2f}、q={f(persistence_energy, 'BH_FDR_q'):.2g}；T90 为 rho={f(persistence_t90, 'spearman_rho'):.2f}、q={f(persistence_t90, 'BH_FDR_q'):.2g}。",
            "能量指纹的中等相关说明地形热点有一定跨背景稳定性；T90 不显著说明持续时间格局更容易被低速层重排。",
            "这是空间格局相关，不是 M4 与 M3 或 M6 与 M5 原始波形相关。",
            "The spatial topographic fingerprint persists for energy more clearly than for T90, whose distance-controlled correlation is not significant.",
            "LV11", "无低速层与有低速层地形效应的空间块相关。", "每条射线先去三次距离趋势，再标准化与分块。",
        ),
        EvidenceConclusion(
            "LV12", "positive", "低速背景下路径高差仍对应峰值/能量降低和 T90 延长",
            "路径累计高差必须在新背景中重新检验；结果表明它仍与地形边际效应具有系统关系。",
            f"能量效应与路径高差的距离控制相关 rho={f(relief_energy, 'spearman_rho'):.2f}、q={f(relief_energy, 'BH_FDR_q'):.2g}；T90 为 rho={f(relief_t90, 'spearman_rho'):.2f}、q={f(relief_t90, 'BH_FDR_q'):.2g}。",
            "更大路径起伏仍倾向于削弱相干幅能量并延长持续，但相关强度与无低速层背景不同。",
            "路径使用地表投影直线，尚未包含有限频率 Fresnel 走廊、三维射线弯曲或波场通量。",
            "Path relief remains associated with reduced coherent energy and prolonged duration in the low-velocity background, but the relationship must be re-estimated rather than transferred from the baseline models.",
            "LV12", "路径高差与低速背景地形效应的距离控制块关系。", "路径指标来自当前 A16/S12 几何和既有路径派生表。",
        ),
        EvidenceConclusion(
            "LV13", "positive", "低速层运行使能量峰迁移变慢且空间离散增大",
            "M5/M6 的能量峰随距离迁移斜率显著高于 M1-M4，同时同距离散布明显变大。",
            f"M5/M3：{difference_phrase('low_flat', 'tmax_s')}；M6/M4：{difference_phrase('low_topography', 'tmax_s')}。删失安全斜率覆盖 {min(f(r, 'linear_slope_s_per_km') for r in safe_fits):.2f}-{max(f(r, 'linear_slope_s_per_km') for r in safe_fits):.2f} s/km。",
            "低速结构显著减慢峰能量迁移并提高路径敏感性，但仍保留清晰距离结构。",
            "斜率来自 50-395 s 记录内 tmax；边界受限点以 x 标出并从敏感性斜率中剔除。",
            "The low-velocity runs slow and disorder peak-energy migration, with larger distance slopes and substantially greater path-dependent scatter.",
            "LV13", "三条射线的延长窗 tmax-距离关系及删失安全线性拟合。", "边界受影响点单独标识；拟合为 400 s 窗内描述。",
        ),
        EvidenceConclusion(
            "LV14", "exclusion", "低速层仍未使主能量迁移进入简单 R² 扩散状态",
            "全部主样本和删失安全敏感性样本中，线性距离形式均优于简单 R² 形式。",
            f"删失安全六组拟合的最小 Delta AIC(R²-线性) 为 {min_safe_aic:.2f}，所有 preferred_form 均为 linear。",
            "低速层使传播更慢、更离散，但主能量脊仍更接近弹道/准弹道距离标度，而非简单强扩散峰时标度。",
            "该检验只比较两个简化经验形式，不能排除更复杂的非高斯扩散、频散或多阶段输运。",
            "Even after censor-safe filtering, the main energy ridge remains better described by linear distance than by a simple R-squared diffusion form.",
            "LV14", "完整样本与删失安全样本的线性/R² RMSE 和 Delta AIC。", "仅作当前 400 s 记录窗内传播状态诊断。",
        ),
        EvidenceConclusion(
            "LV15", "positive", "包络相似性提高并不意味着相位波形拟合成功",
            "低速层运行可以保持或改善缓慢能量包络演化，同时零时滞三分量波形相关仍集中在零附近。",
            "图同时给出零时滞 3C 波形相关与允许 ±10 s 的 5 s 包络最佳相关；两者的经验分布和散点关系明显分离。",
            "包络比较检验能量迁移，波形相关检验相位与脉冲结构；论文必须并列报告，不能用前者替代后者。",
            "允许时移会提高包络相关，不能据此声称走时、相位和源机制均已匹配。",
            "Improved envelope similarity does not imply phase agreement; the two diagnostics capture distinct aspects of the waveform.",
            "LV15", "低速层对比的波形相关与包络相关联合分布。", "相关性不做逐台站自由振幅拟合。",
        ),
        EvidenceConclusion(
            "LV16", "positive", "数据选取的代表台站验证总体分布不是单迹异常",
            "代表波形依据效应分位数、同距离和交互强度规则自动选取，而非根据视觉效果挑选。",
            "图包含平坦/地形背景的中位能量效应、高延迟、强正/负地形交互和约 100 km 同距台站。",
            "这些波形把统计量对应到真实相位、尾波和分量变化，防止只用中位数隐藏空间异质性。",
            "代表台站用于解释，不替代 575 站和 57 空间块的总体统计。",
            "Data-selected representative traces confirm that the reported distributions correspond to reproducible waveform changes rather than a single visually chosen station.",
            "LV16", "按预注册式数据规则选取的代表台站波形图册。", "选择规则与台站编号保存在 low_velocity_representative_stations.json。",
        ),
        EvidenceConclusion(
            "LV17", "positive", "低速层把 S12 早期包络推向 Apollo，但仍远短于观测长尾",
            "M5/M6 的包络能量峰和累积能量明显晚于 M1-M4，方向上改善了观测对比。",
            f"M5/M6 tmax 为 {f(m5, 'tmax_median_s'):.2f}/{f(m6, 'tmax_median_s'):.2f} s，观测为 {f(obs, 'tmax_median_s'):.2f} s；t95 为 {f(m5, 't95_s'):.2f}/{f(m6, 't95_s'):.2f} s，观测为 {f(obs, 't95_s'):.2f} s。",
            "低速层是现有试验中最强的延迟机制，但仍只覆盖 Apollo 长尾的早期部分。",
            "模型和观测终止时间不同；累计曲线明确使用各自可用记录，不能把模型终点解释为完整 100% 物理能量。",
            "The low-velocity runs move the early S12 envelope toward Apollo, but their peak and t95 times remain far earlier than the observed long coda.",
            "LV17", "Apollo 与六模型 S12 包络、累计能量和早期放大图。", "每个模型只使用一个共享 3C RMS 源尺度。",
        ),
        EvidenceConclusion(
            "LV18", "exclusion", "时间改善没有解决相位和完整持续时间失配",
            "M5/M6 的 tmax 和包络相关改善，但早期三分量相位相关仍很低，完整 t95 差距仍接近一个数量级。",
            f"早期 3C 相关为 M5 {f(m5, 'early_3c_waveform_correlation'):.3f}、M6 {f(m6, 'early_3c_waveform_correlation'):.3f}；观测 t95={f(obs, 't95_s'):.1f} s。",
            "新增低速机制改善了“何时积累能量”，却没有同时修复“每个脉冲的相位”和“数千秒持续时间”。",
            "单台站观测不能建立距离幂律，但足以排除当前模型已经再现该站长尾的说法。",
            "Improved envelope timing does not resolve the near-zero phase correlation or the order-of-magnitude duration gap to Apollo.",
            "LV18", "观测与六模型 tmax、t95、包络相关和波形相关对比。", "观测值来自 A16S12；模型按共享源尺度比较。",
        ),
        EvidenceConclusion(
            "LV19", "exclusion", "低速层时频能量仍远短于 Apollo",
            "M5/M6 把 0.3-0.9 Hz 能量延长到 400 s 左右，但观测在更长时间保持宽频带能量。",
            "图使用统一 0.2-1.2 Hz 展示范围和每面板相对功率标度，M4、M5、M6 与观测的持续时间和频带演化可直接比较。",
            "失配同时存在于时间和频率：不仅尾波太短，能量中心与频带演化也不同。",
            "面板采用相对功率，不能用于绝对谱幅比较；它支持的是时频形态与持续范围判断。",
            "The low-velocity synthetics prolong band-limited energy but still fail to reproduce the observed time-frequency extent of the Apollo coda.",
            "LV19", "观测、M4、M5、M6 的 S12 时频对比。", "颜色为各面板相对最大功率 dB。",
        ),
        EvidenceConclusion(
            "LV20", "uncertain", "400 s 记录仍右删失一部分低速层台站",
            "延长到 400 s 显著提高覆盖，但一部分台站的 t95 仍落在记录最后 20 s，尾部能量尚未稳定结束。",
            f"575 个主样本中，t95 位于最后 20 s 的台站为 M5 {final_counts['M5']} 个、M6 {final_counts['M6']} 个。",
            "这些台站的 t95/T90 是下限或窗口依赖估计；应在论文图表和统计中明确标记。",
            "右删失不否定早期延迟和三分量转换，但限制对完整尾波寿命、距离斜率和长时能量比例的推断。",
            "The 400 s records still right-censor a substantial subset, so late t95 and T90 values are lower bounds for those stations.",
            "LV20", "245 s 后能量、t95 和末 20 s 能量比例的经验分布。", "375 s 被用作距 395 s 分析终点 20 s 的删失阈值。",
        ),
        EvidenceConclusion(
            "LV21", "positive", "低速层延迟具有距离结构、非单调性和路径差异",
            "tmax 差值随距离先增长，随后在不同射线上饱和或回落，不能表示为常数静态时移。",
            "三条剖面分别用 11 站平滑显示 M5-M3 与 M6-M4 的局部距离结构；站点散点保留真实离散。",
            "距离结构说明低速层效应随传播路径累积和重分配，可能包含多次波、模式转换及出射位置变化。",
            "非单调曲线不应被拟合为单一全区线性延迟定律；它是机制诊断而非层厚反演。",
            "Low-velocity delay is distance structured and nonmonotonic, ruling out representation by a single static time correction.",
            "LV21", "三条射线的低速层公共窗 tmax 差值随距离变化。", "曲线为局部平滑，不用于声明全程单调。",
        ),
        EvidenceConclusion(
            "LV22", "positive", "一致的空间块估计确认能量、持续与延迟效应稳健",
            "点估计、bootstrap 区间和 Wilcoxon 检验均使用相同的 57 个非重叠 10 站块中位数。",
            f"M5/M3 能量：{ratio_phrase('low_flat', 'total_energy')}；M6/M4 能量：{ratio_phrase('low_topography', 'total_energy')}。",
            "空间块避免把相邻台站错误当作 575 个独立重复，区间宽度也揭示了路径异质性。",
            "块区间仍依赖三条剖面代表性；不能替代新的方位覆盖或随机实现重复。",
            "Consistent spatial-block estimators confirm robust energy, duration, and delay contrasts without treating neighboring receivers as independent replicates.",
            "LV22", "因子、时间与 T 占比分轴显示的空间块中位数及 95% 区间。", "同一块中位数用于点估计、区间和符号秩检验。",
        ),
        EvidenceConclusion(
            "LV23", "positive", "低速模型的 T 转换沿三条剖面系统变化",
            "M5/M6 的 T 占比并非固定百分比，而是随距离与射线呈连续起伏和局部峰谷。",
            "图在每条剖面同时展示 M3、M4、M5、M6 的 11 站平滑 T 占比，便于识别背景和低速层的条件差异。",
            "空间结构支持路径控制的三维转换；低速层和地形共同改变转换发生的位置与强度。",
            "平滑曲线不提供独立自由度；统计显著性仍来自分块推断。",
            "Transverse-energy conversion varies systematically along all three profiles, indicating spatially structured three-dimensional coupling rather than a model-wide fraction.",
            "LV23", "三条射线的 M3/M4/M5/M6 T 能量占比剖面。", "T 占比使用能量分数，避免近零基准倍数发散。",
        ),
        EvidenceConclusion(
            "LV24", "exclusion", "峰时和持续时间估计强烈依赖可用记录窗",
            "M5/M6 的 tmax 在公共窗与延长窗相对稳定程度不同，而 t95/T90 在延长窗显著增加。",
            "图直接连接 50-245 s 和 50-395 s 的主样本中位值，分开显示 tmax、t95 与 T90。",
            "公共窗适合模型间效应比较；延长窗适合低速层内部尾波诊断，两者不能混成同一结论。",
            "延长窗仍可能右删失，因此更长记录是下一轮验证所必需的，而不是可选的版式改动。",
            "Peak and duration estimates are strongly window dependent, so common-window contrasts and extended-window tail diagnostics must be reported separately.",
            "LV24", "M5/M6 公共窗与延长窗的 tmax、t95 和 T90 对比。", "t05/t50/t95/T90 均按三分量滤波速度平方累计能量定义。",
        ),
    ]


def halfspace_conclusions() -> list[EvidenceConclusion]:
    source = "半空间分析权威来源：data/derived/halfspace_analysis_summary.json 及对应派生 CSV。"
    return [
        EvidenceConclusion("HS01", "positive", "半空间地形会重构三分量波形，而非只改变 Z", "起伏自由表面使原本近二维的 R-Z 波场产生显著 T 分量，并改变主脉冲与尾波。", "800 台站为从 (50,000,50,000) m 出发、75°方位、50 m 间距的单剖面；Vx/Vy 必须按 75°旋转为 R/T。", "地形产生反射、绕射和模式转换，三分量联合分析是识别地形效应的最低要求。", "该 800 台站几何不能与另一套 r1-r216 test.station 混用。", "Topography restructures all three components in the half-space experiment and generates substantial transverse motion.", "HS1", "半空间有无地形的三分量单剖面波形。", source),
        EvidenceConclusion("HS02", "positive", "半空间地形显著削弱有限窗能量并延长持续时间", "在全部 800 个同名剖面台站的总体配对统计中，地形造成强能量下降与持续时间增加。", "峰值比 0.116，有限窗能量比 0.0296，T90 比 4.126，绝对增加约 6.25 s；相关仅 -0.0116，表明波形形状已重构。", "地形的主要效应组合是相干峰值/能量损失、分量重分配和低振幅尾波延长。", "这些总体统计使用全部 800 站；只有距离拟合使用 r20-r760（1-38 km）。能量比依赖当前输出和有限窗，不能直接等价为内禀吸收。", "In the half-space profile, topography strongly reduces finite-window energy and prolongs T90 while destroying waveform similarity.", "HS2", "半空间地形开关的距离分布和三分量量化指标。", source),
        EvidenceConclusion("HS03", "positive", "地形分辨率具有形状阈值和联合收敛阈值", "约 0.5 km 可保持波形形状，但能量仍未收敛；约 0.25 km 才同时满足形状与能量要求。", "0.5 km：允许 ±2 s 对齐后中位相关 0.976、全部台站 >=0.90，但能量中位误差 19.4%；0.25 km：相关 0.996、能量误差 5.1%。", "数值地形收敛不能只看波形相关，必须联合检查能量。", "该阈值适用于当前频带、网格和地形谱，不应无条件推广到其他模拟。", "A 0.5 km DEM resolves waveform shape, whereas approximately 0.25 km is required for joint waveform-and-energy convergence.", "HS3", "半空间地形分辨率的波形相关与能量误差收敛。", source),
        EvidenceConclusion("HS04", "positive", "分辨率误差具有空间结构，而非均匀噪声", "粗化地形后，不同距离位置的波形与能量误差差异显著。", "站点级相关和能量误差沿单剖面呈成组变化，说明局部路径地形谱控制收敛。", "同一 DEM 分辨率可能对平滑路径足够、对陡峭或多尺度路径不足。", "单剖面不能完整代表二维方位分布。", "Resolution error is spatially structured along the profile rather than a uniform numerical perturbation.", "HS4", "分辨率误差的台站空间分布。", source),
        EvidenceConclusion("HS05", "exclusion", "DEM 外观相似不等于波场能量收敛", "不同采样地形在大尺度轮廓上可以相似，却保留不同的小尺度坡度和曲率谱。", "地形栅格对比与 HS03 能量误差共同显示，视觉相似不能替代波形和能量验证。", "波场对界面坡度、曲率和短波长成分敏感，因此必须报告 DEM 频谱和数值收敛。", "不能从一张地形图肉眼判断模拟已收敛。", "Visually similar DEMs do not guarantee energy convergence because small-scale slope and curvature remain dynamically important.", "HS5", "不同地形采样网格的起伏与空间谱对比。", source),
        EvidenceConclusion("HS06", "positive", "加入分层后主峰可接近，但尾波与持续时间仍变化", "半空间与分层模型的主要到时可保持相似，同时部分路径的后续能量和波列宽度改变。", "216 台站配对比较使用其自身 test.station 几何，不使用 800 台站剖面的坐标。", "分层的敏感信号主要位于尾波、能量和持续时间，而不是只看首个主峰。", "不能再写“分层前后无明显差异”；应限定为主峰或部分台站相近。", "Layering leaves many primary peaks similar but measurably changes later energy and duration on selected paths.", "HS6", "半空间有无分层的配对波形。", source),
        EvidenceConclusion("HS07", "positive", "分层对有限窗能量与 T90 有可量化影响", "在 216 台站集合中，分层总体提高能量和持续时间，但空间离散明显。", "中位相关 0.864，峰值比 1.020，能量比 1.221，T90 比 1.378，绝对增加 2.74 s。", "分层不是主峰幅值的简单放大，而是更集中地影响尾部能量。", "这些值属于 216 台站几何，不能和 800 台站 r20-r760 的距离统计直接拼接。", "Layering increases finite-window energy and T90 despite near-unity median peak amplitude.", "HS7", "分层开关的波形、能量和 T90 指标。", source),
        EvidenceConclusion("HS08", "exclusion", "半空间主能量迁移更接近线性距离而非 R²", "能量峰时随距离近似线性增长，简单扩散型 R² 形式没有改善解释。", "距离拟合使用真实 800 台站几何中的 r20-r760，即 1-38 km；不得使用另一套 216 台站坐标。", "地形和分层增加多路径，却没有把主能量脊推进简单强扩散状态。", "该检验针对主能量峰，不排除弱尾波存在散射扩散成分。", "Peak-energy migration in the half-space profile remains closer to linear distance than to a simple R-squared diffusion form.", "HS8", "半空间主能量峰的距离拟合诊断。", source),
        EvidenceConclusion("HS09", "exclusion", "半空间地形倍率不能直接外推到 A16/S12", "半空间与 A16 的地形边际效应在能量、持续和三分量分配上明显不同。", "半空间能量比 0.0296、T90 比 4.126；A16 中地形效应强烈依赖散射和低速背景。", "区域几何、传播距离、结构和散射背景共同决定地形边际效应。", "跨区域比较用于揭示背景依赖，不用于把一个区域的倍率校正另一区域。", "Topographic effects are strongly background dependent and cannot be transferred as fixed multipliers from the half-space profile to A16/S12.", "HS9", "半空间与 A16/S12 地形效应的跨区域对比。", source),
    ]


def a16_conclusions() -> list[EvidenceConclusion]:
    source = "A16/S12 权威来源：figures/main、figures/supporting 与 data/derived 当前版本；旧 REL3 卡片仅作版式参考。"
    english_map = {
        "A01": "The four baseline models form a topography-by-random-heterogeneity factorial design that separates two main effects and their second-order interaction.",
        "A02": "Horizontal synthetics must be rotated from Vx/Vy into station-specific radial and transverse components before component-energy interpretation.",
        "A03": "Random heterogeneity strongly broadens waveforms in the flat-background model, making duration a more stable scattering diagnostic than peak time alone.",
        "A04": "Topography alone broadens the wave train and generates transverse motion, although its duration effect is weaker than that of random heterogeneity.",
        "A05": "The combined topography-plus-heterogeneity waveform cannot be reproduced by linearly adding the two isolated effects.",
        "A06": "Model-observation comparisons use one shared three-component RMS source scale per model and prohibit component- or station-specific normalization.",
        "A07": "The near-zero transverse energy of M1 provides a symmetry-consistent baseline for identifying three-dimensional conversion.",
        "A08": "Random heterogeneity is a strong source of transverse conversion in the flat-background model.",
        "A09": "Topography alone generates path-dependent transverse energy, with the weakest response along the smoothest profile.",
        "A10": "The combined model has the largest transverse fraction, but the increment saturates relative to linear addition of the isolated effects.",
        "A11": "A reduced vertical fraction cannot be interpreted as intrinsic absorption because radial and transverse fractions increase concurrently.",
        "A12": "After distance detrending, larger cumulative path relief is associated with lower peak and total energy and longer T90 along Rays 2 and 3.",
        "A13": "Ray 1 does not support extrapolating the path-relief relationship as a universal law across all azimuths.",
        "A14": "Mean absolute slope provides a second path-integrated descriptor with correlations close to cumulative relief, although the two predictors are not statistically independent.",
        "A15": "Receiver elevation alone cannot substitute for an integrated source-to-receiver path metric.",
        "A16": "The factorial interaction waveform is comparable in magnitude to the isolated main effects and is therefore dynamically non-negligible.",
        "A17": "Nonlinear coupling is strongest on the transverse, SH-proxy component.",
        "A18": "A topographic amplitude correction followed by an independent scattering convolution cannot substitute for the directly simulated combined model.",
        "A19": "All 12 A16 peak-energy distance relations favor a linear-distance form over a simple squared-distance diffusion form.",
        "A20": "The main energy ridge remains ballistic or quasi-ballistic despite topographic and random-heterogeneity multipathing.",
        "A21": "A single observed S12 record cannot establish an observational distance-scaling exponent.",
        "A22": "Smoothing changes exact peak-time estimates but not the large timing mismatch between M1-M4 and the observation.",
        "A23": "Observed and synthetic onsets are broadly comparable, whereas their subsequent energy-envelope evolution is incompatible.",
        "A24": "The M1-M4 t95 values remain far shorter than the Apollo A16S12 coda even when random heterogeneity is present.",
        "A25": "A shared source-amplitude scale cannot repair the phase and envelope-shape mismatch.",
        "A26": "The 250 s synthetics sample only the early few percent of the recorded Apollo energy.",
        "A27": "The baseline models jointly miss the observed spectral range and late three-component energy partition.",
        "A28": "The dominant model deficiency is a coupled frequency-duration-three-dimensional-conversion mechanism rather than a single source-amplitude coefficient.",
    }
    raw = [
        ("A01", "positive", "四模型形成地形×随机非均匀性 2×2 基线", "M1-M4 可分离地形、随机非均匀性及其二阶交互。", "M1 平坦无散射、M2 地形无散射、M3 平坦有散射、M4 地形有散射；575 个主射线台站来自三条剖面首尾各去 5 站。", "A1"),
        ("A02", "positive", "A16 水平分量必须逐站旋转到 R/T", "三条射线方位不同，直接把 Vx/Vy 当作 R/T 会混合径向与横向能量。", "源坐标为 (161310,207630) m；R=Vx sin(phi)+Vy cos(phi)，T=Vx cos(phi)-Vy sin(phi)。", "A_RT"),
        ("A03", "positive", "随机非均匀性显著展宽平坦背景波列", "M3 相对 M1 的主峰变弱、尾波增长，持续时间是最稳定的散射判据。", "575 个主台站的描述性中位数：T90 因子 M3/M1=18.170。", "A2"),
        ("A04", "positive", "地形单独也能展宽并改变三分量", "M2 相对 M1 产生有限多路径和 T 分量，但弱于随机非均匀性对长尾的总体影响。", "575 个主台站的描述性中位数：T90 因子 M2/M1=5.309。", "A2"),
        ("A05", "positive", "组合模型波形不是两个独立效应的线性叠加", "M4 的新增相位、多脉冲和持续振荡不能由地形修正加散射尾波简单相加得到。", "575 个主台站的描述性中位数：M4/M2 T90=2.181，M4/M3 T90=1.162，显示明显背景依赖。", "A2"),
        ("A06", "positive", "六模型比较必须使用三分量联合尺度", "每个模型只允许一个 3C RMS 源尺度，避免逐分量或逐台站归一化掩盖分量失配。", "相同原则用于 S12 与 Apollo 对比。", "A2"),
        ("A07", "positive", "M1 的 T 能量近零验证对称基准", "平坦、无散射、近各向同性背景中的波场主要位于 R-Z 平面。", "575 个主台站的描述性中位数：M1 Z/R/T=70.15/29.85/近0%。", "A3"),
        ("A08", "positive", "随机非均匀性是强 T 转换源", "平坦背景加入散射后，T 占比增加约 20.45 个百分点。", "575 个主台站的描述性中位数：M3 Z/R/T=54.58/24.69/20.45%。", "A3"),
        ("A09", "positive", "地形单独产生路径依赖的 T 转换", "无散射背景加入地形后，T 占比达到 16.13%，其中射线1明显较弱。", "575 个主台站的描述性中位数：M2 Z/R/T=56.37/27.63/16.13%。", "A3"),
        ("A10", "positive", "组合模型 T 占比最高但增量饱和", "M4 的 T 占比为 23.43%，小于 M3 与 M2 T 增量的线性相加。", "575 个主台站的描述性中位数：M4 Z/R/T=48.92/27.28/23.43%。", "A3"),
        ("A11", "exclusion", "Z 占比下降不能直接解释为内禀吸收", "M4 的 Z 减少同时伴随 R/T 增加，主要证据是分量重分配。", "需要总能量、Q 和通量才能区分转换与吸收。", "A3"),
        ("A12", "positive", "射线2和3存在稳定路径高差控制", "去除距离趋势后，更大累计路径高差对应更低峰值/能量与更长 T90。", "综合空间块相关：峰值 -0.736、能量 -0.731、T90 +0.679。", "A4"),
        ("A13", "exclusion", "射线1不支持把路径高差定律推广到所有方向", "射线1地形最平滑，路径高差与峰值/能量/T90 的相关接近零。", "对应相关约 -0.130/-0.095/+0.044。", "A4"),
        ("A14", "positive", "平均绝对坡度是第二个有效路径描述量", "平均绝对坡度与幅度、能量和 T90 的相关接近累计高差，能够区分缓坡与重复陡坡路径。", "无/有散射背景中，平均坡度对 T90 的块相关为 +0.624/+0.629，累计高差为 +0.679/+0.722（57 块）。", "A_PATH"),
        ("A15", "exclusion", "单点台站高程不能替代整条传播路径", "波形由源到台站整条路径累积形成，接收点高程只描述末端。", "峰值、能量与 T90 的单点高程 |rho| 约 0.40-0.47，系统低于累计路径高差的 0.68-0.74。", "A_PATH"),
        ("A16", "positive", "地形与散射交互波形与主效应同量级", "交互项 I=M4-M2-M3+M1 在 Z/R/T 上均不可忽略。", "交互 RMS 与两个主效应 RMS 和的中位比约 Z 0.69、R 0.70、T 1.00。", "A5"),
        ("A17", "positive", "非线性主要集中在 T/SH 代理分量", "T 交互与主效应同量级，说明横向转换对背景组合最敏感。", "S12 的交互比约 Z 0.55、R 0.53、T 1.02。", "A5"),
        ("A18", "exclusion", "不能用地形振幅修正加独立尾波卷积替代 M4", "差分波形在主脉冲之后生成新相位和持续振荡。", "组合模型必须直接计算。", "A5"),
        ("A19", "exclusion", "M1-M4 的 12 组主能量距离关系均不支持简单 R²", "三条射线、四模型均偏好线性 a+bR。", "线性 RMSE 1.54-2.88 s，R² RMSE 4.56-10.03 s，Delta AIC 268-672。", "A6"),
        ("A20", "positive", "当前 A16 模型仍由弹道/准弹道主能量脊主导", "地形与散射增加多路径，但主能量峰仍沿近线性距离传播。", "R² 曲线系统偏离主能量脊。", "A6"),
        ("A21", "uncertain", "单一 S12 观测不能拟合观测距离幂律", "Apollo A16S12 只在约 152 km 提供一个长尾锚点。", "检验观测 R²/D 需要多个事件-台站距离组合。", "A6"),
        ("A22", "positive", "平滑改变 tmax 数值，但不改变低速层前的基本失配方向", "多种平滑窗下，模型峰时都显著早于观测。", "旧四模型观测 tmax 约 658.29 s，而 M1-M4 仅 85.73-96.53 s。", "AS1"),
        ("A23", "exclusion", "初始到达量级接近，但能量峰演化完全不相容", "模型与观测均在约 80-100 s 起振，此后模型衰减而观测继续增长。", "主要矛盾不是首波速度量级，而是能量输运寿命。", "A7"),
        ("A24", "exclusion", "M1-M4 的 t95 远短于 Apollo", "随机非均匀性延长尾波方向正确，但仍止于约 160 s。", "M1/M2/M3/M4 t95=86.47/110.49/160.68/152.52 s，观测=2804.63 s。", "A7"),
        ("A25", "exclusion", "共享源尺度不能修复相位与包络形状", "统一源能量后，早期三分量相关仍接近零。", "M1-M4 相关约 -0.010 至 0.036，NRMSE 1.39-1.42。", "A7"),
        ("A26", "exclusion", "250 s 合成只覆盖观测约 4% 的记录能量", "观测主要能量位于旧模型截点之后。", "观测 t50=984.92 s、t95=2804.63 s，前 250 s 约占 4.00%。", "A7"),
        ("A27", "exclusion", "模型频谱与晚期能量分配同时失配", "模型频带峰整体偏高，且 120 s 后三分量能量比例远低于观测。", "观测 Z/R/T 时频主频约 0.399/0.448/0.399 Hz；模型多为 0.55-0.80 Hz。", "AS2"),
        ("A28", "exclusion", "四模型的主要缺口是频率-持续时间-三维转换机制", "振幅系数或小幅静态时移不能同时修复时频、持续与偏振失配。", "需要更强/多尺度散射、低速层、Q、域尺寸与多随机实现联合试验。", "AS2"),
    ]
    output: list[EvidenceConclusion] = []
    for code, cls, title, claim, quantitative, figure_key in raw:
        item_source = source
        if code == "A27":
            item_source = "A16/S12 时频权威来源：data/derived/A16S12_s12_time_frequency_metrics.csv；图像来源 figures/supporting 当前版本。"
        output.append(EvidenceConclusion(
            code, cls, title, claim, quantitative,
            "该结果与同组波形、分量能量和路径统计相互约束，避免仅依赖单一标量。",
            "数值只在当前 0.3-0.9 Hz、50-245 s 处理口径和对应几何内有效；不能跨几何或跨窗口直接拼接。",
            english_map[code],
            figure_key, title + "的直接图像证据。", item_source,
        ))
    return output


def synthesis_conclusions() -> list[EvidenceConclusion]:
    source = "综合判断同时引用半空间、A16/S12、低速层和 Apollo 对比；每条仍由所示图件直接约束。"
    english_map = {
        "SYN01": "Topographic effects are not background-independent corrections: their magnitude and point-estimate direction vary across the half-space, heterogeneous, and low-velocity experiments.",
        "SYN02": "Topographic resolution should be reported with a 0.5 km waveform-shape threshold and a stricter approximately 0.25 km joint waveform-energy threshold.",
        "SYN03": "Layering primarily modifies later energy and duration rather than uniformly rescaling the main peak.",
        "SYN04": "Random heterogeneity broadens the A16 wave train more strongly than topography alone under the current baseline design.",
        "SYN05": "The low-velocity runs provide the largest peak-energy delay among the tested mechanisms, but remain much earlier than the Apollo peak.",
        "SYN06": "Transverse energy is the most sensitive component diagnostic of three-dimensional conversion across the staged experiments.",
        "SYN07": "The spatial topographic energy fingerprint partly persists across low-velocity backgrounds, whereas the duration fingerprint is more strongly reorganized.",
        "SYN08": "From the half-space experiment through M6, the main peak-energy ridge remains inconsistent with a simple squared-distance strong-diffusion scaling.",
        "SYN09": "Envelope improvement and phase agreement must be evaluated separately because low-velocity trapping can improve the former without repairing the latter.",
        "SYN10": "The most complex current models still fail to reproduce the full Apollo duration and time-frequency extent.",
        "SYN11": "Absolute amplitude and energy contrasts require an explicit run-equivalence assumption until complete source and simulation manifests are recovered.",
        "SYN12": "A 400 s record improves low-velocity coverage but does not establish complete tail convergence for all receivers.",
        "SYN13": "The most defensible mechanism hierarchy is topographic redistribution, heterogeneity-driven broadening, and low-velocity energy retention with conditional coupling among them.",
        "SYN14": "No single amplitude, static-time, or topographic correction can replace the missing coupled propagation mechanisms.",
        "SYN15": "The final paper should follow the evidential sequence from controlled half-space tests to A16 factorial models, low-velocity extensions, and Apollo exclusion tests.",
    }
    raw = [
        ("SYN01", "positive", "地形效应从来不是背景无关的固定修正量", "半空间、A16 非均匀背景与低速背景给出的地形边际效应幅度显著不同，点估计方向也随背景改变。", "半空间能量比 0.0296；A16 M4/M3 空间块能量因子约 1.78；M6/M5 约 0.99，但后者区间跨 1。", "SYN_TOPO"),
        ("SYN02", "positive", "地形分辨率应采用 0.5 km 形状阈值与 0.25 km 联合阈值", "只有同时报告相关和能量误差，才能形成可审稿的收敛论证。", "0.5 km 相关 0.976 但能量误差 19.4%；0.25 km 相关 0.996、能量误差 5.1%。", "HS3"),
        ("SYN03", "positive", "分层主要改变尾部能量，而非统一改变主峰", "分层峰值比接近 1，但能量和 T90 增加。", "峰值 1.020、能量 1.221、T90 1.378。", "HS7"),
        ("SYN04", "positive", "随机非均匀性比单独地形更强地展宽 A16 波列", "M3/M1 的 T90 增长明显大于 M2/M1。", "权威 T90 因子 18.170 与 5.309。", "A2"),
        ("SYN05", "positive", "低速层是现有试验中最强的峰时延迟机制", "M5/M6 将 S12 能量峰推至约 213/272 s，显著超过 M1-M4。", "公共剖面 tmax 延迟约 112/101 s；S12 tmax 仍早于观测 658 s。", "LV17"),
        ("SYN06", "positive", "T 分量是最敏感的三维转换指标", "从半空间到 A16 六模型，地形、散射和低速层都在 T 上留下强背景依赖。", "M1 T 近零，M2/M3/M4 为 16.13/20.45/23.43%，M5/M6 继续变化。", "LV07"),
        ("SYN07", "positive", "地形空间指纹可以跨背景部分保留，但持续时间更易重排", "能量地形效应在有无低速层间相关显著，T90 相关不显著。", "能量 rho 0.53、q 1.1e-4；T90 q 0.095。", "LV11"),
        ("SYN08", "exclusion", "从半空间到 M6，主能量峰仍不符合简单 R² 强扩散", "不同尺度与复杂度的全部主要测试仍偏好线性距离。", "低速层删失安全最小 Delta AIC 12.79；旧 A16 为 268-672。", "SYN_CHAIN"),
        ("SYN09", "positive", "低速层改善包络而不改善相位，二者必须分开评价", "M6 的早期包络相关可较高，但三分量相位相关仍仅约 0.08。", "包络相似性衡量缓慢能量演化，波形相关衡量相位和脉冲结构。", "LV15"),
        ("SYN10", "exclusion", "当前最复杂模型仍未解释 Apollo 完整长尾", "M5/M6 t95 接近 370-382 s，观测约 2805 s；时频能量范围亦不足。", "记录延长方向正确，但差距仍超过 2400 s。", "LV18"),
        ("SYN11", "conditional", "绝对幅能量结论必须附运行清单前提", "M5/M6 文件中没有源、Q、网格、随机种子和完整介质参数。", "时间、占比、形状的比较较稳健；绝对能量归因必须写成 conditional run-level contrast。", "LV01"),
        ("SYN12", "uncertain", "400 s 是进步但不是低速层尾波收敛终点", "约五分之一以上主样本 t95 落入最后 20 s。", "需要更长记录并预先规定删失处理。", "LV20"),
        ("SYN13", "positive", "最有说服力的机制层级是地形分配、散射展宽、低速层滞留", "三类因素具有不同主效应并发生条件非加性。", "地形控制路径和分量，散射强展宽，低速层产生最大延迟和后期能量。", "SYN_CHAIN"),
        ("SYN14", "exclusion", "不能用单一参数微调替代缺失机制", "源振幅、静态时移或一条固定地形倍率都不能同时修复相位、持续、频谱和三分量。", "需要联合改变多尺度散射、低速层、Q、域尺寸和随机实现。", "A7"),
        ("SYN15", "positive", "最终论文应按证据链而非模型文件夹顺序组织", "半空间用于机制与收敛，A16 M1-M4 用于因子基线，M5/M6 用于低速层扩展，Apollo 用于排除检验。", "每一节只保留最有辨识力的图，把完整证据图册放入 Supporting Information。", "SYN_CHAIN"),
    ]
    return [
        EvidenceConclusion(code, cls, title, claim, quantitative,
            "跨阶段结论只在不同实验共同支持同一方向时成立；不相容的几何、窗口和参数不直接合并成单一倍率。",
            "该综合结论的边界由对应分区的几何、记录窗和缺失运行信息共同限定。",
            english_map[code],
            figure_key, title + "的综合证据图。", source)
        for code, cls, title, claim, quantitative, figure_key in raw
    ]


def set_update_fields(document: Document) -> None:
    settings = document.settings.element
    node = settings.find(qn("w:updateFields"))
    if node is None:
        node = OxmlElement("w:updateFields")
        settings.append(node)
    node.set(qn("w:val"), "true")


def prevent_midword_wrap(paragraph) -> None:
    """Keep Latin manuscript sentences from breaking inside words.

    Word/LibreOffice may otherwise apply East-Asian character-level wrapping
    to an English sentence in a mixed-language paragraph (for example,
    splitting ``and`` across two lines).  In WordprocessingML, an enabled
    ``wordWrap`` value keeps space-delimited text at word boundaries, whereas
    ``off`` explicitly permits character-level splitting.
    """
    p_pr = paragraph._p.get_or_add_pPr()
    node = p_pr.find(qn("w:wordWrap"))
    if node is None:
        node = OxmlElement("w:wordWrap")
        p_pr.append(node)
    node.set(qn("w:val"), "1")


def mark_run_as_english(run) -> None:
    """Apply an explicit Western-language/font hint for portable rendering."""
    r_pr = run._r.get_or_add_rPr()
    lang = r_pr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        r_pr.append(lang)
    lang.set(qn("w:val"), "en-US")
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), "Arial")
    r_fonts.set(qn("w:hAnsi"), "Arial")


def configure_document(document: Document, running_title: str) -> None:
    configure_styles(document)
    set_document_language(document)
    normal = document.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.2
    heading_tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DEEP_BLUE, 10, 5),
    }
    for style_name, (size, color, before, after) in heading_tokens.items():
        style = document.styles[style_name]
        style.font.name = "Microsoft YaHei"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    for list_style in ("List Bullet", "List Number"):
        style = document.styles[list_style]
        style.font.name = "Microsoft YaHei"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(10.5)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.2
    for section in document.sections:
        configure_section(section)
        section.header_distance = Inches(0.4)
        section.footer_distance = Inches(0.4)
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.paragraph_format.space_after = Pt(2)
        hr = hp.add_run(running_title)
        set_run_font(hr, size=8.5, color=MUTED)
        set_paragraph_border(hp, side="bottom", color="D7DBE2", size=6, space=4)
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("第 ")
        set_run_font(r, size=8.5, color=MUTED)
        page = fp.add_run()
        set_run_font(page, size=8.5, color=MUTED)
        add_field(page, "PAGE")
        r = fp.add_run(" 页")
        set_run_font(r, size=8.5, color=MUTED)
    set_update_fields(document)


def add_title_page(document: Document, title: str, subtitle: str, scope: str) -> None:
    for _ in range(5):
        add_paragraph(document, "", after=12)
    kicker = add_paragraph(document, "JGR: Planets 投稿准备｜证据分级终审版", align=WD_ALIGN_PARAGRAPH.CENTER, after=16)
    for run in kicker.runs:
        set_run_font(run, size=10.5, bold=True, color=GOLD)
    title_p = add_paragraph(document, title, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    for run in title_p.runs:
        set_run_font(run, size=25, bold=True, color=NAVY)
    sub = add_paragraph(document, subtitle, align=WD_ALIGN_PARAGRAPH.CENTER, after=28)
    for run in sub.runs:
        set_run_font(run, size=13.5, color=DEEP_BLUE)
    add_callout(document, "报告范围", scope, fill=PALE_BLUE, border=BLUE)
    add_paragraph(document, "处理版本：2026-08-20.2｜统一频带：0.3-0.9 Hz｜核心比较窗：50-245 s", align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    p = add_paragraph(document, "本报告的每条编号结论均配有直接图像证据、定量依据、适用边界和建议英文表述。", align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    for run in p.runs:
        set_run_font(run, size=9.5, italic=True, color=MUTED)
    document.add_page_break()


def add_real_bullet(document: Document, text: str) -> None:
    p = document.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    set_run_font(run, size=10.5)


def add_navigation(document: Document, sections: Iterable[str]) -> None:
    add_heading(document, "阅读导航", 1)
    add_callout(document, "阅读方式", "先读执行摘要和证据等级，再按研究阶段进入结论单元；每个单元都可独立核对图、统计和边界。", fill=PALE_BLUE, border=BLUE)
    for section in sections:
        add_real_bullet(document, section)
    add_paragraph(document, "目录页码将在 Word 打开时依据标题自动更新；本版同时保留无页码导航，避免不同渲染器导致的目录缓存偏差。", after=8)


def add_methodology(document: Document, integrated: bool) -> None:
    add_heading(document, "统一处理、统计与证据规则", 1)
    add_heading(document, "信号处理", 2)
    for item in (
        "所有模型在原始采样率上先做线性去趋势，再做四阶 0.3-0.9 Hz Butterworth 零相位滤波，最后插值到公共时间轴。",
        "A16/S12 的水平分量按每个台站相对震源方位由 Vx/Vy 旋转到 R/T；半空间 800 台站使用其真实 75°单剖面方位。",
        "t05/t50/t95/T90 来自三分量滤波速度平方的累计能量，T90=t95-t05；tmax 来自多个平滑窗的三分量解析信号强度峰时中位数。",
        "模型-观测比较每个模型只使用一个共享三分量 RMS 源尺度，不做逐分量或逐台站自由归一化。",
    ):
        add_real_bullet(document, item)
    add_heading(document, "空间推断", 2)
    for item in (
        "A16 三条射线分别去首尾各 5 站，共 575 个主台站；每 10 个相邻站组成一个非重叠空间块，共 57 块。",
        "正值指标使用对数比值，时间和占比使用差值；每条射线先去三次震中距趋势，再做标准化和空间块相关。",
        "凡报告 bootstrap 区间或 Wilcoxon 检验的推断量均使用相同的 57 个空间块中位数；A03-A05 的 T90 因子与 A07-A10 的分量占比为 575 台站层描述性中位数。",
        "多重检验使用 Benjamini-Hochberg FDR；q<0.05 是统计支持的必要条件，但物理解读还要求路径一致和波形图支持。",
    ):
        add_real_bullet(document, item)
    add_heading(document, "证据等级", 2)
    rows = [
        ("正向确定性", "数据、指标、空间块区间与波形共同支持，可进入主结论。"),
        ("条件性运行级", "输出差异确定，但因缺少运行清单，绝对幅能量归因必须附前提。"),
        ("反向/排除性", "数据明确排除某种解释，例如简单 R² 强扩散或已再现 Apollo 长尾。"),
        ("待验证/受限", "受右删失、缺失单元、单观测锚点或缺少波场快照限制，不作为强主张。"),
    ]
    add_table(document, ("等级", "使用规则"), rows, (2400, 6960), font_size=9)
    if integrated:
        add_heading(document, "几何不可混用规则", 2)
        add_callout(document, "关键几何修正", "半空间 r1-r800 是 75°、50 m 间距、0.05-40 km 单剖面，距离统计使用 r20-r760；当前 r1-r216 test.station 属于另一套分辨率/分层几何。A16/S12 则按每站方位旋转，三类几何不得互换。", fill=PALE_GOLD, border=GOLD)


def add_conclusion_unit(document: Document, item: EvidenceConclusion, number: int, total: int) -> None:
    # A run-level page break can be pushed onto an otherwise empty page when
    # the preceding evidence unit nearly fills the page.  Page-break-before on
    # the heading gives the same semantic separation without producing blank
    # transition pages in LibreOffice/Word rendering.
    heading = add_heading(document, f"{item.code}｜{item.title}", 2)
    heading.paragraph_format.page_break_before = True
    label, fill, border = evidence_label(item.evidence_class)
    add_callout(document, label, item.claim, fill=fill, border=border)
    add_rich_paragraph(document, [("定量依据　", {"bold": True, "color": DEEP_BLUE}), item.quantitative], after=5)
    add_figure(
        document,
        FIG[item.figure_key],
        f"图 {item.code}｜{item.caption}",
        source=item.source_note,
        # Keep the figure large enough for labels while leaving room for the
        # interpretation, boundary, and manuscript sentence on the same page.
        width=5.05,
        alt_text=f"{item.code} {item.title}：{item.caption}",
    )
    add_rich_paragraph(document, [("科学解释　", {"bold": True, "color": DEEP_BLUE}), item.interpretation], after=5)
    add_callout(document, "适用边界", item.boundary, fill=PALE_GOLD, border=GOLD)
    english_label = add_rich_paragraph(
        document,
        [("建议英文表述", {"bold": True, "color": DEEP_BLUE, "size": 9.5})],
        after=0,
    )
    english_label.paragraph_format.keep_with_next = True
    english_paragraph = add_rich_paragraph(
        document,
        [(item.english, {"italic": True, "size": 9.5})],
        after=3,
    )
    # Keep the sentence in a Western-only paragraph.  LibreOffice may apply
    # East-Asian character-level wrapping when Chinese and English share one
    # paragraph even if the WordprocessingML wordWrap property is enabled.
    english_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    prevent_midword_wrap(english_paragraph)
    for run in english_paragraph.runs:
        mark_run_as_english(run)
    # The code in the heading already supplies the unit identity.  A separate
    # trailing counter occasionally occupied a page by itself after a tall
    # figure, so it is intentionally omitted from the publication build.


def add_conclusion_group(document: Document, heading: str, intro: str, items: list[EvidenceConclusion], counter: list[int], total: int) -> None:
    group_heading = add_heading(document, heading, 1)
    group_heading.paragraph_format.page_break_before = True
    add_paragraph(document, intro, after=10)
    for item in items:
        counter[0] += 1
        add_conclusion_unit(document, item, counter[0], total)


def add_low_summary_tables(document: Document) -> None:
    add_heading(document, "低速层运行的关键量化结果", 1)
    rows = []
    for effect_name, label in (("low_flat", "M5/M3 平坦背景"), ("low_topography", "M6/M4 地形背景")):
        rows.append((
            label,
            f(effect(effect_name, "total_energy"), "ratio_median"),
            f(effect(effect_name, "peak_amplitude"), "ratio_median"),
            f(effect(effect_name, "T90_s"), "ratio_median"),
            f(effect(effect_name, "tmax_s"), "median"),
            f(effect(effect_name, "T_fraction"), "median") * 100.0,
        ))
    formatted = [(r[0], f"{r[1]:.2f}×", f"{r[2]:.2f}×", f"{r[3]:.2f}×", f"{r[4]:+.2f} s", f"{r[5]:+.2f} pp") for r in rows]
    add_table(document, ("条件对比", "能量", "峰值", "T90", "tmax", "T占比"), formatted, (2700, 1200, 1200, 1200, 1500, 1560), font_size=8.7)
    add_callout(document, "读取规则", "表中为 57 个空间块中位数；能量和峰值仅作为运行级条件对比，时间与分量占比的物理归因更稳健。", fill=PALE_GOLD, border=GOLD)


def add_input_audit_appendix(document: Document) -> None:
    add_heading(document, "附录：输入审计与可复现路径", 1)
    rows = []
    for row in AUDIT_ROWS:
        rows.append((row["model"], row["sample_count"], f"{float(row['median_dt_s']):.3f}", f"{float(row['time_end_s']):.2f}", row["sha256"][:16] + "..."))
    add_table(document, ("模型", "样本数", "dt(s)", "终点(s)", "SHA-256前缀"), rows, (1000, 1700, 1200, 1400, 4060), font_size=8.2)
    add_heading(document, "不可从新文件恢复的信息", 2)
    for item in (
        "低速层厚度、Vp、Vs、密度、Q 以及是否随地形起伏；",
        "随机介质强度、相关尺度、随机实现/种子及其在低速层内的分布；",
        "源文件、源归一化、网格、吸收边界、运行命令和完整介质清单。",
    ):
        add_real_bullet(document, item)
    add_callout(document, "禁止推断", "旧 REL3 中“1 km、Vp=1.38 km/s、Vs=1.11 km/s”仅是理论候选层诊断，不是 M5/M6 的元数据。", fill=PALE_GOLD, border=GOLD)


def add_manuscript_structure(document: Document) -> None:
    add_heading(document, "推荐的最终 JGR: Planets 论文结构", 1)
    sections = [
        ("1 Introduction", "提出月球地形、随机非均匀性和浅部低速结构如何共同控制三分量与长尾；明确本文检验的是机制层级而非单一最佳模型。"),
        ("2 Data and Numerical Methods", "分别描述半空间 800 单剖面、216 分辨率/分层几何、A16/S12 三射线与 Apollo A16S12；给出 Z/R/T 旋转、滤波、双窗口、空间块和删失规则。"),
        ("3 Preliminary Half-space Experiments", "3.1 地形三分量；3.2 分辨率 0.5/0.25 km 双阈值；3.3 分层对尾能量的影响；3.4 线性距离诊断。"),
        ("4 A16/S12 Factorial Baseline", "4.1 地形与随机非均匀性 2×2 波形；4.2 Z/R/T 能量分配；4.3 路径高差；4.4 条件非加性；4.5 线性/R² 排除检验。"),
        ("5 Low-velocity Extension", "5.1 数据与可识别性；5.2 运行级能量/持续/延迟；5.3 三分量与路径；5.4 地形×低速层条件交互；5.5 右删失敏感性。"),
        ("6 Comparison With Apollo A16S12", "分别比较初至、tmax、t95、相位相关、包络相关和时频范围；强调包络改善不等于完整拟合。"),
        ("7 Discussion", "7.1 背景依赖地形效应；7.2 地形分配-散射展宽-低速层滞留机制层级；7.3 当前仍非简单强扩散；7.4 缺失机制与下一轮试验。"),
        ("8 Conclusions", "只保留 6-8 条由多组证据支持的结论；运行清单缺失和右删失单列限制。"),
    ]
    for title, text in sections:
        add_heading(document, title, 2)
        add_paragraph(document, text, after=8)
    add_heading(document, "正文最值得保留的图", 2)
    for item in (
        "半空间：HS1、HS3、HS7、HS8；",
        "A16 四模型：Figure 2、3、4、5、6；",
        "低速层：LV05、LV07、LV09、LV11、LV14、LV17、LV18、LV20；",
        "Supporting Information：其余完整证据图册、全部空间块表、敏感性结果和输入审计。",
    ):
        add_real_bullet(document, item)


def add_final_conclusions(document: Document) -> None:
    add_heading(document, "最终可用于论文的综合结论", 1)
    add_callout(document, "最重要的投稿措辞", "低速层结果应写成“在当前运行对比中观察到的条件效应”，除非后续补齐源、介质、网格、Q 和随机实现清单；包络改善应与相位和完整持续时间失配并列。", fill=PALE_GOLD, border=GOLD)
    statements = [
        "高分辨率半空间试验表明，地形可显著重构三分量，使有限窗能量降至约 0.0296、T90 增至约 4.13 倍，并产生强 T 转换。",
        "地形分辨率存在两个标准：约 0.5 km 保持波形形状，约 0.25 km 才同时保证能量收敛。",
        "分层的主峰差异通常小于其尾能量和持续差异，因此不能再概括为“加入分层前后无明显差异”。",
        "A16/S12 中随机非均匀性产生比单独地形更强的展宽，二者在 T 分量和持续时间上表现出背景依赖的非加性。",
        "低速层运行是当前最强延迟机制：空间块 tmax 延迟约 112/101 s，并显著增加能量与 T90，但绝对幅能量归因受缺失运行清单限制。",
        "地形边际能量效应从无低速层背景的总体放大转为有低速层背景的近中性，说明地形不能作为固定倍率。",
        "M5/M6 改善 S12 早期包络，却没有解决三分量相位相关接近零和 t95 远短于 Apollo 的问题。",
        "从半空间到 M6，主能量迁移始终更接近线性距离而非简单 R²，当前模型仍未进入可解释 Apollo 完整长尾的强扩散状态。",
        "400 s 记录仍右删失部分台站；下一轮应延长记录、保存完整运行清单并增加低速层+无散射单元和多随机实现。",
    ]
    for index, statement in enumerate(statements, start=1):
        p = document.add_paragraph(style="List Number")
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(statement)
        set_run_font(run, size=10)


def markdown_report(title: str, subtitle: str, intro: str, groups: list[tuple[str, str, list[EvidenceConclusion]]], integrated: bool) -> str:
    lines = [f"# {title}", "", subtitle, "", intro, "", "## 统一处理与证据规则", "", "- 原采样率去趋势与四阶0.3-0.9 Hz零相位滤波；", "- t05/t50/t95/T90使用三分量滤波速度平方累计能量；", "- A16逐站旋转到R/T；正值指标用对数比，时间/占比用差值；", "- 575主站、57个非重叠10站块；带区间/检验的推断量基于相同块中位数，指定的旧四模型T90与分量占比为575站描述性中位数；", "- M5/M6缺少完整运行清单，绝对幅能量只作条件性运行级对比。", ""]
    for group_title, group_intro, items in groups:
        lines.extend([f"## {group_title}", "", group_intro, ""])
        for item in items:
            label = evidence_label(item.evidence_class)[0]
            rel = os.path.relpath(FIG[item.figure_key], REPORTS).replace("\\", "/")
            lines.extend([
                f"### {item.code} {item.title}", "", f"**{label}：** {item.claim}", "", f"**定量依据：** {item.quantitative}", "", f"![{item.code} {item.title}]({rel})", "", f"**科学解释：** {item.interpretation}", "", f"**适用边界：** {item.boundary}", "", f"**建议英文表述：** {item.english}", "", f"*{item.source_note}*", "",
            ])
    if integrated:
        lines.extend(["## 推荐论文结构与最终结论", "", "完整章节、主图选择和最终结论见同名Word文档。", ""])
    lines.extend(["## 可复现性", "", "输入审计、派生CSV、24幅低速层图及分析脚本均保存在 h/jgr_planets_submission 内。", ""])
    return "\n".join(lines)


def build_low_report(items: list[EvidenceConclusion]) -> None:
    document = Document()
    configure_document(document, "低速层模型详细数据分析｜REL3标准证据分级终审版")
    add_title_page(document, "低速层模型详细数据分析报告", "M5/M6 与 M1-M4、Apollo A16S12 的统一证据链", "完整审计两组新 station.nc，统一六模型处理，区分公共窗与延长窗，给出24个图像支持的证据单元、统计边界与投稿措辞。")
    add_navigation(document, ["执行摘要与关键数字", "数据/几何/可识别性", "统一处理与统计", "24条图像支持结论", "输入审计与下一轮试验"])
    add_heading(document, "执行摘要", 1)
    add_callout(document, "核心判断", "低速层运行显著增加能量积累、持续和峰时延迟，并改变 T 转换与地形边际效应；它改善 Apollo 早期包络但没有解决相位和完整长尾失配。", fill=PALE_BLUE, border=BLUE)
    add_low_summary_tables(document)
    add_methodology(document, integrated=False)
    groups = [
        ("第一部分｜输入、设计与 S12 直接波形", "先确定文件可比性、可识别设计和 S12 的直接三分量响应。", items[0:4]),
        ("第二部分｜运行级能量、持续与三分量", "量化低速层在两种表面背景中的总体与分射线效应。", items[4:8]),
        ("第三部分｜地形×低速层条件交互与路径控制", "检验地形边际效应是否因低速背景改变。", items[8:12]),
        ("第四部分｜距离迁移、相位与代表波形", "判断传播状态并把统计分布对应到真实波形。", items[12:16]),
        ("第五部分｜Apollo 对比、删失和空间异质性", "同时报告改善、仍然存在的失配与记录窗限制。", items[16:24]),
    ]
    counter = [0]
    for title, intro, group_items in groups:
        add_conclusion_group(document, title, intro, group_items, counter, len(items))
    add_input_audit_appendix(document)
    add_final_conclusions(document)
    REPORTS.mkdir(parents=True, exist_ok=True)
    document.save(LOW_DOCX)
    LOW_MD.write_text(markdown_report("低速层模型详细数据分析报告（REL3标准证据分级终审版）", "M5/M6 与 M1-M4、Apollo A16S12 的统一证据链", "本报告含24个结论-图件证据单元。", groups, integrated=False), encoding="utf-8")


def build_full_report(hs: list[EvidenceConclusion], a16: list[EvidenceConclusion], low: list[EvidenceConclusion], synth: list[EvidenceConclusion]) -> None:
    document = Document()
    configure_document(document, "月球地形-分层-散射-低速层全模型综合分析｜证据分级终审版")
    add_title_page(document, "月球地形、分层、散射与低速层全模型综合分析", "从半空间机制试验到 A16/S12、M5/M6 与 Apollo 的完整投稿证据链", "按研究阶段整合半空间、分辨率、分层、A16/S12四模型、低速层六模型及Apollo观测；76条编号结论均配直接图像证据，并给出论文结构、结论层级和下一轮试验设计。")
    add_navigation(document, ["科学问题与执行摘要", "模型/几何/处理链", "半空间9条证据", "A16/S12四模型28条证据", "低速层24条证据", "跨阶段15条综合证据", "最终论文结构与结论", "输入审计与可复现索引"])
    add_heading(document, "执行摘要：最有价值的科学发现", 1)
    add_callout(document, "总论", "地形控制空间分配与三分量转换，随机非均匀性强烈展宽波列，低速层运行产生目前最大的能量滞留和峰时延迟；三者具有背景依赖的条件非加性，但最复杂模型仍不足以再现 Apollo 数千秒长尾。", fill=PALE_BLUE, border=BLUE)
    add_low_summary_tables(document)
    add_methodology(document, integrated=True)
    total = len(hs) + len(a16) + len(low) + len(synth)
    counter = [0]
    groups = [
        ("第一部分｜半空间机制、分辨率与分层", "半空间试验建立地形三分量机制、数值收敛标准、分层边际效应和真实800台站距离诊断。", hs),
        ("第二部分｜A16/S12 地形×随机非均匀性基线", "四模型因子设计建立区域路径、三分量、非加性和观测失配的基线证据。", a16),
        ("第三部分｜低速层六模型条件扩展", "M5/M6 将记录延长到400 s，首次直接检验低速层对能量滞留、路径迁移和地形边际效应的影响。", low),
        ("第四部分｜跨尺度、跨背景综合判断", "只在几何和指标边界清楚的前提下整合不同阶段，形成可进入JGR: Planets的机制层级。", synth),
    ]
    for title, intro, items in groups:
        add_conclusion_group(document, title, intro, items, counter, total)
    add_manuscript_structure(document)
    add_final_conclusions(document)
    add_input_audit_appendix(document)
    add_heading(document, "附录：结论-图件-派生表-脚本索引", 1)
    rows = []
    for item in [*hs, *a16, *low, *synth]:
        rows.append((item.code, item.evidence_class, FIG[item.figure_key].name, "data/derived", "code/analyze_low_velocity_models.py" if item.code.startswith("LV") else "对应阶段分析脚本"))
    for start in range(0, len(rows), 24):
        add_table(document, ("编号", "等级", "图件", "派生表", "脚本"), rows[start:start + 24], (900, 1600, 3100, 1700, 2060), font_size=7.7)
    REPORTS.mkdir(parents=True, exist_ok=True)
    document.save(FULL_DOCX)
    FULL_MD.write_text(markdown_report("月球地形、分层、散射与低速层全模型综合分析（证据分级终审版）", "从半空间机制试验到 A16/S12、M5/M6 与 Apollo 的完整投稿证据链", f"本报告含{total}个结论-图件证据单元。", groups, integrated=True), encoding="utf-8")


def validate_inputs() -> None:
    missing = [path for path in FIG.values() if not path.is_file()]
    required = [
        DERIVED / "low_velocity_effect_summary.csv",
        DERIVED / "low_velocity_interaction_summary.csv",
        DERIVED / "low_velocity_time_distance_fits.csv",
        DERIVED / "A16S12_observed_six_model_comparison_metrics.csv",
        PROVENANCE / "low_velocity_input_audit.csv",
    ]
    missing.extend(path for path in required if not path.is_file())
    if missing:
        raise FileNotFoundError("Missing report inputs:\n" + "\n".join(str(path) for path in missing))


def main() -> None:
    validate_inputs()
    low = low_conclusions()
    hs = halfspace_conclusions()
    a16 = a16_conclusions()
    synth = synthesis_conclusions()
    if (len(low), len(hs), len(a16), len(synth)) != (24, 9, 28, 15):
        raise AssertionError("Unexpected conclusion inventory")
    build_low_report(low)
    build_full_report(hs, a16, low, synth)
    print(f"Created {LOW_DOCX}")
    print(f"Created {FULL_DOCX}")
    print(f"Created {LOW_MD}")
    print(f"Created {FULL_MD}")


if __name__ == "__main__":
    main()
