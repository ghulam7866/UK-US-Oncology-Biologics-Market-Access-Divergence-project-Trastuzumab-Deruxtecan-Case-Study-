"""
clean_numeric_fields.py

Adds clean numeric columns derived from the free-text list_price_gbp and
icer_base_gbp_approx fields, without discarding the original text columns.

WHY THIS IS HAND-MAPPED, NOT REGEX-PARSED:
Several of these fields contain numbers that explicitly should NOT be used as the
value (e.g. NICE_TA704's list_price_gbp text says "117857 was course cost
not ICER" - a naive regex pulling the first number would grab exactly the
wrong figure). Others contain two genuinely different values for two
different subgroups (TA632) that must not be collapsed into one number
without losing information. With only 13 rows, an explicit per-row mapping
is safer and more auditable than parsing logic that would need as many
special cases as there are rows anyway.

New columns added:
  list_price_gbp_numeric   - single float, or blank if not cleanly derivable
  list_price_gbp_type      - one of: single_value, multi_value, approx,
                              not_stated, uncertain_attribution
  icer_base_gbp_numeric    - single float point estimate, or blank
  icer_base_gbp_lower_bound- float, only set for "above X" / ">=X" cases
  icer_base_gbp_type       - one of: single_value, multi_value, approx,
                              lower_bound_only, confidential, not_disclosed,
                              averaged_range
  comparator_is_chemo_excluded - True for rows that cannot be assigned a single
                                 comparator_is_chemo value (currently TA632)

Rows with multi_value or lower_bound_only types deliberately do NOT get a
single icer_base_gbp_numeric - forcing one would misrepresent the source.
Any downstream analysis (e.g. analysis.py) needs to explicitly decide how
to handle these rather than silently receiving a fabricated point estimate.

Input:  data/processed/coded_dataset_final.csv
Output: data/processed/coded_dataset_numeric.csv (all original columns +
        the 6 new ones above)

Usage:
    python analysis/clean_numeric_fields.py
"""

import csv
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
INPUT_FILE  = PROCESSED_DIR / "coded_dataset_final.csv"
OUTPUT_FILE = PROCESSED_DIR / "coded_dataset_numeric.csv"

ID_COLUMN = "appraisal_id"

# ---------------------------------------------------------------------------
# Hand-mapped list_price_gbp values
# ---------------------------------------------------------------------------
# Each entry: (numeric_or_None, type, note)
LIST_PRICE_MAP = {
    "TA992":      (1455, "single_value", ""),
    "TA371":      (None, "multi_value", "Two vial sizes (1641/2625) - no single list price; see original text"),
    "TA458":      (None, "multi_value", "Two vial sizes (1641/2625), same drug as TA371"),
    "TA632":      (None, "multi_value", "Two vial sizes (1641.01/2625.62) for two dose strengths"),
    "NICE_TA704": (None, "not_stated", "117857 in source text is course cost, explicitly NOT list price - excluded"),
    "NICE_TA786": (None, "not_stated", ""),
    "NICE_TA862": (1455, "single_value", ""),
    "TA257_lap":  (965.16, "approx", "Per-pack price; separate lifetime treatment cost (~28212) not captured here"),
    "TA257_tras": (407.40, "approx", "Per-vial price; separate lifetime treatment cost (~26018-26832) not captured here"),
    "TA424":      (None, "not_stated", ""),
    "TA509":      (4790, "approx", "Initial dose cost, not confirmed as full list price - treat as approximate"),
    "NICE_TA569": (2395, "uncertain_attribution", "Unclear which drug in the combination this price refers to"),
    "NICE_TA612": (4500, "single_value", ""),
}

# ---------------------------------------------------------------------------
# Hand-mapped icer_base_gbp_approx values
# ---------------------------------------------------------------------------
# Each entry: (numeric_point_estimate_or_None, lower_bound_or_None, type, note)
ICER_BASE_MAP = {
    "TA992":      (None, 30000, "lower_bound_only", "Qualitative 'considerably above £30,000', no specific figure given"),
    "TA371":      (166800, None, "averaged_range", "Mean of company (167200) and ERG (166400) base cases - both cited in source, averaged for a single representative figure. Flagged distinctly from multi_value (below) because this IS reduced to one number, unlike TA632's genuinely separate subgroup ICERs"),
    "TA458":      (166800, None, "averaged_range", "Same range as TA371 (inherited)"),
    "TA632":      (None, None, "multi_value", "Two genuinely distinct ICERs for two subgroups (node-negative vs trastuzumab: 8829; node-positive vs pertuzumab+trastuzumab+chemo: 4955) - NOT collapsible into one number, no numeric given"),
    "NICE_TA704": (47230, None, "single_value", "Company base case WITH confidential discount applied - despite 'base case' label this is a PAS-adjusted figure, not a pre-discount base case"),
    "NICE_TA786": (None, None, "confidential", ""),
    "NICE_TA862": (None, None, "confidential", ""),
    "TA257_lap":  (74000, None, "approx", "Committee's stated best estimate"),
    "TA257_tras": (None, 51000, "lower_bound_only", "Committee said 'at least £51,000' - treat as a lower bound, not a point estimate"),
    "TA424":      (23467, None, "single_value", "ERG base case, 4 cycles, no PAS"),
    "TA509":      (None, 30000, "lower_bound_only", "Company base case qualitatively 'above £30,000', no specific figure given"),
    "NICE_TA569": (None, None, "not_disclosed", ""),
    "NICE_TA612": (None, None, "confidential", ""),
}

