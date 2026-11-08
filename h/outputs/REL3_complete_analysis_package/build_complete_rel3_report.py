"""Build the complete Chinese REL3 technical report and reproducibility package."""

from __future__ import annotations

import csv
import os
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from build_lunar_five_paper_synthesis_docx import (
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
    add_bullet,
    add_callout,
    add_field,
    add_figure,
    add_heading,
    add_numbered,
    add_paragraph,
    add_rich_paragraph,
    add_table,
    configure_section,
    configure_styles,
    set_document_language,
    set_paragraph_border,
    set_run_font,
)


ROOT = Path(__file__).resolve().parent
DELIVERY_DIR = Path(os.environ.get("REL3_DELIVERY_DIR", ROOT / "REL3_complete_analysis_package"))
DOCUMENT_DIR = DELIVERY_DIR / "document"
REPORT_DOCX = Path(
    os.environ.get(
        "REL3_REPORT_DOCX",
        DOCUMENT_DIR / "REL3月震四模型_数据处理_图表证据_完整综合报告.docx",
    )
)
REPORT_MD = DOCUMENT_DIR / "REL3月震四模型_完整综合报告_文本版.md"
ZIP_FILE = Path(os.environ.get("REL3_ZIP_FILE", ROOT / "REL3_complete_analysis_package.zip"))

CONCLUSION_INDEX = ROOT / "conclusion_evidence" / "conclusion_evidence_index.csv"
PATH_REPORT = ROOT / "path_based_ray_analysis" / "path_based_analysis_report_zh.md"

KEY_FIGURES = {
    "s12": ROOT / "releasy_waveform_figures_python" / "figure1_S12_comparison.png",
    "ray1": ROOT / "releasy_waveform_figures_python" / "figure2_ray1_r102_offset.png",
    "ray2": ROOT / "releasy_waveform_figures_python" / "figure3_ray2_r315_offset.png",
    "ray3": ROOT / "releasy_waveform_figures_python" / "figure4_ray3_r555_offset.png",
    "tmax_distance": ROOT / "releasy_waveform_figures_python" / "figure5_peak_energy_time_vs_epicentral_distance.png",
    "linear_diffusion": ROOT / "releasy_waveform_figures_python" / "figure5b_peak_time_linear_vs_diffusion_fit.png",
    "observed_components": ROOT / "releasy_waveform_figures_python" / "figure6_A16S12_observed_three_components.png",
    "observed_models": ROOT / "releasy_waveform_figures_python" / "figure7_A16S12_observed_vs_four_models.png",
    "rise_diagnostics": ROOT / "releasy_waveform_figures_python" / "figure8_A16S12_envelope_rise_time_diagnostics.png",
    "path": ROOT / "path_based_ray_analysis" / "path_profiles_and_cumulative_metrics.png",
    "zrt": ROOT / "three_component_psvsh_analysis" / "figure_01_zrt_waveform_lanes.png",
    "modes": ROOT / "three_component_psvsh_analysis" / "figure_02_qp_qsv_sh_waveform_lanes.png",
    "mode_envelopes": ROOT / "three_component_psvsh_analysis" / "figure_03_mode_energy_envelopes.png",
    "long_coda": ROOT / "three_component_psvsh_analysis" / "figure_04_long_coda_mode_energy.png",
    "aligned_modes": ROOT / "three_component_psvsh_analysis" / "figure_05_aligned_mode_waveforms.png",
    "low_layer": ROOT / "three_component_psvsh_analysis" / "figure_06_low_velocity_layer_diagnostic.png",
    "factorial_s12": ROOT / "three_component_psvsh_analysis" / "figure_07_s12_three_component_factorial_waveforms.png",
    "factorial_rays": ROOT / "three_component_psvsh_analysis" / "figure_08_ray_three_component_factorial_waveforms.png",
    "energy_fraction_profiles": ROOT / "three_component_psvsh_analysis" / "figure_09_three_component_energy_fraction_profiles.png",
    "factorial_residual_s12": ROOT / "three_component_psvsh_analysis" / "figure_10_s12_factorial_residual_waveforms.png",
    "factorial_residual_rays": ROOT / "three_component_psvsh_analysis" / "figure_11_ray_factorial_residual_waveforms.png",
    "time_varying_polarization": ROOT / "three_component_psvsh_analysis" / "figure_12_s12_time_varying_polarization.png",
    "time_frequency": ROOT / "three_component_psvsh_analysis" / "figure_13_s12_observed_model_time_frequency.png",
}

MECHANISM_FIGURE = ROOT.parent / "tmp" / "lunar_synthesis_docx_assets" / "mechanism_synthesis.png"

SCRIPT_FILES = (
    "plot_releasy_waveform_comparison.py",
    "analyze_releasy_relationships.py",
    "analyze_releasy_literature_guided.py",
    "analyze_three_component_psvsh.py",
    "generate_path_based_ray_analysis.py",
    "generate_conclusion_waveform_atlas.py",
    "generate_conclusion_evidence_atlas.py",
    "run_complete_analysis.py",
    "build_complete_rel3_report.py",
    "build_lunar_five_paper_synthesis_docx.py",
    "audit_lunar_five_paper_synthesis_docx.py",
    "update_reviewer_response_docx.py",
    "requirements-complete-analysis.txt",
    "requirements-waveform-plots.txt",
)

REPORT_SOURCE_FILES = (
    ROOT / "releasy_relationship_analysis" / "analysis_report_zh.md",
    ROOT / "releasy_relationship_analysis" / "analysis_report_literature_guided_zh.md",
    ROOT / "three_component_psvsh_analysis" / "three_component_psvsh_report_zh.md",
    ROOT / "path_based_ray_analysis" / "path_based_analysis_report_zh.md",
    ROOT / "conclusion_evidence" / "conclusion_evidence_guide_zh.md",
)


