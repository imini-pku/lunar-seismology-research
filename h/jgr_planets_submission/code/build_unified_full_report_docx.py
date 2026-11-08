"""Rebuild only the integrated report DOCX with the A16 M1-M6 framing.

The evidence-unit inventory remains unchanged; this wrapper adds the unified
model-ladder narrative and figures before the detailed conditional audits.
The Markdown report is maintained separately so that its extended prose is
not overwritten by the legacy evidence-unit generator.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
PROJECT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[2]
sys.path.insert(0, str(PROJECT / "code"))
sys.path.insert(0, str(WORKSPACE / "work" / "python_pkgs"))

from docx import Document  # noqa: E402

from build_low_velocity_and_integrated_reports import (  # noqa: E402
    FIGURES,
    FULL_DOCX,
    add_callout,
    add_conclusion_group,
    add_figure,
    add_heading,
    add_input_audit_appendix,
    add_low_summary_tables,
    add_methodology,
    add_paragraph,
    configure_document,
    halfspace_conclusions,
    a16_conclusions,
    low_conclusions,
    synthesis_conclusions,
    add_final_conclusions,
    PALE_BLUE,
    PALE_GOLD,
    BLUE,
    GOLD,
)

OUTPUT_DOCX = PROJECT / "reports" / "月球地形_分层_散射_低速层全模型综合分析报告_A16统一版.docx"


def build() -> None:
    doc = Document()
    configure_document(doc, "月球地形-分层-散射-低速层全模型综合分析｜A16 M1-M6统一版")
    add_heading(doc, "月球地形、分层、散射与低速层全模型综合分析", 0)
    add_paragraph(doc, "从半空间机制试验到 A16/S12 M1–M6 统一模型链与 Apollo 排除检验", after=8)
    add_paragraph(doc, "本版本将 A16 的六个输出组织为同一条连续模型链；低速层图件作为 M5/M6 节点的条件性审计，而不是独立研究分支。", after=12)
    add_heading(doc, "执行摘要：统一 A16 主线", 1)
    add_callout(doc, "总论", "M1→M6 依次展示平坦基准、地形分配、散射展宽、非加性组合以及低速层能量滞留；M5/M6 延迟峰时并增加晚期能量，但仍不足以解释 Apollo 长尾。", fill=PALE_BLUE, border=BLUE)
    add_low_summary_tables(doc)
    add_methodology(doc, integrated=True)

    add_heading(doc, "A16/S12 M1–M6统一模型链（正文主结果）", 1)
    add_paragraph(doc, "M1 平坦/无散射 → M2 地形/无散射 → M3 平坦/散射 → M4 地形/散射 → M5 平坦/散射/低速层 → M6 地形/散射/低速层。M5/M6 保持 A16 台站体系和已有散射背景，因此是条件状态。", after=7)
    add_figure(doc, FIGURES / "synthesis" / "Figure_A16_M1_M6_unified_ladder.png", "A16 M1–M6 统一模型链：能量、持续时间、峰时、三分量与峰值的连续变化。", width=6.0, alt_text="A16 M1-M6 unified model ladder")
    add_paragraph(doc, "主台站中位数 tmax/T90/t95 从 M1 的 58.3/3.4/73.1 s 变为 M6 的 173.1/146.8/231.0 s；T 分量占比从近零升至约 29%。该变化应作为连续机制链解释，不应拆成四模型论文和低速层附录两条主线。", after=7)
    add_figure(doc, FIGURES / "synthesis" / "Figure_A16_M1_M6_tmax_distance.png", "A16 M1–M6 三条剖面的峰能量迁移；低速层增加斜率与离散度但未产生 R² 扩散律。", width=6.0, alt_text="A16 M1-M6 tmax distance")
    add_paragraph(doc, "缺少低速层+无散射单元，因此不能估计完整三因素纯主效应；M5/M3 与 M6/M4 是已有散射背景下的条件对比。", after=10)

    hs = halfspace_conclusions()
    a16 = a16_conclusions()
    low = low_conclusions()
    synth = synthesis_conclusions()
    counter = [0]
    total = len(hs) + len(a16) + len(low) + len(synth)
    groups = [
        ("支持性一｜半空间机制、分辨率与分层", "半空间建立地形三分量机制、收敛标准、分层边际效应和真实800台站距离诊断。", hs),
        ("支持性二｜A16 M1–M4 基线节点", "M1–M4 是统一六模型链的前四个节点，用于分离地形、随机非均匀性和二阶交互。", a16),
        ("支持性三｜A16 M5/M6 条件节点审计", "LV01–LV24 细化统一模型链中 M5/M6 的公共窗、延长窗、路径和观测失配边界。", low),
        ("支持性四｜跨尺度综合判断", "只在几何、窗口和运行清单边界清楚时整合不同阶段证据。", synth),
    ]
    for title, intro, items in groups:
        add_conclusion_group(doc, title, intro, items, counter, total)

    add_heading(doc, "推荐论文结构（A16不拆分）", 1)
    for title, body in (
        ("1 Introduction", "提出地形、随机非均匀性和低速层对三分量及长尾的共同影响。"),
        ("2 Methods", "半空间控制试验、A16/S12 M1–M6 模型链、逐站 R/T 旋转、公共/延长窗口和统计规则。"),
        ("3 Half-space validation", "地形三分量、分辨率双阈值、分层尾能量与线性距离诊断。"),
        ("4 A16/S12 unified M1–M6 results", "按 M1→M6 连续展示展宽、地形分配、非加性、低速滞留、路径和传播律。"),
        ("5 Apollo S12 comparison", "六模型三分量、包络、累计能量和相位/包络相关的同图检验。"),
        ("6 Discussion and limitations", "背景依赖、缺失低速层+无散射单元、记录删失、随机实现和缺失运行清单。"),
        ("7 Conclusions", "只保留必要但不充分、条件耦合和长尾仍未解释等证据链结论。"),
    ):
        add_heading(doc, title, 2)
        add_paragraph(doc, body, after=7)
    add_callout(doc, "投稿主结论", "真实地形、随机非均匀性和低速层都是早期月球波形建模的必要组成，但在当前尺度与记录长度内仍不足以产生 Apollo 的数千秒长尾。", fill=PALE_GOLD, border=GOLD)
    add_final_conclusions(doc)
    add_input_audit_appendix(doc)
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_DOCX)
    print(OUTPUT_DOCX)


if __name__ == "__main__":
    build()
