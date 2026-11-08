from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


SRC = Path(r"C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\简单模型更正_2026-09-14\起伏月表与浅层结构_完整中文稿_v3_简单模型.docx")
OUTDIR = Path(r"C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\方法修订_2026-09-16")
MAIN_OUT = OUTDIR / "起伏月表与浅层结构_完整中文稿_v4_方法精简.docx"
SI_OUT = OUTDIR / "Supporting_Information_方法补充_v1.docx"


def set_paragraph_text(paragraph, text):
    ppr = paragraph._p.pPr
    for child in list(paragraph._p):
        if child is not ppr:
            paragraph._p.remove(child)
    paragraph.add_run(text)


def find_paragraph(doc, exact):
    for p in doc.paragraphs:
        if p.text.strip() == exact:
            return p
    raise ValueError(f"paragraph not found: {exact}")


def remove_between(start_p, stop_p):
    node = start_p._p.getnext()
    while node is not None and node is not stop_p._p:
        nxt = node.getnext()
        node.getparent().remove(node)
        node = nxt


def new_paragraph(doc, text="", style="Normal"):
    p = doc.add_paragraph(style=style)
    if text:
        p.add_run(text)
    return p


def math_paragraph(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    omath_para = OxmlElement("m:oMathPara")
    omath = OxmlElement("m:oMath")
    mr = OxmlElement("m:r")
    mt = OxmlElement("m:t")
    mt.set(qn("xml:space"), "preserve")
    mt.text = text
    mr.append(mt)
    omath.append(mr)
    omath_para.append(omath)
    p._p.append(omath_para)
    return p


def insert_elements_after(anchor_p, elements):
    cursor = anchor_p._p
    for element in elements:
        xml = element._p if hasattr(element, "_p") else element._tbl
        cursor.addnext(xml)
        cursor = xml


def set_cell_margins(cell, top=90, start=90, bottom=90, end=90):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def format_table(table, widths_cm):
    table.style = "Table Grid"
    table.autofit = False
    for row_i, row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, width in zip(row.cells, widths_cm):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.0
                for run in p.runs:
                    run.font.size = Pt(9)
        if row_i == 0:
            row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), "D9EAF7")
                cell._tc.get_or_add_tcPr().append(shd)
                for run in cell.paragraphs[0].runs:
                    run.bold = True


def add_table(doc, headers, rows, widths_cm):
    table = doc.add_table(rows=1, cols=len(headers))
    for i, text in enumerate(headers):
        table.rows[0].cells[i].text = str(text)
    for values in rows:
        cells = table.add_row().cells
        for i, text in enumerate(values):
            cells[i].text = str(text)
    format_table(table, widths_cm)
    return table


def add_reference_before(doc, anchor_text, ref_text):
    anchor = find_paragraph(doc, anchor_text)
    p = doc.add_paragraph(ref_text, style=anchor.style)
    anchor._p.addprevious(p._p)


def remove_page_break_before_caption(doc, caption_prefix):
    paragraphs = doc.paragraphs
    for i, paragraph in enumerate(paragraphs):
        if paragraph.text.startswith(caption_prefix) and i >= 2:
            candidate = paragraphs[i - 2]
            page_breaks = [
                br for br in candidate._p.xpath(".//w:br")
                if br.get(qn("w:type")) == "page"
            ]
            if page_breaks and not candidate.text.strip():
                candidate._p.getparent().remove(candidate._p)
            return