CONCLUSION_DETAILS = (
    "M2−M1 的10周期能量峰值延迟中位数为5.244 s，空间块95%区间为4.389–6.213 s，95.7%的台站为正。5、10、20周期平滑下的中位延迟分别为2.679、5.244、7.695 s。方向稳健，但精确秒数依赖平滑尺度。",
    "M2−M1使上升时间乘以6.10、尾波衰减时间乘以3.75、5%–95%能量持续时间乘以17.33；全部台站的衰减时间与持续时间都增加。因此展宽比单一峰值时间更适合作为散射判据。",
    "M2−M1使峰值振幅变为0.293倍、总能量变为0.259倍、脉冲性SNR变为0.354倍。它不仅延后能量，还削弱主波、重分配能量并提高晚到能量比例。",
    "M3−M1使上升时间、拟合衰减时间和5%–95%能量持续时间的中位倍率分别为4.73、3.70和4.97，脉冲性SNR降至0.446倍，且所有台站晚到能量比例增加。但这些大倍率部分源于M1基准持续时间很短，新增能量主要位于低振幅尾部；因此结果只支持有限地形多路径展宽，不构成明显随机散射或强弥散传播的直接证据。",
    "去除震中距后，无散射地形效应的峰值振幅、总能量与路径高差的rho分别为−0.736、−0.731，持续时间为+0.659；有散射背景中仍为−0.711、−0.690和+0.718。路径累计高差显著强于终点高程。",
    "路径平均绝对坡度与无散射地形效应的峰值振幅、总能量和有效衰减时间相关分别为−0.600、−0.632和+0.509。坡度首先改变多路径和包络形态，不对应统一走时修正。",
    "平坦背景加入散射使持续时间乘以17.33，地形背景加入散射仅乘以2.19；无散射背景加入地形乘以4.97，散射背景加入地形仅乘以1.16。二阶交互显示明显饱和型非加性。",
    "四模型脉冲性SNR中位数为M1 6.40、M2 1.59、M3 2.00、M4 1.37。M1最尖锐，M4最弥散；该指标比单纯最大振幅更直接表示主相位可辨识度。",
    "M4−M2的峰值振幅和总能量中位因子为1.012和1.061，正负台站几乎各半。总体接近中性源于局地聚焦和散焦抵消，而不是地形没有作用。",
    "M3−M1与M4−M2的距离控制空间模式中，总能量、持续时间和峰值振幅相关分别为0.552、0.539和0.534。地形的振幅—能量—宽度空间指纹能穿过散射背景。",
    "平坦背景散射造成的tmax延迟在射线1、2、3分别为3.99、6.75、5.32 s；尾波能量比例增量为0.119、0.192、0.044。射线2同时对散射和地形最敏感。",
    "射线1的地形振幅和能量中位损失较小，但上升、衰减与持续时间仍明显增加。峰值幅度变化小不等于传播路径未被改造。",
    "四模型三条射线的td(f)指数均为负，约−0.675至−0.098；有效Qc(f)指数均为正，约0.325至0.902。高频按秒衰减更快，但每秒包含更多周期，因此有效Qc仍可升高。",
    "晚期/早期高低频能量比的对数中位数为M1 −0.446、M2 −0.875、M3 −0.634、M4 −0.486。平坦散射模型M2的尾波频谱软化最强，组合模型的新增散射则没有统一方向。",
    "四模型0.3–0.9 Hz有效Qc中位数为23.3、87.0、85.5、96.2，但移动尾波窗的log-Qc标准差约0.29–0.33，部分射线达0.42。当前Qc混合散射、俘获、回返和窗位效应，不能直接解释为Qi。",
    "平坦散射Δtmax的分段转折约为射线1 128 km、射线2 68 km、射线3 126 km；地形背景约146、94 km，射线3无强证据。不存在三条路径共享的单一转折距离。",
    "坡度/粗糙度与波形效应的最佳空间滞后随射线和指标大幅变化，多个最优值落在±30 km搜索边界且符号不一致。三条单向射线不足以估计唯一地形泄漏距离。",
    "最可靠的识别框架是联合使用包络展宽、脉冲性SNR和路径地形；tmax用于能量输运延迟但对平滑敏感，当前有效Qc仅描述有限时窗的尾波形态。",
    "A16S12方位校正后三分量原始主频为0.4380、0.4389、0.4262 Hz，稳定集中在约0.43 Hz；四模型S12频谱峰整体偏高。差异同时受源时间函数和介质控制。",
    "观测与模型均在约80–100 s出现初始能量，说明几何距离和首波速度量级并非主要矛盾；真正失配是模型主脉冲后迅速衰减，而观测包络继续增长数百秒。",
    "5–100 s六种平滑窗下，观测tmax中位数为658.29 s，范围647.12–770.44 s；M1–M4仅85.73、92.40、96.53、93.67 s，各不确定范围完全不重叠。",
    "相对M1，M2、M3、M4的S12中位峰值仅晚约6.67、10.80、7.95 s，远小于观测与M1之间约573 s的差距。现有地形和散射强度不能解释观测峰值延迟。",
    "从5%累计能量时刻到平滑能量峰值，观测上升持续375.08 s；M1–M4仅2.30、16.47、13.50、13.80 s，差一个至两个数量级。",
    "M1的95%记录能量时刻为86.47 s，M2延至160.68 s，M4为152.52 s。随机散射方向正确，但仍远不足以产生月震级长尾。",
    "M3的95%能量时刻为110.49 s，介于M1与M2/M4之间。地形能够展宽主波列，但单独不能解释千秒级能量累积。",
    "扣除噪声底后，真实记录50–3000 s能量中，前250 s仅占约4.0%；50%和95%能量时刻约984.92 s和2804.63 s。250 s合成只能验证初至与早期尾波。",
    "每个模型只用一个50–245 s三分量RMS源尺度因子后，整体波形相关仍仅−0.010至0.036，归一化RMSE为1.39–1.42。源振幅调整不能修复相位和包络形状。",
    "50–245 s内观测包络仍在增强，而模型包络已在主脉冲后衰减；允许±10 s时移仍不能改变整体负相关趋势，说明能量输运机制不匹配。",
    "三条射线、四模型共12组tmax(R)全部偏好线性a+bR，而非扩散a+cR²；线性RMSE为1.54–2.88 s，R²形式为4.56–10.03 s，ΔAIC为268–672。",
    "距离波形剖面中的主能量脊近似沿直线传播，扩散型R²轨迹系统偏离。当前随机扰动和地形增加多路径，但尚未把能量输运推入强扩散状态。",
    "真实A16S12只在约152 km提供一个长尾锚点，不能独立拟合观测tmax或上升时间的距离幂律。验证R²/D必须加入多个事件—台站距离组合。",
    "下一步应延长记录并重构散射层，而不是继续微调源振幅。延长只用于检验晚期阶段，不会改变固定早期拟合窗得到的td；真正需要同步改变散射强度、相关尺度、厚度、随机种子、低速层、Qi和计算域。",
)

THREE_COMPONENT_CONCLUSIONS = (
    "实测50–245 s能量分配为qP 34.7%、qSV 40.5%、SH 24.8%，是模型比较的真实三分量基准。",
    "qP形状最接近实测的是M4，最佳相关r=+0.15、时移+18.3 s；仍未重合。",
    "qSV形状最接近实测的是M4，最佳相关r=−0.23、时移+6.6 s；R-Z平面失配涉及速度、自由表面转换和浅层多次波。",
    "SH形状最接近实测的是M2，最佳相关r=+0.20、时移−8.7 s；SH对水平散射和横向非均匀性最敏感。",
    "M1的SH占比约0%，符合平坦无散射各向同性结构的对称性；实测24.8%说明真实波场存在当前一维背景没有的三维转换或散射。",
    "平坦模型加入散射后SH增加到14.0%，方向正确但仍低于观测。",
    "无散射条件下加入地形后SH仅3.2%，地形单独不能重现真实横向能量。",
    "有地形条件下再加入散射，SH边际增量为+0.091，小于平坦背景的+0.140，进一步支持非线性耦合。",
    "扣除0–40 s噪声底后，观测50–3000 s总能量中245 s之后仍占95.9%；当前模型无法检验大部分长尾。",
    "最佳时移后仍有明显包络、周期和脉冲数差异，三模态|r|均很低，归一化或整体平移不足以修复波形。",
    "当前0–5 km背景Vp=3.20 km/s、Vs=2.00 km/s；加入1 km、Vp=1.38、Vs=1.11 km/s低速层的最低附加时延约P 0.824 s、S 0.802 s。",
    "低速层P/S往返时间约1.449/1.802 s，可改变短周期干涉与多次波，但不能单独产生数百至数千秒长尾。",
    "静态时移不能生成低速层的陷获、频散、反射、模式转换及其与地形/散射的耦合；正式结论必须重算。",
    "0.9 Hz下Vs=1.11 km/s的最短S波波长约1.233 km；200 m网格约6.17点/波长，需核查数值色散并考虑120–150 m网格或降低最高频率。",
    "qP/qSV是单台站固定偏振基下的代理量；最稳健结果是Z/R/T、P-SV平面总能量和SH=T。严格分离需阵列慢度或散度—旋度波场。",
)

