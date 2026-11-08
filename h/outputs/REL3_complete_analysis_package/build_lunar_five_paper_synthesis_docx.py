from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = next(parent for parent in Path(__file__).resolve().parents if parent.name == "h")
OUTPUT_DIR = ROOT / "outputs"
ASSET_DIR = ROOT / "tmp" / "lunar_synthesis_docx_assets"
RENDERED_PAPERS = ROOT / "tmp" / "pdfs" / "lunar_papers" / "rendered"
OUTPUT_DOCX = OUTPUT_DIR / "月震散射与低速层_五篇论文综合精读.docx"

BLUE = "2E74B5"
DEEP_BLUE = "1F4D78"
NAVY = "203748"
MUTED = "5C6770"
LIGHT_BLUE = "E8EEF5"
PALE_BLUE = "F5F8FB"
PALE_GOLD = "FFF7E6"
GOLD = "C58B22"
WHITE = "FFFFFF"
BLACK = "1F1F1F"
GRID = "AEB8C2"
FONT = "Microsoft YaHei"
MONO = "Consolas"
CONTENT_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120


def set_cell_shading(cell, fill):
    cell_properties = cell._tc.get_or_add_tcPr()
    shading = cell_properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        cell_properties.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, bottom=80, start=120, end=120):
    cell_properties = cell._tc.get_or_add_tcPr()
    cell_margins = cell_properties.first_child_found_in("w:tcMar")
    if cell_margins is None:
        cell_margins = OxmlElement("w:tcMar")
        cell_properties.append(cell_margins)
    for edge, value in (("top", top), ("bottom", bottom), ("start", start), ("end", end)):
        node = cell_margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            cell_margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    table_properties = table._tbl.tblPr
    table_width = table_properties.first_child_found_in("w:tblW")
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        table_properties.append(table_width)
    table_width.set(qn("w:w"), str(sum(widths_dxa)))
    table_width.set(qn("w:type"), "dxa")
    table_indent = table_properties.first_child_found_in("w:tblInd")
    if table_indent is None:
        table_indent = OxmlElement("w:tblInd")
        table_properties.append(table_indent)
    table_indent.set(qn("w:w"), str(TABLE_INDENT_DXA))
    table_indent.set(qn("w:type"), "dxa")
    layout = table_properties.first_child_found_in("w:tblLayout")
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        table_properties.append(layout)
    layout.set(qn("w:type"), "fixed")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        grid_column = OxmlElement("w:gridCol")
        grid_column.set(qn("w:w"), str(width))
        grid.append(grid_column)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.width = Inches(widths_dxa[index] / 1440)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell_properties = cell._tc.get_or_add_tcPr()
            cell_width = cell_properties.first_child_found_in("w:tcW")
            if cell_width is None:
                cell_width = OxmlElement("w:tcW")
                cell_properties.append(cell_width)
            cell_width.set(qn("w:w"), str(widths_dxa[index]))
            cell_width.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def repeat_table_header(row):
    row_properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    row_properties.append(repeat)


def prevent_row_split(row):
    row_properties = row._tr.get_or_add_trPr()
    cannot_split = OxmlElement("w:cantSplit")
    row_properties.append(cannot_split)


def set_repeat_heading(paragraph, keep_with_next=True):
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.keep_together = True


