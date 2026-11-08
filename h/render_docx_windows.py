"""Run the bundled DOCX renderer with a Windows LibreOffice URI fix."""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path


DOCUMENTS_CACHE = Path(
    r"C:\Users\Administrator\.codex\plugins\cache\openai-primary-runtime\documents"
)


def find_renderer() -> Path:
    candidates = sorted(
        DOCUMENTS_CACHE.glob("*/skills/documents/render_docx.py"),
        key=lambda path: path.parent.parent.parent.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No bundled DOCX renderer found under {DOCUMENTS_CACHE}")
    return candidates[0]


RENDERER = find_renderer()
POPPLER_BIN = Path(
    r"C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\poppler\Library\bin"
)
SOFFICE = Path(__file__).resolve().parent / "tools" / "LibreOffice" / "program" / "soffice.com"


def windows_user_installation_uri(argument: str) -> str:
    prefix = "-env:UserInstallation=file://"
    if os.name != "nt" or not argument.startswith(prefix):
        return argument
    path = argument[len(prefix) :].replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", path):
        return prefix + "/" + path
    return argument


def main() -> None:
    os.environ["PATH"] = os.pathsep.join(
        (str(POPPLER_BIN), os.environ.get("PATH", ""))
    )
    specification = importlib.util.spec_from_file_location("codex_render_docx", RENDERER)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Unable to load renderer: {RENDERER}")
    renderer = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(renderer)
    original_run_command = renderer._run_cmd

    def patched_run_command(command, *args, **kwargs):
        fixed_command = [windows_user_installation_uri(str(item)) for item in command]
        if fixed_command and fixed_command[0].lower() == "soffice":
            fixed_command[0] = str(SOFFICE)
        return original_run_command(fixed_command, *args, **kwargs)

    renderer._run_cmd = patched_run_command
    renderer.main()


if __name__ == "__main__":
    main()