FIELD_COMPONENT_CONCLUSIONS = (
    "在50–245 s窗口、0.3–0.9 Hz频带内，575个有效射线台站的Z/R/T能量占比中位数由M1的70.1%/29.9%/近0，依次变为M2的54.6%/24.7%/20.4%、M3的56.4%/27.6%/16.1%和M4的48.9%/27.3%/23.4%。地形与散射主要表现为分量间能量再分配，而不是单一分量同步衰减。",
    "M1的T分量几乎为零，符合平坦、无散射、近对称介质中的二维P-SV传播特征；M2、M3和M4出现稳定T能量，说明随机非均匀性和三维地形都会破坏对称性并产生SH代理能量。",
    "在平坦背景上加入散射，T能量占比的全台站中位增量为+20.4个百分点，三条射线分别约+20.7、+20.3和+20.3个百分点，表明当前随机介质对横向转换的作用强且方向一致。",
    "在无散射背景上加入地形，T占比的全台站中位增量为+16.1个百分点，但具有明显路径差异：射线1仅+3.5个百分点，射线2和3分别+16.7和+18.8个百分点，与后两条路径更大的累计高差和坡度一致。",
    "组合模型M4的T占比最高，达到23.4%，同时Z占比由M1的70.1%降至48.9%。这说明最复杂模型将更多垂向相干能量转移到径向与横向波场，而不能把Z减小直接解释为本征吸收增强。",
    "散射的边际T转换在地形背景上由+20.4降为+8.6个百分点；地形的边际T转换在散射背景上由+16.1降为+2.0个百分点，且四分位区间跨零。二者存在明显饱和型非加性，而不是两个独立效应的线性叠加。",
    "S12与射线总体方向一致但更受散射控制：平坦背景加散射使T占比增加14.0个百分点，无散射背景加地形只增加3.2个百分点；组合模型相对地形模型再增加9.1个百分点。单台站结论不能替代路径统计。",
    "代表波形显示，射线2和3在M2–M4中更容易出现持续T波列、多脉冲和Z/R主脉冲削弱，射线1的纯地形T转换较弱。这把路径起伏、模式转换和尾波展宽直接联系起来。",
    "不能用M2/M1或M3/M1的T能量倍数描述转换强弱，因为M1的T能量接近数值零，分母会使倍数发散。报告采用T能量占比增量、分量波形和分位数统计作为稳健证据。",
    "Z/R/T只能稳健表示台站坐标下的分量再分配，其中T可作SH代理；若要严格分离P、SV和SH并区分几何聚焦与散射转换，仍需三分量波场快照、散度/旋度或能量通量。",
)

EXTENDED_COMPONENT_CONCLUSIONS = (
    "575个有效射线台站中，交互项I=M4−M3−M2+M1的RMS与两个基础主效应RMS之和的比值中位数为Z 0.69、R 0.70、T 1.00。T交互波形与两个单独效应之和同量级，地形和散射的横向转换不能线性叠加。",
    "S12的交互比为Z 0.55、R 0.53、T 1.02；单台站和全路径统计均显示非线性主要集中在T/SH代理分量，而不是统一振幅缩放。",
    "差分波形中的交互项在主脉冲之后形成新的相位、多脉冲和持续振荡，因此不能用‘地形振幅修正+独立散射尾波卷积’替代组合模型。",
    "实测S12有效窗口的中位线性度为0.66、主轴T倾角33.3°、T能量比例0.29；M1为0.85、0°和近0，表现为过度线性化的Z-R平面传播。",
    "M2、M3、M4的中位T倾角分别为17.6°、15.4°和16.0°，方向上接近观测但仍只有约一半，说明当前三维转换或浅部复杂性不足。",
    "观测三分量相对能量在50–239 s总体增强；M1约100 s后已降至相对峰值−30 dB以下，M2/M4虽维持到记录末端但仍持续衰减。",
    "实测Z/R/T时频主频分别为0.399、0.448和0.399 Hz，而模型各分量为0.550–0.800 Hz，系统性偏高不能由振幅归一化修复。",
    "120 s之后实测能量占Z 93.9%、R 88.6%、T 86.0%；模型Z/R最高仅11.5%，T最高29.7%。当前散射可延长T波列，但没有重现三分量共同的晚期能量积累。",
    "模型与观测的频谱形状相关总体很低，三分量平均后M2相对最好但仍接近零；所有模型的时频能量时间相关均为负。",
    "差分、偏振和时频三类证据共同表明：当前模型的主要缺口是频率—持续时间—三维转换机制，而不是单一震源能量系数。",
)

PATH_CONCLUSIONS = (
    "射线1沿途最平滑，累计高差和平均绝对坡度远低于射线2、3，地形系统效应最弱。",
    "射线2在约60–80 km穿越显著低洼区及盆缘，主要表现为散焦和能量损失。",
    "射线3在约30–55 km快速积累起伏且平均坡度最大，更容易产生多脉冲、相位分裂和长尾。",
    "路径累计高差与峰值振幅、总能量强负相关，与90%持续时间强正相关，强于终点高程。",
    "平均绝对坡度控制完整波形畸变和包络宽度，不等于统一的走时修正。",
    "地形把相干直接波转换为反射、绕射、模式转换和多路径能量，常见组合是峰值下降、能量下降、持续时间增加。",
    "射线3最粗糙但射线2部分位置能量损失更强，说明曲率、坡向、盆地几何和聚焦/散焦同样重要。",
    "约50 km同距离对比显示：射线1/2低高差路径M3/M1能量接近1，射线3约3.3 km高差时可降到0.117。",
    "约100 km同距离对比显示：射线2和3高起伏路径均有更强峰值/能量下降和持续时间增长。",
    "地形与随机散射具有饱和型非加性，随机散射已展宽波列时，地形的新增边际作用通常减弱。",
    "当前采用地表投影直线路径；更严格分析需有限频率Fresnel走廊、波场快照和能量通量。",
)

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require_inputs() -> None:
    paths = [CONCLUSION_INDEX, PATH_REPORT, MECHANISM_FIGURE, *KEY_FIGURES.values()]
    paths.extend(ROOT / "conclusion_evidence" / "cards" / f"C{index:02d}_{slug}.png" for index, slug in ())
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing report inputs:\n" + "\n".join(str(path) for path in missing))


def set_header_footer(section) -> None:
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run("REL3四模型月震波形｜完整数据—方法—证据报告")
    set_run_font(run, size=8.5, color=MUTED)
    set_paragraph_border(paragraph, side="bottom", color="D7DBE2", size=6, space=4)
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    set_run_font(run, size=8.5, color=MUTED)
    page_run = paragraph.add_run()
    set_run_font(page_run, size=8.5, color=MUTED)
    add_field(page_run, "PAGE")
    run = paragraph.add_run(" 页")
    set_run_font(run, size=8.5, color=MUTED)


def configure_document(document: Document) -> None:
    configure_styles(document)
    set_document_language(document)
    normal = document.styles["Normal"]
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.2
    normal.paragraph_format.space_after = Pt(6)
    normal.font.size = Pt(10.5)
    for section in document.sections:
        configure_section(section)
        set_header_footer(section)