# ---------------------------------------------------------------------------
# comparator_is_chemo exclusion flag
# ---------------------------------------------------------------------------
# TA632 covers two subgroups under one regulatory decision, with genuinely
# different comparators (node-negative vs trastuzumab alone [not chemo];
# node-positive vs pertuzumab+trastuzumab+chemo [chemo-containing]).
# comparator_is_chemo has no single correct value for this row.
#
# Decision: exclude from any analysis using comparator_is_chemo as a feature,
# rather than splitting into two sub-observations. Splitting would attach the
# same single outcome (recommended) to two rows differing only in
# comparator_is_chemo - that's pseudo-replication, not new information, and
# at n=13 it would distort that predictor's association with outcome.
#
# This is a targeted exclusion: TA632 remains in the dataset and in any
# analysis NOT using comparator_is_chemo as a feature.
COMPARATOR_IS_CHEMO_EXCLUDED = {"TA632"}


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: input file not found at {INPUT_FILE}")
        print("Run analysis/recode_variables.py first to produce coded_dataset_final.csv.")
        return

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows found in {INPUT_FILE.name}")
        return

    missing_price_map = [r[ID_COLUMN] for r in rows if r[ID_COLUMN] not in LIST_PRICE_MAP]
    missing_icer_map  = [r[ID_COLUMN] for r in rows if r[ID_COLUMN] not in ICER_BASE_MAP]
    if missing_price_map:
        print(f"WARNING: no list_price mapping for: {', '.join(missing_price_map)}")
    if missing_icer_map:
        print(f"WARNING: no icer_base mapping for: {', '.join(missing_icer_map)}")

    n_multi_value_icer = 0
    n_lower_bound_only = 0
    n_confidential = 0
    n_not_disclosed = 0
    n_averaged_range = 0

    for row in rows:
        ta_id = row[ID_COLUMN]

        price_val, price_type, price_note = LIST_PRICE_MAP.get(ta_id, (None, "not_mapped", ""))
        row["list_price_gbp_numeric"] = price_val if price_val is not None else ""
        row["list_price_gbp_type"] = price_type

        icer_val, icer_lower, icer_type, icer_note = ICER_BASE_MAP.get(ta_id, (None, None, "not_mapped", ""))
        row["icer_base_gbp_numeric"] = icer_val if icer_val is not None else ""
        row["icer_base_gbp_lower_bound"] = icer_lower if icer_lower is not None else ""
        row["icer_base_gbp_type"] = icer_type

        # ---- comparator_is_chemo exclusion flag ----
        row["comparator_is_chemo_excluded"] = str(
            ta_id in COMPARATOR_IS_CHEMO_EXCLUDED
        )

        if icer_type == "multi_value":
            n_multi_value_icer += 1
        elif icer_type == "lower_bound_only":
            n_lower_bound_only += 1
        elif icer_type == "confidential":
            n_confidential += 1
        elif icer_type == "not_disclosed":
            n_not_disclosed += 1
        elif icer_type == "averaged_range":
            n_averaged_range += 1

    fieldnames = list(rows[0].keys())
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCoded dataset with numeric fields written to {OUTPUT_FILE.name} ({len(rows)} rows)")
    print("Columns added: list_price_gbp_numeric, list_price_gbp_type, "
          "icer_base_gbp_numeric, icer_base_gbp_lower_bound, icer_base_gbp_type, "
          "comparator_is_chemo_excluded")
    print(f"\nSummary of icer_base_gbp_type across n={len(rows)}:")
    print(f"  multi_value (no single point estimate, subgroups/ranges only): {n_multi_value_icer}")
    print(f"  lower_bound_only (qualitative 'above X'/'at least X'):         {n_lower_bound_only}")
    print(f"  averaged_range (mean of cited range, reduced to one figure):   {n_averaged_range}")
    print(f"  confidential (PAS/no figure given):                            {n_confidential}")
    print(f"  not_disclosed (not reported in source):                       {n_not_disclosed}")
    n_usable = sum(1 for r in rows if r["icer_base_gbp_numeric"] != "")
    print(f"  usable single-point icer_base_gbp_numeric:                     {n_usable} of {len(rows)}")
    print(f"\nNOTE: only {n_usable}/{len(rows)} rows have a usable single-point ICER estimate.")
    print("Any downstream regression using icer_base_gbp_numeric as a feature will need")
    print("to either drop the remaining rows or explicitly handle the missing/bounded cases -")
    print("this script does not impute or guess values for them.")


if __name__ == "__main__":
    main()