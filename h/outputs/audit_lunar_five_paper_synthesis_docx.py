import json
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-21\h")
DOCX_PATH = ROOT / "outputs" / "月震散射与低速层_五篇论文综合精读.docx"
REPORT_PATH = ROOT / "tmp" / "lunar_synthesis_structure_audit.json"


def int_attr(element, name):
    value = element.get(qn(name)) if element is not None else None
    return int(value) if value is not None else None


def audit():
    findings = []
    with zipfile.ZipFile(DOCX_PATH) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member:
            findings.append(f"ZIP corruption: {corrupt_member}")
        archive_names = set(archive.namelist())
        media_files = sorted(name for name in archive_names if name.startswith("word/media/"))
    document = Document(DOCX_PATH)
    section = document.sections[0]
    expected_geometry = {
        "page_width": 7772400,
        "page_height": 10058400,
        "margin": 914400,
    }
    actual_geometry = {
        "page_width": section.page_width,
        "page_height": section.page_height,
        "top_margin": section.top_margin,
        "bottom_margin": section.bottom_margin,
        "left_margin": section.left_margin,
        "right_margin": section.right_margin,
    }
    if actual_geometry["page_width"] != expected_geometry["page_width"]:
        findings.append("Page width does not match US Letter")
    if actual_geometry["page_height"] != expected_geometry["page_height"]:
        findings.append("Page height does not match US Letter")
    for margin_name in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        if actual_geometry[margin_name] != expected_geometry["margin"]:
            findings.append(f"{margin_name} does not equal 1 inch")
    table_audit = []
    for table_index, table in enumerate(document.tables, start=1):
        properties = table._tbl.tblPr
        table_width = int_attr(properties.first_child_found_in("w:tblW"), "w:w")
        table_indent = int_attr(properties.first_child_found_in("w:tblInd"), "w:w")
        grid_widths = [int_attr(node, "w:w") for node in table._tbl.tblGrid]
        grid_sum = sum(width for width in grid_widths if width is not None)
        table_ok = table_width == 9360 and table_indent == 120 and grid_sum == 9360
        if not table_ok:
            findings.append(f"Table {table_index} geometry mismatch")
        table_audit.append({
            "index": table_index,
            "rows": len(table.rows),
            "columns": len(table.columns),
            "width_dxa": table_width,
            "indent_dxa": table_indent,
            "grid_sum_dxa": grid_sum,
            "ok": table_ok,
        })
    all_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    forbidden_tokens = ["PLACEHOLDER", "TODO"]
    for token in forbidden_tokens:
        if token in all_text:
            findings.append(f"Forbidden token found: {token}")
    fake_list_paragraphs = [
        paragraph.text for paragraph in document.paragraphs
        if paragraph.text.startswith("- ") or paragraph.text.startswith("• ")
    ]
    if fake_list_paragraphs:
        findings.append(f"Fake list paragraphs found: {len(fake_list_paragraphs)}")
    alt_texts = []
    for drawing in document.element.body.iter(qn("w:drawing")):
        for doc_properties in drawing.iter(qn("wp:docPr")):
            alt_texts.append(doc_properties.get("descr") or "")
    missing_alt = [index for index, value in enumerate(alt_texts, start=1) if not value.strip()]
    if missing_alt:
        findings.append(f"Missing alt text for drawings: {missing_alt}")
    heading_counts = {}
    for paragraph in document.paragraphs:
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.startswith("Heading"):
            heading_counts[style_name] = heading_counts.get(style_name, 0) + 1
    report = {
        "docx": str(DOCX_PATH),
        "size_bytes": DOCX_PATH.stat().st_size,
        "zip_ok": not corrupt_member,
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "inline_shapes": len(document.inline_shapes),
        "embedded_media": len(media_files),
        "alt_text_count": len(alt_texts),
        "heading_counts": heading_counts,
        "section_count": len(document.sections),
        "page_geometry_emu": actual_geometry,
        "table_audit": table_audit,
        "findings": findings,
        "status": "PASS" if not findings else "FAIL",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    audit()
