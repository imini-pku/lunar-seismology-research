"""Build submission DOCX files from the auditable Markdown sources."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_MD = ROOT / "manuscript" / "manuscript.md"
SI_MD = ROOT / "supporting_information" / "supporting_information.md"
COVER_MD = ROOT / "submission_materials" / "cover_letter.md"
FIGURES = ROOT / "figures" / "main"

FIGURE_FILES = {
    1: "Figure_1_experiment_design.png",
    2: "Figure_2_factorial_waveforms.png",
    3: "Figure_3_component_energy.png",
    4: "Figure_4_path_relief.png",
    5: "Figure_5_interaction_residual.png",
    6: "Figure_6_linear_diffusion.png",
    7: "Figure_7_observed_models.png",
}

ADDITIONAL_FIGURE_FILES = {
    8: ROOT / "figures" / "synthesis" / "Figure_A16_M1_M6_unified_ladder.png",
    9: ROOT / "figures" / "synthesis" / "Figure_A16_M1_M6_tmax_distance.png",
    10: ROOT / "figures" / "low_velocity" / "Figure_S12_M1_M6_observed_envelope_comparison.png",
}


def set_run_font(run, name: str = "Times New Roman", size: float | None = None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tcMar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def shade(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), fill)


def fixed_table_geometry(table, widths: list[int]) -> None:
    total = sum(widths)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tblPr = table._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), str(total))
    tblW.set(qn("w:type"), "dxa")
    tblLayout = tblPr.find(qn("w:tblLayout"))
    if tblLayout is None:
        tblLayout = OxmlElement("w:tblLayout")
        tblPr.append(tblLayout)
    tblLayout.set(qn("w:type"), "fixed")
    tblInd = tblPr.find(qn("w:tblInd"))
    if tblInd is None:
        tblInd = OxmlElement("w:tblInd")
        tblPr.append(tblInd)
    tblInd.set(qn("w:w"), "120")
    tblInd.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            tcW = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                cell._tc.get_or_add_tcPr().append(tcW)
            tcW.set(qn("w:w"), str(widths[index]))
            tcW.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.append(fld)


def configure_document(doc: Document, running_title: str) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for style_name, size, before, after in (
        ("Heading 1", 13, 14, 6),
        ("Heading 2", 11.5, 10, 5),
        ("Heading 3", 11, 8, 4),
    ):
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    styles["Heading 2"].font.italic = True

    caption = styles["Caption"]
    caption.font.name = "Times New Roman"
    caption._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    caption._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    caption.font.size = Pt(9.5)
    caption.font.color.rgb = RGBColor(0, 0, 0)
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.line_spacing = 1.0

    header = section.header.paragraphs[0]
    header.text = running_title
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in header.runs:
        set_run_font(run, "Times New Roman", 8.5)
        run.font.color.rgb = RGBColor(90, 90, 90)
    add_page_number(section.footer.paragraphs[0])

    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.core_properties.title = running_title
    doc.core_properties.subject = "JGR: Planets submission manuscript"


def add_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text)
    set_run_font(run, "Times New Roman", 16)
    run.font.bold = True


def clean_inline(text: str) -> str:
    text = text.replace("**", "").replace("`", "")
    text = text.replace("  ", " ")
    return text.strip()


def add_text_paragraph(doc: Document, text: str, *, reference: bool = False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.widow_control = True
    if reference:
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0
    cleaned = clean_inline(text)
    parts = re.split(r"(\^[^^]+\^)", cleaned)
    for part in parts:
        if not part:
            continue
        superscript = part.startswith("^") and part.endswith("^")
        run = p.add_run(part[1:-1] if superscript else part)
        set_run_font(run, "Times New Roman", 10 if reference else 11)
        run.font.superscript = superscript


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        cells = [part.strip() for part in lines[index].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            rows.append(cells)
        index += 1
    return rows, index


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    equal = [9360 // columns] * columns
    equal[-1] += 9360 - sum(equal)
    fixed_table_geometry(table, equal)
    for r_index, values in enumerate(rows):
        for c_index in range(columns):
            cell = table.cell(r_index, c_index)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            text = clean_inline(values[c_index]) if c_index < len(values) else ""
            cell.text = text
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    set_run_font(run, "Times New Roman", 9)
                    if r_index == 0:
                        run.font.bold = True
            if r_index == 0:
                shade(cell, "E8EEF5")
                trPr = table.rows[0]._tr.get_or_add_trPr()
                if trPr.find(qn("w:tblHeader")) is None:
                    trPr.append(OxmlElement("w:tblHeader"))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def figure_captions(lines: list[str]) -> dict[int, str]:
    captions: dict[int, str] = {}
    in_section = False
    for line in lines:
        if line.strip() == "## Figure Captions":
            in_section = True
            continue
        if in_section:
            match = re.match(r"Figure (\d+)\.\s*(.*)", line.strip())
            if match:
                captions[int(match.group(1))] = f"Figure {match.group(1)}. {match.group(2)}"
    return captions


def add_figure(doc: Document, number: int, caption_text: str, file_path: Path) -> None:
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(file_path), width=Inches(6.45))
    drawings = run._r.xpath(".//wp:docPr")
    if drawings:
        drawings[0].set("descr", f"Figure {number}: {caption_text.split('.', 1)[-1].strip()}")
        drawings[0].set("title", f"Figure {number}")
    cp = doc.add_paragraph(style="Caption")
    cp.paragraph_format.keep_with_next = False
    cr = cp.add_run(caption_text)
    set_run_font(cr, "Times New Roman", 9.5)


def build_from_markdown(md_path: Path, output_path: Path, running_title: str,
                        *, include_main_figures: bool = False) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    captions = figure_captions(lines)
    doc = Document()
    configure_document(doc, running_title)
    in_references = False
    skip_captions = False
    first_title = True
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped == "## Figure Captions":
            skip_captions = True
            index += 1
            continue
        if skip_captions:
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if stripped.startswith("[[FIGURE:"):
            index += 1
            continue
        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            add_table(doc, rows)
            continue
        if stripped.startswith("# "):
            title = clean_inline(stripped[2:])
            if first_title:
                add_title(doc, title)
                first_title = False
            else:
                doc.add_heading(title, level=1)
            index += 1
            continue
        if stripped.startswith("## "):
            heading = clean_inline(stripped[3:])
            doc.add_heading(heading, level=1)
            in_references = heading == "References"
            index += 1
            continue
        if stripped.startswith("### "):
            doc.add_heading(clean_inline(stripped[4:]), level=2)
            index += 1
            continue
        if re.match(r"^\d+\.\s+", stripped):
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(re.sub(r"^\d+\.\s+", "", clean_inline(stripped)))
            set_run_font(run, "Times New Roman", 11)
            index += 1
            continue
        if stripped.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            p.paragraph_format.space_after = Pt(5)
            run = p.add_run(clean_inline(stripped[2:]))
            set_run_font(run, "Times New Roman", 11)
            index += 1
            continue
        add_text_paragraph(doc, stripped, reference=in_references)
        index += 1

    if include_main_figures:
        for number, filename in FIGURE_FILES.items():
            file_path = FIGURES / filename
            if not file_path.exists():
                raise FileNotFoundError(file_path)
            add_figure(doc, number, captions[number], file_path)
        for number, file_path in ADDITIONAL_FIGURE_FILES.items():
            if not file_path.exists():
                raise FileNotFoundError(file_path)
            add_figure(doc, number, captions[number], file_path)

    if md_path == SI_MD:
        si_figures = [
            (
                "S1",
                "Figure S1. Sensitivity of the M3-M1 energy-peak delay to envelope smoothing. The positive ensemble delay persists for windows of 5, 10, and 20 dominant periods, while its magnitude changes with window length and receiver profile.",
                ROOT / "figures" / "supporting" / "Figure_S1_smoothing_sensitivity.png",
            ),
            (
                "S2",
                "Figure S2. Time-frequency comparison of the Apollo 16 impact observation at S12 and the four synthetics. The observation retains energetic, time-varying content beyond the 250 s modeled window, whereas all synthetics decay early.",
                ROOT / "figures" / "supporting" / "Figure_S2_time_frequency.png",
            ),
        ]
        for number, caption, path in si_figures:
            if not path.exists():
                raise FileNotFoundError(path)
            add_figure(doc, number, caption, path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def build_cover_letter() -> None:
    lines = COVER_MD.read_text(encoding="utf-8").replace(
        "[submission date]", date(2026, 8, 14).strftime("%B %d, %Y")
    ).splitlines()
    doc = Document()
    configure_document(doc, "Cover letter - JGR: Planets")
    # A cover letter should not carry a running journal header.
    doc.sections[0].header.paragraphs[0].text = ""
    doc.sections[0].footer.paragraphs[0].text = ""
    first = True
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("# ") and first:
            add_title(doc, text[2:])
            first = False
        else:
            add_text_paragraph(doc, text)
    doc.save(ROOT / "submission_materials" / "cover_letter.docx")


def word_count_section(lines: Iterable[str], heading: str, next_heading: str) -> int:
    active = False
    words: list[str] = []
    for line in lines:
        if line.strip() == heading:
            active = True
            continue
        if active and line.strip() == next_heading:
            break
        if active:
            words.extend(re.findall(r"\b[\w'-]+\b", line))
    return len(words)


def preflight() -> None:
    lines = MANUSCRIPT_MD.read_text(encoding="utf-8").splitlines()
    abstract_words = word_count_section(lines, "## Abstract", "## Plain Language Summary")
    pls_words = word_count_section(lines, "## Plain Language Summary", "Keywords: lunar seismology; topographic scattering; seismic coda; numerical modeling; Apollo; wave propagation")
    key_points = []
    active = False
    for line in lines:
        if line.strip() == "## Key Points":
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active and line.strip().startswith("- "):
            key_points.append(line.strip()[2:])
    report = [
        f"Abstract words: {abstract_words} (limit 250)",
        f"Plain Language Summary words: {pls_words} (limit 200)",
        f"Key points: {len(key_points)} (required 1-3)",
    ]
    report.extend(f"Key point {i} characters: {len(text)} (limit 140)" for i, text in enumerate(key_points, 1))
    report.append(f"Main figures found: {sum((FIGURES / name).exists() for name in FIGURE_FILES.values())}/7")
    (ROOT / "provenance" / "preflight_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    if abstract_words > 250 or pls_words > 200 or len(key_points) not in (1, 2, 3):
        raise ValueError("JGR front-matter limit failed; see preflight_report.txt")
    if any(len(text) > 140 for text in key_points):
        raise ValueError("A Key Point exceeds 140 characters")


def main() -> None:
    preflight()
    build_from_markdown(
        MANUSCRIPT_MD,
        ROOT / "manuscript" / "Wu_et_al_JGR_Planets_manuscript.docx",
        "Wu et al. - Lunar topography and early seismic envelopes",
        include_main_figures=True,
    )
    build_from_markdown(
        SI_MD,
        ROOT / "supporting_information" / "Wu_et_al_JGR_Planets_supporting_information.docx",
        "Supporting Information - Wu et al.",
    )
    build_cover_letter()
    print("Built manuscript, Supporting Information, and cover letter DOCX files.")


if __name__ == "__main__":
    main()