def set_run_font(run, name=FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def set_paragraph_border(paragraph, side="left", color=BLUE, size=14, space=8):
    paragraph_properties = paragraph._p.get_or_add_pPr()
    borders = paragraph_properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        paragraph_properties.append(borders)
    edge = OxmlElement(f"w:{side}")
    edge.set(qn("w:val"), "single")
    edge.set(qn("w:sz"), str(size))
    edge.set(qn("w:space"), str(space))
    edge.set(qn("w:color"), color)
    borders.append(edge)


def set_paragraph_shading(paragraph, fill):
    paragraph_properties = paragraph._p.get_or_add_pPr()
    shading = paragraph_properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        paragraph_properties.append(shading)
    shading.set(qn("w:fill"), fill)


def add_field(run, instruction):
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    field_code = OxmlElement("w:instrText")
    field_code.set(qn("xml:space"), "preserve")
    field_code.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(field_code)
    run._r.append(separate)
    run._r.append(end)


def configure_styles(document):
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    heading_tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DEEP_BLUE, 10, 5),
    }
    for style_name, (size, color, before, after) in heading_tokens.items():
        style = styles[style_name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True
    for style_name in ("List Bullet", "List Number"):
        style = styles[style_name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25
    if "Caption Custom" not in [style.name for style in styles]:
        caption = styles.add_style("Caption Custom", WD_STYLE_TYPE.PARAGRAPH)
    else:
        caption = styles["Caption Custom"]
    caption.font.name = FONT
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    caption.font.size = Pt(9)
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.line_spacing = 1.15
    caption.paragraph_format.keep_together = True
    if "Source Note" not in [style.name for style in styles]:
        source = styles.add_style("Source Note", WD_STYLE_TYPE.PARAGRAPH)
    else:
        source = styles["Source Note"]
    source.font.name = FONT
    source._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    source.font.size = Pt(8)
    source.font.italic = True
    source.font.color.rgb = RGBColor.from_string(MUTED)
    source.paragraph_format.space_before = Pt(2)
    source.paragraph_format.space_after = Pt(6)
    source.paragraph_format.line_spacing = 1.1
    if "Table Text" not in [style.name for style in styles]:
        table_text = styles.add_style("Table Text", WD_STYLE_TYPE.PARAGRAPH)
    else:
        table_text = styles["Table Text"]
    table_text.font.name = FONT
    table_text._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    table_text.font.size = Pt(9)
    table_text.paragraph_format.space_before = Pt(0)
    table_text.paragraph_format.space_after = Pt(0)
    table_text.paragraph_format.line_spacing = 1.15


def configure_section(section):
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.4)
    section.footer_distance = Inches(0.4)
    section.different_first_page_header_footer = True


def configure_header_footer(section):
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run("月震散射、低速层与长尾波｜五篇论文综合精读")
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


def set_document_language(document):
    styles = document.styles
    for style_name in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        style = styles[style_name]
        run_properties = style.element.get_or_add_rPr()
        language = run_properties.find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            run_properties.append(language)
        language.set(qn("w:val"), "zh-CN")
        language.set(qn("w:eastAsia"), "zh-CN")


def add_paragraph(document, text="", style=None, align=None, after=None, before=None, keep=False):
    paragraph = document.add_paragraph(style=style)
    if text:
        run = paragraph.add_run(text)
        set_run_font(run)
    if align is not None:
        paragraph.alignment = align
    if after is not None:
        paragraph.paragraph_format.space_after = Pt(after)
    if before is not None:
        paragraph.paragraph_format.space_before = Pt(before)
    if keep:
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.keep_together = True
    return paragraph


def add_rich_paragraph(document, pieces, style=None, align=None, after=None, before=None, keep=False):
    paragraph = document.add_paragraph(style=style)
    for piece in pieces:
        if isinstance(piece, str):
            text = piece
            options = {}
        else:
            text = piece[0]
            options = piece[1]
        run = paragraph.add_run(text)
        set_run_font(
            run,
            name=options.get("font", FONT),
            size=options.get("size"),
            bold=options.get("bold"),
            italic=options.get("italic"),
            color=options.get("color"),
        )
    if align is not None:
        paragraph.alignment = align
    if after is not None:
        paragraph.paragraph_format.space_after = Pt(after)
    if before is not None:
        paragraph.paragraph_format.space_before = Pt(before)
    if keep:
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.keep_together = True
    return paragraph


def add_heading(document, text, level=1):
    paragraph = document.add_heading(text, level=level)
    set_repeat_heading(paragraph)
    for run in paragraph.runs:
        set_run_font(run)
    return paragraph


def add_bullet(document, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    paragraph = document.add_paragraph(style=style)
    run = paragraph.add_run(text)
    set_run_font(run)
    return paragraph


def add_numbered(document, text):
    paragraph = document.add_paragraph(style="List Number")
    run = paragraph.add_run(text)
    set_run_font(run)
    return paragraph


def add_callout(document, label, text, fill=PALE_BLUE, border=BLUE):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.18)
    paragraph.paragraph_format.right_indent = Inches(0.12)
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.2
    paragraph.paragraph_format.keep_together = True
    set_paragraph_shading(paragraph, fill)
    set_paragraph_border(paragraph, side="left", color=border, size=16, space=8)
    label_run = paragraph.add_run(label + "　")
    set_run_font(label_run, bold=True, color=border)
    text_run = paragraph.add_run(text)
    set_run_font(text_run)
    return paragraph


def add_equation(document, equation, explanation):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.keep_together = True
    equation_run = paragraph.add_run(equation)
    set_run_font(equation_run, name="Cambria Math", size=12, bold=True, color=DEEP_BLUE)
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(7)
    note_run = note.add_run(explanation)
    set_run_font(note_run, size=9, italic=True, color=MUTED)


def add_table(document, headers, rows, widths_dxa, font_size=9):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    header_row = table.rows[0]
    repeat_table_header(header_row)
    prevent_row_split(header_row)
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        set_cell_shading(cell, LIGHT_BLUE)
        paragraph = cell.paragraphs[0]
        paragraph.style = document.styles["Table Text"]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(str(header))
        set_run_font(run, size=font_size, bold=True, color=NAVY)
    for row_values in rows:
        row = table.add_row()
        prevent_row_split(row)
        for index, value in enumerate(row_values):
            cell = row.cells[index]
            paragraph = cell.paragraphs[0]
            paragraph.style = document.styles["Table Text"]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if index == 0 and len(headers) > 2 else WD_ALIGN_PARAGRAPH.LEFT
            run = paragraph.add_run(str(value))
            set_run_font(run, size=font_size)
    set_table_geometry(table, widths_dxa)
    following = document.add_paragraph()
    following.paragraph_format.space_after = Pt(1)
    return table


def add_figure(document, path, caption, source=None, width=6.25, alt_text=None):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    inline_shape = run.add_picture(str(path), width=Inches(width))
    doc_properties = inline_shape._inline.docPr
    if alt_text:
        doc_properties.set("descr", alt_text)
    caption_paragraph = document.add_paragraph(style="Caption Custom")
    caption_run = caption_paragraph.add_run(caption)
    set_run_font(caption_run, size=9, color=MUTED)
    if source:
        source_paragraph = document.add_paragraph(style="Source Note")
        source_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        source_run = source_paragraph.add_run(source)
        set_run_font(source_run, size=8, italic=True, color=MUTED)
    return paragraph


def crop_image(source_name, target_name, box):
    source = RENDERED_PAPERS / source_name
    target = ASSET_DIR / target_name
    with Image.open(source) as image:
        cropped = image.crop(box)
        cropped.save(target, quality=95)
    return target


def load_font(size, bold=False):
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def pil_color(value):
    return f"#{value}"


def draw_wrapped_text(draw, xy, text, font, fill, max_width, spacing=8, anchor="la"):
    words = []
    current = ""
    for character in text:
        candidate = current + character
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            words.append(current)
            current = character
    if current:
        words.append(current)
    draw.multiline_text(xy, "\n".join(words), font=font, fill=fill, spacing=spacing, anchor=anchor, align="center")


def create_research_chain_graphic():
    target = ASSET_DIR / "research_chain.png"
    canvas = Image.new("RGB", (1800, 800), pil_color(WHITE))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(46, bold=True)
    year_font = load_font(28, bold=True)
    body_font = load_font(26)
    small_font = load_font(23)
    draw.text((900, 55), "五篇论文构成的一条完整证据链", font=title_font, fill=pil_color(NAVY), anchor="ma")
    boxes = [
        (80, 180, 385, 520, "2012 JGR", "观测归纳", "72 个事件\n369 条记录\n提出近表面全球散射层"),
        (430, 180, 735, 520, "2015 JGR", "机制试验", "速度结构、散射层、Qi\n分别改变\n低速结构最敏感"),
        (780, 180, 1085, 520, "2015 GRL", "横向变化", "盆内外厚度变化\n盆缘能量泄漏\n影响距离约 1–1.5 倍层厚"),
        (1130, 180, 1435, 520, "2016 PSS", "竞争解释", "无随机散射、无吸收时\n薄低速层共振\n也可产生长振铃"),
        (1480, 180, 1785, 520, "2017 PEPI", "定量反演", "446 条记录\ntmax 约束散射\nQc 约束吸收"),
    ]
    fills = ["E8F1F8", "EAF4F0", "F1F4E8", "FFF4E5", "EFEAF7"]
    borders = [BLUE, "2F7D6D", "6E7D32", GOLD, "6A4C93"]
    for index, (left, top, right, bottom, year, role, body) in enumerate(boxes):
        draw.rounded_rectangle((left, top, right, bottom), radius=24, fill=pil_color(fills[index]), outline=pil_color(borders[index]), width=5)
        draw.text(((left + right) / 2, top + 50), year, font=year_font, fill=pil_color(borders[index]), anchor="ma")
        draw.text(((left + right) / 2, top + 110), role, font=body_font, fill=pil_color(NAVY), anchor="ma")
        draw.multiline_text(((left + right) / 2, top + 185), body, font=small_font, fill=pil_color(BLACK), spacing=15, anchor="ma", align="center")
        if index < len(boxes) - 1:
            arrow_y = (top + bottom) / 2
            draw.line((right + 8, arrow_y, boxes[index + 1][0] - 12, arrow_y), fill=pil_color(MUTED), width=8)
            draw.polygon(((boxes[index + 1][0] - 12, arrow_y), (boxes[index + 1][0] - 32, arrow_y - 16), (boxes[index + 1][0] - 32, arrow_y + 16)), fill=pil_color(MUTED))
    draw.rounded_rectangle((190, 595, 1610, 755), radius=28, fill="#F6F8FA", outline="#CBD4DC", width=3)
    draw.text((900, 638), "综合结论：低速层负责俘获与共振，随机非均匀体负责展宽与模态混合，高 Qi 负责让能量长期保存。", font=body_font, fill=pil_color(NAVY), anchor="ma")
    draw.text((900, 700), "三者可以同时成立，不能只靠单一波形指标二选一。", font=year_font, fill=pil_color(DEEP_BLUE), anchor="ma")
    canvas.save(target, quality=95)
    return target


def create_mechanism_graphic():
    target = ASSET_DIR / "mechanism_synthesis.png"
    canvas = Image.new("RGB", (1700, 950), pil_color(WHITE))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(44, bold=True)
    label_font = load_font(28, bold=True)
    body_font = load_font(24)
    small_font = load_font(21)
    draw.text((850, 55), "月震长尾波的联合物理图景", font=title_font, fill=pil_color(NAVY), anchor="ma")
    draw.rectangle((90, 155, 1610, 350), fill="#F5E7CC", outline=pil_color(GOLD), width=4)
    draw.rectangle((90, 350, 1610, 650), fill=pil_color(LIGHT_BLUE), outline=pil_color(BLUE), width=4)
    draw.rectangle((90, 650, 1610, 850), fill="#EEF2F5", outline=pil_color(MUTED), width=4)
    draw.text((155, 205), "近表面低速层 / 月壤", font=label_font, fill="#8A5C00")
    draw.text((155, 275), "低速度与强速度梯度 → 波导、聚焦、反射与共振", font=body_font, fill=pil_color(BLACK))
    draw.text((155, 405), "巨厚风化层 / 强裂隙带", font=label_font, fill=pil_color(DEEP_BLUE))
    draw.text((155, 475), "多尺度随机界面 → 多次散射、P–SV–SH 转换、包络展宽", font=body_font, fill=pil_color(BLACK))
    draw.text((155, 560), "散射层厚度、阻抗扰动和横向盆地结构共同控制有效传播路径", font=small_font, fill=pil_color(MUTED))
    draw.text((155, 705), "较深内部 / 弱散射高 Qi 介质", font=label_font, fill=pil_color(NAVY))
    draw.text((155, 775), "低内禀吸收 → 能量泄漏后仍能绕月传播并重新进入近表面", font=body_font, fill=pil_color(BLACK))
    path_points = [(1280, 760), (1450, 615), (1230, 470), (1470, 300), (1260, 220)]
    draw.line(path_points, fill="#C74343", width=12, joint="curve")
    for point in path_points:
        draw.ellipse((point[0] - 14, point[1] - 14, point[0] + 14, point[1] + 14), fill="#C74343")
    draw.text((1200, 865), "红线：能量多次进入散射层，路径被显著延长", font=small_font, fill="#9D2E2E")
    canvas.save(target, quality=95)
    return target


def prepare_assets():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    assets = {
        "jgr2012_fig3": crop_image("jgr2012_methods-06.png", "jgr2012_fig3.png", (125, 55, 735, 690)),
        "jgr2015_fig11": crop_image("jgr2015_results-14.png", "jgr2015_fig11.png", (40, 95, 735, 625)),
        "grl2015_fig3": crop_image("grl2015-4.png", "grl2015_fig3.png", (45, 50, 810, 685)),
        "burmin_fig7": crop_image("burmin2016-5.png", "burmin_fig7.png", (35, 55, 405, 445)),
        "burmin_fig8": crop_image("burmin2016-5.png", "burmin_fig8.png", (35, 480, 405, 1070)),
        "pepi_fig4": crop_image("pepi2017_qc-06.png", "pepi_fig4.png", (35, 625, 800, 1085)),
        "pepi_fig7": crop_image("pepi2017_inversion-09.png", "pepi_fig7.png", (35, 50, 800, 535)),
        "research_chain": create_research_chain_graphic(),
        "mechanism": create_mechanism_graphic(),
        "observed_models": OUTPUT_DIR / "releasy_waveform_figures_python" / "figure7_A16S12_observed_vs_four_models.png",
        "low_velocity_diagnostic": OUTPUT_DIR / "three_component_psvsh_analysis" / "figure_06_low_velocity_layer_diagnostic.png",
    }
    return assets


def add_cover(document):
    add_paragraph(document, "", after=86)
    kicker = add_paragraph(document, "五篇核心论文 · 中文综合精读", align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
    set_run_font(kicker.runs[0], size=11, bold=True, color=GOLD)
    title = add_paragraph(document, "月震散射、低速层与长尾波", align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    set_run_font(title.runs[0], size=30, bold=True, color=NAVY)
    subtitle = add_paragraph(document, "从 Apollo 观测到扩散反演，再到三维数值模拟", align=WD_ALIGN_PARAGRAPH.CENTER, after=9)
    set_run_font(subtitle.runs[0], size=16, color=DEEP_BLUE)
    descriptor = add_paragraph(document, "一份可独立阅读、用于替代逐篇翻阅的研究指南", align=WD_ALIGN_PARAGRAPH.CENTER, after=58)
    set_run_font(descriptor.runs[0], size=10.5, italic=True, color=GOLD)
    add_callout(
        document,
        "核心判断",
        "Apollo 长尾波最合理的解释不是“散射”与“低速层”二选一，而是低速俘获/共振、强多重散射与极低内禀吸收共同作用。横向盆地和台站附近结构进一步造成路径差异。",
        fill="F6F8FA",
        border=DEEP_BLUE,
    )
    add_paragraph(document, "", after=44)
    date_paragraph = add_paragraph(document, "2026 年 8 月 7 日", align=WD_ALIGN_PARAGRAPH.CENTER, after=5)
    set_run_font(date_paragraph.runs[0], size=12, bold=True, color=NAVY)
    scope = add_paragraph(document, "适用于 Apollo 月震观测解读与 CGFD3D 三维波形模拟", align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
    set_run_font(scope.runs[0], size=9.5, italic=True, color=MUTED)
    document.add_page_break()


def add_front_matter(document, assets):
    add_heading(document, "如何使用本文件", 1)
    add_paragraph(
        document,
        "本文件不是五篇论文的逐句拼接，而是按照“问题—证据—方法—结论—限制—模拟应用”重新组织的独立阅读版。正文保留论文中的关键样本量、频带、定义、参数、图像与不确定性；需要正式引用时，仍应回到文末列出的原论文。",
    )
    add_callout(document, "最快阅读路径", "先读本节后的十二条总判断，再看第 1 章的证据链和第 8 章的争议综合；最后按第 9 章把结论应用到你的四模型与 A16S12 实测对比。")
    add_heading(document, "十二条先行结论", 2)
    conclusions = [
        "Apollo 月震长尾波在多类震源和多个台站上都存在，近表面全球性强散射背景是最稳健的观测事实之一。",
        "低速层或陡峭速度梯度能够把能量俘获在近表面，使其反复进入散射层；它不是散射的替代项，而是散射效率的放大器。",
        "高 Qi 不是尾波形状的主要制造者，却决定被俘获和散射的能量能保存多久。",
        "tmax 是平滑能量包络的峰值到时，主要反映散射展宽；它既不是初至，也不应直接等同于“上升时间”。",
        "晚期 Qc 在充分扩散后可侧重反映吸收，但在早期、短距离或低速波导显著时仍会混入散射和几何效应。",
        "2015 JGR 的参数化模拟显示，速度结构对尾波持续时间的影响可达到至少约 4 倍，通常强于散射层厚度或单一界面扰动。",
        "散射层厚度与阻抗扰动存在强权衡：厚而弱的散射层可能与薄而强的散射层产生相近尾波。",
        "盆缘外部散射能量会泄漏进盆内；台站要看到明显低散射记录，距盆缘通常需达到外围散射层厚度的约 1–1.5 倍。",
        "Burmin 的层状无吸收模型证明薄低速层本身可以产生小时级振铃，但不能解释散射尾波的全部统计特征与台站差异。",
        "2017 PEPI 的反演指向表层 D≈2.43 km²/s、Qi≈2396，并在约 80–100 km 深度出现散射显著减弱。",
        "约 100 km 是有效强裂隙/散射带的模型深度，不应被解释为分辨率无限高的尖锐地质界面。",
        "对你的四模型，最有价值的补充不是事后平移波形，而是给四组同时加入同一低速层，并在同一频带、时窗和三分量标度下比较波形与包络。",
    ]
    for conclusion in conclusions:
        add_numbered(document, conclusion)
    add_figure(document, assets["research_chain"], "图 1　五篇论文的证据链与最终联合解释。", width=6.3, alt_text="五篇月震论文的研究证据链")
    add_heading(document, "阅读导航", 2)
    navigation_rows = [
        ("第 1–2 章", "建立研究链、术语和可比较指标"),
        ("第 3–7 章", "逐篇理解观测、数值试验、横向变化、共振与扩散反演"),
        ("第 8 章", "比较一致结论、关键分歧与可同时成立的机制"),
        ("第 9 章", "把论文结论转化为你现有模型的可执行方案"),
        ("附录", "查关键数值、术语和正式文献来源"),
    ]
    add_table(document, ["位置", "用途"], navigation_rows, [1800, 7560], font_size=9.5)
    document.add_page_break()


def add_chapter_one(document, assets):
    add_heading(document, "1　五篇论文如何共同回答一个问题", 1)
    add_paragraph(
        document,
        "这组文献围绕同一核心问题逐步推进：月球地震记录为什么具有弱直达波、渐进式起始、强烈包络展宽和持续数十分钟的尾波？研究路径从观测统计开始，经过参数化传播模拟与横向盆地试验，再以层状共振模型提出竞争解释，最后回到观测进行散射—吸收反演。",
    )
    comparison_rows = [
        ("2012 JGR", "Apollo 12/14/15/16", "td、Qc、频率与距离关系", "全球近表面散射背景", "不能唯一分离 Qi 与 Qs"),
        ("2015 JGR", "PHONON1D 声子模拟", "速度、TSL、扰动、Qi", "速度结构与低速俘获极敏感", "一维背景、统计能量法"),
        ("2015 GRL", "盆地内外横向结构", "SNR 与盆缘距离", "泄漏影响约 1–1.5×TSL", "忽略真实三维地形等"),
        ("2016 PSS", "层状解析波场", "有/无薄低速层振铃", "共振可单独产生长持续", "无吸收、无随机散射"),
        ("2017 PEPI", "446 条 Apollo 记录", "tmax、Qc、球形扩散", "D(z)、Qsc(z)、Qi 与浅震深度", "不能描述相干震相"),
    ]
    add_table(
        document,
        ["论文", "证据/模型", "核心可观测量", "最强结论", "主要限制"],
        comparison_rows,
        [1200, 1850, 1800, 2450, 2060],
        font_size=8.3,
    )
    add_heading(document, "1.1　四种共同控制机制", 2)
    add_figure(document, assets["mechanism"], "图 2　低速俘获、强散射、高 Qi 与球形回返共同塑造长尾波。", width=6.3, alt_text="月震长尾波联合物理图景")
    mechanism_rows = [
        ("低速层/速度梯度", "减慢传播、增强反射、形成波导或共振", "初至延迟、持续时间增加、频散与窄带振铃"),
        ("随机散射", "延长路径并随机化方向，产生模式转换", "渐进起振、包络展宽、P/S/SH 混合"),
        ("高 Qi", "减小沿路径的非弹性耗散", "晚期能量保存，衰减斜率变缓"),
        ("球形与横向结构", "能量可离开表层后再次返回，且盆缘/地形改变路径", "距离依赖、台站差异、路径不对称"),
    ]
    add_table(document, ["机制", "主要作用", "波形表现"], mechanism_rows, [2000, 3150, 4210], font_size=8.8)
    add_callout(document, "不要做的二选一", "“低速层能产生振铃”并不否定散射；“散射能产生长尾波”也不意味着低速层可以忽略。真正需要比较的是每种机制对初至、包络峰值、早期尾波、晚期衰减和三分量混合分别贡献多少。", fill=PALE_GOLD, border=GOLD)
    document.add_page_break()


def add_chapter_two(document):
    add_heading(document, "2　读图前必须统一的术语与测量", 1)
    add_heading(document, "2.1　三个时间量不能混用", 2)
    timing_rows = [
        ("初至 t0", "波形或包络首次超过噪声阈值", "速度结构、路径长度", "判断传播时间"),
        ("包络峰值 tmax", "平滑能量包络达到最大值的时刻", "散射展宽最敏感，也受吸收影响", "扩散反演、模型展宽比较"),
        ("衰减时间 td", "包络从拟合起点指数下降 1/e 的时间", "吸收、散射、速度俘获和几何", "晚期尾波衰减"),
        ("上升历时", "从 t0 到 tmax，或从某百分位到峰值", "散射和震源时函数", "描述能量积累过程"),
    ]
    add_table(document, ["量", "定义", "主要敏感项", "推荐用途"], timing_rows, [1600, 2750, 2800, 2210], font_size=8.8)
    add_callout(document, "术语修正", "你之前所称“能量到达最高的时间”应写为 tmax 或“包络峰值到时”；若要使用“上升时间”，必须明确它是 tmax−t0 还是 10%–90% 的能量上升历时。")
    add_heading(document, "2.2　包络、平滑和 Q 参数", 2)
    add_equation(document, "E(t) = |x(t) + i·H{x(t)}|", "Hilbert 解析信号的振幅包络；能量包络常取 E²(t)。")
    add_equation(document, "Qc ≈ π · fc · td", "2012 JGR 使用的近似关系；Qc 是有效尾波品质因子，不等同于纯内禀 Qi。")
    add_equation(document, "D = c² · Qsc / (3ω)", "2017 PEPI 中扩散率 D 与散射品质因子 Qsc 的关系。")
    add_paragraph(
        document,
        "包络平滑窗口必须以周期数而不是任意秒数来理解。2017 PEPI 在 0.25–0.75 Hz 频带使用约 20 s 平滑，相当于中心频率 0.5 Hz 的约 10 个周期。过短窗口会保留随机涨落，过长窗口会系统性推迟 tmax。",
    )
    add_heading(document, "2.3　推荐的统一处理链", 2)
    workflow = [
        "去均值、去趋势，并检查仪器响应与饱和。",
        "使用零相位带通滤波；主频带保留 0.3–0.9 Hz，同时增算文献标准的 0.25–0.75 Hz 与 0.75–1.25 Hz。",
        "分别保留原始波形、振幅包络和能量包络，不用单一曲线替代全部证据。",
        "由噪声窗定义阈值和 t0；用 10/20/40 s 平滑敏感性给出 tmax 不确定范围。",
        "在峰值之后、信号降到约 2×噪声 RMS 之前拟合 td 与 Qc。",
        "三分量只使用一个共同振幅尺度，避免每个分量独立归一化掩盖偏振差异。",
    ]
    for item in workflow:
        add_numbered(document, item)
    add_callout(document, "最重要的验证", "同一个结论至少应同时在波形、包络和一个定量指标上成立；若只有平滑后的单点峰值变化，而代表性台站波形看不出差异，结论应降级为探索性。", fill=PALE_GOLD, border=GOLD)
    document.add_page_break()


def add_paper_2012(document, assets):
    add_heading(document, "3　2012 JGR：从 Apollo 记录建立观测事实", 1)
    add_rich_paragraph(document, [
        ("论文：", {"bold": True, "color": DEEP_BLUE}),
        ("Investigation of scattering in lunar seismic coda", {"italic": True}),
        ("　DOI: 10.1029/2011JE004042", {"font": MONO, "size": 9.5, "color": MUTED}),
    ])
    add_heading(document, "3.1　数据规模与处理", 2)
    add_paragraph(
        document,
        "作者从 Apollo 12、14、15、16 台站中筛选 72 个事件、369 条较高质量记录，事件类型包括人工撞击、天然撞击、浅月震和深月震。长周期通道分为 0.25–0.75、0.75–1.25、1.25–1.75 Hz，短周期垂向分量分为 2–4、4–6、6–8、8–10 Hz。最终保留 641 个衰减时间测量。",
    )
    add_figure(
        document,
        assets["jgr2012_fig3"],
        "图 3　2012 JGR 的处理示例：原始记录、多个频带和包络衰减拟合展示了 td 的测量方式。",
        "原图节选自 Blanchette-Guertin et al. (2012), Figure 3。",
        width=5.1,
        alt_text="2012 JGR 月震记录频带与包络处理示例",
    )
    add_heading(document, "3.2　最可靠的观测结果", 2)
    findings = [
        "所有事件类型和所有台站都存在长尾波，支持全球性近表面散射层，而非单一震源或单一台站异常。",
        "浅源事件在高于 2 Hz 时，td 与 Qc 常随震中距增加，符合能量沿近表面散射层传播越远、经历散射越多的解释。",
        "浅源事件的衰减参数随频率增加，说明小尺度散射体数量可能多于大尺度散射体。",
        "深月震的衰减参数基本不随震中距变化，可能因为深源能量主要在接收台附近进入并采样有限的近表面散射区。",
        "台站之间存在系统差异，全球散射背景上还叠加了近台站地质与局地结构。",
    ]
    for finding in findings:
        add_bullet(document, finding)
    add_heading(document, "3.3　这篇论文没有证明什么", 2)
    add_paragraph(
        document,
        "作者没有从 Qc 唯一反演 Qi 或 Qs，也没有证明所有长尾波只能由随机散射产生。Qc 同时受吸收、散射、几何扩散和低速层聚焦影响，指数拟合起点还需要人工选择。因而这篇论文提供的是强约束假说，而不是唯一介质模型。",
    )
    add_callout(document, "对你的数据", "S12 实测与四模型比较应同时展示波形和 10/20/40 s 平滑包络，并以噪声阈值确定有效尾波终点。仅将所有波形按峰值归一化，会丢失散射导致的能量分配差异。")
    document.add_page_break()


def add_paper_2015_jgr(document, assets):
    add_heading(document, "4　2015 JGR：用 PHONON1D 拆分控制因素", 1)
    add_rich_paragraph(document, [
        ("论文：", {"bold": True, "color": DEEP_BLUE}),
        ("Modeling seismic energy propagation in highly scattering environments", {"italic": True}),
        ("　DOI: 10.1002/2014JE004654", {"font": MONO, "size": 9.5, "color": MUTED}),
    ])
    add_heading(document, "4.1　方法的物理含义", 2)
    add_paragraph(
        document,
        "PHONON1D 在一维背景 Vp(z)、Vs(z)、密度、散射概率和 Qi 中追踪大量 P、SV、SH 能量包。随机取向界面允许反射、透射、离面传播和模式转换；散射体间距可服从幂律分布，以表示小尺度结构更多。该方法擅长能量统计传播，但并不完整保留确定性波动干涉。",
    )
    parameter_rows = [
        ("速度结构", "常速、含地壳、VLVL、VPREMOON、含核", "近表面俘获和速度梯度"),
        ("散射层厚度 TSL", "5、15、30、60 km", "能量经历散射的总体积"),
        ("界面扰动", "约 ±25%、±75%、±95%", "单次散射强度与模式转换"),
        ("Qi(1 Hz)", "约 2000、4500、6500", "路径上的内禀能量损失"),
        ("震源深度", "表面、30 km、1000 km", "能量进入散射层的方式"),
    ]
    add_table(document, ["因素", "测试范围", "主要作用"], parameter_rows, [2050, 2950, 4360], font_size=8.8)
    add_figure(
        document,
        assets["jgr2015_fig11"],
        "图 4　2015 JGR Figure 11：不同速度、散射层、界面扰动和 Qi 模型的波形总览。",
        "原图节选自 Blanchette-Guertin et al. (2015), Figure 11。",
        width=6.0,
        alt_text="PHONON1D 不同参数模型的合成波形比较",
    )
    add_heading(document, "4.2　参数敏感性的排序", 2)
    add_numbered(document, "背景速度结构：含壳幔边界、极浅低速层或陡峭梯度时，平均衰减时间相对常速模型可增加到至少约 4 倍。")
    add_numbered(document, "震源深度：浅源更直接耦合近表面散射层，因此对低速层和散射结构更敏感。")
    add_numbered(document, "Qi：增大 2–3 倍可产生相近量级的 td 增长，说明散射与吸收存在强非唯一性。")
    add_numbered(document, "散射层厚度与界面扰动：总体重要，但二者可以互相补偿，不能只凭持续时间唯一确定。")
    add_numbered(document, "散射尺度和深部弱散射：影响模式混合和尾波细节，但通常不是第一控制项。")
    add_heading(document, "4.3　两个衰减状态", 2)
    add_paragraph(
        document,
        "合成记录常出现可拟合的指数衰减阶段，以及随后极低振幅、噪声状的慢衰减阶段。后者并非真实噪声，而是极端多重散射后的能量统计状态。这提醒我们：在实测记录中，拟合窗口应终止于背景噪声之前；在无噪声合成中，则需人为统一动态范围。",
    )
    add_callout(document, "对你的四模型", "平坦/地形 × 无散射/散射只覆盖两个因素。加入低速层后，应让四组使用完全相同的低速层参数；否则地形、散射与低速层效应会混叠，无法归因。", fill=PALE_GOLD, border=GOLD)
    document.add_page_break()


def add_paper_2015_grl(document, assets):
    add_heading(document, "5　2015 GRL：横向变化和盆缘泄漏", 1)
    add_rich_paragraph(document, [
        ("论文：", {"bold": True, "color": DEEP_BLUE}),
        ("Effects of lateral variations in megaregolith thickness on predicted lunar seismic signals", {"italic": True}),
        ("　DOI: 10.1002/2015GL066151", {"font": MONO, "size": 9.5, "color": MUTED}),
    ])
    add_paragraph(
        document,
        "这篇论文把一维散射层推广到盆地内外厚度变化。盆外 TSL 从 5 km 到 60 km，盆内 TB 为 0 或 5 km，散射界面的速度和密度扰动平均约为背景值的 ±35%。目标不是给出唯一月球盆地模型，而是回答台站离盆缘多远才可能获得较干净的记录。",
    )
    add_figure(
        document,
        assets["grl2015_fig3"],
        "图 5　2015 GRL Figure 3：S 波信噪比随盆缘距离和散射层厚度变化。",
        "原图节选自 Blanchette-Guertin et al. (2015), Figure 3。",
        width=5.4,
        alt_text="盆地边缘距离和散射层厚度对S波信噪比的影响",
    )
    add_heading(document, "5.1　可以直接使用的几何结论", 2)
    add_bullet(document, "盆内若仍有约 5 km 的散射层，记录依然会表现出强散射，P、S 可能可拾取，但次级震相仍容易被尾波掩盖。")
    add_bullet(document, "盆外散射层越厚，盆缘泄漏影响越远；TSL=30 km 时约 15 km 内仍明显，TSL=60 km 时需要约 30 km 才显著减弱。")
    add_bullet(document, "达到低散射 SNR 所需的盆缘距离与 TSL 近似成正比，经验比值约为 1–1.5。")
    add_bullet(document, "散射不仅是接收台下方局地性质，还具有显著的震源侧和路径侧贡献。")
    add_heading(document, "5.2　为什么与你的地形模型直接相关", 2)
    add_paragraph(
        document,
        "真实地形、盆地边界和横向速度/密度变化会改变能量聚焦、散射层有效厚度与入射角。2015 GRL 本身没有显式建模真实地形，因此你的“平坦—地形”差分提供了这篇论文缺失的一部分物理；但如果不加入低速层和横向散射厚度变化，仍不能把地形效应等同于真实盆地效应。",
    )
    add_callout(document, "路径解释原则", "射线 1–3 的差异应优先以“路径积分效应”解释，而不是只用台站点位高程。推荐关联沿路径平均起伏、均方坡度、最大高差、盆缘穿越次数与包络展宽。")
    document.add_page_break()


def add_paper_2016(document, assets):
    add_heading(document, "6　2016 PSS：低速层共振的竞争性解释", 1)
    add_rich_paragraph(document, [
        ("论文：", {"bold": True, "color": DEEP_BLUE}),
        ("On the nature of the seismic ringing of the Moon. Analytical modeling", {"italic": True}),
        ("　DOI: 10.1016/j.pss.2016.03.013", {"font": MONO, "size": 9.5, "color": MUTED}),
    ])
    add_heading(document, "6.1　浅表速度结构", 2)
    velocity_rows = [
        ("0", "0.100", "0.040", "极低速表面"),
        ("0.010", "0.300", "0.130", "10 m 界面"),
        ("0.045", "0.500", "0.127", "45 m 界面"),
        ("0.200", "1.000", "0.205", "200 m 界面"),
        ("1.500", "4.000", "2.300", "过渡到底部高速结构"),
    ]
    add_table(document, ["深度 (km)", "Vp (km/s)", "Vs (km/s)", "解释"], velocity_rows, [1700, 1700, 1700, 4260], font_size=8.8)
    add_paragraph(
        document,
        "作者使用无随机散射、无内禀吸收的层状解析模型，以主频约 1 Hz 的地表垂直力模拟撞击。无浅表低速层时，记录约 1 min 内基本衰减；加入薄低速层后，多个距离均出现超过 1 h 的振铃。",
    )
    add_figure(
        document,
        assets["burmin_fig7"],
        "图 6　2016 PSS Figure 7：组合低速层模型产生的小时级垂向振铃。",
        "原图节选自 Burmin et al. (2016), Figure 7。",
        width=3.4,
        alt_text="低速层组合模型的小时级地震振铃",
    )
    add_heading(document, "6.2　这篇论文真正证明了什么", 2)
    add_callout(document, "证明的命题", "在理想层状、无吸收、无随机散射条件下，浅表薄低速层自身的波导和共振可以产生非常长的持续振动。因此，长持续时间不能被视为随机散射的唯一证据。")
    add_callout(document, "没有证明的命题", "它没有证明 Apollo 尾波完全不需要散射，也没有检验频率—距离统计、台站差异、随机包络和 P–SV–SH 能量混合。无吸收设定会极大延长振铃，米级极低速层也对数值网格提出苛刻要求。", fill=PALE_GOLD, border=GOLD)
    add_heading(document, "6.3　对三维模型的分辨率约束", 2)
    add_paragraph(
        document,
        "若直接使用 Vs=0.8 km/s、最高频率 0.9 Hz，则最短 S 波波长约 0.89 km。200 m 网格只有约 4.4 点/波长，通常不足以可靠描述强频散和表面波；建议把网格收细到约 90–110 m，或把比较频带上限降到能够满足求解器点/波长要求的位置。Burmin 表中的 10–200 m 细层更不适合被 200 m 网格粗略离散。",
    )
    add_paragraph(
        document,
        "你的 1 km 等效低速层（Vp=1.38 km/s、Vs=1.11 km/s）更适合作为当前 3D 网格可分辨的工程化候选，但它不等价于 Burmin 的米级层状模型；需要通过一组速度与厚度敏感性测试，而不是把一次拟合作为唯一结构。",
    )
    document.add_page_break()


def add_paper_2017(document, assets):
    add_heading(document, "7　2017 PEPI：用 tmax 与 Qc 反演散射—吸收剖面", 1)
    add_rich_paragraph(document, [
        ("论文：", {"bold": True, "color": DEEP_BLUE}),
        ("Scattering attenuation profile of the Moon", {"italic": True}),
        ("　DOI: 10.1016/j.pepi.2016.11.001", {"font": MONO, "size": 9.5, "color": MUTED}),
    ])
    add_paragraph(
        document,
        "质量筛选后，作者使用 62 个事件对应的 446 条记录。低频重点为 0.25–0.75 Hz，中心频率 0.5 Hz；包络采用约 20 s 平滑。tmax 主要约束散射造成的传播展宽，晚期 Qc 在充分扩散后主要约束体平均吸收。",
    )
    add_figure(
        document,
        assets["pepi_fig4"],
        "图 7　2017 PEPI Figure 4：不同事件类型的 tmax 与震中距关系，是扩散反演的主要观测基础。",
        "原图节选自 Gillet et al. (2017), Figure 4。",
        width=5.9,
        alt_text="不同月震事件的包络峰值到时随震中距变化",
    )
    add_heading(document, "7.1　球形扩散反演", 2)
    add_paragraph(
        document,
        "模型使用球对称、深度相关扩散方程，假设 D 随深度总体增大，以表示撞击裂隙和非均匀性逐渐闭合。遗传算法主要以撞击与深月震的 tmax 搜索 D(z) 和整体 Qi；浅月震在结构确定后再反演震源深度。网格径向分辨率约 17.38 km，因此任何几十公里尺度的突变都只能解释为有效过渡。",
    )
    inversion_rows = [
        ("0.00", "2.43", "11.84", "2396", "1.39"),
        ("8.69", "3.06", "3.61", "2396", "2.83"),
        ("26.05", "6.50", "3.51", "2396", "4.18"),
        ("43.43", "9.10", "4.55", "2396", "4.34"),
        ("60.80", "10.37", "5.16", "2396", "4.35"),
        ("78.17", "26.06", "12.98", "2396", "4.35"),
        ("95.54", "217.59", "107.88", "2396", "4.36"),
        ("112.91", "336.89", "166.26", "2396", "4.37"),
        ("130.28", "871.03", "427.91", "2396", "4.38"),
        ("147.65", "3334.00", "1630.45", "2396", "4.39"),
    ]
    add_table(document, ["深度 km", "D km²/s", "Qsc", "Qi", "Vs km/s"], inversion_rows, [1650, 1900, 1750, 1700, 2360], font_size=8.4)
    add_figure(
        document,
        assets["pepi_fig7"],
        "图 8　2017 PEPI Figure 7 与 Table 2：最佳扩散率、散射品质因子和观测拟合。",
        "原图节选自 Gillet et al. (2017), Figure 7 与 Table 2。",
        width=5.9,
        alt_text="月球扩散率和散射品质因子的深度剖面",
    )
    add_heading(document, "7.2　反演得到的三层结构", 2)
    add_bullet(document, "表层：D≈2.43 km²/s、Qsc 约 10 的量级，代表极强散射。")
    add_bullet(document, "0–80 km：D 缓慢增大，说明非均匀性随围压增加逐步减弱。")
    add_bullet(document, "80–100 km：D 在不到约 20 km 内上升近一个数量级，可解释为强裂隙/散射带的下边界。")
    add_bullet(document, "约 150 km：D≈3334 km²/s、Qsc≈1630，介质转为相对弱非均匀。")
    add_bullet(document, "整体最佳 Qi≈2396；浅月震最可能平均深度约 52 km，总体约 50±20 km。")
    add_heading(document, "7.3　扩散模型的边界", 2)
    add_paragraph(
        document,
        "扩散方程描述的是强多重散射后的能量统计传播，不追踪相干 P、S、反射、折射和低速层干涉。因此它非常适合 tmax 和晚期尾波，却不能代替全波形三维模拟。你的 300 km 局部笛卡尔模型也不能复现球形月球上的全球能量回返，所以没有必要强求它匹配实测记录数千秒的全部尾波。",
    )
    add_callout(document, "对你的时间窗", "先把合成稳定延长到 500–600 s，并检查末端能量是否仍显著；若末端已接近零，再延长时窗意义有限。实测 1000–1200 s 尾波可作为全球回返和未建模散射的证据，而不是局部模型必须逐点拟合的硬目标。")
    document.add_page_break()


def add_synthesis(document):
    add_heading(document, "8　五篇论文的共识、分歧与综合判断", 1)
    add_heading(document, "8.1　可以视为稳健共识的内容", 2)
    consensus = [
        "月球近表面至上部地壳具有极强、跨尺度的非均匀性。",
        "月球内禀吸收很弱，高 Qi 允许能量长时间保存。",
        "低速浅层或强速度梯度对尾波和振铃具有一级影响。",
        "浅源与深源进入散射层的几何不同，不能用同一距离关系简单套用。",
        "台站附近、盆地边缘与传播路径的横向结构会叠加在全球平均背景上。",
        "单一持续时间或单一 Q 参数无法唯一确定速度、散射层厚度、散射强度和吸收。",
    ]
    for item in consensus:
        add_bullet(document, item)
    add_heading(document, "8.2　三组关键分歧", 2)
    disagreement_rows = [
        ("长振铃主因", "2012/2015/2017 强调散射与高 Qi", "2016 表明低速层共振可单独产生长振铃", "联合机制；用包络随机性、模态混合和距离统计区分贡献"),
        ("散射层厚度", "2015 参数试验 5–60 km", "2017 有效强散射延伸至约 100 km", "前者是试验范围，后者是粗分辨率扩散等效深度"),
        ("Qc 的含义", "2012 视为混合有效量", "2017 晚期充分扩散时偏向 Qi", "解释依赖时段、距离和扩散成立程度"),
    ]
    add_table(document, ["问题", "一侧证据", "另一侧证据", "综合处理"], disagreement_rows, [1450, 2450, 2450, 3010], font_size=8.5)
    add_heading(document, "8.3　最合理的联合机制", 2)
    add_paragraph(
        document,
        "震源能量首先进入速度很低、梯度很强的近表面层。该结构延长驻留时间并产生反射、频散或共振；随后多尺度裂隙、块体和界面使 P、SV、SH 反复转换和方向随机化，包络因此缓慢上升、峰值推迟并形成长尾。由于 Qi 很高，能量在多次散射和绕月传播中不易耗散；球形几何又允许进入深部的能量在其他位置返回近表面。盆地、地形和台站局地结构进一步改变某条路径的散射强度。",
    )
    add_callout(document, "最终判断", "低速层控制“能量是否容易被留在浅部”，散射控制“能量如何被展宽和混合”，Qi 控制“能量能保存多久”，球形与横向结构控制“能量从哪里回来、在哪些台站更明显”。")
    add_heading(document, "8.4　什么证据可以区分机制", 2)
    diagnostic_rows = [
        ("低速层/共振", "窄带持续振荡、明显频散、可重复的周期结构、到时整体延迟"),
        ("随机散射", "起振渐进、包络展宽、相位随机化、P–SV–SH 模态混合、距离依赖"),
        ("高 Qi", "峰值之后的晚期衰减斜率缓慢，但不必显著改变早期形态"),
        ("地形/横向结构", "不同射线或盆缘位置出现系统差异，同一局地高程不足以解释"),
    ]
    add_table(document, ["候选机制", "优先寻找的波形证据"], diagnostic_rows, [2250, 7110], font_size=9)
    document.add_page_break()


def add_application(document, assets):
    add_heading(document, "9　直接应用到你的四模型与 A16S12 实测", 1)
    add_heading(document, "9.1　现有模型能回答什么", 2)
    model_rows = [
        ("模型 1", "平坦", "无散射", "几何与背景速度基线"),
        ("模型 2", "平坦", "有散射", "纯散射增量"),
        ("模型 3", "地形", "无散射", "纯地形增量"),
        ("模型 4", "地形", "有散射", "地形—散射交互"),
    ]
    add_table(document, ["模型", "地形", "散射", "主要用途"], model_rows, [1600, 1600, 1600, 4560], font_size=9)
    add_figure(
        document,
        assets["observed_models"],
        "图 9　A16S12 三分量实测与四模型对比：合成波形在约 250 s 内迅速衰减，而实测尾波延续到 1000 s。",
        "图由当前项目数据生成；所有模型使用各自统一的三分量 RMS 标度。",
        width=6.35,
        alt_text="A16S12实测三分量与四个模型的波形和包络比较",
    )
    add_paragraph(
        document,
        "这张图给出一个非常直接的结论：现有地形和散射设置能改变峰值、早期尾波和三分量分配，但没有复制实测的长时间能量保存。差异不能靠单一振幅系数修复；它表明浅表低速俘获、散射尺度/强度、Qi、模型范围或全球回返中至少有一项尚未充分表示。",
    )
    add_heading(document, "9.2　加入低速层的正确方式", 2)
    add_numbered(document, "把同一 1 km 等效低速层同时加入四个模型，保持地形与散射因素正交。")
    add_numbered(document, "以 Vp=1.38 km/s、Vs=1.11 km/s 作为候选起点，同时至少测试一档较温和和一档较强模型。")
    add_numbered(document, "在同一震源时函数、同一滤波器、同一时间窗和同一三分量标度下比较。")
    add_numbered(document, "不要用事后静态平移代替低速层，因为低速层不仅改变初至，还改变反射、频散、模态和尾波。")
    add_figure(
        document,
        assets["low_velocity_diagnostic"],
        "图 10　静态延迟只能平移初至，不能补出实测中的 qSV/SH 长尾与能量持续。",
        "图由当前项目三分量诊断生成；候选低速层仅用于估计最小双程延迟。",
        width=6.35,
        alt_text="低速层速度剖面和静态延迟修正局限",
    )
    add_heading(document, "9.3　推荐的模型矩阵", 2)
    experiment_rows = [
        ("A", "原四模型", "无低速层", "确认现有地形与散射基线"),
        ("B", "原四模型", "1 km，Vp=1.38，Vs=1.11", "主候选等效低速层"),
        ("C", "模型 1/2 或全四组", "更温和速度或 0.5 km", "厚度—速度权衡"),
        ("D", "模型 1/2 或全四组", "更强低速或 1.5–2 km", "振铃上限与数值稳定性"),
    ]
    add_table(document, ["组", "地形×散射", "低速层", "目的"], experiment_rows, [900, 2000, 3050, 3410], font_size=8.6)
    add_heading(document, "9.4　建议统一输出的十项指标", 2)
    metrics = [
        "三分量 t0、tmax 与 tmax−t0；",
        "10%、50%、90%、95% 累积能量时间；",
        "峰值后 td 和 Qc；",
        "70–140 s 直接波窗内的波形相关系数；",
        "100–500 s 早期尾波能量；",
        "每个模型相对实测的单一三分量 RMS 缩放系数；",
        "P、qSV、SH 的能量比例与随时间演化；",
        "0.25–0.75、0.75–1.25、0.3–0.9 Hz 三频带结果；",
        "沿三条射线的平均起伏、均方坡度、最大高差和盆缘穿越；",
        "末端 50 s 能量占比，用于决定是否继续延长模拟。",
    ]
    for metric in metrics:
        add_bullet(document, metric)
    add_heading(document, "9.5　时间窗建议", 2)
    window_rows = [
        ("50–245 s", "直接波形和早期尾波", "与当前合成长度兼容"),
        ("70–180 s", "对齐、相关和相位形态", "避免被长尾主导标度"),
        ("100–500 s", "包络衰减与散射展宽", "需把模拟先延长到 500–600 s"),
        ("500–1200 s", "实测全球长尾背景", "主要用于识别局部模型缺失，不强求逐点拟合"),
    ]
    add_table(document, ["时窗", "用途", "解释"], window_rows, [1900, 3000, 4460], font_size=8.8)
    add_callout(document, "论文写作表述", "可以说“地形与散射解释了早期波形的部分差异，但现有局部模型不能解释 Apollo 实测的长持续尾波；文献表明浅表低速俘获、高 Qi 和球形能量回返是必须进一步纳入的机制。”")
    document.add_page_break()


def add_conclusion_chapter(document):
    add_heading(document, "10　可直接带走的研究结论", 1)
    final_conclusions = [
        ("观测层面", "长尾波具有跨事件、跨台站一致性，但频率、距离和台站依赖说明其并非单一均匀衰减过程。"),
        ("速度层面", "低速层与速度梯度是一级控制项，能够放大散射层驻留并产生共振；缺失它会使合成波形过短、过脉冲化。"),
        ("散射层面", "散射负责包络展宽、渐进起振与模态混合；厚度和强度之间存在非唯一性。"),
        ("吸收层面", "月球 Qi 很高，晚期能量保存强；仅增加散射而 Qi 不够高，仍可能无法产生足够长的尾波。"),
        ("几何层面", "球形能量回返对数百至数千秒尾波很重要，300 km 局部模型不应承担全球传播的全部解释。"),
        ("横向结构", "盆缘和路径起伏可改变有效散射，三个射线应按整条路径统计，而非只看台站高程。"),
        ("方法层面", "tmax、td、Qc、波形相关、累积能量与三分量模式比例必须联合使用。"),
        ("频带层面", "0.3–0.9 Hz 适合当前目标，但需增算 0.25–0.75 和 0.75–1.25 Hz 才能与主要文献严格对照。"),
        ("低速层试验", "先对四模型统一加入可分辨的 1 km 等效层，再用速度—厚度矩阵测试，不要直接照搬米级层状表。"),
        ("实测对比", "三分量只能使用同一缩放尺度；独立归一化会掩盖偏振、能量分配与模态转换差异。"),
        ("时窗层面", "局部模型先扩展到 500–600 s 并检查末端能量；实测 1200 s 可作为缺失全球机制的证据。"),
        ("最终机制", "低速俘获/共振、随机多重散射、高 Qi 与球形/横向传播共同构成最完整解释。"),
    ]
    for index, (label, text) in enumerate(final_conclusions, start=1):
        add_rich_paragraph(document, [
            (f"{index}. {label}：", {"bold": True, "color": DEEP_BLUE}),
            text,
        ], after=6)
    add_callout(document, "一句话总括", "如果只保留一个判断：现有四模型已经能识别地形与散射对早期波形的相对作用，但要逼近 A16S12 的真实形态，下一步必须把可分辨的浅表低速层、足够高的 Qi、三分量模态转换和更长/更全球的能量传播同时纳入验证框架。", fill=PALE_GOLD, border=GOLD)
    document.add_page_break()


def add_appendices(document):
    add_heading(document, "附录 A　关键数值速查", 1)
    quick_rows = [
        ("2012 JGR", "72 事件；369 记录；641 个 td；长周期 0.25–1.75 Hz"),
        ("2015 JGR", "TSL=5/15/30/60 km；扰动 ±25/75/95%；Qi≈2000/4500/6500"),
        ("2015 GRL", "盆外 TSL=5–60 km；盆内 TB=0 或 5 km；低散射距离≈1–1.5×TSL"),
        ("2016 PSS", "0–1.5 km 多层极低速结构；1 Hz 地表力；无吸收/无随机散射"),
        ("2017 PEPI", "62 事件；446 记录；D0=2.43 km²/s；Qi=2396；转变 80–100 km；浅震 50±20 km"),
        ("你的候选低速层", "厚 1 km；Vp=1.38 km/s；Vs=1.11 km/s；应作为等效候选而非唯一真实模型"),
    ]
    add_table(document, ["来源", "关键数值"], quick_rows, [2050, 7310], font_size=9)
    add_heading(document, "附录 B　术语表", 1)
    glossary_rows = [
        ("Coda / 尾波", "主要震相之后持续的散射、反射、转换与共振能量。"),
        ("tmax", "平滑能量包络最大值到时，主要对散射展宽敏感。"),
        ("td", "包络指数衰减一个 e 倍的特征时间。"),
        ("Qc", "由尾波衰减估计的有效品质因子，可能混合散射、吸收与几何。"),
        ("Qi", "内禀吸收品质因子；越大表示非弹性耗散越弱。"),
        ("Qsc / Qs", "散射品质因子；越小通常表示散射越强。"),
        ("D", "扩散率；在强多重散射极限下描述能量扩散速度。"),
        ("TSL / TB", "盆外散射层厚度 / 盆内散射层厚度。"),
        ("VLVL", "极浅低速层，用于表示近表面强低速与梯度。"),
        ("PHONON1D", "一维背景中的蒙特卡洛地震能量包传播模型。"),
    ]
    add_table(document, ["术语", "含义"], glossary_rows, [2000, 7360], font_size=9)
    add_heading(document, "附录 C　正式引用的五篇论文", 1)
    references = [
        "Blanchette-Guertin, J.-F., Johnson, C. L., & Lawrence, J. F. (2012). Investigation of scattering in lunar seismic coda. Journal of Geophysical Research, 117, E06003. https://doi.org/10.1029/2011JE004042",
        "Blanchette-Guertin, J.-F., Johnson, C. L., & Lawrence, J. F. (2015). Modeling seismic energy propagation in highly scattering environments. Journal of Geophysical Research: Planets, 120, 515–537. https://doi.org/10.1002/2014JE004654",
        "Blanchette-Guertin, J.-F., Johnson, C. L., & Lawrence, J. F. (2015). Effects of lateral variations in megaregolith thickness on predicted lunar seismic signals. Geophysical Research Letters, 42, 10171–10178. https://doi.org/10.1002/2015GL066151",
        "Burmin, V. Yu., Miroshnikov, V. V., & Fatyanov, A. G. (2016). On the nature of the seismic ringing of the Moon. Analytical modeling. Planetary and Space Science, 126, 72–77. https://doi.org/10.1016/j.pss.2016.03.013",
        "Gillet, K., Margerin, L., Calvet, M., & Monnereau, M. (2017). Scattering attenuation profile of the Moon: Implications for shallow moonquakes and the structure of the megaregolith. Physics of the Earth and Planetary Interiors, 262, 28–40. https://doi.org/10.1016/j.pepi.2016.11.001",
    ]
    for reference in references:
        paragraph = add_paragraph(document, reference, after=6)
        paragraph.paragraph_format.left_indent = Inches(0.25)
        paragraph.paragraph_format.first_line_indent = Inches(-0.25)
        set_run_font(paragraph.runs[0], size=9.5)
    add_heading(document, "附录 D　使用边界", 1)
    add_paragraph(
        document,
        "本文件为研究导读和综合解释，已尽量保留五篇论文的关键数值、图像、限定条件与相互分歧，但不能替代正式引用时对原文图表、方法细节和上下文的核查。本文中的“对你的数据”部分是基于五篇论文与当前项目结果的综合推论，不代表原作者对你的模型作出的直接结论。",
    )


def build_document():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = prepare_assets()
    document = Document()
    configure_styles(document)
    set_document_language(document)
    for section in document.sections:
        configure_section(section)
        configure_header_footer(section)
    core_properties = document.core_properties
    core_properties.title = "月震散射、低速层与长尾波：五篇论文综合精读"
    core_properties.subject = "Apollo 月震观测、强散射、低速层共振与扩散反演"
    core_properties.author = ""
    core_properties.keywords = "月震, Apollo, 散射, 低速层, 尾波, tmax, Qc, Qi, Qsc"
    add_cover(document)
    add_front_matter(document, assets)
    add_chapter_one(document, assets)
    add_chapter_two(document)
    add_paper_2012(document, assets)
    add_paper_2015_jgr(document, assets)
    add_paper_2015_grl(document, assets)
    add_paper_2016(document, assets)
    add_paper_2017(document, assets)
    add_synthesis(document)
    add_application(document, assets)
    add_conclusion_chapter(document)
    add_appendices(document)
    for section in document.sections:
        configure_section(section)
        configure_header_footer(section)
    document.save(OUTPUT_DOCX)
    print(OUTPUT_DOCX)


if __name__ == "__main__":
    build_document()
