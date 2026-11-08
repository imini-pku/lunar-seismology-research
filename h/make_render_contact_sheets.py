"""Create readable contact sheets from rendered DOCX page PNG files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def page_number(path: Path) -> int:
    match = re.search(r"page-(\d+)$", path.stem)
    return int(match.group(1)) if match else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("render_dir", type=Path)
    parser.add_argument("--pages-per-sheet", type=int, default=4)
    args = parser.parse_args()

    pages = sorted(args.render_dir.glob("page-*.png"), key=page_number)
    output_dir = args.render_dir / "contact_sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    thumb_width = 720
    label_height = 30
    columns = 2
    rows = max(1, (args.pages_per_sheet + columns - 1) // columns)

    for start in range(0, len(pages), args.pages_per_sheet):
        group = pages[start : start + args.pages_per_sheet]
        prepared = []
        max_height = 0
        for page in group:
            with Image.open(page) as image:
                image = image.convert("RGB")
                thumb_height = round(image.height * thumb_width / image.width)
                thumb = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            prepared.append((page_number(page), thumb))
            max_height = max(max_height, thumb.height)
        sheet = Image.new("RGB", (columns * thumb_width, rows * (max_height + label_height)), "#D8D8D8")
        draw = ImageDraw.Draw(sheet)
        for index, (number, thumb) in enumerate(prepared):
            x = (index % columns) * thumb_width
            y = (index // columns) * (max_height + label_height)
            sheet.paste(thumb, (x, y + label_height))
            draw.rectangle((x, y, x + thumb_width, y + label_height), fill="white")
            draw.text((x + 10, y + 8), f"Page {number}", fill="black", font=font)
        end = page_number(group[-1])
        sheet.save(output_dir / f"pages_{page_number(group[0]):03d}_{end:03d}.jpg", quality=88)


if __name__ == "__main__":
    main()
