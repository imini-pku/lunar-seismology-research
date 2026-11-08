"""Generate waveform-first evidence cards for all report conclusions."""

from __future__ import annotations

import csv
import math
import sys
import textwrap
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_PACKAGES = SCRIPT_DIR.parent / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from netCDF4 import Dataset
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, detrend, hilbert, sosfiltfilt

from plot_releasy_waveform_comparison import (
    MODELS,
    build_station_geometry,
    load_observed_s12,
    load_s12_model_components,
    source_matching_scale,
    total_energy_intensity,
)


LITERATURE_DIR = SCRIPT_DIR / "releasy_relationship_analysis" / "literature_guided"
WAVEFORM_DIR = SCRIPT_DIR / "releasy_waveform_figures_python"
OUTPUT_DIR = SCRIPT_DIR / "conclusion_evidence"
CARD_DIR = OUTPUT_DIR / "cards"
ATLAS_DIR = OUTPUT_DIR / "atlas"
FIGURE_DPI = 190

MODEL_NAMES = ("M1", "M2", "M3", "M4")
MODEL_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")
OBSERVED_COLOR = "#222222"
ACCENT = "#7A5195"
NEUTRAL = "#777777"
RAY_COLORS = ("#4477AA", "#EE6677", "#228833")
EPSILON = 1.0e-30
BROAD_BAND = (0.3, 0.9)
SUB_BANDS = ((0.3, 0.5), (0.5, 0.7), (0.7, 0.9))


@dataclass(frozen=True)
class Conclusion:
    identifier: int
    slug: str
    title: str
    takeaway: str
    sources: str


@dataclass
class RawModel:
    name: str
    color: str
    time: np.ndarray
    waveforms: np.ndarray


CONCLUSIONS = (
    Conclusion(1, "scatter-tmax-smoothing", "随机散射稳定推迟能量峰值，但延迟依赖平滑尺度", "同一代表台站在5、10、20周期平滑下都显示M2峰值晚于M1，但峰值位置会随平滑窗移动。", "station.nc + tmax_smoothing_sensitivity.csv"),
    Conclusion(2, "scatter-broadening", "随机散射最稳定的表现是波列全面展宽", "代表台站中M2主脉冲变宽、上升变慢且尾波更长，展宽不是单一数值造成的视觉假象。", "station.nc + station_metrics.csv"),
    Conclusion(3, "scatter-amplitude-energy-snr", "随机散射降低主波幅、总能量和脉冲性", "共享振幅尺度下，M2主脉冲和累计能量均低于M1，同时晚到能量比例增加。", "station.nc + station_metrics.csv"),
    Conclusion(4, "topography-scatter-like", "起伏地形造成有限展宽，但没有形成明显弥散尾波", "M3相对M1的能量窗和拟合衰减时间增大，但差异主要位于低振幅尾部；该图支持弱地形多路径效应，不足以证明强随机散射。", "station.nc + station_metrics.csv"),
    Conclusion(5, "path-relief-control", "路径高差相关主要由射线2、3贡献", "去除震中距后，射线2、3的路径高差与M3−M1振幅、能量和持续时间关系明显；射线1在无散射背景下的对应相关接近零，不能视为三条路径共有规律。", "station.nc + terrain station metrics"),
    Conclusion(6, "mean-slope-waveform", "平均坡度更接近完整波形畸变，而非单一到时", "近似同距离台站表明，路径平均坡度增大时，振幅、尾波和包络宽度会一起改变。", "station.nc + terrain station metrics"),
    Conclusion(7, "nonlinear-saturation", "地形与散射存在显著饱和型非加性耦合", "同一台站的增量波形显示，地形在无散射背景中的影响明显大于其在散射背景中的附加影响。", "station.nc + factorial station metrics"),
    Conclusion(8, "model-snr-separation", "脉冲性 SNR 清楚区分四种模型", "四模型归一化波形的尖锐程度依次分离：M1最集中，M4最弥散。", "station.nc + station_metrics.csv"),
    Conclusion(9, "topography-neutral-median", "散射背景中地形的总体振幅/能量效应接近中性", "两个代表台站分别显示M4相对M2聚焦和散焦，局部效应方向相反，因此总体中位数接近中性。", "station.nc + station_metrics.csv"),
    Conclusion(10, "terrain-signature-persistence", "振幅、能量和持续时间的地形空间指纹可穿过散射背景", "同一高起伏台站中，M3-M1与M4-M2都留下相似的振幅和尾波改造痕迹。", "station.nc + signature_persistence.csv"),
    Conclusion(11, "ray2-strongest", "射线2是散射和地形共同作用最强的路径", "三条射线各取代表台站后，射线2的M2相对M1包络展宽和尾波增强最突出。", "station.nc + ray-wise effects"),
    Conclusion(12, "ray1-envelope-change", "射线1振幅损失弱，但包络仍受地形影响", "共享振幅尺度下M1/M3主脉冲接近，但M3包络更宽、尾波更持久。", "station.nc + ray1 station metrics"),
    Conclusion(13, "frequency-dependent-coda", "高频尾波按秒衰减更快，但有效 Qc 随频率升高", "同一台站三个频带的对数包络和拟合线直接显示：高频衰减斜率更陡，但频率因子使有效Qc升高。", "station.nc + frequency metrics"),
    Conclusion(14, "spectral-softening", "平坦散射模型表现出最强尾波频谱软化", "M2晚窗相对早窗的频谱曲线向高频下降最明显，且对应波形尾部高频细节最先消失。", "station.nc + spectral station metrics"),
    Conclusion(15, "qc-not-qi", "当前有效 Qc 不能解释为内禀吸收 Qi", "同一条尾波在三个移动窗口得到明显不同的衰减斜率，说明有效Qc包含窗口和散射演化。", "station.nc + moving-window coda fits"),
    Conclusion(16, "no-common-breakpoint", "三条路径没有共享单一散射层转折距离", "各射线在各自统计转折点前后的代表波形变化方式不同，不能归并成统一层厚。", "station.nc + breakpoints.csv"),
    Conclusion(17, "no-unique-spatial-lag", "当前数据无法给出唯一地形影响“泄漏距离”", "三条射线按各自最佳距离偏移后，地形扰动波形仍不能稳定对齐，且所需偏移方向不一致。", "station.nc + spatial_lags.csv"),
    Conclusion(18, "combined-diagnostic", "最可靠判据是包络展宽 + 脉冲性 + 路径地形", "同一台站的四模型波形与路径地形放在一起后，可同时判断波列展宽、脉冲性和地形背景。", "station.nc + topography profile"),
    Conclusion(19, "observed-dominant-frequency", "真实A16S12三分量主频稳定集中在约0.43 Hz", "观测三分量时序和频谱峰彼此一致，而模型S12平均频谱峰整体偏高。", "A16S12 three-component waveforms"),
    Conclusion(20, "onset-versus-envelope", "初始能量时间大体相容，但包络演化完全不相容", "观测和模型都在约80-100秒起振；此后模型迅速衰减而观测包络继续增强。", "A16S12 + modeled S12 waveforms"),
    Conclusion(21, "observed-tmax-gap", "观测三分量能量峰值远晚于所有模型", "归一化三分量能量包络显示，模型峰值都在百秒内，观测峰值延迟至约六百秒以后。", "A16S12 + modeled S12 envelopes"),
    Conclusion(22, "small-model-delays", "地形和随机散射只产生小幅峰值延迟", "早期放大图中四模型峰值只相差数秒；完整时间轴上这一差异远小于观测峰值延迟。", "A16S12 + modeled S12 envelopes"),
    Conclusion(23, "rise-duration-gap", "观测上升过程比模型长一个至两个数量级", "从5%累计能量到包络峰值的阴影区间显示，观测跨越数百秒，模型仅跨越数秒到十余秒。", "A16S12 cumulative energy + envelopes"),
    Conclusion(24, "scatter-extends-t95", "随机散射延长合成尾波，但强度仍不足", "累积能量曲线中M2/M4晚于M1到达95%，但仍在约160秒结束，远早于观测。", "A16S12 cumulative energy"),
    Conclusion(25, "topography-weaker-than-scatter", "地形单独作用的尾波延长弱于当前随机散射", "合成记录累积能量曲线显示M3最接近M1，M2和M4的尾部延长更明显。", "modeled S12 cumulative energy"),
    Conclusion(26, "observed-energy-fraction", "真实记录前250 s仅包含约3.98%的总能量", "观测波形、包络和累积能量共同显示，250秒截点只覆盖初始波列，主要能量仍在其后。", "A16S12 waveform and cumulative energy"),
    Conclusion(27, "low-waveform-similarity", "统一源能量后，早期相位波形相似性仍很低", "三个分量逐一叠加后，四模型都无法跟随观测的相位和振幅起伏，差异不是单一分量造成。", "source-matched A16S12 waveforms"),
    Conclusion(28, "negative-envelope-correlation", "早期三分量包络甚至呈负相关", "观测包络在模型主脉冲衰减时仍继续增强，峰谷关系相反；小幅时移不能改变整体趋势。", "source-matched A16S12 envelopes"),
    Conclusion(29, "linear-beats-diffusion", "12组距离关系全部支持线性而非R²形式", "波形剖面的能量脊随距离近似直线移动；线性轨迹沿脊通过，而R²轨迹系统弯离。", "station.nc + peak-time fits"),
    Conclusion(30, "ballistic-dominance", "当前模拟仍由弹道传播主导", "射线2波形剖面的主脉冲形成清晰直线到时脊，扩散型曲线不能沿主能量传播。", "station.nc + peak-time fits"),
    Conclusion(31, "single-observed-anchor", "真实S12单点不能建立观测距离幂律", "合成波形提供完整距离剖面，而真实数据仅在约152千米处提供一条长尾记录，无法拟合距离趋势。", "synthetic waveform section + A16S12"),
    Conclusion(32, "extend-synthetics", "下一步应延长记录并重构散射层，而非只调源振幅", "同一时间轴上，四模型在250秒终止而观测持续至3000秒以上，延长记录是检验长尾机制的前提。", "A16S12 + modeled S12 envelopes"),
)


