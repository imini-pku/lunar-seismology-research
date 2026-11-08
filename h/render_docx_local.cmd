@echo off
setlocal
set "WORKSPACE=%~dp0"
set "LO_DIR=%WORKSPACE%tools\LibreOffice\program"
set "PYTHON=C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "RENDERER=%WORKSPACE%render_docx_windows.py"

if "%~1"=="" (
  echo Usage: render_docx_local.cmd input.docx output_dir [--emit_pdf]
  exit /b 2
)

if not exist "%LO_DIR%\soffice.exe" (
  echo Local LibreOffice renderer is missing: %LO_DIR%
  exit /b 3
)

set "PATH=%LO_DIR%;%PATH%"
"%PYTHON%" "%RENDERER%" "%~1" --output_dir "%~2" %~3
exit /b %ERRORLEVEL%
