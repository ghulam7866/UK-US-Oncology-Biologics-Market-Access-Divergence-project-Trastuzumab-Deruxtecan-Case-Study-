"""
Searches the cleaned NICE text files in data/processed/ for key terms
(ICER, QALY, PAS, discount, threshold, cost-effectiveness) and prints
each match with surrounding context, so you can scan for the actual
figures without reading the full document.

Matches are also written to data/processed/{stem}_matches.txt, so you
can transcribe figures into the spreadsheet from a saved file instead
of scrolling back through the terminal.

NEW: After searching, a draft coding row is generated per document and
all rows are saved to data/processed/_draft_coding.csv.  Every guessed
field is labelled "_guess" – these are FIRST PASSES to verify against
the _matches.txt file, not final values.

Usage:
    python search_key_figures.py
"""

import csv
import re
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Terms to search for. Add to this list as you find other things you need.
SEARCH_TERMS = [
    r"ICER",
    r"QALY",
    r"\bPAS\b",
    r"discount",
    r"threshold",
    r"cost[- ]effectiveness",
    r"£[\d,]+",
    r"\*{4,}",
    r"end[- ]of[- ]life",
    r"severity modifier",
    r"1\.2|1\.7",
    r"Cancer Drugs Fund|\bCDF\b",
    r"not recommended",
    r"appeal",
    r"committee (considered|concluded|discussed)",
]

CONTEXT_CHARS = 200  # characters of context on each side of a match

# ---------------------------------------------------------------------------
# Patterns for the draft structured row (lightweight automated coding)
# ---------------------------------------------------------------------------
ICER_PATTERN = re.compile(r"£([\d,]{4,7})\s*(?:per QALY|/QALY)?", re.IGNORECASE)
SEVERITY_MODIFIER_PATTERN = re.compile(r"severity modifier", re.IGNORECASE)
CLASSIC_EOL_PATTERN = re.compile(r"end[- ]of[- ]life", re.IGNORECASE)
CDF_PATTERN = re.compile(r"Cancer Drugs Fund|\bCDF\b", re.IGNORECASE)
NOT_RECOMMENDED_PATTERN = re.compile(r"not recommended", re.IGNORECASE)
APPEAL_PATTERN = re.compile(r"\bappeal", re.IGNORECASE)


def draft_row(txt_path: Path, text: str) -> dict:
    """Best-guess structured row from a single TA's cleaned text.
    Every field is a draft for manual verification, not a final value —
    this just saves you re-reading the whole doc to fill the spreadsheet."""

    icer_matches = ICER_PATTERN.findall(text)
    has_severity_modifier = bool(SEVERITY_MODIFIER_PATTERN.search(text))
    has_classic_eol = bool(CLASSIC_EOL_PATTERN.search(text))
    has_cdf = bool(CDF_PATTERN.search(text))
    has_not_recommended = bool(NOT_RECOMMENDED_PATTERN.search(text))
    has_appeal = bool(APPEAL_PATTERN.search(text))

    # Era flag: presence of "severity modifier" language implies 2022+ era;
    # presence of classic EoL language (without severity modifier) implies
    # pre-2022 era. If both or neither appear, flag for manual review.
    if has_severity_modifier and not has_classic_eol:
        era = "post_2022_severity"
    elif has_classic_eol and not has_severity_modifier:
        era = "pre_2022_classic_eol"
    else:
        era = "AMBIGUOUS — check manually"

    # outcome_3cat: CDF takes priority over not_recommended if both appear
    # (CDF documents often discuss why full recommendation wasn't reached)
    if has_cdf:
        outcome_3cat = "cdf_managed_access"
    elif has_not_recommended:
        outcome_3cat = "not_recommended"
    else:
        outcome_3cat = "recommended — VERIFY (absence of markers isn't confirmation)"

    return {
        "ta_id": txt_path.stem,
        "icer_candidates": "; ".join(sorted(set(icer_matches))) or "NONE FOUND — check manually",
        "era_guess": era,
        "outcome_3cat_guess": outcome_3cat,
        "appealed_guess": has_appeal,
        "n_icer_mentions": len(icer_matches),
    }


def search_file(txt_path: Path, draft_rows: list):
    """Search for key terms and append a draft coding row to draft_rows."""
    text = txt_path.read_text(encoding="utf-8")
    combined_pattern = "|".join(SEARCH_TERMS)

    matches = list(re.finditer(combined_pattern, text, flags=re.IGNORECASE))

    if not matches:
        print(f"\n{txt_path.name}: no matches found.")
        draft_rows.append(draft_row(txt_path, text))
        return

    header = f"{txt_path.name}: {len(matches)} matches"
    print(f"\n{'=' * 70}")
    print(header)
    print(f"{'=' * 70}")

    output_lines = [header, "=" * 70]

    for i, match in enumerate(matches, start=1):
        start = max(0, match.start() - CONTEXT_CHARS)
        end = min(len(text), match.end() + CONTEXT_CHARS)
        snippet = text[start:end].replace("\n", " ")

        matched_term = match.group(0)
        entry = (
            f"\n[{i}] term: {matched_term!r} (char offset {match.start()})\n"
            f"    ...{snippet}..."
        )

        print(f"\n[{i}] ...{snippet}...")
        output_lines.append(entry)

    matches_path = txt_path.parent / f"{txt_path.stem}_matches.txt"
    matches_path.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"\n  -> saved {matches_path.name} ({len(matches)} matches)")

    # Append draft structured row after the match search
    draft_rows.append(draft_row(txt_path, text))


def main():
    txt_files = sorted(PROCESSED_DIR.glob("*.txt"))
    # Exclude non‑appraisal files (e.g., _extraction_log.txt)
    txt_files = [f for f in txt_files if not f.name.startswith("_")]

    if not txt_files:
        print(f"No .txt files found in {PROCESSED_DIR}. "
              f"Run extract_nice_pdfs.py first.")
        return

    draft_rows = []
    for txt_path in txt_files:
        search_file(txt_path, draft_rows)

    # Write the draft coding sheet
    if draft_rows:
        draft_path = PROCESSED_DIR / "_draft_coding.csv"
        with draft_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=draft_rows[0].keys())
            writer.writeheader()
            writer.writerows(draft_rows)
        print(f"\nDraft coding sheet saved to {draft_path.name} "
              f"— verify every row against _matches.txt before using.")
    else:
        print("\nNo draft rows generated.")


if __name__ == "__main__":
    main()