def configure_fonts() -> None:
    for candidate in (Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")):
        if candidate.is_file():
            font_manager.fontManager.addfont(str(candidate))
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(candidate)).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 9.2


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: str | float | int | None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


STATION_ROWS = read_csv_rows(LITERATURE_DIR / "literature_guided_station_metrics.csv")
TERRAIN_RELATIONSHIP_ROWS = read_csv_rows(LITERATURE_DIR / "literature_guided_terrain_relationships.csv")
BREAKPOINT_ROWS = read_csv_rows(LITERATURE_DIR / "literature_guided_breakpoints.csv")
SPATIAL_LAG_ROWS = read_csv_rows(LITERATURE_DIR / "literature_guided_spatial_lags.csv")
OBSERVED_METRIC_ROWS = read_csv_rows(WAVEFORM_DIR / "A16S12_observed_model_comparison_metrics.csv")
DISTANCE_FIT_ROWS = read_csv_rows(WAVEFORM_DIR / "figure5b_peak_time_fit_summary.csv")
ROW_BY_INDEX = {int(row["station"][1:]) - 1: row for row in STATION_ROWS}
STATION_XY, RAY_STATION_INDICES = build_station_geometry()


def load_raw_model(model_index: int) -> RawModel:
    config = MODELS[model_index]
    with Dataset(config.nc_file, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        waveforms = np.asarray(dataset.variables["Vz"][:], dtype=np.float32)
    if waveforms.shape == (time.size, 606):
        waveforms = waveforms.T
    if waveforms.shape != (606, time.size):
        raise ValueError(f"Unexpected Vz shape {waveforms.shape} in {config.nc_file}")
    return RawModel(config.name, config.color, time, waveforms)


RAW_MODELS = tuple(load_raw_model(index) for index in range(4))
OBSERVED_RECORD = load_observed_s12()
MODEL_RECORDS = tuple(load_s12_model_components(config) for config in MODELS)
SOURCE_SCALES = tuple(source_matching_scale(OBSERVED_RECORD, record) for record in MODEL_RECORDS)
SELECTION_NOTES: dict[int, str] = {}


def primary_rows(ray: int | None = None) -> list[dict[str, str]]:
    rows = [row for row in STATION_ROWS if row["included_in_primary_analysis"] == "1"]
    if ray is not None:
        rows = [row for row in rows if row["ray"] == str(ray)]
    return rows


def station_index(row: dict[str, str]) -> int:
    return int(row["station"][1:]) - 1


def station_label(index: int) -> str:
    row = ROW_BY_INDEX[index]
    return f"{row['station']} · 射线{row['ray']} · {number(row['distance_km']):.1f} km"


def select_representative(columns: tuple[str, ...], ray: int | None = None) -> int:
    rows = primary_rows(ray)
    matrix = np.asarray([[number(row[column]) for column in columns] for row in rows], dtype=float)
    valid = np.all(np.isfinite(matrix), axis=1)
    rows = [row for row, keep in zip(rows, valid, strict=True) if keep]
    matrix = matrix[valid]
    target = np.median(matrix, axis=0)
    scale = np.maximum(np.subtract(*np.percentile(matrix, [75, 25], axis=0)), 1.0e-6)
    scores = np.sum(((matrix - target) / scale) ** 2, axis=1)
    return station_index(rows[int(np.argmin(scores))])


def select_quantile(column: str, quantile: float, ray: int | None = None) -> int:
    rows = primary_rows(ray)
    values = np.asarray([number(row[column]) for row in rows], dtype=float)
    valid = np.isfinite(values)
    rows = [row for row, keep in zip(rows, valid, strict=True) if keep]
    values = values[valid]
    target = float(np.quantile(values, quantile))
    return station_index(rows[int(np.argmin(np.abs(values - target)))])


def matched_feature_pair(column: str, ray: int | None = None, tolerance_km: float = 5.0) -> tuple[int, int]:
    rows = primary_rows(ray)
    values = np.asarray([number(row[column]) for row in rows], dtype=float)
    distances = np.asarray([number(row["distance_km"]) for row in rows], dtype=float)
    low_limit, high_limit = np.quantile(values[np.isfinite(values)], [0.2, 0.8])
    low_candidates = np.flatnonzero(values <= low_limit)
    high_candidates = np.flatnonzero(values >= high_limit)
    best: tuple[float, int, int] | None = None
    for low_index in low_candidates:
        for high_index in high_candidates:
            distance_gap = abs(distances[low_index] - distances[high_index])
            if distance_gap > tolerance_km:
                continue
            score = values[high_index] - values[low_index] - 0.05 * distance_gap
            if best is None or score > best[0]:
                best = (score, low_index, high_index)
    if best is None:
        return select_quantile(column, 0.2, ray), select_quantile(column, 0.8, ray)
    return station_index(rows[best[1]]), station_index(rows[best[2]])


def select_saturation_station() -> int:
    best_score = -np.inf
    best_station = 0
    for row in primary_rows():
        values = (
            number(row["scatter_flat__broad__log_duration_90_s"]),
            number(row["scatter_topography__broad__log_duration_90_s"]),
            number(row["topography_no_scatter__broad__log_duration_90_s"]),
            number(row["topography_scatter__broad__log_duration_90_s"]),
        )
        if not np.all(np.isfinite(values)):
            continue
        score = values[0] - values[1] + values[2] - values[3]
        if score > best_score:
            best_score = score
            best_station = station_index(row)
    return best_station


def select_frequency_trend_station(model: str = "M2") -> int:
    columns = tuple(
        f"{model}__{band}__{metric}"
        for metric in ("log_decay_td_s", "log_effective_qc")
        for band in ("low", "middle", "high")
    )
    rows = primary_rows()
    matrix = np.asarray([[number(row[column]) for column in columns] for row in rows], dtype=float)
    valid = np.all(np.isfinite(matrix), axis=1)
    valid &= matrix[:, 0] > matrix[:, 2]
    valid &= matrix[:, 5] > matrix[:, 3]
    rows = [row for row, keep in zip(rows, valid, strict=True) if keep]
    matrix = matrix[valid]
    target = np.median(matrix, axis=0)
    scale = np.maximum(np.subtract(*np.percentile(matrix, [75, 25], axis=0)), 1.0e-6)
    scores = np.sum(((matrix - target) / scale) ** 2, axis=1)
    return station_index(rows[int(np.argmin(scores))])


def select_softening_station() -> int:
    columns = tuple(f"{model}__spectral_softening_log_ratio" for model in MODEL_NAMES)
    rows = primary_rows()
    matrix = np.asarray([[number(row[column]) for column in columns] for row in rows], dtype=float)
    valid = np.all(np.isfinite(matrix), axis=1)
    valid &= matrix[:, 1] <= np.min(matrix, axis=1) + 1.0e-12
    rows = [row for row, keep in zip(rows, valid, strict=True) if keep]
    matrix = matrix[valid]
    target = np.median(matrix, axis=0)
    scale = np.maximum(np.subtract(*np.percentile(matrix, [75, 25], axis=0)), 1.0e-6)
    scores = np.sum(((matrix - target) / scale) ** 2, axis=1)
    return station_index(rows[int(np.argmin(scores))])


def nearest_station(ray: int, distance_km: float) -> int:
    rows = primary_rows(ray)
    return station_index(min(rows, key=lambda row: abs(number(row["distance_km"]) - distance_km)))


def select_one(rows: list[dict[str, str]], **criteria: str | int) -> dict[str, str]:
    matches = [row for row in rows if all(str(row.get(key)) == str(value) for key, value in criteria.items())]
    if len(matches) != 1:
        raise KeyError(f"Expected one row for {criteria}, found {len(matches)}")
    return matches[0]


@lru_cache(maxsize=1024)
def filtered_trace(model_index: int, station: int, low_hz: float = 0.3, high_hz: float = 0.9) -> np.ndarray:
    model = RAW_MODELS[model_index]
    sample_interval = float(np.median(np.diff(model.time)))
    sos = butter(4, (low_hz, high_hz), btype="bandpass", fs=1.0 / sample_interval, output="sos")
    prepared = detrend(np.asarray(model.waveforms[station], dtype=np.float64), type="linear")
    return sosfiltfilt(sos, prepared)


def rms_envelope(time: np.ndarray, trace: np.ndarray, smooth_s: float = 3.0) -> np.ndarray:
    intensity = np.abs(hilbert(trace)) ** 2
    samples = max(1, int(round(smooth_s / float(np.median(np.diff(time))))))
    return np.sqrt(np.maximum(uniform_filter1d(intensity, samples, mode="nearest"), 0.0))


def normalized(values: np.ndarray, scale: float | None = None) -> np.ndarray:
    denominator = float(np.max(np.abs(values))) if scale is None else float(scale)
    return values / max(denominator, EPSILON)


def trace_on_time(
    model_index: int,
    station: int,
    target_time: np.ndarray,
    low_hz: float = 0.3,
    high_hz: float = 0.9,
) -> np.ndarray:
    return np.interp(
        target_time,
        RAW_MODELS[model_index].time,
        filtered_trace(model_index, station, low_hz, high_hz),
        left=0.0,
        right=0.0,
    )


def station_window(index: int, before_s: float = 18.0, after_s: float = 75.0) -> tuple[float, float]:
    row = ROW_BY_INDEX[index]
    peak_times = [number(row[f"{model}__broad__tmax_s"]) for model in MODEL_NAMES]
    start = max(0.0, min(peak_times) - before_s)
    end = min(float(RAW_MODELS[0].time[-1]), max(peak_times) + after_s)
    return start, max(end, start + 45.0)


def clean_axis(axis: plt.Axes, grid_axis: str = "both") -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis=grid_axis, color="#B8B8B8", alpha=0.24, linewidth=0.65)
    axis.set_axisbelow(True)


