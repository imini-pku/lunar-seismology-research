"""Insert the new A16S12 quantitative results into the reviewer-response draft."""

from __future__ import annotations

import copy
import datetime as dt
import zipfile
from pathlib import Path

from lxml import etree


SOURCE_DOCX = Path(
    r"C:\Users\Administrator\Desktop\组会\月震论文\revise用"
    r"\审稿意见回复初稿——吴天雄_R.docx"
)
OUTPUT_DOCX = Path(__file__).resolve().parent / "审稿意见回复初稿——吴天雄_R_数据补充.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}

REPLACEMENTS = {
    "三维非均匀散射确实是月震模拟中非常重要的影响因素": (
        "三维非均匀散射确实是月震模拟中非常重要的影响因素（补充参考文献）。为了在理论模型中"
        "分离地形的独立作用，原稿没有加入三维速度扰动；在A16S12模拟中，我们则参考"
        "Onodera et al. (2022)设置了三维分层结构，并进一步加入随机速度扰动，以建立同时"
        "包含真实地形、浅表低速层、三维非均匀结构和随机散射的模型。新增真实三分量对比表明，"
        "模型主脉冲与观测初始起振都位于约80–100 s，但观测峰值能量时间为659.12 s，四模型"
        "仅为85.73–96.53 s，且观测前250 s只包含约3.98%的总记录能量。因此，真实数据支持"
        "地形和随机非均匀结构会改造早期波形，却不支持“当前模型已经验证完整月震包络形成"
        "机制”的强结论。我们据此修改讨论，将地形作用、随机散射作用和仍未解释的千秒级长"
        "尾波明确区分。"
    ),
    "您提出的引入波形相似性度量指标来确定空间分辨率的方法非常好": (
        "您提出的引入波形相似性度量指标来确定空间分辨率的方法非常好。我们在Figure R3和"
        "Figure R4中以最高分辨率结果为参考，对0.3–0.9 Hz滤波波形计算滑动时窗最大相关系数，"
        "并分别比较路径A、B和C。随着地形网格变粗，小尺度起伏被逐渐平滑，波形相关系数趋近1；"
        "路径C因地形较平缓，在相同分辨率下的相关系数高于路径A和B。综合新增的0.25和0.5 km"
        "结果，我们把0.5 km/pixel作为当前三条路径上仍能稳定辨认地形波形效应的临界网格尺度，"
        "并在修改稿中补充了参考波形、滑动窗定义和临界值判据。"
    ),
    "您的疑问充分说明了我们原稿件的图和说明不够清晰直观": (
        "您的疑问充分说明了我们原稿件的图和说明不够清晰直观。在修改稿中，我们不再使用各条"
        "波形独立归一化后的系数来说明地面运动变化，而是在Figure R5中对全部台站和三个分量"
        "使用同一个全局归一化系数，从而保留径向、横向和垂向之间以及不同传播距离之间的相对"
        "振幅。图中可直接看到三分量地面运动随传播距离总体减弱，且横向分量峰值总体小于径向"
        "和垂向分量。"
    ),
    "FigureR5 Radial, transverse and vertical velocity seismograms": (
        "Figure R5. Radial, transverse, and vertical velocity seismograms band-pass filtered between "
        "0.1 and 2.0 Hz at 24 observation points selected along path A in Figure 1. Red and blue lines "
        "show results without and with topography, respectively. A single global normalization factor "
        "is applied to all stations and all three components, so relative amplitudes among distance, "
        "component, and model are preserved."
    ),
    "对于上升时间和传播距离之间关系的经验规律": (
        "对于上升时间与传播距离之间关系的经验规律，我们按照您的建议增加了定量比较。"
        "首先，对0.3–0.9 Hz三分量能量包络分别使用5、10、20、40、60和100 s平滑窗，"
        "以中位值及最小—最大范围表示上升时间的不确定性。其次，我们对三条路径、四个模型"
        "共12组峰值能量时间—震中距关系分别拟合线性形式a+bR和扩散形式a+cR²。12组结果"
        "均显著偏好线性形式：线性拟合RMSE为1.54–2.88 s，而R²形式为4.56–10.03 s，"
        "后者相对线性的ΔAIC为268–672。最后，我们加入A16S12真实三分量记录进行验证。"
        "观测能量峰值时间中位数为659.12 s（647.12–770.44 s），而四个模型仅为"
        "85.73–96.53 s；观测前250 s只包含约3.98%的总记录能量。结果表明，新的地形和"
        "随机散射模型能够改造早期波形并延长合成尾波，但仍不能重现真实月震的强扩散包络。"
        "因此我们接受您的核心判断，并在修改稿中收紧结论，不再声称地形散射可以单独解释"
        "月球观测包络的形成。"
    ),
    "回答：等新的结果出来再回答。": (
        "回答：非常感谢您的建议。我们不再使用单一平滑窗估算上升时间，而是对0.3–0.9 Hz"
        "三分量能量包络分别采用5、10、20、40、60和100 s六种平滑窗，并报告峰值能量时间"
        "的中位数及最小—最大范围。A16S12观测的峰值时间为659.12 s，平滑窗范围为"
        "647.12–770.44 s；M1–M4分别为85.73、92.40、96.53和93.67 s，各模型范围均位于"
        "73.45–114.70 s。由此可见，虽然100 s超长平滑窗会使观测峰值略向后移动，但观测与"
        "合成结果在全部平滑尺度下仍完全分离。我们已新增平滑窗敏感性图和相应统计表，并在"
        "正文中明确给出这一不确定性。"
    ),
    "回答：等新的结果出来，再分析回答。": (
        "回答：非常感谢您指出这一关键问题。我们按照您的建议，将三条路径、四个模型共12组"
        "峰值能量时间—震中距关系分别拟合为线性形式a+bR和扩散形式a+cR²。所有12组均明显"
        "偏好线性形式，线性RMSE为1.54–2.88 s，R²形式为4.56–10.03 s，R²形式相对线性的"
        "ΔAIC为268–672。这说明当前合成波场仍以弹道传播为主，地形和随机散射虽然造成"
        "多路径与尾波展宽，却尚未达到扩散模型描述的强散射状态。与A16S12真实三分量记录"
        "的比较进一步支持这一判断：约152 km震中距处，观测峰值能量时间为659.12 s，"
        "四模型仅为85.73–96.53 s；观测50%和95%能量时刻分别为986.88 s和2805.08 s。"
        "因此，我们同意当前结果不能证明地形散射能够解释月球观测包络。修改稿将结论限定为"
        "地形对早期波形和有限时长尾波的改造作用，并明确指出250 s合成记录不足以验证"
        "千秒级月震尾波，后续模拟需延长至至少3000 s并系统检验散射层强度、厚度、相关尺度"
        "和随机实现。"
    ),
}


