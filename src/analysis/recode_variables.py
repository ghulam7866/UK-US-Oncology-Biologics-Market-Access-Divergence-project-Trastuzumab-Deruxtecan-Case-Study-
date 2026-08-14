"""
recode_variables.py

Post-verification recoding of three analytic fields:
  era              - which NICE methods framework was in force
  uplift_applied   - whether EoL/severity weighting was applied and mattered
  outcome_3cat     - consolidated outcome category

Input:  data/processed/draft_coding_verified.csv  (manually verified, locked n=13)
Output: data/processed/coded_dataset_final.csv

Usage:
    python analysis/recode_variables.py

NOTE ON COLUMN NAMES: this script assumes your verified draft_coding_verified.csv uses
the schema built out over this session's verification tables:
    appraisal_id, drug_name, indication, severity_modifier, end_of_life,
    list_price_gbp, threshold_gbp, eag_disagreement_ord, comparator_type,
    comparator_is_chemo, outcome_label, outcome_binary, icer_base_gbp_approx,
    icer_pas_gbp, pas_type, notes
If your actual CSV headers differ (e.g. it still uses "ta_id" instead of
"appraisal_id"), update ID_COLUMN below rather than editing every reference.
"""

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
# Verified input file (source-checked n=13 dataset)
INPUT_FILE  = PROCESSED_DIR / "draft_coding_verified.csv"
OUTPUT_FILE = PROCESSED_DIR / "coded_dataset_final.csv"

# Name of the ID column in your verified CSV. Change this in one place if
# your actual file uses "ta_id" instead of "appraisal_id".
ID_COLUMN = "appraisal_id"

# ---------------------------------------------------------------------------
# Locked list of TAs for the final breast-cancer-focused dataset (n=13)
# ---------------------------------------------------------------------------
IN_SCOPE_TA_IDS = {
    "TA992",
    "TA371",
    "TA458",
    "TA632",
    "NICE_TA704",
    "NICE_TA786",
    "NICE_TA862",
    "TA257_lap",
    "TA257_tras",
    "TA424",
    "TA509",
    "NICE_TA569",
    "NICE_TA612",
}

# ---------------------------------------------------------------------------
# Rule 1: era (based on publication date, with date provenance)
# ---------------------------------------------------------------------------
# Each entry is (date_string, verified_bool). verified=True means the date
# was confirmed against a specific primary source (FAD/guidance page) during
# this session. verified=False means the date is plausible but unconfirmed.
#
# TA569 and TA612 are marked False even though sourced dates exist, because:
#   - TA569's Feb 2019 date came from your original raw extraction notes,
#     not an independently checked primary document.
#   - TA612 has two legitimately different dates in NICE's own records
#     (FAD: 17 Oct 2019; guidance published: 20 Nov 2019) and this script
#     picks one (FAD date) without that choice being flagged elsewhere.
# Neither affects `era` classification (both are unambiguously pre-2022),
# but "verified" should mean "checked", not "convenient".
PUBLICATION_DATES = {
    # ---------- verified against a primary source this session ----------
    "TA632":        ("2020-04-01", True),   # FAD, issue date April 2020
    "TA424":        ("2016-11-01", True),   # FAD, November 2016
    "TA509":        ("2018-01-01", True),   # FAD, January 2018
    "NICE_TA704":   ("2021-04-01", True),   # FAD, April 2021
    "NICE_TA786":   ("2022-03-01", True),   # FAD, March 2022
    "TA257_lap":    ("2012-04-01", True),   # FAD, April 2012 (issue date June 2012 per NICE overview page)
    "TA257_tras":   ("2012-04-01", True),   # same document as TA257_lap
    # ---------- plausible but not independently confirmed this session ----------
    "TA992":        ("2024-06-01", False),
    "TA371":        ("2015-11-01", False),
    "TA458":        ("2017-06-01", False),
    "NICE_TA862":   ("2023-01-01", False),
    "NICE_TA569":   ("2019-02-01", False),  # date came from original raw notes, not independently checked
    "NICE_TA612":   ("2019-10-01", False),  # FAD date; guidance publication date differs (2019-11-20)
}


def assign_era(appraisal_date: str) -> str:
    """Return 'post_2022_severity' if date >= 2022-01-01, else 'pre_2022_classic_eol'."""
    return "post_2022_severity" if appraisal_date >= "2022-01-01" else "pre_2022_classic_eol"