def add_cover(document: Document) -> None:
    add_paragraph(document, "数值月震传播研究综合技术报告", align=WD_ALIGN_PARAGRAPH.CENTER, before=55, after=18)
    title = add_paragraph(document, "REL3四模型月震波形", align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    title_run = title.runs[0]
    set_run_font(title_run, size=28, bold=True, color=NAVY)
    subtitle = add_paragraph(document, "数据处理、地形路径、散射耦合、真实A16S12、低速层、论文方法与审稿修改的完整汇总", align=WD_ALIGN_PARAGRAPH.CENTER, after=20)
    set_run_font(subtitle.runs[0], size=14, color=DEEP_BLUE)
    add_figure(
        document,
        MECHANISM_FIGURE,
        "研究机制总图：低速俘获、随机散射、高Qi与球形/横向结构共同控制月震包络。",
        width=6.15,
        alt_text="月震长尾波联合机制示意图",
    )
    add_callout(
        document,
        "总判断",
        "现有四模型已能可靠识别地形与随机散射对早期波形的相对作用，但不能解释A16S12数百至数千秒的能量积累。最关键的改进是统一加入可分辨低速层、增强并重构三维散射、延长记录、核查Qi与边界，并保持三分量和路径统计的一致性。",
        fill=PALE_GOLD,
        border=GOLD,
    )
    add_paragraph(document, "版本日期：2026-08-11　｜　震源：(161.310, 207.630, 0) km　｜　主频带：0.3–0.9 Hz", align=WD_ALIGN_PARAGRAPH.CENTER, before=10, after=0)
    document.add_page_break()


def add_contents(document: Document) -> None:
    add_heading(document, "内容导航", 1)
    entries = (
        "1　研究对象、数据与统一处理链",
        "2　32条完整结论及逐条波形证据",
        "3　三条射线的传播路径地形解释",
        "4　A16S12真实三分量与P-SV-SH分析",
        "5　低速层补救、候选模型与数值约束",
        "6　td、Qc、平滑窗与记录时长",
        "7　文献方法在本数据中的应用",
        "8　审稿意见对应修改矩阵",
        "9　最终论文表述、限制与下一轮试验",
        "附录　脚本、输出文件与一键复现",
    )
    for entry in entries:
        add_bullet(document, entry)
    add_callout(document, "阅读建议", "先读第1章和第9章把握研究边界；需要写论文结果时使用第2–4章；需要重算模型时使用第5–6章；需要回应审稿人时使用第7–8章。")
    document.add_page_break()


def add_data_methods(document: Document) -> None:
    add_heading(document, "1　研究对象、数据与统一处理链", 1)
    add_heading(document, "1.1　四模型2×2因子设计", 2)
    add_table(
        document,
        ("模型", "地形", "随机散射", "主要用途"),
        (
            ("M1", "平坦", "无", "背景速度与几何基线"),
            ("M2", "平坦", "有", "纯随机散射增量"),
            ("M3", "起伏", "无", "纯地形增量"),
            ("M4", "起伏", "有", "地形—散射交互"),
        ),
        (1000, 1500, 1800, 5060),
    )
    add_paragraph(document, "四个station.nc分别来自E盘的flat/topography × scatter/no-scatter计算。r1为S12；r2–r214、r215–r454、r455–r606分别属于射线1、2、3，共606个相同台站。三条射线约每1 km一个台站。")
    add_heading(document, "1.2　统一预处理", 2)
    steps = (
        "读取station.nc中的time和Vz；三分量分析另读取Vx、Vy。若数组为time×station则转置为station×time。",
        "原始波形先去均值或线性趋势；原始主频在滤波前由幅度谱最大非零频点计算。",
        "所有比较波形采用四阶0.3–0.9 Hz Butterworth带通，并用sosfiltfilt进行零相位滤波。",
        "使用解析信号构造Hilbert能量包络；tmax按5、10、20周期或5–100 s多平滑窗估计。",
        "累计能量给出t05、t50、t90、t95；尾波拟合从包络峰值后开始，并在有效信号或固定窗结束。",
        "真实A16S12先依据SAC头段CMPAZ/CMPINC解算真E/N，再按震源—台站方位旋转至R/T。",
        "观测—模型只使用每个模型一个三分量联合RMS源尺度因子，禁止逐分量、逐台站独立归一化。",
        "地形统计在每条射线内去除三次震中距趋势、按射线标准化，并使用不重叠10台站空间块Spearman相关与FDR。",
    )
    for step in steps:
        add_numbered(document, step)
    add_heading(document, "1.3　指标定义与解释边界", 2)
    add_table(
        document,
        ("指标", "定义", "最敏感因素", "不能直接代表"),
        (
            ("tmax", "平滑能量包络最大值时刻", "散射展宽、路径、平滑窗", "严格首波走时"),
            ("上升历时", "t05或起振至tmax", "散射、源时间函数、低速俘获", "尾波衰减"),
            ("td", "拟合包络衰减1/e的时间", "吸收、散射、窗位、回返", "唯一Qi"),
            ("Qc", "由td与中心频率换算的有效品质因子", "尾波阶段与频率", "当前记录中的纯内禀吸收"),
            ("SNR", "主峰窗RMS/紧随尾波窗RMS", "脉冲性与弥散程度", "仪器噪声信噪比"),
            ("路径高差", "震源至台站路径最大高程差", "累计地形复杂度", "三维Fresnel体积全部结构"),
        ),
        (950, 2800, 2600, 3010),
        font_size=8.5,
    )
    add_figure(document, KEY_FIGURES["s12"], "图1　四模型S12垂向波形叠加；透明度和颜色用于识别重叠部分。", width=6.25, alt_text="四模型S12波形对比")
    add_figure(document, KEY_FIGURES["path"], "图2　三条射线的路径地形、累计高差与累计平均绝对坡度。", width=6.25, alt_text="三条射线路径地形剖面")


def add_conclusion_atlas(document: Document) -> None:
    rows = read_csv(CONCLUSION_INDEX)
    if len(rows) != 32 or len(CONCLUSION_DETAILS) != 32:
        raise RuntimeError("The complete report requires exactly 32 evidence conclusions.")
    add_heading(document, "2　32条完整结论及逐条波形证据", 1)
    add_callout(document, "图证原则", "每条结论均配原始/滤波波形、Hilbert-RMS包络、累计能量、频谱或距离波形剖面，不使用柱状图替代波形证据。归一化图只解释形状；绝对振幅和能量结论来自未独立归一化的指标。")
    for index, (row, detail) in enumerate(zip(rows, CONCLUSION_DETAILS, strict=True), start=1):
        if index > 1:
            document.add_page_break()
        add_heading(document, f"C{index:02d}　{row['title']}", 2)
        add_paragraph(document, detail)
        add_callout(document, "波形判据", row["takeaway"], fill=PALE_BLUE, border=BLUE)
        card_path = ROOT / "conclusion_evidence" / row["card_file"]
        add_figure(
            document,
            card_path,
            f"图C{index:02d}　{row['title']}。代表记录：{row['representative_stations']}。",
            source=f"证据来源：{row['evidence_sources']}",
            width=6.25,
            alt_text=f"结论C{index:02d}的波形证据",
        )


def add_path_analysis(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "3　三条射线的传播路径地形解释", 1)
    add_paragraph(document, "之前若只用台站点位高程解释路径1–3，会漏掉波在到达台站前经历的累计起伏。本章使用震源到台站的地表投影直线路径，计算路径平均高程、平均绝对坡度和累计高差；末端2 km被排除以避免模型边界哨兵值。")
    summary_rows = read_csv(ROOT / "path_based_ray_analysis" / "path_ray_summary.csv")
    add_table(
        document,
        ("射线", "主样本", "终点高程中位/km", "路径平均高程/km", "平均绝对坡度", "累计高差/km"),
        tuple(
            (
                row["ray"],
                row["station_count"],
                f"{float(row['median_endpoint_elevation_km']):.3f}",
                f"{float(row['median_path_mean_elevation_km']):.3f}",
                f"{float(row['median_path_mean_absolute_slope']):.3f}",
                f"{float(row['median_path_relief_range_km']):.3f}",
            )
            for row in summary_rows
        ),
        (700, 900, 1800, 1900, 1800, 2260),
        font_size=8.2,
    )
    add_figure(document, KEY_FIGURES["path"], "图3　三条传播路径的地形剖面与累计路径复杂度。", width=6.25, alt_text="路径剖面及累计地形指标")
    add_heading(document, "3.1　全部路径结论", 2)
    for conclusion in PATH_CONCLUSIONS:
        add_numbered(document, conclusion)
    add_heading(document, "3.2　约100 km同距离波形", 2)
    add_figure(document, KEY_FIGURES["ray1"], "图4a　射线1约101 km台站四模型错列波形：路径平滑，地形效应相对较弱。", width=6.2, alt_text="射线1代表台站波形")
    add_figure(document, KEY_FIGURES["ray2"], "图4b　射线2约101 km台站四模型错列波形：盆缘路径造成显著能量损失和展宽。", width=6.2, alt_text="射线2代表台站波形")
    add_figure(document, KEY_FIGURES["ray3"], "图4c　射线3约101 km台站四模型错列波形：陡峭路径产生多脉冲与长尾。", width=6.2, alt_text="射线3代表台站波形")
    examples = read_csv(ROOT / "path_based_ray_analysis" / "matched_distance_path_examples.csv")
    selected = [row for row in examples if float(row["target_distance_km"]) == 100.0]
    add_table(
        document,
        ("射线", "台站", "高差/km", "坡度", "M3/M1峰值", "M3/M1能量", "M3/M1持续", "M4/M2能量"),
        tuple(
            (
                row["ray"], row["station"], row["path_relief_range_km"], row["path_mean_absolute_slope"],
                row["M3_over_M1_peak_amplitude"], row["M3_over_M1_total_energy"], row["M3_over_M1_duration_90"], row["M4_over_M2_total_energy"],
            )
            for row in selected
        ),
        (650, 800, 950, 850, 1200, 1200, 1400, 2310),
        font_size=8.1,
    )
    add_callout(document, "物理解读", "射线2和3的高起伏路径将相干主脉冲转移到多路径、反射、绕射与模式转换能量中。射线2更像盆缘散焦和总能量损失，射线3更像较早发生的波形分裂与持续展宽；高差并非唯一变量，曲率、坡向和几何聚焦同样关键。", fill=PALE_GOLD, border=GOLD)


def add_observed_three_component(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "4　A16S12真实三分量与P-SV-SH分析", 1)
    add_paragraph(document, "实测BHE/BHN并非严格正东/正北。根据SAC头段，BHE的CMPAZ约9.43°、BHN约90.09°；因此必须先解算真E/N，再旋转为R/T。T作为SH代理，R-Z平面用M1首个主波窗固定偏振基近似投影为qP/qSV。")
    add_figure(document, KEY_FIGURES["observed_components"], "图5　A16S12真实三分量原始、0.3–0.9 Hz滤波及频谱。", width=6.25, alt_text="A16S12真实三分量")
    add_figure(document, KEY_FIGURES["observed_models"], "图6　真实A16S12与四模型S12三分量统一源尺度对比。", width=6.25, alt_text="真实与四模型S12对比")
    add_figure(document, KEY_FIGURES["rise_diagnostics"], "图7　观测与四模型能量包络、累计能量和平滑窗敏感性。", width=6.25, alt_text="包络峰值和上升时间诊断")
    add_heading(document, "4.1　三分量与模态结论", 2)
    for conclusion in THREE_COMPONENT_CONCLUSIONS:
        add_numbered(document, conclusion)
    add_figure(document, KEY_FIGURES["zrt"], "图8a　实测与四模型Z/R/T波形通道。", width=6.2, alt_text="ZRT波形通道")
    add_figure(document, KEY_FIGURES["modes"], "图8b　统一偏振基下qP/qSV/SH波形通道。", width=6.2, alt_text="qP qSV SH波形通道")
    add_figure(document, KEY_FIGURES["mode_envelopes"], "图8c　五条记录的模态能量包络。", width=6.2, alt_text="模态能量包络")
    add_figure(document, KEY_FIGURES["long_coda"], "图8d　实测3000 s长尾与模型250 s时窗的模态能量比较。", width=6.2, alt_text="长尾模态能量")
    add_figure(document, KEY_FIGURES["aligned_modes"], "图8e　允许最佳时移和单模态幅值拟合后的形状比较。", width=6.2, alt_text="对齐后的模态波形")
    add_heading(document, "4.2　加入地形和散射前后的三分量变化", 2)
    add_paragraph(document, "下表统计575个有效射线台站在50–245 s窗口内的三分量能量占比中位数。模型定义为M1平坦无散射、M2平坦有散射、M3地形无散射、M4地形有散射；模型水平分量先按每个台站的震源方位旋转为R/T。")
    add_table(
        document,
        ("模型", "物理设置", "Z占比", "R占比", "T占比"),
        (
            ("M1", "平坦、无散射", "70.1%", "29.9%", "≈0.0%"),
            ("M2", "平坦、有散射", "54.6%", "24.7%", "20.4%"),
            ("M3", "地形、无散射", "56.4%", "27.6%", "16.1%"),
            ("M4", "地形、有散射", "48.9%", "27.3%", "23.4%"),
        ),
        (1100, 2860, 1800, 1800, 1800),
        font_size=8.8,
    )
    for conclusion in FIELD_COMPONENT_CONCLUSIONS:
        add_numbered(document, conclusion)
    add_figure(document, KEY_FIGURES["factorial_s12"], "图8f　S12台站Z/R/T波形的四组因子对比；同一子图采用统一幅值尺度。", width=6.25, alt_text="S12地形与散射三分量因子波形")
    add_figure(document, KEY_FIGURES["factorial_rays"], "图8g　三条射线约100 km代表台站的四模型Z/R/T错列波形。", width=6.25, alt_text="三条射线代表台站三分量波形")
    add_figure(document, KEY_FIGURES["energy_fraction_profiles"], "图8h　三条射线Z/R/T能量占比随震中距变化；T分量最直接显示地形和散射诱发的横向转换。", width=6.25, alt_text="三条射线三分量能量占比剖面")
    add_heading(document, "4.3　差分波形、时变偏振与时频观测对比", 2)
    add_paragraph(document, "差分波形保持模型间原始相对振幅，定义平坦背景散射效应M2−M1、无散射地形效应M3−M1、地形背景散射效应M4−M3，以及交互项I=M4−M3−M2+M1。偏振分析采用12 s滑窗；时频分析采用20 s Hann窗、2 s步长，功率图按各子图峰值归一化，避免震源尺度掩盖频率—持续时间结构。")
    add_table(
        document,
        ("范围", "Z交互比", "R交互比", "T交互比", "解释"),
        (
            ("575个有效台站中位数", "0.69", "0.70", "1.00", "T交互项与两个主效应之和同量级"),
            ("S12", "0.55", "0.53", "1.02", "非线性同样集中于T/SH代理分量"),
        ),
        (2100, 1300, 1300, 1300, 3360),
        font_size=8.4,
    )
    add_table(
        document,
        ("记录", "线性度", "入射角", "主轴T倾角", "T能量比例"),
        (
            ("Observed", "0.66", "69.5°", "33.3°", "0.29"),
            ("M1", "0.85", "5.7°", "0.0°", "0.00"),
            ("M2", "0.59", "47.7°", "17.6°", "0.23"),
            ("M3", "0.62", "28.8°", "15.4°", "0.21"),
            ("M4", "0.62", "32.5°", "16.0°", "0.26"),
        ),
        (1800, 1650, 1800, 2060, 2050),
        font_size=8.4,
    )
    for conclusion in EXTENDED_COMPONENT_CONCLUSIONS:
        add_numbered(document, conclusion)
    add_figure(document, KEY_FIGURES["factorial_residual_s12"], "图8i　S12三分量的散射、地形、地形背景散射和交互项差分波形。", width=6.25, alt_text="S12三分量因子差分及交互波形")
    add_figure(document, KEY_FIGURES["factorial_residual_rays"], "图8j　三条射线约100 km代表台站的因子差分与非线性交互波形。", width=6.25, alt_text="三条射线因子差分及交互波形")
    add_figure(document, KEY_FIGURES["time_varying_polarization"], "图8k　A16S12真实记录与四模型的时变偏振、主轴T倾角和T能量比例。", width=6.25, alt_text="S12时变偏振对比")
    add_figure(document, KEY_FIGURES["time_frequency"], "图8l　A16S12真实记录与四模型Z/R/T时频功率对比；各子图按自身峰值归一化。", width=6.25, alt_text="S12真实与模型三分量时频对比")


def add_low_velocity_layer(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "5　低速层补救、候选模型与数值约束", 1)
    add_callout(document, "首选处理", "四个模型必须在相同低速层背景上全部重算；事后静态平移或卷积只能作为误差方向检查，不能替代反射、频散、陷获、模式转换及其与地形/散射耦合。", fill=PALE_GOLD, border=GOLD)
    add_figure(document, KEY_FIGURES["low_layer"], "图9　1 km候选低速层的速度剖面、最低附加时延与静态修正局限。", width=6.25, alt_text="低速层诊断")
    add_heading(document, "5.1　建议的工程化候选模型", 2)
    add_table(
        document,
        ("方案", "厚度", "Vp", "Vs", "定位", "数值要求"),
        (
            ("LVL-A 温和", "0.5 km", "1.8 km/s", "1.2 km/s", "低速效应下限；平滑过渡", "200 m网格需核查"),
            ("LVL-B 主候选", "1.0 km", "1.38 km/s", "1.11 km/s", "用户给定等效层；阶跃/平滑各一组", "建议120–150 m或降低fmax"),
            ("LVL-C 强端元", "1.5 km", "1.0 km/s", "0.6 km/s", "振铃上限，不作唯一真实模型", "需约80–100 m网格"),
            ("Burmin米级层", "0–1.5 km多层", "0.1–4.0 km/s", "0.04–2.3 km/s", "文献端元与机制参照", "当前200 m网格不能直接离散"),
        ),
        (1050, 1100, 1200, 1200, 2850, 1960),
        font_size=8.0,
    )
    add_paragraph(document, "前三组是面向当前三维网格的数值敏感性候选，不是由现有四模型唯一反演得到的月球真实结构。正式重算前必须补充密度并同时测试阻抗；可将低速层密度设为多个敏感性值，例如低密度端元、过渡值和沿用2760 kg/m³的数值控制组。")
    add_heading(document, "5.2　实施约束", 2)
    constraints = (
        "低速层在平坦模型中设为z=0至−h；地形模型中层底必须随局部自由表面保持等厚。",
        "第一轮让四模型使用完全相同的低速层，原随机扰动先只作用于1 km以下；第二轮再测试低速层内散射。",
        "同时计算尖锐界面和2–4网格点平滑过渡，区分物理反射与网格伪影。",
        "0.9 Hz、Vs=1.11 km/s时最短波长1.233 km，200 m仅6.17点/波长；应按CGFD3D差分阶数核查。",
        "低速层只会产生约秒级最小附加时延，但可通过多次反射和陷获显著改变波形；不能把它简化成一个常量时移。",
        "模拟时窗采用自适应延长：先600 s，若末端50 s能量仍超过总能量1%或包络高于噪声2倍，则延长到1000–1200 s。",
    )
    for item in constraints:
        add_numbered(document, item)
    add_heading(document, "5.3　介质脚本骨架", 2)
    code_lines = (
        "num_of_intfce = 6;",
        "num_of_point_per_lay = [5,20,25,100,53];",
        "dep = [0,1e3,5e3,1e4,3e4,4e4];",
        "Vp  = [1380,1380,3200,5500,7550,7550];",
        "Vs  = [1110,1110,2000,3180,4360,4360];",
        "den = [rho_low,rho_low,2760,2760,3360,3360];",
    )
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.space_after = Pt(8)
    for index, line in enumerate(code_lines):
        run = paragraph.add_run(line)
        set_run_font(run, name="Consolas", size=9, color=DEEP_BLUE)
        if index < len(code_lines) - 1:
            run.add_break()


def add_td_window_analysis(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "6　td、Qc、平滑窗与记录时长", 1)
    add_heading(document, "6.1　当前四模型的早期td是否可算", 2)
    add_table(
        document,
        ("模型", "能量包络td/s", "振幅包络等效td/s", "20 s包含e折数", "60 s包含e折数", "判断"),
        (
            ("M1", "5.49", "10.98", "3.64", "10.93", "20 s即可，60 s更稳健"),
            ("M2", "16.64", "33.27", "1.20", "3.61", "20 s偏短，60 s适合"),
            ("M3", "32.61", "65.22", "0.61", "1.84", "20 s不足，60 s仅早期估计"),
            ("M4", "22.21", "44.43", "0.90", "2.70", "20 s偏短，60 s适合"),
        ),
        (850, 1350, 1600, 1300, 1300, 2960),
        font_size=8.4,
    )
    add_paragraph(document, "20 s并非数学上不能拟合，但M2–M4在20 s内只覆盖约0.6–1.2个e折，拟合很容易受峰后振荡、窗起点和局部多路径控制。60 s覆盖约1.8–3.6个e折，更适合作为统一早期尾波窗；M3仍应报告窗位敏感性。")
    add_heading(document, "6.2　能量包络与振幅包络的换算", 2)
    add_paragraph(document, "当前脚本拟合平滑强度/能量包络I(t)∝exp(−t/td,E)。若文献拟合振幅包络A(t)∝exp(−t/td,A)，则I=A²，因此td,A=2td,E。相应地，Qc=2πf·td,E与Qc=πf·td,A完全一致。比较论文数值前必须先统一包络定义。")
    add_heading(document, "6.3　延长记录会不会改变td", 2)
    add_callout(document, "答案", "若滤波器、平滑、拟合起点和固定60 s拟合窗完全不变，仅把总记录从250 s延长，已有早期td原则上不会改变。延长记录的意义是检查后续是否出现第二衰减阶段、非指数尾波、边界回返和更稳定的晚期Qc，而不是人为放大已有td。")
    add_heading(document, "6.4　推荐时间窗", 2)
    add_table(
        document,
        ("时窗", "用途", "解释边界"),
        (
            ("50–245 s", "当前模型与实测的直接波和早期尾波", "可比较早期形态，不能验证完整月震尾波"),
            ("70–180 s", "最佳时移、相关和相位形态", "避免长尾主导源尺度"),
            ("峰后20 s", "快速或M1短td敏感性", "M2–M4通常不足1–1.2个e折"),
            ("峰后60 s", "当前统一早期td/Qc", "需移动40 s窗报告不确定性"),
            ("100–500 s", "低速层重算后的早期尾波", "模拟先延长到600 s"),
            ("500–1200 s", "实测长尾与局部模型缺失诊断", "不强求局部模型逐点拟合"),
            ("至3000 s", "观测总能量和全球机制", "需更大域、球形传播、Qi与边界共同验证"),
        ),
        (1300, 3000, 5060),
        font_size=8.5,
    )
    add_figure(document, KEY_FIGURES["tmax_distance"], "图10　四模型峰值能量时间随震中距变化，并附三条射线路径地形。", width=6.25, alt_text="能量峰值时间与震中距")
    add_figure(document, KEY_FIGURES["linear_diffusion"], "图11　12组线性与R²扩散形式拟合：所有组合均偏好线性。", width=6.25, alt_text="线性和扩散拟合比较")


def add_literature(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "7　文献方法在本数据中的应用", 1)
    add_callout(document, "本章定位", "五篇论文只作为数据处理、指标定义和解释边界的方法依据。本报告不单独复述这些论文的样例结论，而是说明每项方法怎样作用于你的四个station.nc、A16S12真实三分量和三条传播路径。")
    add_table(
        document,
        ("参考方法", "在你的数据中的实现", "你的数据给出的结果", "使用边界"),
        (
            ("分频带Hilbert包络与td/Qc", "0.3–0.5、0.5–0.7、0.7–0.9及总频带；峰后尾波拟合", "随机散射和地形均延长早期td；高频td较短但有效Qc升高", "当前Qc不能直接当作Qi"),
            ("多平滑窗tmax", "5、10、20周期及5–100 s六个窗口", "M2相对M1延迟方向稳健；观测与模型tmax范围完全分离", "精确秒数依赖平滑尺度"),
            ("脉冲性SNR", "主峰附近RMS与紧随尾波RMS之比", "M1最尖锐、M4最弥散，四模型清楚分离", "不是仪器噪声SNR"),
            ("路径/盆缘思路", "用路径累计高差和平均坡度替代只看台站高程", "射线2盆缘散焦最强，射线3早期粗糙度和多脉冲最强", "当前为地表投影直线，不是Fresnel体"),
            ("低速层端元", "1 km、Vp=1.38、Vs=1.11 km/s作为主候选，并设温和/强端元", "静态延迟仅约0.8 s，但预期会改变反射、陷获、频散和模式转换", "必须重算，不能事后平移"),
            ("线性与扩散距离律", "12组tmax(R)分别拟合a+bR和a+cR²", "12组全部显著偏好线性，当前模拟仍由弹道传播主导", "真实S12单点不能拟合观测距离律"),
        ),
        (1650, 2850, 3000, 1860),
        font_size=7.8,
    )
    add_heading(document, "7.1　对你的论文最重要的方法性修正", 2)
    applications = (
        "把tmax、上升历时、td和Qc分开命名，避免把能量峰值时间误称为衰减时间或首波到时。",
        "所有包络峰值必须报告平滑窗敏感性；当前A16S12与模型差距在5–100 s窗口下仍完全稳健。",
        "当前td采用60 s早期尾波窗，并用移动40 s窗评估时变性；只在固定定义下比较四模型。",
        "路径解释必须使用累计高差和坡度，不能只用台站点位高程；射线2和3的差异已由同距离波形验证。",
        "长尾不能被自动等同于随机散射；你的M3和低速层候选都可产生确定性展宽，但其波形随机性、模态混合和距离规律不同。",
        "真实对比必须保持一个三分量源尺度，并把相位相关、包络相关、累计能量和SH比例联合使用。",
        "线性tmax(R)说明当前模拟尚未进入强扩散状态，因此论文结论应限定为早期地形改造和有限尾波展宽。",
        "低速层、散射、Qi和模型范围存在权衡；下一轮应采用正交模型矩阵，而不是一次只调源振幅。",
    )
    for application in applications:
        add_numbered(document, application)


def add_reviewer_matrix(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "8　审稿意见对应修改矩阵", 1)
    rows = (
        ("模型过于简化、浅层速度过快", "统一加入可分辨低速层，补密度、梯度和网格检查；结论限于早期局部传播", "低速层图、候选矩阵、第5章"),
        ("缺少三维内部非均匀性", "用M2/M4随机散射量化三维非均匀效应，同时承认强度和尺度仍不足", "C02–C03、C07、C24、三分量SH"),
        ("陨石坑地下地质未考虑", "明确地形独立效应与真实地质耦合的边界，建议低速层×散射×地形扩展", "第5、9章"),
        ("波形比较不够定量", "加入32条波形图证、包络、累计能量、相关、SNR、因子效应和空间块统计", "第2章全部图卡"),
        ("地形散射与速度散射不应绝对区分", "改写为几何边界与介质非均匀性的等效散射表述，重点讨论可观测差异", "C04、C07、讨论边界"),
        ("多曲线叠加和独立归一化误导", "统一共享尺度、增加透明度；射线图采用垂直offset，仅解释形状", "图1、图4a–c"),
        ("横向分量不能称为衰减", "改为P-SV向SH/T能量转换；按SAC方位校正", "第4章、SH能量比例"),
        ("坡度、曲率等也控制放大", "路径高差和平均坡度已量化；曲率和坡向列为下一步", "C05–C06、第3章"),
        ("地形分辨率阈值需定量", "原审稿回复给出0.5 km/pixel临界尺度；本报告注明它来自独立分辨率试验", "审稿回复Figure R3/R4/R7"),
        ("频谱解释复杂且不一致", "删除缺乏稳健关系的定性频谱结论，只保留可重复主频与频谱软化结果", "C13–C14、C19"),
        ("包络平滑不足", "使用5、10、20、40、60、100 s或5/10/20周期多窗，报告范围", "C01、C21、第6章"),
        ("线性上升时间与扩散R²/D矛盾", "12/12组均偏好线性；明确当前波场弹道主导，地形散射不能解释观测包络", "C29–C32、图11"),
        ("通俗摘要术语过专", "将散射解释为波被裂隙/起伏反复改变方向，将尾波解释为主震动后的持续振动", "建议修改Plain Language Summary"),
    )
    add_table(document, ("审稿问题", "修改与回答", "证据位置"), rows, (2300, 4800, 2260), font_size=8.0)
    add_callout(document, "关键措辞", "修改稿应写成“地形能够改造早期波形并延长有限时长尾波”，不应写成“地形散射能够解释Apollo月震完整包络”。线性tmax(R)、真实能量峰值延迟和250 s能量缺失共同支持这一收紧。")


def add_final_recommendations(document: Document) -> None:
    heading = add_heading(document, "9　最终论文表述、限制与下一轮试验", 1)
    heading.paragraph_format.page_break_before = True
    add_heading(document, "9.1　可以直接写入论文的综合结论", 2)
    statements = (
        "随机散射是平坦模型中最强的波列展宽机制，稳定降低主波、总能量和脉冲性并延长尾波。",
        "起伏自由表面即使没有随机速度扰动，也可通过多路径、反射和绕射增加低振幅晚到能量并造成有限展宽；当前波形没有形成清晰的强弥散尾波，不能据此声称出现了明显随机散射。",
        "地形作用由整条传播路径控制；累计高差是振幅、能量和持续时间的最稳定解释量，平均坡度更接近波形畸变控制量。",
        "地形与随机散射显著非加性；组合模型不能由M2与M3的简单线性叠加预测。",
        "A16S12真实三分量显示当前模型初始到时量级大致合理，但包络峰值、能量累积、SH比例和波形形状均显著失配。",
        "现有12组tmax—距离关系均为弹道型线性而非强扩散R²形式，因此地形与当前散射参数不足以解释Apollo长包络。",
        "低速层是必须补充的一级机制，但它不能单独替代散射、高Qi、全球回返和横向地质结构。",
        "当前250 s记录足以估计统一早期td，不足以把Qc解释为Qi，也不足以验证实测95%能量约2800 s的长尾。",
    )
    for statement in statements:
        add_numbered(document, statement)
    add_heading(document, "9.2　不能从当前数据推出", 2)
    limitations = (
        "不能从当前有效Qc直接反演真实月球Qi或唯一Qsc。",
        "不能由三条路径的转折点反演统一散射层厚度或唯一地形泄漏距离。",
        "不能从单一A16S12观测建立实测距离幂律。",
        "不能把单台站qP/qSV代理分解视为严格P/SV波场分离。",
        "不能把局部300 km笛卡尔域的缺失长尾全部归因于低速层或散射参数。",
        "不能把地形独立试验直接等同于真实陨石坑地下地质的全部效应。",
    )
    for item in limitations:
        add_bullet(document, item)
    add_heading(document, "9.3　下一轮优先级", 2)
    priorities = (
        "P0：四模型统一加入LVL-B低速层，并用阶跃/平滑接口各重算一组。",
        "P0：输出至600 s并依据末端能量阈值决定是否延长到1000–1200 s。",
        "P0：补充低速层密度与阻抗敏感性，核查0.9 Hz网格色散。",
        "P1：增加3–5个散射随机种子，区分随机实现方差和稳定效应。",
        "P1：输出三分量波场快照、散度/旋度和能量通量，验证P-SV-SH转换。",
        "P1：在射线2盆缘与射线3早期粗糙段布设二维台阵，使用Fresnel走廊统计。",
        "P2：增加多个撞击事件—台站距离组合，严格检验观测tmax(R)与R²/D。",
        "P2：若论文目标包含千秒级尾波，改用更大域或球形能量传播框架并联合Qi。",
    )
    for priority in priorities:
        add_numbered(document, priority)
    add_callout(document, "一句话结论", "当前四模型的价值在于分离早期地形与随机散射效应；要逼近真实A16S12，必须同时补入可分辨低速层、更强/更合理的三维散射、高Qi约束和更长或更全球的能量传播。", fill=PALE_GOLD, border=GOLD)


def add_reproducibility_appendix(document: Document) -> None:
    document.add_page_break()
    add_heading(document, "附录　脚本、输出文件与一键复现", 1)
    add_heading(document, "A.1　一键运行", 2)
    paragraph = document.add_paragraph()
    run = paragraph.add_run("python run_complete_analysis.py --check-only\npython run_complete_analysis.py")
    set_run_font(run, name="Consolas", size=9.5, color=DEEP_BLUE)
    add_paragraph(document, "第一条命令检查四个station.nc、地形文件和真实三分量；第二条依次生成波形图、因子分析、论文方法分析、三分量分析、路径分析、32条证据图和本Word报告。")
    add_heading(document, "A.2　脚本职责", 2)
    script_rows = (
        ("plot_releasy_waveform_comparison.py", "读取四个NetCDF、0.3–0.9 Hz滤波、S12/三射线/实测对比、主频、tmax距离拟合"),
        ("analyze_releasy_relationships.py", "台站级振幅、能量、持续时间、路径地形、2×2因子、空间块相关与稳健性"),
        ("analyze_releasy_literature_guided.py", "分频带包络、tmax平滑敏感性、td/Qc、SNR、频谱软化、转折与空间滞后"),
        ("analyze_three_component_psvsh.py", "SAC方位校正、606台站ZRT旋转、因子差分/交互项、时变偏振、时频对比、qP/qSV/SH代理与低速层诊断"),
        ("generate_path_based_ray_analysis.py", "路径剖面、累计高差、平均坡度、同距离实例、路径结论与CSV"),
        ("generate_conclusion_waveform_atlas.py", "自动选择代表台站并生成32张波形证据卡和8页图册"),
        ("build_complete_rel3_report.py", "整合全部方法、结论、图、审稿修改、论文导读并建立交付包"),
        ("run_complete_analysis.py", "输入检查和完整流水线调度"),
    )
    add_table(document, ("脚本", "功能"), script_rows, (3400, 5960), font_size=8.4)
    add_heading(document, "A.3　主要机器可读输出", 2)
    outputs = (
        "releasy_waveform_figures_python/*.csv：原始主频、tmax、线性/扩散拟合、真实—模型指标。",
        "releasy_relationship_analysis/*.csv：台站级基础指标、路径关系、因子效应与稳健性。",
        "releasy_relationship_analysis/literature_guided/*.csv：分频带、td/Qc、SNR、转折、空间滞后与空间块区间。",
        "three_component_psvsh_analysis/*.csv：模态能量、长尾、最佳对齐、606台站三分量占比、因子差分/交互项、S12时变偏振及时频指标。",
        "path_based_ray_analysis/*.csv：路径采样、射线汇总、同距离实例与最强路径相关。",
        "conclusion_evidence/conclusion_evidence_index.csv：32条结论、代表台站、图件和证据来源索引。",
    )
    for item in outputs:
        add_bullet(document, item)
    add_heading(document, "A.4　参考论文", 2)
    references = (
        "Blanchette-Guertin et al. (2012), Investigation of scattering in lunar seismic coda, JGR, doi:10.1029/2011JE004042.",
        "Blanchette-Guertin et al. (2015), Modeling seismic energy propagation in highly scattering environments, JGR Planets, doi:10.1002/2014JE004654.",
        "Blanchette-Guertin et al. (2015), Effects of lateral variations in megaregolith thickness on predicted lunar seismic signals, GRL, doi:10.1002/2015GL066151.",
        "Burmin et al. (2016), On the nature of the seismic ringing of the Moon: Analytical modeling, Planetary and Space Science, doi:10.1016/j.pss.2016.03.013.",
        "Gillet et al. (2017), Scattering attenuation profile of the Moon, PEPI, doi:10.1016/j.pepi.2016.11.001.",
    )
    for reference in references:
        add_bullet(document, reference)


def write_text_report(conclusion_rows: list[dict[str, str]]) -> None:
    lines = [
        "# REL3月震四模型完整综合报告（文本索引）",
        "",
        "完整排版、全部图件、表格、论文图导读和脚本说明见同目录Word文档。",
        "",
        "## 32条结论",
        "",
    ]
    for index, (row, detail) in enumerate(zip(conclusion_rows, CONCLUSION_DETAILS, strict=True), start=1):
        lines.extend((f"### C{index:02d} {row['title']}", "", detail, "", f"波形判据：{row['takeaway']}", ""))
    lines.extend(("## 路径结论", ""))
    lines.extend(f"{index}. {text}" for index, text in enumerate(PATH_CONCLUSIONS, start=1))
    lines.extend(("", "## 三分量结论", ""))
    lines.extend(f"{index}. {text}" for index, text in enumerate(THREE_COMPONENT_CONCLUSIONS, start=1))
    lines.extend(("", "## 地形与散射加入前后的三分量变化", ""))
    lines.extend(f"{index}. {text}" for index, text in enumerate(FIELD_COMPONENT_CONCLUSIONS, start=1))
    lines.extend(("", "## 因子差分、时变偏振与时频结论", ""))
    lines.extend(f"{index}. {text}" for index, text in enumerate(EXTENDED_COMPONENT_CONCLUSIONS, start=1))
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_document() -> None:
    require_inputs()
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    document = Document()
    configure_document(document)
    add_cover(document)
    add_contents(document)
    add_data_methods(document)
    add_conclusion_atlas(document)
    add_path_analysis(document)
    add_observed_three_component(document)
    add_low_velocity_layer(document)
    add_td_window_analysis(document)
    add_literature(document)
    add_reviewer_matrix(document)
    add_final_recommendations(document)
    add_reproducibility_appendix(document)
    core = document.core_properties
    core.title = "REL3月震四模型：数据处理、图表证据与完整综合报告"
    core.subject = "地形、随机散射、A16S12真实三分量、低速层、td/Qc及审稿修改"
    core.author = "OpenAI Codex"
    core.keywords = "月震, CGFD3D, 地形, 散射, 低速层, A16S12, tmax, td, Qc, P-SV-SH"
    settings = document.settings._element
    update_fields = settings.find(qn("w:updateFields"))
    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        settings.append(update_fields)
    update_fields.set(qn("w:val"), "true")
    document.save(REPORT_DOCX)
    write_text_report(read_csv(CONCLUSION_INDEX))


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def prepare_package() -> None:
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    for name in SCRIPT_FILES:
        source = ROOT / name
        if source.is_file():
            copy_file(source, DELIVERY_DIR / name)
    for source in REPORT_SOURCE_FILES:
        if source.is_file():
            copy_file(source, DELIVERY_DIR / "reports_source" / source.name)
    for source in (ROOT / "conclusion_evidence" / "cards").glob("*.png"):
        copy_file(source, DELIVERY_DIR / "figures" / "conclusion_cards" / source.name)
    for label, source in KEY_FIGURES.items():
        copy_file(source, DELIVERY_DIR / "figures" / "key" / f"{label}_{source.name}")
    legacy_literature_dir = DELIVERY_DIR / "figures" / "literature"
    if legacy_literature_dir.exists():
        legacy_literature_dir.resolve().relative_to(DELIVERY_DIR.resolve())
        shutil.rmtree(legacy_literature_dir)
    csv_roots = (
        ROOT / "releasy_waveform_figures_python",
        ROOT / "releasy_relationship_analysis",
        ROOT / "three_component_psvsh_analysis",
        ROOT / "path_based_ray_analysis",
        ROOT / "conclusion_evidence",
    )
    for csv_root in csv_roots:
        for source in csv_root.rglob("*.csv"):
            relative = source.relative_to(ROOT)
            copy_file(source, DELIVERY_DIR / "tables" / relative)
    readme = f"""# REL3完整分析交付包

## 直接阅读

- `document/{REPORT_DOCX.name}`：包含全部方法、32条图证结论、路径分析、地形/散射三分量变化、低速层、td/Qc、文献方法应用和审稿修改。
- `document/{REPORT_MD.name}`：全部结论的纯文本索引。

## 一键复现

```powershell
python run_complete_analysis.py --check-only
python run_complete_analysis.py
```

安装依赖：`pip install -r requirements-complete-analysis.txt`。

脚本保留原始数据绝对路径；如数据移动，请修改 `plot_releasy_waveform_comparison.py` 顶部的 `MODELS`、`OBSERVED_COMPONENT_FILES` 和 `TOPOGRAPHY_FILE`。

## 目录

- `figures/conclusion_cards`：32条波形证据图。
- `figures/key`：S12、三条路径、因子差分/交互项、时变偏振、时频对比、P-SV-SH和低速层等主图。
- `tables`：全部关键CSV结果，包括606台站指标。
- `reports_source`：各阶段中文分析报告。
"""
    (DELIVERY_DIR / "README.md").write_text(readme, encoding="utf-8")
    with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in DELIVERY_DIR.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(DELIVERY_DIR.parent))


def main() -> None:
    build_document()
    prepare_package()
    print(REPORT_DOCX)
    print(REPORT_MD)
    print(ZIP_FILE)


if __name__ == "__main__":
    main()
