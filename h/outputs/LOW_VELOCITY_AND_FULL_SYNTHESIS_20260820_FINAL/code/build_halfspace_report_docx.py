"""Build the illustrated half-space analysis report DOCX from its Markdown source."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
SOURCE = PACKAGE_DIR / "reports" / "半空间区域数据分析与交叉核对报告.md"
OUTPUT = (
    PACKAGE_DIR
    / "reports"
    / "半空间区域数据分析与交叉核对报告_真实800台站几何修订.docx"
)

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "0B2545"
MUTED = "5B6573"
TABLE_FILL = "E8EEF5"
LIGHT_FILL = "F4F6F9"
WHITE = "FFFFFF"
CONTENT_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120


def set_cell_shading(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def mark_table_header(row) -> None:
    """Mark a table's first row as a semantic/repeating header row."""
    properties = row._tr.get_or_add_trPr()
    header = properties.find(qn("w:tblHeader"))
    if header is None:
        header = OxmlElement("w:tblHeader")
        properties.append(header)
    header.set(qn("w:val"), "true")


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa: list[int]) -> None:
    if sum(widths_dxa) != CONTENT_WIDTH_DXA:
        raise ValueError(f"Table widths must total {CONTENT_WIDTH_DXA}: {widths_dxa}")
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    properties = table._tbl.tblPr
    width = properties.find(qn("w:tblW"))
    if width is None:
        width = OxmlElement("w:tblW")
        properties.append(width)
    width.set(qn("w:w"), str(CONTENT_WIDTH_DXA))
    width.set(qn("w:type"), "dxa")
    indent = properties.find(qn("w:tblInd"))
    if indent is None:
        indent = OxmlElement("w:tblInd")
        properties.append(indent)
    indent.set(qn("w:w"), str(TABLE_INDENT_DXA))
    indent.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for value in widths_dxa:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(value))
        grid.append(column)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.width = Inches(widths_dxa[index] / 1440.0)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc_width = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
            tc_width.set(qn("w:w"), str(widths_dxa[index]))
            tc_width.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def set_font(run, size=None, bold=None, italic=None, color=None, ascii_name="Calibri") -> None:
    run.font.name = ascii_name
    properties = run._element.get_or_add_rPr()
    fonts = properties.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.insert(0, fonts)
    fonts.set(qn("w:ascii"), ascii_name)
    fonts.set(qn("w:hAnsi"), ascii_name)
    fonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_inline(paragraph, text: str, size: float = 11, color: str | None = None) -> None:
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_font(run, size=9.5, color=DARK_BLUE, ascii_name="Consolas")
        elif part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_font(run, size=size, bold=True, color=color)
        else:
            run = paragraph.add_run(part)
            set_font(run, size=size, color=color)


def set_keep_with_next(paragraph) -> None:
    paragraph.paragraph_format.keep_with_next = True


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_font(run, size=9, color=MUTED)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t")
    value.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, value, end])


def configure_styles(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    for name, size, color, before, after in (
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, BLUE, 14, 7),
        ("Heading 3", 12, DARK_BLUE, 10, 5),
    ):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    caption = document.styles["Caption"]
    caption.font.name = "Calibri"
    caption.font.size = Pt(9)
    caption.font.italic = False
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.keep_together = True

    for style_name in ("List Bullet", "List Number"):
        style = document.styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25

    header = section.header
    header_table = header.add_table(rows=1, cols=2, width=Inches(6.5))
    mark_table_header(header_table.rows[0])
    set_table_geometry(header_table, [5200, 4160])
    for cell in header_table.rows[0].cells:
        cell._tc.get_or_add_tcPr().append(OxmlElement("w:tcBorders"))
    left = header_table.cell(0, 0).paragraphs[0]
    left.paragraph_format.space_after = Pt(0)
    add_inline(left, "JGR: Planets 半空间区域数据分析", size=9, color=MUTED)
    right = header_table.cell(0, 1).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right.paragraph_format.space_after = Pt(0)
    add_inline(right, "2026-08-17", size=9, color=MUTED)
    footer = section.footer
    add_page_number(footer.paragraphs[0])


