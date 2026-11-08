from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter, LogLocator, ScalarFormatter
import numpy as np
import pandas as pd
from PIL import Image
from docx import Document
from docx.oxml.ns import qn


ROOT = Path(r"C:\Users\Administrator\Desktop\起伏月表影响数值模拟")
POST = ROOT / "投稿文件"
DATA_ROOT = ROOT / "数据图表" / "绘图数据"
REV = POST / "正文定向修订_2026-09-13"
SRC_DOC = POST / "方法修订_2026-09-16" / "起伏月表与浅层结构_完整中文稿_v4_方法精简.docx"
OUT_DIR = POST / "方法修订_2026-09-16"
OUT_DOC = OUT_DIR / "起伏月表与浅层结构_完整中文稿_v5_图2图6绝对能量.docx"

BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"


def set_paragraph_text(paragraph, text):
    ppr = paragraph._p.pPr
    for child in list(paragraph._p):
        if child is not ppr:
            paragraph._p.remove(child)
    paragraph.add_run(text)


def component_quantiles(energy, model, component, fractions=False):
    subset = energy.loc[energy.model.eq(model)]
    values = subset[f"E{component}"].to_numpy(float)
    if fractions:
        values = 100.0 * values / subset["Etotal"].to_numpy(float)
    return np.quantile(values, [.25, .5, .75])


def draw_ratio_panel(ax, metrics, kind):
    cols = ["peak_amplitude_ratio", "energy_ratio", "t90_ratio"]
    bounds = []
    for x, column in enumerate(cols):
        p10, p25, med, p75, p90 = metrics[column].quantile([.1, .25, .5, .75, .9])
        ax.vlines(x, p10, p90, color=".25", lw=.8)
        ax.vlines(x, p25, p75, color=".25", lw=3.2)
        ax.plot(x, med, "o", color="white", mec=".15", ms=3.2, zorder=3)
        bounds.extend([p10, p90])
        if kind == 2:
            ax.text(x, .965, f"{med:.3g}×", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.5)
        else:
            ax.text(x, p90 * 1.16, f"{med:.2f}×", ha="center", va="bottom", fontsize=5.5)
    ax.axhline(1, color=".4", ls="--", lw=.7)
    ax.set_yscale("log")
    if kind == 2:
        ax.set_ylim(min(min(bounds) * .6, .8), max(max(bounds) * 2.3, 1.5))
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, pos: f"{value:g}"))
        ax.set_ylabel("topography / flat")
    else:
        ax.set_ylim(.72, 7)
        ax.set_yticks([1, 2, 4])
        ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.set_ylabel("layered / topography")
    ax.set_xlim(-.5, 2.5)
    ax.set_xticks([0, 1, 2], ["Peak", "Energy", "$T_{90}$"])
    ax.minorticks_off()
    ax.grid(axis="y", alpha=.18, lw=.4)


def draw_fraction_panel(ax, energy, models, colors, markers):
    offsets = [-.15, .15]
    for off, model, color, marker in zip(offsets, models, colors, markers):
        q = np.array([component_quantiles(energy, model, comp, True) for comp in "RTZ"])
        x = np.arange(3) + off
        ax.errorbar(
            x, q[:, 1], yerr=[q[:, 1] - q[:, 0], q[:, 2] - q[:, 1]],
            fmt=marker, color=color, markersize=3.4, lw=.7, capsize=1.8, label=model.lower(),
        )
        for xx, med, upper in zip(x, q[:, 1], q[:, 2]):
            ax.text(xx, upper + 2.0, f"{med:.1f}", ha="center", va="bottom", fontsize=5.2)
    ymax = max(component_quantiles(energy, model, comp, True)[2] for model in models for comp in "RTZ") + 16
    ax.set_ylim(0, ymax)
    ax.set_xlim(-.5, 2.5)
    ax.set_xticks([0, 1, 2], ["R", "T", "Z"])
    ax.set_ylabel("Component energy (%)")
    ax.grid(axis="y", alpha=.18, lw=.4)