def build_main():
    doc = Document(SRC)

    h22 = find_paragraph(doc, "2.2 对照实验与区域模型")
    h23 = find_paragraph(doc, "2.3 波形处理与响应指标")
    remove_between(h22, h23)

    section22 = []
    section22.append(new_paragraph(
        doc,
        "半空间实验先比较平坦与起伏自由表面，再以0.125 km地形为参考，检验0.25、0.5、1、2.5、4、6.25和10 km名义地形分辨率下的记录变化；在相同地形下进一步比较分层与未分层背景。半空间均匀介质取Vp=1.0 km/s、Vs=0.5 km/s。该组速度对应VPREMOON模型浅表1 km低速层的取值，Nunn等（2024）在其基准模型说明中沿用了该结构，而VPREMOON最初由Garcia等（2011）提出。本文仅借用这一低速端元的速度值，不复制VPREMOON的完整分层结构。需要区分的是，Nunn等（2024）的M-2指以Garcia等（2019）的平滑M1模型为背景、并加入延伸至50 km深度随机非均匀性的模型，并不是Vp=1.0 km/s、Vs=0.5 km/s这组速度的直接来源。"
    ))
    section22.append(new_paragraph(
        doc,
        "A16/S12区域模型水平范围为300 × 300 km，计算深度为40 km，设计网格为1500 × 1500 × 200。模型包含A16撞击位置、Apollo 12台站S12及三个传播方向上的接收剖面（图1b）。区域速度、分层界面和随机散射设置均沿用本文原稿的模型配置，其文献基础主要为Jiang等（2015）和Onodera等（2021），并未改用Onodera等（2022）的模型。平坦参考模型由风化层、巨风化层、下月壳和月幔四层组成，材料参数列于表1。"
    ))
    cap1 = new_paragraph(doc, "表1 A16/S12区域模型的分层与材料参数", style="Caption")
    section22.append(cap1)
    table1 = add_table(
        doc,
        ["层", "平坦参考深度 (km)", "Vp (km/s)", "Vs (km/s)", "密度 (g/cm³)", "Q"],
        [
            ["风化层", "0–5", "3.20", "2.30", "2.60", "6750"],
            ["巨风化层", "5–10", "3.20", "2.30", "2.76", "5000"],
            ["下月壳", "10–30", "5.50", "3.18", "2.76", "4000"],
            ["月幔", "30–40", "7.55", "4.36", "3.36", "3750"],
        ],
        [2.6, 3.2, 2.3, 2.3, 2.8, 2.0],
    )
    section22.append(table1)
    section22.append(new_paragraph(
        doc,
        "注：表中参数保持原稿Table 1的设置，主要依据Jiang等（2015）并结合Onodera等（2021）的A16/S12区域模型。Q列为模型配置值；本文不据此单独反演内禀衰减。M5和M6的浅表1 km低速层参数另见下文。",
        style="Caption",
    ))
    section22.append(new_paragraph(
        doc,
        "起伏模型不是把表1中的平坦界面整体平移，而是依据月表高程和局部地壳厚度构造地下界面。按照Onodera等（2021）及本文原稿，风化层底界面和巨风化层底界面分别写为"
    ))
    section22.append(math_paragraph(doc, "Dreg(x,y) = Dsurf(x,y) + [Dcrust(x,y) − Dsurf(x,y)] / C₁.    (1)"))
    section22.append(math_paragraph(doc, "DMreg(x,y) = Dsurf(x,y) + [Dcrust(x,y) − Dsurf(x,y)] / C₂.    (2)"))
    section22.append(new_paragraph(
        doc,
        "其中x和y为经度与纬度；Dsurf、Dreg、DMreg和Dcrust分别表示月表、风化层—巨风化层界面、巨风化层—下月壳界面以及月壳—月幔界面的深度。C₁=5.84、C₂=2.92，使Apollo 12和Apollo 14邻区的风化层和巨风化层平均厚度分别约为5和10 km（Onodera et al., 2021）。平坦模型对应界面深度为0、5、10、30和40 km；起伏模型则读取相应的地形与地下界面文件，从而同时保留自由表面起伏和随位置变化的层厚。"
    ))
    section22.append(new_paragraph(
        doc,
        "M3–M6的随机散射介质沿用原稿所依据的随机介质统计建模框架（Jiang et al., 2015; Onodera et al., 2021）。本文简单模型采用三维冯·卡尔曼自相关生成零均值相对速度扰动：风化层和巨风化层的扰动标准差分别为9%和5%，相关尺度为4.5 km；起伏模型中的随机场随相应介质层分布。上述配置保持本研究既有A16/S12模型不变，不应归因于Onodera等（2022）。"
    ))
    section22.append(new_paragraph(
        doc,
        "M5和M6在上述结构顶端另设1 km厚的均匀低速层，顶界面随局部月表起伏，层内Vp=1.38 km/s、Vs=0.9 km/s、ρ=2.60 g/cm³，且不叠加随机速度扰动。该设置保持原稿的A16/S12低速层方案。六个区域模型采用嵌套对照设计（表2）：M2/M1、M4/M3和M6/M5隔离不同地下背景上的地形附加响应；M3/M1与M4/M2描述随机非均匀性的附加响应；M5/M3和M6/M4描述低速层的附加响应。"
    ))
    cap2 = new_paragraph(doc, "表2 A16/S12区域模型及配对关系", style="Caption")
    section22.append(cap2)
    table2 = add_table(
        doc,
        ["模型", "表面", "随机非均匀性", "附加1 km低速层"],
        [
            ["M1", "平坦", "无", "无"],
            ["M2", "真实地形", "无", "无"],
            ["M3", "平坦", "有", "无"],
            ["M4", "真实地形", "有", "无"],
            ["M5", "平坦", "有", "有"],
            ["M6", "真实地形", "有", "有"],
        ],
        [2.4, 3.8, 4.6, 4.6],
    )
    section22.append(table2)
    section22.append(new_paragraph(
        doc,
        "区域模型采用0–400 s分析窗。M5和M6的原始记录延伸至约400 s，M1–M4延伸至约250 s；后者在原始记录结束后补零，但补零段不作为实际计算波形解释。半空间统计使用约0–100 s公共记录范围。"
    ))
    insert_elements_after(h22, section22)

    h3 = find_paragraph(doc, "3 结果")
    remove_between(h23, h3)
    set_paragraph_text(h23, "2.3 主文分析设置")
    section23 = []
    section23.append(new_paragraph(
        doc,
        "主文统一分析0.3–0.9 Hz频带。Nunn等（2024）指出，Apollo中周期地震仪记录的人工撞击信号在0.3–0.9 Hz内具有较好的信噪比，这与仪器在该频段的高灵敏度有关，而频带以外通常更易受噪声影响。尽管半空间模型的数值分辨率允许分析更宽的约0.16–2.0 Hz范围，主文仍选用0.3–0.9 Hz作为观测与模拟的共同比较频带；宽频带结果作为敏感性检验在Supporting Information中给出。"
    ))
    section23.append(new_paragraph(
        doc,
        "持续时间采用累计三分量平方速度由5%增长至95%所经历的区间T90，而不使用单独的t95代表持续时间："
    ))
    section23.append(math_paragraph(doc, "T90 = t0.95 − t0.05.    (3)"))
    section23.append(new_paragraph(
        doc,
        "这一指标沿用累计平方运动5%–95%区间的持续时间思想（Trifunac & Brady, 1975; Dammeier et al., 2011），能够排除累计曲线两端对微弱噪声和记录截断最敏感的部分。本文的T90严格对应给定有限分析窗，不解释为完整月震尾波的终止时间。"
    ))
    section23.append(new_paragraph(
        doc,
        "区域三个剖面分别去除两端各5站后保留203、230和142站。为减弱密集沿线采样造成的伪重复，每条路径按震源距排序，以连续10站构成一个非重叠空间块，仅保留完整块，共57块。涉及路径汇总和不确定区间的统计均以空间块而非单个台站作为重采样或汇总单元；完整筛选和自助法设置见Supporting Information。"
    ))
    section23.append(new_paragraph(
        doc,
        "峰时距离趋势分别拟合线性形式和平方距离形式："
    ))
    section23.append(math_paragraph(doc, "tmax = a + bR;    tmax = a + cR².    (4)"))
    section23.append(new_paragraph(
        doc,
        "两种形式在相同台站样本上按高斯残差似然的Akaike信息准则比较（Akaike, 1974）："
    ))
    section23.append(math_paragraph(doc, "AIC = n ln(RSS/n) + 2k + constant;    ΔAIC = AICR² − AICR.    (5)"))
    section23.append(new_paragraph(
        doc,
        "其中n为样本数，RSS为残差平方和，k为估计参数数目。两种形式均含截距和一个距离系数，k相同；因此ΔAIC>0表示线性形式获得更小的AIC并受到相对支持。AIC只比较当前候选模型及共同误差假设下的相对拟合，不将平方项系数直接解释为扩散系数。其余坐标旋转、能量与峰时定义、台站筛选、相关统计及观测归一化步骤见Supporting Information。"
    ))
    insert_elements_after(h23, section23)

    replacements = {
        "表2同时列出各模型Ej的逐站中位数及配对比值中位数。": "表3同时列出各模型Ej的逐站中位数及配对比值中位数。",
        "（表2）": "（表3）",
        "表2所示": "表3所示",
        "见表2": "见表3",
        "同组671个保留台站的R/T/Z绝对能量积分见表2。": "同组671个保留台站的R/T/Z绝对能量积分见表3。",
        "同组144个保留台站的分量绝对积分见表2。": "同组144个保留台站的分量绝对积分见表3。",
        "表2 图2与图6配对台站的绝对分量能量积分": "表3 图2与图6配对台站的绝对分量能量积分",
        "本文式(8)中的截距和系数": "本文式(4)中的截距和系数",
    }
    for p in doc.paragraphs:
        text = p.text
        new = text
        for old, repl in replacements.items():
            new = new.replace(old, repl)
        if new != text:
            set_paragraph_text(p, new)

    for p in doc.paragraphs:
        if p.text.startswith("M5和M6在上述结构顶端另设1 km厚的均匀低速层"):
            set_paragraph_text(p, p.text.replace("（表3）", "（表2）"))

    for p in doc.paragraphs:
        if "d维扩散能量密度满足" in p.text:
            set_paragraph_text(
                p,
                "在均匀无限介质、常数扩散系数D、瞬时点源且无吸收的理想条件下，"
                "d维扩散能量密度满足 E_d(t,R) ∝ t^(−d/2) exp[−R²/(4Dt)]，"
                "对时间求极值得到tmax=R²/(2dD)。该表达式仅用于说明平方距离标度的物理出处。"
                "Gillet等（2017）实际采用球形、深度依赖的散射与吸收描述，不能被简化为所有月震路径都必须严格满足同一个二次函数。"
                "本文式(4)中的截距和系数是经验拟合参数，并未将c直接转换为月球扩散系数。"
            )

    nunn_ref = "Nunn, C., Fernando, B. A., & Panning, M. P. (2024). Artificial Impacts on the Moon: Modeling 3D Seismic Propagation Effects with AxiSEM3D. The Planetary Science Journal, 5(11), 246. https://doi.org/10.3847/PSJ/ad83d2"
    add_reference_before(
        doc,
        nunn_ref,
        "Garcia, R. F., Gagnepain-Beyneix, J., Chevrot, S., & Lognonné, P. (2011). Very preliminary reference Moon model. Physics of the Earth and Planetary Interiors, 188(1–2), 96–113. https://doi.org/10.1016/j.pepi.2011.06.015",
    )
    add_reference_before(
        doc,
        nunn_ref,
        "Garcia, R. F., Khan, A., Drilleau, M., et al. (2019). Lunar seismology: An update on interior structure models. Space Science Reviews, 215, 50. https://doi.org/10.1007/s11214-019-0613-y",
    )
    add_reference_before(
        doc,
        nunn_ref,
        "Jiang, X., Wang, Y., & Furumura, T. (2015). Numerical simulation of lunar seismic coda caused by scattering in the upper Moon crust. Chinese Journal of Geophysics, 58(5), 1675–1691. https://doi.org/10.6038/cjg20150519",
    )

    # Figure 7 and its long caption already fill a page.  The inherited manual
    # page break therefore generated an entirely blank page before Figure 8.
    remove_page_break_before_caption(doc, "图8 Apollo 12")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    doc.save(MAIN_OUT)