# ---------------------------------------------------------------------------
# Rule 2: uplift_applied
# ---------------------------------------------------------------------------
# Derived from manual verification of each appraisal's committee discussion.
#   not_applicable        - curative/adjuvant setting, EoL/severity never invoked
#   applied_insufficient  - criteria considered / modifier applied but outcome still negative
#   applied_decisive      - weighting contributed to a positive or CDF recommendation
#
# NICE_TA862 is coded applied_decisive despite the committee stating the
# severity modifier was "not convincingly met" in all scenarios, because the
# CDF recommendation rested on plausible sub-£30k ICERs that included the
# modifier in some scenarios. This is a judgment call, not a clean fact -
# revisit if reviewer feedback wants a stricter definition of "decisive".
UPLIFT_MAPPING = {
    "TA632":        "not_applicable",       # adjuvant, EoL not applicable
    "TA424":        "not_applicable",       # neoadjuvant, EoL explicitly N/A in FAD
    "NICE_TA569":   "not_applicable",       # adjuvant, EoL not applicable
    "NICE_TA612":   "not_applicable",       # extended adjuvant, EoL N/A
    "TA992":        "applied_insufficient", # severity modifier 1.2 applied, still rejected
    "TA371":        "applied_insufficient", # EoL criteria met, PAS insufficient, rejected
    "TA458":        "applied_decisive",     # CDF reconsideration, EoL-weighted ICER accepted
    "TA509":        "applied_decisive",     # EoL flexibility applied, recommended
    "NICE_TA704":   "applied_decisive",     # EoL met, CDF managed access
    "NICE_TA786":   "applied_decisive",     # EoL met, routine recommendation
    "NICE_TA862":   "applied_decisive",     # severity modifier used in scenarios underpinning CDF rec. (see note above)
    "TA257_lap":    "applied_insufficient", # EoL not met; committee said ICER too high even if it had been
    "TA257_tras":   "applied_insufficient", # same logic as lapatinib
}


# ---------------------------------------------------------------------------
# Rule 3: outcome_3cat
# ---------------------------------------------------------------------------
def assign_outcome_3cat(row: dict) -> str:
    """
    Consolidates outcome into three categories:
      - recommended
      - not_recommended
      - cdf_managed_access
    Reads outcome_label (falls back to notes text if outcome_label is blank
    or unrecognised - this fallback should rarely trigger on the verified
    n=13 and is here mainly as a safety net, not primary logic).
    """
    label = row.get("outcome_label", "").strip().lower()
    outcome_binary = row.get("outcome_binary", "").strip()
    notes = row.get("notes", "").lower()

    # Primary: explicit CDF mentions in the outcome label
    if "cdf" in label or "managed access" in label:
        return "cdf_managed_access"

    # Primary: outcome_binary is the cleanest signal when present
    if outcome_binary == "1":
        return "recommended"
    if outcome_binary == "0":
        return "not_recommended"

    # Fallback: text matching on label/notes if outcome_binary is missing/blank
    if "cdf" in notes or "managed access" in notes:
        return "cdf_managed_access"
    if "not recommended" in label or "not recommended" in notes:
        return "not_recommended"
    if "recommended" in label:
        return "recommended"

    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: input file not found at {INPUT_FILE}")
        print("Check that draft_coding_verified.csv exists in data/processed/, "
              "or update INPUT_FILE at the top of this script.")
        return

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    if not all_rows:
        print(f"No rows found in {INPUT_FILE.name}")
        return

    if ID_COLUMN not in all_rows[0]:
        print(f"ERROR: expected ID column '{ID_COLUMN}' not found in {INPUT_FILE.name}.")
        print(f"Available columns: {list(all_rows[0].keys())}")
        print("Update ID_COLUMN at the top of this script to match your actual header.")
        return

    # Filter to in-scope TAs
    rows = [r for r in all_rows if r[ID_COLUMN] in IN_SCOPE_TA_IDS]
    excluded = [r[ID_COLUMN] for r in all_rows if r[ID_COLUMN] not in IN_SCOPE_TA_IDS]
    if excluded:
        print(f"Excluded {len(excluded)} out-of-scope TA(s): {', '.join(excluded)}")

    found_ids = {r[ID_COLUMN] for r in rows}
    missing_from_input = IN_SCOPE_TA_IDS - found_ids
    if missing_from_input:
        print(f"WARNING: {len(missing_from_input)} in-scope TA(s) not found in input file: "
              f"{', '.join(sorted(missing_from_input))}")

    # Check for missing publication dates
    missing_dates = [r[ID_COLUMN] for r in rows if r[ID_COLUMN] not in PUBLICATION_DATES]
    if missing_dates:
        print(f"WARNING: no publication date for: {', '.join(missing_dates)}. "
              f"They will be assigned a default date of 2000-01-01 (unverified).")

    # Derive new fields
    for row in rows:
        ta_id = row[ID_COLUMN]
        date_info = PUBLICATION_DATES.get(ta_id, ("2000-01-01", False))
        date, verified = date_info[0], date_info[1]

        row["era"] = assign_era(date)
        row["date_verified"] = str(verified)

        row["outcome_3cat"] = assign_outcome_3cat(row)
        row["uplift_applied"] = UPLIFT_MAPPING.get(ta_id, "UNKNOWN")

        if row["outcome_3cat"] == "UNKNOWN":
            print(f"WARNING: could not determine outcome_3cat for {ta_id} - check outcome_label/notes")
        if row["uplift_applied"] == "UNKNOWN":
            print(f"WARNING: no uplift_applied mapping for {ta_id} - add it to UPLIFT_MAPPING")

    # Write final coded dataset
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCoded dataset written to {OUTPUT_FILE.name} ({len(rows)} rows)")
    print("Columns added: era, date_verified, outcome_3cat, uplift_applied")


if __name__ == "__main__":
    main()