def plot_model_lanes(
    axis: plt.Axes,
    station: int,
    model_indices: tuple[int, ...],
    window: tuple[float, float] | None = None,
    scale_mode: str = "each",
    smooth_s: float = 3.0,
    labels: tuple[str, ...] | None = None,
) -> None:
    time = RAW_MODELS[0].time
    if window is None:
        window = station_window(station)
    mask = (time >= window[0]) & (time <= window[1])
    traces = [trace_on_time(model_index, station, time) for model_index in model_indices]
    if scale_mode == "shared":
        shared = max(float(np.max(np.abs(trace[mask]))) for trace in traces)
        scales = [shared] * len(traces)
    elif scale_mode == "m1":
        reference = float(np.max(np.abs(trace_on_time(0, station, time)[mask])))
        scales = [reference] * len(traces)
    else:
        scales = [float(np.max(np.abs(trace[mask]))) for trace in traces]
    offsets = np.arange(len(model_indices) - 1, -1, -1, dtype=float)
    for lane, model_index, trace, scale in zip(offsets, model_indices, traces, scales, strict=True):
        waveform = trace[mask] / max(scale, EPSILON)
        envelope = rms_envelope(time, trace, smooth_s)[mask] / max(scale, EPSILON)
        color = MODEL_COLORS[model_index]
        axis.axhline(lane, color="#C8C8C8", linewidth=0.55)
        axis.plot(time[mask], lane + 0.32 * waveform, color=color, alpha=0.42, linewidth=0.55)
        axis.plot(time[mask], lane + 0.34 * envelope, color=color, linewidth=1.65)
    axis.set_xlim(*window)
    axis.set_ylim(-0.42, len(model_indices) - 0.38)
    axis.set_yticks(offsets, labels or tuple(MODEL_NAMES[index] for index in model_indices))
    axis.set_xlabel("时间（s）")
    axis.set_ylabel(station_label(station))
    clean_axis(axis, "x")


def plot_model_overlay(
    axis: plt.Axes,
    station: int,
    model_indices: tuple[int, ...],
    window: tuple[float, float] | None = None,
    shared_scale: bool = False,
    smooth_s: float = 3.0,
) -> None:
    time = RAW_MODELS[0].time
    if window is None:
        window = station_window(station)
    mask = (time >= window[0]) & (time <= window[1])
    traces = [trace_on_time(model_index, station, time) for model_index in model_indices]
    shared = max(float(np.max(np.abs(trace[mask]))) for trace in traces) if shared_scale else None
    for model_index, trace in zip(model_indices, traces, strict=True):
        scale = shared if shared is not None else float(np.max(np.abs(trace[mask])))
        waveform = trace[mask] / max(scale, EPSILON)
        envelope = rms_envelope(time, trace, smooth_s)[mask] / max(scale, EPSILON)
        axis.plot(time[mask], waveform, color=MODEL_COLORS[model_index], alpha=0.28, linewidth=0.55)
        axis.plot(time[mask], envelope, color=MODEL_COLORS[model_index], linewidth=1.8, label=MODEL_NAMES[model_index])
    axis.axhline(0, color="#999999", linewidth=0.6)
    axis.set_xlim(*window)
    axis.set_xlabel("时间（s）")
    axis.set_ylabel("波形 / RMS包络")
    axis.set_title(station_label(station), fontsize=9.5)
    axis.legend(ncol=len(model_indices), fontsize=7.5, loc="upper right")
    clean_axis(axis, "x")


