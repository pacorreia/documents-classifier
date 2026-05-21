# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['classifier.py'],
    pathex=[],
    binaries=[
        # OCR: bundle tesseract and poppler's pdf2image utilities so the binary
        # is fully self-contained.  PyInstaller will auto-collect their
        # shared-library dependencies.
        # pdf2image calls pdfinfo (page count) then pdftoppm (rasterise).
        ('/usr/bin/tesseract', '.'),
        ('/usr/bin/pdftoppm', '.'),
        ('/usr/bin/pdfinfo', '.'),
    ],
    datas=[
        # English Tesseract language model (required at runtime).
        ('/usr/share/tesseract-ocr/5/tessdata/eng.traineddata', 'tessdata'),
    ],
    hiddenimports=[
        'pdfminer', 'pdfminer.high_level', 'pdfminer.layout', 'pdfminer.pdfpage',
        'pdfminer.pdfinterp', 'pdfminer.converter',
        'docx', 'docx.oxml', 'docx.oxml.ns', 'docx.parts', 'docx.parts.document',
        'yaml',
        'pytesseract', 'pytesseract.pytesseract',
        'pdf2image', 'pdf2image.pdf2image',
        'PIL', 'PIL.Image', 'PIL.ImageOps',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='documents-classifier',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