def draw_absolute_panel(ax, energy, models, colors, markers):
    offsets = [-.15, .15]
    for off, model, color, marker in zip(offsets, models, colors, markers):
        q = np.array([component_quantiles(energy, model, comp, False) for comp in "RTZ"])
        x = np.arange(3) + off
        ax.errorbar(
            x, q[:, 1], yerr=[q[:, 1] - q[:, 0], q[:, 2] - q[:, 1]],
            fmt=marker, color=color, markersize=3.4, lw=.7, capsize=1.8, label=model.lower(),
        )
    ax.set_yscale("log")
    ax.set_xlim(-.5, 2.5)
    ax.set_xticks([0, 1, 2], ["R", "T", "Z"])
    ax.set_ylabel(r"$\int v_j^2dt$ (native units$^2$ s)")
    ax.grid(axis="y", alpha=.18, lw=.4)


def make_figure(kind):
    if kind == 2:
        source = POST / "完整中文稿_2026-09-12" / "核查素材" / "figure2.png"
        metrics_path = DATA_ROOT / "Fig02_FlatTopography_ThreeComponentComparison_v04_retained_station_metrics.csv"
        energy_path = REV / "Figure2_absolute_component_energy.csv"
        models, colors, markers = ["Flat", "Topography"], [BLUE, ORANGE], ["o", "s"]
        stem = "Figure2_增加绝对分量能量_v05"
    else:
        source = POST / "完整中文稿_2026-09-12" / "核查素材" / "figure6.png"
        metrics_path = DATA_ROOT / "Fig05_BackgroundLayering_ThreeComponentComparison_v04_retained_station_metrics.csv"
        energy_path = REV / "Figure6_absolute_component_energy.csv"
        models, colors, markers = ["Topography", "Layered"], [BLUE, GREEN], ["o", "s"]
        stem = "Figure6_增加绝对分量能量_v05"

    background = Image.open(source).convert("RGB")
    width, height = background.size
    dpi = 220
    metrics = pd.read_csv(metrics_path)
    energy = pd.read_csv(energy_path)
    expected_n = 671 if kind == 2 else 144
    assert len(metrics) == expected_n
    assert energy.groupby("model").size().eq(expected_n).all()
    assert list(energy.model.drop_duplicates()) == models

    plt.rcParams.update({
        "font.family": "Arial", "font.size": 6, "axes.labelsize": 5.7,
        "axes.titlesize": 6, "xtick.labelsize": 5.2, "ytick.labelsize": 5.2,
        "axes.linewidth": .65, "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    bg = fig.add_axes([0, 0, 1, 1], zorder=0)
    bg.imshow(background)
    bg.axis("off")
    fig.add_artist(Rectangle((0, 0), 1, .325, transform=fig.transFigure, facecolor="white", edgecolor="none", zorder=1))

    title_y, subtitle_y = .296, .276
    xs = [.075, .382, .690]
    widths = [.255, .255, .285]
    fig.text(xs[0], title_y, "(c) Peak, energy, and duration ratios", va="top", fontsize=6, zorder=3)
    fig.text(xs[0], subtitle_y, "Median, IQR, and 10–90% range", va="top", fontsize=5.2, zorder=3)
    fig.text(xs[1], title_y, "(d) Component energy fractions", va="top", fontsize=6, zorder=3)
    fig.text(xs[1], subtitle_y, "Median and interquartile range", va="top", fontsize=5.2, zorder=3)
    fig.text(xs[2], title_y, "(e) Absolute component integrals", va="top", fontsize=6, zorder=3)
    fig.text(xs[2], subtitle_y, "Median and interquartile range", va="top", fontsize=5.2, zorder=3)

    axes = [fig.add_axes([x, .082, w, .162], zorder=2) for x, w in zip(xs, widths)]
    draw_ratio_panel(axes[0], metrics, kind)
    draw_fraction_panel(axes[1], energy, models, colors, markers)
    draw_absolute_panel(axes[2], energy, models, colors, markers)
    fig.text(.075, .032, f"All panels use the same {expected_n} retained stations.", fontsize=5.2, zorder=3)
    legend_handles = [
        Line2D([], [], color=color, marker=marker, lw=0, markersize=3.5, label=model.lower())
        for model, color, marker in zip(models, colors, markers)
    ]
    fig.legend(
        handles=legend_handles, loc="lower right", bbox_to_anchor=(.975, .018),
        ncol=2, frameon=False, fontsize=5.2, handletextpad=.25, columnspacing=.8,
    )

    png = OUT_DIR / f"{stem}.png"
    pdf = OUT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=dpi, facecolor="white")
    fig.savefig(pdf, dpi=dpi, facecolor="white")
    plt.close(fig)
    return png


def replace_embedded_figure(doc, figure_number, image_path):
    paragraphs = doc.paragraphs
    caption_index = next(i for i, p in enumerate(paragraphs) if p.text.startswith(f"图{figure_number} "))
    image_p = paragraphs[caption_index - 1]
    blips = image_p._p.xpath(".//a:blip")
    assert len(blips) == 1
    rid = blips[0].get(qn("r:embed"))
    image_part = doc.part.related_parts[rid]
    image_part._blob = image_path.read_bytes()


def remove_table3(doc):
    caption = next(p for p in doc.paragraphs if p.text.startswith("表3 图2与图6"))
    table_node = caption._p.getnext()
    assert table_node.tag == qn("w:tbl")
    note_node = table_node.getnext()
    assert note_node.tag == qn("w:p")
    note_text = "".join(note_node.itertext())
    assert "Ej=" in note_text and "671站" in note_text
    parent = caption._p.getparent()
    parent.remove(caption._p)
    parent.remove(table_node)
    parent.remove(note_node)


def revise_document(fig2, fig6):
    doc = Document(SRC_DOC)
    replacements = {
        "（表3）": "（图2e）",
        "其中T的逐站配对增幅中位数大于R和Z（图2e）": "其中T的逐站配对增幅中位数大于R和Z（图6e）",
        "表3所示的R、Z绝对积分减少与T绝对积分增加": "图2(e)所示的R、Z绝对积分减少与T绝对积分增加",
    }
    for paragraph in doc.paragraphs:
        text = paragraph.text
        new = text
        for old, replacement in replacements.items():
            new = new.replace(old, replacement)
        if paragraph.text.startswith("图2 半空间中地形相对于平坦表面的响应。"):
            new = (
                "图2 半空间中地形相对于平坦表面的响应。记录经0.3–0.9 Hz滤波；配对统计窗口为0–99.98 s。"
                "a为代表性R/T/Z波形，同一台站的六条记录采用共同振幅尺度；b为零时移三分量相关与能量比，"
                "颜色为90%累计能量持续时间T90的差；c为逐站峰值、能量及T90比的中位数、四分位区间和10%–90%范围；"
                "d为分量能量占比中位数及四分位区间；e为同组671个保留台站的R/T/Z绝对平方速度积分中位数及四分位区间。"
                "d和e中的圆点与方点分别表示平坦和地形模型。"
            )
        elif paragraph.text.startswith("图6 地形背景上的分层响应。"):
            new = (
                "图6 地形背景上的分层响应。记录经0.3–0.9 Hz滤波，配对统计窗口为0–99.88 s。"
                "a为代表性R/T/Z速度记录，同一台站的两模型采用共同振幅尺度；b为零时移三分量相关与分层/未分层能量比，"
                "颜色为T90差；c为峰值、能量和T90配对比中位数、四分位区间及10%–90%范围；"
                "d为R/T/Z能量占比中位数及四分位区间；e为同组144个保留台站的R/T/Z绝对平方速度积分中位数及四分位区间。"
                "d和e中的圆点与方点分别表示地形模型和分层模型。"
            )
        if new != text:
            set_paragraph_text(paragraph, new)

    remove_table3(doc)
    replace_embedded_figure(doc, 2, fig2)
    replace_embedded_figure(doc, 6, fig6)
    doc.save(OUT_DOC)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig2 = make_figure(2)
    fig6 = make_figure(6)
    revise_document(fig2, fig6)
    print(fig2)
    print(fig6)
    print(OUT_DOC)


if __name__ == "__main__":
    main()
