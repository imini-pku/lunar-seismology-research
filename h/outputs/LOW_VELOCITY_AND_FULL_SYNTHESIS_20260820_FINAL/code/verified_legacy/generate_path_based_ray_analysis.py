import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
TOPOGRAPHY_FILE = Path(r"D:\software\CGFD3D_v26.03\revise\prep_medium\rel3_Z_300_1500_topo.txt")
OUTPUT_DIR = ROOT / "path_based_ray_analysis"
OUTPUT_FILE = OUTPUT_DIR / "path_profiles_and_cumulative_metrics.png"
STATION_METRICS_FILE = (
    ROOT
    / "releasy_relationship_analysis"
    / "literature_guided"
    / "literature_guided_station_metrics.csv"
)
TERRAIN_RELATIONSHIPS_FILE = (
    ROOT
    / "releasy_relationship_analysis"
    / "literature_guided"
    / "literature_guided_terrain_relationships.csv"
)
SOURCE_XY = np.array([161_310.0, 207_630.0])
RAY_TARGETS = np.array(
    [
        [197_256.0, 59_703.0],
        [100_000.0, 140_000.0],
        [213_000.0, 247_000.0],
    ]
)
COLORS = ("#2673B8", "#D66A22", "#26855B")
FILLS = ("#DCEAF6", "#F8E3D5", "#DCEFE6")


def font(size, bold=False):
    path = Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc")
    return ImageFont.truetype(str(path), size=size)


def sample_topography(topography, xy):
    grid_size = topography.shape[0]
    fractional_x = xy[:, 0] / 300_000.0 * (grid_size - 1)
    fractional_y = xy[:, 1] / 300_000.0 * (grid_size - 1)
    x0 = np.clip(np.floor(fractional_x).astype(int), 0, grid_size - 1)
    y0 = np.clip(np.floor(fractional_y).astype(int), 0, grid_size - 1)
    x1 = np.clip(x0 + 1, 0, grid_size - 1)
    y1 = np.clip(y0 + 1, 0, grid_size - 1)
    weight_x = fractional_x - x0
    weight_y = fractional_y - y0
    return (
        topography[y0, x0] * (1.0 - weight_x) * (1.0 - weight_y)
        + topography[y0, x1] * weight_x * (1.0 - weight_y)
        + topography[y1, x0] * (1.0 - weight_x) * weight_y
        + topography[y1, x1] * weight_x * weight_y
    )


def build_profiles(topography):
    profiles = []
    for target in RAY_TARGETS:
        direction = target - SOURCE_XY
        direction /= np.linalg.norm(direction)
        maximum_distance_m = np.inf
        for coordinate, direction_component in zip(SOURCE_XY, direction, strict=True):
            if direction_component > 0:
                boundary_distance = (300_000.0 - coordinate) / direction_component
            elif direction_component < 0:
                boundary_distance = (0.0 - coordinate) / direction_component
            else:
                continue
            maximum_distance_m = min(maximum_distance_m, boundary_distance)
        last_distance_km = max(1.0, np.floor(maximum_distance_m / 1_000.0) - 2.0)
        distance_km = np.arange(0.0, last_distance_km + 1.0)
        coordinates = SOURCE_XY + distance_km[:, None] * 1_000.0 * direction
        elevation_km = sample_topography(topography, coordinates)
        cumulative_relief = np.maximum.accumulate(elevation_km) - np.minimum.accumulate(elevation_km)
        if distance_km.size > 1:
            interval_slope = np.abs(np.diff(elevation_km) / np.diff(distance_km))
            cumulative_slope = np.concatenate(([0.0], np.cumsum(interval_slope) / np.arange(1, interval_slope.size + 1)))
        else:
            cumulative_slope = np.zeros_like(distance_km)
        profiles.append((distance_km, elevation_km, cumulative_relief, cumulative_slope))
    return profiles


def map_x(value, minimum, maximum, left, right):
    return left + (value - minimum) / (maximum - minimum) * (right - left)


def map_y(value, minimum, maximum, top, bottom):
    return bottom - (value - minimum) / (maximum - minimum) * (bottom - top)