def add_title_block(document: Document, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(title)
    set_font(run, size=23, bold=True, color=INK)
    subtitle = document.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(14)
    add_inline(
        subtitle,
        "三分量波形、地形分辨率、分层效应及与 A16/S12 证据链的交叉检验",
        size=12.5,
        color=MUTED,
    )
    for label, value in (
        ("分析日期", "2026-08-17"),
        ("频带", "0.3-0.9 Hz"),
        ("主要产物", "路径目录、校验和、派生表和九幅数据图"),
    ):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(2)
        label_run = paragraph.add_run(f"{label}：")
        set_font(label_run, size=10.5, bold=True, color=DARK_BLUE)
        value_run = paragraph.add_run(value)
        set_font(value_run, size=10.5, color=INK)
    document.add_paragraph().paragraph_format.space_after = Pt(3)


def add_markdown_table(document: Document, lines: list[str]) -> None:
    parsed = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    rows = [parsed[0], *parsed[2:]]
    columns = len(rows[0])
    if columns == 4:
        widths = [1320, 2700, 3060, 2280]
    elif columns == 2:
        widths = [2700, 6660]
    else:
        base = CONTENT_WIDTH_DXA // columns
        widths = [base] * columns
        widths[-1] += CONTENT_WIDTH_DXA - sum(widths)
    table = document.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    mark_table_header(table.rows[0])
    set_table_geometry(table, widths)
    for row_index, row in enumerate(rows):
        for column_index, text in enumerate(row):
            cell = table.cell(row_index, column_index)
            if row_index == 0:
                set_cell_shading(cell, TABLE_FILL)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.08
            add_inline(paragraph, text, size=8.7, color=INK)
            if row_index == 0:
                for run in paragraph.runs:
                    run.bold = True
    after = document.add_paragraph()
    after.paragraph_format.space_before = Pt(4)
    after.paragraph_format.space_after = Pt(4)


def build() -> Path:
    document = Document()
    configure_styles(document)
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("Markdown report must start with a level-one title")
    add_title_block(document, lines[0][2:].strip())
    index = 1
    # The title block already presents these report metadata fields. Skip the
    # Markdown copies so they are not repeated on the first page of the DOCX.
    metadata_prefixes = ("日期：", "处理频带：", "分析范围：")
    while index < len(lines) and (
        not lines[index].strip() or lines[index].startswith(metadata_prefixes)
    ):
        index += 1
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            paragraph = document.add_paragraph()
            add_inline(paragraph, " ".join(item.strip() for item in paragraph_buffer))
            paragraph_buffer = []

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            flush_paragraph()
            index += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            paragraph = document.add_paragraph(line[3:].strip(), style="Heading 1")
            set_keep_with_next(paragraph)
            index += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            paragraph = document.add_paragraph(line[4:].strip(), style="Heading 2")
            set_keep_with_next(paragraph)
            index += 1
            continue
        image_match = re.fullmatch(r"!\[(.+)]\((.+)\)", line.strip())
        if image_match:
            flush_paragraph()
            caption_text, relative_path = image_match.groups()
            image_path = (SOURCE.parent / relative_path).resolve()
            picture_paragraph = document.add_paragraph()
            picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            picture_paragraph.paragraph_format.space_before = Pt(4)
            picture_paragraph.paragraph_format.space_after = Pt(0)
            picture_paragraph.paragraph_format.keep_with_next = True
            run = picture_paragraph.add_run()
            shape = run.add_picture(str(image_path), width=Inches(6.45))
            shape._inline.docPr.set("descr", caption_text)
            shape._inline.docPr.set("title", caption_text)
            caption = document.add_paragraph(caption_text, style="Caption")
            caption.paragraph_format.keep_with_next = False
            index += 1
            continue
        if line.startswith("- "):
            flush_paragraph()
            paragraph = document.add_paragraph(style="List Bullet")
            add_inline(paragraph, line[2:].strip())
            index += 1
            continue
        if re.match(r"^\d+\.\s", line):
            flush_paragraph()
            paragraph = document.add_paragraph(style="List Number")
            add_inline(paragraph, re.sub(r"^\d+\.\s+", "", line).strip())
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            add_markdown_table(document, table_lines)
            continue
        if line.endswith("  "):
            flush_paragraph()
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, line.strip(), size=10.5, color=MUTED)
            index += 1
            continue
        paragraph_buffer.append(line)
        index += 1
    flush_paragraph()

    properties = document.core_properties
    properties.title = "半空间区域数据分析与交叉核对报告"
    properties.subject = "Half-space three-component waveform, resolution, layering, and A16 cross-check"
    properties.author = "JGR: Planets project analysis"
    properties.keywords = "lunar seismology, topography, half-space, waveform similarity, A16"
    document.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