def three_component_envelope(record_index: int, smooth_s: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
    if record_index == 0:
        record = OBSERVED_RECORD
        scale = 1.0
    else:
        record = MODEL_RECORDS[record_index - 1]
        scale = SOURCE_SCALES[record_index - 1]
    intensity = total_energy_intensity(record) * scale**2
    samples = max(1, int(round(smooth_s / float(np.median(np.diff(record.time))))))
    return record.time, np.sqrt(np.maximum(uniform_filter1d(intensity, samples, mode="nearest"), 0.0))


def cumulative_energy(record_index: int) -> tuple[np.ndarray, np.ndarray]:
    if record_index == 0:
        record = OBSERVED_RECORD
        scale = 1.0
    else:
        record = MODEL_RECORDS[record_index - 1]
        scale = SOURCE_SCALES[record_index - 1]
    intensity = total_energy_intensity(record) * scale**2
    cumulative = np.cumsum(intensity, dtype=np.float64)
    cumulative /= max(float(cumulative[-1]), EPSILON)
    return record.time, cumulative


def plot_observed_model_envelopes(
    axis: plt.Axes,
    end_s: float,
    normalize_each: bool = True,
    start_s: float = 0.0,
    smooth_s: float = 5.0,
) -> None:
    colors = (OBSERVED_COLOR, *MODEL_COLORS)
    labels = ("观测", *MODEL_NAMES)
    observed_time, observed_envelope = three_component_envelope(0, smooth_s)
    observed_mask = (observed_time >= start_s) & (observed_time <= end_s)
    reference_scale = float(np.max(observed_envelope[observed_mask]))
    for index, (color, label) in enumerate(zip(colors, labels, strict=True)):
        time, envelope = three_component_envelope(index, smooth_s)
        mask = (time >= start_s) & (time <= end_s)
        scale = float(np.max(envelope[mask])) if normalize_each else reference_scale
        axis.plot(time[mask], envelope[mask] / max(scale, EPSILON), color=color, linewidth=2.0 if index == 0 else 1.35, label=label)
    axis.set_xlim(start_s, end_s)
    axis.set_xlabel("撞击后时间（s）")
    axis.set_ylabel("三分量RMS能量包络")
    axis.legend(ncol=5, fontsize=7.2, loc="upper right")
    clean_axis(axis)


def plot_cumulative_lines(axis: plt.Axes, indices: tuple[int, ...], end_s: float) -> None:
    colors = (OBSERVED_COLOR, *MODEL_COLORS)
    labels = ("观测", *MODEL_NAMES)
    for index in indices:
        time, cumulative = cumulative_energy(index)
        mask = time <= end_s
        axis.plot(time[mask], cumulative[mask], color=colors[index], linewidth=2.0 if index == 0 else 1.55, label=labels[index])
    axis.axhline(0.95, color="#666666", linestyle="--", linewidth=0.8)
    axis.set_xlim(0, end_s)
    axis.set_ylim(-0.02, 1.03)
    axis.set_xlabel("撞击后时间（s）")
    axis.set_ylabel("累计记录能量比例")
    axis.legend(fontsize=7.5, ncol=min(5, len(indices)), loc="lower right")
    clean_axis(axis)


def relative_effect_waveform(model_a: int, model_b: int, station: int, relative_time: np.ndarray) -> np.ndarray:
    time = RAW_MODELS[0].time
    reference_peak = number(ROW_BY_INDEX[station][f"{MODEL_NAMES[model_a]}__broad__tmax_s"])
    effect = trace_on_time(model_b, station, time) - trace_on_time(model_a, station, time)
    return np.interp(relative_time + reference_peak, time, effect, left=0.0, right=0.0)


def fit_row(ray: int, model_index: int) -> dict[str, str]:
    return select_one(DISTANCE_FIT_ROWS, ray=ray, model=model_index + 1)


def plot_waveform_section(
    axis: plt.Axes,
    ray: int,
    model_index: int,
    stride: int = 15,
    end_s: float = 180.0,
    amplitude_km: float = 2.0,
) -> None:
    indices = RAY_STATION_INDICES[ray - 1][::stride]
    time = RAW_MODELS[model_index].time
    mask = (time >= 0) & (time <= end_s)
    for station in indices:
        distance = number(ROW_BY_INDEX[int(station)]["distance_km"])
        trace = filtered_trace(model_index, int(station))[mask]
        axis.plot(time[mask], distance + amplitude_km * normalized(trace), color=MODEL_COLORS[model_index], alpha=0.68, linewidth=0.55)
    axis.set_xlim(0, end_s)
    axis.set_xlabel("时间（s）")
    axis.set_ylabel("震中距（km）")
    clean_axis(axis)


def draw_conclusion_chart(identifier: int, axis: plt.Axes) -> None:
    if identifier == 1:
        station = select_representative(("scatter_flat__broad__tmax_5period_s", "scatter_flat__broad__tmax_10period_s", "scatter_flat__broad__tmax_20period_s"))
        time = RAW_MODELS[0].time
        window = station_window(station, 15.0, 65.0)
        mask = (time >= window[0]) & (time <= window[1])
        axis.axis("off")
        for row_index, periods in enumerate((5, 10, 20)):
            inset = axis.inset_axes([0.08, 0.67 - row_index * 0.30, 0.88, 0.26])
            for model_index in (0, 1):
                trace = trace_on_time(model_index, station, time)
                smooth_s = periods / 0.6
                envelope = rms_envelope(time, trace, smooth_s)
                values = normalized(envelope[mask])
                inset.plot(time[mask], values, color=MODEL_COLORS[model_index], linewidth=1.7, label=MODEL_NAMES[model_index])
                peak_time = float(time[mask][np.argmax(values)])
                inset.axvline(peak_time, color=MODEL_COLORS[model_index], linewidth=0.8, alpha=0.75)
            inset.set_ylabel(f"{periods}周期")
            inset.set_ylim(0, 1.08)
            if row_index < 2:
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("时间（s）")
            if row_index == 0:
                inset.legend(fontsize=7.2, ncol=2, loc="upper right")
            clean_axis(inset, "x")
        axis.set_title(station_label(station), fontsize=9.5)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 2:
        station = select_representative(("scatter_flat__broad__log_rise_time_s", "scatter_flat__broad__log_decay_td_s", "scatter_flat__broad__log_duration_90_s"))
        plot_model_lanes(axis, station, (0, 1), scale_mode="each", smooth_s=4.0)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 3:
        station = select_representative(("scatter_flat__broad__log_peak_amplitude", "scatter_flat__broad__log_total_energy", "scatter_flat__broad__log_impulsiveness_snr"))
        axis.axis("off")
        upper = axis.inset_axes([0.02, 0.48, 0.96, 0.50])
        lower = axis.inset_axes([0.08, 0.05, 0.88, 0.33])
        plot_model_lanes(upper, station, (0, 1), scale_mode="shared", smooth_s=3.0)
        time = RAW_MODELS[0].time
        window = station_window(station)
        mask = (time >= window[0]) & (time <= window[1])
        for model_index in (0, 1):
            energy = np.cumsum(np.abs(hilbert(trace_on_time(model_index, station, time))) ** 2)
            energy /= max(float(energy[-1]), EPSILON)
            lower.plot(time[mask], energy[mask], color=MODEL_COLORS[model_index], linewidth=1.8, label=MODEL_NAMES[model_index])
        lower.set_xlim(*window)
        lower.set_ylabel("全记录累计能量")
        lower.set_xlabel("时间（s）")
        lower.legend(fontsize=7.5)
        clean_axis(lower)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 4:
        station = select_representative(("topography_no_scatter__broad__log_rise_time_s", "topography_no_scatter__broad__log_duration_90_s", "topography_no_scatter__broad__log_impulsiveness_snr"))
        axis.axis("off")
        time = RAW_MODELS[0].time
        window = station_window(station, before_s=22.0, after_s=80.0)
        mask = (time >= window[0]) & (time <= window[1])
        smooth_s = 10.0 / np.mean(BROAD_BAND)
        traces = [trace_on_time(model_index, station, time) for model_index in (0, 2)]
        intensities = [np.abs(hilbert(trace)) ** 2 for trace in traces]
        smooth_samples = max(3, int(round(smooth_s / float(np.median(np.diff(time))))))
        envelopes = [
            np.sqrt(np.maximum(uniform_filter1d(intensity, smooth_samples, mode="nearest"), 0.0))
            for intensity in intensities
        ]
        shared_scale = max(float(np.max(envelope[mask])) for envelope in envelopes)

        upper = axis.inset_axes([0.03, 0.46, 0.95, 0.51])
        lower = axis.inset_axes([0.07, 0.05, 0.90, 0.31])
        row = ROW_BY_INDEX[station]
        metric_lines = []
        for model_index, trace, intensity, envelope in zip((0, 2), traces, intensities, envelopes, strict=True):
            color = MODEL_COLORS[model_index]
            label = MODEL_NAMES[model_index]
            upper.plot(time[mask], 0.48 * trace[mask] / max(shared_scale, EPSILON), color=color, alpha=0.28, linewidth=0.55)
            upper.plot(time[mask], envelope[mask] / max(shared_scale, EPSILON), color=color, linewidth=1.9, label=label)

            cumulative = np.cumsum(intensity, dtype=np.float64)
            cumulative /= max(float(cumulative[-1]), EPSILON)
            lower.plot(time[mask], cumulative[mask], color=color, linewidth=1.9, label=label)
            t05 = float(time[np.argmax(cumulative >= 0.05)])
            t95 = float(time[np.argmax(cumulative >= 0.95)])
            tmax = number(row[f"{label}__broad__tmax_s"])
            lower.scatter((t05, tmax, t95), (0.05, float(np.interp(tmax, time, cumulative)), 0.95), color=color, s=17, zorder=4)
            upper.axvline(tmax, color=color, linestyle=":", linewidth=0.9, alpha=0.9)

            rise_time = math.exp(number(row[f"{label}__broad__log_rise_time_s"]))
            duration_90 = math.exp(number(row[f"{label}__broad__log_duration_90_s"]))
            decay_td = math.exp(number(row[f"{label}__broad__log_decay_td_s"]))
            metric_lines.append(f"{label}: 上升={rise_time:.1f}s，5%–95%={duration_90:.1f}s，td={decay_td:.1f}s")

        upper.axhline(0, color="#999999", linewidth=0.55)
        upper.set_xlim(*window)
        upper.set_ylabel("共享尺度波形 / 10周期RMS包络")
        upper.set_title(f"{station_label(station)}；虚线为包络峰值", fontsize=9.0)
        upper.legend(fontsize=7.5, ncol=2, loc="upper right")
        upper.text(0.995, 0.66, "\n".join(metric_lines), transform=upper.transAxes, ha="right", va="top", fontsize=7.2,
                   bbox={"boxstyle": "round,pad=0.30", "facecolor": "white", "edgecolor": "#D0D0D0", "alpha": 0.90})
        clean_axis(upper, "x")

        lower.axhline(0.05, color="#888888", linestyle=":", linewidth=0.7)
        lower.axhline(0.95, color="#888888", linestyle="--", linewidth=0.7)
        lower.set_xlim(*window)
        lower.set_ylim(-0.02, 1.03)
        lower.set_xlabel("时间（s）")
        lower.set_ylabel("累计能量比例")
        lower.text(0.995, 0.08, "大倍率来自M1基准很短；M3增加的是弱晚到能量，并非清晰弥散波列。",
                   transform=lower.transAxes, ha="right", va="bottom", fontsize=7.0, color="#555555")
        clean_axis(lower)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 5:
        axis.axis("off")
        relationship_rows = {
            metric: select_one(
                TERRAIN_RELATIONSHIP_ROWS,
                outcome=f"topography_no_scatter__{metric}",
                predictor="path_relief_range_km",
            )
            for metric in (
                "broad__log_peak_amplitude",
                "broad__log_total_energy",
                "broad__log_duration_90_s",
            )
        }
        selected_stations = []
        for column, ray in enumerate((1, 2, 3)):
            station = select_quantile("path_relief_range_km", 0.85, ray=ray)
            selected_stations.append(station)
            inset = axis.inset_axes([0.01 + 0.33 * column, 0.23, 0.31, 0.68])
            plot_model_lanes(inset, station, (0, 2), scale_mode="shared", smooth_s=4.0)
            rho_values = tuple(
                number(relationship_rows[metric][f"ray{ray}_rho"])
                for metric in (
                    "broad__log_peak_amplitude",
                    "broad__log_total_energy",
                    "broad__log_duration_90_s",
                )
            )
            relief = number(ROW_BY_INDEX[station]["path_relief_range_km"])
            inset.set_title(
                f"射线{ray}高起伏代表站 · 高差={relief:.2f} km\n"
                f"ρ(峰值/能量/T90)={rho_values[0]:+.2f}/{rho_values[1]:+.2f}/{rho_values[2]:+.2f}",
                fontsize=7.6,
            )
            inset.set_xlabel("")
            if column > 0:
                inset.set_yticklabels([])
            inset.set_ylabel("" if column > 0 else station_label(station))
        axis.text(0.50, 0.145, "时间（s）", transform=axis.transAxes, ha="center", va="center", fontsize=9.0)
        axis.text(
            0.50,
            0.045,
            "分射线ρ基于去除各自震中距趋势后的台站级Spearman相关；综合ρ另由57个十站空间块计算。",
            transform=axis.transAxes,
            ha="center",
            va="bottom",
            fontsize=7.0,
            color="#555555",
        )
        SELECTION_NOTES[identifier] = "；".join(station_label(station) for station in selected_stations)
    elif identifier == 6:
        feature = "path_mean_absolute_slope"
        low_station, high_station = matched_feature_pair(feature)
        axis.axis("off")
        for column, station in enumerate((low_station, high_station)):
            inset = axis.inset_axes([0.02 + 0.50 * column, 0.08, 0.47, 0.86])
            plot_model_lanes(inset, station, (0, 2), scale_mode="shared", smooth_s=4.0)
            value = number(ROW_BY_INDEX[station][feature])
            label = "低值路径" if column == 0 else "高值路径"
            inset.set_title(f"{label} · 路径平均绝对坡度={value:.3f}", fontsize=8.5)
        SELECTION_NOTES[identifier] = f"{station_label(low_station)}；{station_label(high_station)}"
    elif identifier == 7:
        station = select_saturation_station()
        window = station_window(station)
        axis.axis("off")
        comparisons = (
            ((0, 1), "平坦背景：加散射"),
            ((2, 3), "地形背景：加散射"),
            ((0, 2), "无散射背景：加地形"),
            ((1, 3), "散射背景：加地形"),
        )
        for panel_index, (models, title) in enumerate(comparisons):
            row_index, column_index = divmod(panel_index, 2)
            inset = axis.inset_axes([0.02 + 0.50 * column_index, 0.53 - 0.47 * row_index, 0.47, 0.40])
            plot_model_overlay(inset, station, models, window=window, shared_scale=False, smooth_s=4.0)
            inset.set_title(title, fontsize=8.3)
            if row_index == 0:
                inset.set_xlabel("")
                inset.set_xticklabels([])
            if column_index == 1:
                inset.set_ylabel("")
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 8:
        station = select_representative(tuple(f"{model}__broad__log_impulsiveness_snr" for model in MODEL_NAMES))
        plot_model_lanes(axis, station, (0, 1, 2, 3), scale_mode="each", smooth_s=2.0)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 9:
        low_station = select_quantile("topography_scatter__broad__log_peak_amplitude", 0.15)
        high_station = select_quantile("topography_scatter__broad__log_peak_amplitude", 0.85)
        axis.axis("off")
        for column, station in enumerate((low_station, high_station)):
            inset = axis.inset_axes([0.02 + 0.50 * column, 0.08, 0.47, 0.86])
            plot_model_lanes(inset, station, (1, 3), scale_mode="shared", smooth_s=3.0)
            inset.set_title("局部散焦" if column == 0 else "局部聚焦", fontsize=9)
        SELECTION_NOTES[identifier] = f"{station_label(low_station)}；{station_label(high_station)}"
    elif identifier == 10:
        station = select_quantile("path_relief_range_km", 0.85, ray=2)
        axis.axis("off")
        left = axis.inset_axes([0.02, 0.08, 0.47, 0.86])
        right = axis.inset_axes([0.52, 0.08, 0.47, 0.86])
        plot_model_lanes(left, station, (0, 2), scale_mode="shared", smooth_s=4.0, labels=("M1", "M3"))
        plot_model_lanes(right, station, (1, 3), scale_mode="shared", smooth_s=4.0, labels=("M2", "M4"))
        left.set_title("无随机散射背景", fontsize=8.5)
        right.set_title("随机散射背景", fontsize=8.5)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 11:
        axis.axis("off")
        selected = []
        relative_time = np.linspace(-15, 75, 1100)
        for ray in (1, 2, 3):
            station = select_representative(("scatter_flat__broad__tmax_s", "scatter_flat__broad__log_duration_90_s"), ray=ray)
            selected.append(station)
            inset = axis.inset_axes([0.07, 0.68 - (ray - 1) * 0.30, 0.90, 0.26])
            peak = number(ROW_BY_INDEX[station]["M1__broad__tmax_s"])
            for model_index in (0, 1):
                trace = np.interp(relative_time + peak, RAW_MODELS[model_index].time, filtered_trace(model_index, station), left=0.0, right=0.0)
                envelope = rms_envelope(relative_time, trace, 4.0)
                inset.plot(relative_time, normalized(envelope), color=MODEL_COLORS[model_index], linewidth=1.7, label=MODEL_NAMES[model_index])
            inset.set_ylabel(f"射线{ray}\n{ROW_BY_INDEX[station]['station']}")
            inset.set_xlim(-15, 75)
            inset.set_ylim(0, 1.08)
            if ray < 3:
                inset.set_xlabel("")
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("相对M1峰值时间（s）")
            if ray == 1:
                inset.legend(fontsize=7.0, ncol=2, loc="upper right")
            clean_axis(inset, "x")
        SELECTION_NOTES[identifier] = "；".join(station_label(station) for station in selected)
    elif identifier == 12:
        station = select_representative(("topography_no_scatter__broad__log_peak_amplitude", "topography_no_scatter__broad__log_duration_90_s"), ray=1)
        plot_model_lanes(axis, station, (0, 2), scale_mode="shared", smooth_s=5.0)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 13:
        station = select_frequency_trend_station("M2")
        axis.axis("off")
        time = RAW_MODELS[1].time
        for band_index, (low_hz, high_hz) in enumerate(SUB_BANDS):
            inset = axis.inset_axes([0.08, 0.68 - band_index * 0.30, 0.88, 0.26])
            trace = filtered_trace(1, station, low_hz, high_hz)
            center_hz = (low_hz + high_hz) / 2.0
            intensity = np.abs(hilbert(trace)) ** 2
            smooth_samples = max(3, int(round((10.0 / center_hz) / float(np.median(np.diff(time))))))
            smoothed = uniform_filter1d(intensity, smooth_samples, mode="nearest")
            peak = float(time[np.argmax(smoothed)])
            relative_time = time - peak
            mask = (relative_time >= -18.0) & (relative_time <= 82.0)
            reference = max(float(np.max(smoothed[mask])), EPSILON)
            values = np.maximum(smoothed[mask] / reference, 1.0e-5)
            inset.semilogy(relative_time[mask], values, color=MODEL_COLORS[1], linewidth=1.3)
            start_offset = max(5.0, 5.0 / center_hz)
            fit_mask = (relative_time >= start_offset) & (relative_time <= start_offset + 60.0)
            if np.sum(fit_mask) > 20:
                coefficients = np.polyfit(relative_time[fit_mask], np.log(np.maximum(smoothed[fit_mask], EPSILON)), 1)
                fit_time = relative_time[fit_mask]
                prediction = np.exp(np.polyval(coefficients, fit_time)) / reference
                td = -1.0 / coefficients[0] if coefficients[0] < 0 else np.nan
                qc = 2.0 * np.pi * center_hz * td
                inset.semilogy(fit_time, prediction, color="#2F5597", linewidth=2.0)
                inset.text(0.98, 0.80, f"td={td:.1f}s  Qc={qc:.0f}", transform=inset.transAxes, ha="right", fontsize=7.2)
            inset.set_xlim(-18, 82)
            inset.set_ylim(1.0e-5, 1.2)
            inset.set_ylabel(f"{low_hz:.1f}-{high_hz:.1f}Hz")
            if band_index < 2:
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("相对各频带能量峰值时间（s）")
            clean_axis(inset, "x")
        axis.set_title(station_label(station), fontsize=9.5)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 14:
        station = select_softening_station()
        axis.axis("off")
        upper = axis.inset_axes([0.06, 0.55, 0.92, 0.38])
        lower = axis.inset_axes([0.08, 0.06, 0.88, 0.36])
        peak = number(ROW_BY_INDEX[station]["M2__broad__tmax_s"])
        plot_model_lanes(upper, station, (1,), window=(max(0, peak - 18), min(RAW_MODELS[1].time[-1], peak + 85)), scale_mode="each", smooth_s=3.0)
        early = (peak, min(float(RAW_MODELS[1].time[-1]), peak + 20.0))
        late = (peak + 40.0, min(float(RAW_MODELS[1].time[-1]), peak + 80.0))
        upper.axvspan(*early, color="#4477AA", alpha=0.12)
        upper.axvspan(*late, color="#EE6677", alpha=0.12)
        for model_index in range(4):
            time = RAW_MODELS[model_index].time
            model_peak = number(ROW_BY_INDEX[station][f"{MODEL_NAMES[model_index]}__broad__tmax_s"])
            low_envelope = rms_envelope(time, filtered_trace(model_index, station, 0.3, 0.5), 5.0) ** 2
            high_envelope = rms_envelope(time, filtered_trace(model_index, station, 0.7, 0.9), 5.0) ** 2
            relative_time = np.linspace(0, min(80.0, float(time[-1] - model_peak)), 700)
            low_values = np.interp(relative_time + model_peak, time, low_envelope)
            high_values = np.interp(relative_time + model_peak, time, high_envelope)
            ratio = high_values / np.maximum(low_values, EPSILON)
            early_reference = float(np.median(ratio[(relative_time >= 0) & (relative_time <= 20)]))
            ratio = uniform_filter1d(ratio / max(early_reference, EPSILON), 25, mode="nearest")
            lower.plot(relative_time, ratio, color=MODEL_COLORS[model_index], linewidth=1.6, label=MODEL_NAMES[model_index])
        lower.set_yscale("log")
        lower.axvspan(40, 80, color="#EE6677", alpha=0.08)
        lower.set_xlim(0, 80)
        lower.set_xlabel("相对各模型包络峰值时间（s）")
        lower.set_ylabel("高频/低频能量比\n（早窗归一）")
        lower.legend(fontsize=7.2, ncol=4)
        clean_axis(lower)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 15:
        station = select_quantile("M2__broad__qc_lapse_log_std", 0.8)
        time = RAW_MODELS[1].time
        trace = filtered_trace(1, station)
        envelope = rms_envelope(time, trace, 10.0 / 0.6)
        peak = number(ROW_BY_INDEX[station]["M2__broad__tmax_s"])
        window = (max(0, peak - 12), min(float(time[-1]), peak + 85))
        mask = (time >= window[0]) & (time <= window[1])
        reference = max(float(np.max(envelope[mask])), EPSILON)
        axis.semilogy(time[mask], np.maximum(envelope[mask] / reference, 1.0e-5), color="#222222", linewidth=1.0, label="平滑尾波包络")
        colors = ("#4477AA", "#EE6677", "#228833")
        for fit_index, offset in enumerate((0.0, 10.0, 20.0)):
            start = peak + max(5.0, 5.0 / 0.6) + offset
            fit_mask = (time >= start) & (time <= min(start + 40.0, time[-1]))
            coefficients = np.polyfit(time[fit_mask], np.log(np.maximum(envelope[fit_mask], EPSILON)), 1)
            fit_time = time[fit_mask]
            fit = np.exp(np.polyval(coefficients, fit_time)) / reference
            axis.semilogy(fit_time, fit, color=colors[fit_index], linewidth=2.1, label=f"移动窗{fit_index + 1}")
        axis.set_xlim(*window)
        axis.set_ylim(1.0e-4, 1.4)
        axis.set_xlabel("时间（s）")
        axis.set_ylabel("归一化RMS包络（对数）")
        axis.set_title(station_label(station), fontsize=9.5)
        axis.legend(fontsize=7.3, ncol=4)
        clean_axis(axis)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 16:
        axis.axis("off")
        notes = []
        relative_time = np.linspace(-12, 55, 900)
        for ray in (1, 2, 3):
            breakpoint = number(select_one(BREAKPOINT_ROWS, comparison="scatter_flat", metric="broad__tmax_s", ray=ray)["breakpoint_km"])
            before = nearest_station(ray, breakpoint - 8.0)
            after = nearest_station(ray, breakpoint + 8.0)
            inset = axis.inset_axes([0.08, 0.68 - (ray - 1) * 0.30, 0.88, 0.26])
            for station, linestyle, label in ((before, "-", "转折前"), (after, "--", "转折后")):
                for model_index in (0, 1):
                    peak = number(ROW_BY_INDEX[station]["M1__broad__tmax_s"])
                    trace = np.interp(relative_time + peak, RAW_MODELS[model_index].time, filtered_trace(model_index, station))
                    envelope = rms_envelope(relative_time, trace, 3.0)
                    inset.plot(relative_time, normalized(envelope), color=MODEL_COLORS[model_index], linestyle=linestyle, linewidth=1.3, label=f"{label}{MODEL_NAMES[model_index]}")
            inset.set_ylabel(f"射线{ray}\n{breakpoint:.0f}km")
            inset.set_ylim(0, 1.08)
            if ray < 3:
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("相对M1峰值时间（s）")
            if ray == 1:
                inset.legend(fontsize=6.4, ncol=4, loc="upper right")
            clean_axis(inset, "x")
            notes.extend((station_label(before), station_label(after)))
        SELECTION_NOTES[identifier] = "；".join(notes)
    elif identifier == 17:
        axis.axis("off")
        notes = []
        relative_time = np.linspace(-15, 65, 1000)
        for ray in (1, 2, 3):
            lag = number(select_one(SPATIAL_LAG_ROWS, comparison="topography_no_scatter", metric="broad__tmax_s", predictor="absolute_slope", ray=ray)["best_lag_km"])
            ray_rows = primary_rows(ray)
            center_distance = float(np.median([number(row["distance_km"]) for row in ray_rows]))
            center = nearest_station(ray, center_distance)
            shifted = nearest_station(ray, center_distance + lag)
            first = relative_effect_waveform(0, 2, center, relative_time)
            second = relative_effect_waveform(0, 2, shifted, relative_time)
            inset = axis.inset_axes([0.08, 0.68 - (ray - 1) * 0.30, 0.88, 0.26])
            inset.plot(relative_time, normalized(first), color=RAY_COLORS[ray - 1], linewidth=1.15, label=f"中心 {ROW_BY_INDEX[center]['station']}")
            inset.plot(relative_time, normalized(second), color=RAY_COLORS[ray - 1], linestyle="--", linewidth=1.6, label=f"偏移{lag:+.0f}km {ROW_BY_INDEX[shifted]['station']}")
            inset.axhline(0, color="#999999", linewidth=0.55)
            inset.set_ylabel(f"射线{ray}")
            if ray < 3:
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("相对M1峰值时间（s）")
            inset.legend(fontsize=6.8, loc="upper right")
            clean_axis(inset, "x")
            notes.extend((station_label(center), station_label(shifted)))
        SELECTION_NOTES[identifier] = "；".join(notes)
    elif identifier == 18:
        station = select_representative(("scatter_flat__broad__log_duration_90_s", "topography_no_scatter__broad__log_duration_90_s"), ray=2)
        axis.axis("off")
        upper = axis.inset_axes([0.04, 0.33, 0.94, 0.62])
        lower = axis.inset_axes([0.09, 0.05, 0.87, 0.18])
        plot_model_lanes(upper, station, (0, 1, 2, 3), scale_mode="each", smooth_s=3.0)
        rows = sorted(primary_rows(2), key=lambda row: number(row["distance_km"]))
        distance = np.asarray([number(row["distance_km"]) for row in rows])
        elevation = np.asarray([number(row["elevation_km"]) for row in rows])
        lower.plot(distance, elevation, color="#333333", linewidth=1.0)
        lower.fill_between(distance, np.min(elevation) - 0.2, elevation, color="#B8A88A", alpha=0.45)
        selected_distance = number(ROW_BY_INDEX[station]["distance_km"])
        lower.axvline(selected_distance, color=ACCENT, linewidth=1.8)
        lower.set_xlim(distance.min(), distance.max())
        lower.set_xlabel("射线2震中距（km）")
        lower.set_ylabel("地形（km）")
        clean_axis(lower)
        SELECTION_NOTES[identifier] = station_label(station)
    elif identifier == 19:
        axis.axis("off")
        upper = axis.inset_axes([0.05, 0.54, 0.93, 0.40])
        lower = axis.inset_axes([0.08, 0.06, 0.88, 0.36])
        time = OBSERVED_RECORD.time
        mask = (time >= 0) & (time <= 900)
        component_colors = ("#222222", "#666666", "#AAAAAA")
        for component, color, offset, label in zip(OBSERVED_RECORD.raw, component_colors, (2, 1, 0), ("Z", "E", "N"), strict=True):
            upper.plot(time[mask], offset + 0.34 * normalized(component[mask]), color=color, linewidth=0.55)
        upper.set_yticks((2, 1, 0), ("Z", "E", "N"))
        upper.set_xlabel("时间（s）")
        upper.set_title("真实A16S12原始三分量", fontsize=9)
        clean_axis(upper, "x")
        observed_spectra = []
        for component, color, label in zip(OBSERVED_RECORD.raw, component_colors, ("观测Z", "观测E", "观测N"), strict=True):
            spectrum = np.abs(np.fft.rfft(detrend(component)))
            frequencies = np.fft.rfftfreq(component.size, d=float(np.median(np.diff(time))))
            observed_spectra.append(np.interp(np.linspace(0.2, 1.5, 500), frequencies, spectrum))
            keep = (frequencies >= 0.2) & (frequencies <= 1.5)
            lower.plot(frequencies[keep], normalized(spectrum[keep]), color=color, linewidth=1.5, label=label)
        for model_index, record in enumerate(MODEL_RECORDS):
            frequency_grid = np.linspace(0.2, 1.5, 500)
            model_spectra = []
            for component in record.raw:
                spectrum = np.abs(np.fft.rfft(detrend(component)))
                frequencies = np.fft.rfftfreq(component.size, d=float(np.median(np.diff(record.time))))
                model_spectra.append(np.interp(frequency_grid, frequencies, spectrum))
            mean_spectrum = np.mean(np.asarray(model_spectra), axis=0)
            lower.plot(frequency_grid, normalized(mean_spectrum), color=MODEL_COLORS[model_index], linewidth=1.1, alpha=0.85, label=f"{MODEL_NAMES[model_index]}三分量均值")
        lower.set_xlim(0.2, 1.5)
        lower.set_xlabel("频率（Hz）")
        lower.set_ylabel("归一化振幅谱")
        lower.legend(fontsize=6.2, ncol=4)
        clean_axis(lower)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 20:
        plot_observed_model_envelopes(axis, 245.0, normalize_each=False, start_s=50.0, smooth_s=4.0)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 21:
        plot_observed_model_envelopes(axis, 900.0, normalize_each=True, smooth_s=10.0)
        colors = (OBSERVED_COLOR, *MODEL_COLORS)
        for index, row in enumerate(OBSERVED_METRIC_ROWS):
            peak = number(row["peak_energy_time_median_s"])
            axis.axvline(peak, color=colors[index], linewidth=0.9, alpha=0.75)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 22:
        axis.axis("off")
        left = axis.inset_axes([0.02, 0.10, 0.47, 0.84])
        right = axis.inset_axes([0.53, 0.10, 0.45, 0.84])
        for index in range(1, 5):
            time, envelope = three_component_envelope(index, 5.0)
            mask = (time >= 70) & (time <= 125)
            left.plot(time[mask], normalized(envelope[mask]), color=MODEL_COLORS[index - 1], linewidth=1.6, label=MODEL_NAMES[index - 1])
            left.axvline(number(OBSERVED_METRIC_ROWS[index]["peak_energy_time_median_s"]), color=MODEL_COLORS[index - 1], linewidth=0.7)
        left.set_title("模型峰值放大", fontsize=9)
        left.set_xlabel("时间（s）")
        left.set_ylabel("归一化包络")
        left.legend(fontsize=6.8, ncol=2)
        clean_axis(left)
        for index in (0, 1):
            time, envelope = three_component_envelope(index, 10.0)
            mask = time <= 800
            right.plot(time[mask], normalized(envelope[mask]), color=(OBSERVED_COLOR, MODEL_COLORS[0])[index], linewidth=1.8, label=("观测", "M1")[index])
        right.set_title("观测与M1完整差距", fontsize=9)
        right.set_xlabel("时间（s）")
        right.legend(fontsize=7.2)
        clean_axis(right)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 23:
        colors = (OBSERVED_COLOR, *MODEL_COLORS)
        labels = ("观测", *MODEL_NAMES)
        offsets = np.arange(4, -1, -1, dtype=float)
        for index, (offset, color, label, row) in enumerate(zip(offsets, colors, labels, OBSERVED_METRIC_ROWS, strict=True)):
            time, envelope = three_component_envelope(index, 10.0)
            mask = time <= 820
            values = normalized(envelope[mask])
            axis.plot(time[mask], offset + 0.34 * values, color=color, linewidth=1.5)
            axis.axhline(offset, color="#BBBBBB", linewidth=0.5)
            t05 = number(row["energy_t05_s"])
            tmax = number(row["peak_energy_time_median_s"])
            axis.fill_betweenx((offset - 0.28, offset + 0.38), t05, tmax, color=color, alpha=0.10)
        axis.set_yticks(offsets, labels)
        axis.set_xlim(0, 820)
        axis.set_ylim(-0.4, 4.5)
        axis.set_xlabel("时间（s）；阴影为5%能量时刻至包络峰值")
        clean_axis(axis, "x")
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 24:
        plot_cumulative_lines(axis, (0, 1, 2, 3, 4), 3000.0)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 25:
        plot_cumulative_lines(axis, (1, 2, 3, 4), 220.0)
        SELECTION_NOTES[identifier] = "四模型S12"
    elif identifier == 26:
        axis.axis("off")
        upper = axis.inset_axes([0.05, 0.49, 0.93, 0.45])
        lower = axis.inset_axes([0.08, 0.06, 0.88, 0.32])
        time = OBSERVED_RECORD.time
        envelope_time, envelope = three_component_envelope(0, 20.0)
        mask = time <= 3000
        trace = OBSERVED_RECORD.filtered[0]
        upper.plot(time[mask], 0.30 * normalized(trace[mask]), color=OBSERVED_COLOR, alpha=0.45, linewidth=0.45)
        upper.plot(envelope_time[envelope_time <= 3000], normalized(envelope[envelope_time <= 3000]), color=OBSERVED_COLOR, linewidth=1.6)
        upper.axvline(250, color="#D55E00", linestyle="--", linewidth=1.4)
        upper.set_ylabel("Z波形 / 3C包络")
        upper.set_xlim(0, 3000)
        upper.set_xticklabels([])
        clean_axis(upper)
        time_c, cumulative = cumulative_energy(0)
        lower.plot(time_c[time_c <= 3000], cumulative[time_c <= 3000], color=ACCENT, linewidth=2.0)
        lower.axvline(250, color="#D55E00", linestyle="--", linewidth=1.4)
        lower.axhline(0.0398, color="#D55E00", linestyle=":", linewidth=1.0)
        lower.set_xlim(0, 3000)
        lower.set_ylim(0, 1.02)
        lower.set_xlabel("撞击后时间（s）")
        lower.set_ylabel("累计能量")
        clean_axis(lower)
        SELECTION_NOTES[identifier] = "真实A16S12"
    elif identifier == 27:
        axis.axis("off")
        component_labels = ("Z", "E", "N")
        for component_index, label in enumerate(component_labels):
            inset = axis.inset_axes([0.07, 0.68 - component_index * 0.30, 0.90, 0.26])
            comparison_time = OBSERVED_RECORD.time[(OBSERVED_RECORD.time >= 50) & (OBSERVED_RECORD.time <= 245)]
            observed = np.interp(comparison_time, OBSERVED_RECORD.time, OBSERVED_RECORD.filtered[component_index])
            scale = max(float(np.max(np.abs(observed))), EPSILON)
            inset.plot(comparison_time, observed / scale, color=OBSERVED_COLOR, linewidth=1.25, label="观测")
            for model_index, record in enumerate(MODEL_RECORDS):
                model = SOURCE_SCALES[model_index] * np.interp(comparison_time, record.time, record.filtered[component_index])
                inset.plot(comparison_time, model / scale, color=MODEL_COLORS[model_index], linewidth=0.9, alpha=0.85, label=MODEL_NAMES[model_index])
            inset.set_ylabel(label)
            if component_index < 2:
                inset.set_xticklabels([])
            else:
                inset.set_xlabel("时间（s）")
            if component_index == 0:
                inset.legend(fontsize=6.6, ncol=5, loc="upper right")
            clean_axis(inset, "x")
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 28:
        plot_observed_model_envelopes(axis, 245.0, normalize_each=True, start_s=50.0, smooth_s=8.0)
        axis.axvspan(90, 180, color="#BBBBBB", alpha=0.10)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    elif identifier == 29:
        axis.axis("off")
        for ray in (1, 2, 3):
            inset = axis.inset_axes([0.035 + (ray - 1) * 0.325, 0.08, 0.30, 0.86])
            plot_waveform_section(inset, ray, 1, stride=18, end_s=175.0, amplitude_km=5.0)
            distance = np.linspace(10, max(number(ROW_BY_INDEX[int(index)]["distance_km"]) for index in RAY_STATION_INDICES[ray - 1]), 200)
            for model_index in range(4):
                row = fit_row(ray, model_index)
                linear = number(row["linear_intercept_s"]) + number(row["linear_slope_s_per_km"]) * distance
                diffusion = number(row["diffusion_intercept_s"]) + number(row["diffusion_coefficient_s_per_km2"]) * distance**2
                inset.plot(linear, distance, color=MODEL_COLORS[model_index], linewidth=1.35)
                inset.plot(diffusion, distance, color=MODEL_COLORS[model_index], linestyle=":", linewidth=0.85, alpha=0.75)
            inset.set_title(f"射线{ray}", fontsize=8.5)
            if ray > 1:
                inset.set_ylabel("")
            if ray == 1:
                inset.text(0.03, 0.97, "实线=线性\n点线=R²", transform=inset.transAxes, va="top", fontsize=6.8)
        SELECTION_NOTES[identifier] = "三条射线波形剖面；四模型拟合轨迹"
    elif identifier == 30:
        plot_waveform_section(axis, 2, 0, stride=9, end_s=175.0, amplitude_km=3.5)
        row = fit_row(2, 0)
        distance = np.linspace(10, 240, 300)
        linear = number(row["linear_intercept_s"]) + number(row["linear_slope_s_per_km"]) * distance
        diffusion = number(row["diffusion_intercept_s"]) + number(row["diffusion_coefficient_s_per_km2"]) * distance**2
        axis.plot(linear, distance, color="#222222", linewidth=2.2, label="线性传播轨迹")
        axis.plot(diffusion, distance, color=ACCENT, linestyle="--", linewidth=2.0, label="扩散R²轨迹")
        axis.legend(fontsize=7.5, loc="lower right")
        SELECTION_NOTES[identifier] = "射线2 M1波形剖面"
    elif identifier == 31:
        plot_waveform_section(axis, 2, 0, stride=12, end_s=900.0, amplitude_km=4.0)
        distance = number(ROW_BY_INDEX[0]["distance_km"])
        time, envelope = three_component_envelope(0, 12.0)
        mask = time <= 900
        axis.plot(time[mask], distance + 12.0 * normalized(envelope[mask]), color=OBSERVED_COLOR, linewidth=2.0, label="唯一真实S12包络")
        axis.axhline(distance, color=OBSERVED_COLOR, linestyle="--", linewidth=0.8)
        axis.set_xlim(0, 900)
        axis.legend(fontsize=7.5, loc="upper right")
        SELECTION_NOTES[identifier] = "射线2合成剖面；真实S12单点"
    elif identifier == 32:
        colors = (OBSERVED_COLOR, *MODEL_COLORS)
        labels = ("观测", *MODEL_NAMES)
        for index, (color, label) in enumerate(zip(colors, labels, strict=True)):
            time, envelope = three_component_envelope(index, 15.0)
            end = 3000.0 if index == 0 else min(250.0, float(time[-1]))
            mask = time <= end
            axis.plot(time[mask], normalized(envelope[mask]), color=color, linewidth=2.0 if index == 0 else 1.45, label=label)
        axis.axvline(250, color="#D55E00", linestyle="--", linewidth=1.4)
        axis.axvspan(250, 3000, color="#999999", alpha=0.07)
        axis.set_xlim(0, 3000)
        axis.set_xlabel("撞击后时间（s）")
        axis.set_ylabel("归一化三分量包络")
        axis.legend(fontsize=7.3, ncol=5, loc="upper right")
        clean_axis(axis)
        SELECTION_NOTES[identifier] = "真实A16S12；四模型S12"
    else:
        raise ValueError(identifier)


def create_card(conclusion: Conclusion) -> Path:
    fig = plt.figure(figsize=(8.4, 5.3), facecolor="#FAFAFA")
    axis = fig.add_axes([0.10, 0.20, 0.86, 0.66])
    fig.text(0.035, 0.955, f"C{conclusion.identifier:02d}", fontsize=14, weight="bold", color=ACCENT, va="top")
    fig.text(0.125, 0.955, textwrap.fill(conclusion.title, 29), fontsize=12.4, weight="bold", color="#1E1E1E", va="top")
    draw_conclusion_chart(conclusion.identifier, axis)
    fig.text(0.045, 0.108, textwrap.fill(conclusion.takeaway, 68), fontsize=9.1, color="#222222", va="top", bbox={"boxstyle": "round,pad=0.42", "facecolor": "#EEEEEE", "edgecolor": "none"})
    fig.text(0.955, 0.028, f"波形证据：{conclusion.sources}", fontsize=7.1, color="#666666", ha="right")
    file_path = CARD_DIR / f"C{conclusion.identifier:02d}_{conclusion.slug}.png"
    fig.savefig(file_path, dpi=FIGURE_DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return file_path


def create_atlas_pages(card_paths: list[Path]) -> list[Path]:
    atlas_paths = []
    for page_index, start in enumerate(range(0, len(card_paths), 4), start=1):
        current = card_paths[start : start + 4]
        fig, axes = plt.subplots(2, 2, figsize=(16.8, 10.6), facecolor="#F4F4F4")
        for axis, card_path in zip(axes.ravel(), current, strict=False):
            axis.imshow(mpimg.imread(card_path))
            axis.axis("off")
        for axis in axes.ravel()[len(current) :]:
            axis.axis("off")
        fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, wspace=0.012, hspace=0.020)
        file_path = ATLAS_DIR / f"conclusion_evidence_atlas_page_{page_index:02d}.png"
        fig.savefig(file_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        atlas_paths.append(file_path)
    return atlas_paths


def write_index(card_paths: list[Path], atlas_paths: list[Path]) -> None:
    with (OUTPUT_DIR / "conclusion_evidence_index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("conclusion_id", "title", "takeaway", "representative_stations", "card_file", "atlas_page", "evidence_sources"))
        for conclusion, card_path in zip(CONCLUSIONS, card_paths, strict=True):
            page = (conclusion.identifier - 1) // 4 + 1
            writer.writerow((f"C{conclusion.identifier:02d}", conclusion.title, conclusion.takeaway, SELECTION_NOTES.get(conclusion.identifier, ""), card_path.relative_to(OUTPUT_DIR), atlas_paths[page - 1].relative_to(OUTPUT_DIR), conclusion.sources))

    lines = [
        "# 32条结论波形证据图册",
        "",
        "所有结论均改用原始/滤波波形、Hilbert-RMS包络、累积能量或距离波形剖面呈现，不再使用柱状图。图形范式参考Blanchette-Guertin et al. (2012) Fig.3、Blanchette-Guertin et al. (2015, GRL) Fig.2、Gillet et al. (2017) Figs.2-3和Blanchette-Guertin et al. (2015, JGR) Fig.13。",
        "",
    ]
    for conclusion, card_path in zip(CONCLUSIONS, card_paths, strict=True):
        lines.extend(
            (
                f"## C{conclusion.identifier:02d} {conclusion.title}",
                "",
                f"![C{conclusion.identifier:02d}](cards/{card_path.name})",
                "",
                f"**波形判据：** {conclusion.takeaway}",
                "",
                f"**代表记录：** {SELECTION_NOTES.get(conclusion.identifier, '见图内标注')}",
                "",
                f"**证据来源：** `{conclusion.sources}`",
                "",
            )
        )
    (OUTPUT_DIR / "conclusion_evidence_guide_zh.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    configure_fonts()
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    card_paths = [create_card(conclusion) for conclusion in CONCLUSIONS]
    atlas_paths = create_atlas_pages(card_paths)
    write_index(card_paths, atlas_paths)
    print(f"Generated {len(card_paths)} waveform evidence cards and {len(atlas_paths)} atlas pages in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