def draw_panel(draw, box, x_limits, y_limits, title, y_label, series, fill_profiles=False):
    left, top, right, bottom = box
    draw.rectangle(box, outline="#7E8891", width=2, fill="#FFFFFF")
    title_type = font(27, bold=True)
    axis_type = font(21)
    tick_type = font(18)
    draw.text((left, top - 46), title, font=title_type, fill="#203748")
    for x_tick in np.arange(0, x_limits[1] + 1, 50):
        x_pixel = map_x(x_tick, *x_limits, left, right)
        draw.line((x_pixel, top, x_pixel, bottom), fill="#E3E7EA", width=2)
        draw.text((x_pixel, bottom + 10), f"{int(x_tick)}", font=tick_type, fill="#4F5962", anchor="ma")
    y_ticks = np.linspace(y_limits[0], y_limits[1], 5)
    for y_tick in y_ticks:
        y_pixel = map_y(y_tick, *y_limits, top, bottom)
        draw.line((left, y_pixel, right, y_pixel), fill="#E3E7EA", width=2)
        draw.text((left - 14, y_pixel), f"{y_tick:.1f}", font=tick_type, fill="#4F5962", anchor="rm")
    for distance, values, color, fill in series:
        points = [
            (
                map_x(float(distance_value), *x_limits, left, right),
                map_y(float(np.clip(value, y_limits[0], y_limits[1])), *y_limits, top, bottom),
            )
            for distance_value, value in zip(distance, values, strict=True)
            if distance_value <= x_limits[1]
        ]
        if fill_profiles and points:
            polygon = [(points[0][0], bottom), *points, (points[-1][0], bottom)]
            draw.polygon(polygon, fill=fill)
        if len(points) > 1:
            draw.line(points, fill=color, width=5, joint="curve")
    draw.text(((left + right) / 2, bottom + 45), "沿震源—台站方向的累计距离 (km)", font=axis_type, fill="#303941", anchor="ma")
    draw.text((10, (top + bottom) / 2), y_label, font=axis_type, fill="#303941", anchor="lm")


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_profile_samples(profiles):
    rows = []
    for ray, profile in enumerate(profiles, start=1):
        distance_km, elevation_km, cumulative_relief_km, cumulative_mean_slope = profile
        for values in zip(
            distance_km,
            elevation_km,
            cumulative_relief_km,
            cumulative_mean_slope,
            strict=True,
        ):
            rows.append(
                {
                    "ray": ray,
                    "distance_km": f"{values[0]:.6f}",
                    "elevation_km": f"{values[1]:.9f}",
                    "cumulative_relief_km": f"{values[2]:.9f}",
                    "cumulative_mean_absolute_slope": f"{values[3]:.9f}",
                }
            )
    write_csv(
        OUTPUT_DIR / "path_profile_samples.csv",
        (
            "ray",
            "distance_km",
            "elevation_km",
            "cumulative_relief_km",
            "cumulative_mean_absolute_slope",
        ),
        rows,
    )


def median(rows, column):
    return float(np.median([float(row[column]) for row in rows]))


def factor(row, numerator_model, denominator_model, metric):
    numerator = float(row[f"{numerator_model}__broad__log_{metric}"])
    denominator = float(row[f"{denominator_model}__broad__log_{metric}"])
    return math.exp(numerator - denominator)


def summarize_station_paths():
    if not STATION_METRICS_FILE.is_file():
        return [], []
    station_rows = read_csv(STATION_METRICS_FILE)
    primary_rows = [
        row
        for row in station_rows
        if row["ray"] in {"1", "2", "3"}
        and row["included_in_primary_analysis"] == "1"
    ]
    summary_rows = []
    for ray in (1, 2, 3):
        ray_rows = [row for row in primary_rows if row["ray"] == str(ray)]
        summary_rows.append(
            {
                "ray": ray,
                "station_count": len(ray_rows),
                "median_endpoint_elevation_km": f"{median(ray_rows, 'elevation_km'):.6f}",
                "median_path_mean_elevation_km": f"{median(ray_rows, 'path_mean_elevation_km'):.6f}",
                "median_path_mean_absolute_slope": f"{median(ray_rows, 'path_mean_absolute_slope'):.6f}",
                "median_path_relief_range_km": f"{median(ray_rows, 'path_relief_range_km'):.6f}",
            }
        )
    write_csv(
        OUTPUT_DIR / "path_ray_summary.csv",
        (
            "ray",
            "station_count",
            "median_endpoint_elevation_km",
            "median_path_mean_elevation_km",
            "median_path_mean_absolute_slope",
            "median_path_relief_range_km",
        ),
        summary_rows,
    )

    example_rows = []
    all_ray_rows = [row for row in station_rows if row["ray"] in {"1", "2", "3"}]
    for ray in (1, 2, 3):
        ray_rows = [row for row in all_ray_rows if row["ray"] == str(ray)]
        for target_distance_km in (50.0, 100.0):
            row = min(ray_rows, key=lambda item: abs(float(item["distance_km"]) - target_distance_km))
            example_rows.append(
                {
                    "ray": ray,
                    "target_distance_km": f"{target_distance_km:.1f}",
                    "station": row["station"],
                    "actual_distance_km": f"{float(row['distance_km']):.3f}",
                    "path_relief_range_km": f"{float(row['path_relief_range_km']):.3f}",
                    "path_mean_absolute_slope": f"{float(row['path_mean_absolute_slope']):.3f}",
                    "M3_over_M1_peak_amplitude": f"{factor(row, 'M3', 'M1', 'peak_amplitude'):.3f}",
                    "M3_over_M1_total_energy": f"{factor(row, 'M3', 'M1', 'total_energy'):.3f}",
                    "M3_over_M1_duration_90": f"{factor(row, 'M3', 'M1', 'duration_90_s'):.3f}",
                    "M4_over_M2_peak_amplitude": f"{factor(row, 'M4', 'M2', 'peak_amplitude'):.3f}",
                    "M4_over_M2_total_energy": f"{factor(row, 'M4', 'M2', 'total_energy'):.3f}",
                    "M4_over_M2_duration_90": f"{factor(row, 'M4', 'M2', 'duration_90_s'):.3f}",
                }
            )
    write_csv(
        OUTPUT_DIR / "matched_distance_path_examples.csv",
        tuple(example_rows[0]),
        example_rows,
    )
    return summary_rows, example_rows


