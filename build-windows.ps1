#!/usr/bin/env pwsh
# Build documents-classifier as a standalone Windows binary using PyInstaller.
#
# Requirements:
#   - Python 3.10+ installed on Windows (https://python.org/downloads)
#   - Run from the documents-classifier directory in PowerShell:
#
#       cd C:\path\to\documents-classifier
#       .\build-windows.ps1
#
# Output: .\dist\documents-classifier.exe

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ── Find Python ────────────────────────────────────────────────────────────────
$Python = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3\.") {
            $Python = $candidate
            break
        }
    } catch { }
}

if (-not $Python) {
    Write-Error "Python 3 not found. Install it from https://python.org/downloads and ensure it is in PATH."
    exit 1
}

Write-Host "Using: $(& $Python --version)"

# ── Virtual environment ────────────────────────────────────────────────────────
if (-not (Test-Path ".venv-win")) {
    Write-Host "── Creating Windows virtual environment ──────────────────────────────"
    & $Python -m venv .venv-win
}

$Pip    = ".venv-win\Scripts\pip.exe"
$PyExe  = ".venv-win\Scripts\python.exe"

Write-Host "── Installing dependencies ────────────────────────────────────────────"
& $Pip install --quiet --upgrade pip
& $Pip install --quiet -r requirements.txt
& $Pip install --quiet pyinstaller

# ── Locate Tesseract (OCR for scanned PDFs) ───────────────────────────────────
# Tesseract must be installed separately on Windows:
#   https://github.com/UB-Mannheim/tesseract/wiki
# The installer adds itself to PATH by default; if not, set TESSERACT_DIR below.
$TesseractCandidates = @(
    "$env:ProgramFiles\Tesseract-OCR\tesseract.exe",
    "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe",
    "C:\Tesseract-OCR\tesseract.exe"
)
$TesseractExe = $TesseractCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $TesseractExe) {
    try { $TesseractExe = (Get-Command tesseract -ErrorAction Stop).Source } catch { }
}
if ($TesseractExe) {
    Write-Host "Found Tesseract: $TesseractExe"
    $TesseractDir   = Split-Path $TesseractExe
    $TessdataDir    = Join-Path $TesseractDir "tessdata"
    $TesseractHook  = @"
import os, sys
from pathlib import Path
# point pytesseract at the bundled (or installed) tesseract binary
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = str(Path(sys.executable).parent / 'tesseract.exe')
    os.environ.setdefault('TESSDATA_PREFIX', str(Path(sys.executable).parent / 'tessdata'))
except Exception:
    pass
"@
    $TesseractHook | Set-Content -Path "ocr_rthook.py" -Encoding UTF8
    $ExtraSpec = @(
        "--add-binary", "`"$TesseractExe;.`"",
        "--add-data",   "`"$TessdataDir;tessdata`"",
        "--runtime-hook", "ocr_rthook.py"
    )
} else {
    Write-Warning "Tesseract not found — scanned/image PDFs will be skipped (no OCR)."
    Write-Warning "Install from: https://github.com/UB-Mannheim/tesseract/wiki"
    $ExtraSpec = @()
}

# ── Build ──────────────────────────────────────────────────────────────────────
Write-Host "── Building Windows binary ────────────────────────────────────────────"
if ($ExtraSpec.Count -gt 0) {
    & $PyExe -m PyInstaller --clean --noconfirm @ExtraSpec documents-classifier.spec
} else {
    & $PyExe -m PyInstaller --clean --noconfirm documents-classifier.spec
}
if (Test-Path "ocr_rthook.py") { Remove-Item "ocr_rthook.py" }

Write-Host ""
Write-Host "Binary built: $ScriptDir\dist\documents-classifier.exe"
Write-Host ""
Write-Host "Copy it alongside config.yaml and run:"
Write-Host '  $env:GITHUB_TOKEN="ghp_..."; .\documents-classifier.exe C:\path\to\docs\'
