"""
check_cdf_false_positives.py

Checks NICE final-appraisal text files for "Cancer Drugs Fund" mentions and
classifies each hit as:
  - LIKELY GENUINE  : CDF appears inside the numbered‑recommendation section
                      AND has routing language AND (if --drug given) the
                      appraised drug name appears in the same window.
  - OUTSIDE RECOMMENDATION ZONE : the hit is not in the 1.‑recommendation
                      section (likely incidental/boilerplate).
  - LIKELY FALSE POS : CDF appears without routing context, or is a known
                      boilerplate phrase, or (if --drug given) the appraised
                      drug name is not found in the window.
  - AMBIGUOUS / UNCLEAR : both/neither signal present (manual check needed).

New in this version:
  • Optional --drug NAME flag to filter out comparator‑drug mentions.
  • If --drug is provided, any CDF hit where the drug name does not appear
    in the surrounding window is automatically considered a false positive.
  • INCIDENTAL_SIGNALS now includes "Cancer Drugs Fund list" to catch
    boilerplate administrative mentions (e.g., reference lists).

Usage:
    python check_cdf_false_positives.py file1.txt file2.txt ...
    python check_cdf_false_positives.py --dir /path/to/appraisals/
    python check_cdf_false_positives.py --drug tucatinib --dir /path/to/appraisals/
"""

import argparse
import glob
import os
import re

CDF_PATTERN = re.compile(r"Cancer Drugs Fund", re.IGNORECASE)

ROUTING_SIGNALS = [
    r"\bCDF\b",
    r"managed access",
    r"data collection agreement",
    r"data collection arrangement",
    r"recommended.{0,80}Cancer Drugs Fund",
    r"Cancer Drugs Fund.{0,80}recommended",
    r"routed? (?:through|via) the Cancer Drugs Fund",
    r"Cancer Drugs Fund.{0,40}(?:while|until) further data",
]

INCIDENTAL_SIGNALS = [
    r"Cancer Drugs Fund clinical lead",
    r"Cancer Drugs Fund team",
    r"heard from the Cancer Drugs Fund",
    r"Cancer Drugs Fund reconsideration",
    r"Appraisal and funding of cancer drugs",
    r"Cancer Drugs Fund list",                      # NEW – catches "Cancer Drugs Fund list" boilerplate
]

WINDOW_CHARS = 200


def find_recommendation_zone(text):
    """Return (start_char, end_char) of the numbered‑recommendation section, or None."""
    rec_start = None
    for m in re.finditer(r"^1\.\d+\s", text, re.MULTILINE):
        rec_start = m.start()
        break
    if rec_start is None:
        return None

    next_section = None
    for m in re.finditer(r"^(\d+)\.\s", text, re.MULTILINE):
        sec_num = m.group(1)
        if m.start() > rec_start and sec_num != "1":
            next_section = m.start()
            break

    end = next_section if next_section is not None else len(text)
    return (rec_start, end)


def classify(text, start, end, in_zone, drug_name=None):
    """
    Classify a CDF hit.
    If drug_name is given and the appraised drug’s name does NOT appear
    in the surrounding window, the hit is considered a false positive
    (likely about a comparator).
    """
    if not in_zone:
        return "OUTSIDE RECOMMENDATION ZONE — likely false positive", ""

    lo = max(0, start - WINDOW_CHARS)
    hi = min(len(text), end + WINDOW_CHARS)
    window = text[lo:hi]

    # --- drug‑name proximity check (if a drug name was supplied) ---
    if drug_name and not re.search(re.escape(drug_name), window, re.IGNORECASE):
        return (
            "LIKELY FALSE POSITIVE — drug name not in context (possible comparator)",
            "",
        )

    has_incidental = any(re.search(p, window, re.IGNORECASE) for p in INCIDENTAL_SIGNALS)
    has_routing = any(re.search(p, window, re.IGNORECASE) for p in ROUTING_SIGNALS)

    if has_routing and not has_incidental:
        verdict = "LIKELY GENUINE"
    elif has_incidental and not has_routing:
        verdict = "LIKELY FALSE POSITIVE"
    elif has_routing and has_incidental:
        verdict = "AMBIGUOUS (both signals present -- read manually)"
    else:
        verdict = "UNCLEAR (neither signal found -- read manually)"

    return verdict, window.replace("\n", " ")


def check_file(path, drug_name=None):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    zone = find_recommendation_zone(text)
    if zone is None:
        print(f"\n{'=' * 70}\n{os.path.basename(path)}: RECOMMENDATION ZONE NOT FOUND\n{'=' * 70}")
        print("  All CDF hits will be classified as OUTSIDE RECOMMENDATION ZONE.")
        hits = list(CDF_PATTERN.finditer(text))
        if hits:
            for i, m in enumerate(hits, 1):
                print(f"\n[{i}] offset {m.start()} -- OUTSIDE RECOMMENDATION ZONE — likely false positive")
                window = text[max(0, m.start()-WINDOW_CHARS):min(len(text), m.end()+WINDOW_CHARS)]
                print(f"    ...{window.replace(chr(10), ' ')}...")
        else:
            print("  (no mentions found)")
        return

    rec_start, rec_end = zone
    hits = list(CDF_PATTERN.finditer(text))
    print(f"\n{'=' * 70}\n{os.path.basename(path)}: {len(hits)} 'Cancer Drugs Fund' mention(s)\n{'=' * 70}")

    if not hits:
        print("  (no mentions found)")
        return

    for i, m in enumerate(hits, 1):
        in_zone = rec_start <= m.start() <= rec_end
        verdict, window = classify(text, m.start(), m.end(), in_zone, drug_name)
        print(f"\n[{i}] offset {m.start()} -- {verdict}")
        if verdict not in ("OUTSIDE RECOMMENDATION ZONE — likely false positive",
                           "LIKELY FALSE POSITIVE — drug name not in context (possible comparator)"):
            print(f"    ...{window}...")


def main():
    parser = argparse.ArgumentParser(description="Check appraisal texts for CDF regex false positives.")
    parser.add_argument("files", nargs="*", help="Path(s) to appraisal .txt files")
    parser.add_argument("--dir", help="Directory to glob *.txt files from", default=None)
    parser.add_argument("--drug", help="Appraised drug name (e.g., tucatinib) – used to filter out comparator mentions", default=None)
    args = parser.parse_args()

    paths = list(args.files)
    if args.dir:
        paths += glob.glob(os.path.join(args.dir, "*.txt"))

    if not paths:
        parser.error("Provide file paths and/or --dir")

    for path in paths:
        if os.path.isfile(path):
            check_file(path, args.drug)
        else:
            print(f"\nSKIPPED (not found): {path}")


if __name__ == "__main__":
    main()
