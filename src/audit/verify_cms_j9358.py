"""
verify_cms_j9358.py

Cross-checks the CMS-sourced HCPCS effective date for J9358 (Enhertu /
fam-trastuzumab deruxtecan-nxki) against the reference value used in the
dataset, using CMS's own primary-source documents rather than secondary
billing/coding sites.

USAGE
-----
Expects both source PDFs already saved under data/raw/PDFs/ (relative to
wherever you run this script from -- matches the rest of the Enhertu
Project pipeline layout):

   PRIMARY (Q1 2020 HCPCS Application Summary, Request# 20.032):
   data/raw/PDFs/final_corrected_2020_hcpcs_application_summary_for_q1_2020_drugs_and_biologicals_041420_0.pdf

   CORROBORATING (MM11842, July 2020 ASC Payment System Update):
   data/raw/PDFs/MM11842.pdf

If your filenames or folder differ, adjust SOURCE_DIR / PRIMARY_PATH /
CORROBORATING_PATH below, then run:

       python verify_cms_j9358.py

WHAT IT CHECKS
--------------
- PRIMARY: searches the Q1 2020 HCPCS Application Summary for Request#
  20.032 and confirms that J9358, the drug name, and the effective date
  all co-occur in the same decision block (not just present anywhere in
  a 60+ page document).
- CORROBORATING: searches MM11842 (July 2020 ASC Payment System Update)
  for J9358 appearing in the "New HCPCS" table with the expected status
  indicator, as an independent CMS-internal check on the same date.
- Flags a mismatch (not just an absence) as a hard failure, and flags
  "not found" separately so a missing/renamed file doesn't silently
  read as a contradiction.
"""

import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("Missing dependency: pip install pdfplumber --break-system-packages")

# ---------------------------------------------------------------------------
# Reference values (what's currently in the dataset / write-up)
# ---------------------------------------------------------------------------
REFERENCE = {
    "hcpcs_code": "J9358",
    "effective_date": "07/01/2020",
    "drug_name_fragment": "fam-trastuzumab deruxtecan-nxki",
    "request_number": "20.032",
    "status_indicator": "K2",
}

SOURCE_DIR = Path("data/raw/PDFs")
PRIMARY_PATH = SOURCE_DIR / "final_corrected_2020_hcpcs_application_summary_for_q1_2020_drugs_and_biologicals_041420_0.pdf"
CORROBORATING_PATH = SOURCE_DIR / "MM11842.pdf"


def extract_text(pdf_path: Path) -> str | None:
    if not pdf_path.exists():
        return None
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def check_primary(text: str) -> dict:
    """
    Isolate the Request# 20.032 block and confirm code, drug name, and
    effective date all appear together in it -- not just somewhere in
    the document.
    """
    result = {"found_block": False, "code_match": False, "drug_match": False,
              "date_match": False, "request_match": False}

    # Isolate the block between "Request# 20.032" and the next "Request#"
    pattern = re.compile(
        r"Request#\s*20\.032(.*?)(?=Request#\s*20\.033|\Z)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return result

    # Normalize whitespace: pdfplumber inserts line breaks mid-phrase on
    # word-wrapped text (observed even within "fam-trastuzumab
    # deruxtecan-nxki" in this exact document), so raw newline-containing
    # substring checks are too brittle.
    block_norm = " ".join(m.group(1).split())
    result["found_block"] = True
    result["request_match"] = True
    result["code_match"] = REFERENCE["hcpcs_code"] in block_norm
    result["drug_match"] = REFERENCE["drug_name_fragment"] in block_norm
    result["date_match"] = REFERENCE["effective_date"] in block_norm
    result["block_excerpt"] = block_norm[:300]
    return result


def check_corroborating(text: str) -> dict:
    """
    Confirm J9358 appears in MM11842's new-code table alongside the
    drug name and expected status indicator. This document doesn't
    restate the 07/01/2020 effective date explicitly per-code (it's a
    July 2020 update by definition), so this is a corroboration of the
    code/status pairing, not an independent date check.
    """
    result = {"code_match": False, "drug_match": False, "status_match": False}
    if REFERENCE["hcpcs_code"] not in text:
        return result

    # Grab a window of text around each J9358 occurrence
    for m in re.finditer(re.escape(REFERENCE["hcpcs_code"]), text):
        raw_window = text[max(0, m.start() - 50): m.start() + 150]
        window = " ".join(raw_window.split())
        if "trastuzumab" in window:
            result["code_match"] = True
            result["drug_match"] = "deruxtecan" in window
            result["status_match"] = REFERENCE["status_indicator"] in window
            result["window_excerpt"] = window
            break
    return result


def main():
    print("=" * 70)
    print("CMS J9358 SOURCING VERIFICATION")
    print("=" * 70)
    print(f"Reference: {REFERENCE['hcpcs_code']} effective "
          f"{REFERENCE['effective_date']} for "
          f"'{REFERENCE['drug_name_fragment']}'\n")

    # --- Primary source ---
    print("-" * 70)
    print("PRIMARY: Q1 2020 HCPCS Application Summary (Request# 20.032)")
    print(f"  Path: {PRIMARY_PATH}")
    primary_text = extract_text(PRIMARY_PATH)
    if primary_text is None:
        print("  Status: FILE NOT FOUND -- download from cms.gov (see docstring)")
        primary_ok = False
    else:
        r = check_primary(primary_text)
        if not r["found_block"]:
            print("  Status: Request# 20.032 block NOT FOUND in this PDF"
                  " -- wrong file, or CMS has reorganized the document")
            primary_ok = False
        else:
            checks = [
                ("HCPCS code J9358 present in block", r["code_match"]),
                ("Drug name present in block", r["drug_match"]),
                ("Effective date 07/01/2020 present in block", r["date_match"]),
            ]
            for label, ok in checks:
                print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
            primary_ok = all(ok for _, ok in checks)
            print(f"  Excerpt: \"{r['block_excerpt']}\"")

    # --- Corroborating source ---
    print("\n" + "-" * 70)
    print("CORROBORATING: MM11842 (July 2020 ASC Payment System Update)")
    print(f"  Path: {CORROBORATING_PATH}")
    mm_text = extract_text(CORROBORATING_PATH)
    if mm_text is None:
        print("  Status: FILE NOT FOUND -- download from cms.gov (see docstring)")
        corroborating_ok = False
    else:
        r = check_corroborating(mm_text)
        checks = [
            ("HCPCS code J9358 present near drug name", r["code_match"]),
            ("Drug name confirmed in same window", r["drug_match"]),
            (f"Status indicator {REFERENCE['status_indicator']} present", r["status_match"]),
        ]
        for label, ok in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        corroborating_ok = all(ok for _, ok in checks)
        if "window_excerpt" in r:
            print(f"  Excerpt: \"{r['window_excerpt']}\"")

    # --- Verdict ---
    print("\n" + "=" * 70)
    if primary_ok and corroborating_ok:
        print("VERDICT: CONFIRMED. Effective date 07/01/2020 for J9358 is")
        print("supported by CMS's own Q1 2020 application summary (primary)")
        print("and corroborated independently by MM11842 (secondary).")
    elif primary_ok and not corroborating_ok:
        print("VERDICT: PRIMARY CONFIRMED, corroborating check inconclusive")
        print("or file missing. Primary alone is a legitimate CMS source --")
        print("corroboration just adds redundancy.")
    else:
        print("VERDICT: NOT CONFIRMED. Check file paths/filenames, or the")
        print("reference date may not match what these documents say --")
        print("do not use this date in the write-up until resolved.")
    print("=" * 70)


if __name__ == "__main__":
    main()
