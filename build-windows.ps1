#!/usr/bin/env pwsh
# Build cv-classifier as a standalone Windows binary using PyInstaller.
#
# Requirements:
#   - Python 3.10+ installed on Windows (https://python.org/downloads)
#   - Run from the cv-classifier directory in PowerShell:
#
#       cd C:\path\to\cv-classifier
#       .\build-windows.ps1
#
# Output: .\dist\cv-classifier.exe

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

# ── Build ──────────────────────────────────────────────────────────────────────
Write-Host "── Building Windows binary ────────────────────────────────────────────"
& $PyExe -m PyInstaller `
    --onefile `
    --name cv-classifier `
    --hidden-import=pdfminer `
    --hidden-import=pdfminer.high_level `
    --hidden-import=pdfminer.layout `
    --hidden-import=pdfminer.pdfpage `
    --hidden-import=pdfminer.pdfinterp `
    --hidden-import=pdfminer.converter `
    --hidden-import=docx `
    --hidden-import=docx.oxml `
    --hidden-import=docx.oxml.ns `
    --hidden-import=docx.parts `
    --hidden-import=docx.parts.document `
    --hidden-import=yaml `
    --clean `
    --noconfirm `
    classifier.py

Write-Host ""
Write-Host "Binary built: $ScriptDir\dist\cv-classifier.exe"
Write-Host ""
Write-Host "Copy it alongside config.yaml and run:"
Write-Host '  $env:GITHUB_TOKEN="ghp_..."; .\cv-classifier.exe C:\path\to\cvs\'
