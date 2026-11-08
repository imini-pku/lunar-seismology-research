param(
    [Parameter(Mandatory = $true)]
    [string]$InputDocx,
    [string]$OutputDir = "tmp\docx_render",
    [switch]$EmitPdf
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$libreOfficeDir = Join-Path $workspace "tools\LibreOffice\program"
$python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$renderer = Join-Path $workspace "render_docx_windows.py"

if (-not (Test-Path -LiteralPath (Join-Path $libreOfficeDir "soffice.exe"))) {
    throw "Local LibreOffice renderer is missing: $libreOfficeDir"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Bundled Python is missing: $python"
}
if (-not (Test-Path -LiteralPath $renderer)) {
    throw "DOCX renderer script is missing: $renderer"
}

$env:PATH = "$libreOfficeDir;$env:PATH"
$resolvedInput = (Resolve-Path -LiteralPath $InputDocx).Path
$resolvedOutput = if ([IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir
} else {
    Join-Path $workspace $OutputDir
}

$arguments = @($renderer, $resolvedInput, "--output_dir", $resolvedOutput)
if ($EmitPdf) {
    $arguments += "--emit_pdf"
}

& $python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