def strongest_path_relationships():
    if not TERRAIN_RELATIONSHIPS_FILE.is_file():
        return []
    relationships = read_csv(TERRAIN_RELATIONSHIPS_FILE)
    selected = [
        row
        for row in relationships
        if row["predictor"] in {"path_relief_range_km", "path_mean_absolute_slope"}
        and row["outcome"].startswith(("topography_no_scatter__broad__", "topography_scatter__broad__"))
        and math.isfinite(float(row["q_value"]))
    ]
    selected.sort(key=lambda row: (float(row["q_value"]), -abs(float(row["rho"]))))
    selected = selected[:12]
    write_csv(
        OUTPUT_DIR / "strongest_path_relationships.csv",
        (
            "outcome",
            "predictor",
            "rho",
            "q_value",
            "ray1_rho",
            "ray2_rho",
            "ray3_rho",
        ),
        [{key: row[key] for key in (
            "outcome",
            "predictor",
            "rho",
            "q_value",
            "ray1_rho",
            "ray2_rho",
            "ray3_rho",
        )} for row in selected],
    )
    return selected


def write_path_report(summary_rows, example_rows, relationships):
    lines = [
        "# 三条射线的传播路径地形分析",
        "",
        "本分析使用震源至台站方向的地表投影直线路径，沿路径累计地形高差与平均绝对坡度；它比仅使用终点台站高程更接近波场实际经历的自由表面起伏。当前结果仍不是三维弯曲射线或有限频率 Fresnel 体积积分。",
        "",
        "## 路径统计",
        "",
        "| 射线 | 台站数 | 终点高程中位数/km | 路径平均高程/km | 平均绝对坡度 | 累计高差/km |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['ray']} | {row['station_count']} | {row['median_endpoint_elevation_km']} | "
            f"{row['median_path_mean_elevation_km']} | {row['median_path_mean_absolute_slope']} | "
            f"{row['median_path_relief_range_km']} |"
        )
    lines.extend(("", "## 传播路径结论", ""))
    conclusions = (
        "射线1沿途最平滑，路径累计高差和平均绝对坡度都远低于射线2、3，因此地形对其振幅和能量的系统削弱较弱。",
        "射线2在约60–80 km穿越显著低洼区及其边缘，最强特征是散焦和能量损失；相近距离下，地形模型峰值和总能量可显著低于平坦模型。",
        "射线3在约30–55 km就快速积累起伏，且整体平均绝对坡度最大，更容易形成多脉冲、相位分裂和较长尾波。",
        "路径累计高差与振幅、能量和持续时间的综合相关主要由射线2、3贡献；射线1在无散射背景下对应rho接近零。因此路径高差是射线2、3的有效解释量，但不是三条射线共有的单一控制律。",
        "平均绝对坡度主要控制完整波形畸变、包络展宽和尾波，而不是一个统一的首波或峰值走时修正。",
        "地形把相干直接脉冲的一部分能量转换为反射、绕射、模式转换和多路径能量，因而常见组合是峰值下降、局地总能量下降、持续时间增加。",
        "射线3的粗糙度最大，但射线2某些位置的能量损失更强，说明地形曲率、坡向、盆地几何及聚焦/散焦不能由单一高差完全表示。",
        "约50 km的同距离比较已能显示终点高程不足：射线1和2路径高差较小且M3/M1能量接近1，而射线3路径高差约3 km时能量可降至约0.1量级。",
        "约100 km的同距离比较进一步显示，射线2与3的高起伏路径均造成更强的M3/M1振幅和能量下降以及显著持续时间增长。",
        "地形与随机散射具有饱和型非加性；波列已被随机散射展宽后，地形新增的边际作用通常小于无散射背景中的地形作用。",
        "当前路径是地表投影直线。下一步应使用有限频率 Fresnel 走廊、波场快照和能量通量，把路径宽度、曲率、坡向及关键地形段纳入解释。",
    )
    for index, conclusion in enumerate(conclusions, start=1):
        lines.append(f"{index}. {conclusion}")
    lines.extend(("", "## 同距离实例", "", "| 射线 | 目标距离/km | 台站 | 高差/km | 坡度 | M3/M1峰值 | M3/M1能量 | M3/M1持续 | M4/M2峰值 | M4/M2能量 | M4/M2持续 |", "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"))
    for row in example_rows:
        lines.append(
            f"| {row['ray']} | {row['target_distance_km']} | {row['station']} | {row['path_relief_range_km']} | "
            f"{row['path_mean_absolute_slope']} | {row['M3_over_M1_peak_amplitude']} | "
            f"{row['M3_over_M1_total_energy']} | {row['M3_over_M1_duration_90']} | "
            f"{row['M4_over_M2_peak_amplitude']} | {row['M4_over_M2_total_energy']} | "
            f"{row['M4_over_M2_duration_90']} |"
        )
    lines.extend(("", "## 最强路径相关", ""))
    for row in relationships:
        lines.append(
            f"- `{row['outcome']}` 与 `{row['predictor']}`：rho={float(row['rho']):+.3f}，"
            f"q={float(row['q_value']):.3g}，分射线 rho=({float(row['ray1_rho']):+.3f}, "
            f"{float(row['ray2_rho']):+.3f}, {float(row['ray3_rho']):+.3f})。"
        )
    (OUTPUT_DIR / "path_based_analysis_report_zh.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    topography = np.loadtxt(TOPOGRAPHY_FILE, dtype=np.float64)
    profiles = build_profiles(topography)
    write_profile_samples(profiles)
    summary_rows, example_rows = summarize_station_paths()
    relationships = strongest_path_relationships()
    canvas = Image.new("RGB", (1900, 1500), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    draw.text((950, 40), "三条传播路径的地形剖面与累计路径复杂度", font=font(44, bold=True), fill="#203748", anchor="ma")
    draw.text((950, 100), "路径指标从震源开始累积；它们描述整条地表投影路径，而不是仅描述终点台站高程", font=font(24), fill="#5C6770", anchor="ma")
    legend_x = 1320
    for index, color in enumerate(COLORS):
        y_position = 130 + index * 38
        draw.line((legend_x, y_position, legend_x + 70, y_position), fill=color, width=7)
        draw.text((legend_x + 85, y_position), f"射线 {index + 1}", font=font(22, bold=True), fill=color, anchor="lm")
    maximum_distance = 240.0
    elevation_values = np.concatenate([profile[1] for profile in profiles])
    elevation_limits = (float(np.floor(np.nanmin(elevation_values))) - 0.5, float(np.ceil(np.nanmax(elevation_values))) + 0.5)
    elevation_series = [
        (profile[0], profile[1], color, fill)
        for profile, color, fill in zip(profiles, COLORS, FILLS, strict=True)
    ]
    relief_series = [
        (profile[0], profile[2], color, fill)
        for profile, color, fill in zip(profiles, COLORS, FILLS, strict=True)
    ]
    slope_series = [
        (profile[0], profile[3], color, fill)
        for profile, color, fill in zip(profiles, COLORS, FILLS, strict=True)
    ]
    draw_panel(draw, (200, 240, 1760, 580), (0.0, maximum_distance), elevation_limits, "A　路径地形剖面", "高程 (km)", elevation_series, fill_profiles=True)
    draw_panel(draw, (200, 735, 1760, 1010), (0.0, maximum_distance), (0.0, 7.0), "B　从震源累计的路径起伏范围", "累计起伏 (km)", relief_series)
    draw_panel(draw, (200, 1165, 1760, 1400), (0.0, maximum_distance), (0.0, 0.20), "C　从震源累计的平均绝对坡度", "平均绝对坡度", slope_series)
    canvas.save(OUTPUT_FILE, quality=95)
    if summary_rows and example_rows:
        write_path_report(summary_rows, example_rows, relationships)
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
