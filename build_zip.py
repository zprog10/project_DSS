"""Build DSS_###_P01.zip — final submission bundle."""
import os, zipfile, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "DSS_###_P01.zip")

# Files to include at the top level of the zip
TOP = [
    "DSS_###_P01.pdf",       # main report (deliverable 1)
    "README.md",
    "requirements.txt",
    # ETL implementation (deliverable 2)
    "00_setup.ipynb",
    "01_bronze.ipynb",
    "02_silver.ipynb",
    "03_gold.ipynb",
    "04_quality_checks.py",
    "99_verification.py",
    # Supporting documents
    "REPORT.md",
    "data_warehouse_matrix.md",
    "quality_report.json",
]

# Whole subfolders (filtered)
SCRIPTS_DIR = "scripts"

# Sensitive / heavy files we MUST NOT ship
EXCLUDE = {
    ".env",
    "DSS_###_P01.zip",
    "DSS91_Project01_Guide_ESI.pdf",
    "P01 Report Template - Data Mart.docx",
    "build_report_pdf.py",
    "build_zip.py",
    "extract_docs.py",
    "_extract_tables.py",
    "diagnose_countries.py",
    "teste.py",
    "report_draft.md",
    "DSS_###_P01.md",  # markdown source for the PDF, not needed in zip
}

# Remove existing zip first
if os.path.exists(OUT):
    os.remove(OUT)

added = []
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for fn in TOP:
        src = os.path.join(ROOT, fn)
        if not os.path.exists(src):
            print(f"  WARN missing: {fn}", file=sys.stderr)
            continue
        arc = f"DSS_###_P01/{fn}"
        z.write(src, arc)
        added.append(arc)

    scripts_path = os.path.join(ROOT, SCRIPTS_DIR)
    for name in sorted(os.listdir(scripts_path)):
        if name.startswith("__"):
            continue
        if name == "_patch_notebooks.py":  # dev-only
            continue
        if name == "regenerate_profiling.py":  # dev-only helper
            continue
        src = os.path.join(scripts_path, name)
        if os.path.isfile(src):
            arc = f"DSS_###_P01/{SCRIPTS_DIR}/{name}"
            z.write(src, arc)
            added.append(arc)

print(f"OK -> {OUT}")
print(f"   files: {len(added)}")
for a in added:
    print(f"   - {a}")
print(f"   size: {os.path.getsize(OUT)/1024:.1f} KB")