def configure_si_styles(doc):
    sec = doc.sections[0]
    sec.top_margin = Cm(2.3)
    sec.bottom_margin = Cm(2.3)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.6)
    styles = doc.styles
    for name in ("Normal", "Title", "Heading 1", "Heading 2"):
        style = styles[name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        style.font.color.rgb = None
    styles["Normal"].font.size = Pt(10.5)
    styles["Normal"].paragraph_format.line_spacing = 1.35
    styles["Normal"].paragraph_format.space_after = Pt(6)
    styles["Title"].font.size = Pt(16)
    styles["Heading 1"].font.size = Pt(13)
    styles["Heading 2"].font.size = Pt(11.5)


def add_si_math(doc, text):
    return math_paragraph(doc, text)


def build_si():
    doc = Document()
    configure_si_styles(doc)
    title = doc.add_paragraph("Supporting Information 方法补充", style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(
        "本文件集中说明主文中为保持篇幅简洁而未展开的波形处理、坐标旋转、指标计算、台站筛选和统计实现。所有定义均对应当前正文图件与0–400 s区域分析，不改变主文结果。"
    )

    doc.add_paragraph("S1 坐标旋转与三分量表示", style="Heading 1")
    doc.add_paragraph(
        "速度记录经去趋势和零相位带通滤波后，在公共时间轴上比较。根据接收点相对于震源的方位角θ，将模型水平分量X/Y旋转到径向R和横向T，Z保持垂向；θ从模型+x方向逆时针计算。"
    )
    add_si_math(doc, "vR = vX cosθ + vY sinθ;    vT = −vX sinθ + vY cosθ;    vZ = vZ.    (S1)")
    doc.add_paragraph("正交旋转保持三分量平方和不变，但单分量波形和能量占比必须在RTZ系中重新计算。")

    doc.add_paragraph("S2 振幅和接收点能量指标", style="Heading 1")
    doc.add_paragraph("定义瞬时三分量平方速度和I(t)、矢量峰值A、接收点能量积分E以及各分量积分Ej和占比fj：")
    add_si_math(doc, "I(t) = vR²(t) + vT²(t) + vZ²(t);    A = maxt √I(t).    (S2)")
    add_si_math(doc, "E = ∫₀ᵀ I(t)dt;    Ej = ∫₀ᵀ vj²(t)dt;    fj = Ej/E,  j∈{R,T,Z}.    (S3)")
    doc.add_paragraph(
        "E和Ej为接收点振动强度比较指标，单位为原始速度单位的平方乘秒，不等同于全模型机械总能量或穿过某一面的能流。模型间比值先逐站配对计算，再汇总其中位数及分位范围。"
    )

    doc.add_paragraph("S3 累计能量持续时间与峰值时间", style="Heading 1")
    doc.add_paragraph("累计能量比例及分位到时定义为")
    add_si_math(doc, "C(t) = [∫₀ᵗ I(τ)dτ]/E;    tp = inf{t: C(t) ≥ p};    T90 = t0.95 − t0.05.    (S4)")
    doc.add_paragraph(
        "T90采用有限分析窗内累计三分量平方速度的5%–95%区间。小写t95仅表示95%累计量到时，不单独作为持续时间。"
    )
    doc.add_paragraph("峰值时间采用三分量解析能量并统一使用20 s滑动平均：")
    add_si_math(doc, "Ia(t) = Σj |vj(t) + iH[vj(t)]|²;    tmax = argmaxt S20[Ia(t)].    (S5)")
    doc.add_paragraph(
        "H表示Hilbert变换，S20表示20 s滑动平均。解析信号仅用于稳定包络峰时；能量积分仍按式(S3)直接由平方速度计算。全文tmax从震源时刻t=0起算，不减去t05或初至到时；峰值在记录补零前确定。图8比较单分量振幅包络，因此其分量峰时不要求与式(S5)的三分量峰时一致。"
    )

    doc.add_paragraph("S4 台站筛选、空间块与自助法", style="Heading 1")
    doc.add_paragraph(
        "台站按几何、记录完整性和分析用途筛选，不按模型间相关高低或响应正负筛选。图2的800站剖面要求两配对模型在95 s之后的剩余能量比例均不超过1%，保留671站；图6从216站阵列中按对应末端标准保留144站。图3使用r20–r760的几何区间；图5分辨率统计使用完整216站阵列。"
    )
    doc.add_paragraph(
        "区域三个剖面去除两端各5站后分别保留203、230和142站。各路径按震源距排序，以连续10站组成互不重叠的空间块，仅使用完整块，共57块。图7(b)先在块内计算配对差中位数，再汇总57个块中位数。95%区间通过块层面有放回重采样5000次获得，取重采样分布的2.5%和97.5%分位数；当前随机种子为20260913。该区间描述空间样本变异，不代表不同随机介质实现之间的不确定性。"
    )

    doc.add_paragraph("S5 波形相似性与相关系数", style="Heading 1")
    doc.add_paragraph("波形和包络相似性使用Pearson相关系数：")
    add_si_math(doc, "r = Σi(xi−x̄)(yi−ȳ) / √[Σi(xi−x̄)² Σi(yi−ȳ)²].    (S6)")
    doc.add_paragraph(
        "除地形分辨率检验明确允许±2 s时移并取最大相关外，主文相关均采用零时移。分辨率检验同时计算能量绝对相对误差|E−Eref|/Eref，并以相关不小于0.95且能量误差不超过10%作为本实验的数值一致性判据。"
    )
    doc.add_paragraph(
        "Spearman系数通过对变量取秩后计算Pearson相关得到，并列值采用平均秩。相关系数用于描述单调联系，不解释为地形指标对响应的因果解释比例。"
    )

    doc.add_paragraph("S6 沿程地形与距离趋势", style="Heading 1")
    doc.add_paragraph("沿程累计高差范围定义为")
    add_si_math(doc, "H(R) = max{h(s): 0≤s≤R} − min{h(s): 0≤s≤R}.    (S7)")
    doc.add_paragraph(
        "H(R)表示从震源至接收点已经跨越的高程范围，不是逐段绝对高差之和，也不等于台站处高程或局部坡度。图7(d)比较H与低速背景地形响应ln[Q(M6)/Q(M5)]，Q取A、E或T90。每条路径分别以三次多项式去除H和响应中的距离趋势，再对标准化残差计算Spearman相关；57块统计先取路径内块中位数，再在块层面计算相关。"
    )

    doc.add_paragraph("S7 峰时距离模型与AIC", style="Heading 1")
    add_si_math(doc, "tmax = a + bR;    tmax = a + cR².    (S8)")
    add_si_math(doc, "AIC = n ln(RSS/n) + 2k + constant;    ΔAIC = AICR² − AICR.    (S9)")
    doc.add_paragraph(
        "M6主分析样本进一步要求震源距不小于10 km、峰值距记录两端至少20 s，且t95距原始记录末端至少20 s；三条路径分别保留165、149和135站。线性和平方距离形式使用完全相同的台站样本。两者均含截距和一个距离系数，k相同，故ΔAIC>0支持线性形式。AIC只用于候选经验形式之间的相对比较，不据此反演扩散系数。"
    )

    doc.add_paragraph("S8 Apollo观测比较", style="Heading 1")
    doc.add_paragraph(
        "Apollo 12观测和模拟均以撞击时刻为t=0，并采用相同0.3–0.9 Hz频带比较前400 s。为展示波形形态，每个模型在共同可用的约0–250 s内求取一个三分量RMS幅度倍率，并对三个分量共同缩放，不逐分量自由调幅。图8包络相关不搜索时移；联合相关在各分量去均值后拼接计算，缺失端点不纳入。该比较检验早期包络形态，不标定撞击耦合效率，也不验证逐周期相位。"
    )

    doc.add_paragraph("SI参考文献", style="Heading 1")
    refs = [
        "Akaike, H. (1974). A new look at the statistical model identification. IEEE Transactions on Automatic Control, 19(6), 716–723. https://doi.org/10.1109/TAC.1974.1100705",
        "Dammeier, F., Moore, J. R., Haslinger, F., & Loew, S. (2011). Characterization of alpine rockslides using statistical analysis of seismic signals. Journal of Geophysical Research, 116, F04024. https://doi.org/10.1029/2011JF002037",
        "Efron, B. (1979). Bootstrap methods: Another look at the jackknife. The Annals of Statistics, 7(1), 1–26. https://doi.org/10.1214/aos/1176344552",
        "Gillet, K., Margerin, L., Calvet, M., & Monnereau, M. (2017). Scattering attenuation profile of the Moon: Implications for shallow moonquakes and the structure of the megaregolith. Physics of the Earth and Planetary Interiors, 262, 28–40. https://doi.org/10.1016/j.pepi.2016.11.001",
        "Trifunac, M. D., & Brady, A. G. (1975). A study on the duration of strong earthquake ground motion. Bulletin of the Seismological Society of America, 65(3), 581–626. https://doi.org/10.1785/BSSA0650030581",
    ]
    for ref in refs:
        doc.add_paragraph(ref)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    doc.save(SI_OUT)


if __name__ == "__main__":
    build_main()
    build_si()
    print(MAIN_OUT)
    print(SI_OUT)
