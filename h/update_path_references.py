from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph


SOURCE = Path(r"C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\方法修订_2026-09-16\起伏月表与浅层结构_完整中文稿_v5_图2图6绝对能量.docx")
OUTPUT = Path(r"C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\方法修订_2026-09-16\起伏月表与浅层结构_完整中文稿_v6_路径文献补充.docx")

NEW_DISCUSSION = (
    "累计路径高差范围只能概括已经经过的最高点和最低点。两条路径即使具有相同的累计高差范围，也可能包含不同数量、宽度和排列的陨石坑；当沿程高程始终位于已有极值之间时，局部坡面继续变化而累计高差范围不再增加。这解释了为什么该累计指标未必比直接地形剖面更容易对应每一次振幅波动。M6/M5在路径2上表现出较清晰的变化关系，而路径1和路径3上的对应关系相对较弱。这种路径间差异表明，地形对波场的调制不能仅由传播距离或某一单独的路径起伏指标解释，还取决于起伏地形沿震源—接收点路径的空间分布及其与波场的几何关系。既有研究表明，地形效应具有明显的局地性和方向性，并受到坡度、坡向、曲率、相对高程、地形尺度与波长之比以及入射方向等因素的共同影响；山脊或陨石坑等地形单元位于传播路径上的不同位置时，还可能产生不同程度的聚焦、散焦、屏蔽、散射和波型转换（Spudich et al., 1996; Ma et al., 2007; Lee et al., 2009; Maufroy et al., 2015; Takemura et al., 2015; Kuehnert et al., 2020）。真实地形模拟进一步显示，传播路径相对于地形结构的配置可以显著控制台站间谱比，地形曲率的影响也可能强于单纯的高差或深度；与此同时，不规则地形引起的散射具有较强的局地空间变化，不一定随传播距离单调累积。因此，路径2中较清晰的关系应视为特定路径几何条件下的响应，而不能据此建立适用于所有路径的单一距离—地形关系。鉴于现有三条路径尚不足以同时约束上述相互关联的地形参数，本文不进一步开展多参数定量归因，而仅将路径依赖性作为地形影响复杂性的一项证据。"
)

REFS_BEFORE_NUNN = [
    "Kuehnert, J., Mangeney, A., Capdeville, Y., Métaxian, J. P., Bonilla, L. F., Stutzmann, E., Chaljub, E., Boissier, P., Brunet, C., Kowalski, P., Lauret, F., & Hibert, C. (2020). Simulation of topography effects on rockfall-generated seismic signals: Application to Piton de la Fournaise volcano. Journal of Geophysical Research: Solid Earth, 125(10), e2020JB019874. https://doi.org/10.1029/2020JB019874",
    "Lee, S. J., Komatitsch, D., Huang, B. S., & Tromp, J. (2009). Effects of topography on seismic-wave propagation: An example from Northern Taiwan. Bulletin of the Seismological Society of America, 99(1), 314–325. https://doi.org/10.1785/0120080020",
    "Ma, S., Archuleta, R. J., & Page, M. T. (2007). Effects of large-scale surface topography on ground motions, as demonstrated by a study of the San Gabriel Mountains, Los Angeles, California. Bulletin of the Seismological Society of America, 97(6), 2066–2079. https://doi.org/10.1785/0120070040",
    "Maufroy, E., Cruz-Atienza, V. M., Cotton, F., & Gaffet, S. (2015). Frequency-scaled curvature as a proxy for topographic site-effect amplification and ground-motion variability. Bulletin of the Seismological Society of America, 105(1), 354–367. https://doi.org/10.1785/0120140089",
]

REFS_BEFORE_TRIFUNAC = [
    "Spudich, P., Hellweg, M., & Lee, W. H. K. (1996). Directional topographic site response at Tarzana observed in aftershocks of the 1994 Northridge, California, earthquake: Implications for mainshock motions. Bulletin of the Seismological Society of America, 86(1B), S193–S208. https://doi.org/10.1785/BSSA08601BS193",
    "Takemura, S., Furumura, T., & Maeda, T. (2015). Scattering of high-frequency seismic waves caused by irregular surface topography and small-scale velocity inhomogeneity. Geophysical Journal International, 201(1), 459–474. https://doi.org/10.1093/gji/ggv038",
]


def replace_text_preserving_format(paragraph: Paragraph, text: str) -> None:
    rpr = None
    if paragraph.runs and paragraph.runs[0]._r.rPr is not None:
        rpr = deepcopy(paragraph.runs[0]._r.rPr)
    for child in list(paragraph._p):
        if child.tag.endswith("}pPr"):
            continue
        paragraph._p.remove(child)
    run = paragraph.add_run(text)
    if rpr is not None:
        if run._r.rPr is not None:
            run._r.remove(run._r.rPr)
        run._r.insert(0, rpr)


def insert_reference_before(anchor: Paragraph, template: Paragraph, text: str) -> Paragraph:
    new_p = OxmlElement("w:p")
    if template._p.pPr is not None:
        new_p.append(deepcopy(template._p.pPr))
    anchor._p.addprevious(new_p)
    paragraph = Paragraph(new_p, anchor._parent)
    run = paragraph.add_run(text)
    if template.runs and template.runs[0]._r.rPr is not None:
        run._r.insert(0, deepcopy(template.runs[0]._r.rPr))
    return paragraph


def find_exact(doc: Document, start: str) -> Paragraph:
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith(start):
            return paragraph
    raise RuntimeError(f"Paragraph not found: {start}")


doc = Document(SOURCE)

target = find_exact(doc, "累计路径高差范围只能概括")
replace_text_preserving_format(target, NEW_DISCUSSION)

template = find_exact(doc, "Akaike, H.")
anchor_nunn = find_exact(doc, "Nunn, C.")
for reference in REFS_BEFORE_NUNN:
    insert_reference_before(anchor_nunn, template, reference)

anchor_trifunac = find_exact(doc, "Trifunac, M. D.")
for reference in REFS_BEFORE_TRIFUNAC:
    insert_reference_before(anchor_trifunac, template, reference)

doc.save(OUTPUT)
print(OUTPUT)