def qn(local_name: str) -> str:
    return f"{{{W_NS}}}{local_name}"


def accepted_paragraph_text(paragraph: etree._Element) -> str:
    pieces: list[str] = []
    for text_node in paragraph.findall(".//w:t", namespaces=NS):
        if any(ancestor.tag == qn("del") for ancestor in text_node.iterancestors()):
            continue
        pieces.append(text_node.text or "")
    return "".join(pieces)


def next_revision_id(root: etree._Element) -> int:
    identifiers = []
    for element in root.iter():
        value = element.get(qn("id"))
        if value is None:
            continue
        try:
            identifiers.append(int(value))
        except ValueError:
            continue
    return max(identifiers, default=0) + 1


def revision_run(
    text: str, run_properties: etree._Element | None, deleted: bool
) -> etree._Element:
    run = etree.Element(qn("r"))
    if run_properties is not None:
        run.append(copy.deepcopy(run_properties))
    text_element = etree.SubElement(run, qn("delText" if deleted else "t"))
    if text[:1].isspace() or text[-1:].isspace() or "  " in text:
        text_element.set(f"{{{XML_NS}}}space", "preserve")
    text_element.text = text
    return run


def tracked_replace_paragraph(
    paragraph: etree._Element,
    old_text: str,
    new_text: str,
    revision_id: int,
) -> int:
    first_run_properties = paragraph.find(".//w:r/w:rPr", namespaces=NS)
    paragraph_properties = paragraph.find("w:pPr", namespaces=NS)
    for child in list(paragraph):
        if child is not paragraph_properties:
            paragraph.remove(child)

    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    deletion = etree.SubElement(paragraph, qn("del"))
    deletion.set(qn("id"), str(revision_id))
    deletion.set(qn("author"), "")
    deletion.set(qn("date"), timestamp)
    deletion.append(revision_run(old_text, first_run_properties, deleted=True))

    insertion = etree.SubElement(paragraph, qn("ins"))
    insertion.set(qn("id"), str(revision_id + 1))
    insertion.set(qn("author"), "")
    insertion.set(qn("date"), timestamp)
    insertion.append(revision_run(new_text, first_run_properties, deleted=False))
    return revision_id + 2


def update_document_xml(document_xml: bytes) -> bytes:
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(document_xml, parser)
    revision_id = next_revision_id(root)
    matched = {key: False for key in REPLACEMENTS}
    for paragraph in root.findall(".//w:body//w:p", namespaces=NS):
        paragraph_text = accepted_paragraph_text(paragraph)
        for old_snippet, new_text in REPLACEMENTS.items():
            if old_snippet not in paragraph_text:
                continue
            revision_id = tracked_replace_paragraph(
                paragraph, paragraph_text, new_text, revision_id
            )
            matched[old_snippet] = True
            break
    missing = [snippet for snippet, found in matched.items() if not found]
    if missing:
        raise RuntimeError(f"Reviewer-response paragraphs not found: {missing}")
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def main() -> None:
    if not SOURCE_DOCX.is_file():
        raise FileNotFoundError(SOURCE_DOCX)
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE_DOCX, "r") as source_archive:
        document_xml = update_document_xml(source_archive.read("word/document.xml"))
        with zipfile.ZipFile(
            OUTPUT_DOCX, "w", compression=zipfile.ZIP_DEFLATED
        ) as output_archive:
            for entry in source_archive.infolist():
                content = (
                    document_xml
                    if entry.filename == "word/document.xml"
                    else source_archive.read(entry.filename)
                )
                output_archive.writestr(entry, content)
    print(f"Updated reviewer response: {OUTPUT_DOCX}")


if __name__ == "__main__":
    main()
